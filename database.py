import logging
import os
import re
from typing import Optional

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    func,
    inspect,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from dotenv import load_dotenv

load_dotenv()


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Read database configuration from environment variables or Streamlit secrets."""
    value = os.getenv(key)
    if value:
        return value
    try:
        return st.secrets[key]
    except (KeyError, StreamlitSecretNotFoundError):
        return default


DATABASE_URL = str(
    get_secret("DATABASE_URL", "sqlite:///proposals.db") or "sqlite:///proposals.db"
)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

IS_STREAMLIT_CLOUD = (
    os.getenv("STREAMLIT_RUNTIME_ENV", "").lower() == "cloud"
    or os.getenv("IS_STREAMLIT_CLOUD", "").lower() in {"1", "true", "yes"}
)

connect_args = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite:")
    else {}
)
engine: Engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=not DATABASE_URL.startswith("sqlite:"),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

if IS_STREAMLIT_CLOUD and DATABASE_URL.startswith("sqlite:"):
    logging.warning(
        "Streamlit Cloud is using SQLite. Set DATABASE_URL to a persistent "
        "PostgreSQL URL because local SQLite storage may not persist across deployments."
    )


Base = declarative_base()


def get_db():
    """Yield a SQLAlchemy session and always close it after use."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TenantConfig(Base):
    __tablename__ = "tenant_configs"

    id = Column(Integer, primary_key=True, default=1)
    org_name = Column(String(255), nullable=False)
    corporate_entity_name = Column(String(255), nullable=False)
    contact_address = Column(Text, nullable=False, default="")
    admin_email = Column(String(320), nullable=False)
    logo_path = Column(String(1024), nullable=False, default="assets/logo.png")
    setup_completed = Column(Boolean, nullable=False, default=False)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Proposal(Base):
    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True)
    tracking_code = Column(String(100), nullable=False, index=True)
    vendor_name = Column(String(255), nullable=False)
    email = Column(String(320), nullable=False)
    phone_number = Column(String(100), nullable=True)
    category = Column(String(255), nullable=False)
    cac_number = Column(String(100), nullable=False)
    ai_summary = Column(Text, nullable=True)
    budget = Column(Float, nullable=True)
    is_flagged = Column(Boolean, nullable=False, default=False)
    is_high_priority = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="Draft")


VALID_PROPOSAL_STATUSES = ("Draft", "Pending", "Approved")


def get_db_engine() -> Engine:
    """Return the configured SQLAlchemy engine."""
    return engine


def get_db_connection():
    """Return a DB-API connection for existing raw cursor-based call sites."""
    return engine.raw_connection()


def ensure_proposal_status_column() -> None:
    """Add and normalize the lifecycle status field on existing proposal tables."""
    db_engine = engine
    columns = {column["name"] for column in inspect(db_engine).get_columns("proposals")}
    with db_engine.begin() as connection:
        if "status" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE proposals "
                    "ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'Draft'"
                )
            )
        connection.execute(
            text("""
                UPDATE proposals
                SET status = 'Draft'
                WHERE status IS NULL OR status = ''
                   OR status NOT IN ('Draft', 'Pending', 'Approved')
            """)
        )
        if db_engine.dialect.name == "postgresql":
            connection.execute(
                text("ALTER TABLE proposals ALTER COLUMN status SET DEFAULT 'Draft'")
            )


def init_db() -> None:
    """Create ORM tables and bring the proposal status field up to date."""
    Base.metadata.create_all(bind=engine)
    ensure_proposal_status_column()


def initialize_database() -> None:
    """Create new ORM tables and apply the existing additive proposal-status migration."""
    init_db()


def save_tenant_config(config: dict) -> None:
    """Persist the single active tenant's non-secret onboarding settings."""
    init_db()
    with SessionLocal.begin() as session:
        tenant = session.get(TenantConfig, 1)
        if tenant is None:
            tenant = TenantConfig(id=1)
            session.add(tenant)
        tenant.org_name = config["org_name"]
        tenant.corporate_entity_name = config["corporate_entity_name"]
        tenant.contact_address = config["contact_address"]
        tenant.admin_email = config["admin_email"]
        tenant.logo_path = config["logo_path"]
        tenant.setup_completed = bool(config.get("setup_completed", False))


def normalize_proposal_status(status):
    """Validate a proposal status and use Draft for invalid or missing values."""
    if status is None:
        return "Draft"
    normalized = str(status).strip()
    return (
        normalized
        if normalized in VALID_PROPOSAL_STATUSES
        else "Draft"
    )


def sanitize_budget(budget_val):
    """Convert budget strings to floats, returning None for invalid amounts."""
    if isinstance(budget_val, (int, float)):
        return float(budget_val)
    if isinstance(budget_val, str):
        cleaned = re.sub(r"[^\d.]", "", budget_val)
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None
    return None


def insert_proposal(
    tracking_code,
    vendor_name,
    email,
    category,
    cac_number,
    ai_summary,
    budget,
    is_flagged=False,
    status="Draft",
    phone_number=None,
):
    """Insert a proposal while retaining the existing PostgreSQL table contract."""
    safe_budget = sanitize_budget(budget)
    normalized_status = normalize_proposal_status(status)
    proposal = Proposal(
        tracking_code=tracking_code,
        vendor_name=vendor_name,
        email=email,
        phone_number=phone_number,
        category=category,
        cac_number=cac_number,
        ai_summary=ai_summary,
        budget=safe_budget,
        is_flagged=is_flagged,
        is_high_priority=bool(
            safe_budget is not None and safe_budget >= 50000000.0
        ),
        status=normalized_status,
    )
    with SessionLocal.begin() as session:
        session.add(proposal)


def update_proposal_status(proposal_id, status):
    """Update one proposal's lifecycle status."""
    with SessionLocal.begin() as session:
        session.execute(
            text("UPDATE proposals SET status = :status WHERE id = :proposal_id"),
            {
                "status": normalize_proposal_status(status),
                "proposal_id": proposal_id,
            },
        )


def delete_proposal_by_id(proposal_id):
    """Delete one proposal by its primary key."""
    with SessionLocal.begin() as session:
        session.execute(
            text("DELETE FROM proposals WHERE id = :proposal_id"),
            {"proposal_id": proposal_id},
        )


def clear_legacy_or_test_proposals():
    """Delete proposals matching the application's existing test-data rules."""
    query = text("""
        DELETE FROM proposals
        WHERE ai_summary LIKE :summary_pattern
           OR tracking_code LIKE :tracking_pattern
           OR vendor_name = :vendor_name
    """)
    with SessionLocal.begin() as session:
        result = session.execute(
            query,
            {
                "summary_pattern": "%AI processing skipped%",
                "tracking_pattern": "TRK-TEST%",
                "vendor_name": "nan",
            },
        )
        return result.rowcount

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


DEFAULT_DATABASE_URL = "sqlite:///proposals.db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
_database_url_from_environment = bool(os.getenv("DATABASE_URL"))
_cloud_database_url_loaded = False

IS_STREAMLIT_CLOUD = (
    os.getenv("STREAMLIT_RUNTIME_ENV", "").lower() == "cloud"
    or os.getenv("IS_STREAMLIT_CLOUD", "").lower() in {"1", "true", "yes"}
)

def create_database_engine(database_url: str) -> Engine:
    is_sqlite = database_url.startswith("sqlite:")
    return create_engine(
        database_url,
        connect_args={"check_same_thread": False} if is_sqlite else {},
        pool_pre_ping=not is_sqlite,
    )


engine: Engine = create_database_engine(DATABASE_URL)
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
    company_logo_base64 = Column(Text, nullable=False, default="")
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
    status = Column(String(255), nullable=False, default="Draft")
    cac_verification_status = Column(String(255), nullable=False, default="Not checked")
    past_contract_count = Column(Integer, nullable=False, default=0)
    company_logo_base64 = Column(Text, nullable=False, default="")


VALID_PROPOSAL_STATUSES = (
    "Draft",
    "Pending",
    "Approved",
    "Rejected",
    "Clarification Requested",
)


def get_db_engine() -> Engine:
    """Return the configured SQLAlchemy engine."""
    global DATABASE_URL, _cloud_database_url_loaded, engine
    if not _database_url_from_environment and not _cloud_database_url_loaded:
        _cloud_database_url_loaded = True
        secret_database_url = get_secret("DATABASE_URL")
        if secret_database_url:
            DATABASE_URL = str(secret_database_url)
            if DATABASE_URL.startswith("postgres://"):
                DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
            engine.dispose()
            engine = create_database_engine(DATABASE_URL)
            SessionLocal.configure(bind=engine)
    return engine


def get_db_connection():
    """Return a DB-API connection for existing raw cursor-based call sites."""
    return get_db_engine().raw_connection()


def ensure_proposal_status_column() -> None:
    """Add and normalize the lifecycle status field on existing proposal tables."""
    db_engine = get_db_engine()
    columns = {column["name"] for column in inspect(db_engine).get_columns("proposals")}
    with db_engine.begin() as connection:
        if "status" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE proposals "
                    "ADD COLUMN status VARCHAR(255) NOT NULL DEFAULT 'Draft'"
                )
            )
            columns.add("status")
        if "cac_verification_status" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE proposals ADD COLUMN "
                    "cac_verification_status VARCHAR(255) NOT NULL DEFAULT 'Not checked'"
                )
            )
        if "past_contract_count" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE proposals ADD COLUMN "
                    "past_contract_count INTEGER NOT NULL DEFAULT 0"
                )
            )
        if "company_logo_base64" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE proposals ADD COLUMN "
                    "company_logo_base64 TEXT NOT NULL DEFAULT ''"
                )
            )
        connection.execute(
            text("""
                UPDATE proposals
                SET status = 'Draft'
                WHERE status IS NULL OR status = ''
                   OR (
                       status NOT IN (
                           'Draft', 'Pending', 'Approved', 'Rejected',
                           'Clarification Requested'
                       )
                       AND status NOT LIKE 'Routed: %'
                   )
            """)
        )
        if db_engine.dialect.name == "postgresql":
            connection.execute(
                text(
                    "ALTER TABLE proposals ALTER COLUMN status "
                    "TYPE VARCHAR(255), ALTER COLUMN status SET DEFAULT 'Draft'"
                )
            )
    tenant_columns = {
        column["name"]
        for column in inspect(db_engine).get_columns("tenant_configs")
    }
    if "company_logo_base64" not in tenant_columns:
        with db_engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE tenant_configs ADD COLUMN "
                    "company_logo_base64 TEXT NOT NULL DEFAULT ''"
                )
            )


def init_db() -> None:
    """Create ORM tables and bring the proposal status field up to date."""
    Base.metadata.create_all(bind=get_db_engine())
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
        tenant.org_name = config.get("org_name", "")
        tenant.corporate_entity_name = config.get("corporate_entity_name", "")
        tenant.contact_address = config.get("contact_address", "")
        tenant.admin_email = config.get("admin_email", "")
        tenant.logo_path = config.get("logo_path", "assets/logo.png")
        tenant.company_logo_base64 = config.get("company_logo_base64", "")
        tenant.setup_completed = bool(config.get("setup_completed", False))


def normalize_proposal_status(status):
    """Validate a proposal status, including department-routing actions."""
    if status is None:
        return "Draft"
    normalized = str(status).strip()
    if normalized in VALID_PROPOSAL_STATUSES:
        return normalized
    if normalized.lower().startswith("routed:"):
        department = normalized.split(":", 1)[1].strip()
        if department and len(department) <= 245:
            return f"Routed: {department}"
    return "Draft"


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
    cac_verification_status="Not checked",
    past_contract_count=0,
    company_logo_base64="",
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
        cac_verification_status=str(cac_verification_status)[:255],
        past_contract_count=max(0, int(past_contract_count or 0)),
        company_logo_base64=company_logo_base64 or "",
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

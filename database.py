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
from sqlalchemy.orm import declarative_base, sessionmaker

from dotenv import load_dotenv

load_dotenv()


def get_secret(key: str) -> Optional[str]:
    """Read database configuration from environment variables or Streamlit secrets."""
    value = os.getenv(key)
    if value:
        return value
    try:
        return st.secrets[key]
    except (KeyError, StreamlitSecretNotFoundError):
        return None


DATABASE_URL = get_secret("DATABASE_URL")
engine: Optional[Engine] = None
if DATABASE_URL:
    if DATABASE_URL.startswith(("postgres://", "postgresql://")):
        DATABASE_URL = DATABASE_URL.replace(
            DATABASE_URL.split("://", maxsplit=1)[0] + "://",
            "postgresql+psycopg2://",
            1,
        )
    elif DATABASE_URL.startswith("postgresql+psycopg://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgresql+psycopg://", "postgresql+psycopg2://", 1
        )
    elif not DATABASE_URL.startswith("postgresql+psycopg2://"):
        raise ValueError("DATABASE_URL must use a PostgreSQL driver.")
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    logging.warning(
        "PostgreSQL is not configured. Set DATABASE_URL in the environment "
        "or Streamlit secrets; proposal database features will be unavailable."
    )


Base = declarative_base()


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
    """Return the configured SQLAlchemy engine or explain the missing configuration."""
    if engine is None:
        raise RuntimeError(
            "PostgreSQL is unavailable. Configure DATABASE_URL in the environment "
            "or Streamlit secrets."
        )
    return engine


def get_db_connection():
    """Return a pooled DB-API connection for existing PostgreSQL query helpers."""
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
        connection.execute(
            text("ALTER TABLE proposals ALTER COLUMN status SET DEFAULT 'Draft'")
        )


def initialize_database() -> None:
    """Create new ORM tables and apply the existing additive proposal-status migration."""
    db_engine = get_db_engine()
    Base.metadata.create_all(bind=db_engine)
    ensure_proposal_status_column()


def save_tenant_config(config: dict) -> None:
    """Persist the single active tenant's non-secret onboarding settings."""
    initialize_database()
    db_engine = get_db_engine()
    session_factory = sessionmaker(bind=db_engine)
    with session_factory.begin() as session:
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
):
    """Insert a proposal while retaining the existing PostgreSQL table contract."""
    safe_budget = sanitize_budget(budget)
    normalized_status = normalize_proposal_status(status)
    is_high_priority = bool(
        safe_budget is not None and safe_budget >= 50000000.0
    )
    query = """
        INSERT INTO proposals (
            tracking_code, vendor_name, email, category, cac_number, ai_summary,
            budget, is_flagged, is_high_priority, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            query,
            (
                tracking_code,
                vendor_name,
                email,
                category,
                cac_number,
                ai_summary,
                safe_budget,
                is_flagged,
                is_high_priority,
                normalized_status,
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def update_proposal_status(proposal_id, status):
    """Update one proposal's lifecycle status."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE proposals SET status = %s WHERE id = %s;",
            (normalize_proposal_status(status), proposal_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def delete_proposal_by_id(proposal_id):
    """Delete one proposal by its primary key."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM proposals WHERE id = %s;", (proposal_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def clear_legacy_or_test_proposals():
    """Delete proposals matching the application's existing test-data rules."""
    query = """
        DELETE FROM proposals
        WHERE ai_summary LIKE %s
           OR tracking_code LIKE %s
           OR vendor_name = %s;
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(query, ("%AI processing skipped%", "TRK-TEST%", "nan"))
        deleted_count = cur.rowcount
        conn.commit()
        return deleted_count
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

import json
import logging
import os
import re
import secrets
import sqlite3
import string
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
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


SECURITY_DATABASE_PATH = Path(
    os.getenv(
        "SECURITY_DATABASE_PATH",
        str(Path(__file__).resolve().parent / "security_logs.db"),
    )
).expanduser()
if not SECURITY_DATABASE_PATH.is_absolute():
    SECURITY_DATABASE_PATH = Path(__file__).resolve().parent / SECURITY_DATABASE_PATH


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
    rc_number = Column(String(100), nullable=False, default="")
    filename = Column(String(1024), nullable=False, default="")
    ai_summary = Column(Text, nullable=True)
    budget = Column(Float, nullable=True)
    feasibility_rating = Column(String(100), nullable=False, default="Not assessed")
    risk_score = Column(Float, nullable=True)
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    is_flagged = Column(Boolean, nullable=False, default=False)
    is_high_priority = Column(Boolean, nullable=False, default=False)
    status = Column(String(255), nullable=False, default="Draft")
    cac_verification_status = Column(String(255), nullable=False, default="Not checked")
    past_contract_count = Column(Integer, nullable=False, default=0)
    company_logo_base64 = Column(Text, nullable=False, default="")


class KYBLog(Base):
    __tablename__ = "kyb_logs"

    id = Column(Integer, primary_key=True)
    proposal_id = Column(
        Integer,
        ForeignKey("proposals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rc_number = Column(String(100), nullable=False)
    company_status = Column(String(100), nullable=False, default="UNKNOWN")
    tin = Column(String(255), nullable=True)
    directors_json = Column(Text, nullable=False, default="[]")
    risk_label = Column(Text, nullable=False, default="Not assessed")
    verified_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class AuditScore(Base):
    __tablename__ = "audit_scores"

    id = Column(Integer, primary_key=True)
    proposal_id = Column(
        Integer,
        ForeignKey("proposals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    legal_risk_flags = Column(Text, nullable=False, default="[]")
    compliance_gaps = Column(Text, nullable=False, default="[]")
    raw_ai_json = Column(Text, nullable=False, default="{}")


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


def get_proposal_db_connection():
    """Return the configured proposal database's pooled DB-API connection."""
    return get_db_engine().raw_connection()


def get_db_connection() -> sqlite3.Connection:
    """Open the dedicated SQLite connection used by onboarding security tables."""
    SECURITY_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        SECURITY_DATABASE_PATH,
        timeout=10,
        isolation_level="DEFERRED",
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _utc_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp for security audit records."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_security_tables() -> None:
    """Create the onboarding-token and subscribed-client tables idempotently."""
    connection = get_db_connection()
    try:
        connection.execute("PRAGMA journal_mode = WAL")
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS onboarding_tokens (
                    id INTEGER PRIMARY KEY,
                    token TEXT UNIQUE NOT NULL,
                    assigned_client TEXT NOT NULL,
                    is_used INTEGER DEFAULT 0,
                    failed_attempts INTEGER DEFAULT 0,
                    is_locked INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    used_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS subscribed_clients (
                    id INTEGER PRIMARY KEY,
                    client_name TEXT UNIQUE NOT NULL,
                    contact_email TEXT NOT NULL,
                    subscription_status TEXT DEFAULT 'Active',
                    last_login TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_onboarding_tokens_client
                ON onboarding_tokens (assigned_client)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_subscribed_clients_status
                ON subscribed_clients (subscription_status)
                """
            )
    except sqlite3.Error:
        logging.exception("Could not initialize SQLite security tables.")
        raise
    finally:
        connection.close()


def create_onboarding_token(assigned_client: str) -> str:
    """Generate and store a unique single-use 16-character onboarding token."""
    client_name = assigned_client.strip() if isinstance(assigned_client, str) else ""
    if not client_name:
        raise ValueError("assigned_client must be a non-empty string.")

    alphabet = string.ascii_uppercase + string.digits
    connection = get_db_connection()
    try:
        for _ in range(10):
            token = "-".join(
                "".join(secrets.choice(alphabet) for _ in range(4))
                for _ in range(4)
            )
            try:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO onboarding_tokens (
                            token, assigned_client, created_at
                        ) VALUES (?, ?, ?)
                        """,
                        (token, client_name, _utc_timestamp()),
                    )
                return token
            except sqlite3.IntegrityError:
                continue
        raise RuntimeError("Could not generate a unique onboarding token.")
    except sqlite3.Error:
        logging.exception("Could not save onboarding token.")
        raise
    finally:
        connection.close()


def record_failed_attempt(token_input: str) -> tuple[int, bool]:
    """Increment attempts for a known token and lock it after two failures."""
    normalized_token = (
        token_input.strip().upper() if isinstance(token_input, str) else ""
    )
    if not normalized_token:
        return 0, False

    connection = get_db_connection()
    try:
        with connection:
            row = connection.execute(
                """
                SELECT id, failed_attempts, is_locked
                FROM onboarding_tokens
                WHERE token = ?
                """,
                (normalized_token,),
            ).fetchone()
            if row is None:
                return 0, False
            attempts = int(row["failed_attempts"]) + 1
            locked = bool(row["is_locked"]) or attempts >= 2
            connection.execute(
                """
                UPDATE onboarding_tokens
                SET failed_attempts = ?, is_locked = ?
                WHERE id = ?
                """,
                (attempts, int(locked), row["id"]),
            )
        return attempts, locked
    except sqlite3.Error:
        logging.exception("Could not record failed onboarding-token attempt.")
        return 0, False
    finally:
        connection.close()


def verify_and_consume_token(
    token_input: str,
    contact_email: str,
) -> tuple[bool, str]:
    """Atomically consume a valid token and activate its assigned client."""
    normalized_token = (
        token_input.strip().upper() if isinstance(token_input, str) else ""
    )
    email = contact_email.strip() if isinstance(contact_email, str) else ""
    if not normalized_token:
        return False, "Enter an onboarding token."
    if not email or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return False, "Enter a valid contact email address."

    connection = get_db_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
            SELECT id, assigned_client, is_used, failed_attempts, is_locked
            FROM onboarding_tokens
            WHERE token = ?
            """,
            (normalized_token,),
        ).fetchone()
        if row is None:
            connection.rollback()
            return False, "Invalid onboarding token."
        if row["is_used"]:
            connection.rollback()
            return False, "This onboarding token has already been used."
        if row["is_locked"]:
            connection.rollback()
            return False, "This onboarding token is locked. Contact an administrator."

        now = _utc_timestamp()
        updated = connection.execute(
            """
            UPDATE onboarding_tokens
            SET is_used = 1, used_at = ?
            WHERE id = ? AND is_used = 0 AND is_locked = 0
            """,
            (now, row["id"]),
        )
        if updated.rowcount != 1:
            connection.rollback()
            return False, "This onboarding token is no longer available."

        connection.execute(
            """
            INSERT INTO subscribed_clients (
                client_name, contact_email, subscription_status,
                last_login, created_at
            ) VALUES (?, ?, 'Active', ?, ?)
            ON CONFLICT(client_name) DO UPDATE SET
                contact_email = excluded.contact_email,
                subscription_status = 'Active',
                last_login = excluded.last_login
            """,
            (row["assigned_client"], email, now, now),
        )
        connection.commit()
        return True, f"Onboarding completed for {row['assigned_client']}."
    except sqlite3.Error:
        connection.rollback()
        logging.exception("Could not verify or consume onboarding token.")
        return False, "A database error prevented onboarding. Please try again."
    finally:
        connection.close()


def get_all_tokens() -> list[dict]:
    """Return onboarding-token audit rows, newest first."""
    connection = get_db_connection()
    try:
        rows = connection.execute(
            """
            SELECT id, token, assigned_client, is_used, failed_attempts,
                   is_locked, created_at, used_at
            FROM onboarding_tokens
            ORDER BY id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error:
        logging.exception("Could not retrieve onboarding-token audit rows.")
        return []
    finally:
        connection.close()


def get_subscribed_clients() -> list[dict]:
    """Return currently active client records for admin telemetry."""
    connection = get_db_connection()
    try:
        rows = connection.execute(
            """
            SELECT id, client_name, contact_email, subscription_status,
                   last_login, created_at
            FROM subscribed_clients
            WHERE subscription_status = 'Active'
            ORDER BY client_name COLLATE NOCASE
            """
        ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error:
        logging.exception("Could not retrieve subscribed-client records.")
        return []
    finally:
        connection.close()


def revoke_or_reset_token(token: str, action: str) -> bool:
    """Let administrators unlock, reset, or revoke an onboarding token."""
    normalized_token = token.strip().upper() if isinstance(token, str) else ""
    normalized_action = action.strip().lower() if isinstance(action, str) else ""
    if not normalized_token or normalized_action not in {
        "unlock",
        "reset",
        "revoke",
    }:
        return False

    connection = get_db_connection()
    try:
        with connection:
            if normalized_action == "unlock":
                cursor = connection.execute(
                    """
                    UPDATE onboarding_tokens
                    SET failed_attempts = 0, is_locked = 0
                    WHERE token = ? AND is_used = 0
                    """,
                    (normalized_token,),
                )
            elif normalized_action == "reset":
                cursor = connection.execute(
                    """
                    UPDATE onboarding_tokens
                    SET failed_attempts = 0, is_locked = 0,
                        is_used = 0, used_at = NULL
                    WHERE token = ?
                    """,
                    (normalized_token,),
                )
            else:
                cursor = connection.execute(
                    """
                    UPDATE onboarding_tokens
                    SET is_used = 1, used_at = COALESCE(used_at, ?)
                    WHERE token = ?
                    """,
                    (_utc_timestamp(), normalized_token),
                )
            return cursor.rowcount == 1
    except sqlite3.Error:
        logging.exception("Could not %s onboarding token.", normalized_action)
        return False
    finally:
        connection.close()


def ensure_proposal_status_column(db_engine: Engine | None = None) -> None:
    """Add and normalize the lifecycle status field on existing proposal tables."""
    db_engine = db_engine or get_db_engine()
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
        if "filename" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE proposals ADD COLUMN "
                    "filename VARCHAR(1024) NOT NULL DEFAULT ''"
                )
            )
        if "rc_number" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE proposals ADD COLUMN "
                    "rc_number VARCHAR(100) NOT NULL DEFAULT ''"
                )
            )
            connection.execute(
                text(
                    "UPDATE proposals SET rc_number = cac_number "
                    "WHERE rc_number = ''"
                )
            )
        if "feasibility_rating" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE proposals ADD COLUMN "
                    "feasibility_rating VARCHAR(100) NOT NULL "
                    "DEFAULT 'Not assessed'"
                )
            )
        if "risk_score" not in columns:
            connection.execute(
                text("ALTER TABLE proposals ADD COLUMN risk_score FLOAT")
            )
        if "timestamp" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE proposals ADD COLUMN timestamp "
                    "TIMESTAMP NULL"
                )
            )
            connection.execute(
                text(
                    "UPDATE proposals SET timestamp = CURRENT_TIMESTAMP "
                    "WHERE timestamp IS NULL"
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
    ensure_proposal_status_column(get_db_engine())


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


init_security_tables()


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
    filename="",
    feasibility_rating="Not assessed",
    risk_score=None,
    kyb_data=None,
    legal_risk_flags=None,
    compliance_gaps=None,
    raw_ai_json=None,
):
    """Persist a proposal and its KYB/audit records in one database transaction."""
    safe_budget = sanitize_budget(budget)
    normalized_status = normalize_proposal_status(status)
    proposal = Proposal(
        tracking_code=tracking_code,
        vendor_name=vendor_name,
        email=email,
        phone_number=phone_number,
        category=category,
        cac_number=cac_number,
        rc_number=str(cac_number),
        filename=str(filename or ""),
        ai_summary=ai_summary,
        budget=safe_budget,
        feasibility_rating=str(feasibility_rating or "Not assessed"),
        risk_score=float(risk_score) if risk_score is not None else None,
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
        session.flush()

        if kyb_data is not None:
            directors = kyb_data.get("directors", [])
            session.add(
                KYBLog(
                    proposal_id=proposal.id,
                    rc_number=str(kyb_data.get("rc_number") or cac_number),
                    company_status=str(
                        kyb_data.get("company_status") or "UNKNOWN"
                    ),
                    tin=str(kyb_data.get("tin") or ""),
                    directors_json=json.dumps(directors, ensure_ascii=False),
                    risk_label=str(
                        kyb_data.get("risk_label") or "Not assessed"
                    ),
                )
            )

        if any(
            value is not None
            for value in (legal_risk_flags, compliance_gaps, raw_ai_json)
        ):
            session.add(
                AuditScore(
                    proposal_id=proposal.id,
                    legal_risk_flags=json.dumps(
                        legal_risk_flags or [], ensure_ascii=False
                    ),
                    compliance_gaps=json.dumps(
                        compliance_gaps or [], ensure_ascii=False
                    ),
                    raw_ai_json=json.dumps(
                        raw_ai_json or {},
                        ensure_ascii=False,
                        default=str,
                    ),
                )
            )
        return proposal.id


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

import hashlib
import hmac
import json
import logging
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from cryptography.fernet import Fernet, InvalidToken


DB_FILE = Path(
    os.environ.get(
        "NEXUSVAULT_DB_PATH",
        Path(__file__).resolve().with_name("nexus_sovereign.db"),
    )
).expanduser()

_TABLE_COLUMNS = {
    "tenants": (
        ("tenant_slug", "TEXT", 1, None),
        ("full_corporation_name", "TEXT", 0, None),
        ("institution_category", "TEXT", 0, None),
        ("apex_title", "TEXT", 0, None),
        ("sub_directorates_json", "TEXT", 0, None),
        ("logo_path", "TEXT", 0, None),
        ("status", "TEXT", 0, None),
        ("is_deleted", "INTEGER", 0, "0"),
        ("deleted_at", "TEXT", 0, None),
        ("activated_at", "TEXT", 0, None),
        ("activated_by", "TEXT", 0, None),
        ("deactivated_at", "TEXT", 0, None),
        ("deactivated_by", "TEXT", 0, None),
    ),
    "tenant_auth_lockouts": (
        ("tenant_slug", "TEXT", 1, None),
        ("role", "TEXT", 2, None),
        ("failed_attempts", "INTEGER", 0, "0"),
        ("is_locked_out", "INTEGER", 0, "0"),
        ("locked_out_at", "TEXT", 0, None),
        ("updated_at", "TEXT", 0, None),
    ),
    "tenant_onboarding_contacts": (
        ("tenant_slug", "TEXT", 1, None),
        ("admin_email", "TEXT", 0, None),
        ("admin_phone", "TEXT", 0, None),
        ("created_at", "TEXT", 0, None),
    ),
    "admin_access_logs": (
        ("id", "INTEGER", 1, None),
        ("tenant_slug", "TEXT", 0, None),
        ("action", "TEXT", 0, None),
        ("actor", "TEXT", 0, None),
        ("timestamp", "DATETIME", 0, "CURRENT_TIMESTAMP"),
    ),
    "tenant_activity_logs": (
        ("id", "INTEGER", 1, None),
        ("tenant_slug", "TEXT", 0, None),
        ("activity_type", "TEXT", 0, None),
        ("description", "TEXT", 0, None),
        ("performed_by", "TEXT", 0, None),
        ("date", "TEXT", 0, None),
        ("time", "TEXT", 0, None),
        ("month", "TEXT", 0, None),
        ("year", "TEXT", 0, None),
        ("created_at", "TIMESTAMP", 0, None),
    ),
    "tenant_audit_logs": (
        ("id", "INTEGER", 1, None),
        ("tenant_slug", "TEXT", 0, None),
        ("timestamp", "TEXT", 0, None),
        ("actor", "TEXT", 0, None),
        ("action_type", "TEXT", 0, None),
        ("details", "TEXT", 0, None),
    ),
    "physical_proposals": (
        ("tracking_id", "TEXT", 1, None),
        ("tenant_slug", "TEXT", 0, None),
        ("organization_name", "TEXT", 0, None),
        ("organization_address", "TEXT", 0, None),
        ("cac_registration_number", "TEXT", 0, None),
        ("contact_phone", "TEXT", 0, None),
        ("official_email", "TEXT", 0, None),
        ("proposal_title", "TEXT", 0, None),
        ("submission_date", "TEXT", 0, None),
        ("signature_verified", "INTEGER", 0, None),
        ("document_filename", "TEXT", 0, None),
        ("document_sha256", "TEXT", 0, None),
        ("receipt_hash", "TEXT", 0, None),
        ("routed_directorate", "TEXT", 0, None),
        ("routing_basis", "TEXT", 0, None),
        ("submitted_by", "TEXT", 0, None),
        ("submitted_at", "TEXT", 0, None),
        ("document_ciphertext", "BLOB", 0, None),
    ),
    "unsolicited_proposals": (
        ("submission_id", "TEXT", 1, None),
        ("tenant_slug", "TEXT", 0, None),
        ("organization_name", "TEXT", 0, None),
        ("cac_registration_number", "TEXT", 0, None),
        ("tax_identification_number", "TEXT", 0, ""),
        ("proposal_title", "TEXT", 0, None),
        ("document_filename", "TEXT", 0, None),
        ("document_sha256", "TEXT", 0, None),
        ("submitted_at", "TEXT", 0, None),
    ),
    "departmental_review_dossiers": (
        ("id", "INTEGER", 1, None),
        ("tenant_slug", "TEXT", 0, None),
        ("tracking_id", "TEXT", 0, None),
        ("source_type", "TEXT", 0, None),
        ("organization_name", "TEXT", 0, None),
        ("proposal_title", "TEXT", 0, None),
        ("routed_directorate", "TEXT", 0, None),
        ("sector", "TEXT", 0, ""),
        ("submitted_at", "TEXT", 0, ""),
        ("created_at", "TEXT", 0, None),
    ),
    "statutory_compliance_checks": (
        ("id", "INTEGER", 1, None),
        ("tenant_slug", "TEXT", 0, None),
        ("tracking_id", "TEXT", 0, None),
        ("check_name", "TEXT", 0, None),
        ("verification_status", "TEXT", 0, None),
        ("registry_source", "TEXT", 0, None),
        ("credential_reference", "TEXT", 0, ""),
        ("result_details", "TEXT", 0, None),
        ("checked_at", "TEXT", 0, None),
        ("checked_by", "TEXT", 0, None),
    ),
    "departmental_appraisals": (
        ("id", "INTEGER", 1, None),
        ("tenant_slug", "TEXT", 0, None),
        ("tracking_id", "TEXT", 0, None),
        ("directorate", "TEXT", 0, None),
        ("appraiser", "TEXT", 0, None),
        ("appraisal_notes", "TEXT", 0, ""),
        ("executive_summary", "TEXT", 0, ""),
        ("signoff_status", "TEXT", 0, None),
        ("pushed_to_apex", "INTEGER", 0, "0"),
        ("updated_at", "TEXT", 0, None),
    ),
    "notification_outbox": (
        ("id", "INTEGER", 1, None),
        ("tenant_slug", "TEXT", 0, None),
        ("tracking_id", "TEXT", 0, None),
        ("channel", "TEXT", 0, None),
        ("recipient", "TEXT", 0, None),
        ("message", "TEXT", 0, None),
        ("status", "TEXT", 0, None),
        ("created_at", "TEXT", 0, None),
    ),
    "tenant_gateway_configs": (
        ("tenant_slug", "TEXT", 1, None),
        ("tsa_endpoint", "TEXT", 0, ""),
        ("tsa_key_ciphertext", "BLOB", 0, None),
        ("remita_endpoint", "TEXT", 0, ""),
        ("remita_merchant_key_ciphertext", "BLOB", 0, None),
        ("service_head", "TEXT", 0, None),
        ("fee_amount_minor", "INTEGER", 0, None),
        ("currency", "TEXT", 0, "NGN"),
        ("updated_at", "TEXT", 0, None),
        ("updated_by", "TEXT", 0, None),
    ),
    "tenant_tenders": (
        ("tender_id", "TEXT", 1, None),
        ("tenant_slug", "TEXT", 0, None),
        ("title", "TEXT", 0, None),
        ("description", "TEXT", 0, None),
        ("publishing_status", "TEXT", 0, None),
        ("expiration_at", "TEXT", 0, None),
        ("auto_lock", "INTEGER", 0, None),
        ("created_at", "TEXT", 0, None),
        ("created_by", "TEXT", 0, None),
    ),
    "tenant_committee_members": (
        ("member_id", "TEXT", 1, None),
        ("tenant_slug", "TEXT", 0, None),
        ("name", "TEXT", 0, None),
        ("email", "TEXT", 0, None),
        ("encrypted_access_token", "BLOB", 0, None),
        ("coi_signed", "INTEGER", 0, "0"),
        ("coi_signed_at", "TEXT", 0, None),
        ("created_at", "TEXT", 0, None),
    ),
    "tenant_committee_coi_signoffs": (
        ("id", "INTEGER", 1, None),
        ("tenant_slug", "TEXT", 0, None),
        ("member_id", "TEXT", 0, None),
        ("tracking_id", "TEXT", 0, None),
        ("declaration_status", "TEXT", 0, None),
        ("signed_by_name", "TEXT", 0, None),
        ("timestamp", "TEXT", 0, None),
        ("digital_signature_hash", "TEXT", 0, None),
    ),
    "tenant_committee_evaluations": (
        ("id", "INTEGER", 1, None),
        ("tenant_slug", "TEXT", 0, None),
        ("member_id", "TEXT", 0, None),
        ("tracking_id", "TEXT", 0, None),
        ("technical_score", "INTEGER", 0, None),
        ("financial_score", "INTEGER", 0, None),
        ("compliance_score", "INTEGER", 0, None),
        ("notes", "TEXT", 0, ""),
        ("submitted_at", "TEXT", 0, None),
    ),
    "proposal_governance": (
        ("id", "INTEGER", 1, None),
        ("tenant_slug", "TEXT", 0, None),
        ("tracking_id", "TEXT", 0, None),
        ("status", "TEXT", 0, None),
        ("updated_at", "TEXT", 0, None),
        ("updated_by", "TEXT", 0, None),
    ),
    "clearance_passes": (
        ("qr_pass_id", "TEXT", 1, None),
        ("tenant_slug", "TEXT", 0, None),
        ("rfq_code", "TEXT", 0, None),
        ("vendor_name", "TEXT", 0, None),
        ("email", "TEXT", 0, None),
        ("payment_reference", "TEXT", 0, None),
        ("proposal_title", "TEXT", 0, None),
        ("clearance_status", "TEXT", 0, None),
    ),
    "tenant_payment_verifications": (
        ("id", "INTEGER", 1, None),
        ("tenant_slug", "TEXT", 0, None),
        ("payment_reference", "TEXT", 0, None),
        ("qr_pass_id", "TEXT", 0, None),
        ("amount_minor", "INTEGER", 0, None),
        ("currency", "TEXT", 0, None),
        ("provider", "TEXT", 0, None),
        ("vendor_email", "TEXT", 0, None),
        ("verified_at", "TEXT", 0, None),
    ),
    "tenant_archive": (
        ("tenant_slug", "TEXT", 1, None),
        ("tenant_data_json", "TEXT", 0, None),
        ("archived_at", "DATETIME", 0, "CURRENT_TIMESTAMP"),
    ),
    "vendors": (
        ("vendor_slug", "TEXT", 1, None),
        ("tenant_slug", "TEXT", 0, None),
        ("vendor_name", "TEXT", 0, None),
        ("vendor_type", "TEXT", 0, None),
        ("email", "TEXT", 0, None),
        ("status", "TEXT", 0, "PENDING"),
        ("created_at", "DATETIME", 0, "CURRENT_TIMESTAMP"),
    ),
    "system_broadcast": (
        ("id", "INTEGER", 1, None),
        ("message", "TEXT", 0, None),
        ("updated_at", "DATETIME", 0, "CURRENT_TIMESTAMP"),
    ),
}

_CREATE_TABLES = (
    """
    CREATE TABLE IF NOT EXISTS tenants (
        tenant_slug TEXT PRIMARY KEY,
        full_corporation_name TEXT,
        institution_category TEXT,
        apex_title TEXT,
        sub_directorates_json TEXT,
        logo_path TEXT,
        status TEXT,
        is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
        deleted_at TEXT,
        activated_at TEXT,
        activated_by TEXT,
        deactivated_at TEXT,
        deactivated_by TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tenant_auth_lockouts (
        tenant_slug TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('front_desk', 'admin')),
        failed_attempts INTEGER NOT NULL DEFAULT 0 CHECK (failed_attempts >= 0),
        is_locked_out INTEGER NOT NULL DEFAULT 0 CHECK (is_locked_out IN (0, 1)),
        locked_out_at TEXT,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (tenant_slug, role),
        FOREIGN KEY (tenant_slug) REFERENCES tenants (tenant_slug)
            ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tenant_onboarding_contacts (
        tenant_slug TEXT PRIMARY KEY,
        admin_email TEXT NOT NULL,
        admin_phone TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS admin_access_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_slug TEXT,
        action TEXT,
        actor TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tenant_activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_slug TEXT NOT NULL,
        activity_type TEXT NOT NULL,
        description TEXT NOT NULL,
        performed_by TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        month TEXT NOT NULL,
        year TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tenant_audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_slug TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        actor TEXT NOT NULL,
        action_type TEXT NOT NULL,
        details TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS physical_proposals (
        tracking_id TEXT PRIMARY KEY,
        tenant_slug TEXT NOT NULL,
        organization_name TEXT NOT NULL,
        organization_address TEXT NOT NULL,
        cac_registration_number TEXT NOT NULL,
        contact_phone TEXT NOT NULL,
        official_email TEXT NOT NULL,
        proposal_title TEXT NOT NULL,
        submission_date TEXT NOT NULL,
        signature_verified INTEGER NOT NULL CHECK (signature_verified IN (0, 1)),
        document_filename TEXT NOT NULL,
        document_sha256 TEXT NOT NULL,
        receipt_hash TEXT NOT NULL,
        routed_directorate TEXT NOT NULL,
        routing_basis TEXT NOT NULL,
        submitted_by TEXT NOT NULL,
        submitted_at TEXT NOT NULL,
        document_ciphertext BLOB NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_physical_proposals_tenant_submitted
    ON physical_proposals (tenant_slug, submitted_at DESC, tracking_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS unsolicited_proposals (
        submission_id TEXT PRIMARY KEY,
        tenant_slug TEXT NOT NULL,
        organization_name TEXT NOT NULL,
        cac_registration_number TEXT NOT NULL,
        tax_identification_number TEXT NOT NULL DEFAULT '',
        proposal_title TEXT NOT NULL,
        document_filename TEXT NOT NULL,
        document_sha256 TEXT NOT NULL,
        submitted_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS departmental_review_dossiers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_slug TEXT NOT NULL,
        tracking_id TEXT NOT NULL,
        source_type TEXT NOT NULL,
        organization_name TEXT NOT NULL,
        proposal_title TEXT NOT NULL,
        routed_directorate TEXT NOT NULL,
        sector TEXT NOT NULL DEFAULT '',
        submitted_at TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        UNIQUE (tenant_slug, tracking_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_departmental_review_queue
    ON departmental_review_dossiers (
        tenant_slug, routed_directorate, submitted_at DESC, tracking_id
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS statutory_compliance_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_slug TEXT NOT NULL,
        tracking_id TEXT NOT NULL,
        check_name TEXT NOT NULL,
        verification_status TEXT NOT NULL,
        registry_source TEXT NOT NULL,
        credential_reference TEXT NOT NULL DEFAULT '',
        result_details TEXT NOT NULL,
        checked_at TEXT NOT NULL,
        checked_by TEXT NOT NULL,
        UNIQUE (tenant_slug, tracking_id, check_name)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_statutory_compliance_dossier
    ON statutory_compliance_checks (tenant_slug, tracking_id, check_name)
    """,
    """
    CREATE TABLE IF NOT EXISTS departmental_appraisals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_slug TEXT NOT NULL,
        tracking_id TEXT NOT NULL,
        directorate TEXT NOT NULL,
        appraiser TEXT NOT NULL,
        appraisal_notes TEXT NOT NULL DEFAULT '',
        executive_summary TEXT NOT NULL DEFAULT '',
        signoff_status TEXT NOT NULL CHECK (
            signoff_status IN ('Pending', 'Approved', 'Queried', 'Rejected')
        ),
        pushed_to_apex INTEGER NOT NULL DEFAULT 0 CHECK (pushed_to_apex IN (0, 1)),
        updated_at TEXT NOT NULL,
        UNIQUE (tenant_slug, tracking_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_departmental_appraisals_tenant_directorate
    ON departmental_appraisals (tenant_slug, directorate, signoff_status, updated_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_unsolicited_proposals_tenant_submitted
    ON unsolicited_proposals (tenant_slug, submitted_at DESC, submission_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS notification_outbox (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_slug TEXT NOT NULL,
        tracking_id TEXT NOT NULL,
        channel TEXT NOT NULL CHECK (channel IN ('sms', 'email')),
        recipient TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_notification_outbox_tenant_tracking
    ON notification_outbox (tenant_slug, tracking_id, id)
    """,
    """
    CREATE TABLE IF NOT EXISTS tenant_gateway_configs (
        tenant_slug TEXT PRIMARY KEY,
        tsa_endpoint TEXT NOT NULL DEFAULT '',
        tsa_key_ciphertext BLOB,
        remita_endpoint TEXT NOT NULL DEFAULT '',
        remita_merchant_key_ciphertext BLOB,
        service_head TEXT NOT NULL,
        fee_amount_minor INTEGER NOT NULL CHECK (fee_amount_minor >= 0),
        currency TEXT NOT NULL DEFAULT 'NGN',
        updated_at TEXT NOT NULL,
        updated_by TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tenant_tenders (
        tender_id TEXT PRIMARY KEY,
        tenant_slug TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        publishing_status TEXT NOT NULL CHECK (
            publishing_status IN ('DRAFT', 'PUBLISHED', 'LOCKED', 'CANCELLED')
        ),
        expiration_at TEXT NOT NULL,
        auto_lock INTEGER NOT NULL CHECK (auto_lock IN (0, 1)),
        created_at TEXT NOT NULL,
        created_by TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_tenant_tenders_tenant_expiration
    ON tenant_tenders (tenant_slug, expiration_at, tender_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS tenant_committee_members (
        member_id TEXT PRIMARY KEY,
        tenant_slug TEXT NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        encrypted_access_token BLOB NOT NULL,
        coi_signed INTEGER NOT NULL DEFAULT 0 CHECK (coi_signed IN (0, 1)),
        coi_signed_at TEXT,
        created_at TEXT NOT NULL,
        UNIQUE (tenant_slug, email)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_tenant_committee_members_tenant
    ON tenant_committee_members (tenant_slug, created_at, member_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS tenant_committee_coi_signoffs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_slug TEXT NOT NULL,
        member_id TEXT NOT NULL,
        tracking_id TEXT NOT NULL,
        declaration_status TEXT NOT NULL CHECK (
            declaration_status IN ('Signed', 'Declined')
        ),
        signed_by_name TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        digital_signature_hash TEXT NOT NULL,
        UNIQUE (tenant_slug, member_id, tracking_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_committee_coi_proposal
    ON tenant_committee_coi_signoffs (tenant_slug, tracking_id, declaration_status)
    """,
    """
    CREATE TABLE IF NOT EXISTS tenant_committee_evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_slug TEXT NOT NULL,
        member_id TEXT NOT NULL,
        tracking_id TEXT NOT NULL,
        technical_score INTEGER NOT NULL CHECK (
            technical_score BETWEEN 0 AND 100
        ),
        financial_score INTEGER NOT NULL CHECK (
            financial_score BETWEEN 0 AND 100
        ),
        compliance_score INTEGER NOT NULL CHECK (
            compliance_score BETWEEN 0 AND 100
        ),
        notes TEXT NOT NULL DEFAULT '',
        submitted_at TEXT NOT NULL,
        UNIQUE (tenant_slug, member_id, tracking_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_committee_evaluations_proposal
    ON tenant_committee_evaluations (tenant_slug, tracking_id, member_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS proposal_governance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_slug TEXT NOT NULL,
        tracking_id TEXT NOT NULL,
        status TEXT NOT NULL CHECK (
            status IN ('RECEIVED', 'RECALLED', 'STOPPED', 'RESUMED')
        ),
        updated_at TEXT NOT NULL,
        updated_by TEXT NOT NULL,
        UNIQUE (tenant_slug, tracking_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_tenant_audit_logs_tenant_timestamp
    ON tenant_audit_logs (tenant_slug, timestamp DESC, id DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS clearance_passes (
        qr_pass_id TEXT PRIMARY KEY,
        tenant_slug TEXT,
        rfq_code TEXT,
        vendor_name TEXT,
        email TEXT,
        payment_reference TEXT,
        proposal_title TEXT,
        clearance_status TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tenant_payment_verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_slug TEXT NOT NULL,
        payment_reference TEXT NOT NULL,
        qr_pass_id TEXT NOT NULL,
        amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
        currency TEXT NOT NULL,
        provider TEXT NOT NULL,
        vendor_email TEXT NOT NULL,
        verified_at TEXT NOT NULL,
        UNIQUE (tenant_slug, payment_reference),
        UNIQUE (tenant_slug, qr_pass_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_tenant_payment_verifications_tenant_verified
    ON tenant_payment_verifications (tenant_slug, verified_at DESC, id DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS tenant_archive (
        tenant_slug TEXT PRIMARY KEY,
        tenant_data_json TEXT NOT NULL,
        archived_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS vendors (
        vendor_slug TEXT PRIMARY KEY,
        tenant_slug TEXT NOT NULL,
        vendor_name TEXT NOT NULL,
        vendor_type TEXT NOT NULL CHECK (vendor_type IN ('solicited', 'unsolicited')),
        email TEXT,
        status TEXT NOT NULL DEFAULT 'Pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS system_broadcast (
        id INTEGER PRIMARY KEY,
        message TEXT NOT NULL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection, committing on success and always closing it."""
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_FILE, timeout=30)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _verify_schema(connection: sqlite3.Connection) -> None:
    for table_name, expected_columns in _TABLE_COLUMNS.items():
        rows = connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        actual_columns = tuple(
            (
                row["name"],
                row["type"].upper(),
                row["pk"],
                (
                    row["dflt_value"].strip("'\"").upper()
                    if row["dflt_value"] is not None
                    else None
                ),
            )
            for row in rows
        )
        if actual_columns != expected_columns:
            raise RuntimeError(
                f"SQLite table {table_name!r} does not match the required schema. "
                f"Expected {expected_columns!r}, found {actual_columns!r}."
            )

    table_sql = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' "
        "AND name = 'admin_access_logs'"
    ).fetchone()
    if table_sql is None or not re.search(
        r"\b id \s+ INTEGER \s+ PRIMARY \s+ KEY \s+ AUTOINCREMENT \b",
        table_sql["sql"],
        flags=re.IGNORECASE | re.VERBOSE,
    ):
        raise RuntimeError(
            "SQLite table 'admin_access_logs' must use an AUTOINCREMENT primary key."
        )


def _migrate_database_schema(connection: sqlite3.Connection) -> None:
    tenant_columns = {
        row["name"]
        for row in connection.execute('PRAGMA table_info("tenants")').fetchall()
    }
    tenant_lifecycle_columns = (
        ("is_deleted", "INTEGER NOT NULL DEFAULT 0"),
        ("deleted_at", "TEXT"),
        ("activated_at", "TEXT"),
        ("activated_by", "TEXT"),
        ("deactivated_at", "TEXT"),
        ("deactivated_by", "TEXT"),
    )
    for column_name, column_definition in tenant_lifecycle_columns:
        if column_name not in tenant_columns:
            connection.execute(
                f"ALTER TABLE tenants ADD COLUMN {column_name} {column_definition}"
            )

    unsolicited_columns = {
        row["name"]
        for row in connection.execute(
            'PRAGMA table_info("unsolicited_proposals")'
        ).fetchall()
    }
    if "tax_identification_number" not in unsolicited_columns:
        connection.execute(
            "ALTER TABLE unsolicited_proposals "
            "RENAME TO unsolicited_proposals_legacy"
        )
        connection.execute(
            """
            CREATE TABLE unsolicited_proposals (
                submission_id TEXT PRIMARY KEY,
                tenant_slug TEXT NOT NULL,
                organization_name TEXT NOT NULL,
                cac_registration_number TEXT NOT NULL,
                tax_identification_number TEXT NOT NULL DEFAULT '',
                proposal_title TEXT NOT NULL,
                document_filename TEXT NOT NULL,
                document_sha256 TEXT NOT NULL,
                submitted_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO unsolicited_proposals (
                submission_id, tenant_slug, organization_name,
                cac_registration_number, tax_identification_number,
                proposal_title, document_filename, document_sha256, submitted_at
            )
            SELECT submission_id, tenant_slug, organization_name,
                   cac_registration_number, '', proposal_title,
                   document_filename, document_sha256, submitted_at
            FROM unsolicited_proposals_legacy
            """
        )
        connection.execute("DROP TABLE unsolicited_proposals_legacy")
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_unsolicited_proposals_tenant_submitted
            ON unsolicited_proposals (tenant_slug, submitted_at DESC, submission_id)
            """
        )


def init_db() -> None:
    """Create the required tables and fail clearly if an existing schema conflicts."""
    with get_connection() as connection:
        vendors_table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'vendors'"
        ).fetchone() is not None
        for statement in _CREATE_TABLES:
            connection.execute(statement)
        _migrate_database_schema(connection)
        _verify_schema(connection)
        if not vendors_table_exists:
            _backfill_solicited_vendors(connection)


def _required_text(value: Any, field_name: str) -> str:
    normalized = str(value).strip() if value is not None else ""
    if not normalized:
        raise ValueError(f"{field_name} is required.")
    return normalized


def _insert_tenant_activity(
    connection: sqlite3.Connection,
    tenant_slug: str,
    activity_type: str,
    description: str,
    performed_by: str = "System/Admin",
) -> int:
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_type = _required_text(activity_type, "activity_type")
    normalized_description = _required_text(description, "description")
    normalized_actor = _required_text(performed_by, "performed_by")
    timestamp = datetime.now().astimezone()
    timestamp_text = timestamp.isoformat(timespec="seconds")
    cursor = connection.execute(
        """
        INSERT INTO tenant_activity_logs (
            tenant_slug, activity_type, description, performed_by,
            date, time, month, year, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            normalized_slug,
            normalized_type,
            normalized_description,
            normalized_actor,
            timestamp.strftime("%Y-%m-%d"),
            timestamp.strftime("%H:%M:%S"),
            timestamp.strftime("%B %Y"),
            timestamp.strftime("%Y"),
            timestamp.isoformat(sep=" ", timespec="seconds"),
        ),
    )
    connection.execute(
        """
        INSERT INTO tenant_audit_logs (
            tenant_slug, timestamp, actor, action_type, details
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            normalized_slug,
            timestamp_text,
            normalized_actor,
            normalized_type,
            normalized_description,
        ),
    )
    return int(cursor.lastrowid)


def log_tenant_activity(
    tenant_slug: str,
    actor: str,
    action_type: str,
    details: str,
) -> int:
    """Record an auditable tenant event with its actor, action, and details."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_actor = _required_text(actor, "actor")
    normalized_action = _required_text(action_type, "action_type")
    normalized_details = _required_text(details, "details")
    init_db()
    with get_connection() as connection:
        tenant = connection.execute(
            "SELECT 1 FROM tenants WHERE tenant_slug = ?",
            (normalized_slug,),
        ).fetchone()
        if tenant is None:
            raise ValueError("Cannot log activity for an unknown tenant.")
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        cursor = connection.execute(
            """
            INSERT INTO tenant_audit_logs (
                tenant_slug, timestamp, actor, action_type, details
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                normalized_slug,
                timestamp,
                normalized_actor,
                normalized_action,
                normalized_details,
            ),
        )
        return int(cursor.lastrowid)


def log_legacy_tenant_activity(
    tenant_slug: str,
    activity_type: str,
    description: str,
    performed_by: str = "System/Admin",
) -> int:
    """Record an entry in the legacy tenant activity timeline."""
    init_db()
    with get_connection() as connection:
        return _insert_tenant_activity(
            connection,
            tenant_slug,
            activity_type,
            description,
            performed_by,
        )


def get_tenant_activities(tenant_slug: str) -> list[dict[str, Any]]:
    """Return audit entries newest-first for exactly one tenant."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, tenant_slug, timestamp, actor, action_type, details
            FROM tenant_audit_logs
            WHERE tenant_slug = ?
            ORDER BY timestamp DESC, id DESC
            """,
            (normalized_slug,),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_tenant_activity(
    activity_id: int,
    tenant_slug: str,
    actor: str = "tenant_operator",
) -> bool:
    """Delete an audit entry only within the supplied tenant namespace."""
    if isinstance(activity_id, bool) or not isinstance(activity_id, int):
        raise TypeError("activity_id must be an integer.")
    if activity_id < 1:
        raise ValueError("activity_id must be greater than zero.")
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_actor = _required_text(actor, "actor")
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT action_type FROM tenant_audit_logs "
            "WHERE id = ? AND tenant_slug = ?",
            (activity_id, normalized_slug),
        ).fetchone()
        if row is None:
            return False
        cursor = connection.execute(
            "DELETE FROM tenant_audit_logs WHERE id = ? AND tenant_slug = ?",
            (activity_id, normalized_slug),
        )
        if cursor.rowcount != 1:
            return False

        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        connection.execute(
            """
            INSERT INTO tenant_audit_logs (
                tenant_slug, timestamp, actor, action_type, details
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                normalized_slug,
                timestamp,
                normalized_actor,
                "audit_entry_deleted",
                f"Deleted audit entry {activity_id} ({row['action_type']}).",
            ),
        )
        return True


def generate_physical_proposal_receipt_hash(
    proposal_data: dict[str, Any],
    document_bytes: bytes,
) -> str:
    """Hash canonical submission metadata together with the uploaded document."""
    if not isinstance(proposal_data, dict):
        raise TypeError("proposal_data must be a dictionary.")
    if not isinstance(document_bytes, bytes) or not document_bytes:
        raise ValueError("A non-empty document bundle is required.")

    canonical_metadata = json.dumps(
        proposal_data,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256()
    digest.update(len(canonical_metadata).to_bytes(8, "big"))
    digest.update(canonical_metadata)
    digest.update(len(document_bytes).to_bytes(8, "big"))
    digest.update(document_bytes)
    return digest.hexdigest()


def create_physical_proposal(
    tenant_slug: str,
    proposal_data: dict[str, Any],
    document_bytes: bytes,
    document_ciphertext: bytes,
    document_filename: str,
    routed_directorate: str,
    routing_basis: str,
    submitted_by: str,
) -> dict[str, Any]:
    """Persist a tenant-scoped physical intake, receipt, audit, and outbox."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    if not isinstance(proposal_data, dict):
        raise TypeError("proposal_data must be a dictionary.")
    if not isinstance(document_bytes, bytes) or not document_bytes:
        raise ValueError("A non-empty proposal document is required.")
    if not isinstance(document_ciphertext, bytes) or not document_ciphertext:
        raise ValueError("An encrypted proposal document is required.")

    fields = {
        name: _required_text(proposal_data.get(name), name)
        for name in (
            "organization_name",
            "organization_address",
            "cac_registration_number",
            "contact_phone",
            "official_email",
            "proposal_title",
            "submission_date",
        )
    }
    signature_verified = proposal_data.get("signature_verified")
    if not isinstance(signature_verified, bool):
        raise TypeError("signature_verified must be a boolean.")
    filename = _required_text(document_filename, "document_filename")
    filename = filename.replace("\\", "/").rsplit("/", 1)[-1]
    directorate = _required_text(routed_directorate, "routed_directorate")
    normalized_basis = _required_text(routing_basis, "routing_basis")
    actor = _required_text(submitted_by, "submitted_by")
    hash_metadata = {
        **fields,
        "tenant_slug": normalized_slug,
        "signature_verified": signature_verified,
        "document_filename": filename,
    }
    receipt_hash = generate_physical_proposal_receipt_hash(
        hash_metadata,
        document_bytes,
    )
    document_hash = hashlib.sha256(document_bytes).hexdigest()

    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        tenant = connection.execute(
            "SELECT status FROM tenants WHERE tenant_slug = ? AND is_deleted = 0",
            (normalized_slug,),
        ).fetchone()
        if tenant is None or str(tenant["status"] or "").strip().upper() != "ACTIVE":
            raise ValueError("This tenant is not active. Proposal intake is unavailable.")

        tracking_id = f"NV-PHY-{uuid.uuid4().hex.upper()}"
        submitted_at = datetime.now().astimezone().isoformat(timespec="seconds")
        connection.execute(
            """
            INSERT INTO physical_proposals (
                tracking_id, tenant_slug, organization_name, organization_address,
                cac_registration_number, contact_phone, official_email,
                proposal_title, submission_date, signature_verified,
                document_filename, document_sha256, receipt_hash,
                routed_directorate, routing_basis, submitted_by, submitted_at,
                document_ciphertext
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tracking_id,
                normalized_slug,
                fields["organization_name"],
                fields["organization_address"],
                fields["cac_registration_number"],
                fields["contact_phone"],
                fields["official_email"],
                fields["proposal_title"],
                fields["submission_date"],
                int(signature_verified),
                filename,
                document_hash,
                receipt_hash,
                directorate,
                normalized_basis,
                actor,
                submitted_at,
                document_ciphertext,
            ),
        )

        acknowledgement = (
            "Your proposal is acknowledged and due attention will be accorded "
            "for possible action. "
            f"Tracking ID: {tracking_id}. SHA-256 receipt: {receipt_hash}."
        )
        for channel, recipient in (
            ("sms", fields["contact_phone"]),
            ("email", fields["official_email"]),
        ):
            connection.execute(
                """
                INSERT INTO notification_outbox (
                    tenant_slug, tracking_id, channel, recipient, message,
                    status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_slug,
                    tracking_id,
                    channel,
                    recipient,
                    acknowledgement,
                    "SIMULATED_QUEUED",
                    submitted_at,
                ),
            )

        _insert_tenant_activity(
            connection,
            normalized_slug,
            "physical_proposal_submitted",
            (
                f"Tracking ID {tracking_id}; SHA-256 receipt {receipt_hash}; "
                f"routed to {directorate}."
            ),
            actor,
        )
    return {
        "tracking_id": tracking_id,
        "tenant_slug": normalized_slug,
        **fields,
        "signature_verified": signature_verified,
        "document_filename": filename,
        "document_sha256": document_hash,
        "receipt_hash": receipt_hash,
        "routed_directorate": directorate,
        "routing_basis": normalized_basis,
        "submitted_by": actor,
        "submitted_at": submitted_at,
    }


def get_physical_proposals(tenant_slug: str) -> list[dict[str, Any]]:
    """Return proposal metadata for one tenant; never return document ciphertext."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT tracking_id, tenant_slug, organization_name, organization_address,
                   cac_registration_number, contact_phone, official_email,
                   proposal_title, submission_date, signature_verified,
                   document_filename, document_sha256, receipt_hash,
                   routed_directorate, routing_basis, submitted_by, submitted_at
            FROM physical_proposals
            WHERE tenant_slug = ?
            ORDER BY submitted_at DESC, tracking_id
            """,
            (normalized_slug,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_physical_proposal_document(
    tenant_slug: str,
    tracking_id: str,
) -> dict[str, Any] | None:
    """Return one tenant-owned encrypted intake document for authorized handling."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_tracking = _required_text(tracking_id, "tracking_id")
    init_db()
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT tracking_id, tenant_slug, document_filename,
                   document_ciphertext
            FROM physical_proposals
            WHERE tenant_slug = ? AND tracking_id = ?
            """,
            (normalized_slug, normalized_tracking),
        ).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["document_ciphertext"] = bytes(result["document_ciphertext"])
    return result


def save_tenant_gateway_config(
    tenant_slug: str,
    tsa_endpoint: str,
    tsa_key_ciphertext: bytes | None,
    remita_endpoint: str,
    remita_merchant_key_ciphertext: bytes | None,
    service_head: str,
    fee_amount_minor: int,
    updated_by: str,
    currency: str = "NGN",
) -> dict[str, Any]:
    """Save gateway settings while keeping credential ciphertext out of reads."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_tsa_endpoint = str(tsa_endpoint or "").strip()
    normalized_remita_endpoint = str(remita_endpoint or "").strip()
    normalized_service_head = _required_text(service_head, "service_head")
    normalized_actor = _required_text(updated_by, "updated_by")
    normalized_currency = _required_text(currency, "currency").upper()
    if not isinstance(fee_amount_minor, int) or isinstance(fee_amount_minor, bool):
        raise TypeError("fee_amount_minor must be an integer.")
    if fee_amount_minor < 0:
        raise ValueError("fee_amount_minor cannot be negative.")
    for encrypted_value, field in (
        (tsa_key_ciphertext, "tsa_key_ciphertext"),
        (remita_merchant_key_ciphertext, "remita_merchant_key_ciphertext"),
    ):
        if encrypted_value is not None and (
            not isinstance(encrypted_value, bytes) or not encrypted_value
        ):
            raise ValueError(f"{field} must be non-empty bytes or None.")

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        tenant = connection.execute(
            "SELECT status FROM tenants WHERE tenant_slug = ? AND is_deleted = 0",
            (normalized_slug,),
        ).fetchone()
        if tenant is None or str(tenant["status"] or "").strip().upper() != "ACTIVE":
            raise ValueError("Gateway settings require an active tenant.")
        connection.execute(
            """
            INSERT INTO tenant_gateway_configs (
                tenant_slug, tsa_endpoint, tsa_key_ciphertext, remita_endpoint,
                remita_merchant_key_ciphertext, service_head, fee_amount_minor,
                currency, updated_at, updated_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tenant_slug) DO UPDATE SET
                tsa_endpoint = excluded.tsa_endpoint,
                tsa_key_ciphertext = COALESCE(
                    excluded.tsa_key_ciphertext,
                    tenant_gateway_configs.tsa_key_ciphertext
                ),
                remita_endpoint = excluded.remita_endpoint,
                remita_merchant_key_ciphertext = COALESCE(
                    excluded.remita_merchant_key_ciphertext,
                    tenant_gateway_configs.remita_merchant_key_ciphertext
                ),
                service_head = excluded.service_head,
                fee_amount_minor = excluded.fee_amount_minor,
                currency = excluded.currency,
                updated_at = excluded.updated_at,
                updated_by = excluded.updated_by
            """,
            (
                normalized_slug,
                normalized_tsa_endpoint,
                tsa_key_ciphertext,
                normalized_remita_endpoint,
                remita_merchant_key_ciphertext,
                normalized_service_head,
                fee_amount_minor,
                normalized_currency,
                timestamp,
                normalized_actor,
            ),
        )
        _insert_tenant_activity(
            connection,
            normalized_slug,
            "gateway_configuration_updated",
            (
                f"Gateway endpoints and {normalized_service_head} fee settings "
                f"updated to {normalized_currency} "
                f"{fee_amount_minor / 100:.2f}."
            ),
            normalized_actor,
        )
    result = get_tenant_gateway_config(normalized_slug)
    if result is None:
        raise RuntimeError("Saved gateway configuration could not be reloaded.")
    return result


def get_tenant_gateway_config(tenant_slug: str) -> dict[str, Any] | None:
    """Return gateway settings and credential-presence flags, never secrets."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    init_db()
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT tenant_slug, tsa_endpoint,
                   CASE WHEN tsa_key_ciphertext IS NOT NULL THEN 1 ELSE 0 END
                       AS tsa_key_configured,
                   remita_endpoint,
                   CASE WHEN remita_merchant_key_ciphertext IS NOT NULL
                       THEN 1 ELSE 0 END AS remita_key_configured,
                   service_head, fee_amount_minor, currency, updated_at, updated_by
            FROM tenant_gateway_configs
            WHERE tenant_slug = ?
            """,
            (normalized_slug,),
        ).fetchone()
    return dict(row) if row is not None else None


def get_tenant_financial_ledger(tenant_slug: str) -> list[dict[str, Any]]:
    """Return payment-reference entries belonging only to the requested tenant."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT pass.qr_pass_id, pass.tenant_slug, pass.rfq_code,
                   pass.vendor_name, pass.email, pass.payment_reference,
                   pass.proposal_title, pass.clearance_status,
                   verification.amount_minor, verification.currency,
                   verification.provider, verification.verified_at
            FROM clearance_passes AS pass
            LEFT JOIN tenant_payment_verifications AS verification
              ON verification.tenant_slug = pass.tenant_slug
             AND verification.qr_pass_id = pass.qr_pass_id
             AND verification.payment_reference = pass.payment_reference
            WHERE pass.tenant_slug = ?
            ORDER BY COALESCE(verification.verified_at, '') DESC, pass.qr_pass_id DESC
            """,
            (normalized_slug,),
        ).fetchall()
    return [dict(row) for row in rows]


def create_tenant_tender(
    tenant_slug: str,
    title: str,
    description: str,
    expiration_at: str,
    auto_lock: bool,
    created_by: str,
    publish_now: bool = False,
) -> dict[str, Any]:
    """Create a tender with a timezone-aware hard expiration timestamp."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_title = _required_text(title, "title")
    normalized_description = str(description or "").strip()
    normalized_actor = _required_text(created_by, "created_by")
    if not isinstance(auto_lock, bool) or not isinstance(publish_now, bool):
        raise TypeError("auto_lock and publish_now must be booleans.")
    try:
        expiry = datetime.fromisoformat(
            _required_text(expiration_at, "expiration_at").replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValueError("expiration_at must be a valid ISO-8601 timestamp.") from exc
    if expiry.tzinfo is None or expiry.utcoffset() is None:
        raise ValueError("expiration_at must include a timezone.")
    expiry = expiry.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    if expiry <= now:
        raise ValueError("Tender expiration must be in the future.")

    tender_id = f"NV-TND-{uuid.uuid4().hex.upper()}"
    timestamp = now.isoformat(timespec="seconds")
    status = "PUBLISHED" if publish_now else "DRAFT"
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        tenant = connection.execute(
            "SELECT status FROM tenants WHERE tenant_slug = ? AND is_deleted = 0",
            (normalized_slug,),
        ).fetchone()
        if tenant is None or str(tenant["status"] or "").strip().upper() != "ACTIVE":
            raise ValueError("Tender management requires an active tenant.")
        connection.execute(
            """
            INSERT INTO tenant_tenders (
                tender_id, tenant_slug, title, description, publishing_status,
                expiration_at, auto_lock, created_at, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tender_id,
                normalized_slug,
                normalized_title,
                normalized_description,
                status,
                expiry.isoformat(timespec="seconds"),
                int(auto_lock),
                timestamp,
                normalized_actor,
            ),
        )
        _insert_tenant_activity(
            connection,
            normalized_slug,
            "tender_created",
            f"Tender {tender_id} created with status {status}.",
            normalized_actor,
        )
    return {
        "tender_id": tender_id,
        "tenant_slug": normalized_slug,
        "title": normalized_title,
        "description": normalized_description,
        "publishing_status": status,
        "expiration_at": expiry.isoformat(timespec="seconds"),
        "auto_lock": auto_lock,
        "created_at": timestamp,
        "created_by": normalized_actor,
    }


def get_tenant_tenders(tenant_slug: str) -> list[dict[str, Any]]:
    """Return a tenant's tenders and atomically auto-lock expired publications."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        expired = connection.execute(
            """
            SELECT tender_id FROM tenant_tenders
            WHERE tenant_slug = ? AND publishing_status = 'PUBLISHED'
              AND auto_lock = 1 AND expiration_at <= ?
            """,
            (normalized_slug, now),
        ).fetchall()
        for row in expired:
            connection.execute(
                """
                UPDATE tenant_tenders SET publishing_status = 'LOCKED'
                WHERE tender_id = ? AND tenant_slug = ?
                  AND publishing_status = 'PUBLISHED'
                """,
                (row["tender_id"], normalized_slug),
            )
            _insert_tenant_activity(
                connection,
                normalized_slug,
                "tender_auto_locked",
                f"Tender {row['tender_id']} was locked at expiration.",
            )
        rows = connection.execute(
            """
            SELECT tender_id, tenant_slug, title, description, publishing_status,
                   expiration_at, auto_lock, created_at, created_by
            FROM tenant_tenders
            WHERE tenant_slug = ?
            ORDER BY created_at DESC, tender_id
            """,
            (normalized_slug,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_active_solicited_tenders(tenant_slug: str) -> list[dict[str, Any]]:
    """Return only this active tenant's published, unexpired tender windows."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    tenant = get_tenant_by_slug(normalized_slug)
    if tenant is None or str(tenant.get("status", "")).strip().upper() != "ACTIVE":
        return []
    now = datetime.now(timezone.utc)
    tenders = get_tenant_tenders(normalized_slug)
    active = []
    for tender in tenders:
        if tender["publishing_status"] != "PUBLISHED":
            continue
        try:
            expiration = datetime.fromisoformat(
                str(tender["expiration_at"]).replace("Z", "+00:00")
            )
        except ValueError:
            logging.error(
                "Tenant tender %s has an invalid expiration timestamp.",
                tender["tender_id"],
            )
            continue
        if expiration.tzinfo is None or expiration.utcoffset() is None:
            logging.error(
                "Tenant tender %s has a timezone-naive expiration timestamp.",
                tender["tender_id"],
            )
            continue
        if expiration.astimezone(timezone.utc) > now:
            active.append(tender)
    return active


def update_tenant_tender(
    tenant_slug: str,
    tender_id: str,
    publishing_status: str,
    auto_lock: bool,
    updated_by: str,
) -> bool:
    """Update publication/lock controls for a tender owned by this tenant."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_id = _required_text(tender_id, "tender_id")
    normalized_status = _required_text(
        publishing_status,
        "publishing_status",
    ).upper()
    normalized_actor = _required_text(updated_by, "updated_by")
    if normalized_status not in {"DRAFT", "PUBLISHED", "LOCKED", "CANCELLED"}:
        raise ValueError("Unsupported tender status.")
    if not isinstance(auto_lock, bool):
        raise TypeError("auto_lock must be a boolean.")

    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
            SELECT expiration_at FROM tenant_tenders
            WHERE tender_id = ? AND tenant_slug = ?
            """,
            (normalized_id, normalized_slug),
        ).fetchone()
        if row is None:
            return False
        expiry = datetime.fromisoformat(row["expiration_at"])
        if (
            normalized_status == "PUBLISHED"
            and expiry <= datetime.now(timezone.utc)
        ):
            raise ValueError("An expired tender cannot be published.")
        connection.execute(
            """
            UPDATE tenant_tenders
            SET publishing_status = ?, auto_lock = ?
            WHERE tender_id = ? AND tenant_slug = ?
            """,
            (normalized_status, int(auto_lock), normalized_id, normalized_slug),
        )
        _insert_tenant_activity(
            connection,
            normalized_slug,
            "tender_updated",
            (
                f"Tender {normalized_id} status set to {normalized_status}; "
                f"automatic expiration lock {'enabled' if auto_lock else 'disabled'}."
            ),
            normalized_actor,
        )
    return True


def replace_tenant_committee(
    tenant_slug: str,
    members: list[dict[str, Any]],
    updated_by: str,
) -> list[dict[str, Any]]:
    """Replace a tenant's 10–15 member roster, storing only encrypted tokens."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_actor = _required_text(updated_by, "updated_by")
    if not isinstance(members, list) or not 10 <= len(members) <= 15:
        raise ValueError("A committee roster must contain 10 to 15 members.")
    normalized_members = []
    seen_emails: set[str] = set()
    for member in members:
        if not isinstance(member, dict):
            raise TypeError("Each committee member must be a dictionary.")
        member_id = _required_text(member.get("member_id"), "member_id")
        name = _required_text(member.get("name"), "name")
        email = _required_text(member.get("email"), "email").lower()
        encrypted_token = member.get("encrypted_access_token")
        if not isinstance(encrypted_token, bytes) or not encrypted_token:
            raise ValueError("Every committee access token must be encrypted.")
        if email in seen_emails:
            raise ValueError("Committee member email addresses must be unique.")
        seen_emails.add(email)
        normalized_members.append((member_id, name, email, encrypted_token))

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        tenant = connection.execute(
            "SELECT status FROM tenants WHERE tenant_slug = ? AND is_deleted = 0",
            (normalized_slug,),
        ).fetchone()
        if tenant is None or str(tenant["status"] or "").strip().upper() != "ACTIVE":
            raise ValueError("Committee provisioning requires an active tenant.")
        connection.execute(
            "DELETE FROM tenant_committee_members WHERE tenant_slug = ?",
            (normalized_slug,),
        )
        connection.executemany(
            """
            INSERT INTO tenant_committee_members (
                member_id, tenant_slug, name, email, encrypted_access_token,
                coi_signed, coi_signed_at, created_at
            ) VALUES (?, ?, ?, ?, ?, 0, NULL, ?)
            """,
            [
                (member_id, normalized_slug, name, email, token, timestamp)
                for member_id, name, email, token in normalized_members
            ],
        )
        _insert_tenant_activity(
            connection,
            normalized_slug,
            "committee_roster_replaced",
            (
                f"Committee roster replaced with {len(normalized_members)} members; "
                "all COI sign-offs reset."
            ),
            normalized_actor,
        )
    return get_tenant_committee_members(normalized_slug)


def get_tenant_committee_members(tenant_slug: str) -> list[dict[str, Any]]:
    """List committee members and COI state without exposing encrypted tokens."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT member_id, tenant_slug, name, email, coi_signed,
                   coi_signed_at, created_at
            FROM tenant_committee_members
            WHERE tenant_slug = ?
            ORDER BY created_at, member_id
            """,
            (normalized_slug,),
        ).fetchall()
    return [dict(row) for row in rows]


def record_tenant_committee_coi_signoff(
    tenant_slug: str,
    member_id: str,
    actor: str,
) -> bool:
    """Record an executive-attested receipt of a member's COI sign-off."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_member_id = _required_text(member_id, "member_id")
    normalized_actor = _required_text(actor, "actor")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            """
            UPDATE tenant_committee_members
            SET coi_signed = 1, coi_signed_at = ?
            WHERE tenant_slug = ? AND member_id = ?
            """,
            (timestamp, normalized_slug, normalized_member_id),
        )
        if cursor.rowcount:
            _insert_tenant_activity(
                connection,
                normalized_slug,
                "committee_coi_signoff_recorded",
                f"COI sign-off receipt recorded for committee member {normalized_member_id}.",
                normalized_actor,
            )
    return cursor.rowcount == 1


def authenticate_tenant_committee_member(
    tenant_slug: str,
    access_token: str,
    encryption_key: bytes,
) -> dict[str, str] | None:
    """Validate a committee token against only the active tenant's roster."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_token = _required_text(access_token, "access_token")
    if not isinstance(encryption_key, bytes) or not encryption_key:
        raise ValueError("A valid committee-token encryption key is required.")
    try:
        fernet = Fernet(encryption_key)
    except (TypeError, ValueError) as exc:
        raise ValueError("The committee-token encryption key is invalid.") from exc

    init_db()
    with get_connection() as connection:
        tenant = connection.execute(
            "SELECT status FROM tenants WHERE tenant_slug = ? AND is_deleted = 0",
            (normalized_slug,),
        ).fetchone()
        if tenant is None or str(tenant["status"] or "").strip().upper() != "ACTIVE":
            return None
        members = connection.execute(
            """
            SELECT member_id, name, encrypted_access_token
            FROM tenant_committee_members
            WHERE tenant_slug = ?
            """,
            (normalized_slug,),
        ).fetchall()
    for member in members:
        try:
            stored_token = fernet.decrypt(member["encrypted_access_token"]).decode(
                "utf-8"
            )
        except (InvalidToken, UnicodeDecodeError):
            logging.error(
                "Stored committee credential could not be decrypted for tenant %s.",
                normalized_slug,
            )
            continue
        if hmac.compare_digest(stored_token, normalized_token):
            return {
                "member_id": str(member["member_id"]),
                "name": str(member["name"]),
                "tenant_slug": normalized_slug,
            }
    return None


def _validate_committee_proposal(
    connection: sqlite3.Connection,
    tenant_slug: str,
    member_id: str,
    tracking_id: str,
) -> None:
    member = connection.execute(
        """
        SELECT 1 FROM tenant_committee_members
        WHERE tenant_slug = ? AND member_id = ?
        """,
        (tenant_slug, member_id),
    ).fetchone()
    if member is None:
        raise ValueError("The committee member is not provisioned for this tenant.")
    proposal = connection.execute(
        """
        SELECT 1 FROM (
            SELECT tracking_id FROM physical_proposals WHERE tenant_slug = ?
            UNION ALL
            SELECT submission_id AS tracking_id
            FROM unsolicited_proposals WHERE tenant_slug = ?
            UNION ALL
            SELECT qr_pass_id AS tracking_id FROM clearance_passes
            WHERE tenant_slug = ? AND clearance_status = 'DOSSIER_SUBMITTED'
        ) WHERE tracking_id = ?
        LIMIT 1
        """,
        (tenant_slug, tenant_slug, tenant_slug, tracking_id),
    ).fetchone()
    if proposal is None:
        raise ValueError("The proposal is not available in this tenant.")


def record_committee_coi_signoff(
    tenant_slug: str,
    member_id: str,
    tracking_id: str,
    signed_by_name: str,
) -> dict[str, Any]:
    """Persist an immutable, proposal-specific digital COI sign-off receipt."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_member = _required_text(member_id, "member_id")
    normalized_tracking = _required_text(tracking_id, "tracking_id")
    normalized_name = _required_text(signed_by_name, "signed_by_name")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        tenant = connection.execute(
            "SELECT status FROM tenants WHERE tenant_slug = ? AND is_deleted = 0",
            (normalized_slug,),
        ).fetchone()
        if tenant is None or str(tenant["status"] or "").strip().upper() != "ACTIVE":
            raise ValueError("COI sign-off requires an active tenant.")
        _validate_committee_proposal(
            connection,
            normalized_slug,
            normalized_member,
            normalized_tracking,
        )
        member = connection.execute(
            """
            SELECT name FROM tenant_committee_members
            WHERE tenant_slug = ? AND member_id = ?
            """,
            (normalized_slug, normalized_member),
        ).fetchone()
        if str(member["name"]).strip().casefold() != normalized_name.casefold():
            raise ValueError("The COI signer name does not match the committee roster.")
        existing = connection.execute(
            """
            SELECT declaration_status, signed_by_name, timestamp,
                   digital_signature_hash
            FROM tenant_committee_coi_signoffs
            WHERE tenant_slug = ? AND member_id = ? AND tracking_id = ?
            """,
            (normalized_slug, normalized_member, normalized_tracking),
        ).fetchone()
        if existing is not None:
            return dict(existing)

        declaration = (
            "I declare no direct, indirect, or pecuniary interest in the "
            "bidding organization or this proposal."
        )
        signature_payload = json.dumps(
            {
                "tenant_slug": normalized_slug,
                "member_id": normalized_member,
                "tracking_id": normalized_tracking,
                "declaration_status": "Signed",
                "signed_by_name": normalized_name,
                "timestamp": timestamp,
                "declaration": declaration,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        signature_hash = hashlib.sha256(signature_payload.encode("utf-8")).hexdigest()
        connection.execute(
            """
            INSERT INTO tenant_committee_coi_signoffs (
                tenant_slug, member_id, tracking_id, declaration_status,
                signed_by_name, timestamp, digital_signature_hash
            ) VALUES (?, ?, ?, 'Signed', ?, ?, ?)
            """,
            (
                normalized_slug,
                normalized_member,
                normalized_tracking,
                normalized_name,
                timestamp,
                signature_hash,
            ),
        )
        _insert_tenant_activity(
            connection,
            normalized_slug,
            "committee_proposal_coi_signed",
            (
                f"Committee member {normalized_member} signed the COI declaration "
                f"for proposal {normalized_tracking}."
            ),
            normalized_member,
        )
    return {
        "declaration_status": "Signed",
        "signed_by_name": normalized_name,
        "timestamp": timestamp,
        "digital_signature_hash": signature_hash,
    }


def get_committee_coi_status(
    tenant_slug: str,
    member_id: str,
    tracking_id: str,
) -> dict[str, Any] | None:
    """Return one member's tenant- and proposal-specific COI receipt."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_member = _required_text(member_id, "member_id")
    normalized_tracking = _required_text(tracking_id, "tracking_id")
    init_db()
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT declaration_status, signed_by_name, timestamp,
                   digital_signature_hash
            FROM tenant_committee_coi_signoffs
            WHERE tenant_slug = ? AND member_id = ? AND tracking_id = ?
            """,
            (normalized_slug, normalized_member, normalized_tracking),
        ).fetchone()
    return dict(row) if row is not None else None


def save_committee_proposal_evaluation(
    tenant_slug: str,
    member_id: str,
    tracking_id: str,
    scores_dict: dict[str, Any],
    notes: str,
) -> dict[str, Any]:
    """Save one committee member's evaluation after their proposal COI gate."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_member = _required_text(member_id, "member_id")
    normalized_tracking = _required_text(tracking_id, "tracking_id")
    if not isinstance(scores_dict, dict):
        raise TypeError("scores_dict must be a dictionary.")
    score_names = ("technical", "financial", "compliance")
    normalized_scores: dict[str, int] = {}
    for name in score_names:
        score = scores_dict.get(name)
        if isinstance(score, bool) or not isinstance(score, int):
            raise TypeError(f"{name} score must be an integer.")
        if not 0 <= score <= 100:
            raise ValueError(f"{name} score must be between 0 and 100.")
        normalized_scores[name] = score
    if not isinstance(notes, str):
        raise TypeError("Evaluation notes must be text.")
    normalized_notes = notes.strip()
    if len(normalized_notes) > 8_000:
        raise ValueError("Evaluation notes must not exceed 8000 characters.")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        tenant = connection.execute(
            "SELECT status FROM tenants WHERE tenant_slug = ? AND is_deleted = 0",
            (normalized_slug,),
        ).fetchone()
        if tenant is None or str(tenant["status"] or "").strip().upper() != "ACTIVE":
            raise ValueError("Evaluation requires an active tenant.")
        _validate_committee_proposal(
            connection,
            normalized_slug,
            normalized_member,
            normalized_tracking,
        )
        coi = connection.execute(
            """
            SELECT declaration_status FROM tenant_committee_coi_signoffs
            WHERE tenant_slug = ? AND member_id = ? AND tracking_id = ?
            """,
            (normalized_slug, normalized_member, normalized_tracking),
        ).fetchone()
        if coi is None or coi["declaration_status"] != "Signed":
            raise ValueError("A signed proposal-specific COI is required to evaluate.")
        connection.execute(
            """
            INSERT INTO tenant_committee_evaluations (
                tenant_slug, member_id, tracking_id, technical_score,
                financial_score, compliance_score, notes, submitted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tenant_slug, member_id, tracking_id) DO UPDATE SET
                technical_score = excluded.technical_score,
                financial_score = excluded.financial_score,
                compliance_score = excluded.compliance_score,
                notes = excluded.notes,
                submitted_at = excluded.submitted_at
            """,
            (
                normalized_slug,
                normalized_member,
                normalized_tracking,
                normalized_scores["technical"],
                normalized_scores["financial"],
                normalized_scores["compliance"],
                normalized_notes,
                timestamp,
            ),
        )
        _insert_tenant_activity(
            connection,
            normalized_slug,
            "committee_proposal_evaluation_saved",
            f"Committee member {normalized_member} submitted an evaluation for proposal {normalized_tracking}.",
            normalized_member,
        )
        row = connection.execute(
            """
            SELECT technical_score, financial_score, compliance_score,
                   submitted_at
            FROM tenant_committee_evaluations
            WHERE tenant_slug = ? AND member_id = ? AND tracking_id = ?
            """,
            (normalized_slug, normalized_member, normalized_tracking),
        ).fetchone()
    return dict(row)


def get_consolidated_committee_scores(
    tenant_slug: str,
    tracking_id: str,
) -> dict[str, Any]:
    """Return equal-weight committee averages, variance, and reviewer scores."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_tracking = _required_text(tracking_id, "tracking_id")
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT evaluation.member_id, member.name,
                   evaluation.technical_score, evaluation.financial_score,
                   evaluation.compliance_score, evaluation.submitted_at
            FROM tenant_committee_evaluations AS evaluation
            JOIN tenant_committee_members AS member
              ON member.tenant_slug = evaluation.tenant_slug
             AND member.member_id = evaluation.member_id
            JOIN tenant_committee_coi_signoffs AS coi
              ON coi.tenant_slug = evaluation.tenant_slug
             AND coi.member_id = evaluation.member_id
             AND coi.tracking_id = evaluation.tracking_id
             AND coi.declaration_status = 'Signed'
            WHERE evaluation.tenant_slug = ? AND evaluation.tracking_id = ?
            ORDER BY evaluation.submitted_at, evaluation.member_id
            """,
            (normalized_slug, normalized_tracking),
        ).fetchall()
    reviewers = [
        {
            "member_id": str(row["member_id"]),
            "name": str(row["name"]),
            "technical_score": int(row["technical_score"]),
            "financial_score": int(row["financial_score"]),
            "compliance_score": int(row["compliance_score"]),
            "combined_score": (
                int(row["technical_score"])
                + int(row["financial_score"])
                + int(row["compliance_score"])
            )
            / 3,
            "submitted_at": str(row["submitted_at"]),
        }
        for row in rows
    ]
    reviewer_count = len(reviewers)
    averages = {
        name: (
            sum(reviewer[f"{name}_score"] for reviewer in reviewers) / reviewer_count
            if reviewer_count
            else None
        )
        for name in ("technical", "financial", "compliance")
    }
    combined_scores = [reviewer["combined_score"] for reviewer in reviewers]
    weighted_average = (
        sum(combined_scores) / reviewer_count if reviewer_count else None
    )
    score_variance = (
        sum((score - weighted_average) ** 2 for score in combined_scores)
        / reviewer_count
        if reviewer_count
        else None
    )
    return {
        "tenant_slug": normalized_slug,
        "tracking_id": normalized_tracking,
        "reviewer_count": reviewer_count,
        "technical_average": averages["technical"],
        "financial_average": averages["financial"],
        "compliance_average": averages["compliance"],
        "weighted_average": weighted_average,
        "score_variance": score_variance,
        "weighting": "Equal weighting: technical 1/3, financial 1/3, compliance 1/3.",
        "reviewers": reviewers,
    }


def get_committee_proposal_evaluation(
    tenant_slug: str,
    member_id: str,
    tracking_id: str,
) -> dict[str, Any] | None:
    """Return only the requesting member's saved evaluation for one proposal."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_member = _required_text(member_id, "member_id")
    normalized_tracking = _required_text(tracking_id, "tracking_id")
    init_db()
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT technical_score, financial_score, compliance_score,
                   notes, submitted_at
            FROM tenant_committee_evaluations
            WHERE tenant_slug = ? AND member_id = ? AND tracking_id = ?
            """,
            (normalized_slug, normalized_member, normalized_tracking),
        ).fetchone()
    return dict(row) if row is not None else None


def record_unsolicited_proposal(
    tenant_slug: str,
    submission_id: str,
    organization_name: str,
    cac_registration_number: str,
    proposal_title: str,
    document_filename: str,
    document_sha256: str,
    tax_identification_number: str = "",
) -> dict[str, Any]:
    """Index encrypted unsolicited dossier metadata for the executive proposal hub."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_submission_id = _required_text(submission_id, "submission_id")
    organization = _required_text(organization_name, "organization_name")
    cac_number = _required_text(cac_registration_number, "cac_registration_number")
    tax_id = str(tax_identification_number or "").strip()
    title = _required_text(proposal_title, "proposal_title")
    filename = _required_text(document_filename, "document_filename")
    filename = filename.replace("\\", "/").rsplit("/", 1)[-1]
    normalized_hash = _required_text(document_sha256, "document_sha256").lower()
    if not re.fullmatch(r"[a-f0-9]{64}", normalized_hash):
        raise ValueError("document_sha256 must be a SHA-256 hexadecimal digest.")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        tenant = connection.execute(
            "SELECT status FROM tenants WHERE tenant_slug = ? AND is_deleted = 0",
            (normalized_slug,),
        ).fetchone()
        if tenant is None or str(tenant["status"] or "").strip().upper() != "ACTIVE":
            raise ValueError("Proposal intake requires an active tenant.")
        connection.execute(
            """
            INSERT INTO unsolicited_proposals (
                submission_id, tenant_slug, organization_name,
                cac_registration_number, tax_identification_number,
                proposal_title, document_filename, document_sha256, submitted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_submission_id,
                normalized_slug,
                organization,
                cac_number,
                tax_id,
                title,
                filename,
                normalized_hash,
                timestamp,
            ),
        )
        _insert_tenant_activity(
            connection,
            normalized_slug,
            "unsolicited_proposal_submitted",
            (
                f"Unsolicited proposal {normalized_submission_id} indexed; "
                f"document SHA-256 {normalized_hash}."
            ),
            organization,
        )
    return {
        "submission_id": normalized_submission_id,
        "tenant_slug": normalized_slug,
        "organization_name": organization,
        "cac_registration_number": cac_number,
        "tax_identification_number": tax_id,
        "proposal_title": title,
        "document_filename": filename,
        "document_sha256": normalized_hash,
        "submitted_at": timestamp,
    }


def get_tenant_governance_proposals(tenant_slug: str) -> list[dict[str, Any]]:
    """Aggregate all submitted proposal sources within one tenant."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            """
            WITH all_proposals AS (
                SELECT tracking_id, tenant_slug, organization_name,
                       proposal_title, submission_date,
                       cac_registration_number, NULL AS tax_identification_number,
                       official_email, contact_phone, routed_directorate,
                       receipt_hash, submitted_at, 'physical' AS source_type,
                       NULL AS executive_summary
                FROM physical_proposals
                WHERE tenant_slug = ?
                UNION ALL
                SELECT submission_id, tenant_slug, organization_name,
                       proposal_title, submitted_at, cac_registration_number,
                       tax_identification_number, NULL, NULL,
                       'Unsolicited Vendor Intake', document_sha256, submitted_at,
                       'unsolicited', NULL
                FROM unsolicited_proposals
                WHERE tenant_slug = ?
                UNION ALL
                SELECT qr_pass_id, tenant_slug, vendor_name, proposal_title,
                       NULL, NULL, NULL, email, NULL, 'Solicited Vendor Intake',
                       NULL, NULL, 'solicited', NULL
                FROM clearance_passes
                WHERE tenant_slug = ? AND clearance_status = 'DOSSIER_SUBMITTED'
            )
            SELECT proposal.tracking_id, proposal.tenant_slug,
                   proposal.organization_name, proposal.proposal_title,
                   proposal.submission_date, proposal.cac_registration_number,
                   proposal.tax_identification_number, proposal.official_email,
                   proposal.contact_phone, proposal.routed_directorate,
                   proposal.receipt_hash, proposal.submitted_at,
                   proposal.source_type, proposal.executive_summary,
                   COALESCE(governance.status, 'RECEIVED') AS governance_status,
                   appraisal.signoff_status AS departmental_signoff_status,
                   appraisal.directorate AS appraised_by_directorate,
                   appraisal.pushed_to_apex AS appraisal_pushed_to_apex
            FROM all_proposals AS proposal
            LEFT JOIN proposal_governance AS governance
              ON governance.tenant_slug = proposal.tenant_slug
             AND governance.tracking_id = proposal.tracking_id
            LEFT JOIN departmental_appraisals AS appraisal
              ON appraisal.tenant_slug = proposal.tenant_slug
             AND appraisal.tracking_id = proposal.tracking_id
            ORDER BY proposal.submitted_at DESC, proposal.tracking_id
            """,
            (normalized_slug, normalized_slug, normalized_slug),
        ).fetchall()
    return [dict(row) for row in rows]


def save_departmental_review_dossier(
    tenant_slug: str,
    tracking_id: str,
    source_type: str,
    organization_name: str,
    proposal_title: str,
    routed_directorate: str,
    submitted_at: str = "",
) -> dict[str, Any]:
    """Create/update a tenant-owned directorate queue record."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_tracking = _required_text(tracking_id, "tracking_id")
    normalized_source = _required_text(source_type, "source_type").lower()
    if normalized_source not in {"physical", "unsolicited", "solicited"}:
        raise ValueError("Unsupported proposal source type.")
    organization = _required_text(organization_name, "organization_name")
    title = _required_text(proposal_title, "proposal_title")
    directorate = _required_text(routed_directorate, "routed_directorate")
    submitted = str(submitted_at or "").strip()
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    proposal_exists = any(
        proposal["tracking_id"] == normalized_tracking
        for proposal in get_tenant_governance_proposals(normalized_slug)
    )
    if not proposal_exists:
        raise ValueError("The proposal is not available in this tenant.")

    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        tenant = connection.execute(
            "SELECT status FROM tenants WHERE tenant_slug = ? AND is_deleted = 0",
            (normalized_slug,),
        ).fetchone()
        if tenant is None or str(tenant["status"] or "").strip().upper() != "ACTIVE":
            raise ValueError("Departmental review requires an active tenant.")
        previous = connection.execute(
            """
            SELECT routed_directorate FROM departmental_review_dossiers
            WHERE tenant_slug = ? AND tracking_id = ?
            """,
            (normalized_slug, normalized_tracking),
        ).fetchone()
        connection.execute(
            """
            INSERT INTO departmental_review_dossiers (
                tenant_slug, tracking_id, source_type, organization_name,
                proposal_title, routed_directorate, sector, submitted_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, '', ?, ?)
            ON CONFLICT(tenant_slug, tracking_id) DO UPDATE SET
                source_type = excluded.source_type,
                organization_name = excluded.organization_name,
                proposal_title = excluded.proposal_title,
                routed_directorate = excluded.routed_directorate,
                submitted_at = excluded.submitted_at
            """,
            (
                normalized_slug,
                normalized_tracking,
                normalized_source,
                organization,
                title,
                directorate,
                submitted,
                timestamp,
            ),
        )
        if (
            previous is None
            or previous["routed_directorate"] != directorate
        ):
            _insert_tenant_activity(
                connection,
                normalized_slug,
                "departmental_proposal_routed",
                (
                    f"Proposal {normalized_tracking} routed to {directorate} "
                    f"from {normalized_source} intake."
                ),
                "departmental_routing",
            )
        row = connection.execute(
            """
            SELECT tenant_slug, tracking_id, source_type, organization_name,
                   proposal_title, routed_directorate, sector, submitted_at,
                   created_at
            FROM departmental_review_dossiers
            WHERE tenant_slug = ? AND tracking_id = ?
            """,
            (normalized_slug, normalized_tracking),
        ).fetchone()
    if row is None:
        raise RuntimeError("The departmental review dossier could not be loaded.")
    return dict(row)


def get_departmental_review_queue(
    tenant_slug: str,
    directorate: str,
) -> list[dict[str, Any]]:
    """Return queued proposals, scoped by tenant and assigned directorate."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_directorate = _required_text(directorate, "directorate")
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT dossier.tenant_slug, dossier.tracking_id,
                   dossier.source_type, dossier.organization_name,
                   dossier.proposal_title, dossier.routed_directorate,
                   dossier.sector, dossier.submitted_at, dossier.created_at,
                   appraisal.appraiser, appraisal.appraisal_notes,
                   appraisal.executive_summary, appraisal.signoff_status,
                   appraisal.pushed_to_apex, appraisal.updated_at AS appraised_at
            FROM departmental_review_dossiers AS dossier
            LEFT JOIN departmental_appraisals AS appraisal
              ON appraisal.tenant_slug = dossier.tenant_slug
             AND appraisal.tracking_id = dossier.tracking_id
            WHERE dossier.tenant_slug = ?
              AND dossier.routed_directorate = ?
            ORDER BY dossier.submitted_at DESC, dossier.tracking_id
            """,
            (normalized_slug, normalized_directorate),
        ).fetchall()
    return [dict(row) for row in rows]


def get_departmental_review_dossier(
    tenant_slug: str,
    tracking_id: str,
) -> dict[str, Any] | None:
    """Load a single dossier with its latest compliance and appraisal state."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_tracking = _required_text(tracking_id, "tracking_id")
    init_db()
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT dossier.tenant_slug, dossier.tracking_id,
                   dossier.source_type, dossier.organization_name,
                   dossier.proposal_title, dossier.routed_directorate,
                   dossier.sector, dossier.submitted_at, dossier.created_at,
                   appraisal.appraiser, appraisal.appraisal_notes,
                   appraisal.executive_summary, appraisal.signoff_status,
                   appraisal.pushed_to_apex, appraisal.updated_at AS appraised_at
            FROM departmental_review_dossiers AS dossier
            LEFT JOIN departmental_appraisals AS appraisal
              ON appraisal.tenant_slug = dossier.tenant_slug
             AND appraisal.tracking_id = dossier.tracking_id
            WHERE dossier.tenant_slug = ? AND dossier.tracking_id = ?
            """,
            (normalized_slug, normalized_tracking),
        ).fetchone()
        if row is None:
            return None
        checks = connection.execute(
            """
            SELECT check_name, verification_status, registry_source,
                   credential_reference, result_details, checked_at, checked_by
            FROM statutory_compliance_checks
            WHERE tenant_slug = ? AND tracking_id = ?
            ORDER BY check_name
            """,
            (normalized_slug, normalized_tracking),
        ).fetchall()
    result = dict(row)
    result["compliance_checks"] = [dict(check) for check in checks]
    return result


_COMPLIANCE_CHECK_NAMES = {
    "CAC",
    "TIN",
    "KYB",
    "EFCC",
    "PenCom",
    "NAFDAC",
    "COREN",
    "NSCDC",
    "NITDA",
}
_COMPLIANCE_STATUSES = {
    "PROVIDED_UNVERIFIED",
    "MISSING",
    "NOT_APPLICABLE",
    "VERIFIED",
    "FAILED",
    "MANUAL_REVIEW",
}


def save_statutory_compliance_checks(
    tenant_slug: str,
    tracking_id: str,
    directorate: str,
    sector: str,
    checks: list[dict[str, str]],
    checked_by: str,
) -> list[dict[str, Any]]:
    """Persist tenant-scoped local and registry screening results."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_tracking = _required_text(tracking_id, "tracking_id")
    normalized_directorate = _required_text(directorate, "directorate")
    normalized_sector = _required_text(sector, "sector")
    normalized_actor = _required_text(checked_by, "checked_by")
    if not isinstance(checks, list) or not checks:
        raise ValueError("At least one compliance check is required.")

    normalized_checks = []
    seen_names: set[str] = set()
    for check in checks:
        if not isinstance(check, dict):
            raise TypeError("Each compliance check must be a dictionary.")
        name = _required_text(check.get("check_name"), "check_name")
        status = _required_text(
            check.get("verification_status"),
            "verification_status",
        ).upper()
        registry_source = _required_text(
            check.get("registry_source"),
            "registry_source",
        )
        credential_reference = str(check.get("credential_reference") or "").strip()
        details = _required_text(check.get("result_details"), "result_details")
        if name not in _COMPLIANCE_CHECK_NAMES:
            raise ValueError(f"Unsupported statutory check {name!r}.")
        if name in seen_names:
            raise ValueError(f"Duplicate statutory check {name!r}.")
        if status not in _COMPLIANCE_STATUSES:
            raise ValueError(f"Unsupported compliance state {status!r}.")
        seen_names.add(name)
        normalized_checks.append(
            (name, status, registry_source, credential_reference, details)
        )
    if seen_names != _COMPLIANCE_CHECK_NAMES:
        raise ValueError("The complete universal and sector compliance matrix is required.")

    proposal_exists = any(
        proposal["tracking_id"] == normalized_tracking
        for proposal in get_tenant_governance_proposals(normalized_slug)
    )
    if not proposal_exists:
        raise ValueError("The proposal is not available in this tenant.")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        tenant = connection.execute(
            "SELECT status FROM tenants WHERE tenant_slug = ? AND is_deleted = 0",
            (normalized_slug,),
        ).fetchone()
        if tenant is None or str(tenant["status"] or "").strip().upper() != "ACTIVE":
            raise ValueError("Compliance screening requires an active tenant.")
        dossier = connection.execute(
            """
            SELECT routed_directorate FROM departmental_review_dossiers
            WHERE tenant_slug = ? AND tracking_id = ?
            """,
            (normalized_slug, normalized_tracking),
        ).fetchone()
        if dossier is None or dossier["routed_directorate"] != normalized_directorate:
            raise ValueError("The proposal is not assigned to this directorate.")
        connection.execute(
            """
            UPDATE departmental_review_dossiers
            SET sector = ?, routed_directorate = ?
            WHERE tenant_slug = ? AND tracking_id = ?
            """,
            (
                normalized_sector,
                normalized_directorate,
                normalized_slug,
                normalized_tracking,
            ),
        )
        for check in normalized_checks:
            connection.execute(
                """
                INSERT INTO statutory_compliance_checks (
                    tenant_slug, tracking_id, check_name, verification_status,
                    registry_source, credential_reference, result_details,
                    checked_at, checked_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_slug, tracking_id, check_name) DO UPDATE SET
                    verification_status = excluded.verification_status,
                    registry_source = excluded.registry_source,
                    credential_reference = excluded.credential_reference,
                    result_details = excluded.result_details,
                    checked_at = excluded.checked_at,
                    checked_by = excluded.checked_by
                """,
                (
                    normalized_slug,
                    normalized_tracking,
                    *check,
                    timestamp,
                    normalized_actor,
                ),
            )
        provided_count = sum(
            1 for _, status, *_ in normalized_checks
            if status == "PROVIDED_UNVERIFIED"
        )
        _insert_tenant_activity(
            connection,
            normalized_slug,
            "departmental_compliance_screening_completed",
            (
                f"Local screening completed for {normalized_tracking} in "
                f"{normalized_directorate} ({normalized_sector}); "
                f"{provided_count} credentials were present but remain unverified."
            ),
            normalized_actor,
        )
    dossier = get_departmental_review_dossier(
        normalized_slug,
        normalized_tracking,
    )
    if dossier is None:
        raise RuntimeError("The screened proposal dossier could not be reloaded.")
    return dossier["compliance_checks"]


def save_departmental_appraisal(
    tenant_slug: str,
    tracking_id: str,
    directorate: str,
    appraiser: str,
    appraisal_notes: str,
    executive_summary: str,
    signoff_status: str,
    push_to_apex: bool = False,
) -> dict[str, Any]:
    """Save an appraisal and optional Apex handoff for a tenant-owned dossier."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_tracking = _required_text(tracking_id, "tracking_id")
    normalized_directorate = _required_text(directorate, "directorate")
    normalized_appraiser = _required_text(appraiser, "appraiser")
    notes = str(appraisal_notes or "").strip()
    summary = str(executive_summary or "").strip()
    status = _required_text(signoff_status, "signoff_status").title()
    if status not in {"Pending", "Approved", "Queried", "Rejected"}:
        raise ValueError("Unsupported departmental appraisal status.")
    if status != "Pending" and not notes:
        raise ValueError("Appraisal notes are required for a final sign-off.")
    if not isinstance(push_to_apex, bool):
        raise TypeError("push_to_apex must be a boolean.")
    if push_to_apex and not notes:
        raise ValueError("Appraisal notes are required before Apex handoff.")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        tenant = connection.execute(
            "SELECT status FROM tenants WHERE tenant_slug = ? AND is_deleted = 0",
            (normalized_slug,),
        ).fetchone()
        if tenant is None or str(tenant["status"] or "").strip().upper() != "ACTIVE":
            raise ValueError("Departmental appraisal requires an active tenant.")
        dossier = connection.execute(
            """
            SELECT routed_directorate FROM departmental_review_dossiers
            WHERE tenant_slug = ? AND tracking_id = ?
            """,
            (normalized_slug, normalized_tracking),
        ).fetchone()
        if dossier is None:
            raise ValueError("The departmental dossier is not in this tenant queue.")
        if dossier["routed_directorate"] != normalized_directorate:
            raise ValueError("This dossier is routed to a different directorate.")
        connection.execute(
            """
            INSERT INTO departmental_appraisals (
                tenant_slug, tracking_id, directorate, appraiser,
                appraisal_notes, executive_summary, signoff_status,
                pushed_to_apex, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tenant_slug, tracking_id) DO UPDATE SET
                directorate = excluded.directorate,
                appraiser = excluded.appraiser,
                appraisal_notes = excluded.appraisal_notes,
                executive_summary = excluded.executive_summary,
                signoff_status = excluded.signoff_status,
                pushed_to_apex = CASE
                    WHEN excluded.pushed_to_apex = 1 THEN 1
                    ELSE departmental_appraisals.pushed_to_apex
                END,
                updated_at = excluded.updated_at
            """,
            (
                normalized_slug,
                normalized_tracking,
                normalized_directorate,
                normalized_appraiser,
                notes,
                summary,
                status,
                int(push_to_apex),
                timestamp,
            ),
        )
        _insert_tenant_activity(
            connection,
            normalized_slug,
            (
                "departmental_appraisal_pushed_to_apex"
                if push_to_apex
                else "departmental_appraisal_updated"
            ),
            (
                f"{normalized_tracking} appraisal set to {status} by "
                f"{normalized_directorate}"
                + (" and pushed to Apex Command." if push_to_apex else ".")
            ),
            normalized_appraiser,
        )
        row = connection.execute(
            """
            SELECT tenant_slug, tracking_id, directorate, appraiser,
                   appraisal_notes, executive_summary, signoff_status,
                   pushed_to_apex, updated_at
            FROM departmental_appraisals
            WHERE tenant_slug = ? AND tracking_id = ?
            """,
            (normalized_slug, normalized_tracking),
        ).fetchone()
    if row is None:
        raise RuntimeError("The departmental appraisal could not be reloaded.")
    return dict(row)


def list_departmental_appraisals(
    tenant_slug: str,
    directorate: str | None = None,
) -> list[dict[str, Any]]:
    """List a tenant's appraisal records, optionally limited to a directorate."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    init_db()
    with get_connection() as connection:
        if directorate is None:
            rows = connection.execute(
                """
                SELECT tenant_slug, tracking_id, directorate, appraiser,
                       appraisal_notes, executive_summary, signoff_status,
                       pushed_to_apex, updated_at
                FROM departmental_appraisals
                WHERE tenant_slug = ?
                ORDER BY updated_at DESC, tracking_id
                """,
                (normalized_slug,),
            ).fetchall()
        else:
            normalized_directorate = _required_text(directorate, "directorate")
            rows = connection.execute(
                """
                SELECT tenant_slug, tracking_id, directorate, appraiser,
                       appraisal_notes, executive_summary, signoff_status,
                       pushed_to_apex, updated_at
                FROM departmental_appraisals
                WHERE tenant_slug = ? AND directorate = ?
                ORDER BY updated_at DESC, tracking_id
                """,
                (normalized_slug, normalized_directorate),
            ).fetchall()
    return [dict(row) for row in rows]


def set_tenant_proposal_governance_status(
    tenant_slug: str,
    tracking_id: str,
    status: str,
    updated_by: str,
) -> bool:
    """Apply a tenant-owned executive recall/stop/resume decision."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_tracking_id = _required_text(tracking_id, "tracking_id")
    normalized_status = _required_text(status, "status").upper()
    normalized_actor = _required_text(updated_by, "updated_by")
    if normalized_status not in {"RECEIVED", "RECALLED", "STOPPED", "RESUMED"}:
        raise ValueError("Unsupported proposal governance status.")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        proposal = connection.execute(
            """
            SELECT 1 FROM physical_proposals
            WHERE tenant_slug = ? AND tracking_id = ?
            UNION ALL
            SELECT 1 FROM unsolicited_proposals
            WHERE tenant_slug = ? AND submission_id = ?
            UNION ALL
            SELECT 1 FROM clearance_passes
            WHERE tenant_slug = ? AND qr_pass_id = ?
              AND clearance_status = 'DOSSIER_SUBMITTED'
            """,
            (
                normalized_slug,
                normalized_tracking_id,
                normalized_slug,
                normalized_tracking_id,
                normalized_slug,
                normalized_tracking_id,
            ),
        ).fetchone()
        if proposal is None:
            return False
        connection.execute(
            """
            INSERT INTO proposal_governance (
                tenant_slug, tracking_id, status, updated_at, updated_by
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(tenant_slug, tracking_id) DO UPDATE SET
                status = excluded.status,
                updated_at = excluded.updated_at,
                updated_by = excluded.updated_by
            """,
            (
                normalized_slug,
                normalized_tracking_id,
                normalized_status,
                timestamp,
                normalized_actor,
            ),
        )
        _insert_tenant_activity(
            connection,
            normalized_slug,
            "proposal_governance_override",
            f"Proposal {normalized_tracking_id} status changed to {normalized_status}.",
            normalized_actor,
        )
    return True


def get_proposal_notification_outbox(
    tenant_slug: str,
    tracking_id: str,
) -> list[dict[str, Any]]:
    """Return queued acknowledgments only for a tenant-owned tracking ID."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_tracking_id = _required_text(tracking_id, "tracking_id")
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, tenant_slug, tracking_id, channel, recipient, message,
                   status, created_at
            FROM notification_outbox
            WHERE tenant_slug = ? AND tracking_id = ?
            ORDER BY id
            """,
            (normalized_slug, normalized_tracking_id),
        ).fetchall()
    return [dict(row) for row in rows]


def get_all_tenant_activities(
    tenant_slug: str | None = None,
) -> list[dict[str, Any]]:
    """Return tenant activities newest-first, optionally scoped to one tenant."""
    init_db()
    with get_connection() as connection:
        if tenant_slug is None:
            rows = connection.execute(
                "SELECT id, tenant_slug, activity_type, description, performed_by, "
                "date, time, month, year, created_at FROM tenant_activity_logs "
                "ORDER BY date DESC, time DESC, id DESC"
            ).fetchall()
        else:
            normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
            rows = connection.execute(
                "SELECT id, tenant_slug, activity_type, description, performed_by, "
                "date, time, month, year, created_at FROM tenant_activity_logs "
                "WHERE tenant_slug = ? ORDER BY date DESC, time DESC, id DESC",
                (normalized_slug,),
            ).fetchall()
    return [dict(row) for row in rows]


def _vendor_slug(tenant_slug: str, vendor_name: str, vendor_type: str, email: str | None) -> str:
    identity = (email or vendor_name).strip().casefold()
    digest = hashlib.sha256(
        f"{tenant_slug}\0{vendor_type}\0{identity}".encode("utf-8")
    ).hexdigest()[:10]
    name_part = re.sub(r"[^a-z0-9]+", "-", vendor_name.casefold()).strip("-")
    name_part = name_part[:32].strip("-") or "vendor"
    return f"{tenant_slug}-{name_part}-{digest}"


def _register_vendor(
    connection: sqlite3.Connection,
    tenant_slug: str,
    vendor_name: str,
    vendor_type: str,
    email: str | None = None,
) -> str:
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_name = _required_text(vendor_name, "vendor_name")
    normalized_type = _required_text(vendor_type, "vendor_type").lower()
    if normalized_type not in {"solicited", "unsolicited"}:
        raise ValueError("vendor_type must be solicited or unsolicited.")
    normalized_email = email.strip().lower() if isinstance(email, str) and email.strip() else None
    slug = _vendor_slug(
        normalized_slug,
        normalized_name,
        normalized_type,
        normalized_email,
    )
    connection.execute(
        """
        INSERT INTO vendors (
            vendor_slug, tenant_slug, vendor_name, vendor_type, email, status
        ) VALUES (?, ?, ?, ?, ?, 'Pending')
        ON CONFLICT(vendor_slug) DO NOTHING
        """,
        (
            slug,
            normalized_slug,
            normalized_name,
            normalized_type,
            normalized_email,
        ),
    )
    return slug


def _backfill_solicited_vendors(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        "SELECT tenant_slug, vendor_name, email FROM clearance_passes "
        "ORDER BY qr_pass_id"
    ).fetchall()
    for row in rows:
        if not row["tenant_slug"] or not row["vendor_name"]:
            logging.warning(
                "Skipping incomplete legacy clearance pass %s during vendor "
                "registry migration.",
                row["qr_pass_id"],
            )
            continue
        _register_vendor(
            connection,
            row["tenant_slug"],
            row["vendor_name"],
            "solicited",
            row["email"],
        )


def register_vendor(
    tenant_slug: str,
    vendor_name: str,
    vendor_type: str,
    email: str | None = None,
) -> str:
    """Create a pending vendor subscription record and return its stable slug."""
    init_db()
    with get_connection() as connection:
        return register_vendor_in_connection(
            connection, tenant_slug, vendor_name, vendor_type, email
        )


def register_vendor_in_connection(
    connection: sqlite3.Connection,
    tenant_slug: str,
    vendor_name: str,
    vendor_type: str,
    email: str | None = None,
) -> str:
    """Register a vendor using an existing tenant database transaction."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    tenant = connection.execute(
        "SELECT 1 FROM tenants WHERE tenant_slug = ?", (normalized_slug,)
    ).fetchone()
    if tenant is None:
        raise ValueError("Cannot register a vendor for an unknown tenant.")
    return _register_vendor(
        connection, normalized_slug, vendor_name, vendor_type, email
    )


def list_vendors(tenant_slug: str | None = None) -> list[dict[str, Any]]:
    """Return registered vendor subscription records, optionally tenant-scoped."""
    init_db()
    with get_connection() as connection:
        if tenant_slug is None:
            rows = connection.execute(
                "SELECT vendor_slug, tenant_slug, vendor_name, vendor_type, "
                "email, status, created_at FROM vendors "
                "ORDER BY vendor_type, tenant_slug, vendor_name"
            ).fetchall()
        else:
            normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
            rows = connection.execute(
                "SELECT vendor_slug, tenant_slug, vendor_name, vendor_type, "
                "email, status, created_at FROM vendors WHERE tenant_slug = ? "
                "ORDER BY vendor_type, vendor_name",
                (normalized_slug,),
            ).fetchall()
    return [dict(row) for row in rows]


def activate_vendor(vendor_slug: str) -> bool:
    """Activate a vendor subscription without changing payment clearance status."""
    normalized_slug = _required_text(vendor_slug, "vendor_slug")
    init_db()
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE vendors SET status = 'Active' WHERE vendor_slug = ?",
            (normalized_slug,),
        )
    return cursor.rowcount == 1


def update_tenant_status(tenant_slug: str, status: str) -> bool:
    """Compatibility wrapper for audited tenant activation and suspension."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_status = _required_text(status, "status").strip().upper()
    if normalized_status == "ACTIVE":
        return activate_tenant(normalized_slug) is not None
    if normalized_status in {"INACTIVE", "SUSPENDED"}:
        return deactivate_tenant(normalized_slug)
    raise ValueError("Tenant status changes must use activate or deactivate.")


def archive_tenant(tenant_slug: str) -> bool:
    """Move a tenant into the recycle bin while retaining associated records."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT tenant_slug, full_corporation_name, institution_category, "
            "apex_title, sub_directorates_json, logo_path, status "
            "FROM tenants WHERE tenant_slug = ?",
            (normalized_slug,),
        ).fetchone()
        if row is None:
            return False
        connection.execute(
            """
            INSERT INTO tenant_archive (tenant_slug, tenant_data_json)
            VALUES (?, ?)
            ON CONFLICT(tenant_slug) DO UPDATE SET
                tenant_data_json = excluded.tenant_data_json,
                archived_at = CURRENT_TIMESTAMP
            """,
            (normalized_slug, json.dumps(dict(row), ensure_ascii=False)),
        )
        _insert_tenant_activity(
            connection,
            normalized_slug,
            "Tenant archived",
            "Tenant moved to the recycle bin.",
        )
        connection.execute(
            "DELETE FROM tenants WHERE tenant_slug = ?", (normalized_slug,)
        )
    return True


def list_archived_tenants() -> list[dict[str, Any]]:
    """Return archived tenant snapshots ordered by archive time."""
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT tenant_slug, tenant_data_json, archived_at "
            "FROM tenant_archive ORDER BY archived_at DESC, tenant_slug"
        ).fetchall()
    archived = []
    for row in rows:
        tenant_data = json.loads(row["tenant_data_json"])
        if not isinstance(tenant_data, dict):
            raise RuntimeError(
                f"Archived tenant {row['tenant_slug']!r} contains invalid data."
            )
        archived.append(
            {
                "tenant_slug": row["tenant_slug"],
                "tenant_data": tenant_data,
                "archived_at": row["archived_at"],
            }
        )
    return archived


def restore_archived_tenant(tenant_slug: str) -> bool:
    """Restore a tenant snapshot; fail if its slug has since been reused."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT tenant_data_json FROM tenant_archive WHERE tenant_slug = ?",
            (normalized_slug,),
        ).fetchone()
        if row is None:
            return False
        tenant_data = json.loads(row["tenant_data_json"])
        if not isinstance(tenant_data, dict):
            raise RuntimeError(
                f"Archived tenant {normalized_slug!r} contains invalid data."
            )
        existing = connection.execute(
            "SELECT 1 FROM tenants WHERE tenant_slug = ?", (normalized_slug,)
        ).fetchone()
        if existing is not None:
            raise ValueError(
                f"Cannot restore {normalized_slug!r}: that tenant slug is already in use."
            )
        connection.execute(
            """
            INSERT INTO tenants (
                tenant_slug, full_corporation_name, institution_category,
                apex_title, sub_directorates_json, logo_path, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_slug,
                tenant_data.get("full_corporation_name"),
                tenant_data.get("institution_category"),
                tenant_data.get("apex_title"),
                tenant_data.get("sub_directorates_json"),
                tenant_data.get("logo_path"),
                tenant_data.get("status"),
            ),
        )
        _insert_tenant_activity(
            connection,
            normalized_slug,
            "Tenant restored",
            "Tenant restored from the recycle bin.",
        )
        connection.execute(
            "DELETE FROM tenant_archive WHERE tenant_slug = ?", (normalized_slug,)
        )
    return True


def purge_archived_tenant(tenant_slug: str) -> bool:
    """Permanently purge an archived tenant and its associated records."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        archived = connection.execute(
            "SELECT 1 FROM tenant_archive WHERE tenant_slug = ?",
            (normalized_slug,),
        ).fetchone()
        if archived is None:
            return False
        _insert_tenant_activity(
            connection,
            normalized_slug,
            "Tenant permanently purged",
            "Archived tenant permanently purged from the tenant registry.",
        )
        connection.execute(
            "DELETE FROM clearance_passes WHERE tenant_slug = ?", (normalized_slug,)
        )
        connection.execute(
            "DELETE FROM tenant_payment_verifications WHERE tenant_slug = ?",
            (normalized_slug,),
        )
        connection.execute(
            "DELETE FROM admin_access_logs WHERE tenant_slug = ?", (normalized_slug,)
        )
        connection.execute(
            "DELETE FROM tenant_audit_logs WHERE tenant_slug = ?", (normalized_slug,)
        )
        connection.execute(
            "DELETE FROM physical_proposals WHERE tenant_slug = ?", (normalized_slug,)
        )
        connection.execute(
            "DELETE FROM unsolicited_proposals WHERE tenant_slug = ?",
            (normalized_slug,),
        )
        connection.execute(
            "DELETE FROM notification_outbox WHERE tenant_slug = ?", (normalized_slug,)
        )
        connection.execute(
            "DELETE FROM tenant_gateway_configs WHERE tenant_slug = ?",
            (normalized_slug,),
        )
        connection.execute(
            "DELETE FROM tenant_tenders WHERE tenant_slug = ?", (normalized_slug,)
        )
        connection.execute(
            "DELETE FROM tenant_committee_members WHERE tenant_slug = ?",
            (normalized_slug,),
        )
        connection.execute(
            "DELETE FROM tenant_committee_coi_signoffs WHERE tenant_slug = ?",
            (normalized_slug,),
        )
        connection.execute(
            "DELETE FROM tenant_committee_evaluations WHERE tenant_slug = ?",
            (normalized_slug,),
        )
        connection.execute(
            "DELETE FROM tenant_onboarding_contacts WHERE tenant_slug = ?",
            (normalized_slug,),
        )
        connection.execute(
            "DELETE FROM proposal_governance WHERE tenant_slug = ?",
            (normalized_slug,),
        )
        connection.execute(
            "DELETE FROM departmental_review_dossiers WHERE tenant_slug = ?",
            (normalized_slug,),
        )
        connection.execute(
            "DELETE FROM statutory_compliance_checks WHERE tenant_slug = ?",
            (normalized_slug,),
        )
        connection.execute(
            "DELETE FROM departmental_appraisals WHERE tenant_slug = ?",
            (normalized_slug,),
        )
        connection.execute(
            "DELETE FROM vendors WHERE tenant_slug = ?", (normalized_slug,)
        )
        connection.execute(
            "DELETE FROM tenant_archive WHERE tenant_slug = ?", (normalized_slug,)
        )
        _purge_tenant_records(connection, normalized_slug)
        _insert_tenant_activity(
            connection,
            normalized_slug,
            "Tenant permanently purged",
            "Archived tenant data permanently purged after administrative confirmation.",
            "developer",
        )
    return True


def _purge_tenant_records(
    connection: sqlite3.Connection,
    tenant_slug: str,
) -> None:
    """Delete rows keyed to one tenant from every application table."""
    tables = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    for row in tables:
        table_name = str(row["name"])
        escaped_table_name = table_name.replace('"', '""')
        columns = connection.execute(
            f'PRAGMA table_info("{escaped_table_name}")'
        ).fetchall()
        if any(column["name"] == "tenant_slug" for column in columns):
            connection.execute(
                f'DELETE FROM "{escaped_table_name}" WHERE tenant_slug = ?',
                (tenant_slug,),
            )


def purge_tenant_permanently(tenant_slug: str) -> bool:
    """Purge tenant data only after it has entered the recycle bin."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        tenant = connection.execute(
            "SELECT 1 FROM tenants WHERE tenant_slug = ? AND is_deleted = 1",
            (normalized_slug,),
        ).fetchone()
        if tenant is None:
            return False
        _purge_tenant_records(connection, normalized_slug)
        _insert_tenant_activity(
            connection,
            normalized_slug,
            "tenant_permanently_purged",
            "Soft-deleted tenant and tenant-scoped records permanently purged "
            "after administrative confirmation.",
            "developer",
        )
    return True


def set_general_broadcast(message: str) -> None:
    """Persist the current general broadcast shown to all tenant administrators."""
    if not isinstance(message, str):
        raise TypeError("message must be text.")
    if len(message) > 2_000:
        raise ValueError("Broadcast messages must be 2,000 characters or fewer.")
    init_db()
    with get_connection() as connection:
        if message.strip():
            connection.execute(
                """
                INSERT INTO system_broadcast (id, message)
                VALUES (1, ?)
                ON CONFLICT(id) DO UPDATE SET
                    message = excluded.message,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (message.strip(),),
            )
        else:
            connection.execute("DELETE FROM system_broadcast WHERE id = 1")


def get_general_broadcast() -> dict[str, str] | None:
    """Return the current persisted broadcast, if one is published."""
    init_db()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT message, updated_at FROM system_broadcast WHERE id = 1"
        ).fetchone()
    return dict(row) if row is not None else None


def get_tenant_by_slug(tenant_slug: str) -> dict[str, Any] | None:
    """Return a non-deleted tenant record, or None when it is unavailable."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    init_db()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT tenant_slug, full_corporation_name, institution_category, "
            "apex_title, sub_directorates_json, logo_path, status, is_deleted, "
            "deleted_at, activated_at, activated_by, deactivated_at, deactivated_by "
            "FROM tenants WHERE tenant_slug = ? AND is_deleted = 0",
            (normalized_slug,),
        ).fetchone()
    return dict(row) if row is not None else None


def list_tenants() -> list[dict[str, Any]]:
    """Return non-deleted tenants and their onboarding contacts."""
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT tenants.tenant_slug, tenants.full_corporation_name,
                   tenants.institution_category, tenants.apex_title,
                   tenants.sub_directorates_json, tenants.logo_path, tenants.status,
                   tenants.activated_at, tenants.activated_by,
                   tenants.deactivated_at, tenants.deactivated_by,
                   tenant_onboarding_contacts.admin_email,
                   tenant_onboarding_contacts.admin_phone
            FROM tenants
            LEFT JOIN tenant_onboarding_contacts
              ON tenant_onboarding_contacts.tenant_slug = tenants.tenant_slug
            WHERE tenants.is_deleted = 0
            ORDER BY tenants.tenant_slug
            """
        ).fetchall()
    return [dict(row) for row in rows]


def save_tenant(tenant_data: dict[str, Any]) -> dict[str, Any]:
    """Insert or update a tenant and return the persisted record."""
    if not isinstance(tenant_data, dict):
        raise TypeError("tenant_data must be a dictionary.")

    tenant_slug = _required_text(tenant_data.get("tenant_slug"), "tenant_slug").lower()
    sub_directorates = tenant_data.get("sub_directorates_json", "[]")
    if not isinstance(sub_directorates, str):
        sub_directorates = json.dumps(sub_directorates)

    values = (
        tenant_slug,
        tenant_data.get("full_corporation_name"),
        tenant_data.get("institution_category"),
        tenant_data.get("apex_title"),
        sub_directorates,
        tenant_data.get("logo_path", ""),
        tenant_data.get("status", "Active"),
    )
    init_db()
    with get_connection() as connection:
        existing = connection.execute(
            "SELECT is_deleted, status FROM tenants WHERE tenant_slug = ?",
            (tenant_slug,),
        ).fetchone()
        if existing is not None and existing["is_deleted"]:
            raise ValueError(
                f"Cannot update {tenant_slug!r}: restore it from the recycle bin first."
            )
        connection.execute(
            """
            INSERT INTO tenants (
                tenant_slug, full_corporation_name, institution_category,
                apex_title, sub_directorates_json, logo_path, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tenant_slug) DO UPDATE SET
                full_corporation_name = excluded.full_corporation_name,
                institution_category = excluded.institution_category,
                apex_title = excluded.apex_title,
                sub_directorates_json = excluded.sub_directorates_json,
                logo_path = excluded.logo_path,
                status = excluded.status
            """,
            values,
        )
        requested_status = str(values[-1] or "").strip().upper()
        previous_status = (
            str(existing["status"] or "").strip().upper()
            if existing is not None
            else ""
        )
        if requested_status == "ACTIVE" and previous_status != "ACTIVE":
            activated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            connection.execute(
                """
                UPDATE tenants SET activated_at = ?, activated_by = 'developer'
                WHERE tenant_slug = ?
                """,
                (activated_at, tenant_slug),
            )
        elif requested_status == "INACTIVE" and previous_status != "INACTIVE":
            deactivated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            connection.execute(
                """
                UPDATE tenants SET deactivated_at = ?, deactivated_by = 'developer'
                WHERE tenant_slug = ?
                """,
                (deactivated_at, tenant_slug),
            )
        row = connection.execute(
            "SELECT tenant_slug, full_corporation_name, institution_category, "
            "apex_title, sub_directorates_json, logo_path, status "
            "FROM tenants WHERE tenant_slug = ?",
            (tenant_slug,),
        ).fetchone()
        _insert_tenant_activity(
            connection,
            tenant_slug,
            "Tenant created" if existing is None else "Tenant details updated",
            (
                "Tenant added to the registry."
                if existing is None
                else "Tenant registry details updated."
            ),
        )
        if existing is not None and requested_status != previous_status:
            _insert_tenant_activity(
                connection,
                tenant_slug,
                (
                    "tenant_activated"
                    if requested_status == "ACTIVE"
                    else "tenant_deactivated"
                    if requested_status == "INACTIVE"
                    else "tenant_status_updated"
                ),
                f"Tenant status changed from {previous_status or 'unset'} to "
                f"{requested_status or 'unset'} through a developer registry update.",
                "developer",
            )
    return dict(row)


def create_tenant_onboarding(onboarding_data: dict[str, Any]) -> dict[str, Any]:
    """Create a pending tenant and store private activation contact details."""
    if not isinstance(onboarding_data, dict):
        raise TypeError("onboarding_data must be a dictionary.")

    tenant_slug = _required_text(onboarding_data.get("tenant_slug"), "tenant_slug").lower()
    organization_name = _required_text(
        onboarding_data.get("full_corporation_name"),
        "full_corporation_name",
    )
    admin_email = _required_text(onboarding_data.get("admin_email"), "admin_email")
    admin_phone = _required_text(onboarding_data.get("admin_phone"), "admin_phone")
    sub_directorates = onboarding_data.get("sub_directorates_json", "[]")
    if not isinstance(sub_directorates, str):
        sub_directorates = json.dumps(sub_directorates)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            INSERT INTO tenants (
                tenant_slug, full_corporation_name, institution_category,
                apex_title, sub_directorates_json, logo_path, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'Pending Activation')
            """,
            (
                tenant_slug,
                organization_name,
                onboarding_data.get("institution_category"),
                onboarding_data.get("apex_title"),
                sub_directorates,
                onboarding_data.get("logo_path", ""),
            ),
        )
        connection.execute(
            """
            INSERT INTO tenant_onboarding_contacts (
                tenant_slug, admin_email, admin_phone, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            (tenant_slug, admin_email, admin_phone, created_at),
        )
        _insert_tenant_activity(
            connection,
            tenant_slug,
            "tenant_onboarded_pending_activation",
            "Institutional node submitted and is awaiting developer activation.",
        )
        row = connection.execute(
            """
            SELECT tenant_slug, full_corporation_name, institution_category,
                   apex_title, sub_directorates_json, logo_path, status
            FROM tenants WHERE tenant_slug = ?
            """,
            (tenant_slug,),
        ).fetchone()
    return dict(row)


def activate_tenant(tenant_slug: str) -> dict[str, Any] | None:
    """Activate one pending or inactive tenant and return its private contact."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
            SELECT tenant_slug, full_corporation_name, status
            FROM tenants WHERE tenant_slug = ? AND is_deleted = 0
            """,
            (normalized_slug,),
        ).fetchone()
        if row is None:
            return None
        current_status = str(row["status"] or "").strip().upper()
        if current_status not in {
            "PENDING",
            "PENDING ACTIVATION",
            "INACTIVE",
            "SUSPENDED",
        }:
            return None
        cursor = connection.execute(
            """
            UPDATE tenants
            SET status = 'Active', activated_at = ?, activated_by = 'developer'
            WHERE tenant_slug = ? AND is_deleted = 0 AND status = ?
            """,
            (timestamp, normalized_slug, row["status"]),
        )
        if cursor.rowcount != 1:
            return None
        contact = connection.execute(
            """
            SELECT admin_email, admin_phone
            FROM tenant_onboarding_contacts
            WHERE tenant_slug = ?
            """,
            (normalized_slug,),
        ).fetchone()
        _insert_tenant_activity(
            connection,
            normalized_slug,
            "tenant_activated",
            "Institutional node activated by the developer console.",
            "developer",
        )
    return {
        "tenant_slug": normalized_slug,
        "full_corporation_name": str(row["full_corporation_name"] or normalized_slug),
        "status": "Active",
        "admin_email": str(contact["admin_email"]) if contact else "",
        "admin_phone": str(contact["admin_phone"]) if contact else "",
    }


def deactivate_tenant(tenant_slug: str) -> bool:
    """Immediately suspend a registered tenant without deleting its records."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            """
            UPDATE tenants
            SET status = 'Inactive', deactivated_at = ?, deactivated_by = 'developer'
            WHERE tenant_slug = ? AND is_deleted = 0
              AND UPPER(TRIM(COALESCE(status, ''))) = 'ACTIVE'
            """,
            (timestamp, normalized_slug),
        )
        if cursor.rowcount != 1:
            return False
        _insert_tenant_activity(
            connection,
            normalized_slug,
            "tenant_deactivated",
            "Tenant access revoked by the developer console.",
            "developer",
        )
    return True


def soft_delete_tenant(tenant_slug: str) -> bool:
    """Move a tenant into the recycle bin without deleting its records."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    deleted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            """
            UPDATE tenants SET is_deleted = 1, deleted_at = ?
            WHERE tenant_slug = ? AND is_deleted = 0
            """,
            (deleted_at, normalized_slug),
        )
        if cursor.rowcount != 1:
            return False
        _insert_tenant_activity(
            connection,
            normalized_slug,
            "tenant_soft_deleted",
            "Tenant moved to the recycle bin by the developer console.",
            "developer",
        )
    return True


def restore_tenant(tenant_slug: str) -> bool:
    """Restore a tenant while preserving its prior active or inactive status."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            """
            UPDATE tenants SET is_deleted = 0, deleted_at = NULL
            WHERE tenant_slug = ? AND is_deleted = 1
            """,
            (normalized_slug,),
        )
        if cursor.rowcount != 1:
            return False
        _insert_tenant_activity(
            connection,
            normalized_slug,
            "tenant_restored",
            "Tenant restored from the recycle bin with its prior status.",
            "developer",
        )
    return True


def list_recycle_bin_tenants() -> list[dict[str, Any]]:
    """Return soft-deleted tenants and their onboarding contact details."""
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT tenants.tenant_slug, tenants.full_corporation_name,
                   tenants.institution_category, tenants.apex_title,
                   tenants.status, tenants.deleted_at,
                   tenant_onboarding_contacts.admin_email,
                   tenant_onboarding_contacts.admin_phone
            FROM tenants
            LEFT JOIN tenant_onboarding_contacts
              ON tenant_onboarding_contacts.tenant_slug = tenants.tenant_slug
            WHERE tenants.is_deleted = 1
            ORDER BY tenants.deleted_at DESC, tenants.tenant_slug
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_tenant_activation_contact(tenant_slug: str) -> dict[str, str] | None:
    """Return activation contact details for an authorized developer operation."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    init_db()
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT admin_email, admin_phone
            FROM tenant_onboarding_contacts
            WHERE tenant_slug = ?
            """,
            (normalized_slug,),
        ).fetchone()
    return dict(row) if row is not None else None


def delete_tenant(tenant_slug: str) -> bool:
    """Compatibility alias that moves a tenant to the recycle bin."""
    return soft_delete_tenant(tenant_slug)


def log_admin_access(tenant_slug: str, action: str, actor: str) -> int:
    """Write an administrative access event and return its row ID."""
    values = (
        _required_text(tenant_slug, "tenant_slug").lower(),
        _required_text(action, "action"),
        _required_text(actor, "actor"),
    )
    init_db()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO admin_access_logs (tenant_slug, action, actor) "
            "VALUES (?, ?, ?)",
            values,
        )
        return int(cursor.lastrowid)


def log_tenant_access_attempt(
    tenant_slug: str,
    access_tier: str,
    succeeded: bool,
) -> int:
    """Record a tenant staff or executive access-key attempt without its secret."""
    normalized_tier = _required_text(access_tier, "access_tier").lower()
    if normalized_tier not in {"staff", "executive"}:
        raise ValueError("access_tier must be 'staff' or 'executive'.")
    if not isinstance(succeeded, bool):
        raise TypeError("succeeded must be a boolean.")

    outcome = "accepted" if succeeded else "rejected"
    return log_admin_access(
        tenant_slug,
        f"{normalized_tier}_access_key_{outcome}",
        "tenant_access_key",
    )


_TERMINAL_LOGIN_ROLES = frozenset({"front_desk", "admin"})
_TERMINAL_LOGIN_LOCKOUT_THRESHOLD = 3


def _normalize_terminal_login_identity(
    tenant_slug: str,
    role: str,
) -> tuple[str, str]:
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_role = _required_text(role, "role").lower()
    if normalized_role not in _TERMINAL_LOGIN_ROLES:
        raise ValueError("role must be 'front_desk' or 'admin'.")
    return normalized_slug, normalized_role


def _require_existing_tenant(
    connection: sqlite3.Connection,
    tenant_slug: str,
) -> None:
    if connection.execute(
        "SELECT 1 FROM tenants WHERE tenant_slug = ? AND is_deleted = 0",
        (tenant_slug,),
    ).fetchone() is None:
        raise ValueError("The tenant is unavailable.")


def get_tenant_role_lockout(
    tenant_slug: str,
    role: str,
) -> dict[str, Any]:
    """Return persistent authentication lockout state for one tenant role."""
    normalized_slug, normalized_role = _normalize_terminal_login_identity(
        tenant_slug,
        role,
    )
    init_db()
    with get_connection() as connection:
        _require_existing_tenant(connection, normalized_slug)
        row = connection.execute(
            """
            SELECT failed_attempts, is_locked_out, locked_out_at, updated_at
            FROM tenant_auth_lockouts
            WHERE tenant_slug = ? AND role = ?
            """,
            (normalized_slug, normalized_role),
        ).fetchone()
    if row is None:
        return {
            "tenant_slug": normalized_slug,
            "role": normalized_role,
            "failed_attempts": 0,
            "is_locked_out": False,
            "locked_out_at": None,
            "updated_at": None,
        }
    return {
        "tenant_slug": normalized_slug,
        "role": normalized_role,
        "failed_attempts": int(row["failed_attempts"]),
        "is_locked_out": bool(row["is_locked_out"]),
        "locked_out_at": row["locked_out_at"],
        "updated_at": row["updated_at"],
    }


def record_tenant_role_login_failure(
    tenant_slug: str,
    role: str,
) -> dict[str, Any]:
    """Atomically count a failed login and lock its role on the third failure."""
    normalized_slug, normalized_role = _normalize_terminal_login_identity(
        tenant_slug,
        role,
    )
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _require_existing_tenant(connection, normalized_slug)
        connection.execute(
            """
            INSERT OR IGNORE INTO tenant_auth_lockouts (
                tenant_slug, role, failed_attempts, is_locked_out, updated_at
            ) VALUES (?, ?, 0, 0, ?)
            """,
            (normalized_slug, normalized_role, timestamp),
        )
        connection.execute(
            """
            UPDATE tenant_auth_lockouts
            SET failed_attempts = failed_attempts + 1,
                is_locked_out = CASE
                    WHEN failed_attempts + 1 >= ? THEN 1
                    ELSE 0
                END,
                locked_out_at = CASE
                    WHEN failed_attempts + 1 >= ?
                    THEN COALESCE(locked_out_at, ?)
                    ELSE locked_out_at
                END,
                updated_at = ?
            WHERE tenant_slug = ? AND role = ? AND is_locked_out = 0
            """,
            (
                _TERMINAL_LOGIN_LOCKOUT_THRESHOLD,
                _TERMINAL_LOGIN_LOCKOUT_THRESHOLD,
                timestamp,
                timestamp,
                normalized_slug,
                normalized_role,
            ),
        )
        row = connection.execute(
            """
            SELECT failed_attempts, is_locked_out, locked_out_at, updated_at
            FROM tenant_auth_lockouts
            WHERE tenant_slug = ? AND role = ?
            """,
            (normalized_slug, normalized_role),
        ).fetchone()
        connection.execute(
            "INSERT INTO admin_access_logs (tenant_slug, action, actor) "
            "VALUES (?, ?, ?)",
            (
                normalized_slug,
                f"{normalized_role}_login_rejected",
                f"{normalized_role}_authentication",
            ),
        )
    return {
        "tenant_slug": normalized_slug,
        "role": normalized_role,
        "failed_attempts": int(row["failed_attempts"]),
        "is_locked_out": bool(row["is_locked_out"]),
        "locked_out_at": row["locked_out_at"],
        "updated_at": row["updated_at"],
    }


def record_tenant_role_login_success(
    tenant_slug: str,
    role: str,
) -> bool:
    """Clear consecutive failures after successful login unless already locked."""
    normalized_slug, normalized_role = _normalize_terminal_login_identity(
        tenant_slug,
        role,
    )
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _require_existing_tenant(connection, normalized_slug)
        connection.execute(
            """
            INSERT OR IGNORE INTO tenant_auth_lockouts (
                tenant_slug, role, failed_attempts, is_locked_out, updated_at
            ) VALUES (?, ?, 0, 0, ?)
            """,
            (normalized_slug, normalized_role, timestamp),
        )
        connection.execute(
            """
            UPDATE tenant_auth_lockouts
            SET failed_attempts = 0, locked_out_at = NULL, updated_at = ?
            WHERE tenant_slug = ? AND role = ? AND is_locked_out = 0
            """,
            (timestamp, normalized_slug, normalized_role),
        )
        row = connection.execute(
            """
            SELECT is_locked_out FROM tenant_auth_lockouts
            WHERE tenant_slug = ? AND role = ?
            """,
            (normalized_slug, normalized_role),
        ).fetchone()
        if not bool(row["is_locked_out"]):
            connection.execute(
                "INSERT INTO admin_access_logs (tenant_slug, action, actor) "
                "VALUES (?, ?, ?)",
                (
                    normalized_slug,
                    f"{normalized_role}_login_accepted",
                    f"{normalized_role}_authentication",
                ),
            )
    return not bool(row["is_locked_out"])


def reset_tenant_role_login_lockout(
    tenant_slug: str,
    role: str,
    reset_by: str,
) -> None:
    """Clear one role lockout and audit the verified administrative reset."""
    normalized_slug, normalized_role = _normalize_terminal_login_identity(
        tenant_slug,
        role,
    )
    normalized_actor = _required_text(reset_by, "reset_by")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        _require_existing_tenant(connection, normalized_slug)
        connection.execute(
            """
            INSERT INTO tenant_auth_lockouts (
                tenant_slug, role, failed_attempts, is_locked_out,
                locked_out_at, updated_at
            ) VALUES (?, ?, 0, 0, NULL, ?)
            ON CONFLICT(tenant_slug, role) DO UPDATE SET
                failed_attempts = 0,
                is_locked_out = 0,
                locked_out_at = NULL,
                updated_at = excluded.updated_at
            """,
            (normalized_slug, normalized_role, timestamp),
        )
        _insert_tenant_activity(
            connection,
            normalized_slug,
            "terminal_auth_lockout_reset",
            f"The {normalized_role} terminal lockout was reset.",
            normalized_actor,
        )
        connection.execute(
            "INSERT INTO admin_access_logs (tenant_slug, action, actor) "
            "VALUES (?, ?, ?)",
            (
                normalized_slug,
                f"{normalized_role}_lockout_reset",
                normalized_actor,
            ),
        )


def list_admin_access_logs(
    tenant_slug: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return recent access events, optionally limited to one tenant."""
    if limit < 1:
        raise ValueError("limit must be greater than zero.")
    init_db()
    with get_connection() as connection:
        if tenant_slug is None:
            rows = connection.execute(
                "SELECT id, tenant_slug, action, actor, timestamp "
                "FROM admin_access_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
            rows = connection.execute(
                "SELECT id, tenant_slug, action, actor, timestamp "
                "FROM admin_access_logs WHERE tenant_slug = ? "
                "ORDER BY id DESC LIMIT ?",
                (normalized_slug, limit),
            ).fetchall()
    return [dict(row) for row in rows]


def create_clearance_pass(pass_data: dict[str, Any]) -> dict[str, Any]:
    """Persist a clearance pass record; this function does not verify payment."""
    if not isinstance(pass_data, dict):
        raise TypeError("pass_data must be a dictionary.")

    values = (
        _required_text(pass_data.get("qr_pass_id"), "qr_pass_id"),
        _required_text(pass_data.get("tenant_slug"), "tenant_slug").lower(),
        _required_text(pass_data.get("rfq_code"), "rfq_code"),
        _required_text(pass_data.get("vendor_name"), "vendor_name"),
        _required_text(pass_data.get("email"), "email").lower(),
        _required_text(pass_data.get("payment_reference"), "payment_reference"),
        _required_text(pass_data.get("proposal_title"), "proposal_title"),
        _required_text(pass_data.get("clearance_status"), "clearance_status"),
    )
    init_db()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO clearance_passes (
                qr_pass_id, tenant_slug, rfq_code, vendor_name, email,
                payment_reference, proposal_title, clearance_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        register_vendor_in_connection(
            connection,
            values[1],
            values[3],
            "solicited",
            values[4],
        )
        row = connection.execute(
            "SELECT qr_pass_id, tenant_slug, rfq_code, vendor_name, email, "
            "payment_reference, proposal_title, clearance_status "
            "FROM clearance_passes WHERE qr_pass_id = ?",
            (values[0],),
        ).fetchone()
    return dict(row)


def record_tenant_payment_verification_in_connection(
    connection: sqlite3.Connection,
    tenant_slug: str,
    payment_reference: str,
    qr_pass_id: str,
    amount_minor: int,
    currency: str,
    provider: str,
    vendor_email: str,
) -> None:
    """Persist a provider-verified payment in the caller's transaction."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_reference = _required_text(payment_reference, "payment_reference")
    normalized_pass_id = _required_text(qr_pass_id, "qr_pass_id")
    normalized_currency = _required_text(currency, "currency").upper()
    normalized_provider = _required_text(provider, "provider")
    normalized_email = _required_text(vendor_email, "vendor_email").lower()
    if not isinstance(amount_minor, int) or isinstance(amount_minor, bool):
        raise TypeError("amount_minor must be an integer.")
    if amount_minor <= 0:
        raise ValueError("Verified payment amount must be positive.")
    tenant = connection.execute(
        "SELECT status FROM tenants WHERE tenant_slug = ? AND is_deleted = 0",
        (normalized_slug,),
    ).fetchone()
    if tenant is None or str(tenant["status"] or "").strip().upper() != "ACTIVE":
        raise ValueError("Payment verification requires an active tenant.")
    clearance = connection.execute(
        """
        SELECT payment_reference, email, clearance_status
        FROM clearance_passes
        WHERE tenant_slug = ? AND qr_pass_id = ?
        """,
        (normalized_slug, normalized_pass_id),
    ).fetchone()
    if clearance is None:
        raise ValueError("The verified payment has no clearance pass for this tenant.")
    if (
        clearance["payment_reference"] != normalized_reference
        or str(clearance["email"]).strip().casefold() != normalized_email.casefold()
        or str(clearance["clearance_status"]).strip().upper() != "PAYMENT_VERIFIED"
    ):
        raise ValueError("Payment details do not match the verified clearance pass.")
    verified_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    connection.execute(
        """
        INSERT INTO tenant_payment_verifications (
            tenant_slug, payment_reference, qr_pass_id, amount_minor,
            currency, provider, vendor_email, verified_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            normalized_slug,
            normalized_reference,
            normalized_pass_id,
            amount_minor,
            normalized_currency,
            normalized_provider,
            normalized_email,
            verified_at,
        ),
    )
    _insert_tenant_activity(
        connection,
        normalized_slug,
        "payment_provider_verified",
        (
            f"{normalized_provider} verified payment {normalized_reference} "
            f"for pass {normalized_pass_id}: {normalized_currency} "
            f"{amount_minor / 100:.2f}."
        ),
        "payment_provider",
    )


def record_tenant_payment_verification(
    tenant_slug: str,
    payment_reference: str,
    qr_pass_id: str,
    amount_minor: int,
    currency: str,
    provider: str,
    vendor_email: str,
) -> None:
    """Record a verified payment against a tenant-owned clearance pass."""
    init_db()
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        record_tenant_payment_verification_in_connection(
            connection,
            tenant_slug,
            payment_reference,
            qr_pass_id,
            amount_minor,
            currency,
            provider,
            vendor_email,
        )


def get_clearance_pass(
    qr_pass_id: str,
    tenant_slug: str,
) -> dict[str, Any] | None:
    """Return a pass only when its ID belongs to the requested tenant."""
    normalized_pass_id = _required_text(qr_pass_id, "qr_pass_id")
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    init_db()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT qr_pass_id, tenant_slug, rfq_code, vendor_name, email, "
            "payment_reference, proposal_title, clearance_status "
            "FROM clearance_passes WHERE qr_pass_id = ? AND tenant_slug = ?",
            (normalized_pass_id, normalized_slug),
        ).fetchone()
    return dict(row) if row is not None else None


def update_clearance_status(
    qr_pass_id: str,
    tenant_slug: str,
    clearance_status: str,
) -> bool:
    """Update a pass status only within its tenant namespace."""
    values = (
        _required_text(clearance_status, "clearance_status"),
        _required_text(qr_pass_id, "qr_pass_id"),
        _required_text(tenant_slug, "tenant_slug").lower(),
    )
    init_db()
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE clearance_passes SET clearance_status = ? "
            "WHERE qr_pass_id = ? AND tenant_slug = ?",
            values,
        )
    return cursor.rowcount > 0


if __name__ == "__main__":
    init_db()
    print(f"SQLite schema initialized and verified at {DB_FILE}")


import pandas as pd

def get_all_tenants():
    """Retrieve all onboarded tenant records from the persistent database."""
    try:
        conn = sqlite3.connect("database.db")
        df = pd.read_sql("SELECT * FROM tenants", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

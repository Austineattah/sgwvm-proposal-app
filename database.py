import json
import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


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
    ),
    "admin_access_logs": (
        ("id", "INTEGER", 1, None),
        ("tenant_slug", "TEXT", 0, None),
        ("action", "TEXT", 0, None),
        ("actor", "TEXT", 0, None),
        ("timestamp", "DATETIME", 0, "CURRENT_TIMESTAMP"),
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
        status TEXT
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


def init_db() -> None:
    """Create the required tables and fail clearly if an existing schema conflicts."""
    with get_connection() as connection:
        for statement in _CREATE_TABLES:
            connection.execute(statement)
        _verify_schema(connection)


def _required_text(value: Any, field_name: str) -> str:
    normalized = str(value).strip() if value is not None else ""
    if not normalized:
        raise ValueError(f"{field_name} is required.")
    return normalized


def get_tenant_by_slug(tenant_slug: str) -> dict[str, Any] | None:
    """Return a tenant record, or None when the slug is not registered."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    init_db()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT tenant_slug, full_corporation_name, institution_category, "
            "apex_title, sub_directorates_json, logo_path, status "
            "FROM tenants WHERE tenant_slug = ?",
            (normalized_slug,),
        ).fetchone()
    return dict(row) if row is not None else None


def list_tenants() -> list[dict[str, Any]]:
    """Return registered tenants ordered by slug."""
    init_db()
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT tenant_slug, full_corporation_name, institution_category, "
            "apex_title, sub_directorates_json, logo_path, status "
            "FROM tenants ORDER BY tenant_slug"
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
        row = connection.execute(
            "SELECT tenant_slug, full_corporation_name, institution_category, "
            "apex_title, sub_directorates_json, logo_path, status "
            "FROM tenants WHERE tenant_slug = ?",
            (tenant_slug,),
        ).fetchone()
    return dict(row)


def create_tenant_onboarding(onboarding_data: dict[str, Any]) -> dict[str, Any]:
    """Create an active tenant from the sovereign onboarding form payload."""
    if not isinstance(onboarding_data, dict):
        raise TypeError("onboarding_data must be a dictionary.")

    tenant_slug = _required_text(onboarding_data.get("tenant_slug"), "tenant_slug").lower()
    organization_name = _required_text(
        onboarding_data.get("full_corporation_name"),
        "full_corporation_name",
    )
    _required_text(onboarding_data.get("admin_email"), "admin_email")
    _required_text(onboarding_data.get("admin_phone"), "admin_phone")

    return save_tenant(
        {
            "tenant_slug": tenant_slug,
            "full_corporation_name": organization_name,
            "status": "Active",
        }
    )


def delete_tenant(tenant_slug: str) -> bool:
    """Delete a tenant by slug; return whether a record was deleted."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    init_db()
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM tenants WHERE tenant_slug = ?",
            (normalized_slug,),
        )
    return cursor.rowcount > 0


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
        row = connection.execute(
            "SELECT qr_pass_id, tenant_slug, rfq_code, vendor_name, email, "
            "payment_reference, proposal_title, clearance_status "
            "FROM clearance_passes WHERE qr_pass_id = ?",
            (values[0],),
        ).fetchone()
    return dict(row)


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

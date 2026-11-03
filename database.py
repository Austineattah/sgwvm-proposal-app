import hashlib
import json
import logging
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


def init_db() -> None:
    """Create the required tables and fail clearly if an existing schema conflicts."""
    with get_connection() as connection:
        vendors_table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'vendors'"
        ).fetchone() is not None
        for statement in _CREATE_TABLES:
            connection.execute(statement)
        _verify_schema(connection)
        if not vendors_table_exists:
            _backfill_solicited_vendors(connection)


def _required_text(value: Any, field_name: str) -> str:
    normalized = str(value).strip() if value is not None else ""
    if not normalized:
        raise ValueError(f"{field_name} is required.")
    return normalized


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
    """Update an existing tenant status without creating a tenant implicitly."""
    normalized_slug = _required_text(tenant_slug, "tenant_slug").lower()
    normalized_status = _required_text(status, "status")
    init_db()
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE tenants SET status = ? WHERE tenant_slug = ?",
            (normalized_status, normalized_slug),
        )
    return cursor.rowcount == 1


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
        connection.execute(
            "DELETE FROM clearance_passes WHERE tenant_slug = ?", (normalized_slug,)
        )
        connection.execute(
            "DELETE FROM admin_access_logs WHERE tenant_slug = ?", (normalized_slug,)
        )
        connection.execute(
            "DELETE FROM vendors WHERE tenant_slug = ?", (normalized_slug,)
        )
        connection.execute(
            "DELETE FROM tenant_archive WHERE tenant_slug = ?", (normalized_slug,)
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

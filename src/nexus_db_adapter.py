"""Persistence adapter for NexusVault tenant lifecycle and support records."""

from __future__ import annotations

import logging
import os
import re
import secrets
import sqlite3
import uuid
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TypeAlias

import psycopg2

logger = logging.getLogger(__name__)

TenantRow: TypeAlias = dict[str, Any]
ConnectionFactory: TypeAlias = Callable[[], Any]

_TENANT_STATUSES = (
    "PENDING_ACTIVATION",
    "PAYMENT_PENDING",
    "DEMO_ACTIVE",
    "SUBSCRIBED",
    "EXPIRED",
)


class NexusDatabaseAdapter:
    """Parameterized SQLite/PostgreSQL persistence with tenant-scoped access.

    PostgreSQL sessions set ``app.current_tenant`` locally for every database
    transaction. Recovery and expiry scopes can only read tenant records.
    The application must authenticate and authorize the tenant before using
    its ID: PostgreSQL custom settings are not an authentication mechanism.
    Keep database credentials restricted to trusted services and do not use
    a superuser or BYPASSRLS role for application connections.

    SQLite does not provide RLS; each operation instead includes an explicit
    tenant predicate. SQLite is intended as a local fallback, not a production
    multi-tenant security boundary.
    """

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        connection_string: str | None = None,
        connection_factory: ConnectionFactory | None = None,
        initialize: bool = True,
    ) -> None:
        self._custom_connection_factory = connection_factory is not None
        if connection_factory is not None:
            self._connection_factory = connection_factory
            self._dialect = "sqlite" if database_path is not None else "postgres"
        else:
            dsn = connection_string or os.environ.get("DATABASE_URL")
            if dsn and dsn.startswith(("postgres://", "postgresql://")):
                self._dialect = "postgres"
                self._connection_factory = lambda: psycopg2.connect(dsn)
            else:
                self._dialect = "sqlite"
                path = Path(database_path) if database_path is not None else _sqlite_path(dsn)
                path.parent.mkdir(parents=True, exist_ok=True)
                self._database_path = path
                self._connection_factory = lambda: sqlite3.connect(
                    str(path), timeout=30
                )
        if initialize:
            self.initialize()

    @property
    def dialect(self) -> str:
        """Return the active database dialect."""
        return self._dialect

    def initialize(self) -> None:
        """Create lifecycle, ticket, and immutable AI audit tables."""
        with self._cursor("__schema__") as cursor:
            statements = (
                _POSTGRES_SCHEMA if self._dialect == "postgres" else _SQLITE_SCHEMA
            )
            for statement in statements:
                cursor.execute(statement)
            if self._dialect == "postgres":
                for statement in _POSTGRES_RLS:
                    cursor.execute(statement)
                for statement in _POSTGRES_AUDIT_IMMUTABILITY:
                    cursor.execute(statement)

    def register_tenant(
        self,
        org_name: str,
        admin_email: str,
        *,
        demo_days_assigned: int = 14,
    ) -> TenantRow:
        """Register an onboarded tenant in the pending activation state."""
        if not org_name or not org_name.strip():
            raise ValueError("org_name must not be empty.")
        if not admin_email or not admin_email.strip() or "@" not in admin_email:
            raise ValueError("admin_email must be a valid email address.")
        if demo_days_assigned < 1:
            raise ValueError("demo_days_assigned must be at least one day.")

        normalized_email = admin_email.strip().casefold()
        tenant_id = str(uuid.uuid4())
        slug = self._generate_unique_slug(org_name)
        statement = """
            INSERT INTO nv_tenants
                (tenant_id, org_name, admin_email, slug, status,
                 is_activated, demo_days_assigned)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        with self._cursor(tenant_id) as cursor:
            self._execute(
                cursor,
                statement,
                (
                    tenant_id,
                    org_name.strip(),
                    normalized_email,
                    slug,
                    "PENDING_ACTIVATION",
                    False,
                    demo_days_assigned,
                ),
            )
        tenant = self.get_tenant(tenant_id)
        if tenant is None:
            raise RuntimeError("Tenant registration completed but could not be read.")
        return tenant

    def get_tenant(self, tenant_id: str) -> TenantRow | None:
        """Fetch a tenant by its authenticated tenant identifier."""
        if not tenant_id:
            raise ValueError("tenant_id must not be empty.")
        with self._cursor(tenant_id) as cursor:
            self._execute(
                cursor,
                "SELECT * FROM nv_tenants WHERE tenant_id = %s",
                (tenant_id,),
            )
            return _row_to_dict(cursor, cursor.fetchone())

    def lookup_tenant_by_email(self, admin_email: str) -> TenantRow | None:
        """Resolve a resume-login hint using an exact email-only RLS scope."""
        normalized_email = _validate_lookup(admin_email, "admin_email").casefold()
        scope = f"resume-email:{normalized_email}"
        with self._cursor(scope) as cursor:
            self._execute(
                cursor,
                """
                SELECT * FROM nv_tenants
                WHERE lower(admin_email) = %s
                ORDER BY created_at DESC, tenant_id
                LIMIT 2
                """,
                (normalized_email,),
            )
            rows = cursor.fetchall()
            if len(rows) > 1:
                raise ValueError(
                    "This email belongs to multiple tenants; use the tenant slug."
                )
            return _row_to_dict(cursor, rows[0]) if rows else None

    def lookup_tenant_by_slug(self, slug: str) -> TenantRow | None:
        """Resolve a resume-login hint using an exact slug-only RLS scope."""
        normalized_slug = _validate_lookup(slug, "slug").casefold()
        scope = f"resume-slug:{normalized_slug}"
        with self._cursor(scope) as cursor:
            self._execute(
                cursor,
                "SELECT * FROM nv_tenants WHERE lower(slug) = %s",
                (normalized_slug,),
            )
            return _row_to_dict(cursor, cursor.fetchone())

    def transition_tenant(
        self,
        tenant_id: str,
        *,
        expected_status: str,
        status: str,
        is_activated: bool,
        demo_expires_at: datetime | None = None,
        demo_days_assigned: int | None = None,
    ) -> TenantRow:
        """Perform an optimistic, tenant-scoped state update."""
        if status not in _TENANT_STATUSES:
            raise ValueError(f"Unknown tenant status: {status!r}.")
        if demo_days_assigned is not None and demo_days_assigned < 1:
            raise ValueError("demo_days_assigned must be at least one day.")
        if demo_expires_at is not None and demo_expires_at.tzinfo is None:
            raise ValueError("demo_expires_at must include a timezone.")
        assignments = [
            "status = %s",
            "is_activated = %s",
            "demo_expires_at = %s",
        ]
        params: list[Any] = [status, is_activated, demo_expires_at]
        if demo_days_assigned is not None:
            assignments.append("demo_days_assigned = %s")
            params.append(demo_days_assigned)
        params.extend((tenant_id, expected_status))
        query = (
            f"UPDATE nv_tenants SET {', '.join(assignments)} "
            "WHERE tenant_id = %s AND status = %s"
        )
        with self._cursor(tenant_id) as cursor:
            self._execute(cursor, query, tuple(params))
            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Tenant lifecycle changed concurrently or tenant was not found."
                )
        tenant = self.get_tenant(tenant_id)
        if tenant is None:
            raise RuntimeError("Tenant state update completed but could not be read.")
        return tenant

    def list_tenants_for_expiry_scan(self, *, today: datetime) -> list[TenantRow]:
        """Return unpaid demo tenants due within five days, including overdue."""
        if today.tzinfo is None:
            raise ValueError("today must include a timezone.")
        today_utc = today.astimezone(timezone.utc)
        cutoff = today_utc.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=6)
        scope = "__expiry_job__"
        with self._cursor(scope) as cursor:
            self._execute(
                cursor,
                """
                SELECT * FROM nv_tenants
                WHERE status = %s AND is_activated = %s
                  AND demo_expires_at IS NOT NULL AND demo_expires_at < %s
                ORDER BY demo_expires_at, tenant_id
                """,
                ("DEMO_ACTIVE", False, cutoff),
            )
            rows = cursor.fetchall()
            return [_row_to_dict(cursor, row) for row in rows if row is not None]

    def add_expiry_alert(
        self,
        tenant_id: str,
        *,
        alert_key: str,
        message: str,
    ) -> bool:
        """Persist a deduplicated in-portal expiry alert in the support inbox."""
        ticket_id = f"expiry:{tenant_id}:{alert_key}"
        with self._cursor(tenant_id) as cursor:
            self._execute(
                cursor,
                """
                INSERT INTO nv_support_tickets
                    (ticket_id, tenant_id, user_id, email, query_text,
                     priority, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (ticket_id) DO NOTHING
                """,
                (
                    ticket_id,
                    tenant_id,
                    "system:expiry-notifier",
                    None,
                    message,
                    "URGENT",
                    "OPEN",
                ),
            )
            return cursor.rowcount == 1

    def log_ai_query(
        self,
        tenant_id: str,
        *,
        query_id: str,
        user_id: str | None,
        query_text: str,
        confidence_score: float,
        grounded_in_kb: bool,
        escalated_to_human: bool,
        ticket_id: str | None,
    ) -> None:
        """Append one AI audit record; the table rejects updates and deletes."""
        if not 0.0 <= confidence_score <= 1.0:
            raise ValueError("confidence_score must be between 0 and 1.")
        with self._cursor(tenant_id) as cursor:
            self._execute(
                cursor,
                """
                INSERT INTO nv_ai_audit_logs
                    (query_id, tenant_id, user_id, query_text, confidence_score,
                     grounded_in_kb, escalated_to_human, ticket_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    query_id,
                    tenant_id,
                    user_id,
                    query_text,
                    confidence_score,
                    grounded_in_kb,
                    escalated_to_human,
                    ticket_id,
                ),
            )

    def _generate_unique_slug(self, org_name: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "", org_name.casefold())[:53] or "tenant"
        for _ in range(10):
            candidate = f"{base}_{secrets.token_hex(4)}"
            with self._cursor("resume-slug:" + candidate) as cursor:
                self._execute(
                    cursor,
                    "SELECT 1 FROM nv_tenants WHERE lower(slug) = %s",
                    (candidate.casefold(),),
                )
                if cursor.fetchone() is None:
                    return candidate
        raise RuntimeError("Unable to generate a unique tenant slug.")

    @contextmanager
    def _cursor(self, tenant_scope: str) -> Iterator[Any]:
        """Open an atomic transaction and establish its Postgres RLS context."""
        conn = self._connection_factory()
        try:
            if self._dialect == "sqlite":
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON")
                with conn:
                    cursor = conn.cursor()
                    try:
                        yield cursor
                    finally:
                        cursor.close()
            else:
                with conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "SET LOCAL app.current_tenant = %s",
                            (tenant_scope,),
                        )
                        yield cursor
        finally:
            conn.close()

    def _execute(
        self, cursor: Any, query: str, params: Sequence[Any] = ()
    ) -> None:
        if self._dialect == "sqlite":
            cursor.execute(query.replace("%s", "?"), tuple(params))
        else:
            cursor.execute(query, tuple(params))


def _validate_lookup(value: str, field: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"{field} must not be empty.")
    if "\x00" in value:
        raise ValueError(f"{field} contains an invalid character.")
    return value.strip()


def _row_to_dict(cursor: Any, row: Any) -> TenantRow | None:
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return dict(row)
    if isinstance(row, dict):
        return row
    return {
        description[0]: value
        for description, value in zip(cursor.description, row, strict=True)
    }


def _sqlite_path(database_url: str | None) -> Path:
    default_path = Path(__file__).resolve().parents[1] / "nexus_sovereign.db"
    if not database_url or not database_url.startswith("sqlite:///"):
        return default_path
    path_text = database_url.removeprefix("sqlite:///")
    if re.match(r"^/[A-Za-z]:[/\\]", path_text):
        path_text = path_text[1:]
    return Path(path_text)


_SQLITE_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS nv_tenants (
        tenant_id TEXT PRIMARY KEY,
        org_name TEXT NOT NULL,
        admin_email TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL CHECK (
            status IN ('PENDING_ACTIVATION', 'PAYMENT_PENDING', 'DEMO_ACTIVE',
                       'SUBSCRIBED', 'EXPIRED')
        ),
        is_activated INTEGER NOT NULL DEFAULT 0,
        demo_days_assigned INTEGER NOT NULL DEFAULT 14 CHECK (demo_days_assigned > 0),
        demo_expires_at TIMESTAMP NULL,
        desk_operator TEXT NOT NULL DEFAULT 'Authorized Desk Officer',
        solicited_vendor_status TEXT NOT NULL
            DEFAULT 'Managed via Internal Admin Settings',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS nv_support_tickets (
        ticket_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        user_id TEXT,
        email TEXT,
        query_text TEXT NOT NULL,
        priority TEXT NOT NULL DEFAULT 'NORMAL',
        status TEXT NOT NULL DEFAULT 'OPEN',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS nv_ai_audit_logs (
        query_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        user_id TEXT,
        query_text TEXT NOT NULL,
        confidence_score REAL NOT NULL CHECK (
            confidence_score >= 0 AND confidence_score <= 1
        ),
        grounded_in_kb INTEGER NOT NULL,
        escalated_to_human INTEGER NOT NULL,
        ticket_id TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_nv_tenants_admin_email ON nv_tenants(lower(admin_email))",
    "CREATE INDEX IF NOT EXISTS idx_nv_tenants_status_expiry ON nv_tenants(status, demo_expires_at)",
    """
    CREATE TRIGGER IF NOT EXISTS nv_ai_audit_no_update
    BEFORE UPDATE ON nv_ai_audit_logs
    BEGIN
        SELECT RAISE(ABORT, 'nv_ai_audit_logs is immutable');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS nv_ai_audit_no_delete
    BEFORE DELETE ON nv_ai_audit_logs
    BEGIN
        SELECT RAISE(ABORT, 'nv_ai_audit_logs is immutable');
    END
    """,
)

_POSTGRES_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS nv_tenants (
        tenant_id VARCHAR PRIMARY KEY,
        org_name VARCHAR NOT NULL,
        admin_email VARCHAR NOT NULL,
        slug VARCHAR UNIQUE NOT NULL,
        status VARCHAR NOT NULL CHECK (
            status IN ('PENDING_ACTIVATION', 'PAYMENT_PENDING', 'DEMO_ACTIVE',
                       'SUBSCRIBED', 'EXPIRED')
        ),
        is_activated BOOLEAN NOT NULL DEFAULT FALSE,
        demo_days_assigned INTEGER NOT NULL DEFAULT 14 CHECK (demo_days_assigned > 0),
        demo_expires_at TIMESTAMP WITH TIME ZONE NULL,
        desk_operator VARCHAR NOT NULL DEFAULT 'Authorized Desk Officer',
        solicited_vendor_status VARCHAR NOT NULL
            DEFAULT 'Managed via Internal Admin Settings',
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS nv_support_tickets (
        ticket_id VARCHAR PRIMARY KEY,
        tenant_id VARCHAR NOT NULL,
        user_id VARCHAR,
        email VARCHAR,
        query_text TEXT NOT NULL,
        priority VARCHAR NOT NULL DEFAULT 'NORMAL',
        status VARCHAR NOT NULL DEFAULT 'OPEN',
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS nv_ai_audit_logs (
        query_id VARCHAR PRIMARY KEY,
        tenant_id VARCHAR NOT NULL,
        user_id VARCHAR,
        query_text TEXT NOT NULL,
        confidence_score DOUBLE PRECISION NOT NULL CHECK (
            confidence_score >= 0 AND confidence_score <= 1
        ),
        grounded_in_kb BOOLEAN NOT NULL,
        escalated_to_human BOOLEAN NOT NULL,
        ticket_id VARCHAR,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_nv_tenants_admin_email ON nv_tenants(lower(admin_email))",
    "CREATE INDEX IF NOT EXISTS idx_nv_tenants_status_expiry ON nv_tenants(status, demo_expires_at)",
    "ALTER TABLE nv_tenants ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE nv_support_tickets ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE nv_ai_audit_logs ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE nv_tenants FORCE ROW LEVEL SECURITY",
    "ALTER TABLE nv_support_tickets FORCE ROW LEVEL SECURITY",
    "ALTER TABLE nv_ai_audit_logs FORCE ROW LEVEL SECURITY",
)

_POSTGRES_RLS = (
    "DROP POLICY IF EXISTS nv_tenants_tenant_scope ON nv_tenants",
    "DROP POLICY IF EXISTS nv_tenants_lookup_scope ON nv_tenants",
    """
    CREATE POLICY nv_tenants_tenant_scope ON nv_tenants
    USING (tenant_id = current_setting('app.current_tenant', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant', true))
    """,
    """
    CREATE POLICY nv_tenants_lookup_scope ON nv_tenants FOR SELECT
    USING (
        current_setting('app.current_tenant', true) = 'resume-email:' || lower(admin_email)
        OR current_setting('app.current_tenant', true) = 'resume-slug:' || lower(slug)
        OR current_setting('app.current_tenant', true) = '__expiry_job__'
    )
    """,
    "DROP POLICY IF EXISTS nv_support_tickets_tenant_scope ON nv_support_tickets",
    """
    CREATE POLICY nv_support_tickets_tenant_scope ON nv_support_tickets
    USING (tenant_id = current_setting('app.current_tenant', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant', true))
    """,
    "DROP POLICY IF EXISTS nv_ai_audit_tenant_scope ON nv_ai_audit_logs",
    """
    CREATE POLICY nv_ai_audit_tenant_scope ON nv_ai_audit_logs
    USING (tenant_id = current_setting('app.current_tenant', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant', true))
    """,
)

_POSTGRES_AUDIT_IMMUTABILITY = (
    """
    CREATE OR REPLACE FUNCTION nv_reject_ai_audit_mutation()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'nv_ai_audit_logs is immutable';
    END
    $$
    """,
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'nv_ai_audit_immutable'
              AND tgrelid = 'nv_ai_audit_logs'::regclass
        ) THEN
            CREATE TRIGGER nv_ai_audit_immutable
            BEFORE UPDATE OR DELETE ON nv_ai_audit_logs
            FOR EACH ROW EXECUTE FUNCTION nv_reject_ai_audit_mutation();
        END IF;
    END
    $$
    """,
)

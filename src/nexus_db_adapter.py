"""SQLite persistence for tenant lifecycle and tenant-scoped support.

SQLite has no row-level security. Callers must authenticate and authorize the
tenant or platform administrator before supplying an identifier to this module.
"""

from __future__ import annotations

import logging
import os
import re
import secrets
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TypeAlias

from src.developer_kb import NEXUSVAULT_EXECUTIVE_KB

logger = logging.getLogger(__name__)
TenantRow: TypeAlias = dict[str, Any]
DB_PATH = Path(__file__).resolve().parents[1] / "nexus_sovereign.db"
_TENANT_STATUSES = frozenset(
    {"PENDING_ACTIVATION", "PAYMENT_PENDING", "DEMO_ACTIVE", "SUBSCRIBED", "EXPIRED"}
)
_STOP_WORDS = frozenset(
    {
        "what",
        "when",
        "where",
        "which",
        "does",
        "that",
        "this",
        "with",
        "from",
        "into",
        "your",
        "their",
        "have",
        "the",
        "and",
        "for",
        "are",
        "how",
        "who",
        "is",
    }
)


def _required(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ValueError(f"{name} must be a non-empty string without NUL characters.")
    return value.strip()


def _open_connection(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), timeout=30)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise RuntimeError("SQLite foreign key enforcement is unavailable.")
    except Exception:
        conn.close()
        raise
    return conn


@contextmanager
def get_db_connection() -> Iterator[sqlite3.Connection]:
    """Yield a transaction and close its connection on success or failure."""
    conn = _open_connection(DB_PATH)
    try:
        with conn:
            conn.execute("BEGIN")
            yield conn
    finally:
        conn.close()


class NexusDatabaseAdapter:
    """SQLite adapter; every tenant operation requires a trusted tenant scope."""

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        connection_string: str | None = None,
        initialize: bool = True,
    ) -> None:
        dsn = connection_string or (
            os.getenv("DATABASE_URL") if database_path is None else None
        )
        if dsn:
            if not dsn.startswith("sqlite:///"):
                raise ValueError("NexusDatabaseAdapter supports SQLite URLs only.")
            url_path = dsn.removeprefix("sqlite:///")
            if re.match(r"^/[A-Za-z]:[/\\]", url_path):
                url_path = url_path[1:]
            database_path = url_path
        self._database_path = Path(
            database_path if database_path is not None else DB_PATH
        )
        if str(self._database_path) == ":memory:":
            raise ValueError("A persistent SQLite database path is required.")
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        if initialize:
            self.initialize()

    @property
    def dialect(self) -> str:
        return "sqlite"

    @contextmanager
    def get_connection(self) -> Iterator[sqlite3.Connection]:
        conn = _open_connection(self._database_path)
        try:
            with conn:
                conn.execute("BEGIN")
                yield conn
        finally:
            conn.close()

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()

    def initialize(self) -> None:
        with self._cursor() as cursor:
            for statement in _SCHEMA:
                cursor.execute(statement)
            columns = {
                row[1]
                for row in cursor.execute("PRAGMA table_info(nv_support_tickets)")
            }
            required = {
                "ticket_id",
                "tenant_id",
                "tenant_slug",
                "org_name",
                "sender_email",
                "message",
                "response",
                "status",
                "is_auto_responded",
                "created_at",
                "responded_at",
            }
            if not required.issubset(columns):
                raise RuntimeError(
                    "Existing nv_support_tickets schema is incompatible; migrate it before starting."
                )
            for statement in _SUPPORT_SCHEMA:
                cursor.execute(statement)

    def register_tenant(
        self, org_name: str, admin_email: str, *, demo_days_assigned: int = 14
    ) -> TenantRow:
        name = _required(org_name, "org_name")
        email = _required(admin_email, "admin_email").casefold()
        if "@" not in email or demo_days_assigned < 1:
            raise ValueError("A valid email and positive demo duration are required.")
        tenant_id = str(uuid.uuid4())
        base = re.sub(r"[^a-z0-9]+", "", name.casefold())[:53] or "tenant"
        for _ in range(10):
            slug = f"{base}_{secrets.token_hex(4)}"
            try:
                with self._cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO nv_tenants (tenant_id, org_name, admin_email, slug, status, is_activated, demo_days_assigned) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            tenant_id,
                            name,
                            email,
                            slug,
                            "PENDING_ACTIVATION",
                            0,
                            demo_days_assigned,
                        ),
                    )
                    cursor.execute(
                        "SELECT * FROM nv_tenants WHERE tenant_id = ?", (tenant_id,)
                    )
                    row = cursor.fetchone()
                    if row is None:
                        raise RuntimeError("Registered tenant could not be read.")
                    return dict(row)
            except sqlite3.IntegrityError:
                if self.lookup_tenant_by_slug(slug) is None:
                    raise
        raise RuntimeError("Unable to generate a unique tenant slug.")

    def get_tenant(self, tenant_id: str) -> TenantRow | None:
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM nv_tenants WHERE tenant_id = ?",
                (_required(tenant_id, "tenant_id"),),
            )
            row = cursor.fetchone()
            return dict(row) if row is not None else None

    def lookup_tenant_by_slug(self, slug: str) -> TenantRow | None:
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM nv_tenants WHERE lower(slug) = ?",
                (_required(slug, "slug").casefold(),),
            )
            row = cursor.fetchone()
            return dict(row) if row is not None else None

    def lookup_tenant_by_email(self, admin_email: str) -> TenantRow | None:
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM nv_tenants WHERE lower(admin_email) = ? ORDER BY created_at DESC, tenant_id LIMIT 2",
                (_required(admin_email, "admin_email").casefold(),),
            )
            rows = cursor.fetchall()
            if len(rows) > 1:
                raise ValueError(
                    "This email belongs to multiple tenants; use the tenant slug."
                )
            return dict(rows[0]) if rows else None

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
        tenant_id = _required(tenant_id, "tenant_id")
        if status not in _TENANT_STATUSES or expected_status not in _TENANT_STATUSES:
            raise ValueError("Unknown tenant status.")
        if demo_days_assigned is not None and demo_days_assigned < 1:
            raise ValueError("demo_days_assigned must be positive.")
        if demo_expires_at is not None and demo_expires_at.utcoffset() is None:
            raise ValueError("demo_expires_at must include a timezone.")
        expires = (
            str(demo_expires_at.astimezone(timezone.utc)) if demo_expires_at else None
        )
        with self._cursor() as cursor:
            cursor.execute(
                "UPDATE nv_tenants SET status = ?, is_activated = ?, demo_expires_at = ?, demo_days_assigned = COALESCE(?, demo_days_assigned) WHERE tenant_id = ? AND status = ?",
                (
                    status,
                    int(is_activated),
                    expires,
                    demo_days_assigned,
                    tenant_id,
                    expected_status,
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Tenant lifecycle changed concurrently or tenant was not found."
                )
            cursor.execute("SELECT * FROM nv_tenants WHERE tenant_id = ?", (tenant_id,))
            return dict(cursor.fetchone())

    def list_tenants_for_expiry_scan(self, *, today: datetime) -> list[TenantRow]:
        if today.utcoffset() is None:
            raise ValueError("today must include a timezone.")
        cutoff = today.astimezone(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=6)
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM nv_tenants WHERE status = ? AND is_activated = 0 AND demo_expires_at IS NOT NULL AND demo_expires_at < ? ORDER BY demo_expires_at, tenant_id",
                ("DEMO_ACTIVE", str(cutoff)),
            )
            return [dict(row) for row in cursor.fetchall()]

    def add_expiry_alert(self, tenant_id: str, *, alert_key: str, message: str) -> bool:
        with self._cursor() as cursor:
            tenant_id = _required(tenant_id, "tenant_id")
            message = _required(message, "message")
            cursor.execute(
                "INSERT INTO nv_expiry_alerts (tenant_id, alert_key, message) VALUES (?, ?, ?) ON CONFLICT(tenant_id, alert_key) DO NOTHING",
                (tenant_id, _required(alert_key, "alert_key"), message),
            )
            if cursor.rowcount != 1:
                return False
            cursor.execute(
                "SELECT slug, org_name, admin_email FROM nv_tenants WHERE tenant_id = ?",
                (tenant_id,),
            )
            tenant = cursor.fetchone()
            if tenant is None:
                raise RuntimeError("The alert tenant no longer exists.")
            cursor.execute(
                "INSERT INTO nv_support_tickets (tenant_id, tenant_slug, org_name, sender_email, message) VALUES (?, ?, ?, ?, ?)",
                (
                    tenant_id,
                    tenant["slug"],
                    tenant["org_name"],
                    tenant["admin_email"],
                    message,
                ),
            )
            return True

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
        if not 0 <= confidence_score <= 1:
            raise ValueError("confidence_score must be between 0 and 1.")
        with self._cursor() as cursor:
            cursor.execute(
                "INSERT INTO nv_ai_audit_logs (query_id, tenant_id, user_id, query_text, confidence_score, grounded_in_kb, escalated_to_human, ticket_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    _required(query_id, "query_id"),
                    _required(tenant_id, "tenant_id"),
                    user_id,
                    _required(query_text, "query_text"),
                    confidence_score,
                    int(grounded_in_kb),
                    int(escalated_to_human),
                    ticket_id,
                ),
            )

    def create_support_ticket(
        self,
        tenant_id: str,
        tenant_slug: str,
        org_name: str,
        sender_email: str,
        message: str,
    ) -> bool:
        tenant_id = _required(tenant_id, "tenant_id")
        tenant_slug = _required(tenant_slug, "tenant_slug").casefold()
        sender_email = _required(sender_email, "sender_email")
        message = _required(message, "message")
        answer = match_knowledge_base(message)
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT org_name FROM nv_tenants WHERE tenant_id = ? AND slug = ?",
                (tenant_id, tenant_slug),
            )
            tenant = cursor.fetchone()
            if tenant is None:
                return False
            cursor.execute(
                "INSERT INTO nv_support_tickets (tenant_id, tenant_slug, org_name, sender_email, message, response, status, is_auto_responded, responded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    tenant_id,
                    tenant_slug,
                    tenant["org_name"],
                    sender_email,
                    message,
                    answer,
                    "RESOLVED (AI AUTO-REPLY)" if answer else "OPEN",
                    int(answer is not None),
                    datetime.now(timezone.utc).isoformat() if answer else None,
                ),
            )
            return True

    def get_tenant_support_tickets(self, tenant_slug: str) -> list[dict[str, Any]]:
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT ticket.ticket_id, ticket.sender_email, ticket.message, ticket.response, ticket.status, ticket.is_auto_responded, ticket.created_at, ticket.responded_at FROM nv_support_tickets AS ticket JOIN nv_tenants AS tenant ON tenant.tenant_id = ticket.tenant_id AND tenant.slug = ticket.tenant_slug WHERE tenant.slug = ? ORDER BY ticket.created_at DESC, ticket.ticket_id DESC",
                (_required(tenant_slug, "tenant_slug").casefold(),),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_all_support_tickets(self) -> list[dict[str, Any]]:
        """Return all tickets; callers must enforce platform-admin authorization."""
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM nv_support_tickets ORDER BY created_at DESC, ticket_id DESC"
            )
            return [dict(row) for row in cursor.fetchall()]

    def respond_to_support_ticket(self, ticket_id: int, response_text: str) -> bool:
        """Respond to an open ticket; callers must authorize the platform admin."""
        with self._cursor() as cursor:
            cursor.execute(
                "UPDATE nv_support_tickets SET response = ?, status = ?, responded_at = ? WHERE ticket_id = ? AND status = ?",
                (
                    _required(response_text, "response_text"),
                    "RESOLVED (CEO RESPONSE)",
                    datetime.now(timezone.utc).isoformat(),
                    ticket_id,
                    "OPEN",
                ),
            )
            return cursor.rowcount == 1


def init_db() -> None:
    NexusDatabaseAdapter()


def match_knowledge_base(message: str) -> str | None:
    if not isinstance(message, str) or not message.strip():
        return None
    terms = set(re.findall(r"\w+", message.casefold())) - _STOP_WORDS
    if len(terms) < 3:
        return None
    matches = []
    for topic in NEXUSVAULT_EXECUTIVE_KB.values():
        for qa in topic["qa_pairs"]:
            question = set(re.findall(r"\w+", qa["question"].casefold())) - _STOP_WORDS
            score = len(terms & question) / max(len(terms), len(question))
            if score >= 0.85:
                matches.append((score, qa["answer"]))
    matches.sort(key=lambda item: item[0], reverse=True)
    if not matches or (len(matches) > 1 and matches[0][0] == matches[1][0]):
        return None
    return f"**[AUTOMATED SYSTEM INTELLIGENCE BRIEFING]**\n\n{matches[0][1]}\n\n*This response was generated from the NexusVault Knowledge Base.*"


def create_support_ticket(
    tenant_id: str, tenant_slug: str, org_name: str, sender_email: str, message: str
) -> bool:
    try:
        return NexusDatabaseAdapter().create_support_ticket(
            tenant_id, tenant_slug, org_name, sender_email, message
        )
    except (sqlite3.Error, OSError, RuntimeError, ValueError):
        logger.exception("Could not create support ticket.")
        return False


def get_tenant_support_tickets(tenant_slug: str) -> list[dict[str, Any]]:
    return NexusDatabaseAdapter().get_tenant_support_tickets(tenant_slug)


def get_all_support_tickets() -> list[dict[str, Any]]:
    return NexusDatabaseAdapter().get_all_support_tickets()


def respond_to_support_ticket(ticket_id: int, response_text: str) -> bool:
    try:
        return NexusDatabaseAdapter().respond_to_support_ticket(
            ticket_id, response_text
        )
    except (sqlite3.Error, OSError, RuntimeError, ValueError):
        logger.exception("Could not respond to support ticket.")
        return False


_SCHEMA = (
    """CREATE TABLE IF NOT EXISTS nv_tenants (
        tenant_id TEXT PRIMARY KEY, org_name TEXT NOT NULL, admin_email TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE, status TEXT NOT NULL DEFAULT 'PENDING_ACTIVATION',
        is_activated INTEGER NOT NULL DEFAULT 0, demo_days_assigned INTEGER NOT NULL DEFAULT 14,
        demo_expires_at TIMESTAMP, desk_operator TEXT DEFAULT 'Authorized Desk Officer',
        solicited_vendor_status TEXT DEFAULT 'Managed via Internal Admin Settings',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS nv_support_tickets (
        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT NOT NULL,
        tenant_slug TEXT NOT NULL, org_name TEXT NOT NULL, sender_email TEXT NOT NULL,
        message TEXT NOT NULL, response TEXT, status TEXT NOT NULL DEFAULT 'OPEN',
        is_auto_responded INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        responded_at TIMESTAMP, FOREIGN KEY (tenant_id) REFERENCES nv_tenants(tenant_id))""",
    """CREATE TABLE IF NOT EXISTS nv_expiry_alerts (
        tenant_id TEXT NOT NULL, alert_key TEXT NOT NULL, message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (tenant_id, alert_key),
        FOREIGN KEY (tenant_id) REFERENCES nv_tenants(tenant_id))""",
    """CREATE TABLE IF NOT EXISTS nv_ai_audit_logs (
        query_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, user_id TEXT, query_text TEXT NOT NULL,
        confidence_score REAL NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
        grounded_in_kb INTEGER NOT NULL, escalated_to_human INTEGER NOT NULL, ticket_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES nv_tenants(tenant_id))""",
    "CREATE INDEX IF NOT EXISTS idx_nv_tenants_admin_email ON nv_tenants(lower(admin_email))",
    "CREATE INDEX IF NOT EXISTS idx_nv_tenants_status_expiry ON nv_tenants(status, demo_expires_at)",
    """CREATE TRIGGER IF NOT EXISTS nv_ai_audit_no_update BEFORE UPDATE ON nv_ai_audit_logs
       BEGIN SELECT RAISE(ABORT, 'nv_ai_audit_logs is immutable'); END""",
    """CREATE TRIGGER IF NOT EXISTS nv_ai_audit_no_delete BEFORE DELETE ON nv_ai_audit_logs
       BEGIN SELECT RAISE(ABORT, 'nv_ai_audit_logs is immutable'); END""",
)
_SUPPORT_SCHEMA = (
    "CREATE INDEX IF NOT EXISTS idx_nv_support_tenant_created ON nv_support_tickets(tenant_slug, created_at DESC)",
    """CREATE TRIGGER IF NOT EXISTS nv_support_tenant_insert BEFORE INSERT ON nv_support_tickets
       WHEN NOT EXISTS (SELECT 1 FROM nv_tenants WHERE tenant_id = NEW.tenant_id AND slug = NEW.tenant_slug)
       BEGIN SELECT RAISE(ABORT, 'support ticket tenant mismatch'); END""",
    """CREATE TRIGGER IF NOT EXISTS nv_support_tenant_update BEFORE UPDATE OF tenant_id, tenant_slug ON nv_support_tickets
       WHEN NOT EXISTS (SELECT 1 FROM nv_tenants WHERE tenant_id = NEW.tenant_id AND slug = NEW.tenant_slug)
       BEGIN SELECT RAISE(ABORT, 'support ticket tenant mismatch'); END""",
)

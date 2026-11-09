"""Daily demo-expiry notification service for NexusVault tenants."""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.message import EmailMessage
from typing import Callable

from src.nexus_db_adapter import NexusDatabaseAdapter, TenantRow
from src.nexus_tenant_engine import NexusTenantLifecycleEngine, TenantStatus

logger = logging.getLogger(__name__)
EmailDispatcher = Callable[[str, str, str], None]


@dataclass(frozen=True)
class ExpiryNotificationResult:
    """Outcome of notification attempts for one tenant."""

    tenant_id: str
    days_remaining: int
    email_sent: bool
    portal_alert_created: bool
    errors: tuple[str, ...]


class DemoExpiryNotifier:
    """Scans unpaid demos due within five days and dispatches alerts."""

    def __init__(
        self,
        database: NexusDatabaseAdapter,
        engine: NexusTenantLifecycleEngine,
        *,
        email_dispatcher: EmailDispatcher | None = None,
    ) -> None:
        self.database = database
        self.engine = engine
        self._email_dispatcher = email_dispatcher or _send_expiry_email

    def run_expiry_scan(
        self, *, now: datetime | None = None
    ) -> list[ExpiryNotificationResult]:
        """Send an email and persist an in-portal alert for each due demo."""
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            raise ValueError("now must include a timezone.")
        current_time = current_time.astimezone(timezone.utc)
        tenants = self.database.list_tenants_for_expiry_scan(today=current_time)
        results: list[ExpiryNotificationResult] = []
        for tenant in tenants:
            results.append(self._notify_tenant(tenant, current_time))
        return results

    def _notify_tenant(
        self, tenant: TenantRow, current_time: datetime
    ) -> ExpiryNotificationResult:
        tenant_id = str(tenant["tenant_id"])
        expiration = _as_datetime(tenant.get("demo_expires_at"))
        if expiration is None:
            raise RuntimeError(f"Tenant {tenant_id!r} has no demo expiration.")
        days_remaining = (expiration.date() - current_time.date()).days
        errors: list[str] = []
        is_expired = expiration <= current_time
        if is_expired and tenant["status"] == TenantStatus.DEMO_ACTIVE.value:
            self.engine.expire_trial(tenant_id, now=current_time)

        message = (
            "URGENT: Your NexusVault demo access "
            + (
                "has expired. Access is restricted until commercial payment "
                "is acknowledged."
                if is_expired
                else f"expires in {days_remaining} day(s). "
                "Complete subscription payment before expiration to avoid "
                "restricted access."
            )
        )
        email_sent = False
        email = str(tenant.get("admin_email") or "").strip()
        try:
            self._email_dispatcher(
                email,
                "URGENT: NexusVault demo access expiry",
                message,
            )
            email_sent = True
        except Exception as exc:
            logger.exception("Expiry reminder email failed for tenant %s", tenant_id)
            errors.append(f"Email delivery failed: {exc}")

        alert_key = "expired" if is_expired else f"{days_remaining}-days"
        try:
            portal_alert_created = self.database.add_expiry_alert(
                tenant_id,
                alert_key=alert_key,
                message=message,
            )
        except Exception as exc:
            logger.exception("Portal expiry alert failed for tenant %s", tenant_id)
            portal_alert_created = False
            errors.append(f"Portal alert failed: {exc}")
        return ExpiryNotificationResult(
            tenant_id=tenant_id,
            days_remaining=days_remaining,
            email_sent=email_sent,
            portal_alert_created=portal_alert_created,
            errors=tuple(errors),
        )


def _send_expiry_email(recipient: str, subject: str, body: str) -> None:
    """Send via configured SMTP; report missing configuration as an error."""
    settings = {
        "server": os.environ.get("SMTP_SERVER", "").strip(),
        "port": os.environ.get("SMTP_PORT", "").strip(),
        "sender": os.environ.get("SENDER_EMAIL", "").strip(),
        "password": os.environ.get("SMTP_PASSWORD", "").strip(),
    }
    if not all(settings.values()):
        raise RuntimeError(
            "SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, and SMTP_PASSWORD are required."
        )
    if not recipient or "@" not in recipient:
        raise ValueError("Tenant admin email is missing or invalid.")
    try:
        port = int(settings["port"])
    except ValueError as exc:
        raise ValueError("SMTP_PORT must be an integer.") from exc

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings["sender"]
    message["To"] = recipient
    message.set_content(body)
    tls_context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(
            settings["server"], port, timeout=15, context=tls_context
        ) as server:
            server.login(settings["sender"], settings["password"])
            server.send_message(message)
    else:
        with smtplib.SMTP(settings["server"], port, timeout=15) as server:
            server.ehlo()
            server.starttls(context=tls_context)
            server.ehlo()
            server.login(settings["sender"], settings["password"])
            server.send_message(message)


def _as_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("Invalid persisted demo_expires_at value.") from exc
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def remaining_demo_days(expires_at: datetime, current_date: date) -> int:
    """Return date-based days remaining, consistent with the daily job policy."""
    if expires_at.tzinfo is None:
        raise ValueError("expires_at must include a timezone.")
    return (expires_at.astimezone(timezone.utc).date() - current_date).days


def main() -> int:
    """Run one scan; a scheduler must invoke this command daily."""
    logging.basicConfig(level=logging.INFO)
    database = NexusDatabaseAdapter()
    notifier = DemoExpiryNotifier(database, NexusTenantLifecycleEngine(database))
    results = notifier.run_expiry_scan()
    failures = sum(bool(result.errors) for result in results)
    logger.info("Scanned %d due demos; %d had delivery errors.", len(results), failures)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

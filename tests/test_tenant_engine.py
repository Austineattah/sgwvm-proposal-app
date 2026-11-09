from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.cron_expiry_notifier import DemoExpiryNotifier
from src.nexus_db_adapter import NexusDatabaseAdapter
from src.nexus_tenant_engine import (
    NexusTenantLifecycleEngine,
    ResumeDestination,
    TenantStatus,
)


@pytest.fixture
def tenant_system(tmp_path, monkeypatch):
    database = NexusDatabaseAdapter(database_path=tmp_path / "nexus_sovereign.db")
    engine = NexusTenantLifecycleEngine(
        database,
        lead_architect_email="augustine@example.gov",
    )
    suffixes = iter(
        ["7c6c24ae", "00000002", "00000003", "00000004", "00000005"]
    )
    monkeypatch.setattr(
        "src.nexus_db_adapter.secrets.token_hex", lambda _: next(suffixes)
    )
    return database, engine


def test_registration_generates_unique_tenant_slug(tenant_system):
    database, engine = tenant_system

    tenant = engine.register_tenant("Wise Ventures Ltd", "admin@wise.example")

    assert tenant["slug"] == "wiseventuresltd_7c6c24ae"
    assert tenant["status"] == TenantStatus.PENDING_ACTIVATION.value
    assert tenant["is_activated"] in (False, 0)
    assert database.lookup_tenant_by_slug(tenant["slug"])["tenant_id"] == tenant["tenant_id"]


@pytest.mark.parametrize(
    ("commence_now", "expected_status"),
    [
        (True, TenantStatus.PAYMENT_PENDING),
        (False, TenantStatus.DEMO_ACTIVE),
    ],
)
def test_onboarding_decisions_transition_state(
    tenant_system, commence_now, expected_status
):
    _, engine = tenant_system
    tenant = engine.register_tenant("Example Org", "admin@example.gov")

    updated = engine.choose_subscription(
        tenant["tenant_id"],
        commence_now=commence_now,
        now=datetime(2026, 11, 1, tzinfo=timezone.utc),
    )

    assert updated["status"] == expected_status.value
    if commence_now:
        assert updated["demo_expires_at"] is None
    else:
        assert updated["demo_expires_at"] == "2026-11-15 00:00:00+00:00"


def test_resume_login_resolves_by_email_and_slug(tenant_system):
    _, engine = tenant_system
    tenant = engine.register_tenant("Resume Org", "resume@example.gov")
    engine.choose_subscription(tenant["tenant_id"], commence_now=False)

    by_email = engine.resume_login("resume@example.gov")
    by_slug = engine.resume_login(tenant["slug"])

    assert by_email is not None
    assert by_slug is not None
    assert by_email.destination is ResumeDestination.TENANT_DASHBOARD
    assert by_slug.tenant["tenant_id"] == tenant["tenant_id"]


def test_resume_pending_payment_and_expired_route_to_checkout(tenant_system):
    _, engine = tenant_system
    payment = engine.register_tenant("Payment Org", "payment@example.gov")
    engine.choose_subscription(payment["tenant_id"], commence_now=True)

    expired = engine.register_tenant("Expired Org", "expired@example.gov")
    now = datetime.now(timezone.utc)
    engine.choose_subscription(
        expired["tenant_id"], commence_now=False, now=now - timedelta(days=20)
    )
    engine.expire_trial(expired["tenant_id"], now=now)

    assert (
        engine.resume_login("payment@example.gov").destination
        is ResumeDestination.COMMERCIAL_CHECKOUT
    )
    assert (
        engine.resume_login("expired@example.gov").destination
        is ResumeDestination.COMMERCIAL_CHECKOUT
    )


def test_manual_activation_override_requires_lead_architect(tenant_system):
    _, engine = tenant_system
    tenant = engine.register_tenant("Override Org", "override@example.gov")

    with pytest.raises(PermissionError):
        engine.manual_activation_override(
            tenant["tenant_id"],
            actor_name="Unauthorized User",
            actor_email="augustine@example.gov",
        )

    activated = engine.manual_activation_override(
        tenant["tenant_id"],
        actor_name="Augustine Attah",
        actor_email="augustine@example.gov",
    )

    assert activated["is_activated"] in (True, 1)
    assert activated["status"] == TenantStatus.SUBSCRIBED.value


def test_expiry_scan_sends_notifications_within_five_days(tenant_system):
    database, engine = tenant_system
    tenant = engine.register_tenant("Reminder Org", "reminder@example.gov")
    now = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)
    engine.choose_subscription(
        tenant["tenant_id"], commence_now=False, now=now
    )
    messages = []
    notifier = DemoExpiryNotifier(
        database,
        engine,
        email_dispatcher=lambda recipient, subject, body: messages.append(
            (recipient, subject, body)
        ),
    )

    results = notifier.run_expiry_scan(now=now + timedelta(days=10))

    assert len(results) == 1
    assert results[0].days_remaining == 4
    assert results[0].email_sent is True
    assert results[0].portal_alert_created is True
    assert messages[0][0] == "reminder@example.gov"
    assert "expires in 4 day(s)" in messages[0][2]


def test_five_calendar_day_boundary_and_same_day_expiration(tenant_system):
    database, engine = tenant_system
    tenant = engine.register_tenant("Boundary Org", "boundary@example.gov")
    start = datetime(2026, 11, 1, 23, tzinfo=timezone.utc)
    engine.choose_subscription(tenant["tenant_id"], commence_now=False, now=start)
    messages = []
    notifier = DemoExpiryNotifier(
        database, engine,
        email_dispatcher=lambda recipient, subject, body: messages.append(body),
    )

    results = notifier.run_expiry_scan(now=datetime(2026, 11, 10, 1, tzinfo=timezone.utc))
    assert len(results) == 1
    assert results[0].days_remaining == 5

    notifier.run_expiry_scan(now=datetime(2026, 11, 15, 1, tzinfo=timezone.utc))
    assert "expires in 0 day(s)" in messages[-1]
    assert database.get_tenant(tenant["tenant_id"])["status"] == "DEMO_ACTIVE"

    notifier.run_expiry_scan(now=datetime(2026, 11, 15, 23, tzinfo=timezone.utc))
    assert "has expired" in messages[-1]
    assert database.get_tenant(tenant["tenant_id"])["status"] == "EXPIRED"


def test_resume_expired_demo_routes_to_checkout_without_cron(tenant_system):
    _, engine = tenant_system
    tenant = engine.register_tenant("Expired Demo", "demo@example.gov")
    start = datetime(2026, 11, 1, tzinfo=timezone.utc)
    engine.choose_subscription(tenant["tenant_id"], commence_now=False, now=start)

    result = engine.resume_login(tenant["slug"], now=start + timedelta(days=14))

    assert result is not None
    assert result.destination is ResumeDestination.COMMERCIAL_CHECKOUT
    assert result.tenant["status"] == TenantStatus.EXPIRED.value


def test_ambiguous_email_requires_slug(tenant_system):
    _, engine = tenant_system
    first = engine.register_tenant("First", "shared@example.gov")
    second = engine.register_tenant("Second", "shared@example.gov")

    with pytest.raises(ValueError, match="multiple tenants"):
        engine.resume_login("shared@example.gov")
    assert engine.resume_login(first["slug"]).tenant["tenant_id"] == first["tenant_id"]
    assert engine.resume_login(second["slug"]).tenant["tenant_id"] == second["tenant_id"]


def test_generated_slug_fits_existing_portal_route(tenant_system):
    _, engine = tenant_system
    tenant = engine.register_tenant("A" * 100, "long-name@example.gov")
    assert len(tenant["slug"]) <= 62

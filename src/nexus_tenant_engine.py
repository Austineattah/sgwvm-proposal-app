"""Immutable tenant lifecycle transitions and account-resume routing."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from src.nexus_db_adapter import NexusDatabaseAdapter, TenantRow


class TenantStatus(str, Enum):
    """Persisted lifecycle states for an institutional tenant."""

    PENDING_ACTIVATION = "PENDING_ACTIVATION"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    DEMO_ACTIVE = "DEMO_ACTIVE"
    SUBSCRIBED = "SUBSCRIBED"
    EXPIRED = "EXPIRED"


class ResumeDestination(str, Enum):
    """Safe application destinations returned by the resume controller."""

    ACTIVATION_PENDING = "ACTIVATION_PENDING"
    COMMERCIAL_CHECKOUT = "COMMERCIAL_CHECKOUT"
    TENANT_DASHBOARD = "TENANT_DASHBOARD"


class InvalidTenantTransition(ValueError):
    """Raised when a requested lifecycle move is not permitted."""


@dataclass(frozen=True)
class TenantLifecycleState:
    """An immutable value representing one tenant's lifecycle state."""

    tenant_id: str
    status: TenantStatus
    is_activated: bool
    demo_days_assigned: int
    demo_expires_at: datetime | None


@dataclass(frozen=True)
class ResumeResult:
    """Account lookup result and the route allowed by its current status."""

    tenant: TenantRow
    destination: ResumeDestination


_TRANSITIONS: dict[TenantStatus, frozenset[TenantStatus]] = {
    TenantStatus.PENDING_ACTIVATION: frozenset(
        {TenantStatus.PAYMENT_PENDING, TenantStatus.DEMO_ACTIVE, TenantStatus.SUBSCRIBED}
    ),
    TenantStatus.PAYMENT_PENDING: frozenset(
        {TenantStatus.SUBSCRIBED, TenantStatus.EXPIRED}
    ),
    TenantStatus.DEMO_ACTIVE: frozenset(
        {TenantStatus.SUBSCRIBED, TenantStatus.EXPIRED}
    ),
    TenantStatus.SUBSCRIBED: frozenset({TenantStatus.EXPIRED}),
    TenantStatus.EXPIRED: frozenset({TenantStatus.SUBSCRIBED}),
}


def transition_state(
    state: TenantLifecycleState,
    target: TenantStatus,
    *,
    now: datetime | None = None,
) -> TenantLifecycleState:
    """Return a new valid state without mutating the supplied state."""
    if target not in _TRANSITIONS[state.status]:
        raise InvalidTenantTransition(
            f"Cannot transition tenant from {state.status.value} to {target.value}."
        )
    transition_time = now or datetime.now(timezone.utc)
    if transition_time.tzinfo is None:
        raise ValueError("now must include a timezone.")

    expires_at: datetime | None = None
    activated = False
    if target is TenantStatus.DEMO_ACTIVE:
        expires_at = transition_time.astimezone(timezone.utc) + timedelta(
            days=state.demo_days_assigned
        )
    elif target is TenantStatus.SUBSCRIBED:
        activated = True
    return TenantLifecycleState(
        tenant_id=state.tenant_id,
        status=target,
        is_activated=activated,
        demo_days_assigned=state.demo_days_assigned,
        demo_expires_at=expires_at,
    )


class NexusTenantLifecycleEngine:
    """Coordinates state transitions, persistence, and resume routing."""

    def __init__(
        self,
        database: NexusDatabaseAdapter,
        *,
        lead_architect_email: str | None = None,
    ) -> None:
        self.database = database
        self._lead_architect_email = (
            lead_architect_email or os.environ.get("NEXUS_LEAD_ARCHITECT_EMAIL", "")
        ).strip().casefold()

    def register_tenant(
        self,
        org_name: str,
        admin_email: str,
        *,
        demo_days_assigned: int = 14,
    ) -> TenantRow:
        """Create an onboarded account awaiting activation review."""
        return self.database.register_tenant(
            org_name,
            admin_email,
            demo_days_assigned=demo_days_assigned,
        )

    def choose_subscription(
        self,
        tenant_id: str,
        *,
        commence_now: bool,
        now: datetime | None = None,
    ) -> TenantRow:
        """Apply the onboarding YES (payment) or LATER (demo) decision."""
        current = self._load_state(tenant_id)
        target = (
            TenantStatus.PAYMENT_PENDING
            if commence_now
            else TenantStatus.DEMO_ACTIVE
        )
        new_state = transition_state(current, target, now=now)
        return self._persist_state(current, new_state)

    def confirm_payment(
        self, tenant_id: str, *, now: datetime | None = None
    ) -> TenantRow:
        """Activate a tenant after a trusted commercial payment callback."""
        current = self._load_state(tenant_id)
        new_state = transition_state(current, TenantStatus.SUBSCRIBED, now=now)
        return self._persist_state(current, new_state)

    def expire_trial(
        self, tenant_id: str, *, now: datetime | None = None
    ) -> TenantRow:
        """Expire a demo whose unpaid trial window has elapsed."""
        current = self._load_state(tenant_id)
        if current.status is not TenantStatus.DEMO_ACTIVE:
            raise InvalidTenantTransition("Only active demo tenants can expire.")
        expiration = current.demo_expires_at
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            raise ValueError("now must include a timezone.")
        if expiration is None or expiration > current_time:
            raise InvalidTenantTransition("The demo expiration time has not elapsed.")
        return self._persist_state(
            current, transition_state(current, TenantStatus.EXPIRED, now=current_time)
        )

    def manual_activation_override(
        self,
        tenant_id: str,
        *,
        actor_name: str,
        actor_email: str,
        grant: bool = True,
    ) -> TenantRow:
        """Grant or revoke access only for the configured lead architect."""
        self._authorize_lead_architect(actor_name, actor_email)
        current = self._load_state(tenant_id)
        if grant:
            if current.status is TenantStatus.SUBSCRIBED:
                return self.database.get_tenant(tenant_id) or self._missing(tenant_id)
            target = TenantStatus.SUBSCRIBED
        else:
            if current.status is TenantStatus.EXPIRED:
                return self.database.get_tenant(tenant_id) or self._missing(tenant_id)
            if current.status is not TenantStatus.SUBSCRIBED:
                raise InvalidTenantTransition(
                    "Access can only be revoked from a subscribed tenant."
                )
            target = TenantStatus.EXPIRED
        return self._persist_state(current, transition_state(current, target))

    def assign_demo_window(
        self, tenant_id: str, *, demo_days: int
    ) -> TenantRow:
        """Assign a future trial duration for a pending or active demo."""
        if demo_days < 1:
            raise ValueError("demo_days must be at least one.")
        current = self._load_state(tenant_id)
        if current.status not in (
            TenantStatus.PENDING_ACTIVATION,
            TenantStatus.DEMO_ACTIVE,
        ):
            raise InvalidTenantTransition(
                "A demo window can only be assigned before or during a demo."
            )
        expires_at = None
        if current.status is TenantStatus.DEMO_ACTIVE:
            expires_at = datetime.now(timezone.utc) + timedelta(days=demo_days)
        return self.database.transition_tenant(
            tenant_id,
            expected_status=current.status.value,
            status=current.status.value,
            is_activated=current.is_activated,
            demo_expires_at=expires_at,
            demo_days_assigned=demo_days,
        )

    def resume_login(
        self, email_or_slug: str, *, now: datetime | None = None
    ) -> ResumeResult | None:
        """Resolve a routing hint; callers must separately authenticate access."""
        if not email_or_slug or not email_or_slug.strip():
            raise ValueError("An account email or tenant slug is required.")
        identifier = email_or_slug.strip()
        tenant = (
            self.database.lookup_tenant_by_email(identifier)
            if "@" in identifier
            else self.database.lookup_tenant_by_slug(identifier)
        )
        if tenant is None:
            return None
        status = TenantStatus(str(tenant["status"]))
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            raise ValueError("now must include a timezone.")
        if status is TenantStatus.DEMO_ACTIVE:
            state = self._load_state(str(tenant["tenant_id"]))
            if state.demo_expires_at is None:
                raise RuntimeError("An active demo must have an expiration time.")
            if state.demo_expires_at <= current_time:
                tenant = self.expire_trial(state.tenant_id, now=current_time)
                status = TenantStatus.EXPIRED
        if status in (TenantStatus.PAYMENT_PENDING, TenantStatus.EXPIRED):
            destination = ResumeDestination.COMMERCIAL_CHECKOUT
        elif status in (TenantStatus.DEMO_ACTIVE, TenantStatus.SUBSCRIBED):
            destination = ResumeDestination.TENANT_DASHBOARD
        else:
            destination = ResumeDestination.ACTIVATION_PENDING
        return ResumeResult(tenant=tenant, destination=destination)

    def _authorize_lead_architect(self, actor_name: str, actor_email: str) -> None:
        if (
            actor_name.strip().casefold() != "augustine attah"
            or not self._lead_architect_email
            or actor_email.strip().casefold() != self._lead_architect_email
        ):
            raise PermissionError("Only the configured Lead Architect may override access.")

    def _load_state(self, tenant_id: str) -> TenantLifecycleState:
        row = self.database.get_tenant(tenant_id)
        if row is None:
            raise LookupError(f"Tenant {tenant_id!r} was not found.")
        try:
            status = TenantStatus(str(row["status"]))
        except ValueError as exc:
            raise RuntimeError("Tenant has an unsupported persisted lifecycle state.") from exc
        expiration = row.get("demo_expires_at")
        if isinstance(expiration, str):
            expiration = datetime.fromisoformat(expiration)
        if expiration is not None and expiration.tzinfo is None:
            expiration = expiration.replace(tzinfo=timezone.utc)
        return TenantLifecycleState(
            tenant_id=tenant_id,
            status=status,
            is_activated=bool(row["is_activated"]),
            demo_days_assigned=int(row["demo_days_assigned"]),
            demo_expires_at=expiration,
        )

    def _persist_state(
        self, previous: TenantLifecycleState, current: TenantLifecycleState
    ) -> TenantRow:
        return self.database.transition_tenant(
            previous.tenant_id,
            expected_status=previous.status.value,
            status=current.status.value,
            is_activated=current.is_activated,
            demo_expires_at=current.demo_expires_at,
        )

    @staticmethod
    def _missing(tenant_id: str) -> TenantRow:
        raise LookupError(f"Tenant {tenant_id!r} was not found.")

    def choose_subscribe(self, tenant_id: str) -> None:
        """Persist PAYMENT_PENDING for a tenant choosing immediate activation."""
        current = self._load_state(tenant_id)
        if current.status is TenantStatus.PENDING_ACTIVATION:
            self.choose_subscription(tenant_id, commence_now=True)

    def choose_demo(self, tenant_id: str) -> None:
        """Persist DEMO_ACTIVE and the 14-day evaluation window expiry."""
        current = self._load_state(tenant_id)
        if current.status is TenantStatus.PENDING_ACTIVATION:
            self.choose_subscription(tenant_id, commence_now=False)


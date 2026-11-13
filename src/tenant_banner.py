from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import html
from typing import Any

from src.nexus_tenant_engine import NexusTenantLifecycleEngine, TenantStatus
from src.tenant_checkout import render_tenant_checkout


def _coerce_status(raw: Any) -> TenantStatus:
    if isinstance(raw, TenantStatus):
        return raw
    try:
        return TenantStatus(str(raw).strip().upper())
    except ValueError:
        return TenantStatus.PENDING_ACTIVATION


def _parse_iso(ts: Any) -> datetime | None:
    if not ts:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _format_remaining(demo_expires_at: Any, now: datetime | None = None) -> str:
    expiry = _parse_iso(demo_expires_at)
    if expiry is None:
        return "14-day evaluation window active"
    current = now or datetime.now(timezone.utc)
    delta = expiry - current
    total_seconds = int(delta.total_seconds())
    if total_seconds <= 0:
        return "Evaluation window elapsed"
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    if days >= 1:
        return f"{days}d {hours}h remaining"
    minutes = (total_seconds % 3600) // 60
    return f"{hours}h {minutes}m remaining"


def render_tenant_banner(
    tenant: Mapping[str, Any],
    engine: NexusTenantLifecycleEngine,
) -> None:
    import streamlit as st

    tenant_id = str(tenant.get("tenant_id") or "").strip()
    if not tenant_id:
        st.warning("Tenant session context is missing an identifier.")
        return

    org_name = str(tenant.get("org_name") or "YOUR ORGANIZATION").strip()
    slug = str(tenant.get("slug") or "workspace").strip()
    admin_email = str(tenant.get("admin_email") or "").strip()
    status = _coerce_status(tenant.get("status"))

    # If user explicitly toggled the checkout view or is in PAYMENT_PENDING / EXPIRED with checkout active
    if st.session_state.get("show_tenant_checkout") or status == TenantStatus.PAYMENT_PENDING:
        render_tenant_checkout(tenant, engine)
        return

    if status == TenantStatus.PENDING_ACTIVATION:
        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg,#071324 0%,#0E243D 100%);
                        border:1.5px solid #38BDF8;border-radius:14px;padding:1.45rem 1.6rem;
                        margin:0.75rem 0 1.25rem 0;color:#F8FAFC;
                        box-shadow:0 12px 32px rgba(2,12,27,0.38);">
                <div style="font-size:0.75rem;letter-spacing:0.14em;font-weight:800;color:#38BDF8;text-transform:uppercase;margin-bottom:0.45rem;">
                    INSTITUTIONAL ONBOARDING CONFIRMATION &bull; {html.escape(org_name.upper())}
                </div>
                <div style="font-size:1.08rem;font-weight:800;line-height:1.5;letter-spacing:0.02em;color:#FFFFFF;text-transform:uppercase;">
                    YOUR ORGANIZATIONAL CREDENTIALS HAVE BEEN ONBOARDED. TO ACTIVATE YOUR ORGANIZATIONAL SLUG WORKSPACE WOULD YOU LIKE TO PROCEED WITH SUBSCRIPTION DETAILS?
                </div>
                <div style="margin-top:0.75rem;font-size:0.84rem;color:#CBD5E1;">
                    <strong>PROVISIONED WORKSPACE SLUG:</strong> <code>{html.escape(slug)}</code> &nbsp;|&nbsp;
                    <strong>ADMIN LOGIN:</strong> <code>{html.escape(admin_email)}</code>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_yes, col_later = st.columns(2)
        with col_yes:
            if st.button(
                "YES PROCEED",
                type="primary",
                use_container_width=True,
                key=f"btn_yes_proceed_{tenant_id}",
            ):
                try:
                    engine.choose_subscribe(tenant_id)
                    st.session_state["show_tenant_checkout"] = True
                    st.rerun()
                except Exception as exc:
                    st.error(f"Unable to launch subscription gateway: {exc}")

        with col_later:
            if st.button(
                "LATER",
                use_container_width=True,
                key=f"btn_later_{tenant_id}",
            ):
                try:
                    engine.choose_demo(tenant_id)
                    st.session_state["show_tenant_checkout"] = False
                    st.rerun()
                except Exception as exc:
                    st.error(f"Unable to defer activation: {exc}")
        return

    if status == TenantStatus.DEMO_ACTIVE:
        remaining = _format_remaining(tenant.get("demo_expires_at"))
        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg,#1E1B11 0%,#2E2614 100%);
                        border:1.5px solid #F59E0B;border-radius:14px;padding:1.45rem 1.6rem;
                        margin:0.75rem 0 1.25rem 0;color:#FEF3C7;
                        box-shadow:0 12px 32px rgba(24,18,5,0.35);">
                <div style="font-size:0.75rem;letter-spacing:0.14em;font-weight:800;color:#FBBF24;text-transform:uppercase;margin-bottom:0.45rem;">
                    WORKSPACE ACTIVATION DEFERRED &bull; {html.escape(org_name.upper())}
                </div>
                <div style="font-size:1.12rem;font-weight:800;line-height:1.5;letter-spacing:0.03em;color:#FFFFFF;text-transform:uppercase;">
                    YOUR ORGANIZATIONAL CREDENTIALS HAVE BEEN AWAITING ACTIVATION.
                </div>
                <div style="margin-top:0.8rem;font-size:0.85rem;color:#FDE68A;line-height:1.6;">
                    <strong>RETURNING TENANT LOGIN CREDENTIALS:</strong><br/>
                    &bull; <strong>Organizational Slug:</strong> <code>{html.escape(slug)}</code><br/>
                    &bull; <strong>Registered Admin Email:</strong> <code>{html.escape(admin_email)}</code><br/>
                    &bull; <strong>Sandbox Evaluation Status:</strong> {html.escape(remaining)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "PROCEED WITH SUBSCRIPTION DETAILS NOW",
            type="primary",
            key=f"btn_resume_sub_{tenant_id}",
        ):
            try:
                engine.choose_subscribe(tenant_id)
                st.session_state["show_tenant_checkout"] = True
                st.rerun()
            except Exception as exc:
                st.error(f"Unable to open subscription checkout: {exc}")
        return

    if status == TenantStatus.EXPIRED:
        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg,#2A0E14 0%,#3F141D 100%);
                        border:1.5px solid #F43F5E;border-radius:14px;padding:1.4rem 1.55rem;
                        margin:0.75rem 0 1.25rem 0;color:#FFE4E6;">
                <div style="font-size:0.75rem;letter-spacing:0.14em;font-weight:800;color:#FB7185;text-transform:uppercase;margin-bottom:0.4rem;">
                    EVALUATION WINDOW EXPIRED &bull; {html.escape(org_name.upper())}
                </div>
                <div style="font-size:1.05rem;font-weight:800;color:#FFFFFF;text-transform:uppercase;">
                    YOUR ORGANIZATIONAL CREDENTIALS REQUIRE SUBSCRIPTION ACTIVATION TO UNLOCK WORKSPACE SLUG <code>{html.escape(slug)}</code>.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "PROCEED TO SUBSCRIPTION GATEWAY",
            type="primary",
            key=f"btn_expired_sub_{tenant_id}",
        ):
            try:
                engine.choose_subscribe(tenant_id)
                st.session_state["show_tenant_checkout"] = True
                st.rerun()
            except Exception as exc:
                st.error(f"Unable to open subscription checkout: {exc}")
        return

    if status == TenantStatus.SUBSCRIBED:
        receipt = st.session_state.get("checkout_settlement_receipt") or {}
        receipt_note = ""
        if receipt:
            receipt_note = (
                f" &nbsp;|&nbsp; <strong>Settlement Ref:</strong> <code>{html.escape(str(receipt.get('reference', 'VERIFIED')))}</code>"
                f" &nbsp;|&nbsp; <strong>Tier:</strong> {html.escape(str(receipt.get('tier', 'Enterprise')))}"
            )
        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg,#06281E 0%,#0B3B2D 100%);
                        border:1.5px solid #10B981;border-radius:14px;padding:1.35rem 1.55rem;
                        margin:0.75rem 0 1.25rem 0;color:#ECFDF5;">
                <div style="font-size:0.75rem;letter-spacing:0.14em;font-weight:800;color:#34D399;text-transform:uppercase;margin-bottom:0.35rem;">
                    SUBSCRIBED &amp; ACTIVE SOVEREIGN WORKSPACE &bull; {html.escape(org_name.upper())}
                </div>
                <div style="font-size:1.02rem;font-weight:700;color:#FFFFFF;">
                    WORKSPACE SLUG <code>{html.escape(slug)}</code> IS FULLY ACTIVATED AND OPERATIONAL.{receipt_note}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

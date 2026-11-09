"""Streamlit status panel for the institutional onboarding lifecycle."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from src.nexus_tenant_engine import NexusTenantLifecycleEngine, TenantStatus

TENANT_ENDPOINT_BASE = (
    "https://nexusvault-proposal-enterprise-connect.streamlit.app/tenant/"
)


def render_tenant_banner(
    tenant: Mapping[str, Any],
    engine: NexusTenantLifecycleEngine,
) -> None:
    """Render the dynamic status panel and apply its onboarding decisions."""
    import streamlit as st

    tenant_id = str(tenant["tenant_id"])
    slug = str(tenant.get("slug") or tenant.get("tenant_slug") or "")
    status = TenantStatus(str(tenant["status"]))
    is_activated = bool(tenant.get("is_activated", False))

    st.header("NEXUSVAULT INSTITUTIONAL ONBOARDING")
    if is_activated:
        st.info("STATUS: INSTITUTIONAL ACCOUNT FULLY ACTIVATED & OPERATIONAL")
        endpoint = f"{TENANT_ENDPOINT_BASE}{quote(slug, safe='')}"
        st.markdown(f"[Open the production tenant portal]({endpoint})")
        with st.expander("Operational metadata"):
            st.write(f"Client Tenant Slug: {slug}")
            st.write(
                "Authorized Desk Operator: "
                f"{tenant.get('desk_operator') or 'Authorized Desk Officer'}"
            )
            st.write("Unsolicited Intake Module Status: Active")
            st.write(
                "Solicited Vendor Module Status: "
                f"{tenant.get('solicited_vendor_status') or 'Managed via Internal Admin Settings'}"
            )
        return

    if status is TenantStatus.PENDING_ACTIVATION:
        st.info(
            "YOUR INSTITUTIONAL CREDENTIALS HAVE BEEN ONBOARDED, "
            "AWAITING ACTIVATION SHORTLY."
        )
        st.write(
            "Would you want to commence subscription? Or would you wish "
            "to effect subscription later on??"
        )
        st.caption(
            f"Status: Pending Activation | Tenant Reference Slug: {slug}"
        )
        st.caption(
            "Public submissions become available after institutional activation."
        )
        commence, later = st.columns(2)
        if commence.button("[ YES, COMMENCE NOW ]", key=f"commence_{tenant_id}"):
            engine.choose_subscription(tenant_id, commence_now=True)
            st.rerun()
        if later.button("[ EFFECT LATER ]", key=f"later_{tenant_id}"):
            engine.choose_subscription(tenant_id, commence_now=False)
            st.rerun()
        return

    if status is TenantStatus.PAYMENT_PENDING:
        st.info("STATUS: SUBSCRIPTION COMMENCEMENT AWAITING PAYMENT VERIFICATION")
        st.caption(f"Tenant Reference Slug: {slug}")
        return

    if status is TenantStatus.DEMO_ACTIVE:
        expiration = tenant.get("demo_expires_at")
        st.info("STATUS: DEMO ACCESS ACTIVE")
        st.caption(f"Tenant Reference Slug: {slug}")
        if expiration:
            st.caption(f"Demo access expires: {expiration}")
        return

    st.info("STATUS: ACCESS EXPIRED — COMMERCIAL PAYMENT IS REQUIRED")
    st.caption(f"Tenant Reference Slug: {slug}")

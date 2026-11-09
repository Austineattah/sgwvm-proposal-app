"""Lead Architect-only Streamlit controls for tenant lifecycle management."""

from __future__ import annotations

import os

from src.nexus_db_adapter import NexusDatabaseAdapter
from src.nexus_tenant_engine import NexusTenantLifecycleEngine
from src.tenant_banner import TENANT_ENDPOINT_BASE


def render_developer_console(
    database: NexusDatabaseAdapter,
    engine: NexusTenantLifecycleEngine,
) -> None:
    """Render the activation and demo-window controls for Augustine Attah."""
    import streamlit as st

    expected_email = os.environ.get("NEXUS_LEAD_ARCHITECT_EMAIL", "").strip().casefold()
    actor_email = str(
        st.session_state.get("user_email")
        or st.session_state.get("admin_email")
        or ""
    ).strip().casefold()
    actor_name = str(st.session_state.get("user_name") or "").strip()
    if (
        not expected_email
        or actor_email != expected_email
        or actor_name.casefold() != "augustine attah"
    ):
        st.error(
            "Developer Console access is restricted to the configured "
            "Lead Architect / CEO."
        )
        return

    st.subheader("NexusVault Developer Console — Tenant Management")
    slug = st.text_input("Tenant reference slug", key="nexus_console_tenant_slug")
    if not slug.strip():
        st.info("Enter a tenant slug to manage its lifecycle.")
        return
    tenant = database.lookup_tenant_by_slug(slug.strip())
    if tenant is None:
        st.warning("No tenant matches that reference slug.")
        return

    st.write(f"Organization: {tenant['org_name']}")
    st.write(f"Status: {tenant['status']}")
    if bool(tenant["is_activated"]):
        if st.button("[ REVOKE ACCESS ]", key=f"revoke_{tenant['tenant_id']}"):
            engine.manual_activation_override(
                str(tenant["tenant_id"]),
                actor_name=actor_name,
                actor_email=actor_email,
                grant=False,
            )
            st.rerun()
    elif st.button("[ GRANT ACTIVATION ]", key=f"grant_{tenant['tenant_id']}"):
        activated = engine.manual_activation_override(
            str(tenant["tenant_id"]),
            actor_name=actor_name,
            actor_email=actor_email,
            grant=True,
        )
        st.success("Institutional access has been activated.")
        st.markdown(
            "[Open production tenant endpoint]("
            f"{TENANT_ENDPOINT_BASE}{activated['slug']})"
        )

    duration = st.number_input(
        "Demo window duration (days)",
        min_value=1,
        max_value=365,
        value=int(tenant["demo_days_assigned"]),
        step=1,
        key=f"demo_days_{tenant['tenant_id']}",
    )
    if st.button("Assign demo window", key=f"assign_demo_{tenant['tenant_id']}"):
        engine.assign_demo_window(str(tenant["tenant_id"]), demo_days=int(duration))
        st.success(f"Demo window assigned for {int(duration)} days.")
        st.rerun()

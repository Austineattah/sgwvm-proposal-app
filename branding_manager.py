import streamlit as st

def get_tenant_branding():
    """
    Retrieves dynamic white-label branding for the active subscribing tenant.
    Defaults to the subscriber's name or fallback if not yet set in onboarding.
    """
    tenant_name = st.session_state.get("subscribed_organization_name") or "Enterprise Proposal Intake Portal"
    tenant_logo = st.session_state.get("subscribed_organization_logo")
    
    return {
        "title": tenant_name,
        "page_title": f"{tenant_name} | Enterprise Intake Portal",
        "header": f"🏢 {tenant_name}",
        "export_header": f"==================================================\n{tenant_name.upper()} - EXECUTIVE PROPOSAL BRIEF\n=================================================="
    }

def render_portal_header():
    """Renders dynamic header and sidebar branding based on subscriber context."""
    branding = get_tenant_branding()
    
    # Update Page Config Header
    st.title(branding["header"])
    st.caption("Secure Executive Dispatch & Proposal Intake Engine")
    
    # Sidebar White-Label Branding
    with st.sidebar:
        st.markdown(f"### {branding['header']}")
        st.caption("Powered by SGWVM Enterprise Platform")
        st.divider()

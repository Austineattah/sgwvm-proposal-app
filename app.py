import streamlit as st

PRODUCTION_BASE_URL = "https://NexusVault-Proposal-Enterprise-Connect.streamlit.app"

import sqlite3

# Page Configuration
st.set_page_config(
    page_title="NEXUSVAULT Sovereign Enterprise Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
    <style>
    .main { background-color: #070f1a; color: #f8fafc; }
    .stButton>button { background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); color: white; border-radius: 8px; font-weight: 600; border: none; padding: 10px 20px; }
    .stButton>button:hover { background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%); }
    </style>
""", unsafe_allow_html=True)

# Initialize Database safely
try:
    import database as db
    db.init_db()
except Exception as e:
    st.error(f"Database initialization error: {e}")

# Read Query Parameters (Supports unified & legacy parameters)
query_params = st.query_params
_portal = query_params.get("portal") or query_params.get("mode", "")
_slug = query_params.get("slug") or query_params.get("client", "")
_vtype = query_params.get("type") or query_params.get("view", "unsolicited")

# Set session state defaults from URL parameters if present
if _portal and _slug:
    st.session_state["active_tenant_slug"] = _slug
    if _portal in ["tenant", "client"]:
        st.session_state["portal_mode"] = "tenant_login"
    elif _portal in ["vendor", "vendor_portal"]:
        st.session_state["portal_mode"] = "vendor_portal"
        st.session_state["vendor_intake_type"] = _vtype

mode = _portal
client_slug = _slug
view_mode = _vtype

# --- ROUTING DISPATCHER (UNIFIED ENTERPRISE ROUTER) ---
query_params = st.query_params
_portal = query_params.get("portal") or query_params.get("mode", "")
_slug = query_params.get("slug") or query_params.get("client", "")
_vtype = query_params.get("type") or query_params.get("view", "unsolicited")

if _portal == "dev" or _vtype in ["developer", "master_admin"]:
    try:
        import developer_console
        if hasattr(developer_console, "render_developer_master_console"):
            developer_console.render_developer_master_console()
        elif hasattr(developer_console, "render_developer_console"):
            developer_console.render_developer_console()
        elif hasattr(developer_console, "main"):
            developer_console.main()
        else:
            st.error("Developer console master entry function not found.")
    except Exception as e:
        st.error("Error executing developer console module:")
        st.exception(e)

elif _slug and (_portal in ["tenant", "client"] or _vtype == "admin"):
    try:
        import admin_portal
        if hasattr(admin_portal, "render_admin_dashboard"):
            admin_portal.render_admin_dashboard()
        elif hasattr(admin_portal, "main"):
            admin_portal.main()
        else:
            render_tenant_admin_console(_slug)
    except Exception as e:
        # Fallback render if module not standalone
        try:
            render_tenant_admin_console(_slug)
        except Exception as inner_e:
            st.error(f"Error loading tenant admin portal for {_slug}:")
            st.exception(inner_e)

elif _slug and (_portal in ["vendor", "vendor_portal"] or _vtype in ["unsolicited", "solicited"]):
    try:
        from sector_logic import render_unsolicited_vendor_portal, render_solicited_vendor_qr_clearance_gate
        if _vtype == "solicited":
            render_solicited_vendor_qr_clearance_gate(tenant_slug=_slug)
        else:
            render_unsolicited_vendor_portal(tenant_slug=_slug)
    except Exception as e:
        st.error(f"Error loading vendor portal for {_slug}:")
        st.exception(e)

else:
    # --- ROOT DEFAULT: FULL SECTOR ONBOARDING WIZARD ---
    try:
        from sector_logic import render_sector_onboarding_wizard
        render_sector_onboarding_wizard()
    except Exception as e:
        st.error("Error loading Sovereign Onboarding Gateway from sector_logic:")
        st.exception(e)

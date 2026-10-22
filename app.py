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

# Read Query Parameters
query_params = st.query_params
mode = query_params.get("mode", "")
client_slug = query_params.get("client", "")
view_mode = query_params.get("view", "")

# --- ROUTING DISPATCHER ---

if mode == "dev":
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

elif client_slug and view_mode == "admin":
    try:
        import admin_portal
        if hasattr(admin_portal, "render_admin_dashboard"):
            admin_portal.render_admin_dashboard()
        elif hasattr(admin_portal, "main"):
            admin_portal.main()
        else:
            st.success(f"Tenant Admin Portal active for: {client_slug}")
    except Exception as e:
        st.error(f"Error loading tenant admin portal for {client_slug}:")
        st.exception(e)

else:
    # --- ROOT DEFAULT: FULL SECTOR ONBOARDING WIZARD ---
    try:
        from sector_logic import render_sector_onboarding_wizard


        render_sector_onboarding_wizard()
    except Exception as e:
        st.error("Error loading Sovereign Onboarding Gateway from sector_logic:")
        st.exception(e)

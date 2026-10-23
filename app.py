import streamlit as st
import sqlite3
import os

PRODUCTION_BASE_URL = "https://NexusVault-Proposal-Enterprise-Connect.streamlit.app"

st.set_page_config(
    page_title="NEXUSVAULT Sovereign Enterprise Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #070f1a; color: #f8fafc; }
    .stButton>button { background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); color: white; border-radius: 8px; font-weight: 600; border: none; padding: 10px 20px; }
    .stButton>button:hover { background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%); }
    </style>
""", unsafe_allow_html=True)

try:
    import database as db
    db.init_db()
except Exception as e:
    st.error(f"Database initialization error: {e}")

from sector_logic import (
    render_tenant_admin_console,
    render_vendor_proposal_submission_portal,
    render_master_developer_console,
    render_sector_onboarding_wizard
)

query_params = st.query_params
client_slug = query_params.get("client", "")
view_type = query_params.get("view", "")
mode = query_params.get("mode", "")

def diagnose_and_render_tenant(slug, is_admin=False):
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='proposals';")
        if not cursor.fetchone():
            st.error("🚨 **Diagnostic Alert:** The 'proposals' database table does not exist. Please run database migration.")
            conn.close()
            return
            
        cursor.execute("SELECT client_slug, client_name FROM proposals WHERE client_slug = ?", (slug,))
        tenant = cursor.fetchone()
        conn.close()
        
        if not tenant:
            st.warning(f"⚠️ **Diagnostic Notice:** Tenant slug **'{slug}'** was not found in the active database directory.")
            st.info("💡 **How to resolve:** Use the Master Developer Console or Onboarding Wizard to register this tenant slug before accessing its portal.")
            if st.button("🚀 Launch Onboarding Wizard to Register Tenant"):
                st.query_params.clear()
                st.rerun()
            return

        if is_admin:
            render_tenant_admin_console(slug)
        else:
            render_vendor_proposal_submission_portal(slug)
            
    except Exception as e:
        st.error(f"🚨 **Diagnostic Runtime Error:** {e}")
        st.exception(e)

if mode == "dev":
    try:
        import developer_console
        if hasattr(developer_console, "render_developer_master_console"):
            developer_console.render_developer_master_console()
        elif hasattr(developer_console, "main"):
            developer_console.main()
        else:
            st.error("Developer console master entry function not found.")
    except Exception as e:
        st.error("Error executing developer console module:")
        st.exception(e)

elif client_slug:
    if view_type == "admin":
        diagnose_and_render_tenant(client_slug, is_admin=True)
    else:
        diagnose_and_render_tenant(client_slug, is_admin=False)

elif view_type in ["onboarding", "developer", "master_admin"]:
    try:
        render_master_developer_console()
    except Exception as e:
        st.error("Error loading master developer console:")
        st.exception(e)

else:
    try:
        render_sector_onboarding_wizard()
    except Exception as e:
        st.error("Error loading Sovereign Onboarding Gateway:")
        st.exception(e)

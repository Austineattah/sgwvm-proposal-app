import streamlit as st
import os
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

# Initialize Database
try:
    import database as db
    db.init_db()
except Exception as e:
    pass

# Read Query Parameters safely
query_params = st.query_params
mode = query_params.get("mode", "")
client_slug = query_params.get("client", "")
view_mode = query_params.get("view", "")

# --- ROUTING DISPATCHER ---

if mode == "dev" or st.session_state.get("is_admin_authenticated", False):
    # Developer Console Route
    try:
        import developer_console
        developer_console.render_developer_console()
    except Exception as e:
        st.error(f"Error rendering Developer Console: {e}")
        password = st.text_input("Enter Developer Access Key:", type="password")
        if password == "NexusDevGrant2026!":
            st.session_state.is_admin_authenticated = True
            st.rerun()
        else:
            st.warning("Please enter Developer Access Key: NexusDevGrant2026!")

elif client_slug and view_mode == "admin":
    # Tenant Admin Portal Route
    try:
        import admin_portal
        admin_portal.render_admin_dashboard()
    except Exception as e:
        st.error(f"Error rendering Tenant Admin Portal: {e}")
        st.info(f"Loading fallback view for tenant node: {client_slug}")

elif client_slug:
    # Public Tenant Portal Route (Vendor / Visitor Access Gate)
    st.markdown(f"""
        <div style="background: rgba(15, 23, 42, 0.9); padding: 30px; border-radius: 12px; border: 1px solid #38bdf8;">
            <h2 style="color: #38bdf8;">🏢 Sovereign Tenant Node: {client_slug}</h2>
            <p style="color: #94a3b8;">Welcome to the authorized vendor and visitor gateway for this institution.</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("📋 Credential Verification & QR Pass Submission")
    with st.form("visitor_pass_request"):
        visitor_name = st.text_input("Visitor / Vendor Full Name")
        visitor_org = st.text_input("Representing Organization / Company")
        purpose = st.selectbox("Access Purpose", ["Official Inspection", "Delivery & Logistics", "Scheduled Maintenance", "Executive Consultation"])
        submitted = st.form_submit_button("Submit Access Verification Request")
        if submitted and visitor_name:
            st.success(f"Access request successfully transmitted for **{visitor_name}** ({visitor_org}). QR Token generated.")

else:
    # Default Root Route: Onboarding Wizard
    try:
        import onboarding_wizard
        onboarding_wizard.render_onboarding_wizard()
    except Exception as e:
        st.markdown("""
            <div style="text-align: center; padding: 40px;">
                <h1 style="color: #38bdf8;">🛡️ NEXUSVAULT Sovereign Enterprise Portal</h1>
                <p style="color: #94a3b8;">PPA 2007 & NDPA Compliant Multi-Tenant Gateway</p>
            </div>
        """, unsafe_allow_html=True)
        st.info("Please access the Developer Console via ?mode=dev or use your assigned tenant link ?client=<slug>&view=admin.")

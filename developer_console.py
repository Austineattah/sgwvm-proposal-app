import streamlit as st
import database as db

def render_developer_master_console():
    st.markdown("<div class='section-hdr'>🔑 Master Developer & SaaS Platform Administrator Console</div>", unsafe_allow_html=True)
    st.info("Authorized Platform Owner Workspace: Monitor client deployments, manage enterprise licenses, activate pending organizations, or suspend accounts.")

    # Master Password Gate for Developer Admin
    if "dev_master_logged_in" not in st.session_state:
        st.session_state["dev_master_logged_in"] = False

    if not st.session_state["dev_master_logged_in"]:
        with st.form("dev_master_login_form"):
            st.markdown("#### 🔒 Developer Credentials Verification")
            dev_pass = st.text_input("Enter Master Developer Key", type="password", placeholder="Enter key...")
            btn_login = st.form_submit_button("Authenticate Developer Session", use_container_width=True)

            if btn_login:
                if dev_pass == "NexusDevGrant2026!":
                    st.session_state["dev_master_logged_in"] = True
                    st.success("✅ Developer Session Authenticated!")
                    st.rerun()
                else:
                    st.error("❌ Invalid Developer Credentials.")
        return

    # Once authenticated, render dashboard metrics
    st.markdown("---")
    
    # Active Client Settings in DB
    current_status = db.get_setting("node_approved", "False")
    entity_name = st.session_state.get("corp_name", "Unconfigured Enterprise Node")
    entity_type = st.session_state.get("entity_type", "Public MDA / Directorate")
    sub_tier = st.session_state.get("sub_package", "Sovereign Enterprise Tier")
    corp_email = st.session_state.get("corp_email", "admin@entity.gov.ng")

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Deployed Nodes", "1 Node")
    with col_m2:
        st.metric("Node Status", "ACTIVE" if current_status == "True" else "PENDING / SUSPENDED")
    with col_m3:
        st.metric("SaaS Tier", "Sovereign Tier")
    with col_m4:
        st.metric("Cybersecurity Shield", "ACTIVE (NITDA)")

    st.markdown("---")
    st.markdown("### 🏢 Onboarded SaaS Client Directory & License Control")

    # Display Client Node Details Card
    st.markdown(f"""
        <div style="background-color: rgba(15, 23, 42, 0.9); border: 2px solid #1d4ed8; border-radius: 10px; padding: 20px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 style="color: #ffffff; margin: 0; font-size: 18px;">🏢 {entity_name}</h3>
                <span style="background-color: {'#059669' if current_status == 'True' else '#dc2626'}; color: #ffffff; padding: 4px 12px; border-radius: 6px; font-weight: 800; font-size: 12px;">
                    {'NODE ACTIVE' if current_status == 'True' else 'NODE PENDING / SUSPENDED'}
                </span>
            </div>
            <p style="color: #94a3b8; font-size: 13px; margin: 8px 0;"><b>Scope:</b> {entity_type} | <b>Tier:</b> {sub_tier}</p>
            <p style="color: #cbd5e1; font-size: 13px; margin: 2px 0;"><b>Dispatch Email:</b> {corp_email}</p>
        </div>
    """, unsafe_allow_html=True)

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🟢 ACTIVATE CLIENT NODE", use_container_width=True):
            db.set_setting("node_approved", "True")
            st.session_state["developer_access_granted"] = True
            st.session_state["portal_initialized"] = True
            db.log_event("Developer Console", "NODE_ACTIVATED", "SYSTEM", f"Node activated for {entity_name}")
            st.success(f"✅ Workspace Node for '{entity_name}' is now ACTIVE!")
            st.rerun()

    with col_btn2:
        if st.button("🔴 SUSPEND / DEACTIVATE CLIENT NODE", use_container_width=True):
            db.set_setting("node_approved", "False")
            st.session_state["developer_access_granted"] = False
            st.session_state["portal_initialized"] = False
            db.log_event("Developer Console", "NODE_SUSPENDED", "SYSTEM", f"Node suspended for {entity_name}")
            st.warning(f"⚠️ Workspace Node for '{entity_name}' has been SUSPENDED!")
            st.rerun()

    st.markdown("---")
    if st.button("🔒 Logout Developer Admin Session"):
        st.session_state["dev_master_logged_in"] = False
        st.rerun()
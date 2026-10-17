import streamlit as st
import database as db

def render_developer_master_console():
    st.markdown("<div class='section-hdr'>🔑 Master Developer & SaaS Platform Administrator Console</div>", unsafe_allow_html=True)
    st.info("Central Multi-Tenant Management Hub: Monitor tenant subscriptions, identify locked-out nodes, reassign passwords, and generate unique newspaper publication links.")

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

    st.markdown("---")
    
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("➕ Register New Client / Launch Onboarding Wizard", use_container_width=True):
            st.session_state["portal_initialized"] = False
            st.session_state["onboarding_submitted"] = False
            st.session_state["portal_mode"] = "onboarding_wizard"
            st.rerun()
    with col_nav2:
        if st.button("⬅️ Return to Onboarding Selector", use_container_width=True):
            st.session_state["portal_mode"] = "onboarding_wizard"
            st.rerun()

    st.markdown("---")
    st.markdown("### 🏢 Multi-Tenant Subscribed Client Directory & Security Lockout Monitor")

    clients = db.get_all_clients()
    if len(clients) == 0:
        st.info("ℹ️ No tenant clients registered in database yet.")
    else:
        for client in clients:
            is_active = client["is_approved"] == "True"
            is_locked_out = client.get("lockout_status", "False") == "True"
            client_url = f"https://nexusvault.gov.ng/?client={client['client_slug']}"

            status_badge = "CLIENT ACTIVE" if is_active else "PENDING ACTIVATION"
            badge_color = "#059669"
            if is_locked_out:
                status_badge = "🚨 LOCKED OUT (3/3 ATTEMPTS)"
                badge_color = "#dc2626"

            st.markdown(f"""
                <div style="background: rgba(15, 23, 42, 0.85); border: 2px solid {badge_color}; border-radius: 12px; padding: 20px; margin-bottom: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="color: #ffffff; margin: 0; font-size: 18px;">🏢 {client['corp_name']}</h3>
                        <span style="background-color: {badge_color}; color: #ffffff; padding: 4px 12px; border-radius: 6px; font-weight: 800; font-size: 11px;">
                            {status_badge}
                        </span>
                    </div>
                    <p style="color: #94a3b8; font-size: 13px; margin: 6px 0;"><b>Scope:</b> {client['entity_type']} | <b>Tier:</b> {client['sub_package']}</p>
                    <p style="color: #cbd5e1; font-size: 13px; margin: 2px 0;"><b>Admin Email:</b> {client['admin_email']} | <b>Current Admin Pass:</b> <code>{client.get('client_admin_pass', 'NexusExec2026!')}</code></p>
                    <p style="color: #38bdf8; font-size: 13px; margin: 6px 0;"><b>Unique Public Tender Link:</b> <code>{client_url}</code></p>
                </div>
            """, unsafe_allow_html=True)

            # Developer Password Reset & Unlock Controls for this Client
            with st.expander(f"⚙️ Manage Security & Password Reassignment: {client['corp_name']}"):
                with st.form(f"reset_client_form_{client['client_id']}"):
                    new_c_pass = st.text_input("Assign New Password / Executive Key", value="NexusExec2026!", type="password")
                    btn_reset = st.form_submit_button("🔄 Reassign Password & Unlock Node", use_container_width=True)

                    if btn_reset:
                        db.reset_client_password(client['client_id'], new_c_pass)
                        st.success(f"✅ Password reassigned and lockout lifted for '{client['corp_name']}'!")
                        st.rerun()

            col_c1, col_c2 = st.columns(2)
            with col_c1:
                if not is_active:
                    if st.button(f"🟢 Activate Client Node", key=f"act_{client['client_id']}"):
                        db.update_client_approval(client['client_id'], "True")
                        st.success(f"✅ Client activated!")
                        st.rerun()
                else:
                    if st.button(f"🔴 Suspend Client Node", key=f"susp_{client['client_id']}"):
                        db.update_client_approval(client['client_id'], "False")
                        st.warning(f"⚠️ Client suspended.")
                        st.rerun()
            with col_c2:
                if is_locked_out:
                    if st.button(f"🔓 Clear Lockout Only", key=f"unlock_{client['client_id']}"):
                        db.update_client_lockout(client['client_id'], "False")
                        st.success(f"✅ Lockout cleared.")
                        st.rerun()

    st.markdown("---")
    if st.button("🔒 Logout Developer Admin Session"):
        st.session_state["dev_master_logged_in"] = False
        st.rerun()
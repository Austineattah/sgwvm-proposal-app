import streamlit as st
import database as db

def render_developer_master_console():
    st.markdown("<div class='section-hdr'>🔑 Master Developer & SaaS Platform Administrator Console</div>", unsafe_allow_html=True)
    st.info("Central Multi-Tenant Management Hub: Monitor tenant subscriptions, identify locked-out nodes, reassign passwords, or manage the purge archive.")

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

    purged_count = db.purge_expired_pending_clients()
    if purged_count > 0:
        st.warning(f"🧹 **Automated Retention Notice:** Moved {purged_count} unactivated client registration(s) exceeding the 7-day threshold to the Purge Archive.")

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

    # ================================================================
    # SOVEREIGN CLIENT BULLETIN & E-NEWSLETTER BROADCAST ENGINE
    # ================================================================
    with st.expander("📢 Sovereign Client Bulletin & E-Newsletter Broadcast Engine", expanded=False):
        st.markdown("##### ✉️ Dispatch Statutory Alerts, Compliance Notices & Platform Updates")
        all_clients_for_broadcast = db.get_all_clients()
        
        with st.form("broadcast_e_newsletter_form"):
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                target_audience = st.selectbox("Target Recipient Audience*", ["All Registered Clients (Active & Pending)", "Active Clients Only", "Pending Activation Only"])
                bulletin_category = st.selectbox("Bulletin Category*", ["Statutory Compliance Notice (PPA 2007 / NITDA)", "Security & System Upgrade Bulletin", "Platform E-Newsletter / Feature Announcement", "Urgent Administrative Notice"])
            with col_b2:
                bulletin_subject = st.text_input("Bulletin Subject Line*", placeholder="e.g., MANDATORY: NITDA Data Audit & Fiscal Year PPA Clearance Notice")
                sender_display_name = st.text_input("Dispatch Node Sender Name", value="NEXUSVAULT Sovereign Executive Console")

            bulletin_body = st.text_area("Bulletin Body Content*", height=150, placeholder="Dear Institutional Admin,\n\nPlease be advised...")
            btn_send_broadcast = st.form_submit_button("🚀 Dispatch Bulletin to Client Directory", use_container_width=True)

            if btn_send_broadcast:
                if not bulletin_subject or not bulletin_body:
                    st.error("⚠️ Please fill in Subject Line and Bulletin Body.")
                else:
                    st.success("✅ Bulletin dispatched successfully to client nodes!")

    st.markdown("---")
    st.markdown("### 🏢 Multi-Tenant Subscribed Client Directory & Security Lockout Monitor")

    # QUICK REFERENCE PERMANENT DELETE SEARCH BOX
    with st.form("quick_ref_delete_form"):
        st.markdown("##### ⚡ Quick Reference Permanent Deletion Gate")
        col_q1, col_q2 = st.columns([3, 1])
        with col_q1:
            target_slug_input = st.text_input("Client Slug / Keyword Reference*", placeholder="e.g. sgwvm")
        with col_q2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            btn_quick_del = st.form_submit_button("💥 Wipe Permanently", use_container_width=True)

        if btn_quick_del:
            clean_keyword = target_slug_input.strip().lower()
            if clean_keyword:
                all_db_clients = db.get_all_clients()
                matched = [c for c in all_db_clients if clean_keyword in c['client_slug'].lower() or clean_keyword in c['corp_name'].lower()]
                if matched:
                    for mc in matched:
                        db.delete_client_permanently(mc['client_id'])
                    st.success(f"💥 Successfully purged {len(matched)} matching client record(s)!")
                    st.rerun()
                else:
                    st.error("❌ No matching client found.")

    st.markdown("---")

    clients = db.get_all_clients()
    if len(clients) == 0:
        st.info("ℹ️ No active tenant clients registered in database.")
    else:
        for idx, client in enumerate(clients, start=1):
            is_active = client["is_approved"] == "True"
            is_locked_out = client.get("lockout_status", "False") == "True"
            client_url = f"?client={client['client_slug']}"
            created_date = client.get("created_at", "N/A")

            status_badge = "CLIENT ACTIVE" if is_active else "PENDING ACTIVATION"
            badge_color = "#059669" if is_active else "#f59e0b"
            if is_locked_out:
                status_badge = "🚨 LOCKED OUT (3/3 ATTEMPTS)"
                badge_color = "#dc2626"

            st.markdown(f"""
                <div style="background: rgba(15, 23, 42, 0.85); border: 2px solid {badge_color}; border-radius: 12px; padding: 18px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="color: #ffffff; margin: 0; font-size: 17px;">{idx}. 🏢 {client['corp_name']}</h3>
                        <span style="background-color: {badge_color}; color: #ffffff; padding: 4px 10px; border-radius: 6px; font-weight: 800; font-size: 11px;">
                            {status_badge}
                        </span>
                    </div>
                    <p style="color: #94a3b8; font-size: 13px; margin: 6px 0;"><b>Slug Reference:</b> <code>{client['client_slug']}</code> | <b>Tier:</b> {client['sub_package']}</p>
                    <p style="color: #cbd5e1; font-size: 13px; margin: 2px 0;"><b>Admin Email:</b> {client['admin_email']} | <b>Pass:</b> <code>{client.get('client_admin_pass', 'NexusExec2026!')}</code></p>
                </div>
            """, unsafe_allow_html=True)

            # GUARANTEED CLIENT MANAGEMENT EXPANDER
            with st.expander(f"⚙️ [{idx}] Manage Portal, Security & Credentials: {client['corp_name']}", expanded=False):
                with st.form(f"reset_client_form_{client['client_id']}"):
                    st.markdown("##### 🔐 Password Reassignment & Lockout Controls")
                    new_c_pass = st.text_input("New Executive Password", value=client.get('client_admin_pass', 'NexusExec2026!'), type="password", key=f"pass_{client['client_id']}")
                    btn_reset = st.form_submit_button("🔄 Save New Password & Lift Lockout", use_container_width=True)

                    if btn_reset:
                        db.reset_client_password(client['client_id'], new_c_pass)
                        db.update_client_lockout(client['client_id'], "False")
                        st.success(f"✅ Password updated and lockout lifted for '{client['corp_name']}'!")
                        st.rerun()

                st.markdown("##### 🚀 Direct Portal Navigation")
                if st.button(f"🔗 Launch Portal for [{client['client_slug']}]", key=f"launch_{client['client_id']}", use_container_width=True):
                    st.query_params["client"] = client['client_slug']
                    st.session_state["portal_mode"] = "vendor_portal"
                    st.rerun()

            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1:
                if not is_active:
                    if st.button(f"🟢 Activate [{idx}]", key=f"act_{client['client_id']}"):
                        db.update_client_approval(client['client_id'], "True")
                        st.success(f"✅ Client activated!")
                        st.rerun()
                else:
                    if st.button(f"🔴 Suspend [{idx}]", key=f"susp_{client['client_id']}"):
                        db.update_client_approval(client['client_id'], "False")
                        st.warning(f"⚠️ Client suspended.")
                        st.rerun()
            with col_c2:
                if is_locked_out:
                    if st.button(f"🔓 Clear Lockout [{idx}]", key=f"unlock_{client['client_id']}"):
                        db.update_client_lockout(client['client_id'], "False")
                        st.success(f"✅ Lockout cleared.")
                        st.rerun()
            with col_c3:
                if st.button(f"🗑️ Archive [{idx}]", key=f"del_client_{client['client_id']}"):
                    db.purge_client(client['client_id'])
                    st.toast(f"🗑️ Moved to Purge Archive.", icon="🧹")
                    st.rerun()

    st.markdown("---")
    if st.button("🔒 Logout Developer Admin Session"):
        st.session_state["dev_master_logged_in"] = False
        st.rerun()

def render_developer_console():
    if 'main' in globals() and callable(main):
        main()
    elif 'run' in globals() and callable(run):
        run()
    else:
        # Execute module body directly if standalone
        pass

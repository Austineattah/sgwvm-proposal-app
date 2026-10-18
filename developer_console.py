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

    # Execute 7-Day Expiry Purge Script upon loading console
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
    st.markdown("### 🏢 Multi-Tenant Subscribed Client Directory & Security Lockout Monitor")

    # ================================================================
    # QUICK REFERENCE PERMANENT DELETE SEARCH BOX
    # ================================================================
    with st.form("quick_ref_delete_form"):
        st.markdown("##### ⚡ Quick Reference Permanent Deletion Gate")
        st.caption("Type a client slug or corporate name keyword (e.g. 'sgwvm') to instantly purge or wipe them.")
        col_q1, col_q2 = st.columns([3, 1])
        with col_q1:
            target_slug_input = st.text_input("Client Slug / Keyword Reference*", placeholder="e.g. sgwvm or sgwvm_837261")
        with col_q2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            btn_quick_del = st.form_submit_button("💥 Wipe Permanently", use_container_width=True)

        if btn_quick_del:
            clean_keyword = target_slug_input.strip().lower()
            if not clean_keyword:
                st.error("⚠️ Please enter a valid client slug or keyword.")
            else:
                all_db_clients = db.get_all_clients()
                matched = [c for c in all_db_clients if clean_keyword in c['client_slug'].lower() or clean_keyword in c['corp_name'].lower()]
                if matched:
                    for mc in matched:
                        db.delete_client_permanently(mc['client_id'])
                    st.success(f"💥 Successfully purged {len(matched)} matching client record(s) based on reference '{target_slug_input}'!")
                    st.rerun()
                else:
                    st.error(f"❌ No matching client found for reference '{target_slug_input}'. Check slug spelling.")

    st.markdown("---")

    clients = db.get_all_clients()
    if len(clients) == 0:
        st.info("ℹ️ No active tenant clients registered in database.")
    else:
        for idx, client in enumerate(clients, start=1):
            is_active = client["is_approved"] == "True"
            is_locked_out = client.get("lockout_status", "False") == "True"
            client_url = f"https://nexusvault.gov.ng/?client={client['client_slug']}"
            created_date = client.get("created_at", "N/A")

            status_badge = "CLIENT ACTIVE" if is_active else "PENDING ACTIVATION"
            badge_color = "#059669"
            if is_locked_out:
                status_badge = "🚨 LOCKED OUT (3/3 ATTEMPTS)"
                badge_color = "#dc2626"

            st.markdown(f"""
                <div style="background: rgba(15, 23, 42, 0.85); border: 2px solid {badge_color}; border-radius: 12px; padding: 20px; margin-bottom: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="color: #ffffff; margin: 0; font-size: 18px;">{idx}. 🏢 {client['corp_name']}</h3>
                        <span style="background-color: {badge_color}; color: #ffffff; padding: 4px 12px; border-radius: 6px; font-weight: 800; font-size: 11px;">
                            {status_badge}
                        </span>
                    </div>
                    <p style="color: #94a3b8; font-size: 13px; margin: 6px 0;"><b>Slug Reference:</b> <code>{client['client_slug']}</code> | <b>Scope:</b> {client['entity_type']} | <b>Tier:</b> {client['sub_package']} | <b>Registered:</b> {created_date}</p>
                    <p style="color: #cbd5e1; font-size: 13px; margin: 2px 0;"><b>Admin Email:</b> {client['admin_email']} | <b>Current Admin Pass:</b> <code>{client.get('client_admin_pass', 'NexusExec2026!')}</code></p>
                    <p style="color: #38bdf8; font-size: 13px; margin: 6px 0;"><b>Unique Public Tender Link:</b> <code>{client_url}</code></p>
                </div>
            """, unsafe_allow_html=True)

            with st.expander(f"⚙️ [{idx}] Manage Security & Password Reassignment: {client['corp_name']}"):
                with st.form(f"reset_client_form_{client['client_id']}"):
                    new_c_pass = st.text_input("Assign New Password / Executive Key", value="NexusExec2026!", type="password")
                    btn_reset = st.form_submit_button("🔄 Reassign Password & Unlock Node", use_container_width=True)

                    if btn_reset:
                        db.reset_client_password(client['client_id'], new_c_pass)
                        st.success(f"✅ Password reassigned and lockout lifted for '{client['corp_name']}'!")
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
                if st.button(f"🗑️ Archive / Soft-Purge [{idx}]", key=f"del_client_{client['client_id']}"):
                    db.purge_client(client['client_id'])
                    st.toast(f"🗑️ Moved '{client['corp_name']}' to Purge Archive.", icon="🧹")
                    st.rerun()

    # ================================================================
    # PURGE ARCHIVE / TRASH BIN (RESTORE CLIENTS SECTION)
    # ================================================================
    st.markdown("---")
    st.markdown("### 🗑️ Purge Archive & Trash Bin (Restore Mistakenly Purged Clients)")
    
    purged_clients = db.get_purged_clients()
    if len(purged_clients) == 0:
        st.info("ℹ️ Purge Archive is empty. No purged records found.")
    else:
        st.warning(f"⚠️ Found {len(purged_clients)} client record(s) in the archive. You can restore them at any time.")
        for p_idx, p_client in enumerate(purged_clients, start=1):
            st.markdown(f"""
                <div style="background: rgba(127, 29, 29, 0.3); border: 2px dashed #ef4444; border-radius: 12px; padding: 18px; margin-bottom: 14px;">
                    <h4 style="color: #fca5a5; margin: 0 0 6px 0;">🗑️ [{p_idx}] [Archived Slug: {p_client['client_slug']}] {p_client['corp_name']}</h4>
                    <p style="color: #94a3b8; font-size: 13px; margin: 2px 0;"><b>Scope:</b> {p_client['entity_type']} | <b>Admin Email:</b> {p_client['admin_email']}</p>
                </div>
            """, unsafe_allow_html=True)
            
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                if st.button(f"🔄 Restore Client Node [{p_idx}]", key=f"restore_{p_client['client_id']}"):
                    db.restore_client(p_client['client_id'])
                    st.success(f"✅ Successfully restored '{p_client['corp_name']}' back to active directory!")
                    st.rerun()
            with col_r2:
                if st.button(f"❌ Delete Permanently [{p_idx}]", key=f"perm_del_{p_client['client_id']}"):
                    db.delete_client_permanently(p_client['client_id'])
                    st.error(f"💥 Permanently deleted '{p_client['corp_name']}' from database.")
                    st.rerun()

    st.markdown("---")
    if st.button("🔒 Logout Developer Admin Session"):
        st.session_state["dev_master_logged_in"] = False
        st.rerun()
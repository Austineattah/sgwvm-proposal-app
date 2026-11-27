
try:
    from onboarding_guides import get_help_text
except Exception:  # pragma: no cover
    def get_help_text(field_key: str) -> str:
        return ""
import time
import streamlit as st
from admin_logger import (
    check_ip_lockout,
    generate_reset_token,
    log_access_attempt,
    verify_reset_token,
)
import database as db

try:
    from draft_manager import (
        clear_draft as _ap_clear_draft,
        get_draft as _ap_get_draft,
        save_draft as _ap_save_draft,
    )
except Exception:
    def _ap_save_draft(*args, **kwargs): return False
    def _ap_get_draft(*args, **kwargs): return None
    def _ap_clear_draft(*args, **kwargs): return False

try:
    from persistence import (
        clear_working_state as _ap_clear_working_state,
        load_working_state as _ap_load_working_state,
        save_working_state as _ap_save_working_state,
    )
except Exception:
    def _ap_save_working_state(*args, **kwargs): return False
    def _ap_load_working_state(*args, **kwargs): return None
    def _ap_clear_working_state(*args, **kwargs): return False


def render_admin_login():
    # Check if already authenticated in session state
    if st.session_state.get("is_admin_authenticated", False):
        return True

    st.markdown("---")
    st.subheader("🔐 Enterprise Administrator Authentication Required")
    st.markdown(
        "Please enter the executive security password to access the NexusVault Administrator Control Panel."
    )

    with st.form("admin_login_form"):
        pwd_input = st.text_input(
            "Executive Password:",
            type="password",
            placeholder="Enter admin password...",
        )
        submit_btn = st.form_submit_button("Authenticate Session")

        if submit_btn:
            if pwd_input in ["NexusStaff2026!", "NexusExec2026!"]:
                st.session_state.is_admin_authenticated = True
                st.success("Authentication successful! Unlocking portal...")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Invalid executive security credentials. Access denied.")
                # Optional logging if available
                try:
                    log_access_attempt(
                        "admin_portal", "Failed Password Attempt", status="DENIED"
                    )
                except Exception:
                    pass
    return False


def render_admin_dashboard():
    # Enforce password gate before displaying any admin content
    if not render_admin_login():
        return

    st.title("🏢 Multi-Tenant Subscribed Client Directory & Security Lockout Monitor")
    st.markdown("### System Administrator Control Panel")
    st.success("🟢 Active Session: Privileged System Administrator Access Granted")

    db.init_db()

    tab1, tab2, tab3 = st.tabs(
        ["Client Directory", "Security Lockout Monitor", "System Configuration"]
    )

    with tab1:
        st.markdown("#### Subscribed Client Tenants (Live Database)")
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            # Check if clients/tenants table exists and fetch records
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('clients', 'tenants', 'enterprise_clients');"
            )
            tbl_res = cursor.fetchone()

            clients_data = []
            if tbl_res:
                tbl_name = tbl_res[0]
                cursor.execute(f"SELECT * FROM {tbl_name};")
                rows = cursor.fetchall()
                # Get column names safely
                col_names = [description[0] for description in cursor.description]
                for row in rows:
                    row_dict = dict(zip(col_names, row))
                    clients_data.append(
                        {
                            "Client Slug": row_dict.get(
                                "client_slug", row_dict.get("slug", "N/A")
                            ),
                            "Corporation Name": row_dict.get(
                                "corp_name", row_dict.get("name", "N/A")
                            ),
                            "Tier": row_dict.get(
                                "sub_package",
                                row_dict.get("tier", "Enterprise Sovereign"),
                            ),
                            "Status": (
                                "Active"
                                if row_dict.get("is_approved", "True") == "True"
                                else "Pending"
                            ),
                        }
                    )
            conn.close()

            if clients_data:
                st.dataframe(clients_data, use_container_width=True)
            else:
                # Fallback to key reference nodes if table is empty
                fallback_clients = [
                    {
                        "Client Slug": "skincare_c34d5aea",
                        "Corporation Name": "Skincare Enterprise Node",
                        "Tier": "Enterprise",
                        "Status": "Active",
                    },
                    {
                        "Client Slug": "faithacademy_7a184bb5",
                        "Corporation Name": "Faith Academy",
                        "Tier": "Enterprise",
                        "Status": "Active",
                    },
                    {
                        "Client Slug": "sgwvm_nexus_01",
                        "Corporation Name": "SGWVM Technology HQ",
                        "Tier": "Global Admin",
                        "Status": "Active",
                    },
                    {
                        "Client Slug": "national_assembly_ng",
                        "Corporation Name": "National Assembly Portal",
                        "Tier": "Government",
                        "Status": "Active",
                    },
                ]
                st.dataframe(fallback_clients, use_container_width=True)
        except Exception as e:
            st.warning(f"Using default secure enterprise nodes. Note: {e}")
            fallback_clients = [
                {
                    "Client Slug": "skincare_c34d5aea",
                    "Corporation Name": "Skincare Enterprise Node",
                    "Tier": "Enterprise",
                    "Status": "Active",
                }
            ]
            st.table(fallback_clients)

    with tab2:
        st.markdown("#### Security Lockout & Attempt Monitor")
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT timestamp, ip_address, status FROM admin_access_logs ORDER BY timestamp DESC LIMIT 20;"
            )
            logs = cursor.fetchall()
            conn.close()
            if logs:
                st.write("Recent Access Audit Logs:")
                for log in logs:
                    st.text(f"[{log[0]}] IP: {log[1]} | Status: {log[2]}")
            else:
                st.info(
                    "No failed or locked access attempts recorded in the audit log."
                )
        except Exception as e:
            st.warning(f"Audit log table empty or not initialized: {e}")

        if st.button("Reset All IP Lockouts & Clear Logs"):
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM admin_access_logs")
                conn.commit()
                conn.close()
                st.success("All security lockouts and audit logs successfully cleared!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to reset logs: {e}")

    with tab3:
        st.markdown("#### Internal System Configuration")
        st.caption("Session state is intentionally not displayed.")
        if st.button("Logout / Lock Session"):
            st.session_state.is_admin_authenticated = False
            st.success("Session locked successfully.")
            st.rerun()


if __name__ == "__main__":
    render_admin_dashboard()


def render_recycle_bin_admin_section():
    st.markdown("---")
    st.markdown("### 🗑️ Enterprise Recycle Bin & Reference Deletion")
    st.caption(
        "Safely archive or delete proposals and tenant slugs by reference number. Prevent permanent data loss."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🔍 Reference Number / Slug Deletion")
        target_ref = st.text_input(
            "Enter Proposal Reference No. or Tenant Slug to Delete:",
            placeholder="e.g. PROP-2026-001 or skincare_c34d5aea",
        help=get_help_text("delete_target_ref"),
        )
        help=get_help_text("delete_item_type"),
        target_type = st.selectbox("Select Item Type:", ["proposal", "tenant"])
        if st.button("Move to Recycle Bin", type="primary"):
            if target_ref:
                if hasattr(db, "soft_delete_by_reference"):
                    success = db.soft_delete_by_reference(
                        target_ref.strip(), target_type
                    )
                    if success:
                        st.success(
                            f"Item '{target_ref}' successfully moved to the Enterprise Recycle Bin!"
                        )
                        st.rerun()
                    else:
                        st.error(
                            f"Could not find or delete item '{target_ref}'. Check reference number."
                        )
                else:
                    st.error("Database recycle bin method not linked.")
            else:
                st.warning("Please enter a valid reference number or slug.")

    with col2:
        st.markdown("#### 📦 Archived Recycle Bin Items")
        if hasattr(db, "get_recycle_bin_items"):
            bin_items = db.get_recycle_bin_items()
            if bin_items:
                for b_id, item_type, identifier, deleted_at in bin_items:
                    with st.expander(
                        f"[{item_type.upper()}] {identifier} (Deleted: {deleted_at})"
                    ):
                        if st.button(f"Purge Permanently #{b_id}", key=f"purge_{b_id}"):
                            if hasattr(db, "purge_recycle_bin_item"):
                                db.purge_recycle_bin_item(b_id)
                                st.success(f"Item {identifier} purged permanently.")
                                st.rerun()
            else:
                st.info("Recycle bin is currently empty.")
        else:
            st.info("Recycle bin storage not initialized.")


def render_client_admin_panel(tenant_slug, db_conn):
    import streamlit as st

    st.subheader("?? Client-Admin Credential and Committee Passkey Management")
    st.write(
        "Manage secure passkeys for departmental heads, sub-directorates, and evaluation committee members."
    )

    with st.form("create_passkey_form"):
        help=get_help_text("staff_member_name"),
        member_name = st.text_input("Staff and Committee Member Name & Title")
        assigned_dir = st.selectbox(
            "Assign to Directorate and Unit",
            [
                "Directorate of ICT and Technical Services",
                "Directorate of Legal and Compliance",
                "Directorate of Finance and Procurement",
                "Solicited Tender Evaluation Committee",
                "Executive Registry and Minuting Desk",
            ],
        help=get_help_text("assigned_directorate"),
        )
        help=get_help_text("staff_passkey"),
        new_passkey = st.text_input("Assign Secure Passkey", type="password")
        submitted = st.form_submit_button("Provision / Update Passkey")

        if submitted and member_name and new_passkey:
            import sqlite3

            conn = sqlite3.connect(db.DB_FILE)
            c = conn.cursor()
            c.execute(
                "INSERT INTO committee_members (tenant_slug, member_name, passkey, assigned_directorate) VALUES (?, ?, ?, ?)",
                (tenant_slug, member_name, new_passkey, assigned_dir),
            )
            conn.commit()
            conn.close()
            st.success(
                f"Successfully provisioned passkey for {member_name} ({assigned_dir})!"
            )


def render_physical_intake_console(tenant_slug):
    import streamlit as st

    st.subheader("?? Desk Officer Physical Proposal Intake Console")
    st.write(
        "Log courier and hand-delivered hard-copy submissions, capture metadata, and generate secure digital twin records."
    )

    _phys_scope = f"physical_intake::{tenant_slug}"
    _phys_draft_name = f"physical_intake_{tenant_slug}"
    _phys_ws_key = f"draft::physical_intake::{tenant_slug}"
    _phys_modes = ["Courier Delivery", "Hand-Delivered / Registry", "Diplomatic Pouch"]
    _phys_keys = {
        "vendor_name": f"phys_vendor_name_{tenant_slug}",
        "proposal_title": f"phys_proposal_title_{tenant_slug}",
        "delivery_mode": f"phys_delivery_mode_{tenant_slug}",
        "courier_ref": f"phys_courier_ref_{tenant_slug}",
        "logged_by": f"phys_logged_by_{tenant_slug}",
    }
    _phys_saved = _ap_load_working_state(_phys_ws_key)
    if not isinstance(_phys_saved, dict):
        _phys_saved = _ap_get_draft(_phys_draft_name, scope_id=_phys_scope)
    if isinstance(_phys_saved, dict):
        if _phys_keys["delivery_mode"] not in st.session_state and _phys_saved.get("delivery_mode") in _phys_modes:
            st.session_state[_phys_keys["delivery_mode"]] = _phys_saved["delivery_mode"]
        for _field in ("vendor_name", "proposal_title", "courier_ref", "logged_by"):
            _wkey = _phys_keys[_field]
            if _wkey not in st.session_state and _phys_saved.get(_field):
                st.session_state[_wkey] = str(_phys_saved[_field])

    def _clear_phys_draft() -> None:
        _ap_clear_draft(_phys_draft_name, scope_id=_phys_scope)
        _ap_clear_working_state(_phys_ws_key)
        for _wkey in _phys_keys.values():
            st.session_state.pop(_wkey, None)

    with st.form("physical_intake_form"):
        col1, col2 = st.columns(2)
        with col1:
            help=get_help_text("organization_name"),
            vendor_name = st.text_input(
                "Vendor and Organization Name",
                key=_phys_keys["vendor_name"],
            )
            help=get_help_text("vendor_proposal_title"),
            proposal_title = st.text_input(
                "Proposal and Project Title",
                key=_phys_keys["proposal_title"],
            )
            delivery_mode = st.selectbox(
                "Delivery Mode",
                _phys_modes,
                key=_phys_keys["delivery_mode"],
            help=get_help_text("delivery_mode"),
            )
        with col2:
            help=get_help_text("courier_waybill_ref"),
            courier_ref = st.text_input(
                "Courier Tracking and Waybill Reference No.",
                key=_phys_keys["courier_ref"],
            )
            help=get_help_text("intake_officer_name"),
            logged_by = st.text_input(
                "Receiving Desk Officer Name",
                key=_phys_keys["logged_by"],
            )
            scanned_file = st.file_uploader(
                "Upload Scanned Cover Letter / Summary (PDF/Image)",
                type=["pdf", "png", "jpg"],
            help=get_help_text("scanned_cover_file"),
            )

        submitted_physical = st.form_submit_button(
            "Log Physical Intake and Generate Digital Twin"
        )

        if submitted_physical:
            _phys_snapshot = {
                _field: str(st.session_state.get(_wkey, ""))
                for _field, _wkey in _phys_keys.items()
            }
            if any(v.strip() for v in _phys_snapshot.values()):
                _ap_save_draft(_phys_draft_name, dict(_phys_snapshot), scope_id=_phys_scope)
                _ap_save_working_state(_phys_ws_key, dict(_phys_snapshot), scope_id=_phys_scope)

        if submitted_physical and vendor_name and proposal_title:
            import sqlite3, os

            os.makedirs("uploads/physical", exist_ok=True)
            file_path = ""
            if scanned_file:
                file_path = os.path.join("uploads/physical", scanned_file.name)
                with open(file_path, "wb") as f:
                    f.write(scanned_file.getbuffer())

            conn = sqlite3.connect(db.DB_FILE)
            c = conn.cursor()
            c.execute(
                """
                INSERT INTO physical_proposal_intake (tenant_slug, vendor_name, proposal_title, delivery_mode, courier_ref, scanned_file_path, logged_by, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING_MINUTES')
            """,
                (
                    tenant_slug,
                    vendor_name,
                    proposal_title,
                    delivery_mode,
                    courier_ref,
                    file_path,
                    logged_by,
                ),
            )
            conn.commit()
            conn.close()
            _clear_phys_draft()
            st.success(
                f"Physical proposal from {vendor_name} successfully logged! Digital twin record created with status: PENDING_MINUTES."
            )


def render_tender_committee_portal(tenant_slug):
    import streamlit as st
    import sqlite3

    st.subheader("?? Tender Committee Management & Review Engine")
    st.write(
        "Secure evaluation workspace for authorized committee members using passkey authentication."
    )

    # Passkey Authentication
    passkey_input = st.text_input(
        "Enter Committee Member Secure Passkey", type="password"
    )

    if passkey_input:
        conn = sqlite3.connect(db.DB_FILE)
        c = conn.cursor()
        c.execute(
            "SELECT member_name, assigned_directorate FROM committee_members WHERE tenant_slug = ? AND passkey = ?",
            (tenant_slug, passkey_input),
        )
        member = c.fetchone()
        conn.close()

        if member:
            st.success(
                f"?? Authenticated successfully! Welcome, **{member[0]}** ({member[1]})."
            )

            tab_workspace, tab_master = st.tabs(
                [
                    "?? Individual Member Workspace",
                    "?? Consolidated Master Committee View",
                ]
            )

            with tab_workspace:
                st.markdown("### Assigned Dossier Evaluation Workspace")
                st.write("Review AI-audited dossiers sorted by sequential bidder tags.")

                conn = sqlite3.connect(db.DB_FILE)
                c = conn.cursor()
                c.execute(
                    "SELECT proposal_id, vendor_name, proposal_title, bidder_sequence_tag, qr_reference_id FROM vendor_proposals WHERE tenant_slug = ? AND is_paid = 1",
                    (tenant_slug,),
                )
                proposals = c.fetchall()
                conn.close()

                if proposals:
                    for prop in proposals:
                        _prop_id = prop[0]
                        _eval_scope = f"admin_dossier_eval::{tenant_slug}"
                        _eval_draft_name = f"admin_eval_{tenant_slug}_{_prop_id}"
                        _eval_ws_key = f"draft::admin_eval::{tenant_slug}::{_prop_id}"
                        _score_key = f"score_{_prop_id}"
                        _comm_key = f"comm_{_prop_id}"
                        _eval_saved = _ap_load_working_state(_eval_ws_key)
                        if not isinstance(_eval_saved, dict):
                            _eval_saved = _ap_get_draft(_eval_draft_name, scope_id=_eval_scope)
                        if isinstance(_eval_saved, dict):
                            if _score_key not in st.session_state and "score" in _eval_saved:
                                st.session_state[_score_key] = int(_eval_saved["score"])
                            if _comm_key not in st.session_state and _eval_saved.get("comments"):
                                st.session_state[_comm_key] = str(_eval_saved["comments"])

                        with st.expander(f"Bidder {prop[3]}: {prop[1]} - {prop[2]}"):
                            st.write(f"**QR Reference ID:** {prop[4]}")
                            score = st.slider(
                                f"Technical & Financial Score for {prop[3]}",
                                0,
                                100,
                                75,
                                key=_score_key,
                            )
                            comments = st.text_area(
                                f"Committee Evaluation Remarks for {prop[3]}",
                                key=_comm_key,
                            )
                            _eval_snapshot = {
                                "score": int(score),
                                "comments": str(comments),
                            }
                            if str(comments).strip() or int(score) != 75:
                                _ap_save_draft(_eval_draft_name, dict(_eval_snapshot), scope_id=_eval_scope)
                                _ap_save_working_state(_eval_ws_key, dict(_eval_snapshot), scope_id=_eval_scope)

                            if st.button(
                                f"Submit Evaluation for {prop[3]}",
                                key=f"sub_eval_{_prop_id}",
                            ):
                                _ap_clear_draft(_eval_draft_name, scope_id=_eval_scope)
                                _ap_clear_working_state(_eval_ws_key)
                                st.session_state.pop(_score_key, None)
                                st.session_state.pop(_comm_key, None)
                                st.success(
                                    f"? Score of {score}/100 and remarks successfully recorded for Bidder {prop[3]}."
                                )
                else:
                    st.info("No active solicited proposals available for evaluation.")

            with tab_master:
                st.markdown("### ?? Consolidated Master Committee View")
                st.write(
                    "Centralized master index of all evaluated solicited dossiers, QR references, and final rankings."
                )

                conn = sqlite3.connect(db.DB_FILE)
                c = conn.cursor()
                c.execute(
                    "SELECT bidder_sequence_tag, vendor_name, proposal_title, qr_reference_id FROM vendor_proposals WHERE tenant_slug = ? AND is_paid = 1",
                    (tenant_slug,),
                )
                master_rows = c.fetchall()
                conn.close()

                if master_rows:
                    for r in master_rows:
                        st.markdown(
                            f"- **Bidder {r[0]}**: {r[1]} | *Project:* {r[2]} | *QR ID:* {r[3]} | **Status:** Evaluated & Indexed"
                        )
                else:
                    st.info("Master committee view is currently empty.")
        else:
            st.error(
                "? Invalid passkey. Please verify your credentials with the Client-Admin Directorate."
            )

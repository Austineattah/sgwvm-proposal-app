import time
import streamlit as st
from admin_logger import (
    check_ip_lockout,
    generate_reset_token,
    log_access_attempt,
    verify_reset_token,
)
import database as db


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
        st.write("Current Session State:", dict(st.session_state))
        if st.button("Logout / Lock Session"):
            st.session_state.is_admin_authenticated = False
            st.success("Session locked successfully.")
            st.rerun()


if __name__ == "__main__":
    render_admin_dashboard()


def render_recycle_bin_admin_section():
    st.markdown("---")
    st.markdown("### 🗑️ Enterprise Recycle Bin & Reference Deletion")
    st.caption("Safely archive or delete proposals and tenant slugs by reference number. Prevent permanent data loss.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🔍 Reference Number / Slug Deletion")
        target_ref = st.text_input("Enter Proposal Reference No. or Tenant Slug to Delete:", placeholder="e.g. PROP-2026-001 or skincare_c34d5aea")
        target_type = st.selectbox("Select Item Type:", ["proposal", "tenant"])
        if st.button("Move to Recycle Bin", type="primary"):
            if target_ref:
                if hasattr(db, "soft_delete_by_reference"):
                    success = db.soft_delete_by_reference(target_ref.strip(), target_type)
                    if success:
                        st.success(f"Item '{target_ref}' successfully moved to the Enterprise Recycle Bin!")
                        st.rerun()
                    else:
                        st.error(f"Could not find or delete item '{target_ref}'. Check reference number.")
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
                    with st.expander(f"[{item_type.upper()}] {identifier} (Deleted: {deleted_at})"):
                        if st.button(f"Purge Permanently #{b_id}", key=f"purge_{b_id}"):
                            if hasattr(db, "purge_recycle_bin_item"):
                                db.purge_recycle_bin_item(b_id)
                                st.success(f"Item {identifier} purged permanently.")
                                st.rerun()
            else:
                st.info("Recycle bin is currently empty.")
        else:
            st.info("Recycle bin storage not initialized.")

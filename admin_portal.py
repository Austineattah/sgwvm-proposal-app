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
    # AUTO-AUTHENTICATION BYPASS FOR DEMO / INSPECTION
    st.session_state.is_admin_authenticated = True
    return True

def render_admin_dashboard():
    st.title("🏢 Multi-Tenant Subscribed Client Directory & Security Lockout Monitor")
    st.markdown("### System Administrator Control Panel")
    st.success("🟢 Active Session: Privileged System Administrator Access Granted")
    
    db.init_db()
    
    tab1, tab2, tab3 = st.tabs(["Client Directory", "Security Lockout Monitor", "System Configuration"])
    
    with tab1:
        st.markdown("#### Subscribed Client Tenants")
        try:
            clients = [
                {"Client ID": "faithacademy_7a184bb5", "Name": "Faith Academy", "Tier": "Enterprise", "Status": "Active", "Expiry": "2026-12-31"},
                {"Client ID": "sgwvm_nexus_01", "Name": "SGWVM Technology HQ", "Tier": "Global Admin", "Status": "Active", "Expiry": "Permanent"},
                {"Client ID": "national_assembly_ng", "Name": "National Assembly Portal", "Tier": "Government", "Status": "Active", "Expiry": "2027-06-30"}
            ]
            st.table(clients)
        except Exception as e:
            st.error(f"Error loading client records: {e}")
            
    with tab2:
        st.markdown("#### Security Lockout & Attempt Monitor")
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp, ip_address, status FROM admin_access_logs ORDER BY timestamp DESC LIMIT 20;")
            logs = cursor.fetchall()
            conn.close()
            if logs:
                st.write("Recent Access Audit Logs:")
                for log in logs:
                    st.text(f"[{log[0]}] IP: {log[1]} | Status: {log[2]}")
            else:
                st.info("No failed or locked access attempts recorded in the audit log.")
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
            st.rerun()

if __name__ == "__main__":
    render_admin_dashboard()

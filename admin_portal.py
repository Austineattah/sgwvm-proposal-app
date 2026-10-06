import time
import streamlit as st
from admin_logger import (
    check_ip_lockout,
    generate_reset_token,
    log_access_attempt,
    verify_reset_token,
)
from notifications import send_email_notification

ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "SuperSecretPass123")
ADMIN_EMAIL = st.secrets.get("ADMIN_EMAIL", "admin@sgwvmtech.com")
LOCKOUT_WINDOW = 60
MAX_ATTEMPTS = 3


def render_admin_login():
    if "is_admin_authenticated" not in st.session_state:
        st.session_state.is_admin_authenticated = False
    if "reset_mode" not in st.session_state:
        st.session_state.reset_mode = False

    is_blocked, failed_count = check_ip_lockout(
        window_seconds=LOCKOUT_WINDOW, max_attempts=MAX_ATTEMPTS
    )

    st.subheader("🔒 Internal Admin Portal")

    # 1. SYSTEM BLOCKED / LOCKOUT VIEW
    if is_blocked:
        st.error("🚨 SYSTEM BLOCKED: Maximum 3 attempts exceeded. Access Restricted.")
        st.warning("Please contact the Administrator or reset security settings below.")

        st.divider()
        st.markdown("### 🔑 Admin Security Recovery")
        st.write(
            "An administrator can request a verification code sent to the registered email address to restore access."
        )

        with st.form("admin_reset_request_form_unique"):
            recovery_email = st.text_input("Registered Admin Email", placeholder="admin@domain.com")
            submit_recovery = st.form_submit_button("Send Security Recovery Code")

        if submit_recovery:
            active_admin_email = st.secrets.get("ADMIN_EMAIL", ADMIN_EMAIL)
            if recovery_email.strip().lower() == active_admin_email.strip().lower():
                code = generate_reset_token(active_admin_email)
                subject = "Security Alert: Admin Portal Reset Code"
                body = (
                    f"A security lockout was triggered on the Internal Admin Portal.\n\n"
                    f"Your 6-digit Security Verification Code is: {code}\n\n"
                    f"This code will expire in 10 minutes. Use this code to unblock access."
                )
                success, msg = send_email_notification(subject, body, active_admin_email)
                if success:
                    st.success("Verification code sent to your registered email!")
                    st.session_state.reset_mode = True
                else:
                    st.error(f"Failed to deliver email notification: {msg}")
            else:
                st.error("Provided email does not match the registered administrator account.")

        if st.session_state.get("reset_mode", False):
            st.divider()
            with st.form("admin_verify_code_form_unique"):
                entered_code = st.text_input("Enter 6-Digit Verification Code", type="password")
                submit_code = st.form_submit_button("Verify Code & Reset Access")

            if submit_code:
                active_admin_email = st.secrets.get("ADMIN_EMAIL", ADMIN_EMAIL)
                if verify_reset_token(active_admin_email, entered_code):
                    log_access_attempt(status="RESET_SUCCESS")
                    st.session_state.reset_mode = False
                    st.success("Security settings verified! System unblocked. Please try logging in.")
                    st.rerun()
                else:
                    st.error("Invalid or expired verification code.")

        return False

    # 2. STANDARD LOGIN FORM
    remaining_attempts = MAX_ATTEMPTS - failed_count
    st.info(f"Access restricted to internal admin portal. Remaining attempts: {remaining_attempts}")

    with st.form("admin_login_portal_form_v2", clear_on_submit=True):
        input_password = st.text_input("Admin Password", type="password")
        submit_button = st.form_submit_button("Access Portal")

    if submit_button:
        active_password = st.secrets.get("ADMIN_PASSWORD", ADMIN_PASSWORD)

        if input_password == active_password:
            log_access_attempt(status="SUCCESS")
            st.session_state.is_admin_authenticated = True
            st.success("Access Granted. Redirecting to admin portal...")
            st.rerun()
        else:
            log_access_attempt(status="FAILED")
            st.error("Incorrect password. Attempt recorded.")
            st.rerun()

    return False


if __name__ == "__main__":
    if not st.session_state.get("is_admin_authenticated", False):
        render_admin_login()
    else:
        st.title("🔒 Internal Admin Dashboard")
        st.write("Welcome, System Administrator.")
        if st.button("Log Out"):
            st.session_state.is_admin_authenticated = False
            st.rerun()

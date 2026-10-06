import streamlit as st
from notifications import send_email_notification
from admin_logger import generate_reset_token

st.set_page_config(page_title="SMTP Diagnostic Tool", page_icon="✉️")

st.title("✉️ SMTP Recovery Email Test Suite")

# 1. Verify secrets configuration
st.subheader("1. Secret Configuration Status")
required_keys = ["SMTP_SERVER", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "ADMIN_EMAIL"]
missing_keys = [key for key in required_keys if key not in st.secrets]

if missing_keys:
    st.error(f"Missing required secrets: {', '.join(missing_keys)}")
    st.info("Please add them to `.streamlit/secrets.toml` before proceeding.")
else:
    st.success("All required SMTP keys loaded successfully from secrets.")
    st.json({
        "SMTP_SERVER": st.secrets.get("SMTP_SERVER"),
        "SMTP_PORT": st.secrets.get("SMTP_PORT"),
        "SMTP_USER": st.secrets.get("SMTP_USER"),
        "ADMIN_EMAIL": st.secrets.get("ADMIN_EMAIL"),
    })

# 2. Test execution button
st.subheader("2. Dispatch Test Verification Code")
if st.button("Send Test Recovery Code"):
    target_email = st.secrets.get("ADMIN_EMAIL")
    test_code = generate_reset_token(target_email)
    
    subject = "Test: Admin Security Verification Code"
    body = (
        f"This is a local test of your SMTP email delivery pipeline.\n\n"
        f"Generated Verification Code: {test_code}\n\n"
        f"If you received this message, your SMTP credentials and recovery mechanism are functioning correctly."
    )
    
    with st.spinner("Connecting to SMTP server and dispatching email..."):
        success, response = send_email_notification(subject, body, target_email)
        
    if success:
        st.success(f"Recovery email delivered successfully to `{target_email}`!")
        st.info(f"Verification Code logged in SQLite DB: `{test_code}`")
    else:
        st.error(f"SMTP Delivery Failed: {response}")

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from twilio.rest import Client

# Try loading Streamlit safely to check st.secrets in deployed environments
try:
    import streamlit as st
except ImportError:
    st = None


def get_secret(key, default=None):
    """Safely retrieves a secret from Streamlit Cloud Secrets first, falling back to OS environment variables."""
    if st and hasattr(st, "secrets") and key in st.secrets:
        return st.secrets[key]
    return os.getenv(key, default)


# --- CONFIGURATION ENGINE ---
SMTP_SERVER = get_secret("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(get_secret("SMTP_PORT", 587))

SENDER_EMAIL = get_secret("SENDER_EMAIL", get_secret("EMAIL_USER"))
SENDER_PASSWORD = get_secret("SENDER_PASSWORD", get_secret("EMAIL_PASS"))

# Twilio Credentials (Supports both standard Auth Token and API Key SID/Secret)
TWILIO_ACCOUNT_SID = get_secret("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = get_secret("TWILIO_AUTH_TOKEN")
TWILIO_API_KEY_SID = get_secret("TWILIO_API_KEY_SID")
TWILIO_API_SECRET = get_secret("TWILIO_API_SECRET")
TWILIO_PHONE_NUMBER = get_secret("TWILIO_PHONE_NUMBER", "+1234567890")

# Executive leadership distribution list for high-priority or flagged proposals
raw_execs = get_secret(
    "EXECUTIVE_EMAILS",
    "exec.director@sgwvm-portal.com,compliance.head@sgwvm-portal.com",
)
EXECUTIVE_EMAILS = (
    [e.strip() for e in raw_execs.split(",") if e.strip()]
    if isinstance(raw_execs, str)
    else raw_execs
)

# High-priority budget threshold for executive escalation
HIGH_PRIORITY_THRESHOLD = float(get_secret("HIGH_PRIORITY_THRESHOLD", 50000000.0))


def send_credentials_email(
    recipient_email: str, recipient_name: str, username: str, plaintext_password: str
):
    """Sends account login credentials to a newly provisioned user via SMTP."""
    sender_email = get_secret("SENDER_EMAIL", SENDER_EMAIL)
    sender_password = get_secret("SENDER_PASSWORD", SENDER_PASSWORD)

    if not sender_email or not sender_password:
        print("[Notifier] ❌ SMTP credentials missing. Skipping credentials email.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your SGWVM Proposal Portal Access Credentials"
    msg["From"] = f"SGWVM Portal <{sender_email}>"
    msg["To"] = recipient_email

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2>Welcome to the SGWVM Proposal Portal</h2>
        <p>Dear <b>{recipient_name}</b>,</p>
        <p>Your portal account has been provisioned. Below are your active access credentials:</p>
        <table style="background-color: #f8f9fa; padding: 15px; border-radius: 6px; border: 1px solid #e9ecef; width: 100%;">
          <tr><td style="padding: 4px;"><b>Portal URL:</b></td><td>https://sgwvm-proposal-app.streamlit.app</td></tr>
          <tr><td style="padding: 4px;"><b>Username:</b></td><td><code>{username}</code></td></tr>
          <tr><td style="padding: 4px;"><b>Password:</b></td><td><code>{plaintext_password}</code></td></tr>
        </table>
        <p style="margin-top: 15px; color: #d9534f; font-size: 0.9em;">
          <b>Security Note:</b> Please log in and update your password upon your initial login.
        </p>
      </body>
    </html>
    """

    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(
            get_secret("SMTP_SERVER", SMTP_SERVER),
            int(get_secret("SMTP_PORT", SMTP_PORT)),
        ) as server:
            server.starttls()
            # Remove any whitespace in passwords (e.g. Google App Passwords)
            server.login(sender_email, sender_password.replace(" ", ""))
            server.sendmail(sender_email, recipient_email, msg.as_string())
        print(f"[Notifier] ✅ Credentials email successfully sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"[Notifier] ❌ Failed to send credentials email: {e}")
        return False


def send_auto_email(
    recipient_email: str,
    vendor_name: str,
    tracking_code: str,
    is_flagged: bool = False,
    budget: float = 0.0,
):
    """Sends confirmation to vendor and alerts senior leadership if flagged or high priority."""
    sender_email = get_secret("SENDER_EMAIL", SENDER_EMAIL)
    sender_password = get_secret("SENDER_PASSWORD", SENDER_PASSWORD)

    if not sender_email or not sender_password:
        print("[Notifier] ❌ SMTP credentials missing. Skipping email dispatch.")
        return False

    is_high_priority = budget >= HIGH_PRIORITY_THRESHOLD
    needs_executive_attention = is_flagged or is_high_priority

    try:
        with smtplib.SMTP(
            get_secret("SMTP_SERVER", SMTP_SERVER),
            int(get_secret("SMTP_PORT", SMTP_PORT)),
        ) as server:
            server.starttls()
            server.login(sender_email, sender_password.replace(" ", ""))

            # 1. Send confirmation to vendor/organization
            if recipient_email and recipient_email.strip():
                msg_vendor = MIMEMultipart("alternative")
                msg_vendor["Subject"] = (
                    f"Proposal Receipt Confirmation - Tracking ID: {tracking_code}"
                )
                msg_vendor["From"] = sender_email
                msg_vendor["To"] = recipient_email.strip()

                body_vendor = f"""Dear management of {vendor_name},

Your proposal has been received and you will be contacted for further discussion should the need arise upon analysis of your proposal.

Tracking Reference: {tracking_code}

Thank you for partnering with SGWVM Ltd.

Best regards,
SGWVM Proposal Intake & Enterprise Evaluation Team
"""
                msg_vendor.attach(MIMEText(body_vendor, "plain"))
                server.send_message(msg_vendor)
                print(
                    f"[Notifier] ✅ Confirmation email sent to vendor: {recipient_email.strip()}"
                )

            # 2. Escalation: Alert executive leadership if high-priority or risk-flagged
            if needs_executive_attention and EXECUTIVE_EMAILS:
                reasons = []
                if is_flagged:
                    reasons.append("Compliance Risk Flagged")
                if is_high_priority:
                    reasons.append(f"Top Executive Priority Budget ({budget:,.2f})")
                reason_summary = " & ".join(reasons)

                for exec_email in EXECUTIVE_EMAILS:
                    msg_exec = MIMEMultipart("alternative")
                    msg_exec["Subject"] = (
                        f"👑 URGENT EXECUTIVE PRIORITY ALERT: {reason_summary}"
                        f" ({tracking_code})"
                    )
                    msg_exec["From"] = sender_email
                    msg_exec["To"] = exec_email

                    body_exec = f"""ATTENTION EXECUTIVE COMMITTEE,

A proposal requiring topmost executive attention has been ingested from vendor: {vendor_name}.
Tracking Code: {tracking_code}
Escalation Triggers: {reason_summary}

Please log into the Enterprise Dashboard immediately to review findings and audit details.

Best regards,
Automated Executive Surveillance System
"""
                    msg_exec.attach(MIMEText(body_exec, "plain"))
                    server.send_message(msg_exec)

                print(
                    f"[Notifier] ✅ Executive escalation alerts successfully dispatched for: {reason_summary}"
                )

        return True
    except Exception as e:
        print(f"[Notifier] ❌ Failed to send email notification: {e}")
        return False


def send_auto_sms(recipient_phone: str, vendor_name: str, tracking_code: str):
    """Sends an automated SMS notification via Twilio using either API Key or Auth Token."""
    account_sid = get_secret("TWILIO_ACCOUNT_SID", TWILIO_ACCOUNT_SID)
    api_key_sid = get_secret("TWILIO_API_KEY_SID", TWILIO_API_KEY_SID)
    api_secret = get_secret("TWILIO_API_SECRET", TWILIO_API_SECRET)
    auth_token = get_secret("TWILIO_AUTH_TOKEN", TWILIO_AUTH_TOKEN)
    from_number = get_secret("TWILIO_PHONE_NUMBER", TWILIO_PHONE_NUMBER)

    if (
        not recipient_phone
        or not recipient_phone.strip()
        or not account_sid
        or not from_number
    ):
        print(
            "[Notifier] ⚠️ Twilio credentials or recipient phone missing/invalid. Skipping SMS."
        )
        return False

    try:
        # Authenticate with API Key if available; otherwise fall back to Auth Token
        if api_key_sid and api_secret:
            client = Client(api_key_sid, api_secret, account_sid)
        elif auth_token:
            client = Client(account_sid, auth_token)
        else:
            print("[Notifier] ❌ Neither Twilio API Key nor Auth Token is available.")
            return False

        message_body = (
            f"Dear management of {vendor_name}, your proposal has been received "
            f"and you will be contacted for further discussion should the need arise upon "
            f"analysis of your proposal. Ref: {tracking_code} - SGWVM Ltd"
        )

        message = client.messages.create(
            body=message_body,
            from_=from_number,
            to=recipient_phone.strip(),
        )
        print(f"[Notifier] ✅ SMS sent successfully. SID: {message.sid}")
        return True
    except Exception as e:
        print(f"[Notifier] ❌ Failed to send SMS: {e}")
        return False

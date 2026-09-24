import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from twilio.rest import Client

# --- CONFIGURATION VIA ENVIRONMENT VARIABLES ---
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

# Email Credentials (Supports both EMAIL_USER/EMAIL_PASS and SENDER_EMAIL/SENDER_PASSWORD)
SENDER_EMAIL = os.getenv(
    "SENDER_EMAIL", os.getenv("EMAIL_USER", "your-email@gmail.com")
)
SENDER_PASSWORD = os.getenv(
    "SENDER_PASSWORD", os.getenv("EMAIL_PASS", "xxxx xxxx xxxx xxxx")
)

# Twilio Credentials
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "ACxxxxxxxxxxxxxxxxxxxxxxxx")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "your_auth_token")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "+1234567890")

# Executive leadership distribution list for topmost attention
EXECUTIVE_EMAILS = [
    "exec.director@sgwvm-portal.com",
    "compliance.head@sgwvm-portal.com",
]

# Define high-priority budget threshold for executive attention
HIGH_PRIORITY_THRESHOLD = 50000000.0


def send_auto_email(
    recipient_email: str,
    vendor_name: str,
    tracking_code: str,
    is_flagged: bool = False,
    budget: float = 0.0,
):
    """Sends confirmation to vendor and alerts senior leadership if flagged or high priority."""
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("[Notifier] ❌ SMTP credentials missing. Skipping email dispatch.")
        return False

    is_high_priority = budget >= HIGH_PRIORITY_THRESHOLD
    needs_executive_attention = is_flagged or is_high_priority

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)

            # 1. Send exact requested confirmation to the vendor/organization
            if recipient_email and recipient_email.strip():
                msg_vendor = MIMEMultipart("alternative")
                msg_vendor["Subject"] = (
                    f"Proposal Receipt Confirmation - Tracking ID: {tracking_code}"
                )
                msg_vendor["From"] = SENDER_EMAIL
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

            # 2. ESCALATION: Instantly alert top officers if high-priority or risk-flagged
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
                    msg_exec["From"] = SENDER_EMAIL
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
                    f"[Notifier] ✅ Executive escalation alerts successfully"
                    f" dispatched for: {reason_summary}"
                )

        return True
    except Exception as e:
        print(f"[Notifier] ❌ Failed to send email notification: {e}")
        return False


def send_auto_sms(recipient_phone: str, vendor_name: str, tracking_code: str):
    """Sends an automated SMS notification via Twilio."""
    if (
        not recipient_phone
        or not recipient_phone.strip()
        or not TWILIO_ACCOUNT_SID
        or "placeholder" in TWILIO_ACCOUNT_SID
        or not TWILIO_AUTH_TOKEN
        or not TWILIO_PHONE_NUMBER
    ):
        print(
            "[Notifier] ⚠️ Twilio credentials or recipient phone missing/invalid."
            " Skipping SMS."
        )
        return False

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        # Exact required SMS text formatting
        message_body = (
            f"Dear management of {vendor_name}, your proposal has been received "
            f"and you will be contacted for further discussion should the need arise upon "
            f"analysis of your proposal. Ref: {tracking_code} - SGWVM Ltd"
        )

        message = client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=recipient_phone.strip(),
        )
        print(f"[Notifier] ✅ SMS sent successfully. SID: {message.sid}")
        return True
    except Exception as e:
        print(f"[Notifier] ❌ Failed to send SMS: {e}")
        return False

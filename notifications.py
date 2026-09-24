import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()


def send_email_notification(subject: str, body: str, recipient_email: str):
    """Sends an email notification via Gmail SMTP."""
    try:
        server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        port = int(os.getenv("SMTP_PORT", 587))
        sender = os.getenv("SENDER_EMAIL")
        password = os.getenv("SENDER_PASSWORD")

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(server, port) as smtp:
            smtp.starttls()
            smtp.login(sender, password)
            smtp.send_message(msg)
        return True, "Email sent successfully!"
    except Exception as e:
        return False, str(e)


def send_sms_notification(body: str, recipient_phone: str):
    """Sends an SMS notification via Twilio."""
    try:
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=body, from_=twilio_number, to=recipient_phone
        )
        return True, f"SMS sent successfully! SID: {message.sid}"
    except Exception as e:
        return False, str(e)

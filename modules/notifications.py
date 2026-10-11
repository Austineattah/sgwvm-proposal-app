import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_vendor_email(recipient_email: str, subject: str, body_html: str) -> tuple[bool, str]:
    """Sends an HTML email notification to a vendor. Falls back gracefully if unconfigured."""
    if not Config.SMTP_USER or not Config.SMTP_PASSWORD:
        logger.warning("SMTP credentials missing. Email notification simulated.")
        return True, "Email simulation successful (SMTP credentials not configured)."
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = Config.SENDER_EMAIL or Config.SMTP_USER
        msg["To"] = recipient_email
        
        part = MIMEText(body_html, "html")
        msg.attach(part)
        
        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.sendmail(msg["From"], recipient_email, msg.as_string())
            
        return True, "Email sent successfully."
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False, f"Email delivery failed: {str(e)}"

def send_vendor_sms(recipient_phone: str, message_body: str) -> tuple[bool, str]:
    """Sends an SMS acknowledgment to a vendor using Twilio. Falls back gracefully if unconfigured."""
    if not Config.TWILIO_ACCOUNT_SID or not Config.TWILIO_AUTH_TOKEN or not Config.TWILIO_PHONE_NUMBER:
        logger.warning("Twilio credentials missing. SMS notification simulated.")
        return True, "SMS simulation successful (Twilio credentials not configured)."
    
    try:
        from twilio.rest import Client
        client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
        
        message = client.messages.create(
            body=message_body,
            from_=Config.TWILIO_PHONE_NUMBER,
            to=recipient_phone
        )
        return True, f"SMS sent successfully (SID: {message.sid})"
    except Exception as e:
        logger.error(f"Failed to send SMS via Twilio: {e}")
        return False, f"SMS delivery failed: {str(e)}"


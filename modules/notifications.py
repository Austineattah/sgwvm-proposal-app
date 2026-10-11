import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config

def send_email(to_email, subject, body):
    """Sends an email notification. Gracefully simulates if SMTP credentials are missing."""
    smtp_server = getattr(Config, 'SMTP_SERVER', None)
    smtp_port = getattr(Config, 'SMTP_PORT', 587)
    smtp_email = getattr(Config, 'SMTP_EMAIL', None)
    smtp_password = getattr(Config, 'SMTP_PASSWORD', None)

    if not smtp_server or not smtp_email or not smtp_password:
        print(f"\n[EMAIL SIMULATION]")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}\n-----------------------------------")
        return True, "Email simulated successfully (SMTP not configured)."

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_email, smtp_password)
        server.send_message(msg)
        server.quit()
        return True, "Email sent successfully."
    except Exception as e:
        return False, f"Email sending failed: {str(e)}"

def send_sms(to_phone, message):
    """Sends an SMS notification via Termii API. Gracefully simulates if Termii API key is missing."""
    termii_api_key = getattr(Config, 'TERMII_API_KEY', None)
    termii_sender_id = getattr(Config, 'TERMII_SENDER_ID', 'SGWVM')

    if not termii_api_key:
        print(f"\n[SMS SIMULATION]")
        print(f"To Phone: {to_phone}")
        print(f"Message:\n{message}\n-----------------------------------")
        return True, "SMS simulated successfully (Termii API key not configured)."

    try:
        url = "https://v3.api.termii.com/api/sms/send"
        payload = {
            "api_key": termii_api_key,
            "to": to_phone,
            "from": termii_sender_id,
            "sms": message,
            "type": "plain",
            "channel": "generic"
        }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return True, "SMS sent successfully via Termii."
        else:
            return False, f"Termii SMS failed: {response.text}"
    except Exception as e:
        return False, f"SMS sending exception: {str(e)}"

def send_submission_acknowledgement(vendor_email, vendor_phone, company_name, project_title, proposal_id):
    """Sends official automated email AND SMS acknowledgement upon successful vendor submission."""
    org_name = getattr(Config, 'ORG_NAME', 'SGWVM Technology Limited')
    committee_name = getattr(Config, 'COMMITTEE_NAME', f"{org_name} Proposal Evaluation Committee")
    
    # 1. Email Content
    subject = f"Proposal Received: {project_title} (#{proposal_id})"
    email_body = f"""Dear {company_name},

Thank you for your proposal submitted to {org_name}. 

Your proposal is under review (Reference ID: #{proposal_id} - "{project_title}") and you shall be contacted in due course upon need appraisal.

Best regards,
{committee_name}
{org_name}"""

    email_success, email_msg = send_email(vendor_email, subject, email_body)

    # 2. SMS Content (Concise for mobile)
    sms_message = f"Dear {company_name}, your proposal to {org_name} is under review. Ref ID: #{proposal_id}. You will be contacted in due course."
    
    sms_success, sms_msg = True, "SMS skipped (no phone provided)"
    if vendor_phone:
        sms_success, sms_msg = send_sms(vendor_phone, sms_message)

    return email_success and sms_success, f"Email: {email_msg} | SMS: {sms_msg}"

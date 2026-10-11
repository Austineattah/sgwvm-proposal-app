import smtplib
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
        return True, "Email simulated successfully (SMTP not configured in Config)."

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

def send_submission_acknowledgement(vendor_email, company_name, project_title, proposal_id):
    """Sends the official automated acknowledgement email with dynamic client/organization branding."""
    org_name = getattr(Config, 'ORG_NAME', 'SGWVM Technology Limited')
    committee_name = getattr(Config, 'COMMITTEE_NAME', f"{org_name} Proposal Evaluation Committee")
    
    subject = f"Proposal Received: {project_title} (#{proposal_id})"
    body = f"""Dear {company_name},

Thank you for your proposal submitted to {org_name}. 

Your proposal is under review (Reference ID: #{proposal_id} - "{project_title}") and you shall be contacted in due course upon need appraisal.

Best regards,
{committee_name}
{org_name}"""

    return send_email(vendor_email, subject, body)

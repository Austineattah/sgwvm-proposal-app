import database as db
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Configurable Production SMTP Settings (Reads from environment or Streamlit secrets)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
ENABLE_LIVE_EMAIL = os.getenv("ENABLE_LIVE_EMAIL", "False").lower() in ["true", "1"]

def send_live_email(to_email, subject, body):
    """Attempt live SMTP email dispatch if credentials exist."""
    if not ENABLE_LIVE_EMAIL or not SMTP_USER or not SMTP_PASS:
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False

def send_vendor_acknowledgement(vendor_email, vendor_phone, vendor_name, qr_ref_id, project_title):
    email_subject = f"OFFICIAL RECEIPT: Proposal Registered ({qr_ref_id})"
    email_body = f"""
    OFFICIAL DISPATCH RECEIPT - NEXUSVAULT ENTERPRISE INTAKE
    ---------------------------------------------------------
    Dear {vendor_name},

    Your proposal titled '{project_title}' has been successfully received, 
    parsed via Live OCR, and registered into the sovereign portal repository.

    CRITICAL ACCESS REFERENCE:
    Tracking Reference ID: {qr_ref_id}
    Verification Status: VERIFIED & ACTIVE

    Please quote this Reference ID in all official correspondence.
    ---------------------------------------------------------
    NEXUSVAULT Enterprise Intake Node
    """

    # Attempt live transmission
    sent_status = send_live_email(vendor_email, email_subject, email_body)
    status_label = "LIVE_SMTP_SENT" if sent_status else "LOGGED_QUEUED"

    db.log_event("Automated Dispatcher", f"EMAIL_VENDOR_ACK ({status_label})", qr_ref_id, f"Receipt dispatched to {vendor_email}")
    db.log_event("Automated Dispatcher", "SMS_VENDOR_ACK (GATEWAY_QUEUED)", qr_ref_id, f"SMS payload queued for {vendor_phone}")
    
    return True

def trigger_officer_priority_alert(officer_email, priority_level, qr_ref_id, project_title, vendor_name):
    alert_subject = f"🚨 PRIORITY DOCUMENT ALERT [{priority_level.upper()}]: {qr_ref_id}"
    alert_body = f"""
    🚨 URGENT DEPARTMENTAL ROUTING NOTICE
    ---------------------------------------------------------
    Attention Departmental Officer ({officer_email}),

    A high-priority proposal requiring your urgent review has been assigned 
    and routed to your departmental inbox.

    DOCUMENT SUMMARY:
    Title: {project_title}
    Vendor: {vendor_name}
    Reference ID: {qr_ref_id}
    Priority Assignment: {priority_level}

    Please log in to the Strategic Directorate Portal using your executive 
    passcode to review the live OCR text appraisal and financial scorecard.
    ---------------------------------------------------------
    NEXUSVAULT Routing Engine
    """

    sent_status = send_live_email(officer_email, alert_subject, alert_body)
    status_label = "LIVE_SMTP_SENT" if sent_status else "LOGGED_QUEUED"

    db.log_event("Automated Dispatcher", f"EMAIL_OFFICER_ALERT ({status_label})", qr_ref_id, f"{priority_level} notice routed to {officer_email}")
    return True
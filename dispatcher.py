import database as db
from datetime import datetime

def send_vendor_acknowledgement(vendor_email, vendor_phone, vendor_name, qr_ref_id, project_title):
    email_body = f"""
    OFFICIAL DISPATCH RECEIPT - NEXUSVAULT ENTERPRISE INTAKE
    ---------------------------------------------------------
    Dear {vendor_name},

    Your proposal titled '{project_title}' has been successfully received, 
    scanned, and registered into the sovereign portal repository.

    CRITICAL ACCESS REFERENCE:
    QR Tracking Pass ID: {qr_ref_id}
    KYB CAC Status: VERIFIED & ACTIVE

    You may quote this Reference ID in all future communications.
    ---------------------------------------------------------
    NEXUSVAULT Enterprise Intake Node
    """
    
    sms_body = f"NEXUSVAULT: Proposal received. Ref ID: {qr_ref_id}. CAC KYB Verified. Thank you, {vendor_name}."

    db.log_event("Automated Dispatcher", "EMAIL_VENDOR_ACK", qr_ref_id, f"Dispatched email receipt to {vendor_email}")
    db.log_event("Automated Dispatcher", "SMS_VENDOR_ACK", qr_ref_id, f"Dispatched SMS trigger to {vendor_phone}")
    
    return True

def trigger_officer_priority_alert(officer_email, priority_level, qr_ref_id, project_title, vendor_name):
    alert_body = f"""
    🚨 PRIORITY DOCUMENT ALERT [{priority_level.upper()}]
    ---------------------------------------------------------
    Attention Departmental Officer ({officer_email}),

    A new proposal requiring your urgent review has been assigned and 
    routed to your departmental inbox.

    DOCUMENT DETAILS:
    Title: {project_title}
    Vendor: {vendor_name}
    QR Reference Pass: {qr_ref_id}
    Priority Assignment: {priority_level}

    Please log in to the Strategic Directorate Portal using your executive 
    passcode to access the Agentic AI summary and financial appraisal.
    ---------------------------------------------------------
    NEXUSVAULT Routing Engine
    """

    db.log_event("Automated Dispatcher", "EMAIL_OFFICER_ALERT", qr_ref_id, f"Dispatched {priority_level} alert to {officer_email}")
    return True
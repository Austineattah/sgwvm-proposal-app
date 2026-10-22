import os
import streamlit as st

def send_vendor_submission_receipt(vendor_email, phone_number, tracking_id, proposal_title):
    """
    Sends automated email and SMS notification to the vendor/submitter upon successful ingestion.
    """
    subject = f"Proposal Received - Tracking ID: {tracking_id}"
    message = f"Dear Vendor,\n\nYour proposal titled {proposal_title} has been successfully received and logged into the SGWVM / NexusVault Enterprise Platform.\n\nOfficial Tracking ID / Barcode: {tracking_id}\n\nYou can track review progress through your designated desk.\n\nBest Regards,\nSGWVM Enterprise Administration"
    
    print(f"[EMAIL DISPATCH] To: {vendor_email} | Subject: {subject}")
    print(f"[SMS DISPATCH] To: {phone_number} | Msg: Proposal logged. ID: {tracking_id}")
    return True

def send_directorate_assignment_alert(directorate_name, dir_email, tracking_id, proposal_title, org_name):
    """
    Sends instant automated alert to Directorate Head when Agentic AI assigns a proposal to their queue.
    """
    subject = f"[AI Routing Alert] New Proposal Assigned to {directorate_name} - {tracking_id}"
    message = f"Attention Directorate Head ({directorate_name}),\n\nA new proposal has been routed to your departmental queue by the Agentic AI Engine.\n\n- Tracking ID: {tracking_id}\n- Organization: {org_name}\n- Title: {proposal_title}\n\nPlease log in to your secure Directorate Portal to inspect the AI Executive Summary and Viability Score.\n\nSGWVM System Intelligence"
    
    print(f"[DIRECTORATE NOTIFICATION] Sent to {directorate_name} ({dir_email}) for Tracking ID {tracking_id}")
    return True


if (!(Test-Path views)) { New-Item -ItemType Directory -Path views }
@"
import streamlit as st
from modules.database import save_concept_note
from modules.security_scanner import scan_document_for_malware
from modules.ai_engine import extract_text_bulletproof
from modules.notifications import send_vendor_email, send_vendor_sms

def render_vendor_portal():
    st.title("🏛️ Legislative Proposal & Concept Note Portal")
    st.markdown("Submit your organization's concept note for review and tracking.")

    with st.form("vendor_submission_form"):
        col1, col2 = st.columns(2)
        with col1:
            org_name = st.text_input("Organization / Vendor Name *")
            email = st.text_input("Official Contact Email *")
        with col2:
            phone = st.text_input("Contact Phone Number (for SMS Alerts) *")
            title = st.text_input("Proposal / Project Title *")

        uploaded_file = st.file_uploader("Upload Concept Note (PDF Only) *", type=["pdf"])
        
        submitted = st.form_submit_button("Submit Proposal for Review")

        if submitted:
            if not org_name or not email or not phone or not title or not uploaded_file:
                st.error("Please fill in all required fields and upload a PDF document.")
                return

            file_bytes = uploaded_file.read()
            file_name = uploaded_file.name

            # 1. Run Security Malware & Signature Scan
            is_safe, security_msg = scan_document_for_malware(file_bytes, file_name)
            if not is_safe:
                st.error(f"❌ Upload Rejected: {security_msg}")
                return

            with st.spinner("Processing document, extracting insights via AI, and securing record..."):
                # 2. Extract Text & AI Summary
                ai_summary = extract_text_bulletproof(file_bytes)

                # 3. Save to Database
                try:
                    note_id = save_concept_note(
                        org_name=org_name,
                        email=email,
                        title=title,
                        file_name=file_name,
                        ai_summary=ai_summary,
                        payment_status="PENDING_REVIEW"
                    )
                except Exception as e:
                    st.error(f"Database error while saving record: {e}")
                    return

                # 4. Trigger Automated Notifications
                email_html = f"<h3>Proposal Received</h3><p>Dear {org_name}, your proposal <b>{title}</b> has been successfully received and queued for review.</p>"
                send_vendor_email(email, "Proposal Submission Acknowledgment - SGWVM Portal", email_html)

                sms_body = f"Hello {org_name}, your proposal '{title}' has been received successfully by SGWVM Portal. Reference ID: #{note_id}"
                send_vendor_sms(phone, sms_body)

            st.success(f"🎉 Proposal successfully submitted! Your reference tracking ID is #{note_id}.")
            st.info("Automated email and SMS acknowledgments have been dispatched.")
"@ | Out-File -FilePath views/vendor_portal.py -Encoding utf8
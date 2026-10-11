import streamlit as st
import os
from modules import database, ai_engine, security_scanner, notifications

def render():
    st.title("🏛️ Legislative Vendor Proposal Portal")
    st.markdown("Submit your technical proposals, security-vetted documentation, and deliverables for committee evaluation.")

    with st.form("vendor_submission_form"):
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input("Company / Organization Name")
            email = st.text_input("Official Contact Email")
            phone = st.text_input("Phone Number (e.g. 08012345678)")
        with col2:
            project_title = st.text_input("Project / Initiative Title")
            project_category = st.selectbox("Project Category", ["Legislative Technology", "Constituency Outreach", "Access Control & Security", "Infrastructure & Logistics", "Digital Archive & Records"])

        uploaded_file = st.file_uploader("Upload Proposal Document (PDF)", type=["pdf"])
        
        submit_btn = st.form_submit_button("Submit Proposal for Review")

        if submit_btn:
            if not company_name or not email or not phone or not project_title or not uploaded_file:
                st.error("Please fill in all required fields (including phone number) and upload your proposal PDF.")
            else:
                # Save uploaded file temporarily
                os.makedirs("uploads", exist_ok=True)
                file_path = os.path.join("uploads", uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # 1. Security Scan
                is_safe, scan_msg = security_scanner.scan_file(file_path)
                if not is_safe:
                    st.error(f"Security Validation Failed: {scan_msg}")
                    return

                # 2. Multi-engine PDF Text Extraction & AI Summary
                with st.spinner("Extracting text and generating AI summary..."):
                    extracted_text = ai_engine.extract_text_bulletproof(file_path)
                    ai_summary = ai_engine.summarize_proposal(extracted_text)

                # 3. Save to Database
                proposal_id = database.save_proposal(
                    company_name=company_name,
                    email=email,
                    phone=phone,
                    project_title=project_title,
                    project_category=project_category,
                    ai_summary=ai_summary,
                    file_path=file_path
                )

                # 4. Send Automated Email & SMS Acknowledgements
                notifications.send_submission_acknowledgement(email, phone, company_name, project_title, proposal_id)

                st.success(f"Proposal successfully submitted! Reference ID: #{proposal_id}. Automated email and SMS acknowledgements have been dispatched.")

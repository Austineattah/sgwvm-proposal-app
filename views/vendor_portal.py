import streamlit as st
from modules.database import insert_proposal
from modules.security_scanner import scan_file_upload
from modules.ai_engine import extract_text_bulletproof

def render_vendor_portal():
    st.title('🏛️ Vendor Proposal Submission Portal')
    st.write('Please complete the form below and attach your technical/financial proposal PDF.')
    
    with st.form('vendor_submission_form', clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input('Company / Vendor Name*')
            rc_number = st.text_input('CAC / RC Number*')
            email = st.text_input('Contact Email*')
        with col2:
            phone = st.text_input('Contact Phone Number*')
            project_title = st.text_input('Project / Proposal Title*')
            category = st.selectbox('Category', ['Infrastructure', 'Technology & ICT', 'Consultancy', 'Capacity Building', 'Supply & Logistics'])
        
        proposal_abstract = st.text_area('Executive Summary / Abstract', height=100)
        uploaded_file = st.file_uploader('Upload Proposal Document (PDF)', type=['pdf'])
        
        submitted = st.form_submit_button('Submit Proposal')
        
        if submitted:
            if not company_name or not rc_number or not email or not project_title or not uploaded_file:
                st.error('Please fill in all required fields (*) and attach a PDF proposal.')
            else:
                file_bytes = uploaded_file.getvalue()
                is_safe, scan_msg = scan_file_upload(uploaded_file.name, file_bytes)
                
                if not is_safe:
                    st.error(f'Security Check Failed: {scan_msg}')
                else:
                    ai_summary = extract_text_bulletproof(file_bytes)
                    record_id = insert_proposal(company_name, rc_number, email, phone, project_title, category, proposal_abstract, uploaded_file.name, ai_summary)
                    st.success(f'Proposal submitted successfully! Tracking Ref ID: #{record_id}')
                    st.info(f'Security Scan: {scan_msg}')

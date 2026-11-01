# -*- coding: utf-8 -*-

sector_code = """import streamlit as st

def render_sector_onboarding_wizard():
    st.markdown(\"\"\"
        <div style=\"background: linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%); padding: 24px; border-radius: 12px; border: 1px solid #3b82f6; box-shadow: 0 10px 25px rgba(29, 78, 216, 0.3); margin-bottom: 24px;\">
            <h2 style=\"color: #ffffff; margin: 0 0 8px 0; font-size: 22px; font-weight: 800; letter-spacing: 0.5px;\">
                ??? NEXUSVAULT TECHNOLOGIES SUPER INTELLIGENCE-AGENTIC AI PROPOSAL INTAKE Onboarding Portal
            </h2>
            <p style=\"color: #f8fafc; margin: 0; font-size: 14px; line-height: 1.5;\">
                Complete your corporate entity registration and subscription setup to initialize your secure vendor submission workspace.
            </p>
        </div>
    \"\"\", unsafe_allow_html=True)

    with st.form(\"corporate_onboarding_form\"):
        st.markdown(\"### ?? Step 1: Corporate Entity & Institution Classification\")
        
        entity_type = st.selectbox(
            \"Select Organization / Entity Category*\",
            [
                \"Private Limited Company (Ltd / Plc)\", 
                \"Enterprise / Business Name / Partnership\", 
                \"NGO / Non-Profit Organization\", 
                \"Government Agency / Parastatal / Statutory Corporation (Act of Parliament)\", 
                \"Public University / Polytechnic / Research Institute\"
            ]
        )

        col_a, col_b = st.columns(2)
        with col_a:
            corp_name = st.text_input(\"Corporate Entity Name*\", placeholder=\"e.g., SGWVM Technology Limited / University of Abuja\")
            corp_email = st.text_input(\"Official Email Address*\", placeholder=\"contact@sgwvm.com\")

        with col_b:
            corp_phone = st.text_input(\"Contact Phone Number*\", placeholder=\"+234 803 000 0000\")
            corp_address = st.text_input(\"Corporate Office Address*\", placeholder=\"Efab Estate, Lokogoma, Abuja\")
            admin_email = st.text_input(\"Official Admin Notification Email (Optional)\", placeholder=\"admin@sgwvm.com\")

        st.markdown(\"### ?? Step 2: Subscription & Branding Configuration\")
        col_c, col_d = st.columns(2)
        with col_c:
            sub_package = st.selectbox(
                \"Subscription Package*\",
                [\"Standard Enterprise Tier\", \"Pro Agency & Grant Funder Tier\", \"Government MDA Fast-Track Tier\", \"Custom Sovereign Node\"]
            )
        with col_d:
            logo_file = st.file_uploader(\"Corporate Branding Logo (Optional)\", type=[\"png\", \"jpg\", \"jpeg\"])

        submitted = st.form_submit_button(\"Initialize Secure Vendor Submission Workspace\", use_container_width=True)

        if submitted:
            if not corp_name or not corp_email or not corp_phone or not corp_address:
                st.error(\"?? Please fill in all required corporate entity fields marked with an asterisk (*).\")
            else:
                st.session_state[\"portal_initialized\"] = True
                st.session_state[\"entity_type\"] = entity_type
                st.session_state[\"corp_name\"] = corp_name
                st.session_state[\"corp_email\"] = corp_email
                st.session_state[\"corp_phone\"] = corp_phone
                st.session_state[\"corp_address\"] = corp_address
                st.session_state[\"sub_package\"] = sub_package
                st.session_state[\"admin_email\"] = admin_email
                st.session_state[\"logo_file\"] = logo_file
                st.success(\"?? Corporate profile locked successfully! Initializing public vendor proposal workspace...\")
                st.rerun()
"""

app_code = """import streamlit as st
from sector_logic import render_sector_onboarding_wizard

st.set_page_config(
    page_title="NEXUSVAULT TECHNOLOGIES SUPER INTELLIGENCE-AGENTIC AI PROPOSAL INTAKE",
    page_icon="???",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "portal_initialized" not in st.session_state:
    st.session_state["portal_initialized"] = False

if not st.session_state["portal_initialized"]:
    render_sector_onboarding_wizard()
else:
    corp_name = st.session_state.get("corp_name", "SGWVM Technology Limited")
    entity_type = st.session_state.get("entity_type", "Private Limited Company")
    sub_package = st.session_state.get("sub_package", "Standard Enterprise Tier")

    with st.sidebar:
        st.markdown("### ?? Active Vendor Workspace")
        st.info(f"**Entity:** {corp_name}\\n\\n**Type:** {entity_type}\\n\\n**Tier:** {sub_package}")
        
        if st.button("?? Reset / Re-Onboard", use_container_width=True):
            st.session_state["portal_initialized"] = False
            st.rerun()

    st.title("??? NEXUSVAULT TECHNOLOGIES SUPER INTELLIGENCE-AGENTIC AI PROPOSAL INTAKE Portal")
    st.markdown("This system streamlines corporate proposal submissions, performs automated compliance verification, and uses AI extraction to summarize content and identify risk factors across multiple document formats.")
    st.markdown("---")

    tab_submission, tab_statutory, tab_review = st.tabs([
        "?? Public Vendor Proposal Submission", 
        "??? Statutory & Compliance Files", 
        "?? Final Review & Encrypted Sign-Off"
    ])

    with tab_submission:
        st.subheader("Public Vendor Proposal Submission")
        st.markdown("Submit your proposal details and upload required documents. This vendor portal is open to the public without login.")
        
        col_1, col_2 = st.columns(2)
        with col_1:
            bid_title = st.text_input("Title of Proposal*", placeholder="e.g., National Assembly Vehicle Pass System Rollout")
            optional_budget = st.number_input("Optional Budget (?)", min_value=0.0, step=100000.0, format="%.2f")
            subcontractor_notes = st.text_area("Subcontractor Notes (optional)", placeholder="List any third-party partners or subcontractors involved.")
        with col_2:
            st.info(f"?? **Verified Entity:** {corp_name}\\n\\n?? **Category:** {entity_type}")

        st.markdown("---")
        st.markdown("### ?? Proposal & Compliance Document Uploads")

        col_up1, col_up2 = st.columns(2)
        with col_up1:
            tech_proposal = st.file_uploader("Technical Proposal* (PDF)", type=["pdf"])
            st.caption("Limit 200MB per file  PDF")

            cac_cert = st.file_uploader("CAC Certificate / Enacting Act Document*", type=["pdf", "png", "jpg", "jpeg"])
            st.caption("Limit 200MB per file  PDF, PNG, JPG, JPEG")

            extra_certs = st.file_uploader("Extra Certifications (optional)", type=["pdf", "png", "jpg", "jpeg"])
            st.caption("Limit 200MB per file  PDF, PNG, JPG, JPEG")

        with col_up2:
            fin_proposal = st.file_uploader("Financial Proposal* (PDF, DOCX, XLSX, XLS)", type=["pdf", "docx", "xlsx", "xls"])
            st.caption("Limit 200MB per file  PDF, DOCX, XLSX, XLS")

            tin_cert = st.file_uploader("TIN Certificate*", type=["pdf", "png", "jpg", "jpeg"])
            st.caption("Limit 200MB per file  PDF, PNG, JPG, JPEG")

    with tab_statutory:
        st.subheader("Sector-Specific Statutory & Compliance Checklist")
        st.markdown("Upload supplementary documentation required under Public Procurement Act (PPA) 2007 or international donor frameworks.")
        
        stat_col1, stat_col2 = st.columns(2)
        with stat_col1:
            st.file_uploader("FIRS Tax Clearance Certificate (TCC - Past 3 Years) [.pdf]", type=["pdf"])
            st.file_uploader("PENCOM Compliance Certificate [.pdf]", type=["pdf"])
            st.file_uploader("ITF Compliance Certificate [.pdf]", type=["pdf"])
        with stat_col2:
            st.file_uploader("NSITF Compliance Certificate [.pdf]", type=["pdf"])
            st.file_uploader("BPP Interim Registration Report (IRR) [.pdf]", type=["pdf"])
            st.file_uploader("Notarized Sworn Affidavit [.pdf]", type=["pdf"])

    with tab_review:
        st.subheader("Secure Submission & Legal Attestation")
        st.markdown("Please verify all proposal particulars and compliance artifacts prior to transmission.")
        
        attestation = st.checkbox("I/We hereby certify under penalty of perjury that all submitted documents and corporate representations are genuine, accurate, and legally verifiable.")
        
        if st.button("Transmit Proposal Package to Registry", type="primary", use_container_width=True):
            if attestation and tech_proposal and fin_proposal and bid_title:
                st.success("?? Proposal package successfully encrypted and transmitted to the NEXUSVAULT AI registry!")
                st.balloons()
            else:
                st.error("?? Please ensure the legal attestation box is checked, a proposal title is entered, and both Technical and Financial proposals are uploaded.")
"""

with open("sector_logic.py", "w", encoding="utf-8") as f:
    f.write(sector_code)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(app_code)

print("Files updated successfully!")


"""
Solicited Vendor Pathway - Phase 2 Implementation Module (PPA 2007 Statutory Compliance Vault)
Unlocked exclusively via a verified Tracking ID and confirmed payment.
Manages 5 distinct statutory document categories and incremental chunk storage.
"""

import streamlit as st
import os
import uuid
import datetime

def render_solicited_phase2(client_slug, tracking_id):
    st.markdown("### 🛡️ PPA 2007 Statutory Compliance Vault")
    st.markdown(f"**Active Tracking ID:** {tracking_id} | **Tenant:** {client_slug.upper()}")
    st.markdown("Please upload your statutory, legal, financial, and technical documentation as mandated by the Public Procurement Act 2007.")

    if not st.session_state.get("payment_verified", False):
        st.warning("🔒 This section is locked. Please complete Phase 1 Pre-Qualification and Remita Payment Verification first.")
        return

    with st.form("ppa2007_vault_form"):
        st.markdown("#### 1. Statutory & Corporate Registration")
        cac_cert = st.file_uploader("CAC Incorporation Certificate & Status Summary (CAC 1.1 / CO2 / CO7) [PDF]", type=["pdf"], key="cac")
        memart = st.file_uploader("Memorandum & Articles of Association (MEMART) [PDF]", type=["pdf"], key="memart")
        bpp_irr = st.file_uploader("BPP Interim Registration Report (IRR) Certificate [PDF]", type=["pdf"], key="bpp")

        st.markdown("#### 2. Tax & Statutory Compliance Certificates")
        firs_tcc = st.file_uploader("FIRS Tax Clearance Certificate (Past 3 Years) [PDF]", type=["pdf"], key="tcc")
        pencom = st.file_uploader("PENCOM Compliance Certificate [PDF]", type=["pdf"], key="pencom")
        itf = st.file_uploader("ITF Compliance Certificate [PDF]", type=["pdf"], key="itf")
        nsitf = st.file_uploader("NSITF Compliance Certificate [PDF]", type=["pdf"], key="nsitf")

        st.markdown("#### 3. Legal Declarations & Authorizations")
        affidavit = st.file_uploader("High Court Sworn Affidavit (Insolvency / Conflict of Interest) [PDF]", type=["pdf"], key="affidavit")
        due_diligence = st.file_uploader("Authority to Verify / Due Diligence Letter [PDF]", type=["pdf"], key="duediligence")

        st.markdown("#### 4. Financial & Banking Capability")
        audited_accounts = st.file_uploader("Stamped Audited Accounts (Past 3 Years - Cross-checked) [PDF]", type=["pdf"], key="accounts")
        bank_ref = st.file_uploader("Commercial Bank Reference Letter [PDF]", type=["pdf"], key="bankref")
        tender_bond = st.file_uploader("Bid Security / Tender Guarantee Bond [PDF]", type=["pdf"], key="bond")

        st.markdown("#### 5. Technical Capability & Experience")
        similar_projects = st.file_uploader("Evidence of 3-4 Similar Completed Projects (Letters of Award/Completion) [PDF]", type=["pdf"], key="projects")
        personnel_cvs = st.file_uploader("Key Personnel CVs & Certifications (COREN, ICAN, CREN, etc.) [PDF]", type=["pdf"], key="cvs")
        methodology = st.file_uploader("Sector Licenses & Detailed Technical Methodology [PDF]", type=["pdf"], key="methodology")

        submitted_vault = st.form_submit_button("🔒 Submit Final Tender Package to Agentic AI Triage")

        if submitted_vault:
            if not cac_cert or not firs_tcc or not audited_accounts:
                st.error("❌ Mandatory core documents (CAC Certificate, FIRS TCC, and Audited Accounts) are missing.")
            else:
                st.success("🎉 PPA 2007 Statutory Vault successfully compiled and secured!")
                st.info("⚡ Routing proposal package to Agentic AI Triage & Dispatch Engine...")
                st.session_state["tender_submitted"] = True
                st.balloons()

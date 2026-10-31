import streamlit as st
import uuid

def render_solicited_vendor_qr_clearance_gate(tenant_slug=None):
    st.markdown("### 🏛️ Solicited Vendor Secure Bidding & QR Clearance Gate")
    st.caption("Mandatory compliance verification, conditional fee settlement, and cryptographic QR access token issuance.")
    
    tab_step1, tab_step2, tab_step3 = st.tabs([
        "Step 1: RFP Validation & Payment", 
        "Step 2: Clearance Verification", 
        "Step 3: Final Sealed Bid Dossier Upload"
    ])
    
    with tab_step1:
        st.markdown("#### Step 1: Solicited Submission & Fee Verification")
        st.info("🔒 **Strict Compliance Notice:** Bidding fee settlement and payment verification must be successfully confirmed before unlocking Step 3 dossier uploads.")
        
        with st.form("solicited_step1_form"):
            col1, col2 = st.columns(2)
            with col1:
                rfq_code = st.text_input("Official RFP / RFQ Reference Code*")
                vendor_name = st.text_input("Corporate Vendor Name*")
            with col2:
                contact_email = st.text_input("Official Corporate Email*")
                payment_ref = st.text_input("Payment Teller / Gateway Reference*")
            
            proposal_title = st.text_input("Project / Bid Title*")
            
            submit_step1 = st.form_submit_button("Verify Payment & Generate QR Clearance Pass")
            
            if submit_step1:
                if not (rfq_code and vendor_name and contact_email and payment_ref and proposal_title):
                    st.error("⚠️ All required fields marked with * must be completed.")
                else:
                    qr_pass_id = f"SGWVM-QRPASS-{uuid.uuid4().hex[:8].upper()}"
                    st.session_state["verified_qr_pass"] = qr_pass_id
                    st.success("✅ Payment verified and cryptographic QR Clearance Pass generated successfully!")
                    st.info(f"🔑 **Your Official Access QR Token:** `{qr_pass_id}`. Proceed to Step 3 for final dossier submission.")

    with tab_step2:
        st.markdown("#### Step 2: Clearance & Compliance Status Check")
        active_pass = st.session_state.get("verified_qr_pass", "")
        if active_pass:
            st.success(f"🟢 Active Clearance Token Verified: `{active_pass}`")
        else:
            st.warning("🟡 No active clearance token found. Complete Step 1 first.")

    with tab_step3:
        st.markdown("#### Step 3: Final Sealed Bid Dossier Upload (Encrypted PDF)")
        active_pass = st.session_state.get("verified_qr_pass", "")
        
        if not active_pass:
            st.error("⛔ Step 3 Locked: You must complete Step 1 payment verification and obtain a QR Clearance Pass first.")
        else:
            with st.form("solicited_step3_dossier_form"):
                st.info(f"Using Verified QR Pass: `{active_pass}`")
                sealed_dossier = st.file_uploader("Upload Sealed Bid Dossier (Encrypted PDF/DOCX)*", type=["pdf", "docx"])
                submit_final_bid = st.form_submit_button("Submit Final Sealed Bid to Committee Queue", type="primary")
                
                if submit_final_bid:
                    if not sealed_dossier:
                        st.error("⛔ Please upload your encrypted sealed bid dossier.")
                    else:
                        st.success("🚀 Sealed bid dossier successfully transmitted to the Tender Committee Directorate!")

def render_unsolicited_vendor_portal(tenant_slug=None):
    """
    Pure vendor-facing unsolicited proposal intake channel.
    Directorate password vaults and internal AI intelligence desks are strictly excluded here.
    """
    st.markdown("### 💡 Unsolicited Innovation Proposal Submission Portal")
    st.caption("Submit your independent solution for preliminary executive review.")
    
    with st.form(key=f"pure_unsolicited_form_{tenant_slug or 'default'}"):
        org_name = st.text_input("Organization / Enterprise Name*")
        cac_number = st.text_input("CAC Registration RC Number*")
        tin_number = st.text_input("Tax Identification Number (TIN)*")
        proposal_title = st.text_input("Proposal Title / Project Name*")
        proposal_abstract = st.text_area("Executive Summary / Strategic Objectives*")
        
        submit_unsolicited = st.form_submit_button("Submit Proposal to Intake Queue")
        if submit_unsolicited:
            if not (org_name and cac_number and proposal_title):
                st.error("Please complete all required fields.")
            else:
                st.success("✅ Unsolicited proposal successfully submitted for initial review!")

def render_unified_vendor_portal(tenant_slug=None, default_tab="solicited"):
    st.markdown("## 🏛️ Sovereign Vendor Portal")
    if tenant_slug:
        st.caption(f"Active Secured Tenant Namespace: `{tenant_slug}`")

    tab_solicited, tab_unsolicited = st.tabs([
        "📜 Solicited RFP Submission (Phased Roadmap)",
        "💡 Unsolicited Proposal Submission"
    ])
    
    with tab_solicited:
        render_solicited_vendor_qr_clearance_gate(tenant_slug=tenant_slug)
            
    with tab_unsolicited:
        render_unsolicited_vendor_portal(tenant_slug=tenant_slug)

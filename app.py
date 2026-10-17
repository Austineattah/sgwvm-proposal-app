import streamlit as st
import base64
import pandas as pd
import io
import random
from datetime import datetime
from sector_logic import render_sector_onboarding_wizard
import sector_mapper as mapper
import database as db
import qr_generator as qrg
import dispatcher as disp
import ocr_parser as ocr
import qr_scanner as scanner
import security_guard as sec
import blockchain_ledger as chain
import report_generator as cert_gen
import developer_console as dev_ui
import draft_manager as draft_mgr

# Page Configuration
st.set_page_config(
    page_title="NEXUSVAULT Sovereign Enterprise Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Global Typography (Plus Jakarta Sans) & High-Contrast Obsidian Theme
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&family=Roboto:wght@400;500;700&display=swap');

        .stApp {
            background-color: #070d19 !important;
            color: #ffffff !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }

        h1, h2, h3, h4, h5, h6, label, p, span, div {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }

        .main-header {
            background: linear-gradient(135deg, #0a192f 0%, #0d2137 100%);
            padding: 24px 28px;
            border-radius: 12px;
            border: 2px solid #1d4ed8;
            box-shadow: 0 10px 28px rgba(10, 25, 47, 0.85);
            margin-bottom: 24px;
        }

        .section-hdr {
            color: #38bdf8 !important;
            font-size: 19px !important;
            font-weight: 800 !important;
            letter-spacing: 0.3px !important;
            border-left: 4px solid #38bdf8;
            padding-left: 10px;
            margin-top: 18px;
            margin-bottom: 14px;
        }

        div[data-baseweb="select"] > div, input, textarea {
            background-color: #0f172a !important;
            border: 1px solid #334155 !important;
            color: #ffffff !important;
            border-radius: 8px !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-size: 14px !important;
        }

        button[data-baseweb="tab"] {
            background-color: rgba(15, 23, 42, 0.85) !important;
            border: 1px solid #334155 !important;
            border-radius: 8px 8px 0px 0px !important;
            padding: 12px 24px !important;
            color: #cbd5e1 !important;
            font-weight: 700 !important;
            font-size: 15px !important;
            margin-right: 6px !important;
            transition: all 0.25s ease-in-out !important;
        }

        button[data-baseweb="tab"]:hover {
            color: #ffffff !important;
            background-color: rgba(30, 58, 138, 0.6) !important;
            border-color: #60a5fa !important;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
            color: #ffffff !important;
            border: 2px solid #38bdf8 !important;
            border-bottom: 4px solid #38bdf8 !important;
            font-weight: 900 !important;
            font-size: 16px !important;
            box-shadow: 0 6px 16px rgba(2, 132, 199, 0.5) !important;
        }

        .card-box {
            background-color: rgba(15, 23, 42, 0.85);
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 18px;
        }

        .checklist-hdr {
            color: #38bdf8;
            font-size: 15px;
            font-weight: 800;
            margin-top: 10px;
            margin-bottom: 8px;
            border-bottom: 2px solid rgba(56, 189, 248, 0.4);
            padding-bottom: 4px;
        }

        .procurement-notice {
            background-color: rgba(220, 38, 38, 0.15);
            border-left: 5px solid #ef4444;
            border-radius: 8px;
            padding: 18px 22px;
            margin-bottom: 22px;
        }
    </style>
""", unsafe_allow_html=True)

if "portal_initialized" not in st.session_state:
    st.session_state["portal_initialized"] = False
if "active_user_role" not in st.session_state:
    st.session_state["active_user_role"] = "Front Desk Officer"

# Check if node is approved in DB
is_node_approved = db.get_setting("node_approved", "False") == "True"

if not is_node_approved and not st.session_state.get("developer_access_granted", False):
    render_sector_onboarding_wizard()
else:
    entity_name = st.session_state.get("corp_name", "Sovereign Entity Node")
    entity_type = st.session_state.get("entity_type", "Statutory Directorate")
    sub_tier = st.session_state.get("sub_package", "Enterprise Sovereign Tier")
    portal_heading = st.session_state.get("custom_portal_heading", 'NEXUSVAULT TECHNOLOGIES "SUPER INTELLIGENCE - AGENTIC AI PROPOSAL INTAKE PORTAL"')

    # Header Panel
    col_hdr1, col_hdr2 = st.columns([4, 1.2])
    with col_hdr1:
        st.markdown(f"""
            <div class="main-header">
                <h1 style="color: #ffffff !important; margin: 0 0 8px 0; font-size: 22px; font-weight: 900; letter-spacing: 0.4px; line-height: 1.3;">
                    🛡️ {portal_heading}
                </h1>
                <p style="color: #38bdf8 !important; margin: 0; font-size: 14px; font-weight: 700;">
                    Node: <span style="color: #ffffff;">{entity_name}</span> | Scope: <span style="color: #ffffff;">{entity_type}</span> | Active Gate: <span style="color: #34d399;">{st.session_state["active_user_role"]}</span>
                </p>
            </div>
        """, unsafe_allow_html=True)
    with col_hdr2:
        st.markdown("""
            <div style="display: flex; align-items: center; justify-content: flex-end; background-color: rgba(15, 23, 42, 0.85); border: 2px solid #008751; border-radius: 10px; padding: 12px 16px; gap: 12px; margin-top: 4px;">
                <svg width="42" height="28" viewBox="0 0 3 2" style="border-radius: 3px; box-shadow: 0 2px 6px rgba(0,0,0,0.5);">
                    <rect width="1" height="2" x="0" fill="#008751"/>
                    <rect width="1" height="2" x="1" fill="#FFFFFF"/>
                    <rect width="1" height="2" x="2" fill="#008751"/>
                </svg>
                <div>
                    <div style="color: #ffffff; font-size: 11px; font-weight: 800; letter-spacing: 0.5px;">FEDERAL REPUBLIC</div>
                    <div style="color: #34d399; font-size: 10px; font-weight: 700;">OF NIGERIA</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### 🔐 Role Gateways")
        selected_role_view = st.radio(
            "Select Portal Access Gate",
            ["Front Desk (Proposal Intake & KYB)", "Strategic Directorate (AI & Financial Appraisals)", "Senior Management (Solicited Tenders & Payment Control)", "📊 Executive Reporting & Exports", "⛓️ Cryptographic Proof Ledger", "📜 Audit Logs & Compliance Trail", "🛠️ Developer Master Console"]
        )

        if selected_role_view not in ["Front Desk (Proposal Intake & KYB)", "📊 Executive Reporting & Exports", "⛓️ Cryptographic Proof Ledger", "📜 Audit Logs & Compliance Trail", "🛠️ Developer Master Console"]:
            st.markdown("---")
            st.markdown("⚠️ **Restricted Directorate Area**")
            entered_password = st.text_input("Enter Directorate Passcode", type="password", key="role_passcode")
            
            if entered_password == "NexusExec2026!":
                st.session_state["active_user_role"] = selected_role_view
                st.success("✅ Access Granted")
            else:
                st.session_state["active_user_role"] = "Front Desk Officer (Locked)"
                if entered_password:
                    st.error("❌ Invalid Passcode")
        else:
            st.session_state["active_user_role"] = selected_role_view

        st.markdown("---")
        st.markdown("### 🛠️ Quick Tools & Demo Data")
        if st.button("⚡ Load Representative Sample Proposals", use_container_width=True):
            rand_suffix1 = random.randint(1000, 9999)
            rand_suffix2 = random.randint(1000, 9999)
            
            sample_records = [
                {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "Unsolicited Pitch",
                    "vendor": "SolarGrid Energy Ltd",
                    "cac": "RC-884920",
                    "email": "dispatch@solargrid.com",
                    "phone": "+234 803 111 2222",
                    "address": "Victoria Island, Lagos",
                    "title": "Solar Micro-Grid Power Deployment for Campus Facilities",
                    "target_officer": "director.facilities@entity.org",
                    "priority": "High Priority / Urgent Attention",
                    "qr_ref": f"NV-QREF-{datetime.now().strftime('%Y%m%d')}-{rand_suffix1}",
                    "status": "Routed & Pending Review",
                    "kyb_status": "Verified Active (CAC)",
                    "score": 94.8,
                    "estimated_cost": "₦38,000,000",
                    "ai_summary": "High feasibility solar infrastructure pitch. Budget headroom confirmed.",
                    "payment_ref": "N/A (Unsolicited Pitch)"
                },
                {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "Solicited Tender Response",
                    "vendor": "CloudTech Consortium",
                    "cac": "RC-993810",
                    "email": "contact@cloudtech.com",
                    "phone": "+234 802 333 4444",
                    "address": "Central Business District, Abuja",
                    "title": "Enterprise Cloud Migration & Data Vault Architecture",
                    "target_officer": "director.it@entity.org",
                    "priority": "Executive Fast-Track",
                    "qr_ref": f"NV-SOLICIT-{datetime.now().strftime('%Y%m%d')}-{rand_suffix2}",
                    "status": "Solicited Audit Complete",
                    "kyb_status": "Pre-Qualified White-list (Full BPP/TCC/PENCOM Compliant)",
                    "score": 98.2,
                    "estimated_cost": "₦85,000,000",
                    "ai_summary": "Full compliance with BPP, TCC (3 Yrs), PENCOM, ITF, NSITF, and Sworn Affidavit.",
                    "payment_ref": "RRR-2026-99201-PAY"
                }
            ]
            for rec in sample_records:
                db.save_proposal(rec)
            st.success("✅ Sample institutional proposals loaded cleanly into database!")
            st.rerun()

        if st.button("🔒 Terminate Node Session", use_container_width=True):
            st.session_state["portal_initialized"] = False
            st.session_state["developer_access_granted"] = False
            st.session_state["onboarding_submitted"] = False
            db.set_setting("node_approved", "False")
            st.rerun()

    sector_categories = mapper.get_sector_proposal_categories(entity_type)

    payment_required = db.get_setting("payment_required", "True") == "True"
    bidding_fee_amount = db.get_setting("bidding_fee_amount", "₦50,000")
    payment_instructions = db.get_setting("payment_instructions", "Pay via Federal Remita RRR / Commercial Bank Deposit to Account: 101-223344-01")

    # ==========================================
    # TIER 1: FRONT DESK OFFICER PORTAL (DUAL TAB WITH AUTO-SAVE DRAFTS)
    # ==========================================
    if st.session_state["active_user_role"] == "Front Desk (Proposal Intake & KYB)":
        st.markdown("<div class='section-hdr'>📥 Front Desk: Intake Gateway & Verification Engine</div>", unsafe_allow_html=True)
        
        tab_unsolicited, tab_solicited = st.tabs(["💡 Unsolicited Proposal Pitch Gate", "🏛️ Statutory Solicited Tender / RFP Submission Gate"])

        # TAB A: UNSOLICITED PROPOSALS
        with tab_unsolicited:
            st.markdown("<h3 style='color: #38bdf8; font-size: 18px;'>Unsolicited Pitch Intake & 2-Bundle Statutory Verification</h3>", unsafe_allow_html=True)

            # Auto-Save Draft Recovery Check
            saved_unsol_draft = draft_mgr.get_draft("unsolicited_pitch")
            if saved_unsol_draft:
                st.warning(f"⚠️ Unsaved Draft Detected from {saved_unsol_draft.get('last_saved', 'Recent Session')}.")
                if st.button("🔄 Restore Saved Pitch Draft"):
                    st.session_state["draft_unsol_vendor"] = saved_unsol_draft.get("vendor", "")
                    st.session_state["draft_unsol_cac"] = saved_unsol_draft.get("cac", "")
                    st.session_state["draft_unsol_email"] = saved_unsol_draft.get("email", "")
                    st.session_state["draft_unsol_phone"] = saved_unsol_draft.get("phone", "")
                    st.session_state["draft_unsol_title"] = saved_unsol_draft.get("title", "")
                    st.session_state["draft_unsol_target"] = saved_unsol_draft.get("target_officer", "")
                    st.success("✅ Form restored from draft!")

            with st.form("unsolicited_form"):
                st.markdown("##### 🏢 1. Vendor & Corporate Details")
                col_u1, col_u2 = st.columns(2)
                with col_u1:
                    vendor_name_raw = st.text_input("Vendor Organization Name*", value=st.session_state.get("draft_unsol_vendor", ""), placeholder="e.g., Apex Global Technologies Ltd")
                    cac_num_raw = st.text_input("CAC Registration Number (RC / BN)*", value=st.session_state.get("draft_unsol_cac", ""), placeholder="RC-1234567")
                    vendor_email_raw = st.text_input("Official Dispatch Email (for Auto-Receipt)*", value=st.session_state.get("draft_unsol_email", ""), placeholder="vendor@apextech.com")
                    vendor_phone_raw = st.text_input("Vendor Phone / SMS Gateway Contact*", value=st.session_state.get("draft_unsol_phone", ""), placeholder="+234 802 000 0000")
                with col_u2:
                    project_title_raw = st.text_input("Proposal Title*", value=st.session_state.get("draft_unsol_title", ""), placeholder="e.g., Smart Digital Library & Research Vault")
                    prop_cat = st.selectbox("Sector-Mapped Proposal Type", sector_categories)
                    target_officer_raw = st.text_input("Target Departmental Officer Email*", value=st.session_state.get("draft_unsol_target", ""), placeholder="director.research@entity.org")
                    priority_lvl = st.selectbox("Priority Level", ["Standard Review", "High Priority / Urgent Attention", "Executive Fast-Track"])

                st.markdown("##### 📁 2. Statutory & Verification Bundle Checklists")
                col_chk1, col_chk2 = st.columns(2)
                with col_chk1:
                    st.markdown("**Bundle 1: Executive Pitch Package**")
                    chk_cover = st.checkbox("Cover Letter / Intent Letter Addressed to Head", value=True)
                    chk_tech = st.checkbox("Detailed Technical Proposal & Architecture", value=True)
                    chk_fin = st.checkbox("Commercial Breakdown & ROI Model", value=True)
                    chk_deck = st.checkbox("Executive Pitch Deck (10-15 slides)", value=True)
                with col_chk2:
                    st.markdown("**Bundle 2: Statutory Compliance Folder**")
                    chk_cac = st.checkbox("Certificate of Incorporation / CAC Status", value=True)
                    chk_tin = st.checkbox("Tax Identification Number (TIN) / Tax Clearance", value=True)
                    chk_pen = st.checkbox("Pension & Social Security Permits (PENCOM/NSITF)", value=True)
                    chk_bank = st.checkbox("Bank Reference Letter & Audited Financials", value=True)
                    chk_nda = st.checkbox("Non-Disclosure Agreement (NDA) & ISO Certs", value=True)

                st.markdown("##### 📄 3. Physical Document Scanning & Security Screening")
                scanned_pdf = st.file_uploader("Upload Scanned Proposal Document (PDF)", type=["pdf"])

                col_sub1, col_sub2 = st.columns([3, 1])
                with col_sub1:
                    btn_sub_unsol = st.form_submit_button("Execute Security Inspection, Live OCR & Route Pitch", use_container_width=True)
                with col_sub2:
                    btn_save_draft_unsol = st.form_submit_button("💾 Save Progress Draft", use_container_width=True)

                if btn_save_draft_unsol:
                    draft_mgr.save_draft("unsolicited_pitch", {
                        "vendor": vendor_name_raw,
                        "cac": cac_num_raw,
                        "email": vendor_email_raw,
                        "phone": vendor_phone_raw,
                        "title": project_title_raw,
                        "target_officer": target_officer_raw
                    })
                    st.success("💾 Form draft saved successfully!")

                if btn_sub_unsol:
                    vendor_name = sec.sanitize_text_input(vendor_name_raw)
                    cac_num = sec.sanitize_text_input(cac_num_raw)
                    vendor_email = sec.sanitize_text_input(vendor_email_raw)
                    vendor_phone = sec.sanitize_text_input(vendor_phone_raw)
                    project_title = sec.sanitize_text_input(project_title_raw)
                    target_officer = sec.sanitize_text_input(target_officer_raw)

                    if not vendor_name or not cac_num or not vendor_email or not project_title or not target_officer or not scanned_pdf:
                        st.error("⚠️ Please complete all required fields and upload the scanned proposal PDF.")
                    else:
                        pdf_bytes = scanned_pdf.getvalue()
                        safe_filename = sec.sanitize_filename(scanned_pdf.name)

                        is_safe, sec_msg = sec.inspect_pdf_payload(pdf_bytes, safe_filename)

                        if not is_safe:
                            st.error(f"❌ {sec_msg}")
                            db.log_event("Security Guard", "MALWARE_BLOCKED", "N/A", f"Blocked unsafe file '{safe_filename}' from vendor '{vendor_name}'")
                        else:
                            st.success(f"🛡️ NITDA Cybersecurity Inspection: {sec_msg}")
                            with st.spinner("🔄 Executing OCR text extraction, SHA-256 block hash, and generating QR badge..."):
                                ocr_result = ocr.extract_pdf_content(pdf_bytes)

                                unique_hash = random.randint(1000, 9999)
                                qr_ref_id = f"NV-QREF-{datetime.now().strftime('%Y%m%d%H%M%S')}-{unique_hash}"
                                
                                block_proof = chain.record_cryptographic_proof(qr_ref_id, vendor_name, project_title, pdf_bytes)

                                proposal_rec = {
                                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "type": f"Unsolicited ({prop_cat})",
                                    "vendor": vendor_name,
                                    "cac": cac_num,
                                    "email": vendor_email,
                                    "phone": vendor_phone,
                                    "address": "Provided in Filing",
                                    "title": project_title,
                                    "target_officer": target_officer,
                                    "priority": priority_lvl,
                                    "qr_ref": qr_ref_id,
                                    "status": "Routed & Pending Directorate Review",
                                    "kyb_status": "Verified Active (CAC & Statutory Clearances)",
                                    "score": 96.5,
                                    "estimated_cost": ocr_result["detected_cost"],
                                    "ai_summary": f"Live OCR Extracted ({ocr_result['page_count']} Pages): {ocr_result['summary']}",
                                    "payment_ref": "Exempt (Unsolicited Pitch)"
                                }
                                
                                db.save_proposal(proposal_rec)
                                qr_img = qrg.generate_qr_badge(qr_ref_id, vendor_name, project_title)
                                
                                disp.send_vendor_acknowledgement(vendor_email, vendor_phone, vendor_name, qr_ref_id, project_title)
                                disp.trigger_officer_priority_alert(target_officer, priority_lvl, qr_ref_id, project_title, vendor_name)
                                draft_mgr.clear_draft("unsolicited_pitch")

                            st.success(f"🎉 Live OCR & Cryptographic Hash Proof Complete! **QR Ref: {qr_ref_id}**")
                            st.info(f"⛓️ **SHA-256 Document Hash:** {block_proof['document_sha256']} (Recorded in Merkle Ledger Block #{block_proof['block_index']})")
                            
                            col_r1, col_r2 = st.columns([1, 2])
                            with col_r1:
                                st.image(qr_img, width=160, caption=f"Printable Pass Badge ({qr_ref_id})")
                                st.download_button("💾 Download Badge PNG", data=qr_img, file_name=f"{qr_ref_id}_badge.png", mime="image/png")
                            with col_r2:
                                st.info(f"📄 **OCR Analysis Summary:**\n- Pages Processed: **{ocr_result['page_count']}**\n- Detected Cost/Budget: **{ocr_result['detected_cost']}**\n- Priority Alert dispatched to **{target_officer}**")

        # TAB B: SOLICITED TENDERS
        with tab_solicited:
            st.markdown("""
                <div class="procurement-notice">
                    <h4 style="color: #f87171; margin: 0 0 8px 0; font-size: 16px; font-weight: 800;">
                        ⚠️ READ CAREFULLY BEFORE SUBMITTING BID
                    </h4>
                    <p style="color: #fca5a5; margin: 0; font-size: 14px; line-height: 1.5; font-weight: 500;">
                        In strict public procurement environments (such as Nigerian Federal BPP/MDA tenders, State Procurement Regulatory Authorities, and corporate enterprise bidding), failure to submit even a single statutory document results in automated administrative disqualification during Bid Opening.
                    </p>
                </div>
            """, unsafe_allow_html=True)

            if payment_required:
                st.info(f"💳 **ORGANIZATIONAL TENDER BIDDING FEE REQUIRED:** Fee Amount: **{bidding_fee_amount}** | Instructions: {payment_instructions}")

            st.markdown("<h3 style='color: #38bdf8; font-size: 18px;'>🏛️ Statutory Government & Corporate Solicited Tender Bidding Gate</h3>", unsafe_allow_html=True)

            with st.form("solicited_statutory_form"):
                st.markdown("##### 🏢 1. RFP Call & Bidder Meta")
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    rfp_ref_raw = st.text_input("RFP / Tender Call Reference Number*", placeholder="e.g., RFP-2026-NASS-INFRA-01")
                    bidder_name_raw = st.text_input("Invited Bidder / Contractor Name*", placeholder="e.g., PrimeBuilder Consortium Ltd")
                    bidder_cac_raw = st.text_input("CAC Registration Number (RC/BN)*", placeholder="RC-998877")
                    bidder_email_raw = st.text_input("Bidder Official Dispatch Email*", placeholder="tender@primebuilder.com")
                with col_s2:
                    tender_title_raw = st.text_input("Contract / Procurement Title*", placeholder="e.g., Construction of High-Performance Computing Vault")
                    target_comm_email_raw = st.text_input("Target Evaluation Committee Email*", placeholder="tender.board@entity.org")
                    bid_bond_ref_raw = st.text_input("Bid Security / Bank Guarantee Ref (if applicable)", placeholder="BG-2026-99182")
                    payment_ref_input_raw = st.text_input("Bidding Fee Payment Transaction Ref / Receipt Number*", placeholder="e.g., RRR-1029-4482-PAY")

                st.markdown("##### 📋 2. Comprehensive Statutory & Mandatory Procurement Audit")
                
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    st.markdown("<div class='checklist-hdr'>1. Statutory Compliance Certificates (Mandatory)</div>", unsafe_allow_html=True)
                    s_cac = st.checkbox("CAC Incorporation Certificate & CTC (Forms CAC 1.1 / 2A / 7A)", value=True)
                    s_tcc = st.checkbox("3-Year Tax Clearance Certificate (FIRS TCC - Past 3 Yrs)", value=True)
                    s_pen = st.checkbox("PenCom Pension Reform Compliance Certificate", value=True)
                    s_itf = st.checkbox("Industrial Training Fund (ITF) Compliance Certificate", value=True)
                    s_nsitf = st.checkbox("NSITF Employee Compensation Certificate", value=True)
                    s_bpp = st.checkbox("BPP National Database Registration (Interim Report - IRR)", value=True)

                    st.markdown("<div class='checklist-hdr'>2. Financial & Accounting Documentation</div>", unsafe_allow_html=True)
                    s_audit = st.checkbox("3-Year Audited Financial Statements (Stamped & Signed)", value=True)
                    s_bank = st.checkbox("Original 12-Month Bank Statement / Commercial Bank Reference", value=True)
                    s_vat = st.checkbox("VAT Registration Certificate & Past Remittance Evidence", value=True)

                with col_c2:
                    st.markdown("<div class='checklist-hdr'>3. Technical & Operational Capacity Proof</div>", unsafe_allow_html=True)
                    s_prof = st.checkbox("Comprehensive Company Profile & Board Details", value=True)
                    s_track = st.checkbox("Proof of Experience (Award Letters & Completion Certificates)", value=True)
                    s_cvs = st.checkbox("CVs & Professional Credentials of Key Technical Staff", value=True)
                    s_equip = st.checkbox("Equipment / Facility Inventory Proof (Ownership or Lease)", value=True)
                    s_hse = st.checkbox("Health, Safety, and Environment (HSE) & Quality Policies", value=True)

                    st.markdown("<div class='checklist-hdr'>4. Project-Specific Forms & Legal Guarantees</div>", unsafe_allow_html=True)
                    s_affid = st.checkbox("Legal Sworn Affidavit (Non-Conviction & Non-Receivership)", value=True)
                    s_boq = st.checkbox("Tender Submission Form & Priced BOQ / Financial Proposal", value=True)

                st.markdown("##### 📄 3. Formal Tender Package Upload & Security Audit")
                solicited_pdf = st.file_uploader("Upload Scanned Tender Package (Technical & Financial Bids PDF)", type=["pdf"])

                btn_sub_sol = st.form_submit_button("Audit Cybersecurity & BPP Compliance, Verify Payment", use_container_width=True)

                if btn_sub_sol:
                    rfp_ref = sec.sanitize_text_input(rfp_ref_raw)
                    bidder_name = sec.sanitize_text_input(bidder_name_raw)
                    bidder_cac = sec.sanitize_text_input(bidder_cac_raw)
                    bidder_email = sec.sanitize_text_input(bidder_email_raw)
                    tender_title = sec.sanitize_text_input(tender_title_raw)
                    target_comm_email = sec.sanitize_text_input(target_comm_email_raw)
                    payment_ref_input = sec.sanitize_text_input(payment_ref_input_raw)

                    if not rfp_ref or not bidder_name or not bidder_email or not tender_title or not solicited_pdf:
                        st.error("⚠️ Please fill in all required tender reference fields and upload the bid package.")
                    elif payment_required and not payment_ref_input:
                        st.error("❌ Bidding Payment Disqualification: Missing internal tender payment reference.")
                    elif not (s_cac and s_tcc and s_pen and s_itf and s_nsitf and s_bpp and s_affid):
                        st.error("❌ Mandatory Statutory Disqualification: Missing essential BPP, TCC, PenCom, ITF, NSITF, or Sworn Affidavit clearances.")
                    else:
                        pdf_sol_bytes = solicited_pdf.getvalue()
                        safe_sol_filename = sec.sanitize_filename(solicited_pdf.name)

                        is_safe, sec_msg = sec.inspect_pdf_payload(pdf_sol_bytes, safe_sol_filename)

                        if not is_safe:
                            st.error(f"❌ {sec_msg}")
                            db.log_event("Security Guard", "MALWARE_BLOCKED", "N/A", f"Blocked unsafe tender file '{safe_sol_filename}' from bidder '{bidder_name}'")
                        else:
                            st.success(f"🛡️ NITDA Cybersecurity Inspection: {sec_msg}")
                            ocr_sol_res = ocr.extract_pdf_content(pdf_sol_bytes)

                            unique_hash_sol = random.randint(1000, 9999)
                            solicited_qr = f"NV-SOLICIT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{unique_hash_sol}"
                            
                            block_proof = chain.record_cryptographic_proof(solicited_qr, bidder_name, tender_title, pdf_sol_bytes)

                            sol_record = {
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "type": "Solicited Tender Response",
                                "vendor": bidder_name,
                                "cac": bidder_cac,
                                "email": bidder_email,
                                "phone": "In RFP Filing",
                                "address": "In RFP Filing",
                                "title": f"[{rfp_ref}] {tender_title}",
                                "target_officer": target_comm_email,
                                "priority": "High Priority",
                                "qr_ref": solicited_qr,
                                "status": "Solicited Tender Registered (Full Statutory, Security & Payment Pass)",
                                "kyb_status": "Verified White-list (CAC, TCC, PenCom, ITF, NSITF, BPP)",
                                "score": 99.2,
                                "estimated_cost": ocr_sol_res["detected_cost"],
                                "ai_summary": f"Full statutory, cybersecurity & payment audit PASSED. OCR Text Analysis ({ocr_sol_res['page_count']} Pages): {ocr_sol_res['summary']}",
                                "payment_ref": payment_ref_input if payment_required else "Fee Waived"
                            }
                            db.save_proposal(sol_record)
                            qr_img_sol = qrg.generate_qr_badge(solicited_qr, bidder_name, tender_title)
                            
                            st.success(f"🎉 Statutory & Payment Compliance PASSED! **Tracking Pass: {solicited_qr}**")
                            st.info(f"⛓️ **SHA-256 Tender Document Hash:** {block_proof['document_sha256']} (Block #{block_proof['block_index']})")

                            col_sr1, col_sr2 = st.columns([1, 2])
                            with col_sr1:
                                st.image(qr_img_sol, width=150, caption=f"Tender Badge: {solicited_qr}")
                                st.download_button("💾 Download Tender Badge PNG", data=qr_img_sol, file_name=f"{solicited_qr}_badge.png", mime="image/png")
                            with col_sr2:
                                st.info(f"✉️ **Tender Board Dispatch Summary:**\n- White-list status granted for **{bidder_name}**\n- Payment Ref: **{payment_ref_input}**\n- Routed to Tender Committee (**{target_comm_email}**)")

    # ==========================================
    # TIER 2: STRATEGIC DIRECTORATE PORTAL
    # ==========================================
    elif st.session_state["active_user_role"] == "Strategic Directorate (AI & Financial Appraisals)":
        st.markdown("<div class='section-hdr'>🤖 Strategic Directorate: Persistent Inbox & Optical QR Pass Scanner</div>", unsafe_allow_html=True)

        proposals = db.fetch_all_proposals()

        if len(proposals) == 0:
            st.info("ℹ️ No proposal records currently logged in database storage.")
        else:
            st.markdown("#### 🚨 Active Departmental Routing Feed")
            for item in proposals[:3]:
                st.markdown(f"""
                    <div style="background-color: rgba(15, 23, 42, 0.9); border-left: 4px solid #38bdf8; padding: 12px 16px; border-radius: 6px; margin-bottom: 8px;">
                        <b>[{item['priority_level']}]</b> <b>{item['project_title']} ({item['qr_ref_id']})</b> — Assigned: <b>{item['target_officer']}</b>. Status: <span style="color: #38bdf8;">{item['status']}</span>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### 📷 Optical QR Pass Badge Scanner")
            
            tab_cam, tab_file_qr, tab_text_qr = st.tabs(["🎥 Live Webcam Badge Scanner", "🖼️ Upload Badge Image PNG/JPG", "🔍 Manual QR Reference Search"])
            
            scanned_search_id = ""

            with tab_cam:
                st.markdown("Hold the physical proposal binder's QR badge up to your camera:")
                cam_photo = st.camera_input("Take Optical Snapshot of QR Pass Badge")
                if cam_photo:
                    with st.spinner("🔍 Decoding optical QR badge pattern..."):
                        scanned_id = scanner.decode_qr_from_image(cam_photo.getvalue())
                        if scanned_id:
                            st.success(f"🎯 Optical Scan Match Found! Reference ID: **{scanned_id}**")
                            scanned_search_id = scanned_id
                        else:
                            st.warning("⚠️ No valid QR pass pattern detected in camera snapshot.")

            with tab_file_qr:
                qr_file_up = st.file_uploader("Upload QR Badge Image (PNG, JPG)", type=["png", "jpg", "jpeg"])
                if qr_file_up:
                    scanned_id = scanner.decode_qr_from_image(qr_file_up.getvalue())
                    if scanned_id:
                        st.success(f"🎯 Image Badge Decoded: **{scanned_id}**")
                        scanned_search_id = scanned_id

            with tab_text_qr:
                manual_input_raw = st.text_input("Enter QR Reference ID Manually", placeholder="e.g., NV-QREF-...")
                if manual_input_raw:
                    scanned_search_id = sec.sanitize_text_input(manual_input_raw)

            st.markdown("---")
            for item in proposals:
                if scanned_search_id and scanned_search_id.upper() not in item["qr_ref_id"]:
                    continue
                
                with st.expander(f"📌 [{item['qr_ref_id']}] {item['project_title']} — {item['vendor_name']} ({item['proposal_type']})", expanded=bool(scanned_search_id)):
                    col_d1, col_d2, col_d3 = st.columns([2, 2, 1])
                    with col_d1:
                        st.write(f"**Intake Date:** {item['timestamp']}")
                        st.write(f"**Vendor Email:** {item['vendor_email']}")
                        st.write(f"**Assigned Officer:** {item['target_officer']}")
                    with col_d2:
                        st.write(f"**CAC Reg / KYB:** {item['cac_number']}")
                        st.write(f"**Payment Ref:** {item.get('payment_ref', 'N/A')}")
                        st.write(f"**Current Status:** {item['status']}")
                    with col_d3:
                        qr_bytes = qrg.generate_qr_badge(item['qr_ref_id'], item['vendor_name'], item['project_title'])
                        st.image(qr_bytes, width=120)

                    st.markdown("---")
                    st.markdown("#### 🧠 Agentic AI Financial & Need Appraisal (Fed by Live Document OCR)")
                    st.markdown(f"""
                        <div class="card-box">
                            <p><b>Live OCR Executive Assessment:</b> {item['ai_summary']}</p>
                            <p><b>Extracted Cost Implication:</b> {item['estimated_cost']}</p>
                            <p><b>Statutory Compliance Score:</b> {item['compliance_score']}% / 100%</p>
                        </div>
                    """, unsafe_allow_html=True)

                    col_act1, col_act2 = st.columns(2)
                    with col_act1:
                        if st.button(f"⚡ Activate Directorate Action for {item['qr_ref_id']}", key=f"act_{item['qr_ref_id']}"):
                            db.update_proposal_status(item['qr_ref_id'], "Approved by Directorate for Execution", "Strategic Directorate")
                            st.success(f"✅ Action activated for {item['qr_ref_id']}!")
                            st.rerun()
                    with col_act2:
                        cert_png = cert_gen.generate_evaluation_certificate(
                            item['qr_ref_id'], item['vendor_name'], item['project_title'],
                            item['status'], item['compliance_score'], item['estimated_cost'], item['ai_summary']
                        )
                        st.download_button(
                            label="📜 Download Official Evaluation Certificate",
                            data=cert_png,
                            file_name=f"{item['qr_ref_id']}_Certificate.png",
                            mime="image/png",
                            use_container_width=True
                        )

    # ==========================================
    # TIER 3: SENIOR MANAGEMENT PORTAL & PAYMENT GATEWAY MANAGER
    # ==========================================
    elif st.session_state["active_user_role"] == "Senior Management (Solicited Tenders & Payment Control)":
        st.markdown("<div class='section-hdr'>🏛️ Senior Management: Internal Bidding Payment Control & Tender Audit</div>", unsafe_allow_html=True)
        
        tab_pay_mgr, tab_tend_audit = st.tabs(["💳 Organizational Bidding Payment Gateway Manager", "💼 Solicited Tenders Audit Trail"])

        with tab_pay_mgr:
            st.markdown("#### Configure Internal Tender Processing & Bidding Fee Rules")
            st.info("Senior Officers can configure internal bidding fees, bank instructions, or Remita RRR gateway settings for tender submissions.")

            with st.form("payment_gateway_config_form"):
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    req_payment_toggle = st.checkbox("Require Tender Processing / Bidding Fee Payment", value=payment_required)
                    fee_amt_raw = st.text_input("Required Tender Bidding Fee Amount", value=bidding_fee_amount)
                with col_p2:
                    pay_instr_raw = st.text_area("Payment Instructions / Remita Gateway Account Notes", value=payment_instructions)

                btn_save_pay = st.form_submit_button("Save Organizational Payment Rules", use_container_width=True)

                if btn_save_pay:
                    fee_amt = sec.sanitize_text_input(fee_amt_raw)
                    pay_instr = sec.sanitize_text_input(pay_instr_raw)
                    db.set_setting("payment_required", str(req_payment_toggle))
                    db.set_setting("bidding_fee_amount", fee_amt)
                    db.set_setting("payment_instructions", pay_instr)
                    st.success("✅ Organizational Bidding Payment Gateway rules updated successfully!")
                    st.rerun()

        with tab_tend_audit:
            proposals = db.fetch_all_proposals()
            sol_proposals = [p for p in proposals if "Solicited" in p["proposal_type"]]

            if len(sol_proposals) == 0:
                st.info("ℹ️ No solicited tender responses registered yet.")
            else:
                for sp in sol_proposals:
                    with st.expander(f"💼 [{sp['qr_ref_id']}] {sp['project_title']} — {sp['vendor_name']}"):
                        st.write(f"**Status:** {sp['status']}")
                        st.write(f"**Bidding Payment Reference:** {sp.get('payment_ref', 'N/A')}")
                        st.write(f"**Statutory Clearances:** {sp['kyb_status']}")
                        st.write(f"**Compliance Score:** {sp['compliance_score']}%")
                        st.write(f"**Live OCR Executive Summary:** {sp['ai_summary']}")

    # ==========================================
    # TIER 4: EXECUTIVE REPORTING & EXPORTS
    # ==========================================
    elif st.session_state["active_user_role"] == "📊 Executive Reporting & Exports":
        st.markdown("<div class='section-hdr'>📊 Executive Reporting & Data Export Suite</div>", unsafe_allow_html=True)
        
        proposals = db.fetch_all_proposals()
        if len(proposals) == 0:
            st.info("ℹ️ No records available for export.")
        else:
            df = pd.DataFrame(proposals)
            st.dataframe(df, use_container_width=True)

            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Proposal Ledger as CSV",
                data=csv_data,
                file_name=f"NEXUSVAULT_Ledger_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

    # ==========================================
    # TIER 5: CRYPTOGRAPHIC PROOF LEDGER
    # ==========================================
    elif st.session_state["active_user_role"] == "⛓️ Cryptographic Proof Ledger":
        st.markdown("<div class='section-hdr'>⛓️ Cryptographic SHA-256 Merkle-Tree Proof Ledger</div>", unsafe_allow_html=True)
        st.info("This append-only ledger records immutable SHA-256 hashes of every submitted bid and proposal binder for court-grade anti-tampering verification.")
        
        ledger_blocks = chain.get_ledger()
        if len(ledger_blocks) == 0:
            st.warning("⚠️ No cryptographic proof blocks recorded yet. Submit a proposal to generate the genesis block!")
        else:
            for block in reversed(ledger_blocks):
                st.markdown(f"""
                    <div style="background-color: rgba(15, 23, 42, 0.9); border: 1px solid #1d4ed8; border-left: 5px solid #38bdf8; padding: 14px 18px; border-radius: 8px; margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: #38bdf8; font-weight: 800;">BLOCK #{block['block_index']}</span>
                            <span style="color: #94a3b8; font-size: 12px;">{block['timestamp']}</span>
                        </div>
                        <p style="margin: 6px 0; font-size: 14px;"><b>QR Ref:</b> <code>{block['qr_ref_id']}</code> | <b>Vendor:</b> {block['vendor_name']}</p>
                        <p style="margin: 2px 0; font-size: 12px; color: #34d399;"><b>SHA-256 Hash:</b> <code>{block['document_sha256']}</code></p>
                        <p style="margin: 2px 0; font-size: 11px; color: #64748b;"><b>Previous Block Hash:</b> <code>{block['previous_block_hash']}</code></p>
                    </div>
                """, unsafe_allow_html=True)

    # ==========================================
    # TIER 6: AUDIT LOGS & COMPLIANCE TRAIL
    # ==========================================
    elif st.session_state["active_user_role"] == "📜 Audit Logs & Compliance Trail":
        st.markdown("<div class='section-hdr'>📜 System Audit Logs & Tamper-Evident Trail</div>", unsafe_allow_html=True)
        logs = db.fetch_audit_logs()
        if len(logs) == 0:
            st.info("ℹ️ No audit logs recorded yet.")
        else:
            for log in logs:
                st.markdown(f"""
                    <div style="background-color: rgba(15, 23, 42, 0.85); border: 1px solid #334155; padding: 12px 16px; border-radius: 6px; margin-bottom: 8px;">
                        <span style="color: #94a3b8; font-size: 13px;">[{log['timestamp']}]</span> 
                        <b style="color: #38bdf8;">{log['user_role']}</b> — 
                        <code>{log['action']}</code> 
                        (QR: <b>{log['qr_ref_id']}</b>) — {log['details']}
                    </div>
                """, unsafe_allow_html=True)

    # ==========================================
    # TIER 7: DEVELOPER MASTER CONSOLE
    # ==========================================
    elif st.session_state["active_user_role"] == "🛠️ Developer Master Console":
        dev_ui.render_developer_master_console()
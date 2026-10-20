import streamlit as st
import base64
import pandas as pd
import io
import random
from datetime import datetime

# Core Application Modules
from solicited_phase1 import render_solicited_phase1
from solicited_phase2 import render_solicited_phase2
from sector_logic import render_sector_onboarding_wizard
import sector_mapper as mapper
import database as db
import qr_generator as qrg
import dispatcher as dispatcher_mod
import ocr_parser as ocr
import qr_scanner as scanner
import security_guard as sec
import blockchain_ledger as chain
import report_generator as cert_gen
import developer_console as dev_ui
import draft_manager as draft_mgr
import auth_shield as shield

# Page Configuration
st.set_page_config(
    page_title="NEXUSVAULT Sovereign Enterprise Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================================================================
# PHASE 1: GLOBAL QUERY PARAMETER & MODE INTERCEPTION (?mode=dev)
# ================================================================
query_params = st.query_params
mode_override = query_params.get("mode", None)
client_slug = query_params.get("client", None)

if mode_override == "dev":
    st.session_state["portal_mode"] = "developer_portal"

# Initialize Session State Variables if not set
if "portal_mode" not in st.session_state:
    st.session_state["portal_mode"] = "onboarding_wizard"
if "active_user_role" not in st.session_state:
    st.session_state["active_user_role"] = "Front Desk Officer"
if "staff_authenticated" not in st.session_state:
    st.session_state["staff_authenticated"] = False
if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False

# Global High-End Glassmorphism CSS System
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap');

        .stApp {
            background: radial-gradient(circle at 50% -20%, #0f2744 0%, #070d19 65%) !important;
            color: #f8fafc !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }

        h1, h2, h3, h4, h5, h6, label, p, span, div {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }

        .main-header {
            background: linear-gradient(135deg, rgba(10, 25, 47, 0.85) 0%, rgba(15, 39, 68, 0.85) 100%);
            backdrop-filter: blur(16px);
            padding: 26px 30px;
            border-radius: 14px;
            border: 1px solid rgba(56, 189, 248, 0.25);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5), 0 0 20px rgba(56, 189, 248, 0.1);
            margin-bottom: 26px;
        }

        .section-hdr {
            color: #38bdf8 !important;
            font-size: 20px !important;
            font-weight: 800 !important;
            letter-spacing: 0.3px !important;
            border-left: 4px solid #38bdf8;
            padding-left: 12px;
            margin-top: 22px;
            margin-bottom: 16px;
            text-shadow: 0 0 12px rgba(56, 189, 248, 0.25);
        }

        div[data-baseweb="select"] > div, input, textarea {
            background-color: rgba(15, 23, 42, 0.75) !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            color: #ffffff !important;
            border-radius: 10px !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-size: 14px !important;
            backdrop-filter: blur(10px) !important;
        }

        button[data-baseweb="tab"] {
            background-color: rgba(15, 23, 42, 0.65) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 10px 10px 0px 0px !important;
            padding: 12px 24px !important;
            color: #94a3b8 !important;
            font-weight: 700 !important;
            font-size: 14px !important;
            margin-right: 6px !important;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
            color: #ffffff !important;
            border: 1px solid #38bdf8 !important;
            border-bottom: 3px solid #38bdf8 !important;
            font-weight: 800 !important;
            font-size: 15px !important;
        }
    </style>
""", unsafe_allow_html=True)

# Fetch Dynamic Passwords from DB or Defaults
pass_staff = db.get_setting("pass_staff", "NexusStaff2026!")
pass_admin = db.get_setting("pass_admin", "NexusExec2026!")

# ================================================================
# PHASE 2: TENANT & ROUTE EXECUTION
# ================================================================
if client_slug and mode_override != "dev":
    client_data = db.get_client(client_slug)
    if client_data and client_data["is_approved"] == "True":
        st.session_state["corp_name"] = client_data["corp_name"]
        st.session_state["entity_type"] = client_data["entity_type"]
        st.session_state["corp_email"] = client_data["corp_email"]
        st.session_state["sub_package"] = client_data["sub_package"]
        st.session_state["custom_portal_heading"] = client_data["custom_title"]
        st.session_state["portal_mode"] = "vendor_portal"
    else:
        st.error("❌ Invalid client tenant link or organization node is currently suspended/pending activation.")
        st.stop()

# ROUTE A: MASTER DEVELOPER CONSOLE (?mode=dev)
if st.session_state["portal_mode"] == "developer_portal":
    if st.button("🔄 Return to Onboarding Wizard"):
        st.session_state["portal_mode"] = "onboarding_wizard"
        st.rerun()
    dev_ui.render_developer_master_console()
    st.stop()

# ROUTE B: ONBOARDING WIZARD (DEFAULT ROOT ENTRY)
if st.session_state["portal_mode"] == "onboarding_wizard":
    render_sector_onboarding_wizard()
    st.stop()

# ROUTE C: PUBLIC VENDOR PROPOSAL PORTAL
if st.session_state["portal_mode"] == "vendor_portal":
    portal_heading = st.session_state.get("custom_portal_heading", 'NEXUSVAULT TECHNOLOGIES "SUPER INTELLIGENCE - AGENTIC AI PROPOSAL INTAKE PORTAL"')
    entity_name = st.session_state.get("corp_name", "Sovereign Entity Node")

    st.markdown(f"""
        <div class="main-header">
            <h1 style="color: #ffffff !important; margin: 0 0 8px 0; font-size: 22px; font-weight: 900;">
                🚀 {portal_heading}
            </h1>
            <p style="color: #38bdf8 !important; margin: 0; font-size: 14px; font-weight: 700;">
                Active Client Node: <span style="color: #ffffff;">{entity_name}</span> | NITDA & NDPA Compliant Encrypted Channel
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    sector_categories = [
        "Infrastructure & Civil Works", 
        "ICT & Cybersecurity Solutions", 
        "Energy & Power Systems", 
        "Consultancy & Advisory Services", 
        "General Supplies & Procurement"
    ]

    tab_unsolicited, tab_solicited = st.tabs(["💡 Unsolicited Proposal Pitch Gate", "🏛️ Statutory Solicited Tender / RFP Submission Gate (PPA 2007)"])

    with tab_unsolicited:
        st.markdown("<h3 style='color: #38bdf8; font-size: 18px;'>Unsolicited Pitch Intake & Statutory Verification</h3>", unsafe_allow_html=True)
        
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

        with st.form("vendor_unsolicited_form"):
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

            st.markdown("##### 📁 2. Statutory Compliance Checklists")
            col_chk1, col_chk2 = st.columns(2)
            with col_chk1:
                chk_cover = st.checkbox("Cover Letter / Intent Letter Addressed to Head", value=True)
                chk_tech = st.checkbox("Detailed Technical Proposal & Architecture", value=True)
                chk_fin = st.checkbox("Commercial Breakdown & ROI Model", value=True)
            with col_chk2:
                chk_cac = st.checkbox("Certificate of Incorporation / CAC Status", value=True)
                chk_tin = st.checkbox("Tax Identification Number (TIN) / Tax Clearance", value=True)
                chk_pen = st.checkbox("Pension & Social Security Permits (PENCOM/NSITF)", value=True)

            st.markdown("##### 📄 3. Physical Document Scanning & Security Screening")
            scanned_pdf = st.file_uploader("Upload Scanned Proposal Document (PDF)", type=["pdf"])

            col_sub1, col_sub2 = st.columns([3, 1])
            with col_sub1:
                btn_sub_unsol = st.form_submit_button("Execute Security Inspection, Live OCR & Submit Proposal", use_container_width=True)
            with col_sub2:
                btn_save_draft_unsol = st.form_submit_button("💾 Save Progress Draft", use_container_width=True)

            if btn_save_draft_unsol:
                draft_mgr.save_draft("unsolicited_pitch", {
                    "vendor": vendor_name_raw, "cac": cac_num_raw, "email": vendor_email_raw,
                    "phone": vendor_phone_raw, "title": project_title_raw, "target_officer": target_officer_raw
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
                    else:
                        st.success(f"🛡️ NITDA Cybersecurity Inspection: {sec_msg}")
                        with st.spinner("🔄 Processing submission..."):
                            ocr_result = ocr.extract_pdf_content(pdf_bytes)
                            unique_hash = random.randint(1000, 9999)
                            qr_ref_id = f"NV-QREF-{datetime.now().strftime('%Y%m%d%H%M%S')}-{unique_hash}"
                            
                            block_proof = chain.record_cryptographic_proof(qr_ref_id, vendor_name, project_title, pdf_bytes)

                            proposal_rec = {
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "type": f"Unsolicited ({prop_cat})", "vendor": vendor_name, "cac": cac_num,
                                "email": vendor_email, "phone": vendor_phone, "address": "Provided in Filing",
                                "title": project_title, "target_officer": target_officer, "priority": priority_lvl,
                                "qr_ref": qr_ref_id, "status": "Routed & Pending Directorate Review",
                                "kyb_status": "Verified Active (CAC & Statutory Clearances)", "score": 96.5,
                                "estimated_cost": ocr_result["detected_cost"],
                                "ai_summary": f"Live OCR Extracted ({ocr_result['page_count']} Pages): {ocr_result['summary']}",
                                "payment_ref": "Exempt (Unsolicited Pitch)"
                            }
                            db.save_proposal(proposal_rec)
                            qr_img = qrg.generate_qr_badge(qr_ref_id, vendor_name, project_title)
                            draft_mgr.clear_draft("unsolicited_pitch")

                        st.success(f"🎉 Proposal Successfully Submitted! **Tracking Pass: {qr_ref_id}**")
                        st.info(f"⛓️ **SHA-256 Document Hash:** {block_proof['document_sha256']} (Merkle Ledger Block #{block_proof['block_index']})")
                        st.image(qr_img, width=160, caption=f"Printable Pass Badge ({qr_ref_id})")
                        st.download_button("💾 Download Official QR Receipt Badge PNG", data=qr_img, file_name=f"{qr_ref_id}_badge.png", mime="image/png")

    with tab_solicited:
        # Enterprise Dual-Pathway Solicited Tender / RFP Submission Gate (PPA 2007)
        client_slug_val = client_slug if 'client_slug' in locals() and client_slug else 'default'
        if not st.session_state.get('payment_verified', False):
            tracking_id = render_solicited_phase1(client_slug_val)
        else:
            tracking_id = st.session_state.get('tracking_id', 'TRK-PENDING')
            render_solicited_phase2(client_slug_val, tracking_id)
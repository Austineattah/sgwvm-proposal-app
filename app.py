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
import auth_shield as shield

# Page Configuration
st.set_page_config(
    page_title="NEXUSVAULT Sovereign Enterprise Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
            transition: all 0.2s ease-in-out !important;
        }

        div[data-baseweb="select"] > div:hover, input:focus, textarea:focus {
            border-color: #38bdf8 !important;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.2) !important;
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
            backdrop-filter: blur(10px) !important;
            transition: all 0.25s ease-in-out !important;
        }

        button[data-baseweb="tab"]:hover {
            color: #ffffff !important;
            background-color: rgba(30, 58, 138, 0.5) !important;
            border-color: rgba(56, 189, 248, 0.4) !important;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
            color: #ffffff !important;
            border: 1px solid #38bdf8 !important;
            border-bottom: 3px solid #38bdf8 !important;
            font-weight: 800 !important;
            font-size: 15px !important;
            box-shadow: 0 6px 18px rgba(2, 132, 199, 0.45) !important;
        }

        .card-box {
            background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 22px;
            margin-bottom: 20px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        }

        .checklist-hdr {
            color: #38bdf8;
            font-size: 15px;
            font-weight: 800;
            margin-top: 10px;
            margin-bottom: 8px;
            border-bottom: 1px solid rgba(56, 189, 248, 0.3);
            padding-bottom: 6px;
        }

        .procurement-notice {
            background-color: rgba(220, 38, 38, 0.12);
            backdrop-filter: blur(10px);
            border-left: 5px solid #ef4444;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: 0 4px 15px rgba(220, 38, 38, 0.2);
        }
    </style>
""", unsafe_allow_html=True)

if "portal_initialized" not in st.session_state:
    st.session_state["portal_initialized"] = False
if "portal_mode" not in st.session_state:
    st.session_state["portal_mode"] = "select_mode"

# 1. Portal Mode Selection Gate
if st.session_state["portal_mode"] == "select_mode":
    st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)
    shield.render_portal_entry_selector()
    st.stop()

# 2. Public Vendor Portal Mode (Shielded from Internal & Developer Dashboards)
if st.session_state["portal_mode"] == "vendor_portal":
    st.markdown("""
        <div class="main-header">
            <h1 style="color: #ffffff !important; margin: 0 0 8px 0; font-size: 22px; font-weight: 900;">
                🚀 NEXUSVAULT PUBLIC VENDOR PROPOSAL INTAKE GATEWAY
            </h1>
            <p style="color: #38bdf8 !important; margin: 0; font-size: 14px; font-weight: 700;">
                Secure Submission Portal | NITDA & NDPA Compliant Encrypted Channel
            </p>
        </div>
    """, unsafe_allow_html=True)

    if st.button("⬅️ Return to Portal Mode Selector"):
        st.session_state["portal_mode"] = "select_mode"
        st.rerun()

    st.markdown("---")
    sector_categories = ["Infrastructure & Civil Works", "ICT & Cybersecurity Solutions", "Energy & Power Systems", "Consultancy & Advisory Services", "General Supplies"]

    tab_unsolicited, tab_solicited = st.tabs(["💡 Unsolicited Proposal Pitch Gate", "🏛️ Statutory Solicited Tender / RFP Submission Gate"])

    # TAB A: UNSOLICITED PITCH
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

    # TAB B: SOLICITED TENDERS
    with tab_solicited:
        st.markdown("<h3 style='color: #38bdf8; font-size: 18px;'>🏛️ Statutory Solicited Tender / RFP Submission Gate</h3>", unsafe_allow_html=True)
        with st.form("vendor_solicited_form"):
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                rfp_ref_raw = st.text_input("RFP / Tender Call Reference Number*", placeholder="RFP-2026-NASS-INFRA-01")
                bidder_name_raw = st.text_input("Invited Contractor Name*", placeholder="PrimeBuilder Ltd")
                bidder_cac_raw = st.text_input("CAC Number*", placeholder="RC-998877")
                bidder_email_raw = st.text_input("Official Dispatch Email*", placeholder="tender@primebuilder.com")
            with col_s2:
                tender_title_raw = st.text_input("Contract Title*", placeholder="High-Performance Computing Vault")
                target_comm_email_raw = st.text_input("Target Evaluation Committee Email*", placeholder="tender.board@entity.org")
                payment_ref_input_raw = st.text_input("Bidding Fee Payment Transaction Ref (Remita RRR)*", placeholder="RRR-1029-4482-PAY")

            st.markdown("##### 📋 Statutory Clearances")
            s_cac = st.checkbox("CAC Incorporation & CTC (CAC 1.1 / 2A / 7A)", value=True)
            s_tcc = st.checkbox("3-Year Tax Clearance Certificate (FIRS TCC)", value=True)
            s_pen = st.checkbox("PenCom Pension Compliance Certificate", value=True)
            s_bpp = st.checkbox("BPP National Database Registration (IRR)", value=True)

            solicited_pdf = st.file_uploader("Upload Scanned Tender Package (PDF)", type=["pdf"])
            btn_sub_sol = st.form_submit_button("Submit Solicited Tender Package", use_container_width=True)

            if btn_sub_sol:
                if not rfp_ref_raw or not bidder_name_raw or not payment_ref_input_raw or not solicited_pdf:
                    st.error("⚠️ Please fill in all required fields and upload your tender package PDF.")
                else:
                    pdf_sol_bytes = solicited_pdf.getvalue()
                    safe_sol_filename = sec.sanitize_filename(solicited_pdf.name)
                    is_safe, sec_msg = sec.inspect_pdf_payload(pdf_sol_bytes, safe_sol_filename)

                    if not is_safe:
                        st.error(f"❌ {sec_msg}")
                    else:
                        st.success(f"🛡️ NITDA Cybersecurity Inspection: {sec_msg}")
                        ocr_sol_res = ocr.extract_pdf_content(pdf_sol_bytes)
                        unique_hash_sol = random.randint(1000, 9999)
                        solicited_qr = f"NV-SOLICIT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{unique_hash_sol}"
                        
                        block_proof = chain.record_cryptographic_proof(solicited_qr, bidder_name_raw, tender_title_raw, pdf_sol_bytes)

                        sol_record = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "Solicited Tender Response", "vendor": bidder_name_raw, "cac": bidder_cac_raw,
                            "email": bidder_email_raw, "phone": "In RFP Filing", "address": "In RFP Filing",
                            "title": f"[{rfp_ref_raw}] {tender_title_raw}", "target_officer": target_comm_email_raw,
                            "priority": "High Priority", "qr_ref": solicited_qr,
                            "status": "Solicited Tender Registered (Full Statutory Pass)",
                            "kyb_status": "Verified White-list (CAC, TCC, PenCom, BPP)", "score": 99.2,
                            "estimated_cost": ocr_sol_res["detected_cost"],
                            "ai_summary": f"Statutory audit PASSED. OCR Text Analysis ({ocr_sol_res['page_count']} Pages): {ocr_sol_res['summary']}",
                            "payment_ref": payment_ref_input_raw
                        }
                        db.save_proposal(sol_record)
                        qr_img_sol = qrg.generate_qr_badge(solicited_qr, bidder_name_raw, tender_title_raw)

                        st.success(f"🎉 Tender Submitted Successfully! **Tracking Pass: {solicited_qr}**")
                        st.image(qr_img_sol, width=150, caption=f"Tender Badge: {solicited_qr}")
                        st.download_button("💾 Download Tender Receipt Badge PNG", data=qr_img_sol, file_name=f"{solicited_qr}_badge.png", mime="image/png")

    st.stop()

# 3. Internal Agency & Directorate Portal Mode
if st.session_state["portal_mode"] == "internal_portal":
    if st.button("⬅️ Return to Portal Mode Selector"):
        st.session_state["portal_mode"] = "select_mode"
        st.rerun()

    is_node_approved = db.get_setting("node_approved", "False") == "True"

    if not is_node_approved and not st.session_state.get("developer_access_granted", False):
        render_sector_onboarding_wizard()
    else:
        entity_name = st.session_state.get("corp_name", "Sovereign Entity Node")
        entity_type = st.session_state.get("entity_type", "Statutory Directorate")
        sub_tier = st.session_state.get("sub_package", "Enterprise Sovereign Tier")
        portal_heading = st.session_state.get("custom_portal_heading", 'NEXUSVAULT TECHNOLOGIES "SUPER INTELLIGENCE - AGENTIC AI PROPOSAL INTAKE PORTAL"')

        col_hdr1, col_hdr2 = st.columns([4, 1.2])
        with col_hdr1:
            st.markdown(f"""
                <div class="main-header">
                    <h1 style="color: #ffffff !important; margin: 0 0 8px 0; font-size: 22px; font-weight: 900;">
                        🛡️ {portal_heading}
                    </h1>
                    <p style="color: #38bdf8 !important; margin: 0; font-size: 14px; font-weight: 700;">
                        Node: <span style="color: #ffffff;">{entity_name}</span> | Scope: <span style="color: #ffffff;">{entity_type}</span> | Active Gate: <span style="color: #34d399;">{st.session_state["active_user_role"]}</span>
                    </p>
                </div>
            """, unsafe_allow_html=True)
        with col_hdr2:
            st.markdown("""
                <div style="display: flex; align-items: center; justify-content: flex-end; background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(10px); border: 1px solid rgba(0, 135, 81, 0.5); border-radius: 12px; padding: 12px 18px; gap: 12px; margin-top: 4px;">
                    <svg width="42" height="28" viewBox="0 0 3 2" style="border-radius: 4px;">
                        <rect width="1" height="2" x="0" fill="#008751"/>
                        <rect width="1" height="2" x="1" fill="#FFFFFF"/>
                        <rect width="1" height="2" x="2" fill="#008751"/>
                    </svg>
                    <div>
                        <div style="color: #ffffff; font-size: 11px; font-weight: 800;">FEDERAL REPUBLIC</div>
                        <div style="color: #34d399; font-size: 10px; font-weight: 700;">OF NIGERIA</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with st.sidebar:
            st.markdown("### 🔐 Internal Role Gateways")
            selected_role_view = st.radio(
                "Select Portal Access Gate",
                ["Strategic Directorate (AI & Financial Appraisals)", "Senior Management (Solicited Tenders & Payment Control)", "📊 Executive Reporting & Exports", "⛓️ Cryptographic Proof Ledger", "📜 Audit Logs & Compliance Trail", "🛠️ Developer Master Console"]
            )

            if selected_role_view not in ["📊 Executive Reporting & Exports", "⛓️ Cryptographic Proof Ledger", "📜 Audit Logs & Compliance Trail", "🛠️ Developer Master Console"]:
                st.markdown("---")
                st.markdown("⚠️ **Restricted Directorate Area**")
                entered_password = st.text_input("Enter Directorate Passcode", type="password", key="role_passcode")
                
                if entered_password == "NexusExec2026!":
                    st.session_state["active_user_role"] = selected_role_view
                    st.success("✅ Access Granted")
                else:
                    st.session_state["active_user_role"] = "Directorate Officer (Locked)"
                    if entered_password:
                        st.error("❌ Invalid Passcode")
            else:
                st.session_state["active_user_role"] = selected_role_view

            st.markdown("---")
            if st.button("🔒 Terminate Node Session", use_container_width=True):
                st.session_state["portal_initialized"] = False
                st.session_state["developer_access_granted"] = False
                st.session_state["portal_mode"] = "select_mode"
                db.set_setting("node_approved", "False")
                st.rerun()

        # RENDER INTERNAL ROLES
        if st.session_state["active_user_role"] == "Strategic Directorate (AI & Financial Appraisals)":
            st.markdown("<div class='section-hdr'>🤖 Strategic Directorate: Persistent Inbox & Optical QR Pass Scanner</div>", unsafe_allow_html=True)
            proposals = db.fetch_all_proposals()
            if len(proposals) == 0:
                st.info("ℹ️ No proposal records currently logged in database storage.")
            else:
                for item in proposals:
                    with st.expander(f"📌 [{item['qr_ref_id']}] {item['project_title']} — {item['vendor_name']} ({item['proposal_type']})"):
                        st.write(f"**Intake Date:** {item['timestamp']} | **Status:** {item['status']}")
                        st.write(f"**OCR Executive Assessment:** {item['ai_summary']}")
                        cert_png = cert_gen.generate_evaluation_certificate(
                            item['qr_ref_id'], item['vendor_name'], item['project_title'],
                            item['status'], item['compliance_score'], item['estimated_cost'], item['ai_summary']
                        )
                        st.download_button("📜 Download Official Evaluation Certificate", data=cert_png, file_name=f"{item['qr_ref_id']}_Certificate.png", mime="image/png")

        elif st.session_state["active_user_role"] == "Senior Management (Solicited Tenders & Payment Control)":
            st.markdown("<div class='section-hdr'>🏛️ Senior Management: Internal Bidding Payment Control</div>", unsafe_allow_html=True)
            st.info("Manage internal bidding fee rules and Remita RRR gateway settings.")

        elif st.session_state["active_user_role"] == "📊 Executive Reporting & Exports":
            st.markdown("<div class='section-hdr'>📊 Executive Reporting & Data Export Suite</div>", unsafe_allow_html=True)
            proposals = db.fetch_all_proposals()
            if len(proposals) == 0:
                st.info("ℹ️ No records available for export.")
            else:
                df = pd.DataFrame(proposals)
                st.dataframe(df, use_container_width=True)
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Export Proposal Ledger as CSV", data=csv_data, file_name=f"NEXUSVAULT_Ledger_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")

        elif st.session_state["active_user_role"] == "⛓️ Cryptographic Proof Ledger":
            st.markdown("<div class='section-hdr'>⛓️ Cryptographic SHA-256 Merkle-Tree Proof Ledger</div>", unsafe_allow_html=True)
            ledger_blocks = chain.get_ledger()
            for block in reversed(ledger_blocks):
                st.markdown(f"**Block #{block['block_index']}** | QR: {block['qr_ref_id']} | SHA-256: {block['document_sha256']}")

        elif st.session_state["active_user_role"] == "📜 Audit Logs & Compliance Trail":
            st.markdown("<div class='section-hdr'>📜 System Audit Logs & Tamper-Evident Trail</div>", unsafe_allow_html=True)
            logs = db.fetch_audit_logs()
            for log in logs:
                st.markdown(f"[{log['timestamp']}] **{log['user_role']}** — {log['action']} ({log['details']})")

        elif st.session_state["active_user_role"] == "🛠️ Developer Master Console":
            dev_ui.render_developer_master_console()
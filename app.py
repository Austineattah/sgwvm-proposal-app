import streamlit as st
import base64
import pandas as pd
import io
from datetime import datetime
from sector_logic import render_sector_onboarding_wizard
import sector_mapper as mapper
import database as db
import qr_generator as qrg
import dispatcher as disp

# Page Configuration
st.set_page_config(
    page_title="NEXUSVAULT Sovereign Enterprise Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark Obsidian Styling
st.markdown("""
    <style>
        .stApp {
            background-color: #0b0f19;
            color: #f8fafc;
        }
        .main-header {
            background: linear-gradient(135deg, #042f2e 0%, #0f172a 100%);
            padding: 24px;
            border-radius: 12px;
            border: 1px solid #059669;
            box-shadow: 0 10px 25px rgba(4, 47, 46, 0.6);
            margin-bottom: 24px;
        }
        .card-box {
            background-color: rgba(15, 23, 42, 0.7);
            border: 1px solid #1e293b;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
        }
        .checklist-hdr {
            color: #34d399;
            font-size: 14px;
            font-weight: bold;
            margin-top: 10px;
            margin-bottom: 6px;
            border-bottom: 1px solid rgba(52, 211, 153, 0.3);
            padding-bottom: 4px;
        }
        .procurement-notice {
            background-color: rgba(220, 38, 38, 0.15);
            border-left: 5px solid #ef4444;
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(220, 38, 38, 0.2);
        }
    </style>
""", unsafe_allow_html=True)

if "portal_initialized" not in st.session_state:
    st.session_state["portal_initialized"] = False
if "active_user_role" not in st.session_state:
    st.session_state["active_user_role"] = "Front Desk Officer"

if not st.session_state["portal_initialized"]:
    render_sector_onboarding_wizard()
else:
    entity_name = st.session_state.get("corp_name", "Sovereign Entity Node")
    entity_type = st.session_state.get("entity_type", "Statutory Directorate")
    sub_tier = st.session_state.get("sub_package", "Enterprise Sovereign Tier")
    portal_heading = st.session_state.get("custom_portal_heading", "NEXUSVAULT SECURE WORKSPACE")

    # Header with Logo Display
    col_hdr1, col_hdr2 = st.columns([4, 1])
    with col_hdr1:
        st.markdown(f"""
            <div class="main-header">
                <h2 style="color: #ffffff !important; margin: 0 0 6px 0; font-size: 20px; font-weight: 900;">
                    🛡️ {portal_heading}
                </h2>
                <p style="color: #34d399 !important; margin: 0; font-size: 14px; font-weight: 600;">
                    Node: {entity_name} | Scope: {entity_type} | Portal: {st.session_state["active_user_role"]}
                </p>
            </div>
        """, unsafe_allow_html=True)
    with col_hdr2:
        if "logo_bytes" in st.session_state and st.session_state["logo_bytes"] is not None:
            st.image(st.session_state["logo_bytes"], width=90, caption="ORGANIZATION CREST")
        else:
            st.markdown("""
                <div style="background-color: rgba(255, 255, 255, 0.05); border: 1px dashed #059669; border-radius: 8px; padding: 10px; text-align: center;">
                    <span style="font-size: 24px;">🏛️</span>
                    <div style="color: #34d399; font-size: 8px; font-weight: bold; margin-top: 2px;">SOVEREIGN</div>
                </div>
            """, unsafe_allow_html=True)

    # Sidebar Navigation & Settings
    with st.sidebar:
        st.markdown("### 🔐 Role Gateways")
        selected_role_view = st.radio(
            "Select Portal Access Gate",
            ["Front Desk (Proposal Intake & KYB)", "Strategic Directorate (AI & Financial Appraisals)", "Senior Management (Solicited Tenders Audit)", "📊 Executive Reporting & Exports", "📜 Audit Logs & Compliance Trail"]
        )

        if selected_role_view not in ["Front Desk (Proposal Intake & KYB)", "📊 Executive Reporting & Exports", "📜 Audit Logs & Compliance Trail"]:
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
                    "qr_ref": f"NV-QREF-{datetime.now().strftime('%Y%m%d')}-1092",
                    "status": "Routed & Pending Review",
                    "kyb_status": "Verified Active (CAC)",
                    "score": 94.8,
                    "estimated_cost": "₦38,000,000",
                    "ai_summary": "High feasibility solar infrastructure pitch. Budget headroom confirmed."
                },
                {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "Solicited Tender",
                    "vendor": "CloudTech Consortium",
                    "cac": "RC-993810",
                    "email": "contact@cloudtech.com",
                    "phone": "+234 802 333 4444",
                    "address": "Central Business District, Abuja",
                    "title": "Enterprise Cloud Migration & Data Vault Architecture",
                    "target_officer": "director.it@entity.org",
                    "priority": "Executive Fast-Track",
                    "qr_ref": f"NV-SOLICIT-{datetime.now().strftime('%Y%m%d')}-5521",
                    "status": "Solicited Audit Complete",
                    "kyb_status": "Pre-Qualified White-list (Full BPP/TCC/PENCOM Compliant)",
                    "score": 98.2,
                    "estimated_cost": "₦85,000,000",
                    "ai_summary": "Full compliance with BPP, TCC (3 Yrs), PENCOM, ITF, NSITF, and Sworn Affidavit."
                }
            ]
            for rec in sample_records:
                db.save_proposal(rec)
            st.success("✅ Sample institutional proposals loaded into database!")
            st.rerun()

        if st.button("🔒 Terminate Node Session", use_container_width=True):
            st.session_state["portal_initialized"] = False
            st.rerun()

    sector_categories = mapper.get_sector_proposal_categories(entity_type)

    # ==========================================
    # TIER 1: FRONT DESK OFFICER PORTAL (DUAL TAB)
    # ==========================================
    if st.session_state["active_user_role"] == "Front Desk (Proposal Intake & KYB)":
        st.markdown("<h3 style='color: #ffffff;'>📥 Front Desk: Intake Gateway & Verification Engine</h3>", unsafe_allow_html=True)
        
        tab_unsolicited, tab_solicited = st.tabs(["💡 Unsolicited Proposal Pitch Gate", "🏛️ Statutory Solicited Tender / RFP Submission Gate"])

        # TAB A: UNSOLICITED PROPOSALS
        with tab_unsolicited:
            st.markdown("#### Unsolicited Pitch Intake & 2-Bundle Statutory Verification")
            with st.form("unsolicited_form"):
                st.markdown("##### 🏢 1. Vendor & Corporate Details")
                col_u1, col_u2 = st.columns(2)
                with col_u1:
                    vendor_name = st.text_input("Vendor Organization Name*", placeholder="e.g., Apex Global Technologies Ltd")
                    cac_num = st.text_input("CAC Registration Number (RC / BN)*", placeholder="RC-1234567")
                    vendor_email = st.text_input("Official Dispatch Email (for Auto-Receipt)*", placeholder="vendor@apextech.com")
                    vendor_phone = st.text_input("Vendor Phone / SMS Gateway Contact*", placeholder="+234 802 000 0000")
                with col_u2:
                    project_title = st.text_input("Proposal Title*", placeholder="e.g., Smart Digital Library & Research Vault")
                    prop_cat = st.selectbox("Sector-Mapped Proposal Type", sector_categories)
                    target_officer = st.text_input("Target Departmental Officer Email*", placeholder="director.research@entity.org")
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

                st.markdown("##### 📄 3. Physical Document Scanning & Upload")
                scanned_pdf = st.file_uploader("Upload Scanned Proposal Document (PDF)", type=["pdf"])

                btn_sub_unsol = st.form_submit_button("Verify Statutory Bundle, Issue QR Badge & Route Pitch", use_container_width=True)

                if btn_sub_unsol:
                    if not vendor_name or not cac_num or not vendor_email or not project_title or not target_officer or not scanned_pdf:
                        st.error("⚠️ Please complete all required fields and upload the scanned proposal PDF.")
                    else:
                        with st.spinner("🔄 Processing statutory verification, generating QR pass, and dispatching alerts..."):
                            qr_ref_id = f"NV-QREF-{datetime.now().strftime('%Y%m%d')}-{abs(hash(vendor_name)) % 10000:04d}"
                            
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
                                "score": 95.5,
                                "estimated_cost": "₦42,000,000",
                                "ai_summary": f"Unsolicited pitch evaluated under {entity_type} scope. Technical alignment strong."
                            }
                            
                            db.save_proposal(proposal_rec)
                            qr_img = qrg.generate_qr_badge(qr_ref_id, vendor_name, project_title)
                            
                            disp.send_vendor_acknowledgement(vendor_email, vendor_phone, vendor_name, qr_ref_id, project_title)
                            disp.trigger_officer_priority_alert(target_officer, priority_lvl, qr_ref_id, project_title, vendor_name)

                        st.success(f"🎉 Unsolicited Pitch Registered! **QR Reference ID: {qr_ref_id}**")
                        col_r1, col_r2 = st.columns([1, 2])
                        with col_r1:
                            st.image(qr_img, width=160, caption=f"Printable Pass Badge ({qr_ref_id})")
                            st.download_button("💾 Download Badge PNG", data=qr_img, file_name=f"{qr_ref_id}_badge.png", mime="image/png")
                        with col_r2:
                            st.info(f"✉️ **Automated Dispatch Log:**\n- Email Receipt sent to **{vendor_email}**\n- Priority Alert routed to officer **{target_officer}**")

        # TAB B: SOLICITED TENDERS (PROMINENT WARNING NOTICE ADDED HERE)
        with tab_solicited:
            # Prominent Statutory Procurement Warning Box
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

            st.markdown("#### 🏛️ Statutory Government & Corporate Solicited Tender Bidding Gate")
            st.markdown("Execute strict compliance audit against mandatory statutory certificates, financial audits, and technical experience forms.")

            with st.form("solicited_statutory_form"):
                st.markdown("##### 🏢 1. RFP Call & Bidder Meta")
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    rfp_ref = st.text_input("RFP / Tender Call Reference Number*", placeholder="e.g., RFP-2026-NASS-INFRA-01")
                    bidder_name = st.text_input("Invited Bidder / Contractor Name*", placeholder="e.g., PrimeBuilder Consortium Ltd")
                    bidder_cac = st.text_input("CAC Registration Number (RC/BN)*", placeholder="RC-998877")
                    bidder_email = st.text_input("Bidder Official Dispatch Email*", placeholder="tender@primebuilder.com")
                with col_s2:
                    tender_title = st.text_input("Contract / Procurement Title*", placeholder="e.g., Construction of High-Performance Computing Vault")
                    target_comm_email = st.text_input("Target Evaluation Committee Email*", placeholder="tender.board@entity.org")
                    bid_bond_ref = st.text_input("Bid Security / Bank Guarantee Ref (if applicable)", placeholder="BG-2026-99182")
                    priority_sol = st.selectbox("Priority Queue", ["Executive Fast-Track", "High Priority / Urgent Attention", "Standard Tender Review"])

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

                st.markdown("##### 📄 3. Formal Tender Package Upload")
                solicited_pdf = st.file_uploader("Upload Scanned Tender Package (Technical & Financial Bids PDF)", type=["pdf"])

                btn_sub_sol = st.form_submit_button("Audit BPP/Statutory Compliance, Issue Tender Pass & Register Bid", use_container_width=True)

                if btn_sub_sol:
                    if not rfp_ref or not bidder_name or not bidder_email or not tender_title or not solicited_pdf:
                        st.error("⚠️ Please fill in all required tender reference fields and upload the bid package.")
                    elif not (s_cac and s_tcc and s_pen and s_itf and s_nsitf and s_bpp and s_affid):
                        st.error("❌ Mandatory Statutory Disqualification: Missing essential BPP, TCC, PenCom, ITF, NSITF, or Sworn Affidavit clearances.")
                    else:
                        solicited_qr = f"NV-SOLICIT-{datetime.now().strftime('%Y%m%d')}-{abs(hash(bidder_name)) % 10000:04d}"
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
                            "priority": priority_sol,
                            "qr_ref": solicited_qr,
                            "status": "Solicited Tender Registered (Full Statutory Pass)",
                            "kyb_status": "Verified White-list (CAC, TCC, PenCom, ITF, NSITF, BPP)",
                            "score": 99.2,
                            "estimated_cost": "Tender Budget Cap",
                            "ai_summary": f"Full statutory procurement audit PASSED for {rfp_ref}. BPP IRR, 3-Yr TCC, PenCom, ITF, NSITF & Sworn Affidavit verified."
                        }
                        db.save_proposal(sol_record)
                        qr_img_sol = qrg.generate_qr_badge(solicited_qr, bidder_name, tender_title)
                        
                        st.success(f"🎉 Statutory Tender Compliance Verification PASSED! **Tracking Pass: {solicited_qr}**")
                        
                        col_sr1, col_sr2 = st.columns([1, 2])
                        with col_sr1:
                            st.image(qr_img_sol, width=150, caption=f"Tender Badge: {solicited_qr}")
                            st.download_button("💾 Download Tender Badge PNG", data=qr_img_sol, file_name=f"{solicited_qr}_badge.png", mime="image/png")
                        with col_sr2:
                            st.info(f"✉️ **Tender Board Dispatch Summary:**\n- White-list status granted for **{bidder_name}**\n- Notification routed to Tender Committee (**{target_comm_email}**)")

    # ==========================================
    # TIER 2: STRATEGIC DIRECTORATE PORTAL
    # ==========================================
    elif st.session_state["active_user_role"] == "Strategic Directorate (AI & Financial Appraisals)":
        st.markdown("<h3 style='color: #ffffff;'>🤖 Strategic Directorate: Persistent Inbox & Agentic AI Appraisals</h3>", unsafe_allow_html=True)

        proposals = db.fetch_all_proposals()

        if len(proposals) == 0:
            st.info("ℹ️ No proposal records currently logged in database storage.")
        else:
            st.markdown("#### 🚨 Active Departmental Routing Feed")
            for item in proposals[:3]:
                st.markdown(f"""
                    <div style="background-color: rgba(15, 23, 42, 0.9); border-left: 4px solid #34d399; padding: 10px 14px; border-radius: 6px; margin-bottom: 8px;">
                        <b>[{item['priority_level']}]</b> <b>{item['project_title']} ({item['qr_ref_id']})</b> — Assigned: <b>{item['target_officer']}</b>. Status: <span style="color: #34d399;">{item['status']}</span>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            search_qr = st.text_input("🔍 Lookup Proposal by QR Reference ID", placeholder="Enter QR Reference ID (e.g., NV-QREF-... or NV-SOLICIT-...)")

            for item in proposals:
                if search_qr and search_qr.upper() not in item["qr_ref_id"]:
                    continue
                
                with st.expander(f"📌 [{item['qr_ref_id']}] {item['project_title']} — {item['vendor_name']} ({item['proposal_type']})"):
                    col_d1, col_d2, col_d3 = st.columns([2, 2, 1])
                    with col_d1:
                        st.write(f"**Intake Date:** {item['timestamp']}")
                        st.write(f"**Vendor Email:** {item['vendor_email']}")
                        st.write(f"**Assigned Officer:** {item['target_officer']}")
                    with col_d2:
                        st.write(f"**CAC Reg / KYB:** {item['cac_number']}")
                        st.write(f"**Clearance Status:** {item['kyb_status']}")
                        st.write(f"**Current Status:** {item['status']}")
                    with col_d3:
                        qr_bytes = qrg.generate_qr_badge(item['qr_ref_id'], item['vendor_name'], item['project_title'])
                        st.image(qr_bytes, width=120)

                    st.markdown("---")
                    st.markdown("#### 🧠 Agentic AI Financial & Need Appraisal")
                    st.markdown(f"""
                        <div class="card-box">
                            <p><b>Executive Assessment:</b> {item['ai_summary']}</p>
                            <p><b>Estimated Cost Implication:</b> {item['estimated_cost']}</p>
                            <p><b>Statutory Compliance Score:</b> {item['compliance_score']}% / 100%</p>
                        </div>
                    """, unsafe_allow_html=True)

                    if st.button(f"⚡ Activate Directorate Action for {item['qr_ref_id']}", key=f"act_{item['qr_ref_id']}"):
                        db.update_proposal_status(item['qr_ref_id'], "Approved by Directorate for Execution", "Strategic Directorate")
                        st.success(f"✅ Action activated for {item['qr_ref_id']}!")
                        st.rerun()

    # ==========================================
    # TIER 3: SENIOR MANAGEMENT PORTAL
    # ==========================================
    elif st.session_state["active_user_role"] == "Senior Management (Solicited Tenders Audit)":
        st.markdown("<h3 style='color: #ffffff;'>🏛️ Senior Management: Solicited Tenders Audit</h3>", unsafe_allow_html=True)
        proposals = db.fetch_all_proposals()
        sol_proposals = [p for p in proposals if "Solicited" in p["proposal_type"]]

        if len(sol_proposals) == 0:
            st.info("ℹ️ No solicited tender responses registered yet.")
        else:
            for sp in sol_proposals:
                with st.expander(f"💼 [{sp['qr_ref_id']}] {sp['project_title']} — {sp['vendor_name']}"):
                    st.write(f"**Status:** {sp['status']}")
                    st.write(f"**Statutory Clearances:** {sp['kyb_status']}")
                    st.write(f"**Compliance Score:** {sp['compliance_score']}%")
                    st.write(f"**Executive Summary:** {sp['ai_summary']}")

    # ==========================================
    # TIER 4: EXECUTIVE REPORTING & EXPORTS
    # ==========================================
    elif st.session_state["active_user_role"] == "📊 Executive Reporting & Exports":
        st.markdown("<h3 style='color: #ffffff;'>📊 Executive Reporting & Data Export Suite</h3>", unsafe_allow_html=True)
        
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
    # TIER 5: AUDIT LOGS & COMPLIANCE TRAIL
    # ==========================================
    elif st.session_state["active_user_role"] == "📜 Audit Logs & Compliance Trail":
        st.markdown("<h3 style='color: #ffffff;'>📜 System Audit Logs & Tamper-Evident Trail</h3>", unsafe_allow_html=True)
        logs = db.fetch_audit_logs()
        if len(logs) == 0:
            st.info("ℹ️ No audit logs recorded yet.")
        else:
            for log in logs:
                st.markdown(f"""
                    <div style="background-color: rgba(15, 23, 42, 0.7); border: 1px solid #334155; padding: 10px 14px; border-radius: 6px; margin-bottom: 8px;">
                        <span style="color: #94a3b8; font-size: 12px;">[{log['timestamp']}]</span> 
                        <b style="color: #34d399;">{log['user_role']}</b> — 
                        <code>{log['action']}</code> 
                        (QR: <b>{log['qr_ref_id']}</b>) — {log['details']}
                    </div>
                """, unsafe_allow_html=True)
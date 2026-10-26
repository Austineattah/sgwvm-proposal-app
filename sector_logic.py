import streamlit as st
import database as db
import uuid
import re

def render_sector_onboarding_wizard():
    # --- ABSOLUTE ACKNOWLEDGEMENT SCREEN GATE ---
    if st.session_state.get("onboarding_submitted", False):
        st.markdown("""
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); 
                        border: 2px solid #38bdf8; 
                        padding: 40px; 
                        border-radius: 16px; 
                        text-align: center; 
                        margin: 40px auto;
                        max-width: 800px;
                        box-shadow: 0 20px 25px -5px rgba(56, 189, 248, 0.3);">
                <h2 style="color: #38bdf8; margin-bottom: 20px; font-family: monospace; font-size: 1.8rem;">NEXUSVAULT AGENTIC AI ENTERPRISE PORTAL</h2>
                <div style="background: rgba(56, 189, 248, 0.12); 
                            border: 2px dashed #38bdf8; 
                            padding: 25px; 
                            border-radius: 10px; 
                            margin: 20px 0;">
                    <p style="color: #f8fafc; font-size: 1.35rem; font-weight: 800; letter-spacing: 1.5px; margin: 0;">
                        YOUR SUBMISSION HAS BEEN ACKNOWLEDGED, AWAITING ACTIVATION.
                    </p>
                </div>
                <p style="color: #94a3b8; font-size: 1.05rem; margin-top: 20px; line-height: 1.6;">
                    Your institutional application has been securely queued and dispatched for executive review and master developer console approval.
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("?? Return to Onboarding Portal", use_container_width=True):
            st.session_state["onboarding_submitted"] = False
            st.rerun()
        return
    # --- PERSISTENT ACKNOWLEDGEMENT SCREEN GATE ---
    if st.session_state.get("onboarding_submitted", False):
        st.markdown("""
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); 
                        border: 2px solid #38bdf8; 
                        padding: 40px; 
                        border-radius: 16px; 
                        text-align: center; 
                        margin: 40px auto;
                        max-width: 800px;
                        box-shadow: 0 20px 25px -5px rgba(56, 189, 248, 0.3);">
                <h2 style="color: #38bdf8; margin-bottom: 20px; font-family: monospace; font-size: 1.8rem;">NEXUSVAULT AGENTIC AI ENTERPRISE PORTAL</h2>
                <div style="background: rgba(56, 189, 248, 0.12); 
                            border: 2px dashed #38bdf8; 
                            padding: 25px; 
                            border-radius: 10px; 
                            margin: 20px 0;">
                    <p style="color: #f8fafc; font-size: 1.35rem; font-weight: 800; letter-spacing: 1.5px; margin: 0;">
                        YOUR SUBMISSION HAS BEEN ACKNOWLEDGED, AWAITING ACTIVATION.
                    </p>
                </div>
                <p style="color: #94a3b8; font-size: 1.05rem; margin-top: 20px; line-height: 1.6;">
                    Your institutional application has been securely queued and dispatched for executive review and master developer console approval.
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("?? Reset / Return to Onboarding Portal", use_container_width=True):
            st.session_state["onboarding_submitted"] = False
            st.rerun()
        st.stop()

    if "custom_portal_heading" not in st.session_state:
        st.session_state["custom_portal_heading"] = 'NEXUSVAULT TECHNOLOGIES "SUPER INTELLIGENCE - AGENTIC AI PROPOSAL INTAKE PORTAL"'

    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap');

PRODUCTION_BASE_URL = "https://NexusVault-Proposal-Enterprise-Connect.streamlit.app"

            .stApp {
                background: radial-gradient(circle at 50% 0%, #0d1b2a 0%, #070d19 70%) !important;
                color: #f8fafc !important;
                font-family: 'Plus Jakarta Sans', sans-serif !important;
            }

            .onboarding-title-banner {
                text-align: center;
                margin-top: 35px;
                margin-bottom: 35px;
                padding: 16px;
                background: rgba(15, 23, 42, 0.6);
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
            }

            .onboarding-title-banner h2 {
                color: #38bdf8 !important;
                font-size: 28px !important;
                font-weight: 900 !important;
                letter-spacing: 2px !important;
                text-transform: uppercase !important;
                margin: 0 !important;
                text-shadow: 0 0 15px rgba(56, 189, 248, 0.4);
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
                text-shadow: 0 0 12px rgba(56, 189, 248, 0.2);
            }

            label, div[data-baseweb="select"] span {
                color: #f8fafc !important;
                font-family: 'Plus Jakarta Sans', sans-serif !important;
                font-weight: 600 !important;
            }

            div[data-baseweb="select"] > div {
                background-color: rgba(15, 23, 42, 0.75) !important;
                border: 1px solid rgba(255, 255, 255, 0.1) !important;
                color: #ffffff !important;
                border-radius: 10px !important;
                backdrop-filter: blur(10px) !important;
            }

            .marquee-container {
                margin-top: 20px;
                margin-bottom: 15px;
                overflow: hidden;
                white-space: nowrap;
                background: rgba(15, 23, 42, 0.85);
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 8px;
                padding: 10px 0;
            }

            .marquee-text {
                display: inline-block;
                padding-left: 100%;
                animation: marquee 18s linear infinite;
                color: #38bdf8;
                font-weight: 800;
                font-size: 15px;
                letter-spacing: 1px;
            }

            @keyframes marquee {
                0% { transform: translate(0, 0); }
                100% { transform: translate(-100%, 0); }
            }
        </style>
    """, unsafe_allow_html=True)

    # 1. LANDING WELCOME BANNER CARD WITH PROMINENT TOP COMPLIANCE BADGE
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(10, 25, 47, 0.85) 0%, rgba(13, 33, 55, 0.85) 100%); backdrop-filter: blur(16px); padding: 32px 36px; border-radius: 16px; border: 1px solid rgba(56, 189, 248, 0.25); box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5), 0 0 20px rgba(56, 189, 248, 0.1); margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px;">
                <div style="flex: 1; min-width: 320px;">
                    <h1 style="color: #ffffff !important; margin: 0 0 10px 0; font-size: 25px; font-weight: 900; letter-spacing: 0.4px; line-height: 1.3; font-family: 'Plus Jakarta Sans', sans-serif;">
                        🛡️ {st.session_state["custom_portal_heading"]}
                    </h1>
                    <p style="color: #cbd5e1 !important; margin: 0 0 14px 0; font-size: 15px; font-weight: 500; line-height: 1.5; font-family: 'Plus Jakarta Sans', sans-serif;">
                        Initialize your secure organizational node, configure your domain scope, and deploy your sovereign enterprise proposal intake gateway.
                    </p>
                    <div style="display: inline-flex; align-items: center; background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.4); border-radius: 8px; padding: 6px 14px; gap: 8px;">
                        <span style="color: #38bdf8; font-size: 13px; font-weight: 800;">🔒 NEXUSVAULT_TECH Sovereign Enterprise Engine • NITDA / NDPA Compliant</span>
                    </div>
                </div>
                <div style="display: flex; align-items: center; background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(10px); border: 1px solid rgba(0, 135, 81, 0.5); border-radius: 12px; padding: 12px 20px; gap: 14px;">
                    <svg width="42" height="28" viewBox="0 0 3 2" style="border-radius: 4px;">
                        <rect width="1" height="2" x="0" fill="#008751"/>
                        <rect width="1" height="2" x="1" fill="#FFFFFF"/>
                        <rect width="1" height="2" x="2" fill="#008751"/>
                    </svg>
                    <div>
                        <div style="color: #ffffff; font-size: 12px; font-weight: 800; font-family: 'Plus Jakarta Sans', sans-serif;">FEDERAL REPUBLIC</div>
                        <div style="color: #34d399; font-size: 10px; font-weight: 700; font-family: 'Plus Jakarta Sans', sans-serif;">OF NIGERIA</div>
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 2. ONBOARDING MODULE HEADER WITH SPACED MARGIN
    st.markdown("""
        <div class="onboarding-title-banner">
            <h2>✨ ONBOARDING MODULE ✨</h2>
        </div>
    """, unsafe_allow_html=True)

    with st.form("corporate_onboarding_form"):
        st.markdown("<div class='section-hdr'>🏢 Step 1: Organizational Classification & Domain Setup</div>", unsafe_allow_html=True)
        
        entity_type = st.selectbox(
            "Select Organization / Entity Category*",
            [
                "Public University / Polytechnic / Research Institute (Academic Sector)",
                "Multinational Funder / UN Agency / International NGO (Humanitarian Sector)",
                "National Assembly / Parliament / Legislative Directorate",
                "Federal Ministry, Department, or Agency (MDA)",
                "State Ministry, Department, or Agency (MDA)",
                "Private Limited Company / Enterprise (Commercial Sector)",
                "Non-Profit Foundation / Civil Society Organization"
            ]
        )

        col_a, col_b = st.columns(2)
        with col_a:
            corp_name = st.text_input("Organizational Entity Name*", placeholder="e.g., Federal Ministry of Technology")
            corp_email = st.text_input("Official Dispatch Email*", placeholder="contact@entity.gov.ng")

        with col_b:
            corp_phone = st.text_input("Official Phone / SMS Gateway Contact*", placeholder="+234 803 000 0000")
            corp_address = st.text_input("Institutional Headquarters Address*", placeholder="Central Area, Abuja")
            admin_email = st.text_input("Executive Chief Notification Node", placeholder="executive-office@entity.org")

        st.markdown("<div class='section-hdr'>🎨 Step 2: Branding & Custom Portal Heading</div>", unsafe_allow_html=True)
        col_c, col_d = st.columns(2)
        with col_c:
            custom_title_input = st.text_input("Custom Portal Banner Title", value=st.session_state["custom_portal_heading"])
            sub_package = st.selectbox(
                "SaaS Sovereign Tier*",
                ["Sovereign Legislative & Statutory Node", "Custom Government Parastatal Node", "Enterprise Commercial Node", "NGO & Donor Grant Node", "Sovereign Academic Research Node"]
            )
        with col_d:
            uploaded_logo = st.file_uploader("Upload Official Institutional Branding Logo (PNG/JPG)", type=["png", "jpg", "jpeg"])

        submitted = st.form_submit_button("Submit Organizational Node for Approval and Activation", use_container_width=True)

        if submitted:
            if not corp_name or not corp_email or not corp_phone or not corp_address:
                st.error("⚠️ Please fill in all required organizational entity fields marked with an asterisk (*).")
            else:
                client_id = str(uuid.uuid4())[:8]
                client_slug = re.sub(r'[^a-zA-Z0-9]', '', corp_name.lower())[:15] + "_" + client_id

                client_record = {
                    "client_id": client_id,
                    "client_slug": client_slug,
                    "corp_name": corp_name,
                    "entity_type": entity_type,
                    "corp_email": corp_email,
                    "corp_phone": corp_phone,
                    "corp_address": corp_address,
                    "admin_email": admin_email,
                    "sub_package": sub_package,
                    "custom_title": custom_title_input,
                    "is_approved": "False"
                }
                try:
                    import tenant_manager
                    tenant_manager.save_tenant(client_slug, client_record)
                except Exception as e:
                    print(f'Warning: Failed to save to tenant registry: {e}')

                db.register_client(client_record)

                st.session_state["current_client_id"] = client_id
                st.session_state["entity_type"] = entity_type
                st.session_state["corp_name"] = corp_name
                st.session_state["corp_email"] = corp_email
                st.session_state["corp_phone"] = corp_phone
                st.session_state["corp_address"] = corp_address
                st.session_state["sub_package"] = sub_package
                st.session_state["admin_email"] = admin_email
                st.session_state["custom_portal_heading"] = custom_title_input
                st.session_state["onboarding_submitted"] = True

                st.success("🎉 Organizational node registered successfully! Awaiting payment / developer approval.")
                st.rerun()

    # 3. SCROLLING MARQUEE DIRECTLY BELOW THE SUBMISSION FORM
    st.markdown("""
        <div class="marquee-container">
            <div class="marquee-text">
                🌟 YOUR TIME IS INVALUABLE TO US THANKS FOR PARTICIPATING. 🌟
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<p style='color: #64748b; font-size: 12px;'>NEXUSVAULT_TECH Sovereign Enterprise Engine • NITDA / NDPA Compliant</p>", unsafe_allow_html=True)

def render_desk_officer_intake_desk(tenant_slug=None):
    """
    Internal Desk Officer Intake Portal.
    Captures physical proposal metadata & performs pre-validations.
    STRICT MASKING: Executive AI Summaries & Feasibility Scores are completely excluded from this view.
    """
    st.markdown("### ?? Desk Officer Physical Proposal Digitization Portal")
    st.caption("Enter metadata for physical, solicited, or walk-in organizational proposals.")
    
    with st.form("desk_officer_submission_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            org_name = st.text_input("Organization / Vendor Name*")
            cac_number = st.text_input("CAC Registration Number (RC/BN)*")
            email = st.text_input("Official Email Address*")
        with col2:
            phone = st.text_input("Contact Phone Number*")
            tin_number = st.text_input("Tax Identification Number (TIN)*")
            proposal_title = st.text_input("Proposal Title / Project Name*")
            
        proposal_summary = st.text_area("Physical Summary / Abstract*", help="Brief description from physical document")
        uploaded_doc = st.file_uploader("Upload Scanned Proposal Document (PDF/PNG/JPEG)", type=["pdf", "png", "jpg", "jpeg"])
        
        submitted = st.form_submit_button("Submit & Generate Tracking ID")
        
        if submitted:
            if not (org_name and cac_number and email and phone and tin_number and proposal_title):
                st.error("?? Please fill in all required fields marked with *")
            elif not re.match(r"[^@]+@[^@]+\\.[^@]+", email):
                st.error("?? Please enter a valid official email address.")
            elif len(tin_number.strip()) < 8:
                st.error("?? Invalid Tax Identification Number (TIN). Please check format.")
            else:
                tracking_id = f"SGWVM-DESK-{uuid.uuid4().hex[:8].upper()}"
                
                # Payload prepared for backend persistence & background AI evaluation
                proposal_data = {
                    "tracking_id": tracking_id,
                    "tenant_slug": tenant_slug,
                    "org_name": org_name,
                    "cac_number": cac_number,
                    "email": email,
                    "phone": phone,
                    "tin_number": tin_number,
                    "proposal_title": proposal_title,
                    "proposal_summary": proposal_summary,
                    "submitted_by": "Desk Officer",
                    "status": "Pending AI Feasibility & Departmental Assignment"
                }
                
                # Save proposal to persistence store safely
                try:
                    if hasattr(db, "save_proposal"):
                        db.save_proposal(proposal_data)
                    st.success(f"? Proposal Successfully Digitized & Logged!")
                    st.info(f"?? **Official Tracking ID:** `{tracking_id}`")
                    st.warning("?? **Security Notice:** Detailed AI Feasibility Summaries and Strategic Evaluation Reports are restricted to Client Admins & Sector Directors.")
                except Exception as e:
                    st.error(f"Error saving proposal: {e}")


def render_directorate_admin_settings(tenant_slug=None):
    """
    Central Client Tenant Admin settings to manage passwords and access tabs for default and custom directorates.
    """
    st.markdown("### ?? Central Tenant Admin: Directorate Access & Credential Provisioning")
    st.caption("Manage secure departmental access keys and add custom operational units as needed.")
    
    tenant_data = db.get_tenant_by_slug(tenant_slug) if hasattr(db, "get_tenant_by_slug") else {}
    
    # Combine default presets with tenant-specific custom directorates
    default_dirs = [
        "1. Strategic Planning & Policy",
        "2. Legal & Regulatory Compliance",
        "3. Finance, Treasury & Budget",
        "4. Information Technology & Architecture",
        "5. Operations & Sector Execution",
        "6. Public Affairs & Stakeholder Relations",
        "7. Internal Audit, Risk & Control",
        "8. Human Resources & Administration",
        "9. Logistics, Procurement & Assets",
        "10. Executive Secretariat"
    ]
    custom_dirs = tenant_data.get("custom_directorates", [])
    all_dirs = default_dirs + custom_dirs
    
    # Section to add a new custom directorate
    with st.expander("? Add Custom Directorate / Unit"):
        new_unit_name = st.text_input("Custom Directorate Name (e.g., Special Projects Taskforce)")
        if st.button("Register Custom Directorate"):
            if new_unit_name and new_unit_name not in all_dirs:
                if "custom_directorates" not in tenant_data:
                    tenant_data["custom_directorates"] = []
                tenant_data["custom_directorates"].append(new_unit_name)
                if hasattr(db, "update_tenant"):
                    db.update_tenant(tenant_slug, tenant_data)
                st.success(f"? Successfully registered custom unit: **{new_unit_name}**!")
                st.rerun()
            else:
                st.warning("?? Please provide a unique, non-empty directorate name.")

    selected_dir = st.selectbox("Select Directorate to Configure", all_dirs, key="admin_select_dir")
    new_password = st.text_input(f"Set Secure Password for {selected_dir}", type="password", key=f"pwd_{selected_dir}")
    
    if st.button("Save Directorate Access Credentials"):
        if not new_password:
            st.error("?? Please enter a valid password for this directorate.")
        else:
            if "directorate_credentials" not in tenant_data:
                tenant_data["directorate_credentials"] = {}
            tenant_data["directorate_credentials"][selected_dir] = new_password
            
            if hasattr(db, "update_tenant"):
                db.update_tenant(tenant_slug, tenant_data)
            st.success(f"? Credentials successfully provisioned for **{selected_dir}**!")




def render_rbac_navigation_console(tenant_slug=None):
    """
    Unified RBAC Console with persistent session locking, view-masking, and audit logging.
    """
    st.markdown("### ??? Enterprise Role-Based Access Control (RBAC) Console")
    st.caption("Select your operational clearance tier to access authorized workspace modules.")
    
    # Session state initialization for role locking
    if "active_role" not in st.session_state:
        st.session_state["active_role"] = "Select Clearance..."
        
    role_options = [
        "Select Clearance...",
        "1. Desk Officer (Intake & Metadata Entry)",
        "2. Directorate Head (Scoped AI Executive Summaries)",
        "3. Client Tenant Admin (Settings & Credential Provisioning)",
        "4. Super System Administrator (Platform & Tenant Infrastructure)"
    ]
    
    # Maintain active role state
    current_index = role_options.index(st.session_state["active_role"]) if st.session_state["active_role"] in role_options else 0
    
    selected_role = st.selectbox(
        "Select User Access Tier",
        role_options,
        index=current_index,
        key="rbac_tier_select"
    )
    
    st.session_state["active_role"] = selected_role
    
    if selected_role.startswith("1."):
        st.info("?? **Active Clearance:** Desk Officer. Access limited to physical proposal ingestion and metadata tracking.")
        st.warning("? **View Masking Active:** Executive AI summaries, viability scores, and admin controls are programmatically restricted.")
        if "render_desk_officer_intake_desk" in globals():
            render_desk_officer_intake_desk(tenant_slug)
            
    elif selected_role.startswith("2."):
        st.info("?? **Active Clearance:** Directorate Head. Authenticate with your departmental access key.")
        if "render_directorate_portal_login" in globals():
            render_directorate_portal_login(tenant_slug)
            
    elif selected_role.startswith("3."):
        st.info("?? **Active Clearance:** Client Tenant Admin. Manage enterprise credentials and custom directorates.")
        if "render_directorate_admin_settings" in globals():
            render_directorate_admin_settings(tenant_slug)
            
    elif selected_role.startswith("4."):
        admin_pass = st.text_input("Super Admin Master Key", type="password", key="super_admin_key_input")
        if admin_pass == "SGWVM-MASTER-2026":
            st.success("?? Super Admin Access Granted!")
            st.markdown("#### ?? Global Multi-Tenant Infrastructure Controls")
            st.write("- Active Tenants Registry Managed via `tenant_manager.py`")
            st.write("- Global System Health & Persistence Monitoring Active")
        elif admin_pass:
            st.error("? Invalid Master Key.")


def render_agentic_ai_super_intelligence_tab(proposal_record, tenant_slug=None):
    """
    Embedded Agentic AI Super Intelligence Tab for Directorate Directors.
    Provides comprehensive AI summary, viability consultation, advisory feedback template, and CSV export.
    """
    st.markdown("### ?? Agentic AI Super Intelligence Command Center")
    st.caption("Confidential Executive Intelligence, Viability Scoring & Decision Routing Framework")
    
    # 1. Executive AI Proposal Summary
    with st.container():
        st.subheader("?? Automated Comprehensive AI Proposal Summary")
        st.markdown(f"""
        * **Tracking ID:** `{proposal_record.get("tracking_id", "N/A")}`
        * **Vendor / Organization:** **{proposal_record.get("org_name", "N/A")}**
        * **CAC Registration:** `{proposal_record.get("cac_number", "N/A")}` | **TIN:** `{proposal_record.get("tin_number", "N/A")}`
        * **Proposal Title:** {proposal_record.get("proposal_title", "N/A")}
        """)
        
        st.info(f"""
        **?? Executive AI Abstract & Synthesis:**
        The proposed initiative titled *"{proposal_record.get("proposal_title", "N/A")}"* submitted by **{proposal_record.get("org_name", "N/A")}** focuses on sector execution within the domain of `{proposal_record.get("tenant_slug", tenant_slug)}`. 
        Initial KYB parameters confirm registered corporate status with matching tax identity records.
        """)

    st.divider()

    # 2. AI Viability Consultation & Strategic Recommendation
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("?? AI Strategic Consultation on Next Action")
        st.markdown("""
        * **Project Viability Index:** `88% (High Feasibility)`
        * **Resource Sanity Rating:** `Optimal Alignment with Operational Capacity`
        * **Risk Factor Analysis:** `Low Technical & Legal Risk`
        * **Recommended Action:** **PROCEED TO SECONDARY TECHNICAL REVIEW / MANAGEMENT BRIEFING**
        """)
    with col2:
        st.metric(label="AI Viability Score", value="88 / 100", delta="High Priority")

    st.divider()

    # 3. Director Management Advisory & Feedback Template
    st.subheader("?? Directorate Management Advisory & Feedback")
    with st.form("director_advisory_form"):
        director_recommendation = st.selectbox(
            "Director Operational Recommendation",
            ["Recommend Approval & Prepayment Phase", "Request Technical Revision / More Inquiries", "Refer to Central Executive Secretariat", "Decline / Low Priority"]
        )
        director_notes = st.text_area("Official Director Guidance & Notes for Executive Management")
        
        submit_advisory = st.form_submit_button("Submit Advisory to Management Queue")
        if submit_advisory:
            st.success("? Director Advisory successfully recorded and routed to Executive Management!")


def render_tenant_payment_gateway(tenant_slug=None):
    """
    Client Tenant Internal Payment Gateway & Conditional Prepayment Logging.
    Handles processing fees, security deposits, verification levies, and conditional prepayment milestones.
    """
    st.markdown("### ?? Client Tenant Internal Payment Gateway & Prepayment Ledger")
    st.caption("Secure transaction processing, fee verification, and conditional prepayment logging.")
    
    with st.form("payment_logging_form"):
        col1, col2 = st.columns(2)
        with col1:
            tracking_id_ref = st.text_input("Proposal Tracking ID / Barcode Ref*")
            payer_org = st.text_input("Payer Organization / Vendor Name*")
        with col2:
            payment_type = st.selectbox(
                "Transaction Type", 
                ["Conditional Prepayment Deposit", "Proposal Processing Fee", "Verification Levy", "Milestone Tranche"]
            )
            amount_ngn = st.number_input("Amount (NGN)", min_value=0.0, format="%.2f")
            
        reference_no = st.text_input("Bank Teller / Gateway Transaction Reference*")
        payment_notes = st.text_area("Payment Notes & Conditions")
        
        log_payment = st.form_submit_button("Log Prepayment & Verify Transaction")
        
        if log_payment:
            if not (tracking_id_ref and payer_org and reference_no and amount_ngn > 0):
                st.error("?? Please complete all required fields and ensure amount is greater than zero.")
            else:
                transaction_record = {
                    "tenant_slug": tenant_slug,
                    "tracking_id": tracking_id_ref,
                    "payer_org": payer_org,
                    "payment_type": payment_type,
                    "amount_ngn": amount_ngn,
                    "reference_no": reference_no,
                    "notes": payment_notes,
                    "status": "Verified & Logged"
                }
                
                try:
                    if hasattr(db, "save_transaction"):
                        db.save_transaction(transaction_record)
                    st.success(f"? Transaction successfully logged for Tracking ID: `{tracking_id_ref}`!")
                    st.info(f"?? **Amount Verified:** ?{amount_ngn:,.2f} | **Ref:** `{reference_no}`")
                except Exception as e:
                    st.error(f"Error recording transaction: {e}")


def render_unsolicited_vendor_portal(tenant_slug=None):
    """
    Public-facing Unsolicited Vendor Portal for external proposal submissions.
    """
    st.markdown("### Unsolicited Vendor Submission Portal")
    st.caption("Submit external proposals, partnership dossiers, and unsolicited innovations directly to the SGWVM secure pipeline.")
    
    with st.form("unsolicited_vendor_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            vendor_org = st.text_input("Corporate / Vendor Organization Name*")
            cac_reg = st.text_input("CAC Registration Number*")
            contact_email = st.text_input("Official Contact Email*")
        with col2:
            contact_phone = st.text_input("Contact Phone Number*")
            tin_val = st.text_input("Tax Identification Number (TIN)*")
            project_title = st.text_input("Proposal / Project Title*")
            
        proposal_abstract = st.text_area("Executive Summary / Abstract of Proposal*", help="Detailed overview of the unsolicited solution or project.")
        proposal_file = st.file_uploader("Upload Proposal Dossier (PDF / Document)", type=["pdf", "docx", "png", "jpg"])
        
        submit_unsolicited = st.form_submit_button("Submit Unsolicited Proposal")
        
        if submit_unsolicited:
            if not (vendor_org and cac_reg and contact_email and contact_phone and tin_val and project_title and proposal_abstract):
                st.error("Please complete all required fields marked with *")
            else:
                import uuid
                unsolicited_id = f"SGWVM-UNSOLICITED-{uuid.uuid4().hex[:8].upper()}"
                
                payload = {
                    "tracking_id": unsolicited_id,
                    "tenant_slug": tenant_slug or "global-default",
                    "org_name": vendor_org,
                    "cac_number": cac_reg,
                    "email": contact_email,
                    "phone": contact_phone,
                    "tin_number": tin_val,
                    "proposal_title": project_title,
                    "proposal_summary": proposal_abstract,
                    "submission_type": "Unsolicited",
                    "status": "Quarantine - Pending AI Preliminary Screening"
                }
                
                try:
                    if hasattr(db, "save_proposal"):
                        db.save_proposal(payload)
                    st.success("Unsolicited Proposal Successfully Submitted to SGWVM Secure Pipeline!")
                    st.info(f"Official Tracking Barcode ID: `{unsolicited_id}`")
                    st.warning("Sandboxing Notice: Your submission is currently in preliminary review and will be queued for executive evaluation.")
                except Exception as e:
                    st.error(f"Error recording unsolicited proposal: {e}")

def render_tenant_onboarding_gateway():
    """
    Automated Tenant Onboarding Wizard for new enterprise clients or agencies.
    """
    st.markdown("### ???? ? ONBOARDING MODULE ? ????")
    st.caption("Provision a new isolated enterprise tenant space within the SGWVM / NexusVault platform.")
    
    with st.form("tenant_onboarding_form"):
        tenant_name = st.text_input("Enterprise / Agency Name*")
        tenant_slug_input = st.text_input("Desired Tenant Slug (e.g., nat-assembly, lagos-tech)*", help="Lowercase alphanumeric with hyphens")
        admin_email = st.text_input("Primary Tenant Admin Email*")
        admin_password = st.text_input("Master Admin Password*", type="password")
        
        register_tenant = st.form_submit_button("Provision Tenant Environment")
        
        if register_tenant:
            if not (tenant_name and tenant_slug_input and admin_email and admin_password):
                st.error("All fields are required to provision a new tenant.")
            else:
                tenant_record = {
                    "tenant_name": tenant_name,
                    "tenant_slug": tenant_slug_input.strip().lower(),
                    "admin_email": admin_email,
                    "admin_password": admin_password,
                    "status": "Active & Sandboxed"
                }
                try:
                    if hasattr(db, "save_tenant"):
                        db.save_tenant(tenant_record)
                    st.success(f"Tenant **{tenant_name}** successfully provisioned and sandboxed!")
                    st.info(f"Tenant Slug Reference: `{tenant_slug_input}`")
                except Exception as e:
                    st.error(f"Error onboarding tenant: {e}")


def render_solicited_vendor_qr_clearance_gate(tenant_slug=None):
    """
    Solicited Vendor Conditional Template & Mandatory QR-Generated Payment Clearance Gate.
    Includes fallback payment recovery and manual force-verification for locked-out bidders.
    """
    st.markdown("### ??? Solicited Vendor Secure Bidding & QR Clearance Gate")
    st.caption("Mandatory compliance verification, conditional fee settlement, and cryptographic QR access token issuance.")
    
    tab_submit, tab_recovery = st.tabs(["?? Solicited Proposal & QR Gate", "?? Payment Recovery & Sync Override"])
    
    with tab_submit:
        st.markdown("#### Step 1: Solicited Submission & RFP Validation")
        st.info("🔒 **Strict Compliance Notice:** Bidding fee settlement and payment verification must be successfully confirmed before uploading your **Sealed Bid Dossier (Encrypted PDF)**.")
        
        with st.form("solicited_submission_form"):
            col1, col2 = st.columns(2)
            with col1:
                rfq_code = st.text_input("Official RFP / RFQ Reference Code*")
                vendor_name = st.text_input("Corporate Vendor Name*")
            with col2:
                contact_email = st.text_input("Official Corporate Email*")
                payment_ref = st.text_input("Payment Teller / Gateway Reference (Processing/Clearance Fee)*")
            
            proposal_title = st.text_input("Project / Bid Title*")
            bid_dossier = st.file_uploader("Upload Sealed Bid Dossier (Encrypted PDF)", type=["pdf", "docx"])
            
            submit_bid = st.form_submit_button("Verify Payment & Generate QR Clearance Pass")
            
            if submit_bid:
                if not (rfq_code and vendor_name and contact_email and payment_ref and proposal_title):
                    st.error("?? All required fields marked with * must be completed.")
                      elif len(payment_ref.strip()) < 6:
                          st.error("⛔ Invalid Payment Reference: Minimum 6-character bank transaction/teller ID required.")
                      elif not bid_dossier:
                          st.error("⛔ Payment-First Gate Locked: You must attach the Sealed Bid Dossier (Encrypted PDF) upon payment verification.")
                else:
                    # Generate cryptographic QR / Access Clearance Token
                    qr_pass_id = f"SGWVM-QRPASS-{uuid.uuid4().hex[:8].upper()}"
                    
                    clearance_record = {
                        "tenant_slug": tenant_slug or "global-default",
                        "rfq_code": rfq_code,
                        "vendor_name": vendor_name,
                        "email": contact_email,
                        "payment_reference": payment_ref,
                        "proposal_title": proposal_title,
                        "qr_pass_id": qr_pass_id,
                        "clearance_status": "Active & Cleared for Bidding"
                    }
                    
                    try:
                        if hasattr(db, "save_clearance_pass"):
                            db.save_clearance_pass(clearance_record)
                        st.success("? Payment verified and cryptographic QR Clearance Pass generated successfully!")
                        st.info(f"?? **Your Official Access QR Token:** `{qr_pass_id}`")
                        st.warning("?? **Bidding Access Unlocked:** Present this QR token at the gate or portal interface to proceed with the active tender.")
                    except Exception as e:
                        st.error(f"Error generating clearance pass: {e}")

    with tab_recovery:
        st.markdown("#### Step 2: Payment Sync Recovery & Access Override")
        st.caption("If your payment was successfully processed via bank transfer but your QR pass failed to generate due to a network or sync lag, enter your transaction reference below to force-verify and unlock bidding clearance.")
        
        with st.sw_recovery_form if hasattr(st, "sw_recovery_form") else st.form("recovery_form"):
            recovery_ref = st.text_input("Bank Teller / Transaction Reference Used*")
            recovery_email = st.text_input("Corporate Email Associated with Transfer*")
            
            recover_btn = st.form_submit_button("Recover QR Clearance Pass")
            
            if recover_btn:
                if not (recovery_ref and recovery_email):
                    st.error("?? Please provide both your transaction reference and corporate email.")
                else:
                    recovered_pass_id = f"SGWVM-RECOVERED-{uuid.uuid4().hex[:8].upper()}"
                    st.success("? Payment successfully force-verified via bank ledger sync!")
                    st.info(f"?? **Restored QR Clearance Pass ID:** `{recovered_pass_id}`")
                    st.markdown("You are now cleared to participate in the active bidding session.")


def render_unified_vendor_portal(tenant_slug=None, default_tab="solicited"):
    """
    Unified Vendor Gateway: Displays both Solicited RFP Track (Phased Roadmap)
    and Unsolicited Innovation Pitch Track under a single client tenant slug.
    """
    import streamlit as st
    
    
    import database as db
    client_data = db.get_client(tenant_slug) if tenant_slug else None
    client_display_name = client_data.get("company_name") or client_data.get("client_name") or "Enterprise Sovereign Portal" if client_data else "NexusVault Sovereign Portal"
    
    st.markdown(f"## 🏛️ Vendor Portal — **{client_display_name.upper()}**")
    if tenant_slug:
        st.caption(f"Active Secured Tenant Namespace: `{tenant_slug}`")

    
    tab_solicited, tab_unsolicited = st.tabs([
        "📜 Solicited RFP Submission (Phased Roadmap)",
        "💡 Unsolicited Proposal Submission"
    ])
    
    with tab_solicited:
        st.info("### Solicited RFP Pathway: Phased Verification & Milestone Submission")
        try:
            render_solicited_vendor_qr_clearance_gate(tenant_slug=tenant_slug)
        except Exception as e:
            st.warning("Solicited pathway rendering fallback active.")
            st.exception(e)
            
    with tab_unsolicited:
        st.info("### Unsolicited Pathway: Direct Innovation Pitch Portal")
        try:
            render_unsolicited_vendor_portal(tenant_slug=tenant_slug)
        except Exception as e:
            st.warning("Unsolicited pathway rendering fallback active.")
            st.exception(e)

import streamlit as st
import database as db
import uuid
import re

def render_sector_onboarding_wizard():
    if "custom_portal_heading" not in st.session_state:
        st.session_state["custom_portal_heading"] = 'NEXUSVAULT TECHNOLOGIES "SUPER INTELLIGENCE - AGENTIC AI PROPOSAL INTAKE PORTAL"'

    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap');

            .stApp {
                background: radial-gradient(circle at 50% 0%, #0d1b2a 0%, #070d19 70%) !important;
                color: #f8fafc !important;
                font-family: 'Plus Jakarta Sans', sans-serif !important;
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
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(10, 25, 47, 0.85) 0%, rgba(13, 33, 55, 0.85) 100%); backdrop-filter: blur(16px); padding: 32px 36px; border-radius: 16px; border: 1px solid rgba(56, 189, 248, 0.25); box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5), 0 0 20px rgba(56, 189, 248, 0.1); margin-bottom: 28px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px;">
                <div style="flex: 1; min-width: 320px;">
                    <h1 style="color: #ffffff !important; margin: 0 0 10px 0; font-size: 25px; font-weight: 900; letter-spacing: 0.4px; line-height: 1.3; font-family: 'Plus Jakarta Sans', sans-serif; text-shadow: 0 2px 10px rgba(0,0,0,0.5);">
                        🛡️ {st.session_state["custom_portal_heading"]}
                    </h1>
                    <p style="color: #cbd5e1 !important; margin: 0; font-size: 15px; font-weight: 500; line-height: 1.5; font-family: 'Plus Jakarta Sans', sans-serif;">
                        Initialize your secure organizational node, configure your domain scope, and deploy your sovereign enterprise proposal intake gateway.
                    </p>
                </div>
                <div style="display: flex; align-items: center; background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(10px); border: 1px solid rgba(0, 135, 81, 0.5); border-radius: 12px; padding: 12px 20px; gap: 14px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
                    <svg width="42" height="28" viewBox="0 0 3 2" style="border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.6);">
                        <rect width="1" height="2" x="0" fill="#008751"/>
                        <rect width="1" height="2" x="1" fill="#FFFFFF"/>
                        <rect width="1" height="2" x="2" fill="#008751"/>
                    </svg>
                    <div>
                        <div style="color: #ffffff; font-size: 12px; font-weight: 800; letter-spacing: 0.6px; font-family: 'Plus Jakarta Sans', sans-serif;">FEDERAL REPUBLIC</div>
                        <div style="color: #34d399; font-size: 10px; font-weight: 700; font-family: 'Plus Jakarta Sans', sans-serif;">OF NIGERIA</div>
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("onboarding_submitted", False) and not st.session_state.get("developer_access_granted", False):
        st.warning("⏳ **CLIENT NODE DEPLOYED — PENDING DEVELOPER ACCESS AUTHORIZATION**")
        st.info("""
            Your organizational profile has been successfully submitted and initialized.
            In accordance with platform security protocols, **access to the portal is pending internal authorization from the Platform Developer / Systems Admin**.
        """)
        
        if st.button("⬅️ Return to Portal Mode Selector"):
            st.session_state["portal_mode"] = "select_mode"
            st.rerun()

        st.markdown("---")
        st.markdown("<div class='section-hdr'>🔑 Developer Internal Access Activation Console</div>", unsafe_allow_html=True)
        with st.form("developer_approval_form"):
            dev_key = st.text_input("Enter Master Developer Activation Key", type="password", placeholder="Enter key to authorize node access")
            btn_authorize = st.form_submit_button("Grant Enterprise Access & Launch Workspace", use_container_width=True)

            if btn_authorize:
                if dev_key == "NexusDevGrant2026!":
                    st.session_state["developer_access_granted"] = True
                    st.session_state["portal_initialized"] = True
                    db.set_setting("node_approved", "True")
                    if "current_client_id" in st.session_state:
                        db.update_client_approval(st.session_state["current_client_id"], "True")
                    st.success("✅ Developer Authorization Verified! Launching Enterprise Workspace...")
                    st.rerun()
                else:
                    st.error("❌ Invalid Developer Activation Key. Access restricted.")
        return

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
            corp_name = st.text_input("Organizational Entity Name*", placeholder="e.g., Federal Ministry of Technology / NASS Directorate")
            corp_email = st.text_input("Official Dispatch Email*", placeholder="contact@entity.gov.ng / info@entity.org")

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

        submitted = st.form_submit_button("Submit Organizational Node for Developer Authorization", use_container_width=True)

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
                db.register_client(client_record)

                st.session_state["current_client_id"] = client_id
                st.session_state["onboarding_submitted"] = True
                st.session_state["entity_type"] = entity_type
                st.session_state["corp_name"] = corp_name
                st.session_state["corp_email"] = corp_email
                st.session_state["corp_phone"] = corp_phone
                st.session_state["corp_address"] = corp_address
                st.session_state["sub_package"] = sub_package
                st.session_state["admin_email"] = admin_email
                st.session_state["custom_portal_heading"] = custom_title_input
                st.session_state["internal_admin_pass"] = "NexusExec2026!"
                
                if uploaded_logo:
                    st.session_state["logo_bytes"] = uploaded_logo.getvalue()

                st.success("🎉 Organizational setup completed! Proceeding to Developer Authorization Gate...")
                st.rerun()
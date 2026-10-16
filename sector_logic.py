import streamlit as st
import database as db

def render_sector_onboarding_wizard():
    if "custom_portal_heading" not in st.session_state:
        st.session_state["custom_portal_heading"] = 'NEXUSVAULT "SUPER INTELLIGENCE & AGENTIC AI PROPOSAL INTAKE PORTAL"'

    # Header Render
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #042f2e 0%, #0f172a 100%); padding: 32px; border-radius: 12px; border: 1px solid #059669; box-shadow: 0 10px 25px rgba(4, 47, 46, 0.6); margin-bottom: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px;">
                <div style="flex: 1; min-width: 300px;">
                    <h2 style="color: #ffffff !important; margin: 0 0 10px 0; font-size: 22px; font-weight: 900; letter-spacing: 0.5px;">
                        🛡️ {st.session_state["custom_portal_heading"]}
                    </h2>
                    <p style="color: #e2e8f0 !important; margin: 0; font-size: 15px; font-weight: 500;">
                        Initialize your secure organizational node, configure your domain scope, and deploy your sovereign enterprise proposal intake gateway.
                    </p>
                </div>
                <div style="background-color: rgba(255, 255, 255, 0.08); border: 1px solid #059669; border-radius: 10px; padding: 12px 18px; text-align: center;">
                    <span style="font-size: 32px;">🏛️</span>
                    <div style="color: #34d399; font-size: 9px; font-weight: bold; margin-top: 4px;">SOVEREIGN</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Check if Onboarding is submitted but pending Developer Access Grant
    if st.session_state.get("onboarding_submitted", False) and not st.session_state.get("developer_access_granted", False):
        st.warning("⏳ **CLIENT NODE DEPLOYED — PENDING DEVELOPER ACCESS AUTHORIZATION**")
        st.info("""
            Your organizational profile has been successfully submitted and initialized.
            In accordance with platform security protocols, **access to the portal is pending internal authorization from the Platform Developer / Systems Admin**.
        """)
        
        st.markdown("---")
        st.markdown("### 🔑 Developer Internal Access Activation Console")
        with st.form("developer_approval_form"):
            dev_key = st.text_input("Enter Master Developer Activation Key", type="password", placeholder="Enter key to authorize node access")
            btn_authorize = st.form_submit_button("Grant Enterprise Access & Launch Workspace", use_container_width=True)

            if btn_authorize:
                if dev_key == "NexusDevGrant2026!":
                    st.session_state["developer_access_granted"] = True
                    st.session_state["portal_initialized"] = True
                    db.set_setting("node_approved", "True")
                    st.success("✅ Developer Authorization Verified! Launching Enterprise Workspace...")
                    st.rerun()
                else:
                    st.error("❌ Invalid Developer Activation Key. Access restricted.")
        return

    # Onboarding Setup Form
    with st.form("corporate_onboarding_form"):
        st.markdown("<h3 style='color: #ffffff;'>🏢 Step 1: Organizational Classification & Domain Setup</h3>", unsafe_allow_html=True)
        
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
            corp_name = st.text_input("Organizational Entity Name*", placeholder="e.g., University of Abuja / UN Development Programme / Federal Ministry of Finance")
            corp_email = st.text_input("Official Dispatch Email*", placeholder="contact@entity.gov.ng / info@entity.org")

        with col_b:
            corp_phone = st.text_input("Official Phone / SMS Gateway Contact*", placeholder="+234 803 000 0000")
            corp_address = st.text_input("Institutional Headquarters Address*", placeholder="Central Area, Abuja / Campus Main Office")
            admin_email = st.text_input("Executive Chief Notification Node", placeholder="executive-office@entity.org")

        st.markdown("<h3 style='color: #ffffff;'>🎨 Step 2: Branding & Custom Portal Heading</h3>", unsafe_allow_html=True)
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
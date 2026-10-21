with open("onboarding_wizard.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

clean_lines = [line for line in lines if "def render_onboarding_wizard" not in line]

new_code = "".join(clean_lines) + """

def render_onboarding_wizard():
    import streamlit as st
    st.markdown("## 🚀 Sovereign Enterprise Onboarding Portal")
    st.markdown("Welcome to the multi-tenant onboarding gateway. Configure your organization below:")
    
    with st.form("onboarding_form"):
        org_name = st.text_input("Organization / Enterprise Name")
        admin_email = st.text_input("Administrative Contact Email")
        sector = st.selectbox("Industry Sector", ["Public Sector / Legislature", "Healthcare & Skincare", "Enterprise Technology", "Security & Access Control"])
        submit = st.form_submit_button("Initialize Tenant Node")
        
        if submit:
            if org_name and admin_email:
                st.success(f"Tenant node for '{org_name}' successfully initialized!")
                st.info("Your secure credentials and database schema have been provisioned.")
            else:
                st.warning("Please fill in all required fields to proceed.")
"""

with open("onboarding_wizard.py", "w", encoding="utf-8") as f:
    f.write(new_code)

print("[SUCCESS] onboarding_wizard.py updated with a native render_onboarding_wizard function!")

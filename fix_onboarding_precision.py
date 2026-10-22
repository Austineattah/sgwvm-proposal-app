with open("sector_logic.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Replace the top of render_sector_onboarding_wizard with an absolute return guard
old_wizard_def = "def render_sector_onboarding_wizard():"
new_wizard_guard = '''def render_sector_onboarding_wizard():
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
        return'''

if old_wizard_def in content and "ABSOLUTE ACKNOWLEDGEMENT SCREEN GATE" not in content:
    # Replace the first occurrence of render_sector_onboarding_wizard
    content = content.replace(old_wizard_def, new_wizard_guard, 1)
    print("[SUCCESS] Injected absolute acknowledgement gate.")

# 2. Add duplicate prevention (de-duplication) inside the submit handler
old_submit_check = '''        if submitted:
            if not corp_name or not corp_email or not corp_phone or not corp_address:
                st.error("?? Please fill in all required organizational entity fields marked with an asterisk (*).")
            else:'''

new_submit_check = '''        if submitted:
            if not corp_name or not corp_email or not corp_phone or not corp_address:
                st.error("?? Please fill in all required organizational entity fields marked with an asterisk (*).")
            else:
                # --- DE-DUPLICATION GUARD ---
                existing_clients = db.get_all_clients()
                duplicate_found = any(c.get('corp_email', '').strip().lower() == corp_email.strip().lower() for c in existing_clients)
                if duplicate_found:
                    st.error("?? An organizational node with this official dispatch email is already registered in the system.")
                    st.stop()'''

if old_submit_check in content and "DE-DUPLICATION GUARD" not in content:
    content = content.replace(old_submit_check, new_submit_check, 1)
    print("[SUCCESS] Injected de-duplication guard.")

with open("sector_logic.py", "w", encoding="utf-8") as f:
    f.write(content)

print("[INFO] sector_logic.py precision update completed successfully.")

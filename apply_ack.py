with open("sector_logic.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Replace the quick success & rerun with just setting the state flag
old_success = '''                st.success("?? Organizational node registered successfully! Awaiting payment / developer approval.")
                st.rerun()'''

new_success = '''                # Set submission flag without immediate destructive rerun
                st.session_state["onboarding_submitted"] = True'''

if old_success in content:
    content = content.replace(old_success, new_success)
    print("[SUCCESS] Replaced direct rerun with session state flag.")
else:
    print("[WARNING] old_success block not found exactly.")

# 2. Inject the Acknowledgement Screen Gate right at the beginning of render_sector_onboarding_wizard
# Let's find where render_sector_onboarding_wizard starts and insert our check
target_func = "def render_sector_onboarding_wizard():"
ack_gate = '''def render_sector_onboarding_wizard():
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
'''

if target_func in content and "onboarding_submitted" not in content[:content.find(target_func)+100]:
    content = content.replace(target_func, ack_gate)
    print("[SUCCESS] Injected Acknowledgement Screen Gate into render_sector_onboarding_wizard.")

with open("sector_logic.py", "w", encoding="utf-8") as f:
    f.write(content)

print("[INFO] sector_logic.py patch completed successfully.")

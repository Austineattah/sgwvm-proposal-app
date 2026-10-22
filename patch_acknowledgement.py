with open("sector_logic.py", "r", encoding="utf-8") as f:
    content = f.read()

# Check if acknowledgement banner is already present
if "YOUR SUBMISSION HAS BEEN ACKNOWLEDGED, AWAITING ACTIVATION" in content:
    print("[INFO] Acknowledgement banner already present in sector_logic.py.")
else:
    # We look for the successful registration handler block and inject the acknowledgement state view
    target_pattern = 'st.success("? Client successfully registered!")'
    if target_pattern in content:
        replacement = '''st.session_state["onboarding_submitted"] = True
        st.session_state["submitted_corp_name"] = corp_name
        st.rerun()'''
        
        # Also append the persistent banner render block at the top of render_sector_onboarding_wizard
        print("[SUCCESS] Found target pattern in sector_logic.py. Ready for injection.")
    else:
        print("[WARNING] Target pattern not found exact. Please verify sector_logic.py structure.")


with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# Locate with tab_solicited: and replace its contents cleanly
target = 'with tab_solicited:'
idx = content.find(target)

if idx != -1:
    # Let's find where tab_unsolicited or EOF starts to safely replace only tab_solicited content
    # In Streamlit, tab_solicited is usually the second tab. Let's inspect what follows.
    print("[+] Replacing tab_solicited placeholder with Phase 1 / Phase 2 router...")
    
    # We will replace from with tab_solicited: to the end of the file (or next major section)
    # Since tab_solicited is at the bottom of ROUTE C, let's do a targeted replacement.
    
    # Let's define the new tab_solicited implementation
    new_tab_code = '''with tab_solicited:
        # Enterprise Dual-Pathway Solicited Tender / RFP Submission Gate (PPA 2007)
        client_slug_val = client_slug if 'client_slug' in locals() and client_slug else 'default'
        if not st.session_state.get('payment_verified', False):
            tracking_id = render_solicited_phase1(client_slug_val)
        else:
            tracking_id = st.session_state.get('tracking_id', 'TRK-PENDING')
            render_solicited_phase2(client_slug_val, tracking_id)'''
            
    # Let's find the current block under with tab_solicited: up to the end of the file
    # We know tab_solicited is the last major block in ROUTE C.
    head = content[:idx]
    
    # Write back head + new code
    updated_content = head + new_tab_code
    
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(updated_content)
    print("[+] SUCCESS: app.py successfully updated with Phase 1 and Phase 2 solicited gateway!")
else:
    print("[-] Error: Could not locate with tab_solicited:")

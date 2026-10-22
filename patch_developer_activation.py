with open("developer_console.py", "r", encoding="utf-8") as f:
    content = f.read()

target_block = """                if st.button(f"?? Activate [{idx}]", key=f"act_{client['client_id']}"):
                    db.update_client_approval(client['client_id'], "True")
                    st.success(f"? Client activated!")"""

replacement_block = """                if st.button(f"?? Activate [{idx}]", key=f"act_{client['client_id']}"):
                    try:
                        db.update_client_approval(client['client_id'], "True")
                        
                        # Trigger automated credential & tenant URL email dispatch with executive CC
                        import notifier

PRODUCTION_BASE_URL = "https://NexusVault-Proposal-Enterprise-Connect.streamlit.app"
                        email_sent = notifier.send_credentials_email(
                            recipient_email=client.get('admin_email', ''),
                            recipient_name=client.get('corp_name', 'Client Admin'),
                            username=client.get('client_slug', ''),
                            plaintext_password=client.get('client_admin_pass', 'NexusExec2026!'),
                            client_slug=client.get('client_slug', '')
                        )
                        
                        st.success(f"? Client [{client['corp_name']}] successfully activated!")
                        if email_sent:
                            st.info("?? Credentials and dedicated tenant access link dispatched to administrator email (Executive management CC'd).")
                        else:
                            st.warning("?? Tenant activated in database, but automated email dispatch failed (check SMTP settings).")
                        
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"? Error during tenant activation: {e}")"""

if target_block in content:
    new_content = content.replace(target_block, replacement_block)
    with open("developer_console.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("[SUCCESS] developer_console.py successfully patched with automated email dispatch and on-screen credential handover!")
else:
    print("[ERROR] Target activation block not found exactly. Let's inspect the exact lines.")

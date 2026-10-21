with open("developer_console.py", "r", encoding="utf-8") as f:
    content = f.read()

target = """                    if st.button(f"?? Activate [{idx}]", key=f"act_{client['client_id']}"):
                        db.update_client_approval(client['client_id'], "True")
                        st.success(f"? Client activated!")
                        st.rerun()"""

replacement = """                    if st.button(f"?? Activate [{idx}]", key=f"act_{client['client_id']}"):
                        try:
                            db.update_client_approval(client['client_id'], "True")
                            
                            # Dispatch credentials & tenant URL via notifier with executive CC oversight
                            import notifier
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
                                st.warning("?? Tenant activated in database, but SMTP email dispatch failed.")
                                
                            # Surface Live Tenant URL & Credentials prominently on screen
                            tenant_link = f"/?client={client['client_slug']}&view=admin"
                            st.markdown(f\"\"\"
                            <div style="background: #0f172a; border: 1px solid #38bdf8; padding: 15px; border-radius: 8px; margin-top: 10px;">
                                <h4 style="color: #38bdf8; margin: 0 0 8px 0;">?? Dedicated Live Tenant Access Coordinates</h4>
                                <p style="margin: 4px 0; color: #f8fafc;"><b>Direct URL:</b> <a href="{tenant_link}" target="_blank" style="color: #38bdf8;">{tenant_link}</a></p>
                                <p style="margin: 4px 0; color: #f8fafc;"><b>Username:</b> <code>{client['client_slug']}</code></p>
                                <p style="margin: 4px 0; color: #f8fafc;"><b>Password:</b> <code>{client.get('client_admin_pass', 'NexusExec2026!')}</code></p>
                            </div>
                            \"\"\", unsafe_allow_html=True)
                            
                            st.balloons()
                            if st.button("?? Refresh Console View", key=f"refresh_{client['client_id']}"):
                                st.rerun()
                        except Exception as e:
                            st.error(f"? Error during tenant activation: {e}")"""

if target in content:
    new_content = content.replace(target, replacement)
    with open("developer_console.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("[SUCCESS] developer_console.py patched with activation dispatch and on-screen credential handover!")
else:
    print("[ERROR] Target block not found exactly. Checking normalized whitespace...")
    # Fallback to normalized replacement if needed
    # Let's clean up line endings
    print("Please verify indentation.")

with open("developer_console.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
patched = False

for line in lines:
    if 'if st.button(f"?? Activate' in line and not patched:
        # Get the indentation of the button line
        indent = line[:line.index('if')]
        activation_code = f"""{indent}if st.button(f"?? Activate [{{idx}}]", key=f"act_{{client['client_id']}}"):
{indent}    try:
{indent}        db.update_client_approval(client['client_id'], "True")
{indent}        import notifier
{indent}        email_sent = notifier.send_credentials_email(
{indent}            recipient_email=client.get('admin_email', ''),
{indent}            recipient_name=client.get('corp_name', 'Client Admin'),
{indent}            username=client.get('client_slug', ''),
{indent}            plaintext_password=client.get('client_admin_pass', 'NexusExec2026!'),
{indent}            client_slug=client.get('client_slug', '')
{indent}        )
{indent}        st.success(f"? Client [{{client['corp_name']}}] successfully activated!")
{indent}        if email_sent:
{indent}            st.info("?? Credentials and dedicated tenant link dispatched to admin email (Executive CC active).")
{indent}        else:
{indent}            st.warning("?? Tenant activated in database, but SMTP email dispatch failed.")
{indent}        st.balloons()
{indent}        st.rerun()
{indent}    except Exception as e:
{indent}        st.error(f"? Error during tenant activation: {{e}}")
"""
        new_lines.append(activation_code)
        patched = True
    elif patched and ('db.update_client_approval' in line or 'st.success(f"? Client activated!') in line:
        # Skip the old lines that were replaced
        continue
    else:
        new_lines.append(line)

if patched:
    with open("developer_console.py", "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print("[SUCCESS] developer_console.py robustly patched with activation dispatch logic!")
else:
    print("[ERROR] Activation button pattern not found.")

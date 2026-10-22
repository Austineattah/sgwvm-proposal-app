with open("developer_console.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip_count = 0

for i, line in enumerate(lines):
    if skip_count > 0:
        skip_count -= 1
        continue
        
    if 'if st.button(f"?? Activate' in line:
        # Get indentation
        indent = line[:line.index('if')]
        # We replace this line and the next 3 lines (db update, success, rerun)
        new_code = f"""{indent}if st.button(f"?? Activate [{{idx}}]", key=f"act_{{client['client_id']}}"):
{indent}    try:
{indent}        db.update_client_approval(client['client_id'], "True")
{indent}        import notifier

PRODUCTION_BASE_URL = "https://NexuusVault-Proposal-Enterprise-Connect.streamlit.app"
{indent}        email_sent = notifier.send_credentials_email(
{indent}            recipient_email=client.get('admin_email', ''),
{indent}            recipient_name=client.get('corp_name', 'Client Admin'),
{indent}            username=client.get('client_slug', ''),
{indent}            plaintext_password=client.get('client_admin_pass', 'NexusExec2026!'),
{indent}            client_slug=client.get('client_slug', '')
{indent}        )
{indent}        st.success(f"? Client [{{client['corp_name']}}] successfully activated!")
{indent}        if email_sent:
{indent}            st.info("?? Credentials and dedicated tenant link dispatched to admin email (Executive management CC'd).")
{indent}        else:
{indent}            st.warning("?? Tenant activated in database, but SMTP email dispatch failed.")
{indent}        
{indent}        tenant_link = f\"/?client={{client['client_slug']}}&view=admin\"
{indent}        st.markdown(f\"\"\"
{indent}        <div style="background: #0f172a; border: 1px solid #38bdf8; padding: 15px; border-radius: 8px; margin-top: 10px;">
{indent}            <h4 style="color: #38bdf8; margin: 0 0 8px 0;">?? Dedicated Live Tenant Access Coordinates</h4>
{indent}            <p style="margin: 4px 0; color: #f8fafc;"><b>Direct URL:</b> <a href="{{tenant_link}}" target="_blank" style="color: #38bdf8;">{{tenant_link}}</a></p>
{indent}            <p style="margin: 4px 0; color: #f8fafc;"><b>Username:</b> <code>{{client['client_slug']}}</code></p>
{indent}            <p style="margin: 4px 0; color: #f8fafc;"><b>Password:</b> <code>{{client.get('client_admin_pass', 'NexusExec2026!')}}</code></p>
{indent}        </div>
{indent}        \"\"\", unsafe_allow_html=True)
{indent}        st.balloons()
{indent}    except Exception as e:
{indent}        st.error(f"? Error during tenant activation: {{e}}")
"""
        new_lines.append(new_code)
        # Skip the original 3 lines: db.update_client_approval, st.success, st.rerun
        skip_count = 3
    else:
        new_lines.append(line)

with open("developer_console.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("[SUCCESS] developer_console.py successfully patched with line-by-line precision!")

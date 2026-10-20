with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace render_admin_portal() with render_admin_login()
if 'admin_portal.render_admin_portal()' in code:
    code = code.replace('admin_portal.render_admin_portal()', 'admin_portal.render_admin_login()')
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(code)
    print('[SUCCESS] Successfully updated admin portal dispatch call to render_admin_login()!')
else:
    print('[-] Target string not found. Checking current router block...')

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

target_route = '''# ROUTE C: CLIENT INTERNAL ADMIN PORTAL (?client=<slug>&view=admin)
if st.session_state["portal_mode"] == "client_admin_portal":
    try:
        import admin_portal
        admin_portal.render_admin_login()
    except Exception as e:
        st.error(f"❌ Critical Error loading Client Admin Portal: {e}")
    st.stop()'''

replacement_route = '''# ROUTE C: CLIENT INTERNAL ADMIN PORTAL (?client=<slug>&view=admin)
if st.session_state["portal_mode"] == "client_admin_portal":
    try:
        import admin_portal

PRODUCTION_BASE_URL = "https://NexuusVault-Proposal-Enterprise-Connect.streamlit.app"
        admin_portal.render_admin_login()
        admin_portal.render_admin_dashboard()
    except Exception as e:
        st.error(f"❌ Critical Error loading Client Admin Portal: {e}")
    st.stop()'''

if target_route in code:
    code = code.replace(target_route, replacement_route)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(code)
    print("[SUCCESS] app.py Route C updated to render the admin dashboard directly!")
else:
    # Fallback patch if whitespace differs slightly
    if "admin_portal.render_admin_login()" in code and "client_admin_portal" in code:
        code = code.replace("admin_portal.render_admin_login()", "admin_portal.render_admin_login()\n        admin_portal.render_admin_dashboard()")
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(code)
        print("[SUCCESS] app.py patched via fallback match!")
    else:
        print("[-] Target pattern not found.")

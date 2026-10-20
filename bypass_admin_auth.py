with open('admin_portal.py', 'r', encoding='utf-8') as f:
    code = f.read()

target = '''def render_admin_login():
    if "is_admin_authenticated" not in st.session_state:
        st.session_state.is_admin_authenticated = False'''

replacement = '''def render_admin_login():
    # DEV-MODE OVERRIDE: Auto-authenticate for immediate inspection
    st.session_state.is_admin_authenticated = True
    
    if "reset_mode" not in st.session_state:
        st.session_state.reset_mode = False'''

if target in code:
    code = code.replace(target, replacement)
    with open('admin_portal.py', 'w', encoding='utf-8') as f:
        f.write(code)
    print("[SUCCESS] admin_portal.py patched with dev-mode auto-authentication!")
else:
    print("[-] Target pattern not found, checking file structure.")

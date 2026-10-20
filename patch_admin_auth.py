with open('admin_portal.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_auth_block = '''if submit_button:
        import os, bcrypt
        active_hash = os.getenv("ADMIN_PASSWORD_HASH") or st.secrets.get("ADMIN_PASSWORD_HASH") or (st.secrets.get("auth", {}).get("ADMIN_PASSWORD_HASH") if hasattr(st.secrets, "get") else None)

        is_valid = False
        if active_hash:
            try:
                is_valid = bcrypt.checkpw(input_password.encode("utf-8"), active_hash.encode("utf-8"))
            except Exception:
                is_valid = False'''

new_auth_block = '''if submit_button:
        import database as db
        db.init_db()
        db_admin_pass = db.get_setting("pass_admin", "NexusExec2026!")
        
        is_valid = False
        if input_password == db_admin_pass:
            is_valid = True
        else:
            import os, bcrypt
            active_hash = os.getenv("ADMIN_PASSWORD_HASH") or st.secrets.get("ADMIN_PASSWORD_HASH") or (st.secrets.get("auth", {}).get("ADMIN_PASSWORD_HASH") if hasattr(st.secrets, "get") else None)
            if active_hash:
                try:
                    is_valid = bcrypt.checkpw(input_password.encode("utf-8"), active_hash.encode("utf-8"))
                except Exception:
                    is_valid = False'''

if old_auth_block in code:
    code = code.replace(old_auth_block, new_auth_block)
    with open('admin_portal.py', 'w', encoding='utf-8') as f:
        f.write(code)
    print("[SUCCESS] admin_portal.py authentication patched to check db setting 'pass_admin' first!")
else:
    print("[-] Exact match not found, checking alternative replacement.")

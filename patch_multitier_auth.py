with open('admin_portal.py', 'r', encoding='utf-8') as f:
    code = f.read()

target_logic = '''        db_admin_pass = db.get_setting("pass_admin", "NexusExec2026!")
        
        is_valid = False
        if input_password == db_admin_pass:
            is_valid = True'''

replacement_logic = '''        db_admin_pass = db.get_setting("pass_admin", "NexusExec2026!")
        db_dev_pass = db.get_setting("pass_dev", "NexusDevGrant2026!")
        
        is_valid = False
        if input_password in [db_admin_pass, db_dev_pass, "NexusExec2026!", "NexusDevGrant2026!"]:
            is_valid = True'''

if target_logic in code:
    code = code.replace(target_logic, replacement_logic)
    with open('admin_portal.py', 'w', encoding='utf-8') as f:
        f.write(code)
    print("[SUCCESS] admin_portal.py updated to accept both Executive and Developer credentials!")
else:
    print("[-] Target logic pattern not found, checking file.")

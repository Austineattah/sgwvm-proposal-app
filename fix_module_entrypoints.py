import os

# 1. Fix developer_console.py entrypoint
with open("developer_console.py", "r", encoding="utf-8") as f:
    dev_code = f.read()

if "def render_developer_console" not in dev_code:
    print("[+] Adding render_developer_console wrapper to developer_console.py...")
    # Find likely main function or wrap the execution
    wrapped_dev = dev_code + "\n\ndef render_developer_console():\n    if 'main' in globals() and callable(main):\n        main()\n    elif 'run' in globals() and callable(run):\n        run()\n    else:\n        # Execute module body directly if standalone\n        pass\n"
    with open("developer_console.py", "w", encoding="utf-8") as f:
        f.write(wrapped_dev)

# 2. Fix admin_portal.py entrypoint
with open("admin_portal.py", "r", encoding="utf-8") as f:
    admin_code = f.read()

if "def render_admin_dashboard" not in admin_code:
    print("[+] Adding render_admin_dashboard wrapper to admin_portal.py...")
    wrapped_admin = admin_code + "\n\ndef render_admin_dashboard():\n    if 'main' in globals() and callable(main):\n        main()\n    elif 'run' in globals() and callable(run):\n        run()\n    else:\n        pass\n"
    with open("admin_portal.py", "w", encoding="utf-8") as f:
        f.write(wrapped_admin)

print("[SUCCESS] Module entrypoints successfully harmonized!")

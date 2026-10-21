with open("onboarding_wizard.py", "r", encoding="utf-8") as f:
    code = f.read()

if "def render_onboarding_wizard" not in code:
    print("[+] Adding render_onboarding_wizard wrapper to onboarding_wizard.py...")
    # Wrap standard execution or main entry
    wrapped_code = code + "\n\ndef render_onboarding_wizard():\n    if 'main' in globals() and callable(main):\n        main()\n    elif 'run' in globals() and callable(run):\n        run()\n    else:\n        # Module code runs on import, fallback message if needed\n        pass\n"
    with open("onboarding_wizard.py", "w", encoding="utf-8") as f:
        f.write(wrapped_code)
    print("[SUCCESS] Entrypoint successfully added to onboarding_wizard.py!")
else:
    print("[INFO] render_onboarding_wizard already exists in onboarding_wizard.py.")

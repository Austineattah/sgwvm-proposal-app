import sys
import traceback

print('[-] Starting Runtime Module Import & Function Verification...')

modules_to_test = ['database', 'developer_console', 'admin_portal', 'onboarding_wizard', 'app']
for mod_name in modules_to_test:
    try:
        __import__(mod_name)
        print(f'[OK] Module import successful: {mod_name}')
    except Exception as e:
        print(f'[FAIL] Runtime error importing {mod_name}: {e}')
        traceback.print_exc()

print('[INFO] Runtime verification complete.')

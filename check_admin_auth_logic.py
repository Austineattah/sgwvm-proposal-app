with open('admin_portal.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print('🔍 Authentication logic in admin_portal.py:')
for idx, line in enumerate(lines, start=1):
    if any(k in line for k in ['password', 'pass_admin', 'ADMIN_PASSWORD', 'st.session_state', 'verify', 'auth']):
        print(f'{idx:3d} | {line.rstrip()}')

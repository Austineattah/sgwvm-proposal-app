with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print('--- app.py Router Dispatch Section (Lines 111 onwards) ---')
for i, line in enumerate(lines[110:], start=111):
    if any(k in line for k in ['portal_mode', 'developer_portal', 'admin', 'solicited', 'render', 'client']):
        print(f'{i}: {line.rstrip()}')

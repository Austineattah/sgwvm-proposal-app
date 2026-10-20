with open('admin_portal.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print('=== admin_portal.py lines 1-80 ===')
for idx, line in enumerate(lines[:80], start=1):
    print(f'{idx:3d} | {line}', end='')

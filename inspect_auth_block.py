with open('admin_portal.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print('=== admin_portal.py lines 80-115 ===')
for idx, line in enumerate(lines[79:115], start=80):
    print(f'{idx:3d} | {line}', end='')

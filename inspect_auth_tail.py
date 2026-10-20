with open('admin_portal.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print('=== admin_portal.py lines 81-125 ===')
for idx, line in enumerate(lines[80:125], start=81):
    print(f'{idx:3d} | {line}', end='')

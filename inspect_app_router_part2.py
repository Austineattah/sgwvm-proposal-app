with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print('=== app.py (Lines 101 to 200) ===')
for idx, line in enumerate(lines[100:200], start=101):
    print(f'{idx:3d} | {line}', end='')

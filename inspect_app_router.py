with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print('=== app.py (First 100 lines) ===')
for idx, line in enumerate(lines[:100], start=1):
    print(f'{idx:3d} | {line}', end='')

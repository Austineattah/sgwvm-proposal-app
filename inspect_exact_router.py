with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print('=== EXACT LINES 120-160 OF app.py ===')
for idx, line in enumerate(lines[119:160], start=120):
    print(f'{idx:3d} | {line}', end='')

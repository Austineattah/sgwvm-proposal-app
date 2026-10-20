with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print('--- app.py Router Section (Lines 30 to 110) ---')
for i, line in enumerate(lines[29:110], start=30):
    print(f'{i}: {line.rstrip()}')

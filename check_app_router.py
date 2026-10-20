with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

print("🔍 Inspecting query parameter handling in app.py:\n")
for i, line in enumerate(lines[:80]):
    if any(k in line for k in ["query_params", "client", "admin", "view", "mode"]):
        print(f"Line {i+1}: {line.strip()}")

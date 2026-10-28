import os
import ast

imported_modules = set()
for root, dirs, files in os.walk("."):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    node = ast.parse(f.read(), filename=path)
                    for subnode in ast.walk(node):
                        if isinstance(subnode, ast.Import):
                            for alias in subnode.names:
                                imported_modules.add(alias.name.split(".")[0])
                        elif isinstance(subnode, ast.ImportFrom):
                            if subnode.module:
                                imported_modules.add(subnode.module.split(".")[0])
            except Exception:
                pass

stdlib = {'os', 'sys', 'ast', 're', 'math', 'json', 'datetime', 'time', 'collections', 
          'pathlib', 'logging', 'typing', 'hashlib', 'base64', 'io', 'urllib', 'http', 
          'smtplib', 'email', 'subprocess', 'shutil', 'tempfile', 'unittest', 'copy', 
          'contextlib', 'functools', 'itertools', 'operator', 'string', 'sqlite3', 'dataclasses'}

import_map = {'cv2': 'opencv-python', 'PIL': 'pillow', 'fitz': 'pymupdf'}

existing_reqs = set()
if os.path.exists("requirements.txt"):
    with open("requirements.txt", "r", encoding="utf-8") as f:
        for line in f:
            cleaned = line.strip().split("#")[0].split("==")[0].split(">=")[0].strip().lower()
            if cleaned:
                existing_reqs.add(cleaned)

missing = []
for mod in sorted(imported_modules):
    if mod in stdlib:
        continue
    pkg = import_map.get(mod, mod).lower()
    if pkg not in existing_reqs:
        missing.append(pkg)

print("=== REQUIREMENTS AUDIT ===")
if missing:
    print(f"[WARNING] These imported modules are missing from requirements.txt: {missing}")
else:
    print("[SUCCESS] Every single imported module in your project is present in requirements.txt!")

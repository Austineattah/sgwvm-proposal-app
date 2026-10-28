import os
import ast
import re

# 1. Find all imported modules across all .py files
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
            except Exception as e:
                pass

# 2. Read existing requirements.txt
existing_reqs = set()
if os.path.exists("requirements.txt"):
    with open("requirements.txt", "r", encoding="utf-8") as f:
        for line in f:
            cleaned = line.strip().split("#")[0].split("==")[0].split(">=")[0].strip().lower()
            if cleaned:
                existing_reqs.add(cleaned)

# 3. Standard library modules to ignore
stdlib_modules = {
    'os', 'sys', 'ast', 're', 'math', 'json', 'datetime', 'time', 'collections', 
    'pathlib', 'logging', 'typing', 'hashlib', 'base64', 'io', 'urllib', 'http', 
    'smtplib', 'email', 'subprocess', 'shutil', 'tempfile', 'unittest', 'copy', 
    'contextlib', 'functools', 'itertools', 'operator', 'string', 'sqlite3', 'dataclasses'
}

# 4. Map import names to pip package names where they differ
import_to_pip = {
    'cv2': 'opencv-python',
    'PIL': 'pillow',
    'fitz': 'pymupdf',
    'pydantic': 'pydantic',
    'streamlit': 'streamlit'
}

missing_packages = []
for mod in sorted(imported_modules):
    if mod in stdlib_modules:
        continue
    pip_name = import_to_pip.get(mod, mod).lower()
    if pip_name not in existing_reqs:
        missing_packages.append(pip_name)

print("=== COMPREHENSIVE DEPENDENCY SCAN ===")
if missing_packages:
    print(f"Found {len(missing_packages)} missing packages to append:")
    for pkg in missing_packages:
        print(f" + {pkg}")
    
    # Automatically append missing packages to requirements.txt
    with open("requirements.txt", "a", encoding="utf-8") as f:
        f.write("\n" + "\n".join(missing_packages) + "\n")
    print("\n[SUCCESS] All missing packages automatically appended to requirements.txt!")
else:
    print("[SUCCESS] requirements.txt is already fully comprehensive! No missing imports found.")

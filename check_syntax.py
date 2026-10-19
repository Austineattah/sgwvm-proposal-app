import py_compile
import glob

files = glob.glob("*.py")
print(f"Inspecting {len(files)} Python files for syntax integrity...\n")

has_error = False
for file in files:
    try:
        py_compile.compile(file, doraise=True)
        print(f"[OK] {file}: Clean syntax.")
    except Exception as e:
        print(f"[ERROR] {file}: Syntax error detected -> {e}")
        has_error = True

if not has_error:
    print("\n[SUCCESS] ALL SYSTEMS GO! Every module passed syntax inspection with 100% integrity.")

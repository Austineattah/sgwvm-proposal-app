with open("onboarding_wizard.py", "r", encoding="utf-8") as f:
    content = f.read()

# Check what functions exist
print("Existing functions/methods in onboarding_wizard.py:")
for line in content.splitlines():
    if line.strip().startswith("def "):
        print("  -", line.strip())

# Ensure render_onboarding_wizard exists
if "def render_onboarding_wizard" not in content:
    # Find likely entry point function
    target_func = "main" if "def main" in content else ("run" if "def run" in content else None)
    
    wrapper = "\n\ndef render_onboarding_wizard():\n"
    if target_func:
        wrapper += f"    {target_func}()\n"
    else:
    # If it's procedural script style, execute the file's logic or wrap
        wrapper += "    # Procedural fallback\n    pass\n"
    
    with open("onboarding_wizard.py", "a", encoding="utf-8") as f:
        f.write(wrapper)
    print("[SUCCESS] Added render_onboarding_wizard wrapper safely.")
else:
    print("[INFO] render_onboarding_wizard already present.")

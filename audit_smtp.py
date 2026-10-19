import os
import toml

print("="*60)
print("🔍 SYSTEM SMTP CONFIGURATION AUDIT")
print("="*60)

# 1. Check Local .env File
env_exists = os.path.exists(".env")
print(f"1. Local .env file exists: {env_exists}")
if env_exists:
    with open(".env", "r", encoding="utf-8", errors="ignore") as f:
        env_lines = [line.strip() for line in f.readlines() if "SMTP" in line or "MAIL" in line or "EMAIL" in line]
    print(f"   - SMTP Keys in .env: {env_lines if env_lines else 'None found'}")

# 2. Check .streamlit/secrets.toml
secrets_path = os.path.join(".streamlit", "secrets.toml")
secrets_exists = os.path.exists(secrets_path)
print(f"\n2. Local .streamlit/secrets.toml exists: {secrets_exists}")
if secrets_exists:
    try:
        secrets = toml.load(secrets_path)
        smtp_sec = secrets.get("smtp", secrets.get("email", {}))
        print("   - Secrets keys detected:")
        for k, v in secrets.items():
            if isinstance(v, dict):
                print(f"     [{k}] -> {list(v.keys())}")
            else:
                print(f"     {k} = {'*****' if 'pass' in k.lower() or 'secret' in k.lower() else v}")
    except Exception as e:
        print(f"   - Error reading secrets.toml: {e}")

# 3. Test SMTP Helper Module (test_smtp.py / email_notifier.py / dispatcher.py)
print("\n3. Testing email notification modules:")
for mod in ["test_smtp.py", "email_notifier.py", "notifier.py", "dispatcher.py"]:
    if os.path.exists(mod):
        print(f"   - Found module: {mod}")

print("="*60)

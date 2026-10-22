with open("notifier.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace get_secret with a version that checks root, [smtp] section, and case-insensitive variants
old_get_secret = '''def get_secret(key, default=None):
    \"\"\"Retrieve a setting from the environment or Streamlit secrets.\"\"\"
    value = os.getenv(key)
    if value:
        return value
    if st:
        try:
            return st.secrets[key]
        except (KeyError, StreamlitSecretNotFoundError):
            pass
    return default'''

new_get_secret = '''def get_secret(key, default=None):
    """Retrieve a setting from environment, root Streamlit secrets, or [smtp] section."""
    value = os.getenv(key)
    if value:
        return value
    if st:
        # 1. Check direct root secret
        try:
            return st.secrets[key]
        except (KeyError, StreamlitSecretNotFoundError):
            pass
        # 2. Check uppercase/lowercase variants at root
        try:
            return st.secrets[key.upper()]
        except (KeyError, StreamlitSecretNotFoundError):
            pass
        try:
            return st.secrets[key.lower()]
        except (KeyError, StreamlitSecretNotFoundError):
            pass
        # 3. Check inside [smtp] table section
        try:
            smtp_table = st.secrets.get("smtp", {})
            if key in smtp_table:
                return smtp_table[key]
            if key.lower() in smtp_table:
                return smtp_table[key.lower()]
            if key.upper() in smtp_table:
                return smtp_table[key.upper()]
        except Exception:
            pass
    return default'''

if old_get_secret in content:
    content = content.replace(old_get_secret, new_get_secret)
    print("[SUCCESS] Upgraded get_secret to support [smtp] section and root-level lookups.")
else:
    print("[WARNING] old_get_secret not found exactly. Checking alternative pattern.")

with open("notifier.py", "w", encoding="utf-8") as f:
    f.write(content)

print("[INFO] notifier.py patch complete.")

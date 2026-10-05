import os
import re
import psycopg2
import streamlit as st

# Path to secrets file
secrets_path = ".streamlit/secrets.toml"

print("--- [1] CHECKING SECRETS FILE ---")
if os.path.exists(secrets_path):
    with open(secrets_path, "r", encoding="utf-8") as f:
        print("Current secrets content:")
        print(f.read())
else:
    print("secrets.toml does not exist!")

# Prompt user for PostgreSQL connection details
print("\n--- [2] ENTER DATABASE CREDENTIALS ---")
db_user = input("Enter your PostgreSQL app username (e.g., postgres or sgwvm_user): ").strip()
db_pass = input("Enter password for this DB user: ").strip()
db_host = input("Enter host [default: localhost]: ").strip() or "localhost"
db_port = input("Enter port [default: 5432]: ").strip() or "5432"
db_name = input("Enter database name (e.g., sgwvm_proposal_db): ").strip()

db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

# Existing admin hash or prompt
admin_hash = "$2b$12$R1m9ilk7bFnaozK5mJPiAepeBQbMYxu0fsutWKlx1RsdpwmDNPO.."

# Read existing secrets if ADMIN_PASSWORD_HASH is present
try:
    if "ADMIN_PASSWORD_HASH" in st.secrets:
        admin_hash = st.secrets["ADMIN_PASSWORD_HASH"]
except Exception:
    pass

# Rewrite secrets.toml cleanly with both keys
secrets_content = f'''ADMIN_PASSWORD_HASH = "{admin_hash}"
DATABASE_URL = "{db_url}"
'''

with open(secrets_path, "w", encoding="utf-8") as f:
    f.write(secrets_content)

print("\nSUCCESS: Saved ADMIN_PASSWORD_HASH and DATABASE_URL to .streamlit/secrets.toml.")

# Attempt schema privilege grant on PostgreSQL
print("\n--- [3] GRANTING SCHEMA PUBLIC PERMISSIONS ---")
super_user = input("Enter PostgreSQL superuser (usually 'postgres'): ").strip() or "postgres"
super_pass = input(f"Enter password for superuser '{super_user}': ").strip()

try:
    conn = psycopg2.connect(
        dbname=db_name,
        user=super_user,
        password=super_pass,
        host=db_host,
        port=db_port
    )
    conn.autocommit = True
    cursor = conn.cursor()

    cursor.execute(f'GRANT ALL ON SCHEMA public TO "{db_user}";')
    cursor.execute(f'ALTER SCHEMA public OWNER TO "{db_user}";')
    cursor.execute(f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "{db_user}";')
    cursor.execute(f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "{db_user}";')

    print("SUCCESS: Permissions updated on schema 'public'.")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"ERROR: Could not update permissions automatically: {e}")
    print("If you are using the default 'postgres' user as your DB user, permissions are already sufficient.")

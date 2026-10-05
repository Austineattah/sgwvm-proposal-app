import os
import psycopg2
from urllib.parse import urlparse
import streamlit as st

# 1. Fetch DB URL from Streamlit Secrets
db_url = st.secrets.get("DATABASE_URL", "")

if not db_url:
    print("❌ DATABASE_URL not found in .streamlit/secrets.toml")
    exit(1)

parsed = urlparse(db_url)
db_user = parsed.username
db_name = parsed.path.lstrip('/')
db_host = parsed.hostname or 'localhost'
db_port = parsed.port or 5432

print(f"Target Database: {db_name}")
print(f"Target App User: {db_user}")

# 2. Get postgres superuser password
pg_superpass = input("\nEnter password for PostgreSQL superuser 'postgres': ").strip()

try:
    conn = psycopg2.connect(
        dbname=db_name,
        user="postgres",
        password=pg_superpass,
        host=db_host,
        port=db_port
    )
    conn.autocommit = True
    cursor = conn.cursor()

    # Grant necessary permissions
    cursor.execute(f"GRANT ALL ON SCHEMA public TO \"{db_user}\";")
    cursor.execute(f"ALTER SCHEMA public OWNER TO \"{db_user}\";")
    cursor.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO \"{db_user}\";")
    cursor.execute(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO \"{db_user}\";")

    print(f"\n✅ Permissions granted! '{db_user}' is now the owner of schema 'public'.")
    cursor.close()
    conn.close()

except Exception as e:
    print(f"\n❌ Failed to update permissions: {e}")

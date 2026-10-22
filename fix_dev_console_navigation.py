import sqlite3
import os

PRODUCTION_BASE_URL = "https://NexusVault-Proposal-Enterprise-Connect.streamlit.app"

db_path = "nexusvault.db"
if not os.path.exists(db_path):
    for f in os.listdir("."):
        if f.endswith(".db"):
            db_path = f
            break

print(f"[+] Target DB: {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Keep only the latest active 'SKINCARE' tenant, delete the rest
cursor.execute("SELECT id, client_slug, corp_name, status FROM clients WHERE corp_name LIKE '%SKINCARE%';")
skincare_rows = cursor.fetchall()
print(f"[+] Found {len(skincare_rows)} Skincare records.")

if len(skincare_rows) > 1:
    # Keep the last one, delete the rest
    keep_id = skincare_rows[-1][0]
    keep_slug = skincare_rows[-1][1]
    print(f"[+] Preserving latest Skincare node: {keep_slug} (ID: {keep_id})")
    
    cursor.execute("DELETE FROM clients WHERE corp_name LIKE '%SKINCARE%' AND id != ?;", (keep_id,))
    conn.commit()
    print(f"[-] Purged redundant Skincare duplicate records.")

conn.close()
print("[SUCCESS] Database cleanup complete.")

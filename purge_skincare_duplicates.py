import sqlite3

PRODUCTION_BASE_URL = "https://NexusVault-Proposal-Enterprise-Connect.streamlit.app"

conn = sqlite3.connect('nexusvault_sovereign.db')
cursor = conn.cursor()

cursor.execute("SELECT client_id, client_slug, corp_name, is_approved FROM clients WHERE corp_name LIKE '%SKINCARE%';")
rows = cursor.fetchall()
print(f"[+] Found {len(rows)} SKINCARE record(s) in local database.")

if len(rows) > 1:
    keep_id = rows[-1][0]  # Preserve the latest registered entry
    print(f"[+] Preserving active client_id: {keep_id} ({rows[-1][1]})")
    cursor.execute("DELETE FROM clients WHERE corp_name LIKE '%SKINCARE%' AND client_id != ?;", (keep_id,))
    conn.commit()
    print(f"[SUCCESS] Purged duplicate records. Retained active tenant record: {keep_id}")
else:
    print("[INFO] Local SKINCARE records are already clean.")

conn.close()

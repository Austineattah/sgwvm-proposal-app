import database as db
import sqlite3
import os

db.init_db()

# Check database file path configured in database.py
db_file = getattr(db, 'DB_FILE', 'database.db')
if not os.path.exists(db_file):
    for f in os.listdir('.'):
        if f.endswith('.db'):
            db_file = f
            break

print(f"[+] Application Database File: {db_file}")

conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# Find all table names in the active database
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]
print(f"[+] Detected Tables: {tables}")

# Locate client table (checking common table names: clients, client_tenants, subscriptions)
client_table = None
for t in ['clients', 'client_tenants', 'subscriptions', 'tenants']:
    if t in tables:
        client_table = t
        break

if client_table:
    print(f"[+] Deduplicating entries in table: '{client_table}'")
    cursor.execute(f"SELECT rowid, * FROM {client_table};")
    records = cursor.fetchall()
    print(f"[+] Total tenant records currently stored: {len(records)}")
    
    # Keep the single latest record for SKINCARE and remove duplicates
    cursor.execute(f"SELECT rowid FROM {client_table} WHERE corp_name LIKE '%SKINCARE%';")
    skincare_ids = [r[0] for r in cursor.fetchall()]
    
    if len(skincare_ids) > 1:
        keep_id = skincare_ids[-1] # preserve the most recent
        delete_ids = skincare_ids[:-1]
        for d_id in delete_ids:
            cursor.execute(f"DELETE FROM {client_table} WHERE rowid = ?;", (d_id,))
        conn.commit()
        print(f"[SUCCESS] Successfully purged {len(delete_ids)} duplicate SKINCARE records. Preserved row ID: {keep_id}")
    else:
        print("[INFO] No duplicate SKINCARE records found in local table.")
else:
    print("[!] No tenant table found in this database file.")

conn.close()

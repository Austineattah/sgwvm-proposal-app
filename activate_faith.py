import sqlite3
import os

PRODUCTION_BASE_URL = "https://NexusVault-Proposal-Enterprise-Connect.streamlit.app"

db_files = [f for f in os.listdir(".") if f.endswith(".db")]
print("Detected DB files:", db_files)

for db_file in db_files:
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cursor.fetchall()]
        print(f"Tables in {db_file}:", tables)
        
        for tname in ["clients", "tenants", "organizations"]:
            if tname in tables:
                cursor.execute(f"SELECT * FROM {tname}")
                rows = cursor.fetchall()
                print(f"Rows in {tname}:", rows)
                
                # Update status
                cursor.execute(f"UPDATE {tname} SET is_approved = 1 WHERE slug = ? OR corp_name LIKE ?", ("faith-academy", "%Faith Academy%"))
                conn.commit()
                print(f"[+] Successfully activated Faith Academy in table '{tname}' of {db_file}!")
    except Exception as e:
        print(f"Note on {db_file}: {e}")
    finally:
        conn.close()

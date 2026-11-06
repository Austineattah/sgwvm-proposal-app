import sqlite3
import os
import database as db

db_path = db.DB_FILE
print("--- DATABASE DIAGNOSTIC REPORT ---")
print(f"Absolute Path: {os.path.abspath(db_path)}")
print(f"File Exists: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    print(f"File Size: {os.path.getsize(db_path)} bytes")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Tables Found: {tables}")

    if "tenants" in tables:
        cursor.execute("SELECT COUNT(*) FROM tenants;")
        count = cursor.fetchone()[0]
        print(f"Total Tenants Recorded: {count}")

        cursor.execute(
            "SELECT tenant_slug, full_corporation_name, institution_category FROM tenants;"
        )
        for row in cursor.fetchall():
            print(f"  - Slug: {row[0]} | Name: {row[1]} | Category: {row[2]}")
    else:
        print('WARNING: "tenants" table does not exist in this database file!')

    conn.close()
else:
    print(f"CRITICAL: {db_path} was not found.")

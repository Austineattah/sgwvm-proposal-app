import sqlite3
import database as db

db.init_db()
conn = db.get_connection()
cursor = conn.cursor()

# Remove test client slugs
test_slugs = ['faithacademy_7a184bb5', 'faithacademy']
for slug in test_slugs:
    cursor.execute("DELETE FROM clients WHERE client_slug = ?", (slug,))
    print(f"[-] Purged client node: {slug}")

conn.commit()
conn.close()
print("[SUCCESS] Test tenant nodes wiped clean. Ready for a fresh demo onboarding!")

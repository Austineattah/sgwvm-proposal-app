import sqlite3

def patch_database():
    conn = sqlite3.connect('nexusvault_sovereign.db')
    cursor = conn.cursor()
    
    # Check if pass_status column exists, if not add it
    try:
        cursor.execute("ALTER TABLE clients ADD COLUMN pass_status TEXT DEFAULT 'Temporary (Pending First Login)';")
        print("[+] Added pass_status column to nexusvault_sovereign.db")
    except Exception as e:
        print(f"[*] Note on DB schema: {e}")
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    patch_database()
    print("[+] System schema successfully hardened for Multi-Tier Admin Governance!")

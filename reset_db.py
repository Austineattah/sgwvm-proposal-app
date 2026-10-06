import sqlite3

def reset_security_logs():
    try:
        conn = sqlite3.connect('security_logs.db')
        c = conn.cursor()
        tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        for table in tables:
            c.execute(f"DELETE FROM {table[0]}")
        conn.commit()
        conn.close()
        print("🔓 Security logs cleared successfully!")
    except Exception as e:
        print(f"Error resetting database: {e}")

if __name__ == "__main__":
    reset_security_logs()

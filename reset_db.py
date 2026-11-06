import sqlite3
import database as db


def reset_security_logs():
    try:
        with sqlite3.connect(db.DB_FILE) as conn:
            conn.execute("DELETE FROM admin_security_access_logs")
            conn.execute("DELETE FROM reset_tokens")
        print(" Security logs cleared successfully!")
    except Exception as e:
        print(f"Error resetting database: {e}")


if __name__ == "__main__":
    reset_security_logs()

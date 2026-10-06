import sqlite3
import time
from pathlib import Path
import streamlit as st

DB_PATH = Path(__file__).resolve().parent / "security_logs.db"


def init_security_db():
    """Initializes the SQLite database table for access logs."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                status TEXT,
                attempt_number INTEGER
            )
        """
        )
        conn.commit()


def get_client_ip() -> str:
    """Extracts client IP address from Streamlit context headers."""
    try:
        headers = st.context.headers
        forwarded_for = headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return headers.get("Host", "127.0.0.1").split(":")[0]
    except Exception:
        return "127.0.0.1"


def log_access_attempt(status: str, attempt_number: int):
    """Logs an access attempt into SQLite database."""
    init_security_db()
    ip_addr = get_client_ip()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO admin_access_logs (ip_address, status, attempt_number)
            VALUES (?, ?, ?)
        """,
            (ip_addr, status, attempt_number),
        )
        conn.commit()

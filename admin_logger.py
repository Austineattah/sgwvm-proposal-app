import hashlib
import os
import sqlite3
import time
from pathlib import Path
import streamlit as st

DB_PATH = Path(__file__).resolve().parent / "security_logs.db"


def init_security_db():
    """Initializes SQLite database tables for access logs and reset tokens."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Access logs table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER,
                ip_address TEXT,
                status TEXT
            )
        """
        )
        # Reset tokens table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                token TEXT,
                created_at INTEGER,
                used INTEGER DEFAULT 0
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


def log_access_attempt(status: str):
    """Logs an access attempt with Unix timestamp into SQLite."""
    init_security_db()
    ip_addr = get_client_ip()
    current_time = int(time.time())
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO admin_access_logs (timestamp, ip_address, status)
            VALUES (?, ?, ?)
        """,
            (current_time, ip_addr, status),
        )
        conn.commit()


def check_ip_lockout(window_seconds: int = 60, max_attempts: int = 3):
    """Checks SQLite database to see if current IP has exceeded failed attempts within window."""
    init_security_db()
    ip_addr = get_client_ip()
    cutoff = int(time.time()) - window_seconds

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) FROM admin_access_logs
            WHERE ip_address = ? AND status LIKE 'FAILED%' AND timestamp >= ?
        """,
            (ip_addr, cutoff),
        )
        failed_count = cursor.fetchone()[0]

    return failed_count >= max_attempts, failed_count


def generate_reset_token(email: str) -> str:
    """Generates a secure 6-digit reset code and saves it to SQLite."""
    init_security_db()
    code = f"{int.from_bytes(os.urandom(4), 'big') % 900000 + 100000}"
    current_time = int(time.time())

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO reset_tokens (email, token, created_at)
            VALUES (?, ?, ?)
        """,
            (email, code, current_time),
        )
        conn.commit()
    return code


def verify_reset_token(email: str, code: str, validity_seconds: int = 600) -> bool:
    """Verifies if the reset token is valid and not expired (10 min validity)."""
    init_security_db()
    cutoff = int(time.time()) - validity_seconds

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id FROM reset_tokens
            WHERE email = ? AND token = ? AND created_at >= ? AND used = 0
        """,
            (email.strip().lower(), code.strip(), cutoff),
        )
        row = cursor.fetchone()
        if row:
            token_id = row[0]
            cursor.execute("UPDATE reset_tokens SET used = 1 WHERE id = ?", (token_id,))
            conn.commit()
            return True
    return False
import sqlite3
import json
import os
from datetime import datetime, timedelta

PRODUCTION_BASE_URL = "https://NexusVault-Proposal-Enterprise-Connect.streamlit.app"

DB_FILE = "nexusvault_sovereign.db"

def init_db():
    """Initializes SQLite tables and automatically performs schema migrations for missing columns."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Proposals Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            proposal_type TEXT,
            vendor_name TEXT,
            cac_number TEXT,
            vendor_email TEXT,
            vendor_phone TEXT,
            address TEXT,
            project_title TEXT,
            target_officer TEXT,
            priority_level TEXT,
            qr_ref_id TEXT UNIQUE,
            status TEXT,
            kyb_status TEXT,
            compliance_score REAL,
            estimated_cost TEXT,
            ai_summary TEXT,
            payment_ref TEXT
        )
    ''')

    # Audit Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            user_role TEXT,
            action TEXT,
            qr_ref_id TEXT,
            details TEXT
        )
    ''')

    # System Settings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # Multi-Tenant Client Registry Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            client_id TEXT PRIMARY KEY,
            client_slug TEXT UNIQUE,
            corp_name TEXT,
            entity_type TEXT,
            corp_email TEXT,
            corp_phone TEXT,
            corp_address TEXT,
            admin_email TEXT,
            sub_package TEXT,
            custom_title TEXT,
            is_approved TEXT
        )
    ''')

    # Safe Schema Migrations for existing DB files
    columns_to_add = [
        ("lockout_status", "TEXT DEFAULT 'False'"),
        ("client_admin_pass", "TEXT DEFAULT 'NexusExec2026!'"),
        ("created_at", "TEXT"),
        ("is_purged", "TEXT DEFAULT 'False'")
    ]

    for col_name, col_def in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE clients ADD COLUMN {col_name} {col_def}")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()

def save_proposal(data):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO proposals 
        (timestamp, proposal_type, vendor_name, cac_number, vendor_email, vendor_phone, address, project_title, target_officer, priority_level, qr_ref_id, status, kyb_status, compliance_score, estimated_cost, ai_summary, payment_ref)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data["timestamp"], data["type"], data["vendor"], data["cac"], data["email"], 
        data["phone"], data["address"], data["title"], data["target_officer"], 
        data["priority"], data["qr_ref"], data["status"], data["kyb_status"], 
        data["score"], data["estimated_cost"], data["ai_summary"], data.get("payment_ref", "N/A")
    ))
    conn.commit()
    conn.close()

def fetch_all_proposals():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM proposals ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_proposal_status(qr_ref, new_status, role):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE proposals SET status = ? WHERE qr_ref_id = ?", (new_status, qr_ref))
    conn.commit()
    conn.close()

def set_setting(key, value):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_setting(key, default=""):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def register_client(data):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT OR IGNORE INTO clients 
        (client_id, client_slug, corp_name, entity_type, corp_email, corp_phone, corp_address, admin_email, sub_package, custom_title, is_approved, lockout_status, client_admin_pass, created_at, is_purged)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'False', 'NexusExec2026!', ?, 'False')
    ''', (
        data["client_id"], data["client_slug"], data["corp_name"], data["entity_type"],
        data["corp_email"], data["corp_phone"], data["corp_address"], data["admin_email"],
        data["sub_package"], data["custom_title"], data["is_approved"], current_time
    ))
    conn.commit()
    conn.close()

def get_client(client_slug):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE client_slug = ? AND (is_purged != 'True' OR is_purged IS NULL)", (client_slug,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_clients():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE is_purged != 'True' OR is_purged IS NULL")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_purged_clients():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE is_purged = 'True'")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_client_approval(client_id, status):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE clients SET is_approved = ? WHERE client_id = ?", (str(status), client_id))
    conn.commit()
    conn.close()

def update_client_lockout(client_id, lockout_status):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE clients SET lockout_status = ? WHERE client_id = ?", (str(lockout_status), client_id))
    conn.commit()
    conn.close()

def reset_client_password(client_id, new_pass):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE clients SET client_admin_pass = ?, lockout_status = 'False' WHERE client_id = ?", (new_pass, client_id))
    conn.commit()
    conn.close()

def purge_client(client_id):
    """Soft-deletes a client by moving them to the purge archive."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE clients SET is_purged = 'True' WHERE client_id = ?", (client_id,))
    conn.commit()
    conn.close()

def restore_client(client_id):
    """Restores a client from the purge archive back to active status."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE clients SET is_purged = 'False' WHERE client_id = ?", (client_id,))
    conn.commit()
    conn.close()

def delete_client_permanently(client_id):
    """Permanently deletes a client record from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clients WHERE client_id = ?", (client_id,))
    conn.commit()
    conn.close()

def purge_expired_pending_clients():
    """Soft-purges client records that have remained in 'Pending' for more than 7 days."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    threshold_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("SELECT client_id FROM clients WHERE is_approved = 'False' AND (is_purged != 'True' OR is_purged IS NULL) AND created_at < ?", (threshold_date,))
    expired_clients = cursor.fetchall()
    if expired_clients:
        for ec in expired_clients:
            cursor.execute("UPDATE clients SET is_purged = 'True' WHERE client_id = ?", (ec[0],))
        conn.commit()
    conn.close()
    return len(expired_clients)

init_db()

def get_connection():
    """Fallback SQLite connection helper."""
    import sqlite3
    return sqlite3.connect("nexusvault.db", check_same_thread=False)

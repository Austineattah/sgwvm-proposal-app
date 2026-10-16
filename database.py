import sqlite3
import os
from datetime import datetime

DB_FILE = "nexusvault.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            proposal_type TEXT NOT NULL,
            vendor_name TEXT NOT NULL,
            cac_number TEXT NOT NULL,
            vendor_email TEXT NOT NULL,
            vendor_phone TEXT NOT NULL,
            vendor_address TEXT,
            project_title TEXT NOT NULL,
            target_officer TEXT,
            priority_level TEXT DEFAULT 'Standard Review',
            qr_ref_id TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'Routed & Pending Review',
            kyb_status TEXT DEFAULT 'Verified Active (CAC Registry)',
            compliance_score REAL DEFAULT 95.0,
            estimated_cost TEXT,
            ai_summary TEXT,
            payment_ref TEXT DEFAULT 'N/A'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_role TEXT NOT NULL,
            action TEXT NOT NULL,
            qr_ref_id TEXT,
            details TEXT
        )
    ''')

    conn.commit()
    conn.close()

def save_proposal(proposal_data):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO proposals (
            timestamp, proposal_type, vendor_name, cac_number, vendor_email, 
            vendor_phone, vendor_address, project_title, target_officer, 
            priority_level, qr_ref_id, status, kyb_status, compliance_score, 
            estimated_cost, ai_summary, payment_ref
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        proposal_data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        proposal_data.get("type", "Unsolicited (Physical Intake)"),
        proposal_data.get("vendor"),
        proposal_data.get("cac"),
        proposal_data.get("email"),
        proposal_data.get("phone"),
        proposal_data.get("address"),
        proposal_data.get("title"),
        proposal_data.get("target_officer"),
        proposal_data.get("priority", "Standard Review"),
        proposal_data.get("qr_ref"),
        proposal_data.get("status", "Routed & Pending Review"),
        proposal_data.get("kyb_status", "Verified Active (CAC Registry)"),
        proposal_data.get("score", 95.5),
        proposal_data.get("estimated_cost", "₦45,500,000"),
        proposal_data.get("ai_summary", "Automated compliance audit complete. Recommended for executive review."),
        proposal_data.get("payment_ref", "N/A")
    ))
    
    conn.commit()
    conn.close()
    
    log_event("System", "PROPOSAL_SAVED", proposal_data.get("qr_ref"), f"Proposal record saved for {proposal_data.get('vendor')}")

def set_setting(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)', (key, str(value)))
    conn.commit()
    conn.close()

def get_setting(key, default_value=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM system_settings WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default_value

def fetch_all_proposals():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM proposals ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_proposal_status(qr_ref_id, new_status, updated_by_role="Strategic Directorate"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE proposals SET status = ? WHERE qr_ref_id = ?', (new_status, qr_ref_id))
    conn.commit()
    conn.close()
    log_event(updated_by_role, "STATUS_UPDATE", qr_ref_id, f"Status updated to '{new_status}'")

def log_event(role, action, qr_ref_id, details):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO audit_logs (timestamp, user_role, action, qr_ref_id, details)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        role,
        action,
        qr_ref_id,
        details
    ))
    conn.commit()
    conn.close()

def fetch_audit_logs():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM audit_logs ORDER BY id DESC LIMIT 50')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

init_db()
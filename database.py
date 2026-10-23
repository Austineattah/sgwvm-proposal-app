import sqlite3
import os
import json

DB_PATH = "proposals.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create proposals table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS proposals (
            client_slug TEXT PRIMARY KEY,
            client_name TEXT,
            sector TEXT,
            status TEXT,
            proposal_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Self-healing schema check
    cursor.execute("PRAGMA table_info(proposals)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'client_slug' not in columns:
        cursor.execute("DROP TABLE proposals")
        cursor.execute("""
            CREATE TABLE proposals (
                client_slug TEXT PRIMARY KEY,
                client_name TEXT,
                sector TEXT,
                status TEXT,
                proposal_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    # Create audit logs and system settings tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_slug TEXT,
            action TEXT,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # Auto-seed default active tenant if missing
    cursor.execute("SELECT client_slug FROM proposals WHERE client_slug = ?", ('skincarenigltd_ad1aab57',))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO proposals (client_slug, client_name, sector, status, proposal_data)
            VALUES (?, ?, ?, ?, ?)
        """, ('skincarenigltd_ad1aab57', 'SKINCARENIG LTD', 'Enterprise Commercial Node', 'Active', json.dumps({'email': 'austattah@gmail.com'})))

    conn.commit()
    conn.close()

def get_tenant_by_slug(slug):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT client_slug, client_name, sector, status, proposal_data FROM proposals WHERE client_slug = ?", (slug,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "client_slug": row[0],
            "client_name": row[1],
            "sector": row[2],
            "status": row[3],
            "proposal_data": json.loads(row[4]) if row[4] else {}
        }
    return None

def register_client(slug, name, sector, status, data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO proposals (client_slug, client_name, sector, status, proposal_data) VALUES (?, ?, ?, ?, ?)", (slug, name, sector, status, json.dumps(data)))
    conn.commit()
    conn.close()

def save_tenant(slug, data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE proposals SET proposal_data = ? WHERE client_slug = ?", (json.dumps(data), slug))
    conn.commit()
    conn.close()

def update_tenant(slug, name, sector, status, data):
    register_client(slug, name, sector, status, data)

def save_proposal(slug, proposal_info):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO audit_logs (client_slug, action, details) VALUES (?, ?, ?)", (slug, "SAVE_PROPOSAL", json.dumps(proposal_info)))
    conn.commit()
    conn.close()

def save_transaction(slug, tx_info):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO audit_logs (client_slug, action, details) VALUES (?, ?, ?)", (slug, "TRANSACTION", json.dumps(tx_info)))
    conn.commit()
    conn.close()

def save_clearance_pass(slug, pass_info):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO audit_logs (client_slug, action, details) VALUES (?, ?, ?)", (slug, "CLEARANCE_PASS", json.dumps(pass_info)))
    conn.commit()
    conn.close()

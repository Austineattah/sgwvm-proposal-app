import sqlite3
import os
import json

DB_PATH = "proposals.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Primary Tenant Table
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
    
    # Self-healing check for proposals table
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

    # 2. Audit Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_slug TEXT,
            action TEXT,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. System Settings Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # 4. Unsolicited Vendor Submissions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendor_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_slug TEXT,
            org_name TEXT,
            vendor_rep_name TEXT,
            email TEXT,
            phone TEXT,
            cac_number TEXT,
            tin_number TEXT,
            document_ref TEXT,
            assigned_directorate TEXT,
            status TEXT DEFAULT 'PENDING_REVIEW',
            acknowledgment_sent INTEGER DEFAULT 1,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

def save_vendor_submission(slug, org_name, rep_name, email, phone, cac, tin, doc_ref, directorate="UNASSIGNED"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO vendor_submissions 
        (client_slug, org_name, vendor_rep_name, email, phone, cac_number, tin_number, document_ref, assigned_directorate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (slug, org_name, rep_name, email, phone, cac, tin, doc_ref, directorate))
    submission_id = cursor.lastrowid
    
    # Log event into audit ledger
    audit_data = json.dumps({"submission_id": submission_id, "org_name": org_name, "cac": cac, "tin": tin})
    cursor.execute("INSERT INTO audit_logs (client_slug, action, details) VALUES (?, ?, ?)", (slug, "VENDOR_SUBMISSION_INTAKE", audit_data))
    
    conn.commit()
    conn.close()
    return submission_id

def get_vendor_submissions(slug, directorate=None):
    conn = get_connection()
    cursor = conn.cursor()
    if directorate:
        cursor.execute("SELECT id, org_name, vendor_rep_name, email, phone, cac_number, tin_number, document_ref, assigned_directorate, status, timestamp FROM vendor_submissions WHERE client_slug = ? AND assigned_directorate = ? ORDER BY id DESC", (slug, directorate))
    else:
        cursor.execute("SELECT id, org_name, vendor_rep_name, email, phone, cac_number, tin_number, document_ref, assigned_directorate, status, timestamp FROM vendor_submissions WHERE client_slug = ? ORDER BY id DESC", (slug,))
    rows = cursor.fetchall()
    conn.close()
    return rows

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


def get_audit_logs(slug=""):
    """Retrieves audit logs for a given tenant slug."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, tenant_slug, action, details, timestamp FROM audit_logs WHERE tenant_slug = ? ORDER BY id DESC", (slug,))
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        # Fallback if table schema varies
        try:
            cursor.execute("SELECT id, tenant_slug, action, details, timestamp FROM audit_logs ORDER BY id DESC")
            return cursor.fetchall()
        except:
            return []
    finally:
        conn.close()


def log_audit_event(slug, action, details):
    """Records an audit event for a given tenant slug."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Check table columns for audit_logs
        cursor.execute("PRAGMA table_info(audit_logs);")
        cols = [c[1] for c in cursor.fetchall()]
        
        if 'client_slug' in cols:
            cursor.execute("INSERT INTO audit_logs (client_slug, action, details) VALUES (?, ?, ?)", (slug, action, details))
        elif 'tenant_slug' in cols:
            cursor.execute("INSERT INTO audit_logs (tenant_slug, action, details) VALUES (?, ?, ?)", (slug, action, details))
        else:
            cursor.execute("INSERT INTO audit_logs (action, details) VALUES (?, ?)", (action, details))
            
        conn.commit()
    except Exception as e:
        print(f"[ERROR] Failed to log audit event: {e}")
    finally:
        conn.close()

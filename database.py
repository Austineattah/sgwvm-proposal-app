import sqlite3
import json
import os
import datetime

DB_FILE = "proposals.db"

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tenants / Clients table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            slug TEXT PRIMARY KEY,
            client_name TEXT NOT NULL,
            sector TEXT NOT NULL,
            status TEXT DEFAULT 'Active',
            proposal_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Vendor Submissions table with Auto-Increment Ref ID
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendor_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_slug TEXT NOT NULL,
            org_name TEXT NOT NULL,
            rep_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            cac_num TEXT NOT NULL,
            tin_num TEXT NOT NULL,
            doc_ref TEXT,
            directorate TEXT NOT NULL,
            status TEXT DEFAULT 'Under Review',
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Audit Logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_slug TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Technical Evaluation Committee (TEC) Evaluations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS committee_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_slug TEXT NOT NULL,
            submission_id INTEGER NOT NULL,
            evaluator_name TEXT NOT NULL,
            evaluator_role TEXT NOT NULL,
            technical_score REAL NOT NULL,
            financial_score REAL NOT NULL,
            verdict TEXT NOT NULL,
            comments TEXT,
            evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Default Tenant Seeding
    cursor.execute("SELECT COUNT(*) FROM clients WHERE slug='skincarenigltd_ad1aab57'")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO clients (slug, client_name, sector, status, proposal_data) VALUES (?, ?, ?, ?, ?)",
            ("skincarenigltd_ad1aab57", "SKINCARENIG LTD", "Enterprise Commercial Node", "Active", json.dumps({"email": "info@skincarenig.com", "phone": "+234 800 123 4567"}))
        )
        
    conn.commit()
    conn.close()

def get_tenant_by_slug(slug):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT slug, client_name, sector, status, proposal_data FROM clients WHERE slug=?", (slug,))
    row = cursor.fetchone()
    conn.close()
    if row:
        pdata = json.loads(row[4]) if row[4] else {}
        return {"slug": row[0], "client_name": row[1], "sector": row[2], "status": row[3], "proposal_data": pdata}
    return None

def register_client(slug, name, sector, status="Active", data=None):
    conn = get_connection()
    cursor = conn.cursor()
    pdata_json = json.dumps(data) if data else json.dumps({})
    cursor.execute(
        "INSERT OR REPLACE INTO clients (slug, client_name, sector, status, proposal_data) VALUES (?, ?, ?, ?, ?)",
        (slug, name, sector, status, pdata_json)
    )
    conn.commit()
    conn.close()

def save_vendor_submission(slug, org_name, rep_name, email, phone, cac, tin, doc_ref, directorate):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO vendor_submissions (tenant_slug, org_name, rep_name, email, phone, cac_num, tin_num, doc_ref, directorate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (slug, org_name, rep_name, email, phone, cac, tin, doc_ref, directorate)
    )
    sub_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return sub_id

def get_vendor_submissions(slug):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, tenant_slug, org_name, rep_name, email, phone, cac_num, tin_num, doc_ref, directorate, status, submitted_at FROM vendor_submissions WHERE tenant_slug=? ORDER BY id DESC", (slug,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def log_audit_event(slug, action, details):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO audit_logs (tenant_slug, action, details) VALUES (?, ?, ?)", (slug, action, details))
    conn.commit()
    conn.close()

def get_audit_logs(slug):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, tenant_slug, action, details, timestamp FROM audit_logs WHERE tenant_slug=? ORDER BY id DESC", (slug,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def save_committee_evaluation(slug, submission_id, evaluator_name, evaluator_role, tech_score, fin_score, verdict, comments):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO committee_evaluations (tenant_slug, submission_id, evaluator_name, evaluator_role, technical_score, financial_score, verdict, comments) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (slug, submission_id, evaluator_name, evaluator_role, tech_score, fin_score, verdict, comments)
    )
    conn.commit()
    conn.close()

def get_committee_evaluations(slug, submission_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if submission_id:
        cursor.execute("SELECT id, submission_id, evaluator_name, evaluator_role, technical_score, financial_score, verdict, comments, evaluated_at FROM committee_evaluations WHERE tenant_slug=? AND submission_id=? ORDER BY id DESC", (slug, submission_id))
    else:
        cursor.execute("SELECT id, submission_id, evaluator_name, evaluator_role, technical_score, financial_score, verdict, comments, evaluated_at FROM committee_evaluations WHERE tenant_slug=? ORDER BY id DESC", (slug,))
    rows = cursor.fetchall()
    conn.close()
    return rows

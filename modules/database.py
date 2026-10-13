import sqlite3
import os
from config import Config

def get_connection():
    os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)
    return sqlite3.connect(Config.DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            rc_number TEXT,
            email TEXT,
            phone TEXT,
            project_title TEXT,
            category TEXT,
            proposal_abstract TEXT,
            file_name TEXT,
            ai_summary TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def insert_proposal(company_name, rc_number, email, phone, project_title, category, proposal_abstract, file_name, ai_summary):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO proposals (company_name, rc_number, email, phone, project_title, category, proposal_abstract, file_name, ai_summary, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
    ''', (company_name, rc_number, email, phone, project_title, category, proposal_abstract, file_name, ai_summary))
    conn.commit()
    proposal_id = cursor.lastrowid
    conn.close()
    return proposal_id

def get_all_proposals():
    init_db()
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM proposals ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_proposal_status(proposal_id, new_status):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE proposals SET status = ? WHERE id = ?', (new_status, proposal_id))
    conn.commit()
    conn.close()


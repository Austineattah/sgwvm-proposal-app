import sqlite3
import os

DB_FILE = "nexus_sovereign.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Tenants table with full enterprise taxonomy & branding
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            tenant_slug TEXT PRIMARY KEY,
            full_corporation_name TEXT,
            institution_category TEXT,
            apex_title TEXT,
            sub_directorates_json TEXT,
            logo_path TEXT,
            status TEXT
        )
    """)
    
    # Security audit & access logs table (resolves 'no such table: admin_access_logs')
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_slug TEXT,
            action TEXT,
            actor TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Clearance passes table for solicited vendors
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clearance_passes (
            qr_pass_id TEXT PRIMARY KEY,
            tenant_slug TEXT,
            rfq_code TEXT,
            vendor_name TEXT,
            email TEXT,
            payment_reference TEXT,
            proposal_title TEXT,
            clearance_status TEXT
        )
    """)
    
    conn.commit()
    conn.close()

def get_tenant_by_slug(tenant_slug):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tenants WHERE tenant_slug = ?", (tenant_slug,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        "tenant_slug": tenant_slug,
        "full_corporation_name": "NexusVault Sovereign Portal",
        "institution_category": "Federal Ministry, Department, or Agency",
        "apex_title": "Executive Directorate",
        "logo_path": "",
        "status": "Active"
    }

def save_tenant(tenant_data):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO tenants (tenant_slug, full_corporation_name, institution_category, apex_title, sub_directorates_json, logo_path, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        tenant_data.get("tenant_slug"),
        tenant_data.get("full_corporation_name"),
        tenant_data.get("institution_category"),
        tenant_data.get("apex_title"),
        tenant_data.get("sub_directorates_json", "[]"),
        tenant_data.get("logo_path", ""),
        tenant_data.get("status", "Active")
    ))
    conn.commit()
    conn.close()
    return True

if __name__ == "__main__":
    init_db()
    print("Database schema initialized successfully with admin_access_logs!")

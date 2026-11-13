import sqlite3
from pathlib import Path

db_paths = ["nexus_sovereign.db", "data/nexus_sovereign.db", "sovereign.db"]
db_path = None

for p in db_paths:
    if Path(p).exists():
        db_path = p
        break

if not db_path:
    db_path = "nexus_sovereign.db"

print(f"Targeting database: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
existing_tables = [row[0] for row in cursor.fetchall()]
print(f"Existing tables: {existing_tables}")

schema_queries = [
    """
    CREATE TABLE IF NOT EXISTS nv_tenants (
        tenant_id TEXT PRIMARY KEY,
        slug TEXT UNIQUE,
        org_name TEXT,
        status TEXT,
        sub_package TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS nv_document_parses (
        parse_id TEXT PRIMARY KEY,
        tenant_id TEXT,
        file_name TEXT,
        extracted_json TEXT,
        confidence_score REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES nv_tenants(tenant_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS nv_scoring_grids (
        grid_id TEXT PRIMARY KEY,
        tenant_id TEXT,
        criteria_name TEXT,
        weight_percentage REAL,
        score_awarded REAL,
        FOREIGN KEY (tenant_id) REFERENCES nv_tenants(tenant_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS nv_audit_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id TEXT,
        action_type TEXT,
        actor_email TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES nv_tenants(tenant_id)
    );
    """
]

for query in schema_queries:
    cursor.execute(query)

conn.commit()
conn.close()

print("Database inspection and schema initialization completed successfully!")

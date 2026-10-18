import os
import json
import psycopg2
from typing import Any, Optional

class PostgresStorage:
    """
    Production-grade PostgreSQL storage adapter conforming to StorageAdapter protocol.
    Stores session drafts and complaint tickets securely with JSON serialization.
    """
    def __init__(self, connection_string: Optional[str] = None):
        # Pulls from environment variable or defaults to local PostgreSQL instance
        self.conn_str = connection_string or os.getenv(
            "DATABASE_URL", 
            "postgresql://postgres:postgres@localhost:5432/nexusvault_db"
        )
        self._init_db()

    def _get_connection(self):
        return psycopg2.connect(self.conn_str)

    def _init_db(self):
        """Initializes the secure key-value app store table if it does not exist."""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS app_store (
                    key VARCHAR(255) PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Database Initialization Notice: {e}")

    def upsert(self, key: str, value: Any) -> bool:
        """Inserts or updates a record serialized as JSON."""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            payload_json = json.dumps(value)
            cur.execute("""
                INSERT INTO app_store (key, payload, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (key) 
                DO UPDATE SET payload = EXCLUDED.payload, updated_at = CURRENT_TIMESTAMP;
            """, (key, payload_json))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"DB Upsert Error: {e}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """Retrieves and deserializes a record by key."""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("SELECT payload FROM app_store WHERE key = %s;", (key,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                return json.loads(row[0])
            return None
        except Exception as e:
            print(f"DB Get Error: {e}")
            return None

    def save(self, key: str, value: Any) -> bool:
        """Alias for upsert to maintain complete compatibility with ticket storage."""
        return self.upsert(key, value)

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from database import get_connection
except Exception:  # pragma: no cover
    from contextlib import contextmanager

    @contextmanager
    def get_connection():
        db_path = Path("nexusvault.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path, timeout=30)
        try:
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


# --- LINK CLICK & TRAFFIC ANALYTICS ---
def init_analytics_table() -> None:
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS link_click_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    link_type TEXT NOT NULL,
                    client_slug TEXT DEFAULT 'global',
                    clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    except Exception as e:
        print(f"[ANALYTICS INIT ERROR] {e}")


def log_link_click(link_type: str, client_slug: str = "global") -> None:
    try:
        init_analytics_table()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO link_click_analytics (link_type, client_slug) VALUES (?, ?)",
                (link_type, client_slug),
            )
    except Exception as e:
        print(f"[LOG CLICK ERROR] {e}")


def get_link_click_stats() -> dict:
    try:
        init_analytics_table()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT link_type, COUNT(*) FROM link_click_analytics GROUP BY link_type")
            rows = cursor.fetchall()
            stats = {row[0]: row[1] for row in rows}
            return {
                "main_domain_clicks": stats.get("main_domain", 0),
                "tenant_portal_clicks": stats.get("tenant_portal", 0),
                "vendor_portal_clicks": stats.get("vendor_portal", 0),
                "total_clicks": sum(stats.values()),
            }
    except Exception:
        return {
            "main_domain_clicks": 0,
            "tenant_portal_clicks": 0,
            "vendor_portal_clicks": 0,
            "total_clicks": 0,
        }


# --- DURABLE WORKING ENVIRONMENT & AUTO-SAVE STATE ---
def init_working_state_table() -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS client_working_state (
                session_key TEXT PRIMARY KEY,
                scope_id TEXT NOT NULL DEFAULT 'global',
                state_json TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_working_state(
    session_key: str,
    state_payload: Dict[str, Any],
    scope_id: str = "global",
) -> bool:
    clean_key = str(session_key or "").strip()
    if not clean_key:
        return False
    try:
        init_working_state_table()
        serialized = json.dumps(state_payload or {}, default=str)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO client_working_state (session_key, scope_id, state_json, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(session_key) DO UPDATE SET
                    scope_id = excluded.scope_id,
                    state_json = excluded.state_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (clean_key, str(scope_id or "global").strip(), serialized),
            )
        return True
    except Exception as e:
        print(f"[WORKING STATE SAVE ERROR] {e}")
        return False


def load_working_state(session_key: str) -> Optional[Dict[str, Any]]:
    clean_key = str(session_key or "").strip()
    if not clean_key:
        return None
    try:
        init_working_state_table()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT state_json, updated_at FROM client_working_state WHERE session_key = ?",
                (clean_key,),
            )
            row = cursor.fetchone()
        if not row:
            return None
        parsed = json.loads(row["state_json"])
        if isinstance(parsed, dict):
            parsed.setdefault("_persisted_at", row["updated_at"])
            return parsed
        return None
    except Exception as e:
        print(f"[WORKING STATE LOAD ERROR] {e}")
        return None


def clear_working_state(session_key: str) -> bool:
    clean_key = str(session_key or "").strip()
    if not clean_key:
        return False
    try:
        init_working_state_table()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM client_working_state WHERE session_key = ?", (clean_key,))
        return True
    except Exception as e:
        print(f"[WORKING STATE CLEAR ERROR] {e}")
        return False

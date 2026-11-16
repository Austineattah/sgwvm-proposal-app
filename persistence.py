

# --- LINK CLICK & TRAFFIC ANALYTICS ---
def init_analytics_table() -> None:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS link_click_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_type TEXT NOT NULL,
                client_slug TEXT DEFAULT "global",
                clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    except Exception as e:
        print(f"[ANALYTICS INIT ERROR] {e}")

def log_link_click(link_type: str, client_slug: str = "global") -> None:
    try:
        init_analytics_table()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO link_click_analytics (link_type, client_slug) VALUES (?, ?)",
            (link_type, client_slug)
        )
        conn.commit()
    except Exception as e:
        print(f"[LOG CLICK ERROR] {e}")

def get_link_click_stats() -> dict:
    try:
        init_analytics_table()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT link_type, COUNT(*) FROM link_click_analytics GROUP BY link_type")
        rows = cursor.fetchall()
        stats = {row[0]: row[1] for row in rows}
        return {
            "main_domain_clicks": stats.get("main_domain", 0),
            "tenant_portal_clicks": stats.get("tenant_portal", 0),
            "vendor_portal_clicks": stats.get("vendor_portal", 0),
            "total_clicks": sum(stats.values())
        }
    except Exception as e:
        return {"main_domain_clicks": 0, "tenant_portal_clicks": 0, "vendor_portal_clicks": 0, "total_clicks": 0}


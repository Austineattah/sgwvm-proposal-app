"""Regression tests for bounded developer activity and lazy workspace loading."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


class DeveloperPerformanceTests(unittest.TestCase):
    def test_platform_only_fetches_selected_section(self):
        script = f"""
import ast
import sqlite3
import logging
from pathlib import Path
import streamlit as st

class Store:
    def list_tenants(self):
        st.session_state["tenant_fetches"] = st.session_state.get("tenant_fetches", 0) + 1
        return []
    def list_archived_tenants(self):
        raise AssertionError("archive loaded outside deletion section")
    def list_recycle_bin_tenants(self):
        raise AssertionError("recycle bin loaded outside deletion section")
    def get_general_broadcast(self):
        st.session_state["broadcast_fetches"] = st.session_state.get("broadcast_fetches", 0) + 1
        return None

db = Store()
_persist_general_broadcast = lambda: None
source = {str(ROOT / "app.py")!r}
tree = ast.parse(Path(source).read_text(encoding="utf-8-sig"))
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
            and n.name == "_render_platform_developer_console")
exec(compile(ast.Module(body=[node], type_ignores=[]), source, "exec"))
_render_platform_developer_console()
"""
        app = AppTest.from_string(script, default_timeout=60).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["tenant_fetches"], 1)
        self.assertNotIn("broadcast_fetches", app.session_state)
        app.selectbox[0].set_value("Platform Broadcasts").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["tenant_fetches"], 1)
        self.assertEqual(app.session_state["broadcast_fetches"], 1)

    def test_activity_page_is_bounded_and_tenant_scoped(self):
        test_engine = database.create_database_engine("sqlite://")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                with patch.object(database, "DB_FILE", Path(temp_dir) / "portal.sqlite3"), \
                     patch.object(database, "engine", test_engine):
                    database.init_db()
                    with database.get_connection() as connection:
                        connection.executemany(
                            "INSERT INTO tenant_activity_logs "
                            "(tenant_slug, activity_type, description, performed_by, date, "
                            "time, month, year, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            [
                                ("tenant-a" if i < 53 else "tenant-b", "test", str(i),
                                 "tester", "2026-01-01", "12:00:00", "01", "2026",
                                 "2026-01-01T12:00:00")
                                for i in range(56)
                            ],
                        )
                    total, first = database.get_tenant_activity_page("TENANT-A")
                    second_total, second = database.get_tenant_activity_page(
                        "tenant-a", offset=50
                    )
                    self.assertEqual((total, second_total), (53, 53))
                    self.assertEqual((len(first), len(second)), (50, 3))
                    self.assertTrue(all(row["tenant_slug"] == "tenant-a" for row in first + second))
                    self.assertGreater(first[-1]["id"], second[0]["id"])
                    self.assertEqual(database.get_tenant_activity_slugs(), ["tenant-a", "tenant-b"])
                    with database.get_connection() as connection:
                        plan = connection.execute(
                            "EXPLAIN QUERY PLAN SELECT id FROM tenant_activity_logs "
                            "WHERE tenant_slug = ? ORDER BY date DESC, time DESC, id DESC LIMIT ?",
                            ("tenant-a", 50),
                        ).fetchall()
                    self.assertTrue(any("idx_tenant_activity_logs_tenant_order" in row[3] for row in plan))
                    with self.assertRaises(ValueError):
                        database.get_tenant_activity_page(limit=101)
                    database.save_tenant({
                        "tenant_slug": "tenant-a",
                        "full_corporation_name": "Tenant A",
                        "status": "ACTIVE",
                    })
                    with database.get_connection() as connection:
                        connection.executemany(
                            "INSERT INTO tenant_support_tickets "
                            "(tenant_slug, org_name, sender_email, message, status, "
                            "is_auto_responded, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            [
                                ("tenant-a", "Tenant A", "a@example.org", str(i),
                                 "OPEN" if i < 3 else "RESOLVED (AI AUTO-REPLY)", 0,
                                 "2026-01-01T12:00:00")
                                for i in range(53)
                            ],
                        )
                    total_tickets, open_tickets, first_tickets = database.get_platform_support_ticket_page()
                    _, _, remaining_tickets = database.get_platform_support_ticket_page(offset=50)
                    self.assertEqual((total_tickets, open_tickets), (53, 3))
                    self.assertEqual((len(first_tickets), len(remaining_tickets)), (50, 3))
                    self.assertGreater(first_tickets[-1]["ticket_id"], remaining_tickets[0]["ticket_id"])
                    with self.assertRaises(ValueError):
                        database.get_platform_support_ticket_page(offset=-1)
        finally:
            test_engine.dispose()


if __name__ == "__main__":
    unittest.main()

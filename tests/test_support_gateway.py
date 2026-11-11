import ast
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import database
from src.tenant_support_panel import render_client_tenant_support_panel


class SupportGatewayTests(unittest.TestCase):
    def test_developer_navigation_is_available_only_after_authentication(self):
        app_source = Path(__file__).resolve().parents[1] / "app.py"
        script = f"""
import ast
from pathlib import Path
import streamlit as st

source_path = Path({str(app_source)!r})
tree = ast.parse(source_path.read_text(encoding="utf-8-sig"))
node = next(
    node for node in tree.body
    if isinstance(node, ast.FunctionDef) and node.name == "render_developer_console"
)
_guard_session_interaction = lambda: True
_render_platform_developer_console = lambda: st.write("platform operations")
_render_platform_support_feedback = lambda: st.write("support feedback")
_render_executive_knowledge_base = lambda: st.write("executive knowledge base")
_render_seminar_training_suite = lambda: st.write("tenant slide deck")
_render_developer_master_console = lambda: st.write("SaaS master console")
_DEVELOPER_UI_IMPORT_ERROR = None
_MASTER_CONSOLE_IMPORT_ERROR = None
exec(compile(ast.Module(body=[node], type_ignores=[]), str(source_path), "exec"))
render_developer_console()
"""
        app = AppTest.from_string(
            "import streamlit as st\nst.session_state['dev_authenticated'] = True\n"
            + script,
            default_timeout=30,
        ).run()
        self.assertFalse(app.exception)

        unauthorized = AppTest.from_string(
            "import streamlit as st\n"
            + script.replace(
                "st.session_state['dev_authenticated'] = True\n",
                "st.session_state['dev_authenticated'] = False\n",
            ),
            default_timeout=30,
        ).run()
        self.assertFalse(unauthorized.exception)
        self.assertTrue(
            any("Developer authentication is required" in item.value
                for item in unauthorized.error)
        )

    def test_support_tickets_are_tenant_scoped_and_resolvable(self):
        test_engine = database.create_database_engine("sqlite://")
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch.object(database, "DB_FILE", Path(temp_dir) / "portal.sqlite3"),
                patch.object(database, "engine", test_engine),
            ):
                database.save_tenant(
                    {
                        "tenant_slug": "active-node",
                        "full_corporation_name": "Active Node",
                        "status": "ACTIVE",
                    }
                )
                database.save_tenant(
                    {
                        "tenant_slug": "inactive-node",
                        "full_corporation_name": "Inactive Node",
                        "status": "PENDING",
                    }
                )

                created, automated_response = database.create_tenant_support_ticket(
                    "active-node",
                    "contact@example.gov",
                    "Please explain the procurement workflow.",
                    automated_response="Use the committee workspace.",
                )
                self.assertTrue(created)
                self.assertEqual(automated_response, "Use the committee workspace.")
                active_tickets = database.get_tenant_support_tickets("active-node")
                self.assertEqual(len(active_tickets), 1)
                self.assertEqual(active_tickets[0]["status"], "RESOLVED (AI AUTO-REPLY)")
                self.assertEqual(
                    database.get_tenant_support_tickets("inactive-node"),
                    [],
                )
                self.assertEqual(
                    database.create_tenant_support_ticket(
                        "inactive-node",
                        "contact@example.gov",
                        "Please activate this node.",
                    ),
                    (False, None),
                )

                created, response = database.create_tenant_support_ticket(
                    "active-node",
                    "contact@example.gov",
                    "Please contact me about an unlisted policy.",
                )
                self.assertTrue(created)
                self.assertIsNone(response)
                pending = database.get_all_tenant_support_tickets()[0]
                self.assertEqual(pending["status"], "OPEN")
                self.assertTrue(
                    database.respond_to_tenant_support_ticket(
                        pending["ticket_id"],
                        "The executive office will follow up.",
                    )
                )
                self.assertFalse(
                    database.respond_to_tenant_support_ticket(
                        pending["ticket_id"],
                        "Duplicate response.",
                    )
                )
                self.assertEqual(
                    database.get_all_tenant_support_tickets()[0]["response"],
                    "The executive office will follow up.",
                )
        test_engine.dispose()

    def test_support_panel_captures_query_and_displays_immediate_response(self):
        app = AppTest.from_string(
            """
import streamlit as st
from src.tenant_support_panel import render_client_tenant_support_panel

def create_ticket(**values):
    st.session_state["submitted_message"] = values["message"]
    return True, "Knowledge Base response"

def get_tickets(tenant_slug):
    return []

render_client_tenant_support_panel(
    "tenant-a",
    "tenant-a",
    "Tenant A",
    create_ticket=create_ticket,
    get_tickets=get_tickets,
)
""",
            default_timeout=30,
        ).run()
        self.assertFalse(app.exception)
        app.text_input[0].set_value("operator@example.gov")
        app.text_area[0].set_value("How do I access the committee workspace?")
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(
            app.session_state["submitted_message"],
            "How do I access the committee workspace?",
        )
        self.assertTrue(
            any("Knowledge Base response" in item.value for item in app.info)
        )


if __name__ == "__main__":
    unittest.main()

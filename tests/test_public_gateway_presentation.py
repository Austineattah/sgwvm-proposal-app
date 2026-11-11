"""Regression coverage for public routing and solicited vendor presentation."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]

VENDOR_APP = """
from unittest.mock import patch
import streamlit as st
import sector_logic

tenders = [{"tender_id": "rfq-1", "title": "Active tender"}]
config = {"payment_mode": "corporate_lodgment"}
with patch.object(sector_logic, "_tenant_is_active", return_value=True), \\
     patch.object(sector_logic.db, "get_active_solicited_tenders", return_value=tenders), \\
     patch.object(sector_logic.db, "get_tenant_gateway_config", return_value=config):
    with st.container():
        sector_logic.render_solicited_vendor_qr_clearance_gate("tenant-a", "test")
    st.markdown("Unsolicited content outside the solicited panel")
"""


class PublicGatewayPresentationTests(unittest.TestCase):
    def test_public_home_has_no_developer_navigation(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120).run()
        self.assertFalse(app.exception)
        self.assertFalse(any("Developer" in radio.label for radio in app.radio))
        self.assertFalse(
            any("Developer Console" in radio.options for radio in app.radio)
        )
        self.assertFalse(any("Developer" in button.label for button in app.button))
        self.assertFalse(any("Developer" in tab.label for tab in app.tabs))

    def test_developer_mode_requires_authentication_and_is_purged_on_exit(self):
        with patch.dict(os.environ, {"NEXUSVAULT_DEVELOPER_GRANT_PASSWORD": "test-password"}):
            app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
            app.query_params["mode"] = "dev"
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(any("Restricted Developer Console" in item.value for item in app.warning))
            self.assertTrue(any(item.label == "Enter Developer Grant Password" for item in app.text_input))
            self.assertFalse(app.session_state.get("dev_authenticated", False))
            self.assertFalse(any("Executive Report" in button.label for button in app.button))

            app.session_state["dev_authenticated"] = True
            del app.query_params["mode"]
            app.run()
            self.assertFalse(app.exception)
            self.assertFalse(app.session_state.get("dev_authenticated", False))
            self.assertFalse(any("Developer Console" in radio.options for radio in app.radio))

    def test_tenant_route_does_not_enter_developer_mode(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
        app.query_params["mode"] = "dev"
        app.query_params["portal"] = "vendor"
        app.run()
        self.assertFalse(app.exception)
        self.assertFalse(any(item.label == "Enter Developer Grant Password" for item in app.text_input))
        self.assertFalse(app.session_state.get("dev_authenticated", False))
        self.assertTrue(app.error)

    def test_solicited_panel_keeps_widgets_and_validation(self):
        app = AppTest.from_string(VENDOR_APP, default_timeout=30).run()
        self.assertFalse(app.exception)
        styles = [item.value for item in app.markdown if "nv-solicited-panel-marker" in item.value]
        self.assertTrue(any("linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)" in value for value in styles))
        self.assertTrue(any('class="nv-solicited-panel-marker"' in value for value in styles))
        self.assertTrue(any(item.label == "Corporate vendor name*" for item in app.text_input))
        self.assertTrue(any(item.label == "Step 2: Clearance Verification" for item in app.tabs))
        submit = next(item for item in app.button if item.label == "Submit transfer reference for executive review")
        submit.click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Complete all required fields" in item.value for item in app.error))
        self.assertTrue(any("Unsolicited content outside" in item.value for item in app.markdown))


if __name__ == "__main__":
    unittest.main()

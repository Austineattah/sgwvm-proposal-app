"""Regression tests for the onboarding review and confirmation flow."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import database
import src.nexus_db_adapter as nexus_db_adapter


ROOT = Path(__file__).resolve().parents[1]


class OnboardingReviewTests(unittest.TestCase):
    def test_review_edit_and_confirmation(self):
        with TemporaryDirectory() as directory:
            lifecycle_path = Path(directory) / "lifecycle.db"
            with patch.object(nexus_db_adapter, "DB_PATH", lifecycle_path), patch.object(
                database, "create_tenant_onboarding"
            ) as create_onboarding:
                app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120).run()
                self.assertFalse(app.exception)
                for label, value in {
                    "Organizational Entity Name*": "Example Institution",
                    "Official Dispatch Email*": "contact@example.gov",
                    "Official Phone / SMS Gateway Contact*": "123456",
                    "Institutional Headquarters Address*": "Abuja",
                    "Executive Chief Notification Node": "admin@example.gov",
                    "Custom Portal Banner Title": "Example Portal",
                }.items():
                    next(item for item in app.text_input if item.label == label).set_value(value)
                next(item for item in app.checkbox if "Review & Verify" in item.label).check()
                next(item for item in app.button if item.label.startswith("Submit Organizational Node")).click().run()

                self.assertFalse(app.exception)
                self.assertTrue(app.table)
                self.assertFalse(any(item.label == "Organizational Entity Name*" for item in app.text_input))
                create_onboarding.assert_not_called()

                next(item for item in app.button if "Edit Organizational Credentials" in item.label).click().run()
                self.assertFalse(app.exception)
                self.assertEqual(
                    next(item for item in app.text_input if item.label == "Organizational Entity Name*").value,
                    "Example Institution",
                )
                self.assertEqual(
                    next(item for item in app.text_input if item.label == "Official Dispatch Email*").value,
                    "contact@example.gov",
                )

                next(item for item in app.checkbox if "Review & Verify" in item.label).check()
                next(item for item in app.button if item.label.startswith("Submit Organizational Node")).click().run()
                next(item for item in app.button if "Confirm & Submit" in item.label).click().run()
                self.assertFalse(app.exception)
                create_onboarding.assert_called_once()
                self.assertEqual(
                    create_onboarding.call_args.args[0]["full_corporation_name"],
                    "Example Institution",
                )
                self.assertTrue(app.session_state["onboarding_submitted"])
                tenant = nexus_db_adapter.NexusDatabaseAdapter(
                    database_path=lifecycle_path
                ).get_tenant(app.session_state["onboarded_tenant_id"])
                self.assertEqual(tenant["status"], "PENDING_ACTIVATION")


if __name__ == "__main__":
    unittest.main()

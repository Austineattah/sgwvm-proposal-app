import io
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf
import requests
from PIL import Image
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

import database
import email_notifier
import kyb_verifier
from document_processing import extract_pdf_text
from proposal_evaluation import assess_budget, is_critical_kyb_result
from report_generator import generate_pdf_audit_report


class PortalPipelineTests(unittest.TestCase):
    def test_onboarding_token_lifecycle_and_admin_controls(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            security_db = Path(temp_dir) / "security.sqlite3"
            with patch.object(database, "SECURITY_DATABASE_PATH", security_db):
                database.init_security_tables()
                token = database.create_onboarding_token("Example Organization")

                self.assertRegex(token, re.compile(r"^[A-Z0-9]{4}(-[A-Z0-9]{4}){3}$"))
                attempts, locked = database.record_failed_attempt(token.lower())
                self.assertEqual(attempts, 1)
                self.assertFalse(locked)
                attempts, locked = database.record_failed_attempt(token)
                self.assertEqual(attempts, 2)
                self.assertTrue(locked)
                success, message = database.verify_and_consume_token(
                    token,
                    "contact@example.com",
                )
                self.assertFalse(success)
                self.assertIn("locked", message)

                self.assertTrue(database.revoke_or_reset_token(token, "unlock"))
                success, message = database.verify_and_consume_token(
                    token,
                    "contact@example.com",
                )
                self.assertTrue(success, message)
                self.assertFalse(
                    database.verify_and_consume_token(token, "other@example.com")[0]
                )
                self.assertEqual(
                    database.get_subscribed_clients()[0]["client_name"],
                    "Example Organization",
                )
                self.assertTrue(database.revoke_or_reset_token(token, "reset"))
                self.assertTrue(database.revoke_or_reset_token(token, "revoke"))
                self.assertEqual(database.get_all_tokens()[0]["is_used"], 1)

    def test_inactive_rc_kyb_lookup_is_critical(self):
        class Response:
            status_code = 200

            @staticmethod
            def json():
                return {
                    "status": True,
                    "data": {
                        "company_status": "INACTIVE",
                        "company_name": "Example Ltd",
                        "directors": [{"firstname": "A", "surname": "Director"}],
                    },
                }

        with (
            patch.object(
                kyb_verifier,
                "st",
                type(
                    "StreamlitSecrets",
                    (),
                    {
                        "secrets": {
                            "PREMBLY_API_KEY": "test-key",
                            "PREMBLY_APP_ID": "test-app",
                        }
                    },
                )(),
            ),
            patch.object(requests, "post", return_value=Response()),
        ):
            result = kyb_verifier.verify_company_kyb("RC12345")

        self.assertFalse(result["is_active"])
        self.assertTrue(is_critical_kyb_result(result))

    def test_scanned_multipage_pdf_uses_ocr_fallback(self):
        pdf = pymupdf.open()
        for _ in range(2):
            page = pdf.new_page()
            page.insert_image(
                page.rect,
                stream=_make_test_image_bytes(),
            )
        pdf_bytes = pdf.tobytes()
        pdf.close()

        recognized_pages = []

        def fake_ocr(image):
            recognized_pages.append(image.size)
            return " ".join(f"scannedword{index}" for index in range(30))

        extracted = extract_pdf_text(pdf_bytes, ocr_function=fake_ocr)
        self.assertEqual(len(recognized_pages), 2)
        self.assertGreaterEqual(len(extracted.split()), 50)

    def test_missing_budget_is_conditional_and_not_zero(self):
        has_budget, budget_display, feasibility = assess_budget(
            "Company: Example Ltd\nBudget: To be negotiated"
        )
        self.assertFalse(has_budget)
        self.assertEqual(budget_display, "To be negotiated")
        self.assertEqual(feasibility, "Conditional")

        missing, display, rating = assess_budget("No financial information supplied.")
        self.assertFalse(missing)
        self.assertNotIn("0.00", display)
        self.assertEqual(rating, "Conditional")

    def test_database_has_structured_pipeline_tables(self):
        engine = database.create_database_engine("sqlite://")
        previous_bind = database.SessionLocal.kw["bind"]
        try:
            database.Base.metadata.create_all(engine)
            database.SessionLocal.configure(bind=engine)
            inspector = inspect(engine)
            self.assertTrue(
                {
                    "proposals",
                    "kyb_logs",
                    "audit_scores",
                }.issubset(inspector.get_table_names())
            )
            proposal_columns = {
                column["name"] for column in inspector.get_columns("proposals")
            }
            self.assertTrue(
                {
                    "filename",
                    "vendor_name",
                    "cac_number",
                    "rc_number",
                    "budget",
                    "feasibility_rating",
                    "risk_score",
                    "status",
                    "timestamp",
                }.issubset(proposal_columns)
            )

            proposal_id = database.insert_proposal(
                tracking_code="PIPELINE-TEST",
                vendor_name="Example Ltd",
                email="test@example.com",
                category="Test",
                cac_number="12345",
                ai_summary="Test executive brief",
                budget=None,
                filename="proposal.pdf",
                feasibility_rating="Conditional",
                risk_score=100,
                kyb_data={
                    "rc_number": "12345",
                    "company_status": "INACTIVE",
                    "tin": "N/A",
                    "directors": ["A Director"],
                    "risk_label": "Inactive",
                },
                legal_risk_flags=["Inactive registration"],
                compliance_gaps=["No explicit budget"],
                raw_ai_json={"has_budget": False},
            )
            with Session(engine) as session:
                proposal = session.get(database.Proposal, proposal_id)
                kyb_log = session.query(database.KYBLog).filter_by(
                    proposal_id=proposal_id
                ).one()
                audit_score = session.query(database.AuditScore).filter_by(
                    proposal_id=proposal_id
                ).one()
                self.assertEqual(proposal.filename, "proposal.pdf")
                self.assertEqual(proposal.rc_number, "12345")
                self.assertEqual(kyb_log.company_status, "INACTIVE")
                self.assertIn("Inactive registration", audit_score.legal_risk_flags)
        finally:
            database.SessionLocal.configure(bind=previous_bind)
            engine.dispose()

    def test_database_migrates_existing_proposal_table(self):
        engine = database.create_database_engine("sqlite://")
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "CREATE TABLE proposals ("
                        "id INTEGER PRIMARY KEY, "
                        "tracking_code VARCHAR(100) NOT NULL, "
                        "vendor_name VARCHAR(255) NOT NULL, "
                        "email VARCHAR(320) NOT NULL, "
                        "category VARCHAR(255) NOT NULL, "
                        "cac_number VARCHAR(100) NOT NULL)"
                    )
                )
            database.Base.metadata.create_all(engine)
            database.ensure_proposal_status_column(engine)
            proposal_columns = {
                column["name"] for column in inspect(engine).get_columns("proposals")
            }
            self.assertTrue(
                {
                    "filename",
                    "rc_number",
                    "feasibility_rating",
                    "risk_score",
                    "timestamp",
                    "status",
                }.issubset(proposal_columns)
            )
        finally:
            engine.dispose()

    def test_vendor_acknowledgment_handles_missing_secrets(self):
        with patch.object(email_notifier, "st") as streamlit:
            streamlit.secrets = {}
            success, message = email_notifier.send_vendor_acknowledgment(
                "vendor@example.com",
                "Example Vendor",
                42,
            )
        self.assertFalse(success)
        self.assertIn("SMTP secrets", message)

    def test_vendor_acknowledgment_sends_when_smtp_is_configured(self):
        class SMTPServer:
            def __init__(self):
                self.message = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                return False

            def ehlo(self):
                pass

            def starttls(self, context):
                pass

            def login(self, sender, password):
                self.sender = sender
                self.password = password

            def send_message(self, message):
                self.message = message

        smtp_server = SMTPServer()
        with (
            patch.object(email_notifier, "st") as streamlit,
            patch.object(
                email_notifier.smtplib,
                "SMTP",
                return_value=smtp_server,
            ),
        ):
            streamlit.secrets = {
                "SMTP_SERVER": "smtp.example.com",
                "SMTP_PORT": "587",
                "SENDER_EMAIL": "sender@example.com",
                "SENDER_PASSWORD": "test-password",
            }
            success, message = email_notifier.send_vendor_acknowledgment(
                "vendor@example.com",
                "Example Vendor",
                42,
            )

        self.assertTrue(success)
        self.assertEqual(message, "Vendor acknowledgment email sent.")
        self.assertEqual(smtp_server.message["To"], "vendor@example.com")
        self.assertIn("42", smtp_server.message.get_content())

    def test_pdf_audit_report_generates_pdf_bytes(self):
        pdf_bytes = generate_pdf_audit_report(
            {
                "company_name": "Vendor & Co",
                "rc_number": "12345",
                "budget_display": "To be negotiated",
                "feasibility_rating": "Conditional",
                "risk_score": 60,
                "executive_summary": "Assessment & review required.",
                "risk_flagged": True,
            },
            {
                "company_name": "Vendor & Co",
                "rc_number": "12345",
                "company_status": "INACTIVE",
                "tin": "Not verified",
                "directors": ["A & B"],
                "flagged": True,
            },
        )
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


def _make_test_image_bytes():
    image_buffer = io.BytesIO()
    Image.new("RGB", (30, 30), color="white").save(image_buffer, format="PNG")
    return image_buffer.getvalue()


if __name__ == "__main__":
    unittest.main()

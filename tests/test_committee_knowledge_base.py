import unittest

from streamlit.testing.v1 import AppTest

from src.developer_kb import NEXUSVAULT_EXECUTIVE_KB


class CommitteeKnowledgeBaseTests(unittest.TestCase):
    def test_committee_guidance_appears_in_lookup(self):
        app = AppTest.from_string(
            "from src.developer_console import render_seminar_training_suite\n"
            "render_seminar_training_suite()",
            default_timeout=60,
        ).run()
        self.assertFalse(app.exception)
        app.radio[0].set_value("🔍 Interactive Knowledge Base Lookup").run()
        self.assertFalse(app.exception)
        topic = next(
            widget
            for widget in app.selectbox
            if widget.label == "Select System Component / Module for Deep Dive:"
        )
        topic.set_value("Committee Evaluation Workspace").run()
        self.assertFalse(app.exception)
        questions = {
            "Executive Committee Access Generation",
            "Tender Review Committee Provisioning",
            "Mandatory Password Rotation Policy",
            "Immediate Token Revocation",
            "What is the Committee Evaluation Workspace and what are its core functions?",
        }
        rendered = [expander.label for expander in app.expander]
        for question in questions:
            self.assertTrue(any(question in label for label in rendered), question)
        self.assertTrue(
            any("**Core Functions of the Committee Workspace:**" in item.value for item in app.markdown)
        )

    def test_committee_overview_has_requested_category_and_content(self):
        entries = NEXUSVAULT_EXECUTIVE_KB["Committee Evaluation Workspace"]["qa_pairs"]
        entry = next(
            entry
            for entry in entries
            if entry["question"]
            == "What is the Committee Evaluation Workspace and what are its core functions?"
        )
        self.assertEqual(entry["category"], "Committee Security & Access Management")
        for section in (
            "Encrypted Dossier Review",
            "Standardized Scoring & Compliance Auditing",
            "The Bridge to Contract Award",
            "Immutable Audit Trails",
            "tenant_audit_logs",
        ):
            self.assertIn(section, entry["answer"])

    def test_committee_guidance_appears_in_slide_deck(self):
        slides = [
            qa
            for topic in NEXUSVAULT_EXECUTIVE_KB.values()
            for qa in topic["qa_pairs"]
        ]
        index = next(
            index
            for index, slide in enumerate(slides)
            if slide["question"] == "Immediate Token Revocation"
        )
        app = AppTest.from_string(
            "from src.developer_console import render_seminar_training_suite\n"
            "render_seminar_training_suite()",
            default_timeout=60,
        )
        app.session_state["seminar_slide_idx"] = index
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(
            any("Immediate Token Revocation" in item.value for item in app.markdown)
        )
        self.assertTrue(any(widget.label == "Jump to Slide:" for widget in app.selectbox))


if __name__ == "__main__":
    unittest.main()

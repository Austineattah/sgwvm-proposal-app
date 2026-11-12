import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.developer_kb import NEXUSVAULT_EXECUTIVE_KB

BRIEFING_TITLE = (
    "🛡️ NEXUSVAULT TECHNOLOGIES: Super Intelligence — "
    "Agentic AI Proposal Intake & Governance Portal"
)
PRESENTATION_TITLE = "📊 Executive Presentation"


class CommitteeKnowledgeBaseTests(unittest.TestCase):
    def assert_briefing_rendered(self, app):
        document = NEXUSVAULT_EXECUTIVE_KB[BRIEFING_TITLE]["documentation"]
        self.assertTrue(any(item.value == document for item in app.markdown))
        self.assertTrue(
            any("backdrop-filter: blur(12px)" in item.value for item in app.markdown)
        )
        self.assertTrue(any("nv-kb-executive-badge" in item.value for item in app.markdown))

    def test_briefing_is_selectable_in_training_lookup(self):
        app = AppTest.from_string(
            "from src.developer_console import render_seminar_training_suite\n"
            "render_seminar_training_suite()",
            default_timeout=120,
        ).run()
        self.assertFalse(app.exception)
        app.radio[0].set_value("🔍 Interactive Knowledge Base Lookup").run()
        self.assertFalse(app.exception)
        document = NEXUSVAULT_EXECUTIVE_KB[BRIEFING_TITLE]["documentation"]
        self.assertFalse(any(item.value == document for item in app.markdown))
        topic = next(
            item for item in app.selectbox
            if item.label == "Select System Component / Module for Deep Dive:"
        )
        topic.set_value(BRIEFING_TITLE).run()
        self.assertFalse(app.exception)
        self.assert_briefing_rendered(app)
        topic.set_value(PRESENTATION_TITLE).run()
        self.assertFalse(app.exception)
        presentation = NEXUSVAULT_EXECUTIVE_KB[PRESENTATION_TITLE]["documentation"]
        self.assertTrue(any(item.value == presentation for item in app.markdown))
        self.assertFalse(any(item.value == document for item in app.markdown))
        self.assertTrue(any("backdrop-filter: blur(12px)" in item.value for item in app.markdown))
        topic.set_value("Committee Evaluation Workspace").run()
        self.assertFalse(app.exception)
        self.assertFalse(any(item.value == document for item in app.markdown))
        self.assertTrue(any("Immediate Token Revocation" in item.label for item in app.expander))

    def test_briefing_is_selectable_in_main_knowledge_base(self):
        source = Path(__file__).resolve().parents[1] / "app.py"
        script = f"""
import ast
from pathlib import Path
import streamlit as st
from src.developer_kb import NEXUSVAULT_EXECUTIVE_KB
from src.kb_presentation import render_executive_document
_DEVELOPER_KB_IMPORT_ERROR = None
path = Path({str(source)!r})
tree = ast.parse(path.read_text(encoding="utf-8-sig"))
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
            and n.name == "_render_executive_knowledge_base")
exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"))
_render_executive_knowledge_base()
"""
        app = AppTest.from_string(script, default_timeout=120).run()
        self.assertFalse(app.exception)
        app.selectbox[0].set_value(BRIEFING_TITLE).run()
        self.assertFalse(app.exception)
        self.assert_briefing_rendered(app)
        app.selectbox[0].set_value(PRESENTATION_TITLE).run()
        self.assertFalse(app.exception)
        presentation = NEXUSVAULT_EXECUTIVE_KB[PRESENTATION_TITLE]["documentation"]
        self.assertTrue(any(item.value == presentation for item in app.markdown))
        self.assertTrue(any("nv-kb-executive-badge" in item.value for item in app.markdown))

    def test_presentation_contains_all_slides_and_speaker_notes(self):
        presentation = NEXUSVAULT_EXECUTIVE_KB[PRESENTATION_TITLE]["documentation"]
        self.assertEqual(presentation.count("#### Slide "), 6)
        self.assertEqual(presentation.count("**Speaker Notes:**"), 6)
        self.assertIn("80%+ Faster Proposal Review Cycles", presentation)
        self.assertTrue(presentation.endswith('ready for Phase 1 deployment."'))

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

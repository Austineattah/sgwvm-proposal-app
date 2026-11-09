"""Streamlit interaction tests for the signed committee-token sandbox."""

from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from src.committee_auth import CommitteeTokenManager

_APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
_HARNESS = """
import ast
import logging
import os
import sqlite3
import time
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
from src.committee_auth import CommitteeTokenManager

class AuditStore:
    def log_security_audit_event(self, *args):
        pass

db = AuditStore()
_TENANT_SESSION_PREFIX = "tenant:"
_guard_session_interaction = lambda: True
_security_session_identifier = lambda: "session:test"
names = {
    "_tenant_key",
    "_configured_committee_token_manager",
    "_verified_committee_token",
    "_handle_signed_committee_login",
    "_render_signed_committee_sandbox",
}
tree = ast.parse(open(APP_PATH, encoding="utf-8").read())
selected = ast.Module(
    body=[node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names],
    type_ignores=[],
)
exec(compile(selected, APP_PATH, "exec"))
_render_signed_committee_sandbox("example_tenant")
"""


@pytest.fixture
def sandbox(monkeypatch):
    monkeypatch.setenv("DOSSIER_ENCRYPTION_KEY", "test-signing-key")
    app = AppTest.from_string(
        f"APP_PATH = {str(_APP_PATH)!r}\n" + _HARNESS, default_timeout=30
    )
    app.run()
    assert not app.exception
    return app


def _submit(app, token):
    app.text_input[0].set_value(token)
    app.button[0].click().run()
    assert not app.exception


def test_signed_token_unlocks_and_logout_locks(sandbox):
    token = CommitteeTokenManager("test-signing-key").generate_token(
        "member@example.org", "example_tenant", "tender-123"
    )
    _submit(sandbox, token)
    assert len(sandbox.success) == 1
    assert "member@example.org" in sandbox.markdown[0].value
    assert "example_tenant" in sandbox.markdown[1].value
    assert "tender-123" in sandbox.markdown[2].value
    assert sandbox.session_state["tenant:example_tenant:committee_signed:input"] == ""

    sandbox.button[0].click().run()
    assert not sandbox.success
    assert len(sandbox.text_input) == 1


@pytest.mark.parametrize(
    ("signing_key", "tenant", "days"),
    [
        ("wrong-key", "example_tenant", 14),
        ("test-signing-key", "another_tenant", 14),
        ("test-signing-key", "example_tenant", -1),
    ],
)
def test_invalid_cross_tenant_or_expired_token_stays_locked(
    sandbox, signing_key, tenant, days
):
    token = CommitteeTokenManager(signing_key).generate_token(
        "member@example.org", tenant, "tender-123", expiration_days=days
    )
    _submit(sandbox, token)
    assert not sandbox.success
    assert "invalid" in sandbox.error[0].value


def test_key_rotation_locks_existing_session(sandbox, monkeypatch):
    token = CommitteeTokenManager("test-signing-key").generate_token(
        "member@example.org", "example_tenant", "tender-123"
    )
    _submit(sandbox, token)
    monkeypatch.setenv("DOSSIER_ENCRYPTION_KEY", "new-signing-key")
    sandbox.run()
    assert not sandbox.success
    assert sandbox.warning
    assert len(sandbox.text_input) == 1


def test_missing_key_fails_closed(monkeypatch):
    monkeypatch.delenv("DOSSIER_ENCRYPTION_KEY", raising=False)
    monkeypatch.setattr(st, "secrets", {})
    app = AppTest.from_string(
        f"APP_PATH = {str(_APP_PATH)!r}\n" + _HARNESS, default_timeout=30
    )
    app.run()
    assert not app.exception
    assert "DOSSIER_ENCRYPTION_KEY" in app.error[0].value
    assert not app.text_input


def test_streamlit_secret_can_supply_signing_key(monkeypatch):
    monkeypatch.delenv("DOSSIER_ENCRYPTION_KEY", raising=False)
    monkeypatch.setattr(st, "secrets", {"DOSSIER_ENCRYPTION_KEY": "secret-key"})
    app = AppTest.from_string(
        f"APP_PATH = {str(_APP_PATH)!r}\n" + _HARNESS, default_timeout=30
    )
    app.run()
    token = CommitteeTokenManager("secret-key").generate_token(
        "member@example.org", "example_tenant", "tender-123"
    )
    _submit(app, token)
    assert app.success


def test_missing_tender_claim_cannot_unlock(sandbox):
    token = CommitteeTokenManager("test-signing-key").generate_token(
        "member@example.org", "example_tenant", ""
    )
    _submit(sandbox, token)
    assert not sandbox.success
    assert sandbox.error


_WORKSPACE_HARNESS = """
import ast
import logging
import os
import sqlite3
import time
from collections.abc import Mapping
from typing import Any
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
from src.committee_auth import CommitteeTokenManager

class Store:
    def get_active_solicited_tenders(self, tenant):
        return [] if st.session_state.get("closed") else [
            {"tender_id": "tender-1", "title": "First"},
            {"tender_id": "tender-2", "title": "Second"},
        ]
    def get_tenant_committee_members(self, tenant):
        return [] if st.session_state.get("revoked") else [
            {"member_id": "member-1", "name": "Reviewer", "email": "member@example.org", "coi_signed": False}
        ]
    def log_security_audit_event(self, *args):
        if st.session_state.get("audit_failure"):
            raise RuntimeError("audit unavailable")
        st.session_state["audit_event"] = args[2]
    def get_tenant_governance_proposals(self, tenant):
        return [
            {"tracking_id": "pass-1", "proposal_title": "First dossier", "source_type": "solicited"},
            {"tracking_id": "pass-2", "proposal_title": "Second dossier", "source_type": "solicited"},
            {"tracking_id": "physical", "proposal_title": "Physical dossier", "source_type": "physical"},
        ]
    def get_tenant_financial_ledger(self, tenant):
        return [
            {"qr_pass_id": "pass-1", "rfq_code": "tender-1", "clearance_status": "DOSSIER_SUBMITTED"},
            {"qr_pass_id": "pass-2", "rfq_code": "tender-2", "clearance_status": "DOSSIER_SUBMITTED"},
        ]
    def get_committee_coi_status(self, *args):
        return None

db = Store()
_TENANT_SESSION_PREFIX = "tenant:"
_guard_session_interaction = lambda: True
_security_session_identifier = lambda: "session:test"
names = {
    "_tenant_key", "_configured_committee_token_manager", "enforce_committee_access",
    "_clear_committee_access", "_handle_committee_access", "_render_committee_workspace",
}
tree = ast.parse(open(APP_PATH, encoding="utf-8").read())
selected = ast.Module(
    body=[node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names],
    type_ignores=[],
)
exec(compile(selected, APP_PATH, "exec"))
_render_committee_workspace("example_tenant")
"""


@pytest.fixture
def workspace(monkeypatch):
    monkeypatch.setenv("DOSSIER_ENCRYPTION_KEY", "test-signing-key")
    app = AppTest.from_string(
        f"APP_PATH = {str(_APP_PATH)!r}\n" + _WORKSPACE_HARNESS, default_timeout=30
    ).run()
    assert not app.exception
    return app


def test_workspace_unlocks_only_selected_batch_and_logout(workspace):
    token = CommitteeTokenManager("test-signing-key").generate_token(
        "member@example.org", "example_tenant", "tender-1"
    )
    _submit(workspace, token)
    assert workspace.session_state["committee_authenticated"] is True
    assert workspace.session_state["committee_payload"]["tender_id"] == "tender-1"
    assert "member@example.org" in workspace.success[0].value
    assert workspace.selectbox[0].options == ["pass-1 · First dossier"]
    assert workspace.session_state["tenant:example_tenant:committee:signed_input"] == ""
    workspace.button[0].click().run()
    assert workspace.session_state["committee_authenticated"] is False
    assert workspace.session_state["committee_payload"] is None
    assert len(workspace.text_input) == 1


@pytest.mark.parametrize(
    ("key", "tenant", "tender", "days", "email"),
    [
        ("wrong-key", "example_tenant", "tender-1", 14, "member@example.org"),
        ("test-signing-key", "other", "tender-1", 14, "member@example.org"),
        ("test-signing-key", "example_tenant", "tender-2", 14, "member@example.org"),
        ("test-signing-key", "example_tenant", "tender-1", -1, "member@example.org"),
        ("test-signing-key", "example_tenant", "tender-1", 14, "unknown@example.org"),
    ],
)
def test_workspace_rejects_invalid_claims_and_unregistered_members(
    workspace, key, tenant, tender, days, email
):
    token = CommitteeTokenManager(key).generate_token(email, tenant, tender, days)
    _submit(workspace, token)
    assert workspace.session_state["committee_authenticated"] is False
    assert workspace.error
    assert "Compliance error" in workspace.error[0].value
    assert len(workspace.selectbox) == 1


@pytest.mark.parametrize("change", ["key", "closed", "revoked"])
def test_workspace_revalidates_authenticated_sessions(workspace, monkeypatch, change):
    token = CommitteeTokenManager("test-signing-key").generate_token(
        "member@example.org", "example_tenant", "tender-1"
    )
    _submit(workspace, token)
    if change == "key":
        monkeypatch.setenv("DOSSIER_ENCRYPTION_KEY", "rotated-key")
    else:
        workspace.session_state[change] = True
    workspace.run()
    assert not workspace.exception
    assert workspace.session_state["committee_authenticated"] is False
    assert workspace.session_state["committee_payload"] is None
    assert workspace.warning


@pytest.mark.parametrize("audit_failure", [False, True])
def test_executive_issues_audited_signed_tender_token(monkeypatch, audit_failure):
    monkeypatch.setenv("DOSSIER_ENCRYPTION_KEY", "test-signing-key")
    harness = _WORKSPACE_HARNESS.replace(
        '"_clear_committee_access", "_handle_committee_access", "_render_committee_workspace",',
        '"_clear_committee_access", "_handle_committee_access", "_render_committee_workspace", "_render_executive_committee_tab", "_render_executive_committee_roster",',
    ).replace(
        '_render_committee_workspace("example_tenant")',
        "_physical_document_encryption_key = lambda: None\n"
        "_render_committee_leaderboard = lambda tenant: None\n"
        '_render_executive_committee_tab("example_tenant", "executive")',
    )
    app = AppTest.from_string(
        f"APP_PATH = {str(_APP_PATH)!r}\n" + harness, default_timeout=30
    ).run()
    assert not app.exception
    app.session_state["audit_failure"] = audit_failure
    next(
        button for button in app.button if button.label == "Issue signed access token"
    ).click().run()
    assert not app.exception
    if audit_failure:
        assert app.error
        assert not app.code
    else:
        assert app.session_state["audit_event"] == "COMMITTEE_TOKEN_ISSUED"
        valid, payload, _ = CommitteeTokenManager("test-signing-key").verify_token(
            app.code[0].value
        )
        assert valid
        assert payload["tenant_id"] == "example_tenant"
        assert payload["tender_id"] == "tender-1"
        assert payload["email"] == "member@example.org"

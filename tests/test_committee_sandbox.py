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

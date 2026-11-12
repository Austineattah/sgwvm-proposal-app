"""Streamlit session security regression tests without production databases."""

import time
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP_HARNESS = """
import ast
import hmac
import logging
import os
import sqlite3
import time
import uuid
from collections.abc import Mapping
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

class AuditStore:
    def log_security_audit_event(self, *args):
        if st.session_state.get("audit_failure"):
            raise OSError("audit unavailable")

db = AuditStore()
_raw_portal = None
inject_sovereign_workspace_css = lambda: None
_sync_tenant_session = lambda tenant, portal: None
render_developer_console = lambda: st.write("Protected console")
tree = ast.parse(open(APP_PATH, encoding="utf-8-sig").read())
functions = {
    "_security_session_identifier", "_authenticated_actor_context",
    "_expire_idle_session", "_guard_session_interaction", "_touch_session_activity",
    "_configured_developer_password", "_handle_developer_login",
    "_handle_primary_workspace_change",
}
constants = {"_IDLE_SESSION_TIMEOUT_SECONDS", "_SESSION_ACTIVITY_KEY",
             "_SECURITY_SESSION_ID_KEY", "_SESSION_EXPIRY_NOTICE"}
selected = [
    node for node in tree.body
    if (isinstance(node, ast.FunctionDef) and node.name in functions)
    or (isinstance(node, ast.Assign) and any(
        isinstance(target, ast.Name) and target.id in constants for target in node.targets
    ))
]
exec(compile(ast.Module(body=selected, type_ignores=[]), APP_PATH, "exec"))
if _touch_session_activity():
    st.rerun()
notice = st.session_state.pop("session_expired_msg", None)
if notice:
    st.warning(notice)
branch = next(node for node in tree.body if isinstance(node, ast.If)
              and 'st.query_params.get("mode") == "dev"' in ast.get_source_segment(
                  open(APP_PATH, encoding="utf-8-sig").read(), node.test))
exec(compile(ast.Module(body=[branch], type_ignores=[]), APP_PATH, "exec"))
"""

LEGACY_HARNESS = """
import ast
import hmac
import os
import time
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
class Store:
    def purge_expired_pending_clients(self): return 0
    def get_all_clients(self): return []
db = Store()
tree = ast.parse(open(APP_PATH, encoding="utf-8-sig").read())
names = {"_developer_password", "_expire_developer_session", "_monitor_developer_session",
         "_authenticate_developer", "render_developer_master_console"}
selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
exec(compile(ast.Module(body=selected, type_ignores=[]), APP_PATH, "exec"))
render_developer_master_console()
"""


@pytest.fixture
def developer_app(monkeypatch):
    monkeypatch.setenv("NEXUSVAULT_DEVELOPER_GRANT_PASSWORD", "  test-password  ")
    app = AppTest.from_string(
        f"APP_PATH = {str(ROOT / 'app.py')!r}\n" + APP_HARNESS,
        default_timeout=30,
    )
    app.query_params["mode"] = "dev"
    app.run()
    assert not app.exception
    return app


def test_developer_password_cleared_on_failure_and_success(developer_app):
    developer_app.text_input[0].set_value("wrong")
    developer_app.button[0].click().run()
    assert not developer_app.exception
    assert developer_app.text_input[0].value == ""
    assert not developer_app.session_state.get("dev_authenticated", False)
    assert "Developer access could not be verified" in developer_app.error[0].value
    developer_app.text_input[0].set_value("  test-password  ")
    developer_app.button[0].click().run()
    assert not developer_app.exception
    assert developer_app.text_input[0].value == ""
    assert developer_app.session_state["dev_authenticated"] is True


def test_developer_expiry_purges_all_state_and_shows_notice(developer_app):
    developer_app.text_input[0].set_value("test-password")
    developer_app.button[0].click().run()
    for key in (
        "auth_token",
        "developer_password",
        "developer_grant_password",
        "tenant:a:password",
    ):
        developer_app.session_state[key] = "sensitive"
    developer_app.session_state["dev_password_input"] = "sensitive"
    developer_app.session_state["last_activity"] = time.time() - 901
    developer_app.run()
    assert not developer_app.exception
    assert developer_app.text_input[0].value == ""
    assert not developer_app.session_state.get("dev_authenticated", False)
    for key in (
        "auth_token",
        "developer_password",
        "developer_grant_password",
        "tenant:a:password",
    ):
        assert key not in developer_app.session_state
    assert any(
        "Session expired due to 15 minutes" in notice.value
        for notice in developer_app.warning
    )


def test_developer_audit_failure_denies_access(developer_app):
    developer_app.session_state["audit_failure"] = True
    developer_app.text_input[0].set_value("test-password")
    developer_app.button[0].click().run()
    assert not developer_app.exception
    assert developer_app.text_input[0].value == ""
    assert not developer_app.session_state.get("dev_authenticated", False)
    assert any(
        "could not be verified and recorded" in item.value
        for item in developer_app.error
    )


@pytest.mark.parametrize(
    ("path", "monitor", "expire"),
    [
        ("app.py", "_session_idle_timeout_monitor", "_expire_idle_session"),
        (
            "developer_console.py",
            "_monitor_developer_session",
            "_expire_developer_session",
        ),
        (
            "src/developer_console.py",
            "_monitor_developer_session",
            "_expire_developer_session",
        ),
    ],
)
def test_idle_monitor_requests_full_rerun(path, monitor, expire):
    source = ROOT / path
    tree = ast.parse(source.read_text(encoding="utf-8-sig"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == monitor
    )
    reruns = []
    namespace = {
        "st": SimpleNamespace(rerun=lambda: reruns.append(True)),
        expire: lambda: True,
    }
    exec(
        compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"),
        namespace,
    )
    namespace[monitor]()
    assert reruns == [True]


def test_expired_login_submission_cannot_reauthenticate(developer_app):
    developer_app.session_state["last_activity"] = time.time() - 901
    developer_app.text_input[0].set_value("test-password")
    developer_app.button[0].click().run()
    assert not developer_app.exception
    assert not developer_app.session_state.get("dev_authenticated", False)
    assert developer_app.text_input[0].value == ""
    assert any(
        "Session expired due to 15 minutes" in notice.value
        for notice in developer_app.warning
    )


def test_developer_secret_fallback(monkeypatch):
    monkeypatch.delenv("NEXUSVAULT_DEVELOPER_GRANT_PASSWORD", raising=False)
    monkeypatch.setattr(
        st, "secrets", {"NEXUSVAULT_DEVELOPER_GRANT_PASSWORD": "  secret-key  "}
    )
    app = AppTest.from_string(
        f"APP_PATH = {str(ROOT / 'app.py')!r}\n" + APP_HARNESS, default_timeout=30
    )
    app.query_params["mode"] = "dev"
    app.run()
    app.text_input[0].set_value(" secret-key ")
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state.get("dev_authenticated", app.session_state.get("developer_authenticated", True))
    assert app.text_input[0].value == ""


def test_legacy_console_clears_password_and_expires(monkeypatch):
    monkeypatch.setenv("NEXUSVAULT_DEVELOPER_GRANT_PASSWORD", "  test-password  ")
    app = AppTest.from_string(
        f"APP_PATH = {str(ROOT / 'developer_console.py')!r}\n" + LEGACY_HARNESS,
        default_timeout=30,
    ).run()
    app.text_input[0].set_value("wrong")
    app.button[0].click().run()
    assert not app.exception
    assert app.text_input[0].value == ""
    app.text_input[0].set_value(" test-password ")
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state["dev_master_logged_in"] is True
    app.session_state["auth_token"] = "sensitive"
    app.session_state["last_activity"] = time.time() - 901
    app.run()
    assert not app.exception
    assert "auth_token" not in app.session_state
    assert not app.session_state.get("dev_master_logged_in", False)
    assert app.text_input[0].value == ""
    assert app.warning


def test_support_developer_console_requires_authentication():
    app = AppTest.from_string(
        """
import streamlit as st
from src.developer_console import render_developer_console

def get_tickets():
    st.session_state["support_tickets_loaded"] = True
    return []

render_developer_console(get_tickets=get_tickets)
""",
        default_timeout=30,
    ).run()
    assert not app.exception
    assert any(
        "Developer authentication is required" in item.value for item in app.error
    )
    assert "support_tickets_loaded" not in app.session_state

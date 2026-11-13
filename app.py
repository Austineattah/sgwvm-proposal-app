import hashlib
import html
import hmac
import json
import logging
import os
import re
import secrets
import sqlite3
import tempfile
import textwrap
import time
import uuid
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from email.utils import parseaddr
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

import streamlit as st


def _handle_primary_workspace_change() -> None:
    """Unconditional module-level callback for primary workspace navigation."""
    if not _guard_session_interaction():
        return
    selected_workspace = st.session_state.get(
        "_primary_workspace_selection",
        "Developer Console",
    )
    if selected_workspace not in {"Onboarding Portal", "Developer Console"}:
        logging.error(
            "The primary workspace selector returned an unsupported value: %r.",
            selected_workspace,
        )
        return
    st.session_state["_primary_workspace"] = selected_workspace
    if selected_workspace == "Developer Console":
        st.query_params["mode"] = "dev"
    else:
        st.query_params.pop("mode", None)


import requests
from PIL import Image, UnidentifiedImageError
from cryptography.fernet import Fernet, InvalidToken

from streamlit.errors import StreamlitSecretNotFoundError

import database as db

from src.nexus_db_adapter import NexusDatabaseAdapter
from src.nexus_tenant_engine import NexusTenantLifecycleEngine
from src.tenant_banner import render_tenant_banner


try:
    from src.committee_auth import CommitteeTokenManager
except ImportError as exc:
    CommitteeTokenManager = None
    _COMMITTEE_AUTH_IMPORT_ERROR: ImportError | None = exc
else:
    _COMMITTEE_AUTH_IMPORT_ERROR = None

try:
    from src.developer_console import (
        render_seminar_training_suite as _render_seminar_training_suite,
        render_tenant_feedback_tab as _render_tenant_feedback_tab,
    )
except ImportError as exc:
    _render_seminar_training_suite = None
    _render_tenant_feedback_tab = None
    _DEVELOPER_UI_IMPORT_ERROR: ImportError | None = exc
else:
    _DEVELOPER_UI_IMPORT_ERROR = None

try:
    from src.developer_kb import NEXUSVAULT_EXECUTIVE_KB
    from src.kb_presentation import render_executive_document
except ImportError as exc:
    NEXUSVAULT_EXECUTIVE_KB = {}
    render_executive_document = None
    _DEVELOPER_KB_IMPORT_ERROR: ImportError | None = exc
else:
    _DEVELOPER_KB_IMPORT_ERROR = None

try:
    from src.nexus_db_adapter import match_knowledge_base as _match_knowledge_base
except ImportError as exc:
    _match_knowledge_base = None
    _SUPPORT_KB_IMPORT_ERROR: ImportError | None = exc
else:
    _SUPPORT_KB_IMPORT_ERROR = None

try:
    from psycopg2 import Error as _PostgreSQLSupportError
    from src.nexus_ai_support import (
        NexusAgenticSupportEngine,
        SovereignKnowledgeBase,
        SupportTier,
        UserContext,
    )
except ImportError as exc:
    _PostgreSQLSupportError = None
    NexusAgenticSupportEngine = None
    SovereignKnowledgeBase = None
    SupportTier = None
    UserContext = None
    _AI_SUPPORT_IMPORT_ERROR: ImportError | None = exc
else:
    _AI_SUPPORT_IMPORT_ERROR = None

try:
    from src.tenant_support_panel import (
        render_client_tenant_support_panel as _render_tenant_support_panel,
    )
except ImportError as exc:
    _render_tenant_support_panel = None
    _TENANT_SUPPORT_IMPORT_ERROR: ImportError | None = exc
else:
    _TENANT_SUPPORT_IMPORT_ERROR = None

try:
    from developer_console import (
        render_developer_master_console as _render_developer_master_console,
    )
except ImportError as exc:
    _render_developer_master_console = None
    _MASTER_CONSOLE_IMPORT_ERROR: ImportError | None = exc
else:
    _MASTER_CONSOLE_IMPORT_ERROR = None

try:
    from src.nexus_report_exporter import render_report_export_widget
except ImportError as exc:
    render_report_export_widget = None
    _REPORT_EXPORTER_IMPORT_ERROR: ImportError | None = exc
else:
    _REPORT_EXPORTER_IMPORT_ERROR = None

try:
    from src.nexus_pdf_exporter import render_pdf_export_widget
except ImportError as exc:
    render_pdf_export_widget = None
    _PDF_EXPORTER_IMPORT_ERROR: ImportError | None = exc
else:
    _PDF_EXPORTER_IMPORT_ERROR = None

PRODUCTION_BASE_URL = "https://nexusvault-proposal-enterprise-connect.streamlit.app"


def inject_production_security_css() -> None:
    """Hide Streamlit chrome and source controls from the public portal UI."""
    isolated_portals = {"vendor", "internal", "frontdesk", "admin"}
    portal = st.query_params.get("portal")
    hide_sidebar_navigation = (
        isinstance(portal, str) and portal.strip().lower() in isolated_portals
    )
    selectors = [
        'header[data-testid="stHeader"]',
        'div[data-testid="stToolbar"]',
        'div[data-testid="stStatusWidget"]',
        "#MainMenu",
        "footer",
        ".viewerBadge_container__16g8m",
        'button[title="View app source"]',
    ]
    if hide_sidebar_navigation:
        selectors.append('div[data-testid="stSidebarNav"]')
    selector_list = ",\n".join(selectors)
    st.markdown(
        f"""
        <style>
        {selector_list} {{
            display: none !important;
            visibility: hidden !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_sovereign_workspace_css() -> None:
    """Apply a shared dark surface to the onboarding and developer workspaces."""
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(135deg, #0f172a, #1e1b4b);
            color: #f8fafc;
        }
        div[data-testid="stForm"],
        div[data-testid="stExpander"],
        div[data-testid="stMetric"],
        .onboarding-title-banner {
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(56, 189, 248, 0.2);
            border-radius: 12px;
        }
        div[data-testid="stMetric"] {
            padding: 1rem;
        }
        div[data-testid="stMetric"],
        div[data-testid="stButton"] > button,
        div[data-testid="stFormSubmitButton"] > button,
        table tbody tr {
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }
        div[data-testid="stMetric"]:hover,
        div[data-testid="stButton"] > button:hover,
        div[data-testid="stFormSubmitButton"] > button:hover {
            border-color: #2563eb;
            box-shadow: 0 4px 16px rgba(37, 99, 235, 0.25);
        }
        table tbody tr:hover {
            background: rgba(37, 99, 235, 0.2);
        }
        div[data-testid="stMetricLabel"],
        div[data-testid="stMetricValue"],
        div[data-testid="stExpander"] summary,
        div[data-testid="stForm"] label {
            color: #f8fafc;
        }
        .section-hdr, .onboarding-title-banner h2,
        div[data-testid="stBadge"] {
            color: #38bdf8;
        }
        @media (prefers-reduced-motion: reduce) {
            div[data-testid="stMetric"],
            div[data-testid="stButton"] > button,
            div[data-testid="stFormSubmitButton"] > button,
            table tbody tr {
                transition: none;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(
    page_title="NEXUSVAULT Sovereign Enterprise Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_production_security_css()


def _tenant_portal_url(
    portal: str,
    tenant_slug: str,
    intake_type: str | None = None,
) -> str:
    params = {"portal": portal, "tenant": tenant_slug}
    if intake_type is not None:
        params["type"] = intake_type
    return f"{PRODUCTION_BASE_URL}/?{urlencode(params)}"


_DEPARTMENTAL_SECTORS = (
    "Food / Consumables",
    "Engineering / Infrastructure",
    "Private Security",
    "IT & Software",
    "Other / Not specified",
)
_SECTOR_COMPLIANCE_CHECKS = {
    "NAFDAC": "Food / Consumables",
    "COREN": "Engineering / Infrastructure",
    "NSCDC": "Private Security",
    "NITDA": "IT & Software",
}

_query_params = st.query_params
_raw_portal = _query_params.get("portal")
_raw_tenant = _query_params.get("tenant")
_raw_intake_type = _query_params.get("type")
_LEGACY_ROUTING_KEYS = {"mode", "slug", "client", "view", "t"}
_TENANT_SLUG_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,62}\Z")
_ALLOWED_INTERNAL_ROLES = {
    "admin",
    "tenant_admin",
    "directorate_staff",
    "committee_member",
    "front_desk",
}
_TENANT_SESSION_PREFIX = "tenant:"
_TENANT_ACCESS_KEY_NAMES = {
    "staff": "NEXUSVAULT_TENANT_STAFF_ACCESS_KEY",
    "executive": "NEXUSVAULT_TENANT_EXEC_ACCESS_KEY",
}
_LEGACY_TENANT_SESSION_KEYS = {
    "active_tenant_slug",
    "verified_qr_pass",
    "vendor_email",
    "tracking_id",
    "payment_verified",
    "tender_submitted",
    "is_admin_authenticated",
    "admin_authenticated",
    "staff_authenticated",
}
_TENANT_SCOPED_AUTH_KEYS = {
    "tenant_staff_auth",
    "tenant_staff_auth_slug",
    "tenant_exec_auth",
    "tenant_exec_auth_slug",
    "committee_authenticated",
    "committee_payload",
}
_IDLE_SESSION_TIMEOUT_SECONDS = 15 * 60
_SESSION_ACTIVITY_KEY = "last_activity"
_SECURITY_SESSION_ID_KEY = "security_session_id"
_SESSION_EXPIRY_NOTICE = (
    "Session expired due to 15 minutes of inactivity. Re-authentication required."
)


def _security_session_identifier() -> str:
    session_id = st.session_state.get(_SECURITY_SESSION_ID_KEY)
    if not isinstance(session_id, str) or not session_id:
        session_id = uuid.uuid4().hex
        st.session_state[_SECURITY_SESSION_ID_KEY] = session_id
    return f"session:{session_id}"


def _authenticated_actor_context() -> tuple[str, str] | None:
    if st.session_state.get("dev_authenticated") is True:
        return "platform", "platform_admin"

    for key in list(st.session_state.keys()):
        if not isinstance(key, str) or not key.endswith(":identity"):
            continue
        identity = st.session_state.get(key)
        if not isinstance(identity, Mapping):
            continue
        tenant_slug = identity.get("tenant_slug")
        role = identity.get("user_role") or identity.get("role")
        if not isinstance(role, str):
            surface = key.split(":")[-2] if ":" in key else ""
            role = {
                "committee": "committee_member",
                "front_desk": "front_desk",
                "admin": "admin",
            }.get(surface)
        if isinstance(tenant_slug, str) and isinstance(role, str):
            return tenant_slug, role

    tenant_slug = st.session_state.get("tenant_exec_auth_slug")
    if st.session_state.get("tenant_exec_auth") is True and isinstance(
        tenant_slug, str
    ):
        return tenant_slug, "executive"
    tenant_slug = st.session_state.get("tenant_staff_auth_slug")
    if st.session_state.get("tenant_staff_auth") is True and isinstance(
        tenant_slug, str
    ):
        return tenant_slug, "staff"
    return None


def _expire_idle_session(now: float | None = None) -> bool:
    current_time = time.time() if now is None else now
    last_activity = st.session_state.get(
        _SESSION_ACTIVITY_KEY, st.session_state.get("last_activity_timestamp")
    )
    if not isinstance(last_activity, (int, float)):
        return False
    if current_time - float(last_activity) <= _IDLE_SESSION_TIMEOUT_SECONDS:
        return False

    actor = _authenticated_actor_context()
    session_id = _security_session_identifier()
    if actor is not None:
        tenant_slug, role = actor
        try:
            db.log_security_audit_event(
                tenant_slug,
                role,
                "SESSION_EXPIRED",
                {"reason": "idle_timeout"},
                session_id,
            )
        except Exception:
            logging.exception("Could not record an idle session expiration.")

    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state[_SESSION_ACTIVITY_KEY] = current_time
    st.session_state[_SECURITY_SESSION_ID_KEY] = uuid.uuid4().hex
    st.session_state["session_expired_msg"] = _SESSION_EXPIRY_NOTICE
    return True


def _guard_session_interaction() -> bool:
    return not _expire_idle_session()


def _touch_session_activity() -> bool:
    now = time.time()
    expired = _expire_idle_session(now)
    st.session_state[_SESSION_ACTIVITY_KEY] = now
    _security_session_identifier()
    return expired


def _session_idle_timeout_monitor() -> None:
    if _expire_idle_session():
        st.rerun()


_SESSION_EXPIRED_THIS_RUN = _touch_session_activity()
if _SESSION_EXPIRED_THIS_RUN:
    st.rerun()
if not hasattr(st, "fragment"):
    st.error("Session security requires Streamlit 1.37 or newer.")
    st.stop()
st.fragment(run_every="1s")(_session_idle_timeout_monitor)()


def _single_query_value(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise ValueError(f"Query parameter {name!r} must appear only once.")
        value = value[0]
    if not isinstance(value, str):
        raise ValueError(f"Query parameter {name!r} must be text.")
    normalized = value.strip()
    return normalized or None


def _parse_route() -> tuple[str, str | None, str | None]:
    if _LEGACY_ROUTING_KEYS.intersection(_query_params.keys()):
        raise ValueError(
            "Legacy routing parameters are not supported. Use the canonical portal URL."
        )

    portal = _single_query_value(_raw_portal, "portal")
    tenant_slug = _single_query_value(_raw_tenant, "tenant")
    intake_type = _single_query_value(_raw_intake_type, "type")

    if portal is None and tenant_slug is None and intake_type is None:
        return "home", None, None
    if portal is None:
        raise ValueError("A portal parameter is required.")

    portal = portal.lower()
    if portal == "vendor":
        if tenant_slug is None:
            raise ValueError("Vendor links must include portal=vendor and tenant.")
        if intake_type is not None:
            intake_type = intake_type.lower()
            if intake_type not in {"solicited", "unsolicited"}:
                raise ValueError("Vendor type must be solicited or unsolicited.")
    elif portal in {"internal", "frontdesk", "admin"}:
        if tenant_slug is None:
            raise ValueError("Tenant portal links must include a tenant.")
        if intake_type is not None:
            raise ValueError("Tenant portals do not accept a vendor type.")
    else:
        raise ValueError(
            "Unsupported portal. Use portal=vendor, internal, frontdesk, or admin."
        )

    tenant_slug = tenant_slug.lower()
    if not _TENANT_SLUG_PATTERN.fullmatch(tenant_slug):
        raise ValueError("The tenant identifier is invalid.")

    return portal, tenant_slug, intake_type


def _tenant_key(tenant_slug: str, surface: str, name: str) -> str:
    return f"{_TENANT_SESSION_PREFIX}{tenant_slug}:{surface}:{name}"


def _sync_tenant_session(
    tenant_slug: str | None,
    portal: str | None,
) -> None:
    previous_slug = st.session_state.get("_active_tenant_slug")
    previous_portal = st.session_state.get("_active_tenant_portal")
    has_active_tenant = "_active_tenant_slug" in st.session_state
    if has_active_tenant and previous_slug == tenant_slug and previous_portal == portal:
        for key in _LEGACY_TENANT_SESSION_KEYS:
            st.session_state.pop(key, None)
        return

    for key in list(st.session_state.keys()):
        if (
            isinstance(key, str) and key.startswith(_TENANT_SESSION_PREFIX)
        ) or key in _LEGACY_TENANT_SESSION_KEYS | _TENANT_SCOPED_AUTH_KEYS:
            del st.session_state[key]

    st.session_state["_active_tenant_slug"] = tenant_slug
    st.session_state["_active_tenant_portal"] = portal


def _configured_staff_users() -> dict[str, Any]:
    raw_users = os.environ.get("NEXUSVAULT_STAFF_USERS_JSON")
    if raw_users:
        try:
            users = json.loads(raw_users)
        except json.JSONDecodeError:
            logging.exception("NEXUSVAULT_STAFF_USERS_JSON is not valid JSON.")
            return {}
    else:
        try:
            users = st.secrets.get("NEXUSVAULT_STAFF_USERS", {})
        except (KeyError, StreamlitSecretNotFoundError):
            return {}

    if not isinstance(users, Mapping):
        logging.error("Configured staff users must be a mapping.")
        return {}
    return dict(users)


def _configured_developer_password() -> str | None:
    password = os.environ.get("NEXUSVAULT_DEVELOPER_GRANT_PASSWORD")
    if isinstance(password, str) and password.strip():
        return password.strip()
    try:
        password = st.secrets.get("NEXUSVAULT_DEVELOPER_GRANT_PASSWORD")
    except (KeyError, StreamlitSecretNotFoundError):
        return ""
    return password.strip() if isinstance(password, str) and password.strip() else ""


def _handle_developer_login() -> None:
    if not _guard_session_interaction():
        return
    submitted_password = str(st.session_state.get("dev_password_input", "")).strip()
    st.session_state["dev_password_input"] = ""
    configured_password = _configured_developer_password()
    authenticated = bool(
        submitted_password and configured_password
    ) and hmac.compare_digest(
        submitted_password.encode("utf-8"), configured_password.encode("utf-8")
    )
    try:
        db.log_security_audit_event(
            "platform",
            "platform_admin",
            "LOGIN_SUCCESS" if authenticated else "LOGIN_FAILED",
            {"authentication_method": "developer_password"},
            _security_session_identifier(),
        )
    except Exception:
        logging.exception("Could not record a developer login attempt.")
        st.session_state.pop("dev_authenticated", None)
        st.session_state["dev_login_feedback"] = "audit_error"
        return
    if authenticated:
        st.session_state["dev_authenticated"] = True
        st.session_state["dev_login_feedback"] = "success"
    else:
        st.session_state.pop("dev_authenticated", None)
        st.session_state["dev_login_feedback"] = "invalid"


def _configured_tenant_access_key(tier: str) -> str | None:
    secret_name = _TENANT_ACCESS_KEY_NAMES.get(tier)
    if secret_name is None:
        raise ValueError("Unsupported tenant access tier.")

    password = os.environ.get(secret_name)
    if isinstance(password, str) and password.strip():
        return password.strip()

    try:
        password = st.secrets.get(secret_name)
    except (KeyError, StreamlitSecretNotFoundError):
        return None
    return password.strip() if isinstance(password, str) and password.strip() else None


def _tenant_access_is_authenticated(tier: str, tenant_slug: str) -> bool:
    flag_key = "tenant_staff_auth" if tier == "staff" else "tenant_exec_auth"
    scope_key = f"{flag_key}_slug"
    return (
        st.session_state.get(flag_key) is True
        and st.session_state.get(scope_key) == tenant_slug
    )


def _handle_tenant_access_login(tenant_slug: str, tier: str) -> None:
    if not _guard_session_interaction():
        return
    flag_key = "tenant_staff_auth" if tier == "staff" else "tenant_exec_auth"
    scope_key = f"{flag_key}_slug"
    password_key = _tenant_key(tenant_slug, "internal", f"{tier}_access_key")
    error_key = _tenant_key(tenant_slug, "internal", f"{tier}_access_error")
    supplied_password = st.session_state.get(password_key, "")
    supplied_password = (
        supplied_password.strip() if isinstance(supplied_password, str) else ""
    )
    st.session_state[password_key] = ""

    expected_password = _configured_tenant_access_key(tier)
    if not expected_password:
        st.session_state.pop(flag_key, None)
        st.session_state.pop(scope_key, None)
        st.session_state[error_key] = "This access tier is not configured."
        return

    authenticated = bool(supplied_password) and hmac.compare_digest(
        supplied_password,
        expected_password,
    )
    try:
        db.log_tenant_access_attempt(tenant_slug, tier, authenticated)
        db.log_tenant_activity(
            tenant_slug,
            "tenant_access_key",
            f"{tier}_access_key_{'accepted' if authenticated else 'rejected'}",
            f"{tier.title()} access-key authentication attempt.",
        )
        db.log_security_audit_event(
            tenant_slug,
            f"{tier}_access",
            "LOGIN_SUCCESS" if authenticated else "LOGIN_FAILED",
            {"access_tier": tier},
            _security_session_identifier(),
        )
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception(
            "Could not record %s access attempt for tenant %s.",
            tier,
            tenant_slug,
        )
        st.session_state.pop(flag_key, None)
        st.session_state.pop(scope_key, None)
        st.session_state[error_key] = (
            "Access could not be verified and recorded. Please try again."
        )
        return

    if authenticated:
        st.session_state[flag_key] = True
        st.session_state[scope_key] = tenant_slug
        st.session_state.pop(error_key, None)
    else:
        st.session_state.pop(flag_key, None)
        st.session_state.pop(scope_key, None)
        st.session_state[error_key] = "The access key is incorrect."


def _render_tenant_access_gate(tenant_slug: str, tier: str) -> bool:
    if _tenant_access_is_authenticated(tier, tenant_slug):
        return True

    labels = {
        "staff": "Desk Officer / Staff Access",
        "executive": "Executive / Management Access",
    }
    label = labels[tier]
    if _configured_tenant_access_key(tier) is None:
        st.error(
            f"{label} is unavailable. Configure "
            f"{_TENANT_ACCESS_KEY_NAMES[tier]} in the deployment environment "
            "or Streamlit secrets."
        )
        return False

    st.subheader(label)
    st.caption("Enter the access key assigned to this tenant access tier.")
    password_key = _tenant_key(tenant_slug, "internal", f"{tier}_access_key")
    error_key = _tenant_key(tenant_slug, "internal", f"{tier}_access_error")
    with st.form(key=_tenant_key(tenant_slug, "internal", f"{tier}_access_form")):
        st.text_input("Access key", type="password", key=password_key)
        st.form_submit_button(
            "Unlock",
            key=_tenant_key(tenant_slug, "internal", f"{tier}_access_submit"),
            on_click=_handle_tenant_access_login,
            args=(tenant_slug, tier),
            type="primary",
        )

    error_message = st.session_state.get(error_key)
    if isinstance(error_message, str) and error_message:
        st.error(error_message)
    return False


def _verify_password(password: str, encoded_hash: Any) -> bool:
    if not isinstance(encoded_hash, str):
        return False
    try:
        algorithm, iterations_text, salt_hex, digest_hex = encoded_hash.split("$", 3)
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_hex)
        expected_digest = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False

    if (
        algorithm != "pbkdf2_sha256"
        or not 100_000 <= iterations <= 2_000_000
        or len(salt) < 16
        or len(expected_digest) != hashlib.sha256().digest_size
    ):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
        dklen=len(expected_digest),
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def _authenticate_internal_user(
    tenant_slug: str,
    username: str,
    password: str,
) -> dict[str, str] | None:
    normalized_username = username.strip().lower()
    normalized_password = password.strip()
    if not normalized_username or not normalized_password:
        return None

    users = _configured_staff_users()
    account = users.get(normalized_username)
    if not isinstance(account, Mapping):
        return None

    configured_tenant = account.get("tenant_slug")
    role = account.get("role")
    password_hash = account.get("password_hash")
    if (
        not isinstance(configured_tenant, str)
        or configured_tenant.strip().lower() != tenant_slug
        or not isinstance(role, str)
        or role.strip().lower() not in _ALLOWED_INTERNAL_ROLES
        or not _verify_password(normalized_password, password_hash)
    ):
        return None

    return {
        "username": normalized_username,
        "role": role.strip().lower(),
        "tenant_slug": tenant_slug,
        "directorate": str(
            account.get("directorate") or account.get("department") or ""
        ).strip(),
    }


def _handle_internal_login(tenant_slug: str) -> None:
    if not _guard_session_interaction():
        return
    username_key = _tenant_key(tenant_slug, "internal", "username")
    password_key = _tenant_key(tenant_slug, "internal", "password")
    identity_key = _tenant_key(tenant_slug, "internal", "identity")
    failed_key = _tenant_key(tenant_slug, "internal", "login_failed")

    identity = _authenticate_internal_user(
        tenant_slug,
        str(st.session_state.get(username_key, "")),
        str(st.session_state.get(password_key, "")).strip(),
    )
    st.session_state[password_key] = ""
    try:
        db.log_security_audit_event(
            tenant_slug,
            identity["role"] if identity is not None else "internal",
            "LOGIN_SUCCESS" if identity is not None else "LOGIN_FAILED",
            {"authentication_method": "staff_account"},
            _security_session_identifier(),
        )
    except (sqlite3.Error, RuntimeError, TypeError, ValueError):
        logging.exception("Could not record an internal login attempt.")
        st.session_state[failed_key] = True
        st.session_state.pop(identity_key, None)
        return
    if identity is None:
        st.session_state[failed_key] = True
        st.session_state.pop(identity_key, None)
        return

    st.session_state[failed_key] = False
    st.session_state[identity_key] = identity


_TERMINAL_LOCKOUT_MESSAGE = (
    "⚠️ TERMINAL LOCKED: 3 consecutive failed authentication attempts detected. "
    "Access is suspended until credentials are reset by the Master Administrator "
    "or IT Officer."
)


def _handle_terminal_role_login(tenant_slug: str, role: str) -> None:
    if not _guard_session_interaction():
        return
    username_key = _tenant_key(tenant_slug, role, "username")
    passkey_key = _tenant_key(tenant_slug, role, "passkey")
    identity_key = _tenant_key(tenant_slug, role, "identity")
    error_key = _tenant_key(tenant_slug, role, "login_error")
    supplied_username = str(st.session_state.get(username_key, ""))
    supplied_passkey = str(st.session_state.get(passkey_key, ""))
    st.session_state[passkey_key] = ""

    try:
        lockout = db.get_tenant_role_lockout(tenant_slug, role)
        if lockout["is_locked_out"]:
            st.session_state.pop(identity_key, None)
            st.session_state[error_key] = _TERMINAL_LOCKOUT_MESSAGE
            return

        identity = _authenticate_internal_user(
            tenant_slug,
            supplied_username,
            supplied_passkey,
        )
        if identity is None or identity["role"] != role:
            lockout = db.record_tenant_role_login_failure(
                tenant_slug,
                role,
                _security_session_identifier(),
            )
            st.session_state.pop(identity_key, None)
            st.session_state[error_key] = (
                _TERMINAL_LOCKOUT_MESSAGE
                if lockout["is_locked_out"]
                else "The username or passkey is incorrect for this access role."
            )
            return

        if not db.record_tenant_role_login_success(
            tenant_slug,
            role,
            _security_session_identifier(),
        ):
            st.session_state.pop(identity_key, None)
            st.session_state[error_key] = _TERMINAL_LOCKOUT_MESSAGE
            return
    except (sqlite3.Error, RuntimeError, TypeError, ValueError):
        logging.exception(
            "Could not verify %s credentials for tenant %s.",
            role,
            tenant_slug,
        )
        st.session_state.pop(identity_key, None)
        st.session_state[error_key] = (
            "Authentication could not be verified securely. Please try again."
        )
        return

    identity["user_role"] = role
    st.session_state[identity_key] = identity
    st.session_state.pop(error_key, None)


def _handle_terminal_lockout_reset(tenant_slug: str, role: str) -> None:
    if not _guard_session_interaction():
        return
    import sector_logic

    reset_key_name = _tenant_key(tenant_slug, role, "reset_key")
    result_key = _tenant_key(tenant_slug, role, "reset_result")
    supplied_key = st.session_state.get(reset_key_name, "")
    st.session_state[reset_key_name] = ""

    if not sector_logic.terminal_reset_key_is_configured():
        st.session_state[result_key] = "unconfigured"
        return
    if not sector_logic.verify_terminal_reset_key(supplied_key):
        try:
            db.log_security_audit_event(
                tenant_slug,
                "master_admin",
                "TERMINAL_RESET_REJECTED",
                {"role": role},
                _security_session_identifier(),
            )
        except (sqlite3.Error, RuntimeError, TypeError, ValueError):
            logging.exception(
                "Could not record a rejected %s terminal reset request.",
                role,
            )
        st.session_state[result_key] = "rejected"
        return

    try:
        db.reset_tenant_role_login_lockout(
            tenant_slug,
            role,
            "master_admin_recovery_key",
            _security_session_identifier(),
        )
    except (sqlite3.Error, RuntimeError, TypeError, ValueError):
        logging.exception(
            "Could not reset the %s terminal lockout for tenant %s.",
            role,
            tenant_slug,
        )
        st.session_state[result_key] = "error"
        return

    st.session_state.pop(_tenant_key(tenant_slug, role, "identity"), None)
    st.session_state.pop(_tenant_key(tenant_slug, role, "login_error"), None)
    st.session_state[result_key] = "accepted"


def _render_terminal_lockout_alert(tenant_slug: str, role: str) -> None:
    import sector_logic

    st.markdown(
        """
        <div style="background:#3b0a0a;border:2px solid #ef4444;border-left:8px solid #facc15;
                    border-radius:12px;color:#fff;padding:1.1rem 1.25rem;
                    font-weight:800;line-height:1.55;margin:1rem 0;">
            ⚠️ TERMINAL LOCKED: 3 consecutive failed authentication attempts detected.
            Access is suspended until credentials are reset by the Master Administrator
            or IT Officer.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("**Request IT / Admin Reset**")
    st.caption(
        "Enter the configured master recovery key. The reset is tenant- and "
        "role-scoped and written to the security audit trail."
    )
    configured = sector_logic.terminal_reset_key_is_configured()
    if not configured:
        st.error(
            "Lockout recovery is not configured. Set "
            "NEXUSVAULT_TERMINAL_RESET_KEY in the deployment environment or "
            "Streamlit secrets, then retry."
        )
    with st.form(key=_tenant_key(tenant_slug, role, "reset_form")):
        st.text_input(
            "Master recovery key",
            type="password",
            key=_tenant_key(tenant_slug, role, "reset_key"),
            disabled=not configured,
        )
        st.form_submit_button(
            "Request IT / Admin Reset",
            key=_tenant_key(tenant_slug, role, "reset_submit"),
            on_click=_handle_terminal_lockout_reset,
            args=(tenant_slug, role),
            disabled=not configured,
            type="primary",
        )

    result_key = _tenant_key(tenant_slug, role, "reset_result")
    result = st.session_state.pop(result_key, None)
    if result == "accepted":
        st.success("The terminal lockout was reset. Sign in with your role account.")
        st.rerun()
    if result == "rejected":
        st.error("The recovery key was not accepted.")
    elif result == "error":
        st.error("The lockout could not be reset. Please contact IT.")
    elif result == "unconfigured":
        st.error("The master recovery key is not configured.")


def _render_terminal_role_login(
    tenant_slug: str,
    role: str,
) -> dict[str, str] | None:
    identity_key = _tenant_key(tenant_slug, role, "identity")
    error_key = _tenant_key(tenant_slug, role, "login_error")
    try:
        lockout = db.get_tenant_role_lockout(tenant_slug, role)
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception(
            "Could not load %s lockout state for tenant %s.",
            role,
            tenant_slug,
        )
        st.error("Authentication is unavailable because security state could not load.")
        return None

    if lockout["is_locked_out"]:
        st.session_state.pop(identity_key, None)
        _render_terminal_lockout_alert(tenant_slug, role)
        return None

    reset_result_key = _tenant_key(tenant_slug, role, "reset_result")
    if st.session_state.pop(reset_result_key, None) == "accepted":
        st.success("The terminal lockout was reset. Sign in with your role account.")

    identity = st.session_state.get(identity_key)
    if (
        isinstance(identity, Mapping)
        and identity.get("tenant_slug") == tenant_slug
        and identity.get("role") == role
        and identity.get("user_role") == role
    ):
        return dict(identity)

    users = _configured_staff_users()
    account_is_configured = any(
        isinstance(account, Mapping)
        and str(account.get("tenant_slug") or "").strip().lower() == tenant_slug
        and str(account.get("role") or "").strip().lower() == role
        for account in users.values()
    )
    if not account_is_configured:
        st.error(
            f"No {role.replace('_', ' ')} accounts are configured for this tenant."
        )
        return None

    labels = {
        "front_desk": "Front Desk Authentication",
        "admin": "Master Admin Authentication",
    }
    st.subheader(labels[role])
    st.caption("Sign in with the account assigned exclusively to this role.")
    with st.form(key=_tenant_key(tenant_slug, role, "login_form")):
        st.text_input(
            "Username",
            key=_tenant_key(tenant_slug, role, "username"),
        )
        st.text_input(
            "Passkey",
            type="password",
            key=_tenant_key(tenant_slug, role, "passkey"),
        )
        st.form_submit_button(
            "Authenticate",
            key=_tenant_key(tenant_slug, role, "login_submit"),
            on_click=_handle_terminal_role_login,
            args=(tenant_slug, role),
            type="primary",
        )

    error = st.session_state.pop(error_key, None)
    if isinstance(error, str) and error:
        if error == _TERMINAL_LOCKOUT_MESSAGE:
            _render_terminal_lockout_alert(tenant_slug, role)
        else:
            st.error(error)

    identity = st.session_state.get(identity_key)
    if (
        isinstance(identity, Mapping)
        and identity.get("tenant_slug") == tenant_slug
        and identity.get("role") == role
        and identity.get("user_role") == role
    ):
        return dict(identity)
    return None


def _render_frontdesk_portal(
    tenant: Mapping[str, Any],
    tenant_slug: str,
) -> None:
    identity = _render_terminal_role_login(tenant_slug, "front_desk")
    if identity is None:
        return

    st.success(f"Authenticated as {identity['username']} (Front Desk).")
    _render_physical_proposal_intake(
        tenant,
        tenant_slug,
        identity["username"],
    )
    if st.button(
        "Sign out of Front Desk",
        key=_tenant_key(tenant_slug, "front_desk", "logout"),
    ):
        st.session_state.pop(_tenant_key(tenant_slug, "front_desk", "identity"), None)
        st.rerun()


def _render_master_admin_portal(
    tenant: Mapping[str, Any],
    tenant_slug: str,
) -> None:
    identity = _render_terminal_role_login(tenant_slug, "admin")
    if identity is None:
        return

    st.success(f"Authenticated as {identity['username']} (Master Admin).")
    _render_internal_portal(tenant, tenant_slug)
    if st.button(
        "Sign out of Master Admin",
        key=_tenant_key(tenant_slug, "admin", "logout"),
    ):
        st.session_state.pop(_tenant_key(tenant_slug, "admin", "identity"), None)
        st.rerun()


def _persist_general_broadcast() -> None:
    message = str(st.session_state.get("developer_broadcast_message", ""))
    try:
        db.set_general_broadcast(message)
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception("Could not save the tenant administrator broadcast.")
        st.error("The broadcast could not be saved. Please try again.")


def _physical_document_encryption_key() -> bytes | None:
    value = os.environ.get("NEXUSVAULT_DOSSIER_ENCRYPTION_KEY", "").strip()
    if not value:
        try:
            value = st.secrets.get("NEXUSVAULT_DOSSIER_ENCRYPTION_KEY", "")
        except (KeyError, StreamlitSecretNotFoundError):
            return None
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        key = value.strip().encode("ascii")
        Fernet(key)
    except (UnicodeEncodeError, ValueError, TypeError):
        return None
    return key


def _tenant_directorate_nodes(tenant: Mapping[str, Any]) -> tuple[str, ...]:
    configured = tenant.get("sub_directorates_json")
    if isinstance(configured, str):
        try:
            configured = json.loads(configured)
        except json.JSONDecodeError:
            logging.warning(
                "Tenant %s has invalid sub-directorate configuration.",
                tenant.get("tenant_slug"),
            )
            configured = []
    names = list(_DIRECTORATE_NODES)
    if isinstance(configured, list):
        for item in configured:
            name = item.get("name") if isinstance(item, Mapping) else item
            if isinstance(name, str) and name.strip() and name.strip() not in names:
                names.append(name.strip())
    return tuple(names)


def _proposal_directorate(
    proposal: Mapping[str, Any],
    tenant: Mapping[str, Any],
) -> tuple[str, str]:
    saved_directorate = str(proposal.get("routed_directorate") or "").strip()
    if proposal.get("source_type") == "physical" and saved_directorate:
        return saved_directorate, "Persisted desk-officer routing recommendation."
    recommendation, basis = _recommend_proposal_directorate(
        str(proposal.get("proposal_title") or ""),
        tenant,
    )
    return recommendation, basis


def _masked_compliance_reference(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return ""
    return f"***{normalized[-4:]}" if len(normalized) > 4 else "***"


def _local_compliance_results(
    proposal: Mapping[str, Any],
    sector: str,
    references: Mapping[str, str],
) -> list[dict[str, str]]:
    universal_values = {
        "CAC": (
            str(proposal.get("cac_registration_number") or "").strip()
            or references.get("CAC", "").strip()
        ),
        "TIN": (
            str(proposal.get("tax_identification_number") or "").strip()
            or references.get("TIN", "").strip()
        ),
        "KYB": references.get("KYB", "").strip(),
        "EFCC": references.get("EFCC", "").strip(),
        "PenCom": references.get("PenCom", "").strip(),
    }
    results = []
    for check_name in ("CAC", "TIN", "KYB", "EFCC", "PenCom"):
        reference = universal_values[check_name]
        results.append(
            {
                "check_name": check_name,
                "verification_status": (
                    "PROVIDED_UNVERIFIED" if reference else "MISSING"
                ),
                "registry_source": "Local field-presence screening; no registry connector configured",
                "credential_reference": _masked_compliance_reference(reference),
                "result_details": (
                    "A credential or supporting reference is present; "
                    "the issuing registry has not been queried."
                    if reference
                    else "No credential or supporting reference was provided."
                ),
            }
        )

    for check_name, applicable_sector in _SECTOR_COMPLIANCE_CHECKS.items():
        if sector != applicable_sector:
            results.append(
                {
                    "check_name": check_name,
                    "verification_status": "NOT_APPLICABLE",
                    "registry_source": "Sector applicability rule",
                    "credential_reference": "",
                    "result_details": f"Proposal sector is {sector}.",
                }
            )
            continue
        reference = references.get(check_name, "").strip()
        results.append(
            {
                "check_name": check_name,
                "verification_status": (
                    "PROVIDED_UNVERIFIED" if reference else "MISSING"
                ),
                "registry_source": "Local field-presence screening; no registry connector configured",
                "credential_reference": _masked_compliance_reference(reference),
                "result_details": (
                    "A supporting reference is present; the sector registry "
                    "has not been queried."
                    if reference
                    else "This sector-specific credential was not provided."
                ),
            }
        )
    return results


def _configured_prembly_credentials() -> tuple[str | None, str | None]:
    api_key = (
        os.environ.get("PREMBLY_API_KEY") or os.environ.get("PREMBLY_SECRET_KEY") or ""
    ).strip()
    app_id = (os.environ.get("PREMBLY_APP_ID") or "").strip()
    if api_key and app_id:
        return api_key, app_id
    try:
        secrets = st.secrets
        api_key = (
            api_key
            or str(
                secrets.get("PREMBLY_API_KEY")
                or secrets.get("PREMBLY_SECRET_KEY")
                or ""
            ).strip()
        )
        app_id = app_id or str(secrets.get("PREMBLY_APP_ID") or "").strip()
    except (KeyError, StreamlitSecretNotFoundError):
        return None, None
    if not api_key:
        return None, None
    if not app_id:
        return None, None
    return api_key, app_id


def _run_statutory_compliance_screening(
    proposal: Mapping[str, Any],
    sector: str,
    references: Mapping[str, str],
) -> list[dict[str, str]]:
    checks = _local_compliance_results(proposal, sector, references)
    cac_reference = (
        str(proposal.get("cac_registration_number") or "").strip()
        or references.get("CAC", "").strip()
    )
    if not cac_reference:
        return checks

    api_key, app_id = _configured_prembly_credentials()
    if not api_key or not app_id:
        return checks

    cac_check = next(check for check in checks if check["check_name"] == "CAC")

    def mark_cac_for_manual_review(details: str) -> None:
        cac_check.update(
            {
                "verification_status": "MANUAL_REVIEW",
                "registry_source": "Prembly CAC registry",
                "result_details": details,
            }
        )

    clean_reference = re.sub(r"^(?:RC|BN)\s*", "", cac_reference, flags=re.IGNORECASE)
    company_type = "BN" if cac_reference.strip().upper().startswith("BN") else "RC"
    try:
        response = requests.post(
            "https://api.prembly.com/identitypass/verification/cac",
            json={"rc_number": clean_reference, "company_type": company_type},
            headers={
                "x-api-key": api_key,
                "app-id": app_id,
                "Content-Type": "application/json",
            },
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        logging.warning(
            "Prembly CAC verification was unavailable for proposal %s.",
            proposal.get("tracking_id"),
        )
        mark_cac_for_manual_review(
            "Prembly CAC lookup was unavailable; confirm this reference manually."
        )
        return checks
    if not isinstance(payload, Mapping):
        mark_cac_for_manual_review(
            "Prembly returned an unreadable response; confirm this reference manually."
        )
        return checks

    if payload.get("status") is not True:
        mark_cac_for_manual_review(
            "Prembly did not confirm a match; verify this reference with the "
            "issuing authority."
        )
        return checks

    data = payload.get("data")
    if not isinstance(data, Mapping):
        mark_cac_for_manual_review(
            "Prembly returned no entity details; confirm this reference manually."
        )
        return checks
    company_status = str(data.get("company_status") or "UNKNOWN").strip().upper()
    verification_status = (
        "VERIFIED"
        if company_status == "ACTIVE"
        else (
            "FAILED"
            if company_status in {"INACTIVE", "DORMANT", "DISSOLVED", "CANCELLED"}
            else "MANUAL_REVIEW"
        )
    )
    cac_check.update(
        {
            "verification_status": verification_status,
            "registry_source": "Prembly CAC registry",
            "result_details": (f"Prembly returned company status {company_status}."),
        }
    )
    registry_tin = data.get(
        "tax_identification_number",
        data.get("tin"),
    )
    if isinstance(registry_tin, str) and registry_tin.strip():
        tin_check = next(check for check in checks if check["check_name"] == "TIN")
        if registry_tin.strip().casefold() not in {
            "not listed on registry",
            "not verified",
            "unverified",
            "n/a",
            "none",
        }:
            tin_check.update(
                {
                    "verification_status": "VERIFIED",
                    "registry_source": "Prembly CAC registry",
                    "credential_reference": _masked_compliance_reference(registry_tin),
                    "result_details": "Prembly returned a TIN for the matched entity.",
                }
            )
    return checks


def _generate_departmental_executive_summary(
    proposal: Mapping[str, Any],
    directorate: str,
    sector: str,
    appraisal_notes: str,
    checks: list[Mapping[str, Any]],
) -> str:
    present = sum(
        check.get("verification_status") == "PROVIDED_UNVERIFIED" for check in checks
    )
    missing = sum(check.get("verification_status") == "MISSING" for check in checks)
    notes = appraisal_notes.strip()
    note_sentence = f" Directorate appraisal: {notes}" if notes else ""
    external_checks = sorted(
        {
            str(check.get("registry_source"))
            for check in checks
            if check.get("registry_source") == "Prembly CAC registry"
        }
    )
    registry_sentence = (
        "External registry lookups were attempted for "
        + ", ".join(external_checks)
        + "."
        if external_checks
        else "No external statutory registries were queried."
    )
    return (
        f"{proposal.get('organization_name') or 'The submitting organization'} "
        f"submitted “{proposal.get('proposal_title') or 'Untitled proposal'}” "
        f"({proposal.get('tracking_id')}) for review by {directorate}. "
        f"Sector: {sector}. The local screening recorded {present} credential "
        f"references as provided but unverified and {missing} as missing; no "
        f"local status should be treated as proof of compliance. "
        f"{registry_sentence}{note_sentence}"
    )


def _render_departmental_directorate_interface(
    tenant: Mapping[str, Any],
    tenant_slug: str,
    identity: Mapping[str, Any],
) -> None:
    role = str(identity.get("role") or "")
    admin_roles = {"admin", "tenant_admin"}
    if role not in admin_roles | {"directorate_staff"}:
        return

    st.divider()
    st.header("Departmental Evaluation & Statutory Compliance")
    st.caption(
        "Directorate access is restricted to this tenant. The screening runner "
        "checks submitted fields locally. If Prembly credentials are configured, "
        "only the CAC reference is sent for a CAC/TIN registry lookup; no proposal "
        "document or summary is sent. EFCC, PenCom, NAFDAC, COREN, NSCDC, and "
        "NITDA still require their own authorized registry integrations."
    )
    feedback_key = _tenant_key(
        tenant_slug,
        "internal",
        "departmental_review_feedback",
    )
    feedback = st.session_state.pop(feedback_key, None)
    if isinstance(feedback, tuple) and len(feedback) == 2:
        feedback_level, feedback_message = feedback
        if feedback_level == "success":
            st.success(feedback_message)
        elif feedback_level == "error":
            st.error(feedback_message)
    directorate_nodes = _tenant_directorate_nodes(tenant)
    if role in admin_roles:
        directorate = st.selectbox(
            "Directorate review node",
            options=directorate_nodes,
            key=_tenant_key(tenant_slug, "internal", "departmental_directorate"),
        )
    else:
        directorate = str(identity.get("directorate") or "").strip()
        if not directorate:
            st.error(
                "This directorate account has no assigned directorate. Configure "
                "the account's directorate field before opening departmental review."
            )
            return
        if directorate not in directorate_nodes:
            st.error(
                "This account's assigned directorate is not configured for this tenant."
            )
            return
        st.info(f"Assigned directorate: **{directorate}**")

    try:
        proposals = db.get_tenant_governance_proposals(tenant_slug)
        routed_proposals = []
        for proposal in proposals:
            proposal_route, routing_basis = _proposal_directorate(proposal, tenant)
            proposal_with_route = dict(proposal)
            proposal_with_route["routed_directorate"] = proposal_route
            proposal_with_route["routing_basis"] = routing_basis
            db.save_departmental_review_dossier(
                tenant_slug=tenant_slug,
                tracking_id=str(proposal["tracking_id"]),
                source_type=str(proposal["source_type"]),
                organization_name=str(proposal["organization_name"]),
                proposal_title=str(proposal["proposal_title"]),
                routed_directorate=proposal_route,
                submitted_at=str(proposal.get("submitted_at") or ""),
            )
            if proposal_route == directorate:
                routed_proposals.append(proposal_with_route)
        queue = db.get_departmental_review_queue(tenant_slug, directorate)
    except (sqlite3.Error, RuntimeError, TypeError, ValueError):
        logging.exception(
            "Could not load departmental queue for %s / %s.",
            tenant_slug,
            directorate,
        )
        st.error("The departmental proposal queue could not be loaded.")
        return

    st.subheader(f"Incoming proposals · {directorate}")
    if not routed_proposals:
        st.info("No proposals are currently routed to this directorate.")
        return
    proposals_by_id = {
        str(proposal["tracking_id"]): proposal for proposal in routed_proposals
    }
    queue_by_id = {str(item["tracking_id"]): item for item in queue}
    proposal_ids = list(proposals_by_id)
    selected_id = st.selectbox(
        "Select a proposal dossier",
        options=proposal_ids,
        format_func=lambda tracking_id: (
            f"{proposals_by_id[tracking_id]['proposal_title']} · "
            f"{proposals_by_id[tracking_id]['organization_name']} · "
            f"{tracking_id}"
        ),
        key=_tenant_key(tenant_slug, "internal", f"departmental_select_{directorate}"),
    )
    proposal = proposals_by_id[selected_id]
    review_record = queue_by_id.get(selected_id, {})
    st.write("Source:", str(proposal.get("source_type") or "").title())
    st.write("Organization:", proposal["organization_name"])
    st.write("Proposal:", proposal["proposal_title"])
    st.write("Tracking ID:", proposal["tracking_id"])
    st.write("Routing basis:", proposal["routing_basis"])
    if proposal.get("cac_registration_number"):
        st.write(
            "CAC reference:",
            _masked_compliance_reference(str(proposal["cac_registration_number"])),
        )
    if proposal.get("tax_identification_number"):
        st.write(
            "TIN reference:",
            _masked_compliance_reference(str(proposal["tax_identification_number"])),
        )

    inferred_sector = "Other / Not specified"
    title_lower = str(proposal["proposal_title"]).casefold()
    if any(term in title_lower for term in ("food", "consumable", "medicine", "drug")):
        inferred_sector = "Food / Consumables"
    elif any(
        term in title_lower
        for term in ("engineering", "construction", "bridge", "road", "infrastructure")
    ):
        inferred_sector = "Engineering / Infrastructure"
    elif any(term in title_lower for term in ("security", "guard", "surveillance")):
        inferred_sector = "Private Security"
    elif any(
        term in title_lower
        for term in ("software", "digital", "ict", "technology", "data")
    ):
        inferred_sector = "IT & Software"
    stored_sector = str(review_record.get("sector") or "")
    sector = st.selectbox(
        "Proposal sector for applicability rules",
        options=_DEPARTMENTAL_SECTORS,
        index=(
            _DEPARTMENTAL_SECTORS.index(stored_sector)
            if stored_sector in _DEPARTMENTAL_SECTORS
            else _DEPARTMENTAL_SECTORS.index(inferred_sector)
        ),
        key=_tenant_key(
            tenant_slug,
            "internal",
            f"departmental_sector_{selected_id}",
        ),
    )
    references: dict[str, str] = {}
    with st.expander("Optional registry identifiers / evidence references"):
        for check_name, label in (
            ("CAC", "CAC registration reference (if not supplied)"),
            ("TIN", "Tax identification number (if not supplied)"),
            ("KYB", "KYB / beneficial ownership evidence reference"),
            ("EFCC", "EFCC clearance reference"),
            ("PenCom", "PenCom compliance reference"),
            ("NAFDAC", "NAFDAC license/reference"),
            ("COREN", "COREN registration/reference"),
            ("NSCDC", "NSCDC license/reference"),
            ("NITDA", "NITDA registration/reference"),
        ):
            references[check_name] = st.text_input(
                label,
                max_chars=120,
                key=_tenant_key(
                    tenant_slug,
                    "internal",
                    f"compliance_{check_name}_{selected_id}",
                ),
            )
    if st.button(
        "One-Click Statutory Compliance Deep-Search",
        type="primary",
        key=_tenant_key(tenant_slug, "internal", f"screen_{selected_id}"),
    ):
        checks = _run_statutory_compliance_screening(
            proposal,
            sector,
            references,
        )
        try:
            db.save_statutory_compliance_checks(
                tenant_slug=tenant_slug,
                tracking_id=selected_id,
                directorate=directorate,
                sector=sector,
                checks=checks,
                checked_by=str(identity["username"]),
            )
        except (sqlite3.Error, RuntimeError, TypeError, ValueError):
            logging.exception(
                "Statutory screening failed for %s in %s.",
                selected_id,
                tenant_slug,
            )
            st.error("The statutory screening results could not be saved.")
        else:
            cac_check = next(check for check in checks if check["check_name"] == "CAC")
            screening_message = (
                "Prembly CAC lookup completed with status "
                f"{cac_check['verification_status']}; other registry states "
                "remain locally screened and unverified."
                if cac_check["registry_source"] == "Prembly CAC registry"
                else "Local credential-presence screening completed. External "
                "registry verification is still required."
            )
            st.session_state[feedback_key] = (
                "success",
                screening_message,
            )
            st.rerun()

    try:
        dossier = db.get_departmental_review_dossier(tenant_slug, selected_id)
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception("Could not load review details for %s.", selected_id)
        st.error("Compliance and appraisal details could not be loaded.")
        return
    if dossier is None:
        st.error("This proposal is no longer available in the tenant review queue.")
        return
    if dossier["compliance_checks"]:
        st.markdown("#### Statutory compliance matrix")
        status_labels = {
            "PROVIDED_UNVERIFIED": "🟢 Provided · unverified",
            "MISSING": "🔴 Missing",
            "NOT_APPLICABLE": "⚪ Not applicable",
            "VERIFIED": "🟢 Registry verified",
            "FAILED": "🔴 Registry check failed",
            "MANUAL_REVIEW": "🟡 Manual review required",
        }
        st.dataframe(
            [
                {
                    "Registry": check["check_name"],
                    "Status": status_labels.get(
                        check["verification_status"],
                        check["verification_status"],
                    ),
                    "Reference": check["credential_reference"] or "—",
                    "Result": check["result_details"],
                    "Checked at": check["checked_at"],
                }
                for check in dossier["compliance_checks"]
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "Green means a credential reference was supplied or externally "
            "verified as labeled; provided/unverified is not proof of compliance."
        )
    else:
        st.info("Run the screening action to create the compliance matrix.")

    st.markdown("#### Departmental appraisal & sign-off")
    notes_key = _tenant_key(tenant_slug, "internal", f"appraisal_notes_{selected_id}")
    summary_key = _tenant_key(
        tenant_slug, "internal", f"appraisal_summary_{selected_id}"
    )
    st.text_area(
        "Official departmental appraisal notes",
        value=str(dossier.get("appraisal_notes") or ""),
        max_chars=8_000,
        key=notes_key,
    )
    st.text_area(
        "Executive proposal summary",
        value=str(dossier.get("executive_summary") or ""),
        max_chars=4_000,
        key=summary_key,
        help="Generated locally from dossier fields and appraisal notes; no external AI service is called.",
    )
    if st.button(
        "Generate executive proposal summary",
        key=_tenant_key(tenant_slug, "internal", f"generate_summary_{selected_id}"),
    ):
        summary = _generate_departmental_executive_summary(
            proposal,
            directorate,
            sector,
            str(st.session_state.get(notes_key, "")),
            dossier["compliance_checks"],
        )
        st.session_state[summary_key] = summary
        st.rerun()

    def save_appraisal(status: str, push_to_apex: bool = False) -> bool:
        try:
            saved = db.save_departmental_appraisal(
                tenant_slug=tenant_slug,
                tracking_id=selected_id,
                directorate=directorate,
                appraiser=str(identity["username"]),
                appraisal_notes=str(st.session_state.get(notes_key, "")),
                executive_summary=str(st.session_state.get(summary_key, "")),
                signoff_status=status,
                push_to_apex=push_to_apex,
            )
        except (sqlite3.Error, RuntimeError, TypeError, ValueError) as exc:
            logging.exception(
                "Departmental appraisal save failed for %s.",
                selected_id,
            )
            st.error(f"The departmental appraisal could not be saved: {exc}")
            return False
        st.session_state[feedback_key] = (
            "success",
            f"Appraisal saved as {saved['signoff_status']}."
            + (" Pushed to Apex Command." if push_to_apex else ""),
        )
        return True

    save_col, approve_col, query_col, reject_col, apex_col = st.columns(5)
    if save_col.button(
        "Save pending",
        key=_tenant_key(tenant_slug, "internal", f"appraisal_pending_{selected_id}"),
    ):
        if save_appraisal("Pending"):
            st.rerun()
    if approve_col.button(
        "Approve",
        key=_tenant_key(tenant_slug, "internal", f"appraisal_approve_{selected_id}"),
    ):
        if save_appraisal("Approved"):
            st.rerun()
    if query_col.button(
        "Query",
        key=_tenant_key(tenant_slug, "internal", f"appraisal_query_{selected_id}"),
    ):
        if save_appraisal("Queried"):
            st.rerun()
    if reject_col.button(
        "Reject",
        key=_tenant_key(tenant_slug, "internal", f"appraisal_reject_{selected_id}"),
    ):
        if save_appraisal("Rejected"):
            st.rerun()
    if apex_col.button(
        "Push to Apex Command",
        type="primary",
        key=_tenant_key(tenant_slug, "internal", f"appraisal_apex_{selected_id}"),
    ):
        if save_appraisal(
            "Pending",
            push_to_apex=True,
        ):
            st.rerun()

    packet_lines = [
        "NEXUSVAULT — Departmental Proposal Dossier",
        f"Tenant: {tenant_slug}",
        f"Directorate: {directorate}",
        f"Tracking ID: {selected_id}",
        f"Source: {proposal.get('source_type')}",
        f"Organization: {proposal.get('organization_name')}",
        f"Proposal: {proposal.get('proposal_title')}",
        f"Submission date: {proposal.get('submission_date') or proposal.get('submitted_at') or 'Not recorded'}",
        f"Sector: {sector}",
        f"Appraisal status: {dossier.get('signoff_status') or 'Pending'}",
        "",
        "Statutory screening (local presence checks only; not registry verification):",
    ]
    packet_lines.extend(
        f"- {check['check_name']}: {check['verification_status']} — "
        f"{check['result_details']}"
        for check in dossier["compliance_checks"]
    )
    packet_lines.extend(
        [
            "",
            "Departmental appraisal:",
            str(dossier.get("appraisal_notes") or st.session_state.get(notes_key, "")),
            "",
            "Executive summary:",
            str(
                dossier.get("executive_summary")
                or st.session_state.get(summary_key, "")
            ),
        ]
    )
    st.download_button(
        "Download / Print Dossier Packet",
        data="\n".join(packet_lines),
        file_name=f"{selected_id}-departmental-dossier.txt",
        mime="text/plain",
        key=_tenant_key(tenant_slug, "internal", f"download_dossier_{selected_id}"),
    )
    st.caption(
        "Open the downloaded dossier packet and use your browser/OS print command."
    )
    if st.button(
        "Prepare original uploaded proposal document",
        key=_tenant_key(
            tenant_slug,
            "internal",
            f"prepare_source_document_{selected_id}",
        ),
    ):
        try:
            from sector_logic import get_departmental_proposal_document

            source_filename, source_bytes = get_departmental_proposal_document(
                tenant_slug,
                selected_id,
            )
        except (
            FileNotFoundError,
            InvalidToken,
            OSError,
            RuntimeError,
            sqlite3.Error,
            ValueError,
        ) as exc:
            logging.exception(
                "Could not prepare source proposal document %s.",
                selected_id,
            )
            st.error(f"The original proposal document is unavailable: {exc}")
        else:
            st.session_state[
                _tenant_key(
                    tenant_slug,
                    "internal",
                    f"source_document_{selected_id}",
                )
            ] = {
                "filename": source_filename,
                "bytes": source_bytes,
            }
            st.rerun()

    source_document = st.session_state.get(
        _tenant_key(
            tenant_slug,
            "internal",
            f"source_document_{selected_id}",
        )
    )
    if isinstance(source_document, Mapping):
        source_filename = str(source_document.get("filename") or "proposal")
        source_bytes = source_document.get("bytes")
        if isinstance(source_bytes, bytes):
            st.download_button(
                "Download original uploaded document",
                data=source_bytes,
                file_name=Path(source_filename).name,
                mime=(
                    "application/pdf"
                    if Path(source_filename).suffix.lower() == ".pdf"
                    else (
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        if Path(source_filename).suffix.lower() == ".docx"
                        else "application/octet-stream"
                    )
                ),
                key=_tenant_key(
                    tenant_slug,
                    "internal",
                    f"download_source_document_{selected_id}",
                ),
            )


def _validate_physical_proposal_document(filename: str, document_bytes: bytes) -> None:
    if not document_bytes:
        raise ValueError("The scanned proposal document is empty.")
    if len(document_bytes) > 25 * 1024 * 1024:
        raise ValueError("Scanned proposal documents must be 25 MB or smaller.")

    extension = Path(filename).suffix.lower()
    if extension == ".pdf":
        if not document_bytes.startswith(b"%PDF-"):
            raise ValueError("The uploaded file does not have a valid PDF signature.")
        return
    if extension not in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}:
        raise ValueError("Upload a PDF or supported image file.")

    try:
        with Image.open(BytesIO(document_bytes)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("The uploaded file is not a valid image.") from exc


_DIRECTORATE_SUBJECT_RULES = (
    (
        "Information and Communications Technology",
        (
            "ict",
            "technology",
            "digital",
            "software",
            "cybersecurity",
            "data",
            "network",
        ),
    ),
    (
        "Works and Infrastructure",
        (
            "construction",
            "building",
            "road",
            "infrastructure",
            "facility",
            "water",
            "power",
        ),
    ),
    (
        "Finance and Treasury",
        ("finance", "tax", "budget", "treasury", "payment", "accounting", "revenue"),
    ),
    (
        "Health and Social Services",
        ("health", "hospital", "medical", "clinic", "medicine", "public health"),
    ),
    (
        "Education and Research",
        ("education", "school", "university", "research", "training", "curriculum"),
    ),
    (
        "Agriculture and Environment",
        ("agriculture", "farming", "livestock", "environment", "climate", "forestry"),
    ),
    (
        "Procurement and Supply Chain",
        ("procurement", "tender", "supply", "purchase", "logistics", "contract"),
    ),
    (
        "Legal and Compliance",
        ("legal", "law", "compliance", "regulation", "policy", "statutory"),
    ),
    (
        "Security and Public Safety",
        ("security", "safety", "policing", "emergency", "defense", "surveillance"),
    ),
)
_DIRECTORATE_NODES = tuple(
    directorate for directorate, _ in _DIRECTORATE_SUBJECT_RULES
) + ("General Administration / Manual Review",)


def _recommend_proposal_directorate(
    proposal_title: str,
    tenant: Mapping[str, Any],
) -> tuple[str, str]:
    normalized_title = re.sub(r"[^a-z0-9]+", " ", proposal_title.casefold()).strip()
    matches = [
        (
            sum(keyword in normalized_title for keyword in keywords),
            directorate,
            keywords,
        )
        for directorate, keywords in _DIRECTORATE_SUBJECT_RULES
    ]
    match_count, directorate, keywords = max(matches, default=(0, "", ()))
    if match_count == 0:
        return (
            "General Administration / Manual Review",
            "No configured subject keyword matched; manual review is required.",
        )

    configured_departments = tenant.get("sub_directorates_json")
    if isinstance(configured_departments, str):
        try:
            configured_departments = json.loads(configured_departments)
        except json.JSONDecodeError:
            logging.warning(
                "Tenant %s has invalid sub-directorate configuration.",
                tenant.get("tenant_slug"),
            )
            configured_departments = []

    if isinstance(configured_departments, list):
        normalized_keywords = set(keywords)
        normalized_keywords.update(
            word for word in directorate.casefold().split() if len(word) > 3
        )
        configured_names = [
            item.get("name") if isinstance(item, Mapping) else item
            for item in configured_departments
        ]
        matching_departments = [
            name.strip()
            for name in configured_names
            if isinstance(name, str)
            and name.strip()
            and normalized_keywords.intersection(
                set(re.sub(r"[^a-z0-9]+", " ", name.casefold()).split())
            )
        ]
        if matching_departments:
            directorate = matching_departments[0]

    matched_terms = [keyword for keyword in keywords if keyword in normalized_title]
    return (
        directorate,
        "Local title-keyword match: " + ", ".join(matched_terms),
    )


def _render_physical_proposal_intake(
    tenant: Mapping[str, Any],
    tenant_slug: str,
    actor: str,
) -> None:
    st.subheader("Desk Officer Physical Proposal Intake")
    st.caption(
        "Scanned files are encrypted before storage. Directorate routing is a "
        "local keyword recommendation and should be reviewed by staff."
    )
    encryption_key = _physical_document_encryption_key()
    if encryption_key is None:
        st.error(
            "Physical proposal intake is unavailable. Configure a valid Fernet "
            "NEXUSVAULT_DOSSIER_ENCRYPTION_KEY."
        )
        return

    with st.form(
        key=_tenant_key(tenant_slug, "internal", "physical_proposal_form"),
        clear_on_submit=True,
    ):
        organization_name = st.text_input("Name of Organization", max_chars=200)
        organization_address = st.text_area(
            "Address of Organization",
            max_chars=1_000,
        )
        cac_registration_number = st.text_input(
            "CAC Registration Number",
            max_chars=100,
        )
        contact_phone = st.text_input("Contact Phone Number", max_chars=40)
        official_email = st.text_input("Official Email Address", max_chars=254)
        proposal_title = st.text_input("Proposal Title", max_chars=250)
        submission_date = st.date_input(
            "Date of Proposal Submission",
            value=date.today(),
            max_value=date.today(),
        )
        signature_verified = st.radio(
            "Signature Verification",
            options=["Yes", "No"],
            horizontal=True,
        )
        scanned_document = st.file_uploader(
            "Scanned Document Upload (PDF or image file)",
            type=["pdf", "png", "jpg", "jpeg", "tif", "tiff", "webp"],
            max_upload_size=25,
        )
        submitted = st.form_submit_button(
            "Submit Physical Proposal",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        organization_name = organization_name.strip()
        organization_address = organization_address.strip()
        cac_registration_number = cac_registration_number.strip()
        contact_phone = contact_phone.strip()
        official_email = official_email.strip()
        proposal_title = proposal_title.strip()
        _, parsed_email = parseaddr(official_email)
        if not all(
            (
                organization_name,
                organization_address,
                cac_registration_number,
                contact_phone,
                official_email,
                proposal_title,
            )
        ):
            st.error("Complete all required proposal intake fields.")
        elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", parsed_email):
            st.error("Enter a valid official email address.")
        elif scanned_document is None:
            st.error("Upload the scanned proposal document.")
        else:
            try:
                document_bytes = scanned_document.getvalue()
                _validate_physical_proposal_document(
                    scanned_document.name,
                    document_bytes,
                )
                route, routing_basis = _recommend_proposal_directorate(
                    proposal_title,
                    tenant,
                )
                proposal_data = {
                    "organization_name": organization_name,
                    "organization_address": organization_address,
                    "cac_registration_number": cac_registration_number,
                    "contact_phone": contact_phone,
                    "official_email": parsed_email,
                    "proposal_title": proposal_title,
                    "submission_date": submission_date.isoformat(),
                    "signature_verified": signature_verified == "Yes",
                }
                encrypted_document = Fernet(encryption_key).encrypt(document_bytes)
                result = db.create_physical_proposal(
                    tenant_slug=tenant_slug,
                    proposal_data=proposal_data,
                    document_bytes=document_bytes,
                    document_ciphertext=encrypted_document,
                    document_filename=scanned_document.name,
                    routed_directorate=route,
                    routing_basis=routing_basis,
                    submitted_by=actor,
                    actor_role="front_desk",
                    ip_or_session=_security_session_identifier(),
                )
            except (OSError, sqlite3.Error, RuntimeError, TypeError, ValueError) as exc:
                logging.exception(
                    "Physical proposal intake failed for tenant %s.",
                    tenant_slug,
                )
                st.error(f"The physical proposal could not be recorded: {exc}")
            else:
                st.session_state[
                    _tenant_key(tenant_slug, "internal", "last_physical_receipt")
                ] = result
                st.success("Proposal acknowledged and recorded successfully.")

    result = st.session_state.get(
        _tenant_key(tenant_slug, "internal", "last_physical_receipt")
    )
    if isinstance(result, Mapping):
        st.markdown("#### Intake receipt")
        st.write("Tracking ID:", result["tracking_id"])
        st.write("SHA-256 receipt:", result["receipt_hash"])
        st.write("Document SHA-256:", result["document_sha256"])
        st.write("Routing recommendation:", result["routed_directorate"])
        st.caption(result["routing_basis"])
        st.info(
            "Your proposal is acknowledged and due attention will be accorded "
            "for possible action. SMS and Email acknowledgments were simulated "
            "and queued in the notification outbox."
        )

    try:
        proposals = db.get_physical_proposals(tenant_slug)
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception("Could not load physical proposals for %s.", tenant_slug)
        st.warning("Previously received physical proposals could not be loaded.")
    else:
        if proposals:
            st.markdown("#### Recent physical submissions")
            st.dataframe(
                [
                    {
                        "Tracking ID": proposal["tracking_id"],
                        "Organization": proposal["organization_name"],
                        "Proposal": proposal["proposal_title"],
                        "Submitted": proposal["submitted_at"],
                        "Directorate": proposal["routed_directorate"],
                        "Receipt SHA-256": proposal["receipt_hash"],
                    }
                    for proposal in proposals
                ],
                use_container_width=True,
            )


def _valid_gateway_endpoint(value: str, label: str) -> str:
    normalized = value.strip()
    if normalized:
        parsed = urlparse(normalized)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError(
                f"{label} must be an HTTPS URL without embedded credentials."
            )
    return normalized


def _render_executive_gateway_tab(tenant_slug: str, actor: str) -> None:
    st.subheader("Tenant Payment Gateway Configuration")
    st.caption(
        "Configure tenant-specific payment instructions and choose the active "
        "collection mode. TSA/Remita endpoints are configuration only; live "
        "provider verification remains subject to the existing Paystack integration."
    )
    try:
        config = db.get_tenant_gateway_config(tenant_slug)
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception("Could not load gateway settings for %s.", tenant_slug)
        st.error("Gateway settings could not be loaded.")
        return

    config = config or {}
    tsa_default = str(config.get("tsa_endpoint") or "")
    remita_default = str(config.get("remita_endpoint") or "")
    service_head_default = str(
        config.get("service_head") or "Tender Fee/Bidding Document Fee"
    )
    fee_default = f"{Decimal(config.get('fee_amount_minor') or 0) / 100:.2f}"
    payment_modes = ("remita_tsa", "corporate_lodgment")
    configured_mode = str(config.get("payment_mode") or "corporate_lodgment")
    if configured_mode not in payment_modes:
        configured_mode = "corporate_lodgment"
    mode_key = _tenant_key(tenant_slug, "executive", "payment_mode")
    selected_mode = st.radio(
        "Active payment mode",
        options=payment_modes,
        index=payment_modes.index(configured_mode),
        format_func=lambda mode: (
            "Government TSA / Remita"
            if mode == "remita_tsa"
            else "Corporate bank lodgment"
        ),
        horizontal=True,
        key=mode_key,
    )
    st.caption(
        "The selected mode becomes active when either configuration tab is saved."
    )

    def save_config(
        *,
        tsa_endpoint: str,
        tsa_key: str,
        remita_endpoint: str,
        remita_key: str,
        service_head: str,
        fee_amount: str,
        corporate_bank_name: str,
        corporate_account_number: str,
        corporate_account_name: str,
        payment_reference_prefix: str,
        lodgment_instructions: str,
    ) -> None:
        try:
            tsa_url = _valid_gateway_endpoint(tsa_endpoint, "TSA endpoint")
            remita_url = _valid_gateway_endpoint(remita_endpoint, "Remita endpoint")
            fee_decimal = Decimal(fee_amount.strip())
            if not fee_decimal.is_finite() or fee_decimal < 0:
                raise ValueError("Fee amount must be a non-negative number.")
            if fee_decimal.as_tuple().exponent < -2:
                raise ValueError("Fee amount cannot have more than two decimal places.")
            fee_minor = int(fee_decimal * 100)
            encryption_key = _physical_document_encryption_key()
            if (tsa_key.strip() or remita_key.strip()) and encryption_key is None:
                raise ValueError(
                    "A valid NEXUSVAULT_DOSSIER_ENCRYPTION_KEY is required "
                    "to save gateway credentials."
                )
            fernet = Fernet(encryption_key) if encryption_key else None
            tsa_ciphertext = (
                fernet.encrypt(tsa_key.strip().encode("utf-8"))
                if fernet and tsa_key.strip()
                else None
            )
            remita_ciphertext = (
                fernet.encrypt(remita_key.strip().encode("utf-8"))
                if fernet and remita_key.strip()
                else None
            )
            db.save_tenant_gateway_config(
                tenant_slug=tenant_slug,
                tsa_endpoint=tsa_url,
                tsa_key_ciphertext=tsa_ciphertext,
                remita_endpoint=remita_url,
                remita_merchant_key_ciphertext=remita_ciphertext,
                service_head=service_head,
                fee_amount_minor=fee_minor,
                updated_by=actor,
                payment_mode=selected_mode,
                corporate_bank_name=corporate_bank_name,
                corporate_account_number=corporate_account_number,
                corporate_account_name=corporate_account_name,
                payment_reference_prefix=payment_reference_prefix,
                lodgment_instructions=lodgment_instructions,
            )
        except (
            InvalidOperation,
            sqlite3.Error,
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:
            logging.exception("Could not save gateway settings for %s.", tenant_slug)
            st.error(f"Gateway configuration was not saved: {exc}")
        else:
            st.success("Tenant gateway configuration saved.")
            st.session_state[
                _tenant_key(tenant_slug, "executive", "gateway_config_saved")
            ] = True
            st.rerun()

    tsa_tab, corporate_tab = st.tabs(
        [
            "🏛️ Government TSA & Remita Gateway",
            "🏢 Corporate & Institutional Bank Lodgment",
        ]
    )
    with tsa_tab:
        with st.form(
            key=_tenant_key(tenant_slug, "executive", "tsa_gateway_form"),
        ):
            tsa_endpoint = st.text_input(
                "TSA payment endpoint",
                value=tsa_default,
                key=_tenant_key(tenant_slug, "executive", "tsa_endpoint"),
            )
            tsa_key = st.text_input(
                "TSA key (leave blank to preserve saved key)",
                type="password",
                max_chars=512,
                key=_tenant_key(tenant_slug, "executive", "tsa_key_input"),
            )
            remita_endpoint = st.text_input(
                "Remita payment endpoint",
                value=remita_default,
                key=_tenant_key(tenant_slug, "executive", "remita_endpoint"),
            )
            remita_key = st.text_input(
                "Remita merchant key (leave blank to preserve saved key)",
                type="password",
                max_chars=512,
                key=_tenant_key(tenant_slug, "executive", "remita_merchant_key_input"),
            )
            service_head = st.text_input(
                "Service head",
                value=service_head_default,
                max_chars=160,
                key=_tenant_key(tenant_slug, "executive", "service_head"),
            )
            fee_amount = st.text_input(
                "Tender Fee/Bidding Document Fee (NGN)",
                value=fee_default,
                max_chars=24,
                key=_tenant_key(tenant_slug, "executive", "fee_amount"),
            )
            save_tsa = st.form_submit_button(
                "Save TSA / Remita configuration",
                type="primary",
            )
        if save_tsa:
            save_config(
                tsa_endpoint=tsa_endpoint,
                tsa_key=tsa_key,
                remita_endpoint=remita_endpoint,
                remita_key=remita_key,
                service_head=service_head,
                fee_amount=fee_amount,
                corporate_bank_name=str(config.get("corporate_bank_name") or ""),
                corporate_account_number=str(
                    config.get("corporate_account_number") or ""
                ),
                corporate_account_name=str(config.get("corporate_account_name") or ""),
                payment_reference_prefix=str(
                    config.get("payment_reference_prefix") or ""
                ),
                lodgment_instructions=str(config.get("lodgment_instructions") or ""),
            )

    with corporate_tab:
        with st.form(
            key=_tenant_key(tenant_slug, "executive", "corporate_gateway_form"),
        ):
            corporate_bank_name = st.text_input(
                "Bank Name",
                value=str(config.get("corporate_bank_name") or ""),
                max_chars=120,
                key=_tenant_key(tenant_slug, "executive", "corporate_bank_name"),
            )
            corporate_account_number = st.text_input(
                "Account Number",
                value=str(config.get("corporate_account_number") or ""),
                max_chars=34,
                key=_tenant_key(tenant_slug, "executive", "corporate_account_number"),
            )
            corporate_account_name = st.text_input(
                "Account Name",
                value=str(config.get("corporate_account_name") or ""),
                max_chars=160,
                key=_tenant_key(tenant_slug, "executive", "corporate_account_name"),
            )
            payment_reference_prefix = st.text_input(
                "Payment Reference Prefix",
                value=str(config.get("payment_reference_prefix") or ""),
                max_chars=40,
                key=_tenant_key(tenant_slug, "executive", "payment_reference_prefix"),
            )
            lodgment_instructions = st.text_area(
                "Transfer Instructions",
                value=str(config.get("lodgment_instructions") or ""),
                max_chars=2000,
                key=_tenant_key(tenant_slug, "executive", "lodgment_instructions"),
            )
            save_corporate = st.form_submit_button(
                "Save corporate lodgment configuration",
                type="primary",
            )
        if save_corporate:
            save_config(
                tsa_endpoint=tsa_default,
                tsa_key="",
                remita_endpoint=remita_default,
                remita_key="",
                service_head=service_head_default,
                fee_amount=fee_default,
                corporate_bank_name=corporate_bank_name,
                corporate_account_number=corporate_account_number,
                corporate_account_name=corporate_account_name,
                payment_reference_prefix=payment_reference_prefix,
                lodgment_instructions=lodgment_instructions,
            )

    if config:
        tsa_col, remita_col, fee_col = st.columns(3)
        tsa_col.metric(
            "TSA credential",
            "Configured" if config["tsa_key_configured"] else "Not configured",
        )
        remita_col.metric(
            "Remita credential",
            "Configured" if config["remita_key_configured"] else "Not configured",
        )
        fee_col.metric(
            "Configured fee",
            f"{config['currency']} {Decimal(config['fee_amount_minor']) / 100:.2f}",
        )
        st.caption(f"Last updated {config['updated_at']} by {config['updated_by']}.")


def _render_executive_financial_tab(tenant_slug: str) -> None:
    st.subheader("DFA Financial Reconciliation")
    st.caption(
        "Tenant-local payment reference ledger sourced from recorded clearance "
        "passes and provider verification events. Corporate bank references remain "
        "locked until an executive approves them; TSA/Remita configuration does "
        "not itself verify a payment."
    )
    try:
        ledger = db.get_tenant_financial_ledger(tenant_slug)
        config = db.get_tenant_gateway_config(tenant_slug)
        pending_lodgments = db.get_pending_corporate_lodgments(tenant_slug)
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception("Could not load financial ledger for %s.", tenant_slug)
        st.error("The financial ledger could not be loaded.")
        return

    verified = [row for row in ledger if row["amount_minor"] is not None]
    unmatched = [row for row in ledger if row not in verified]
    verified_col, unmatched_col, fee_col = st.columns(3)
    verified_col.metric("Provider-verified payments", len(verified))
    unmatched_col.metric("Missing verification / RRR match", len(unmatched))
    fee_col.metric(
        "Configured tender fee",
        (
            f"{config['currency']} {Decimal(config['fee_amount_minor']) / 100:.2f}"
            if config
            else "Not configured"
        ),
    )
    if ledger:
        st.dataframe(
            [
                {
                    "Pass ID": row["qr_pass_id"],
                    "RFQ / Tender": row["rfq_code"],
                    "Vendor": row["vendor_name"],
                    "Payment / RRR Reference": row["payment_reference"],
                    "Proposal": row["proposal_title"],
                    "Clearance Status": row["clearance_status"],
                    "Provider": row["provider"] or "Not verified",
                    "Verified Amount": (
                        f"{row['currency']} {Decimal(row['amount_minor']) / 100:.2f}"
                        if row["amount_minor"] is not None
                        else "Not recorded"
                    ),
                    "Vendor Fee Match": (
                        (
                            "Matched"
                            if row["currency"] == config["currency"]
                            and row["amount_minor"] == config["fee_amount_minor"]
                            else "Amount / currency mismatch"
                        )
                        if config and row["amount_minor"] is not None
                        else (
                            "Not configured"
                            if not config
                            else "No provider-verified amount"
                        )
                    ),
                    "Verified At": row["verified_at"] or "—",
                }
                for row in ledger
            ],
            use_container_width=True,
        )
    else:
        st.info("No payment-reference records exist for this tenant yet.")

    st.markdown("#### Corporate lodgment review queue")
    if not pending_lodgments:
        st.info("There are no corporate transfer references awaiting review.")
        return
    for lodgment in pending_lodgments:
        st.text(
            f"{lodgment['vendor_name']} · {lodgment['email']}\n"
            f"Reference: {lodgment['payment_reference']} · "
            f"Tender: {lodgment['rfq_code']}\n"
            f"Proposal: {lodgment['proposal_title']} · "
            f"Submitted: {lodgment['submitted_at']}"
        )
        approve_col, reject_col = st.columns(2)
        if approve_col.button(
            "Approve transfer",
            key=_tenant_key(
                tenant_slug,
                "executive",
                f"approve_lodgment_{lodgment['qr_pass_id']}",
            ),
            type="primary",
        ):
            try:
                resolved = db.resolve_corporate_lodgment(
                    tenant_slug,
                    lodgment["qr_pass_id"],
                    "APPROVE",
                    "tenant_executive",
                    _security_session_identifier(),
                )
            except (sqlite3.Error, RuntimeError, TypeError, ValueError) as exc:
                logging.exception(
                    "Could not approve corporate lodgment for %s.",
                    tenant_slug,
                )
                st.error(f"The transfer could not be approved: {exc}")
            else:
                if resolved:
                    st.success("Transfer approved and clearance pass activated.")
                    st.rerun()
                st.warning("This transfer was already resolved by another session.")
        if reject_col.button(
            "Reject transfer",
            key=_tenant_key(
                tenant_slug,
                "executive",
                f"reject_lodgment_{lodgment['qr_pass_id']}",
            ),
        ):
            try:
                resolved = db.resolve_corporate_lodgment(
                    tenant_slug,
                    lodgment["qr_pass_id"],
                    "REJECT",
                    "tenant_executive",
                    _security_session_identifier(),
                )
            except (sqlite3.Error, RuntimeError, TypeError, ValueError):
                logging.exception(
                    "Could not reject corporate lodgment for %s.",
                    tenant_slug,
                )
                st.error("The transfer could not be rejected.")
            else:
                if resolved:
                    st.success("Transfer rejected; its clearance pass remains locked.")
                    st.rerun()
                st.warning("This transfer was already resolved by another session.")
        st.divider()


def _render_executive_tenders_tab(tenant_slug: str, actor: str) -> None:
    st.subheader("Tender Publishing & Time-Locks")
    st.caption(
        "Published tenders with Auto-lock enabled are locked on the first dashboard "
        "load at or after their expiration timestamp. Countdown values refresh on "
        "dashboard reruns."
    )
    if st.button(
        "Refresh countdowns and expiration locks",
        key=_tenant_key(
            tenant_slug,
            "executive",
            "refresh_tender_countdowns",
        ),
    ):
        st.rerun()
    with st.form(
        key=_tenant_key(tenant_slug, "executive", "tender_form"),
        clear_on_submit=True,
    ):
        title = st.text_input(
            "Tender title",
            max_chars=250,
            key=_tenant_key(tenant_slug, "executive", "tender_title"),
        )
        description = st.text_area(
            "Tender description",
            max_chars=4_000,
            key=_tenant_key(tenant_slug, "executive", "tender_description"),
        )
        expiration = st.datetime_input(
            "Hard expiration date and time",
            value=datetime.now().astimezone() + timedelta(days=30),
            key=_tenant_key(tenant_slug, "executive", "tender_expiration"),
        )
        auto_lock = st.checkbox(
            "Automatically lock at expiration",
            value=True,
            key=_tenant_key(tenant_slug, "executive", "tender_auto_lock"),
        )
        publish_now = st.checkbox(
            "Publish immediately",
            value=False,
            key=_tenant_key(tenant_slug, "executive", "tender_publish_now"),
        )
        create_tender = st.form_submit_button(
            "Create solicited tender",
            type="primary",
        )

    if create_tender:
        try:
            if expiration.tzinfo is None:
                expiration = expiration.astimezone()
            tender = db.create_tenant_tender(
                tenant_slug=tenant_slug,
                title=title,
                description=description,
                expiration_at=expiration.isoformat(timespec="seconds"),
                auto_lock=auto_lock,
                created_by=actor,
                publish_now=publish_now,
            )
        except (sqlite3.Error, RuntimeError, TypeError, ValueError) as exc:
            logging.exception("Could not create tender for tenant %s.", tenant_slug)
            st.error(f"The tender could not be created: {exc}")
        else:
            st.success(
                f"Tender {tender['tender_id']} created as "
                f"{tender['publishing_status']}."
            )

    try:
        tenders = db.get_tenant_tenders(tenant_slug)
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception("Could not load tenders for tenant %s.", tenant_slug)
        st.error("Tenant tenders could not be loaded.")
        return
    if not tenders:
        st.info("No solicited tenders have been created for this tenant.")
        return

    now = datetime.now().astimezone()
    for tender in tenders:
        expires_at = datetime.fromisoformat(tender["expiration_at"]).astimezone()
        remaining_seconds = max(0, int((expires_at - now).total_seconds()))
        remaining_days, remainder = divmod(remaining_seconds, 86_400)
        remaining_hours, remainder = divmod(remainder, 3_600)
        remaining_minutes, remaining_seconds = divmod(remainder, 60)
        countdown = (
            f"{remaining_days}d {remaining_hours}h "
            f"{remaining_minutes}m {remaining_seconds}s"
        )
        with st.expander(
            f"{tender['title']} · {tender['publishing_status']} · {countdown}"
        ):
            st.write("Tender ID:", tender["tender_id"])
            st.write("Expiration:", tender["expiration_at"])
            st.write("Auto-lock:", "Enabled" if tender["auto_lock"] else "Disabled")
            if tender["description"]:
                st.write(tender["description"])
            action_col, lock_col, auto_col = st.columns(3)
            if tender["publishing_status"] in {"DRAFT", "LOCKED"}:
                action_label = "Publish"
                next_status = "PUBLISHED"
            else:
                action_label = "Cancel tender"
                next_status = "CANCELLED"
            if action_col.button(
                action_label,
                key=_tenant_key(
                    tenant_slug,
                    "executive",
                    f"tender_action_{tender['tender_id']}",
                ),
            ):
                try:
                    changed = db.update_tenant_tender(
                        tenant_slug,
                        tender["tender_id"],
                        next_status,
                        bool(tender["auto_lock"]),
                        actor,
                    )
                except (sqlite3.Error, RuntimeError, TypeError, ValueError) as exc:
                    logging.exception("Tender update failed for %s.", tenant_slug)
                    st.error(f"The tender could not be updated: {exc}")
                else:
                    if changed:
                        st.rerun()
                    st.error("The tender was not found for this tenant.")
            if tender["publishing_status"] == "PUBLISHED" and lock_col.button(
                "Lock now",
                key=_tenant_key(
                    tenant_slug,
                    "executive",
                    f"tender_lock_{tender['tender_id']}",
                ),
            ):
                try:
                    changed = db.update_tenant_tender(
                        tenant_slug,
                        tender["tender_id"],
                        "LOCKED",
                        bool(tender["auto_lock"]),
                        actor,
                    )
                except (sqlite3.Error, RuntimeError, TypeError, ValueError) as exc:
                    logging.exception("Tender lock failed for %s.", tenant_slug)
                    st.error(f"The tender could not be locked: {exc}")
                else:
                    if changed:
                        st.rerun()
                    st.error("The tender was not found for this tenant.")
            toggled_auto_lock = not bool(tender["auto_lock"])
            if auto_col.button(
                f"Turn auto-lock {'on' if toggled_auto_lock else 'off'}",
                key=_tenant_key(
                    tenant_slug,
                    "executive",
                    f"tender_autolock_{tender['tender_id']}",
                ),
            ):
                try:
                    changed = db.update_tenant_tender(
                        tenant_slug,
                        tender["tender_id"],
                        tender["publishing_status"],
                        toggled_auto_lock,
                        actor,
                    )
                except (sqlite3.Error, RuntimeError, TypeError, ValueError) as exc:
                    logging.exception(
                        "Tender auto-lock update failed for %s.", tenant_slug
                    )
                    st.error(f"Auto-lock could not be updated: {exc}")
                else:
                    if changed:
                        st.rerun()
                    st.error("The tender was not found for this tenant.")


def _render_executive_committee_tab(tenant_slug: str, actor: str) -> None:
    st.subheader("Committee Slot Provisioning")
    st.caption(
        "Provisioning replaces the existing roster and resets all COI state. "
        "Legacy roster credentials are encrypted at rest; issue signed tender "
        "tokens below for the evaluation workspace."
    )
    encryption_key = _physical_document_encryption_key()
    roster_count = st.selectbox(
        "Committee member slots",
        options=list(range(10, 16)),
        key=_tenant_key(tenant_slug, "executive", "committee_count"),
    )
    member_values: list[tuple[str, str]] = []
    with st.container():
        for index in range(roster_count):
            name_col, email_col = st.columns(2)
            name = name_col.text_input(
                f"Member {index + 1} name",
                key=_tenant_key(tenant_slug, "executive", f"committee_name_{index}"),
            )
            email = email_col.text_input(
                f"Member {index + 1} email",
                key=_tenant_key(tenant_slug, "executive", f"committee_email_{index}"),
            )
            member_values.append((name.strip(), email.strip()))
        provision = st.button(
            "Provision committee and credentials",
            key=_tenant_key(tenant_slug, "executive", "provision_committee"),
            type="primary",
            disabled=encryption_key is None,
        )
    if encryption_key is None:
        st.warning(
            "Committee credential provisioning requires a valid "
            "NEXUSVAULT_DOSSIER_ENCRYPTION_KEY."
        )

    if provision:
        invalid_email = next(
            (
                email
                for _, email in member_values
                if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
            ),
            None,
        )
        empty_member = any(not name for name, _ in member_values)
        if empty_member:
            st.error("Enter a name for every committee member.")
        elif invalid_email is not None:
            st.error(f"Enter a valid email address for {invalid_email!r}.")
        elif encryption_key is None:
            st.error("Committee credentials cannot be encrypted.")
        else:
            fernet = Fernet(encryption_key)
            credentials = []
            db_members = []
            for name, email in member_values:
                token = secrets.token_urlsafe(32)
                member_id = f"NV-CMT-{uuid.uuid4().hex.upper()}"
                credentials.append(
                    {
                        "member_id": member_id,
                        "name": name,
                        "email": email,
                        "access_token": token,
                    }
                )
                db_members.append(
                    {
                        "member_id": member_id,
                        "name": name,
                        "email": email,
                        "encrypted_access_token": fernet.encrypt(token.encode("utf-8")),
                    }
                )
            try:
                db.replace_tenant_committee(tenant_slug, db_members, actor)
            except (sqlite3.Error, RuntimeError, TypeError, ValueError) as exc:
                logging.exception(
                    "Could not provision committee for tenant %s.",
                    tenant_slug,
                )
                st.error(f"The committee roster was not provisioned: {exc}")
            else:
                st.session_state[
                    _tenant_key(tenant_slug, "executive", "committee_credentials")
                ] = credentials
                st.success(f"Provisioned {len(credentials)} committee member slots.")

    credentials = st.session_state.get(
        _tenant_key(tenant_slug, "executive", "committee_credentials")
    )
    if isinstance(credentials, list) and credentials:
        with st.expander("Legacy roster credentials — copy and distribute securely"):
            st.warning(
                "These plaintext tokens are retained only in this Streamlit session. "
                "They cannot be retrieved from the database later."
            )
            st.dataframe(
                [
                    {
                        "Member ID": member["member_id"],
                        "Name": member["name"],
                        "Email": member["email"],
                        "Access token": member["access_token"],
                    }
                    for member in credentials
                ],
                use_container_width=True,
            )
            if st.button(
                "Hide plaintext credentials",
                key=_tenant_key(
                    tenant_slug,
                    "executive",
                    "hide_committee_credentials",
                ),
            ):
                st.session_state.pop(
                    _tenant_key(
                        tenant_slug,
                        "executive",
                        "committee_credentials",
                    ),
                    None,
                )
                st.rerun()

    st.subheader("Issue signed committee access")
    try:
        members = db.get_tenant_committee_members(tenant_slug)
        tenders = db.get_active_solicited_tenders(tenant_slug)
    except (sqlite3.Error, RuntimeError, TypeError, ValueError):
        logging.exception(
            "Could not load committee token issuance options for %s.", tenant_slug
        )
        st.error("Committee token issuance is temporarily unavailable.")
        _render_executive_committee_roster(tenant_slug, actor)
        return
    manager = _configured_committee_token_manager()
    if manager is None:
        st.warning(
            "Signed token issuance requires DOSSIER_ENCRYPTION_KEY configuration."
        )
        _render_executive_committee_roster(tenant_slug, actor)
        return
    if not members or not tenders:
        st.info(
            "A committee roster and an active tender are required to issue signed access."
        )
        _render_executive_committee_roster(tenant_slug, actor)
        return
    member_options = {member["member_id"]: member for member in members}
    tender_options = {tender["tender_id"]: tender for tender in tenders}
    with st.container():
        member_id = st.selectbox(
            "Evaluator",
            options=list(member_options),
            format_func=lambda value: f"{member_options[value]['name']} ({member_options[value]['email']})",
        )
        tender_id = st.selectbox(
            "Tender batch",
            options=list(tender_options),
            format_func=lambda value: f"{tender_options[value]['title']} ({value})",
        )
        issue = st.button(
            "Issue signed access token",
            key=_tenant_key(tenant_slug, "executive", "issue_signed_token"),
        )
    issued_key = _tenant_key(tenant_slug, "executive", "issued_signed_token")
    if issue:
        st.session_state.pop(issued_key, None)
        try:
            active_ids = {
                tender["tender_id"]
                for tender in db.get_active_solicited_tenders(tenant_slug)
            }
            current_members = db.get_tenant_committee_members(tenant_slug)
            member = next(
                (entry for entry in current_members if entry["member_id"] == member_id),
                None,
            )
            if tender_id not in active_ids or member is None:
                st.error("The evaluator or active tender is no longer available.")
            else:
                token = manager.generate_token(member["email"], tenant_slug, tender_id)
                db.log_security_audit_event(
                    tenant_slug,
                    actor,
                    "COMMITTEE_TOKEN_ISSUED",
                    {"member_id": member_id, "tender_id": tender_id},
                    _security_session_identifier(),
                )
                st.session_state[issued_key] = token
        except (sqlite3.Error, RuntimeError, TypeError, ValueError, KeyError):
            logging.exception(
                "Could not issue signed committee token for %s.", tenant_slug
            )
            st.error("The signed committee token could not be issued and recorded.")
    issued_token = st.session_state.get(issued_key)
    if isinstance(issued_token, str):
        st.code(issued_token)
        if st.button(
            "Hide signed token",
            key=_tenant_key(tenant_slug, "executive", "hide_signed_token"),
        ):
            st.session_state.pop(issued_key, None)
            st.rerun()

    _render_executive_committee_roster(tenant_slug, actor)


def _render_executive_committee_roster(tenant_slug: str, actor: str) -> None:
    try:
        members = db.get_tenant_committee_members(tenant_slug)
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception("Could not load committee roster for %s.", tenant_slug)
        st.warning("The committee roster could not be loaded.")
        return
    if not members:
        st.info("No committee roster has been provisioned.")
        return

    signed_count = sum(bool(member["coi_signed"]) for member in members)
    st.metric("COI sign-offs recorded", f"{signed_count} / {len(members)}")
    st.caption(
        "Use this control only after receiving the member's signed digital COI "
        "declaration. The audit trail records the executive who attested receipt."
    )
    for member in members:
        with st.expander(f"{member['name']} · {member['email']}"):
            st.write("Member ID:", member["member_id"])
            st.write(
                "COI status:",
                "Signed" if member["coi_signed"] else "Pending",
            )
            if member["coi_signed"]:
                st.caption(f"Recorded at {member['coi_signed_at']}.")
            else:
                with st.container():
                    attested = st.checkbox(
                        "I confirm the member's signed COI declaration was received.",
                        key=_tenant_key(
                            tenant_slug,
                            "executive",
                            f"coi_attested_{member['member_id']}",
                        ),
                    )
                    record_signoff = st.button(
                        "Record received COI sign-off",
                        key=_tenant_key(
                            tenant_slug,
                            "executive",
                            f"coi_submit_{member['member_id']}",
                        ),
                        disabled=not attested,
                    )
                if record_signoff:
                    try:
                        updated = db.record_tenant_committee_coi_signoff(
                            tenant_slug,
                            member["member_id"],
                            actor,
                        )
                    except (sqlite3.Error, RuntimeError, ValueError):
                        logging.exception(
                            "Could not record committee COI for tenant %s.",
                            tenant_slug,
                        )
                        st.error("The COI sign-off could not be recorded.")
                    else:
                        if updated:
                            st.rerun()
                        st.error("The committee member was not found.")

    _render_committee_leaderboard(tenant_slug)


def _render_committee_leaderboard(tenant_slug: str) -> None:
    st.markdown("#### Consolidated Committee Ranking")
    try:
        proposals = db.get_tenant_governance_proposals(tenant_slug)
        leaderboard = []
        reviewer_details = []
        for proposal in proposals:
            scores = db.get_consolidated_committee_scores(
                tenant_slug,
                str(proposal["tracking_id"]),
            )
            if not scores["reviewer_count"]:
                continue
            leaderboard.append(
                {
                    "Tracking ID": proposal["tracking_id"],
                    "Proposal": proposal["proposal_title"],
                    "Reviewers": scores["reviewer_count"],
                    "Technical avg": round(scores["technical_average"], 2),
                    "Financial avg": round(scores["financial_average"], 2),
                    "Compliance avg": round(scores["compliance_average"], 2),
                    "Equal-weight avg": round(scores["weighted_average"], 2),
                    "Score variance": round(scores["score_variance"], 2),
                }
            )
            reviewer_details.append((proposal, scores))
    except (sqlite3.Error, RuntimeError, TypeError, ValueError):
        logging.exception(
            "Could not load committee rankings for tenant %s.",
            tenant_slug,
        )
        st.error("The committee ranking summary could not be loaded.")
        return

    if not leaderboard:
        st.info("No committee evaluations have been submitted.")
        return

    top_score = max(row["Equal-weight avg"] for row in leaderboard)
    for row in leaderboard:
        row["Recommendation"] = (
            "Recommended Winner" if row["Equal-weight avg"] == top_score else ""
        )
    st.caption(
        "Scores weight Technical, Financial, and Compliance equally (1/3 each). "
        "Variance is the population variance of reviewers' combined scores; "
        "recommendation is advisory, not an award decision."
    )
    st.dataframe(leaderboard, use_container_width=True, hide_index=True)
    for proposal, scores in reviewer_details:
        with st.expander(
            f"Individual scores · {proposal['tracking_id']} · "
            f"{proposal['proposal_title']}"
        ):
            st.dataframe(
                [
                    {
                        "Member": reviewer["name"],
                        "Member ID": reviewer["member_id"],
                        "Technical": reviewer["technical_score"],
                        "Financial": reviewer["financial_score"],
                        "Compliance": reviewer["compliance_score"],
                        "Combined": round(reviewer["combined_score"], 2),
                        "Submitted": reviewer["submitted_at"],
                    }
                    for reviewer in scores["reviewers"]
                ],
                use_container_width=True,
                hide_index=True,
            )


def _configured_committee_token_manager() -> Any | None:
    """Load the signing key without treating a missing key as valid."""
    if CommitteeTokenManager is None:
        logging.error(
            "Committee token authentication is unavailable: %s",
            _COMMITTEE_AUTH_IMPORT_ERROR,
        )
        return None
    key = os.environ.get("DOSSIER_ENCRYPTION_KEY", "").strip()
    if not key:
        try:
            secret = st.secrets.get("DOSSIER_ENCRYPTION_KEY", "")
        except (KeyError, StreamlitSecretNotFoundError):
            secret = ""
        if isinstance(secret, str):
            key = secret.strip()
    return CommitteeTokenManager(key) if key else None


def _verified_committee_token(
    manager: Any, token: str, tenant_slug: str
) -> dict[str, str] | None:
    """Validate signed claims and bind the token to the current tenant."""
    valid, payload, _ = manager.verify_token(token)
    if not valid or not isinstance(payload, dict):
        return None
    email = payload.get("email")
    tenant_id = payload.get("tenant_id")
    tender_id = payload.get("tender_id")
    expires = payload.get("exp")
    if (
        not isinstance(email, str)
        or not email.strip()
        or not isinstance(tenant_id, str)
        or tenant_id != tenant_slug
        or not isinstance(tender_id, str)
        or not tender_id.strip()
        or type(expires) is not int
        or expires <= time.time()
    ):
        return None
    return {"email": email, "tenant_id": tenant_id, "tender_id": tender_id}


def enforce_committee_access(
    token: str, target_tenant_id: str, target_tender_id: str
) -> tuple[dict[str, Any] | None, str]:
    manager = _configured_committee_token_manager()
    if manager is None:
        return None, "Committee access requires DOSSIER_ENCRYPTION_KEY configuration."
    valid, payload, _ = manager.verify_token(token)
    if not valid or not isinstance(payload, dict):
        return None, "Compliance error: the committee token is invalid or expired."
    expires = payload.get("exp")
    email = payload.get("email")
    if type(expires) is not int or expires <= time.time():
        return None, "Compliance error: the committee token is expired or invalid."
    if not isinstance(email, str) or not email.strip():
        return None, "Compliance error: the committee token has an invalid evaluator."
    if (
        payload.get("tenant_id") != target_tenant_id
        or payload.get("tender_id") != target_tender_id
    ):
        return (
            None,
            "Compliance error: the token does not match this tenant and tender.",
        )
    return payload, ""


def _handle_signed_committee_login(tenant_slug: str) -> None:
    if not _guard_session_interaction():
        return
    input_key = _tenant_key(tenant_slug, "committee_signed", "input")
    token_key = _tenant_key(tenant_slug, "committee_signed", "token")
    error_key = _tenant_key(tenant_slug, "committee_signed", "login_error")
    token = str(st.session_state.get(input_key, "")).strip()
    st.session_state[input_key] = ""
    st.session_state.pop(token_key, None)
    manager = _configured_committee_token_manager()
    identity = (
        _verified_committee_token(manager, token, tenant_slug)
        if manager is not None
        else None
    )
    try:
        db.log_security_audit_event(
            tenant_slug,
            "committee_member",
            "LOGIN_SUCCESS" if identity is not None else "LOGIN_FAILED",
            {"authentication_method": "signed_committee_token"},
            _security_session_identifier(),
        )
    except (sqlite3.Error, RuntimeError, TypeError, ValueError):
        logging.exception("Could not audit signed committee login for %s.", tenant_slug)
        st.session_state[error_key] = (
            "Committee access could not be verified and recorded."
        )
        return
    if identity is None:
        st.session_state[error_key] = (
            "The committee token is invalid, expired, or for another tenant."
        )
        return
    st.session_state[token_key] = token
    st.session_state.pop(error_key, None)


def _render_signed_committee_sandbox(tenant_slug: str) -> None:
    """Display only the claims from a valid, tenant-bound signed token."""
    st.subheader("Signed-token evaluation sandbox")
    st.caption(
        "Use a signed token issued by your administrator for this tenant slug "
        "and tender."
    )
    manager = _configured_committee_token_manager()
    token_key = _tenant_key(tenant_slug, "committee_signed", "token")
    if manager is None:
        st.session_state.pop(token_key, None)
        st.error(
            "Committee access requires DOSSIER_ENCRYPTION_KEY in the environment "
            "or Streamlit secrets."
        )
        return
    token = st.session_state.get(token_key)
    identity = (
        _verified_committee_token(manager, token, tenant_slug)
        if isinstance(token, str)
        else None
    )
    if identity is None:
        if token is not None:
            st.session_state.pop(token_key, None)
            st.warning("Your committee token has expired or is no longer valid.")
        with st.container():
            st.text_input(
                "Signed committee token",
                type="password",
                key=_tenant_key(tenant_slug, "committee_signed", "input"),
            )
            st.button(
                "Unlock signed-token sandbox",
                key=_tenant_key(tenant_slug, "committee_signed", "submit"),
                on_click=_handle_signed_committee_login,
                args=(tenant_slug,),
            )
        error = st.session_state.pop(
            _tenant_key(tenant_slug, "committee_signed", "login_error"), None
        )
        if isinstance(error, str) and error:
            st.error(error)
        return

    st.success("Signed committee token verified.")
    st.write("Committee member email:", identity["email"])
    st.write("Tenant ID:", identity["tenant_id"])
    st.write("Tender ID:", identity["tender_id"])
    st.caption(
        "Sandbox only: proposal dossiers and evaluations remain protected by "
        "the separate roster-backed workspace."
    )
    if st.button(
        "Lock signed-token sandbox",
        key=_tenant_key(tenant_slug, "committee_signed", "logout"),
    ):
        st.session_state.pop(token_key, None)
        st.rerun()


def _handle_committee_login(tenant_slug: str) -> None:
    if not _guard_session_interaction():
        return
    identity_key = _tenant_key(tenant_slug, "committee", "identity")
    token_key = _tenant_key(tenant_slug, "committee", "access_token")
    error_key = _tenant_key(tenant_slug, "committee", "login_error")
    token = str(st.session_state.get(token_key, "")).strip()
    st.session_state[token_key] = ""
    encryption_key = _physical_document_encryption_key()
    if encryption_key is None:
        st.session_state[error_key] = (
            "Committee access is unavailable because the dossier encryption key "
            "is not configured."
        )
        return
    try:
        identity = db.authenticate_tenant_committee_member(
            tenant_slug,
            token,
            encryption_key,
        )
        db.log_security_audit_event(
            tenant_slug,
            "committee_member",
            "LOGIN_SUCCESS" if identity is not None else "LOGIN_FAILED",
            {"authentication_method": "committee_token"},
            _security_session_identifier(),
        )
        if identity is not None:
            db.log_tenant_activity(
                tenant_slug,
                identity["member_id"],
                "committee_workspace_accessed",
                "Committee member authenticated to the evaluation workspace.",
            )
    except (sqlite3.Error, RuntimeError, TypeError, ValueError):
        logging.exception(
            "Committee member authentication failed for tenant %s.",
            tenant_slug,
        )
        st.session_state[error_key] = (
            "Committee access could not be verified. Please retry."
        )
        return
    if identity is None:
        st.session_state[error_key] = (
            "The committee access token is invalid for this tenant."
        )
        st.session_state.pop(identity_key, None)
        return
    st.session_state[identity_key] = identity
    st.session_state.pop(error_key, None)


def _clear_committee_access(tenant_slug: str) -> None:
    st.session_state["committee_authenticated"] = False
    st.session_state["committee_payload"] = None
    st.session_state.pop(_tenant_key(tenant_slug, "committee", "signed_token"), None)
    st.session_state.pop(_tenant_key(tenant_slug, "committee", "identity"), None)


def _handle_committee_access(tenant_slug: str) -> None:
    if not _guard_session_interaction():
        return
    input_key = _tenant_key(tenant_slug, "committee", "signed_input")
    tender_key = _tenant_key(tenant_slug, "committee", "tender")
    error_key = _tenant_key(tenant_slug, "committee", "login_error")
    token = str(st.session_state.get(input_key, "")).strip()
    st.session_state[input_key] = ""
    _clear_committee_access(tenant_slug)
    tender_id = st.session_state.get(tender_key, "")
    payload, error = enforce_committee_access(token, tenant_slug, tender_id)
    try:
        tenders = db.get_active_solicited_tenders(tenant_slug)
        members = db.get_tenant_committee_members(tenant_slug) if payload else []
        if payload and tender_id not in {tender["tender_id"] for tender in tenders}:
            payload = None
            error = "Compliance error: the selected tender is no longer active."
        member = (
            next(
                (
                    member
                    for member in members
                    if str(member.get("email", "")).strip().casefold()
                    == str(payload["email"]).strip().casefold()
                ),
                None,
            )
            if payload
            else None
        )
        if payload and member is None:
            payload = None
            error = "Compliance error: the evaluator is not on this tenant's committee roster."
        db.log_security_audit_event(
            tenant_slug,
            "committee_member",
            "LOGIN_SUCCESS" if payload else "LOGIN_FAILED",
            {"authentication_method": "signed_committee_token"},
            _security_session_identifier(),
        )
    except (sqlite3.Error, RuntimeError, TypeError, ValueError, KeyError):
        logging.exception(
            "Could not verify committee access for tenant %s.", tenant_slug
        )
        st.session_state[error_key] = (
            "Committee access could not be verified and recorded."
        )
        return
    if payload is None or member is None:
        st.session_state[error_key] = error
        return
    st.session_state[_tenant_key(tenant_slug, "committee", "signed_token")] = token
    st.session_state[_tenant_key(tenant_slug, "committee", "identity")] = {
        "member_id": str(member["member_id"]),
        "name": str(member["name"]),
        "tenant_slug": tenant_slug,
    }
    st.session_state["committee_payload"] = payload
    st.session_state["committee_authenticated"] = True
    st.session_state.pop(error_key, None)


def _render_committee_workspace(tenant_slug: str) -> None:
    st.header("Committee Evaluation Workspace")
    st.session_state.setdefault("committee_authenticated", False)
    st.session_state.setdefault("committee_payload", None)
    identity_key = _tenant_key(tenant_slug, "committee", "identity")
    identity = st.session_state.get(identity_key)
    token = st.session_state.get(_tenant_key(tenant_slug, "committee", "signed_token"))
    saved_payload = st.session_state.get("committee_payload")
    try:
        tenders = db.get_active_solicited_tenders(tenant_slug)
    except (sqlite3.Error, RuntimeError, TypeError, ValueError):
        _clear_committee_access(tenant_slug)
        logging.exception("Could not load active tenders for tenant %s.", tenant_slug)
        st.error(
            "Committee access is unavailable: active tenders could not be verified."
        )
        return
    tender_options = {
        str(tender["tender_id"]): str(tender["title"]) for tender in tenders
    }
    payload = None
    if st.session_state.committee_authenticated is True and isinstance(
        saved_payload, dict
    ):
        tender_id = saved_payload.get("tender_id")
        if (
            isinstance(token, str)
            and isinstance(tender_id, str)
            and tender_id in tender_options
        ):
            payload, _ = enforce_committee_access(token, tenant_slug, tender_id)
        if (
            payload != saved_payload
            or not isinstance(identity, Mapping)
            or identity.get("tenant_slug") != tenant_slug
        ):
            payload = None
        if payload is not None:
            try:
                members = db.get_tenant_committee_members(tenant_slug)
                if not any(
                    member.get("member_id") == identity.get("member_id")
                    and str(member.get("email", "")).strip().casefold()
                    == payload["email"].strip().casefold()
                    for member in members
                ):
                    payload = None
            except (sqlite3.Error, RuntimeError, TypeError, ValueError):
                logging.exception(
                    "Could not verify committee roster for tenant %s.", tenant_slug
                )
                payload = None
        if payload is None:
            _clear_committee_access(tenant_slug)
            st.warning(
                "Compliance error: committee access has expired or is no longer valid."
            )
    if payload is None:
        _clear_committee_access(tenant_slug)
        if _configured_committee_token_manager() is None:
            st.error(
                "Committee access requires DOSSIER_ENCRYPTION_KEY in the environment or Streamlit secrets."
            )
            return
        if not tender_options:
            st.info("No active tender batches are available for committee evaluation.")
            return
        with st.container():
            st.text_input(
                "Cryptographic access token",
                type="password",
                key=_tenant_key(tenant_slug, "committee", "signed_input"),
            )
            st.selectbox(
                "Active tender batch",
                options=list(tender_options),
                format_func=lambda tender_id: f"{tender_options[tender_id]} ({tender_id})",
                key=_tenant_key(tenant_slug, "committee", "tender"),
            )
            submitted = st.button(
                "Authenticate & Unlock Workspace",
                key=_tenant_key(tenant_slug, "committee", "login_submit"),
                type="primary",
                on_click=_handle_committee_access,
                args=(tenant_slug,),
            )
        if submitted and st.session_state.committee_authenticated:
            st.rerun()
        login_error = st.session_state.pop(
            _tenant_key(tenant_slug, "committee", "login_error"),
            None,
        )
        if isinstance(login_error, str) and login_error:
            st.error(login_error)
        return

    st.success(
        f"Evaluator: {payload['email']} | Tenant: {payload['tenant_id']} | "
        f"Tender: {payload['tender_id']}"
    )
    if st.button(
        "Lock Workspace / Logout",
        key=_tenant_key(tenant_slug, "committee", "logout"),
    ):
        _clear_committee_access(tenant_slug)
        st.rerun()
    try:
        proposals = db.get_tenant_governance_proposals(tenant_slug)
        passes = db.get_tenant_financial_ledger(tenant_slug)
        tender_passes = {
            str(entry["qr_pass_id"])
            for entry in passes
            if entry.get("rfq_code") == payload["tender_id"]
            and entry.get("clearance_status") == "DOSSIER_SUBMITTED"
        }
        proposals = [
            proposal
            for proposal in proposals
            if proposal.get("source_type") == "solicited"
            and str(proposal["tracking_id"]) in tender_passes
        ]
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception("Could not load committee proposals for %s.", tenant_slug)
        st.error("Proposal assignments could not be loaded.")
        return
    if not proposals:
        st.info("No proposals are available for committee evaluation.")
        return

    proposal_options = {
        f"{proposal['tracking_id']} · {proposal['proposal_title']}": proposal
        for proposal in proposals
    }
    selected_label = st.selectbox(
        "Select proposal for review",
        options=list(proposal_options),
        key=_tenant_key(tenant_slug, "committee", "proposal_selection"),
    )
    proposal = proposal_options[selected_label]
    tracking_id = str(proposal["tracking_id"])

    try:
        coi_status = db.get_committee_coi_status(
            tenant_slug,
            str(identity["member_id"]),
            tracking_id,
        )
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception(
            "Could not load COI status for proposal %s.",
            tracking_id,
        )
        st.error("The proposal's COI gate could not be checked.")
        return

    if coi_status is None or coi_status.get("declaration_status") != "Signed":
        st.warning("Proposal access is locked until you sign the COI declaration.")
        st.markdown(
            "> I declare no direct, indirect, or pecuniary interest in the "
            "bidding organization or this proposal. I will disclose any actual "
            "or potential conflict and will not participate in an evaluation "
            "where such a conflict exists."
        )
        attested = st.checkbox(
            "I have read and agree to this Conflict of Interest declaration.",
            key=_tenant_key(
                tenant_slug,
                "committee",
                f"coi_attested_{tracking_id}",
            ),
        )
        if st.button(
            "Sign Digital COI Attestation",
            type="primary",
            disabled=not attested,
            key=_tenant_key(tenant_slug, "committee", f"sign_coi_{tracking_id}"),
        ):
            try:
                db.record_committee_coi_signoff(
                    tenant_slug,
                    str(identity["member_id"]),
                    tracking_id,
                    str(identity["name"]),
                )
            except (sqlite3.Error, RuntimeError, TypeError, ValueError):
                logging.exception(
                    "Committee COI sign-off failed for proposal %s.",
                    tracking_id,
                )
                st.error("The COI attestation could not be recorded.")
            else:
                st.session_state[
                    _tenant_key(
                        tenant_slug,
                        "committee",
                        "workspace_feedback",
                    )
                ] = "COI attestation recorded. Proposal review is now unlocked."
                st.rerun()
        return

    feedback_key = _tenant_key(tenant_slug, "committee", "workspace_feedback")
    feedback = st.session_state.pop(feedback_key, None)
    if isinstance(feedback, str) and feedback:
        st.success(feedback)
    st.success(
        f"COI signed by {coi_status['signed_by_name']} at {coi_status['timestamp']}."
    )
    st.caption(f"Digital signature SHA-256: {coi_status['digital_signature_hash']}")
    st.subheader("Proposal dossier")
    st.write("Tracking ID:", tracking_id)
    st.write("Proposal:", proposal["proposal_title"])
    st.caption(
        "The source dossier may identify the submitting organization and is not "
        "automatically redacted. Review technical specifications and bill-of-"
        "quantities content in the source file; these are not separately indexed."
    )
    try:
        from sector_logic import get_departmental_proposal_document

        source_filename, source_bytes = get_departmental_proposal_document(
            tenant_slug,
            tracking_id,
        )
    except (FileNotFoundError, OSError, RuntimeError, ValueError, sqlite3.Error):
        logging.exception(
            "Could not load committee dossier %s for tenant %s.",
            tracking_id,
            tenant_slug,
        )
        st.error("The proposal dossier could not be opened.")
        return
    st.download_button(
        "Download proposal dossier",
        data=source_bytes,
        file_name=source_filename,
        mime="application/octet-stream",
        key=_tenant_key(
            tenant_slug,
            "committee",
            f"download_dossier_{tracking_id}",
        ),
    )

    try:
        saved_evaluation = db.get_committee_proposal_evaluation(
            tenant_slug,
            str(identity["member_id"]),
            tracking_id,
        )
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception(
            "Could not load member evaluation for proposal %s.",
            tracking_id,
        )
        st.error("Your saved evaluation could not be loaded.")
        return
    st.subheader("Evaluation matrix")
    with st.container():
        score_keys = {}
        score_values = (
            ("technical", "Technical Capacity", "technical_score"),
            ("financial", "Financial Capability", "financial_score"),
            ("compliance", "Regulatory Compliance", "compliance_score"),
        )
        for score_name, label, db_field in score_values:
            key = _tenant_key(
                tenant_slug,
                "committee",
                f"{score_name}_score_{tracking_id}",
            )
            st.session_state.setdefault(
                key,
                int(saved_evaluation[db_field]) if saved_evaluation else 50,
            )
            st.slider(label, min_value=0, max_value=100, key=key)
            score_keys[score_name] = key
        notes_key = _tenant_key(
            tenant_slug,
            "committee",
            f"evaluation_notes_{tracking_id}",
        )
        st.session_state.setdefault(
            notes_key,
            str(saved_evaluation["notes"]) if saved_evaluation else "",
        )
        st.text_area(
            "Appraisal notes",
            max_chars=8_000,
            key=notes_key,
        )
        submitted = st.button(
            "Save proposal evaluation",
            key=_tenant_key(
                tenant_slug,
                "committee",
                f"save_evaluation_{tracking_id}",
            ),
            type="primary",
        )
    if submitted:
        scores = {name: int(st.session_state[key]) for name, key in score_keys.items()}
        try:
            db.save_committee_proposal_evaluation(
                tenant_slug=tenant_slug,
                member_id=str(identity["member_id"]),
                tracking_id=tracking_id,
                scores_dict=scores,
                notes=str(st.session_state.get(notes_key, "")),
            )
        except (sqlite3.Error, RuntimeError, TypeError, ValueError):
            logging.exception(
                "Committee evaluation save failed for proposal %s.",
                tracking_id,
            )
            st.error("The evaluation could not be saved.")
        else:
            st.session_state[feedback_key] = "Your evaluation has been saved."
            st.rerun()


def _proposal_compliance_matrix(proposal: Mapping[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "Check": "CAC registration",
            "Completeness": (
                "Provided; registry verification required"
                if str(proposal.get("cac_registration_number") or "").strip()
                else "Missing"
            ),
            "Verification": "Not externally verified",
        },
        {
            "Check": "TIN",
            "Completeness": "Not captured in this intake",
            "Verification": "Manual verification required",
        },
        {
            "Check": "KYB / beneficial ownership",
            "Completeness": "Not captured in this intake",
            "Verification": "Manual verification required",
        },
        *[
            {
                "Check": check_name,
                "Completeness": "Not captured in this intake",
                "Verification": "Sector authority review required",
            }
            for check_name in (
                "EFCC",
                "PenCom",
                "NAFDAC",
                "COREN",
                "NSCDC",
                "NITDA / NDPA",
            )
        ],
        {
            "Check": "Contact details",
            "Completeness": (
                "Provided"
                if proposal.get("official_email") and proposal.get("contact_phone")
                else "Missing"
            ),
            "Verification": "Not externally verified",
        },
    ]


def _render_executive_ai_advisor(
    tenant_id: str,
    proposals_data: list[dict[str, Any]],
) -> None:
    if not _tenant_access_is_authenticated("executive", tenant_id):
        return

    import sector_logic

    try:
        advisor_data = sector_logic.build_executive_ai_advisor_context(
            tenant_id,
            proposals_data,
        )
        ai_configured = sector_logic.executive_ai_is_configured()
    except (sqlite3.Error, RuntimeError, TypeError, ValueError):
        logging.exception(
            "Could not prepare the executive AI advisor for tenant %s.",
            tenant_id,
        )
        st.error("The executive AI advisor could not load its proposal audit.")
        return

    summary_key = _tenant_key(tenant_id, "executive", "ai_advisor_summary")
    strategy_key = _tenant_key(tenant_id, "executive", "ai_advisor_strategy")
    with st.container(border=True):
        st.markdown(
            """
            <style>
            div[data-testid="stVerticalBlockBorderWrapper"]:has(
                .executive-ai-advisor-anchor
            ) {
                border: 2px solid transparent !important;
                border-radius: 18px !important;
                background:
                    linear-gradient(#121827, #121827) padding-box,
                    linear-gradient(120deg, #10b981, #d4af37) border-box !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"]:has(
                .executive-ai-advisor-anchor
            ) [data-testid="stMarkdownContainer"] {
                color: #f8fafc;
            }
            .executive-ai-advisor-anchor { height: 0; }
            .executive-ai-advisor-status {
                color: #34d399;
                font-weight: 700;
                letter-spacing: 0.02em;
            }
            </style>
            <div class="executive-ai-advisor-anchor"></div>
            <div class="executive-ai-advisor-status">
                ● Agentic AI Executive Strategy Node Active
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.subheader("Sovereign Executive AI Consultation Advisor")
        st.caption(
            "Decision support only; not a procurement decision or compliance "
            "certification. Gemini receives proposal titles, routing/workflow "
            "status, compliance-check names and statuses, and aggregate committee "
            "scores only. Proposal documents, organization/contact details, and "
            "reviewer identities are not sent."
        )

        st.markdown("**Committee Evaluation & COI Anomaly Audit**")
        if advisor_data["committee_audit"]:
            st.dataframe(
                advisor_data["committee_audit"],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info(
                "No committee members or proposal-scoped COI records are available."
            )

        st.caption(
            "Scoring outlier screening flags reviewer category scores at least "
            f"{advisor_data['outlier_threshold']} points from that proposal's panel "
            "average. This is a review heuristic, not evidence of misconduct."
        )
        if advisor_data["scoring_outliers"]:
            st.dataframe(
                [
                    {
                        "Proposal": finding["proposal"],
                        "Committee member": finding["reviewer"],
                        "Category": finding["category"],
                        "Score": finding["score"],
                        "Panel average": finding["panel_average"],
                        "Difference": finding["difference"],
                    }
                    for finding in advisor_data["scoring_outliers"]
                ],
                use_container_width=True,
                hide_index=True,
            )
        elif advisor_data["committee_audit"]:
            st.success("No scoring outliers were detected by this screening heuristic.")

        if not ai_configured:
            st.warning(
                "Gemini consultation is unavailable. Configure GEMINI_API_KEY in "
                ".streamlit/secrets.toml to enable AI-generated summaries and "
                "strategy responses. The committee audit and all other portal "
                "features remain available."
            )

        st.markdown("**Executive Summary Generator**")
        if st.button(
            "Generate executive summary",
            key=_tenant_key(tenant_id, "executive", "ai_summary_button"),
            disabled=not ai_configured or advisor_data["proposal_count"] == 0,
        ):
            try:
                st.session_state[summary_key] = (
                    sector_logic.generate_executive_ai_consultation(
                        advisor_data["ai_context"],
                        (
                            "Assess overall proposal viability and policy alignment "
                            "across the available proposals."
                        ),
                        "summary",
                        tenant_id=tenant_id,
                    )
                )
            except (RuntimeError, ValueError) as exc:
                st.error(str(exc))

        summary = st.session_state.get(summary_key)
        if isinstance(summary, str) and summary:
            st.markdown(summary)

        st.markdown("**Interactive Strategy Query**")
        with st.form(key=_tenant_key(tenant_id, "executive", "ai_strategy_form")):
            strategy_question = st.text_area(
                "Ask the Executive Strategy Advisor",
                placeholder=("Analyze risk profiles for physical security proposals"),
                max_chars=2_000,
                key=_tenant_key(tenant_id, "executive", "ai_strategy_question"),
            )
            submitted = st.form_submit_button(
                "Run strategy consultation",
                disabled=not ai_configured,
            )
        if submitted:
            if not strategy_question.strip():
                st.warning("Enter a question for the executive advisor.")
            else:
                try:
                    st.session_state[strategy_key] = (
                        sector_logic.generate_executive_ai_consultation(
                            advisor_data["ai_context"],
                            strategy_question,
                            "strategy",
                            tenant_id=tenant_id,
                        )
                    )
                except (RuntimeError, ValueError) as exc:
                    st.error(str(exc))

        strategy_response = st.session_state.get(strategy_key)
        if isinstance(strategy_response, str) and strategy_response:
            st.markdown(strategy_response)


def _render_executive_apex_tab(tenant_slug: str, actor: str) -> None:
    st.subheader("Apex Proposal Hub")
    st.caption(
        "Completeness indicators below are local rules, not external registry checks "
        "or an AI compliance certification. Executive overrides are tenant-scoped "
        "and written to the audit trail."
    )
    _render_committee_leaderboard(tenant_slug)
    try:
        proposals = db.get_tenant_governance_proposals(tenant_slug)
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception("Could not load apex proposals for %s.", tenant_slug)
        st.error("The proposal hub could not be loaded.")
        return
    _render_executive_ai_advisor(tenant_slug, proposals)
    if not proposals:
        st.info("No physical proposals are available for executive review.")
        return

    st.dataframe(
        [
            {
                "Tracking ID": proposal["tracking_id"],
                "Organization": proposal["organization_name"],
                "Proposal": proposal["proposal_title"],
                "Directorate": proposal["routed_directorate"],
                "Submitted": proposal["submitted_at"],
                "Governance status": proposal["governance_status"],
                "Departmental sign-off": (
                    proposal.get("departmental_signoff_status") or "Pending"
                ),
                "Pushed to Apex": bool(proposal.get("appraisal_pushed_to_apex")),
            }
            for proposal in proposals
        ],
        use_container_width=True,
    )
    for proposal in proposals:
        status = proposal["governance_status"]
        with st.expander(
            f"{proposal['tracking_id']} · {proposal['proposal_title']} · {status}"
        ):
            st.write("Organization:", proposal["organization_name"])
            st.write("Receipt SHA-256:", proposal["receipt_hash"])
            st.write("Directorate:", proposal["routed_directorate"])
            st.write(
                "Departmental sign-off:",
                proposal.get("departmental_signoff_status") or "Pending",
            )
            st.write(
                "Pushed to Apex:",
                "Yes" if proposal.get("appraisal_pushed_to_apex") else "No",
            )
            try:
                departmental_dossier = db.get_departmental_review_dossier(
                    tenant_slug,
                    proposal["tracking_id"],
                )
            except (sqlite3.Error, RuntimeError, ValueError):
                logging.exception(
                    "Could not load Apex appraisal for %s.",
                    proposal["tracking_id"],
                )
                departmental_dossier = None
            if departmental_dossier and departmental_dossier["compliance_checks"]:
                st.dataframe(
                    [
                        {
                            "Registry": check["check_name"],
                            "Status": check["verification_status"],
                            "Details": check["result_details"],
                        }
                        for check in departmental_dossier["compliance_checks"]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.dataframe(
                    _proposal_compliance_matrix(proposal),
                    use_container_width=True,
                    hide_index=True,
                )
            if departmental_dossier:
                st.markdown("**Departmental appraisal notes**")
                st.write(
                    departmental_dossier.get("appraisal_notes") or "Not submitted."
                )
                st.markdown("**Executive summary**")
                st.write(
                    departmental_dossier.get("executive_summary") or "Not generated."
                )
            choices = (
                [("Recall proposal", "RECALLED"), ("Stop processing", "STOPPED")]
                if status in {"RECEIVED", "RESUMED"}
                else [("Resume processing", "RESUMED")]
            )
            action_columns = st.columns(len(choices))
            for action_column, (label, next_status) in zip(
                action_columns,
                choices,
            ):
                if action_column.button(
                    label,
                    key=_tenant_key(
                        tenant_slug,
                        "executive",
                        f"proposal_{next_status}_{proposal['tracking_id']}",
                    ),
                ):
                    try:
                        updated = db.set_tenant_proposal_governance_status(
                            tenant_slug,
                            proposal["tracking_id"],
                            next_status,
                            actor,
                            actor_role="executive",
                            ip_or_session=_security_session_identifier(),
                        )
                    except (sqlite3.Error, RuntimeError, TypeError, ValueError):
                        logging.exception(
                            "Proposal override failed for tenant %s.",
                            tenant_slug,
                        )
                        st.error("The executive proposal override failed.")
                    else:
                        if updated:
                            st.rerun()
                        st.error("The proposal was not found for this tenant.")


def _render_executive_command_center(
    tenant: Mapping[str, Any],
    tenant_slug: str,
) -> None:
    actor = "tenant_executive"
    st.header("Executive Protected Command Center")
    st.caption(
        f"{tenant.get('apex_title') or 'Permanent Secretary / Top Management'} · "
        f"{tenant.get('full_corporation_name') or tenant_slug}"
    )
    gateway_tab, finance_tab, tenders_tab, committee_tab, apex_tab = st.tabs(
        [
            "Payment Gateway",
            "DFA Reconciliation",
            "Tender Publishing",
            "Committee Provisioning",
            "Apex Proposal Hub",
        ]
    )
    with gateway_tab:
        _render_executive_gateway_tab(tenant_slug, actor)
    with finance_tab:
        _render_executive_financial_tab(tenant_slug)
    with tenders_tab:
        _render_executive_tenders_tab(tenant_slug, actor)
    with committee_tab:
        _render_executive_committee_tab(tenant_slug, actor)
    with apex_tab:
        _render_executive_apex_tab(tenant_slug, actor)


def _create_primary_tenant_support_ticket(
    *,
    tenant_id: str,
    tenant_slug: str,
    org_name: str,
    sender_email: str,
    message: str,
) -> tuple[bool, str | None]:
    if tenant_id != tenant_slug:
        raise ValueError("Support tenant identity does not match the active route.")
    if not org_name.strip():
        raise ValueError("org_name is required.")
    automated_response = (
        _match_knowledge_base(message) if _match_knowledge_base is not None else None
    )
    return db.create_tenant_support_ticket(
        tenant_slug=tenant_slug,
        sender_email=sender_email,
        message=message,
        automated_response=automated_response,
    )


def _configured_support_postgresql_dsn() -> str | None:
    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn:
        try:
            secret = st.secrets.get("DATABASE_URL", "")
        except (KeyError, StreamlitSecretNotFoundError):
            secret = ""
        if isinstance(secret, str):
            dsn = secret.strip()
    if dsn.startswith("postgresql+psycopg2://"):
        dsn = dsn.replace("postgresql+psycopg2://", "postgresql://", 1)
    if dsn.startswith(("postgresql://", "postgres://")):
        return dsn
    return None


def _render_tenant_ai_support_query(
    tenant_slug: str,
    identity: Mapping[str, Any],
) -> None:
    st.markdown("### Tenant-Scoped AI Knowledge Base")
    st.caption(
        "Queries and any escalation tickets are scoped to this authenticated "
        "tenant by PostgreSQL row-level security."
    )
    if (
        NexusAgenticSupportEngine is None
        or SovereignKnowledgeBase is None
        or SupportTier is None
        or UserContext is None
    ):
        detail = (
            f" {_AI_SUPPORT_IMPORT_ERROR}"
            if _AI_SUPPORT_IMPORT_ERROR is not None
            else ""
        )
        st.error(f"The tenant-scoped AI support engine is unavailable.{detail}")
        return
    dsn = _configured_support_postgresql_dsn()
    if dsn is None:
        st.info(
            "The tenant-scoped PostgreSQL Knowledge Base is not configured. "
            "Submit an inquiry in Support & Feedback for local Knowledge Base "
            "matching and executive follow-up."
        )
        return

    query_key = _tenant_key(tenant_slug, "support", "ai_query")
    result_key = _tenant_key(tenant_slug, "support", "ai_result")
    with st.form(key=_tenant_key(tenant_slug, "support", "ai_query_form")):
        query_text = st.text_area(
            "Ask a question about this tenant's services or procedures",
            key=query_key,
            max_chars=10_000,
        )
        submitted = st.form_submit_button("Submit Knowledge Base Query")

    if submitted:
        if not _guard_session_interaction():
            st.rerun()
        if not query_text.strip():
            st.warning("Enter a question before submitting.")
        else:
            context = UserContext(
                user_id=str(identity["username"]),
                tenant_id=tenant_slug,
                role=str(identity["role"]),
                tier=SupportTier.INTERNAL_ADMIN,
                email=None,
            )
            try:
                engine = NexusAgenticSupportEngine(
                    SovereignKnowledgeBase(connection_string=dsn),
                )
                response = engine.process_query(query_text, context)
            except (RuntimeError, ValueError):
                logging.exception(
                    "Tenant Knowledge Base query failed for %s.",
                    tenant_slug,
                )
                st.session_state.pop(result_key, None)
                st.error(
                    "The tenant Knowledge Base could not process this query. "
                    "Please use the Support & Feedback gateway."
                )
            except Exception as exc:
                if (
                    _PostgreSQLSupportError is None
                    or not isinstance(exc, _PostgreSQLSupportError)
                ):
                    raise
                logging.exception(
                    "Tenant PostgreSQL Knowledge Base query failed for %s.",
                    tenant_slug,
                )
                st.session_state.pop(result_key, None)
                st.error(
                    "The tenant Knowledge Base is temporarily unavailable. "
                    "Please use the Support & Feedback gateway."
                )
            else:
                st.session_state[result_key] = response

    response = st.session_state.get(result_key)
    if response is not None:
        st.markdown("#### Query response")
        st.markdown(response.response_text)
        st.caption(
            f"Confidence: {response.confidence_score:.0%} · "
            f"{'Grounded in the tenant Knowledge Base' if response.grounded_in_kb else 'No matching Knowledge Base entry'}"
        )
        if response.escalated_to_human:
            st.warning(
                f"Escalated for human assistance · Ticket {response.ticket_id}"
            )
        else:
            st.success("Answered from the tenant Knowledge Base.")


def _render_authenticated_tenant_support(
    tenant: Mapping[str, Any],
    tenant_slug: str,
) -> None:
    identity = st.session_state.get(
        _tenant_key(tenant_slug, "internal", "identity")
    )
    if (
        not _tenant_access_is_authenticated("staff", tenant_slug)
        or not isinstance(identity, Mapping)
        or identity.get("tenant_slug") != tenant_slug
        or identity.get("role")
        not in {"admin", "tenant_admin", "directorate_staff"}
    ):
        st.info(
            "Sign in under Desk Operations · Staff before opening this "
            "tenant-scoped support gateway."
        )
        return
    if _render_tenant_support_panel is None:
        detail = (
            f" {_TENANT_SUPPORT_IMPORT_ERROR}"
            if _TENANT_SUPPORT_IMPORT_ERROR is not None
            else ""
        )
        st.error(f"The tenant support interface is unavailable.{detail}")
        return
    if _SUPPORT_KB_IMPORT_ERROR is not None:
        st.warning(
            "Automated Knowledge Base responses are unavailable; inquiries "
            "will still be routed for manual review."
        )
    ai_query_tab, feedback_tab = st.tabs(
        ["Tenant-Scoped AI Query", "Support & Feedback"]
    )
    with ai_query_tab:
        _render_tenant_ai_support_query(tenant_slug, identity)
    with feedback_tab:
        _render_tenant_support_panel(
            tenant_id=tenant_slug,
            tenant_slug=tenant_slug,
            org_name=str(tenant.get("full_corporation_name") or tenant_slug),
            create_ticket=_create_primary_tenant_support_ticket,
            get_tickets=db.get_tenant_support_tickets,
        )


def _render_internal_portal(tenant: Mapping[str, Any], tenant_slug: str) -> None:
    st.title("Internal Directorate Access")
    st.caption(str(tenant.get("full_corporation_name") or tenant_slug))

    staff_tab, executive_tab, committee_tab, support_tab = st.tabs(
        [
            "Desk Operations · Staff",
            "Executive Management",
            "Committee Workspace",
            "Support & Feedback Gateway",
        ]
    )

    with staff_tab:
        if _render_tenant_access_gate(tenant_slug, "staff"):
            identity_key = _tenant_key(tenant_slug, "internal", "identity")
            failed_key = _tenant_key(tenant_slug, "internal", "login_failed")
            identity = st.session_state.get(identity_key)
            if (
                not isinstance(identity, Mapping)
                or identity.get("tenant_slug") != tenant_slug
                or identity.get("role") not in _ALLOWED_INTERNAL_ROLES
            ):
                users = _configured_staff_users()
                if not users:
                    st.error(
                        "Desk operations are unavailable: no staff accounts are configured."
                    )
                else:
                    st.caption("Sign in with your tenant staff account to continue.")
                    with st.form(
                        key=_tenant_key(tenant_slug, "internal", "login_form")
                    ):
                        st.text_input(
                            "Staff username",
                            key=_tenant_key(tenant_slug, "internal", "username"),
                        )
                        st.text_input(
                            "Password",
                            type="password",
                            key=_tenant_key(tenant_slug, "internal", "password"),
                        )
                        st.form_submit_button(
                            "Sign in",
                            key=_tenant_key(tenant_slug, "internal", "login_submit"),
                            on_click=_handle_internal_login,
                            args=(tenant_slug,),
                        )

                    if st.session_state.get(failed_key, False):
                        st.error(
                            "Sign-in failed or this account is not authorized for this tenant."
                        )
            else:
                st.success(
                    f"Authenticated as {identity['username']} ({identity['role']})."
                )
                if identity["role"] not in {
                    "admin",
                    "tenant_admin",
                    "directorate_staff",
                }:
                    st.info(
                        "This account is not assigned to desk or directorate "
                        "operations. Open the committee workspace when it is provisioned."
                    )
                else:
                    try:
                        broadcast = db.get_general_broadcast()
                    except (sqlite3.Error, RuntimeError):
                        logging.exception(
                            "Could not load tenant administrator broadcast for %s.",
                            tenant_slug,
                        )
                        st.warning("The platform broadcast is temporarily unavailable.")
                    else:
                        if broadcast is not None:
                            st.info(
                                f"**Platform broadcast** · Updated "
                                f"{broadcast['updated_at']}\n\n{broadcast['message']}"
                            )

                    st.subheader("Tenant profile")
                    st.write(
                        "Institution category:",
                        tenant.get("institution_category") or "Not configured",
                    )
                    st.write(
                        "Executive title:",
                        tenant.get("apex_title") or "Not configured",
                    )
                    _render_physical_proposal_intake(
                        tenant,
                        tenant_slug,
                        str(identity["username"]),
                    )
                    _render_departmental_directorate_interface(
                        tenant,
                        tenant_slug,
                        identity,
                    )

                if st.button(
                    "Sign out of desk operations",
                    key=_tenant_key(tenant_slug, "internal", "logout"),
                ):
                    st.session_state.pop(identity_key, None)
                    st.session_state.pop("tenant_staff_auth", None)
                    st.session_state.pop("tenant_staff_auth_slug", None)
                    st.rerun()

    with executive_tab:
        if _render_tenant_access_gate(tenant_slug, "executive"):
            st.success("Executive / Management access granted for this tenant.")
            _render_executive_command_center(
                tenant,
                tenant_slug,
            )
            with st.container():
                if render_pdf_export_widget is None:
                    detail = (
                        f" {_PDF_EXPORTER_IMPORT_ERROR}"
                        if _PDF_EXPORTER_IMPORT_ERROR is not None
                        else ""
                    )
                    st.error(f"The Executive PDF Briefing exporter is unavailable.{detail}")
                else:
                    render_pdf_export_widget(tenant_slug=tenant_slug)
            if st.button(
                "Sign out of executive management",
                key=_tenant_key(tenant_slug, "internal", "executive_logout"),
            ):
                st.session_state.pop("tenant_exec_auth", None)
                st.session_state.pop("tenant_exec_auth_slug", None)
                st.rerun()

    with committee_tab:
        _render_committee_workspace(tenant_slug)

    with support_tab:
        _render_authenticated_tenant_support(tenant, tenant_slug)


def _render_vendor_portal(
    tenant_slug: str,
    intake_type: str | None = None,
) -> None:
    from sector_logic import render_unified_vendor_portal

    render_unified_vendor_portal(
        tenant_slug=tenant_slug,
        key_prefix=f"tenant:{tenant_slug}:vendor",
        intake_type=intake_type,
    )


def _tenant_logo_directory() -> Path:
    return Path(
        os.environ.get(
            "NEXUSVAULT_TENANT_LOGO_DIR",
            Path(__file__).resolve().parent / "uploads" / "tenant_logos",
        )
    ).expanduser()


def _store_tenant_logo(tenant_slug: str, uploaded_logo: Any) -> str:
    image_bytes = uploaded_logo.getvalue()
    if not image_bytes:
        raise ValueError("The uploaded institution logo is empty.")
    if len(image_bytes) > 10 * 1024 * 1024:
        raise ValueError("Institution logos must be 10 MB or smaller.")

    try:
        with Image.open(BytesIO(image_bytes)) as source:
            source.load()
            if source.width * source.height > 16_000_000:
                raise ValueError("Institution logos must be 16 megapixels or smaller.")
            image = source.convert("RGBA" if "A" in source.getbands() else "RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Upload a valid PNG or JPEG institution logo.") from exc

    logo_directory = _tenant_logo_directory()
    logo_directory.mkdir(parents=True, exist_ok=True)
    logo_filename = f"{tenant_slug}.png"
    destination = logo_directory / logo_filename
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=logo_directory,
            prefix=".tenant-logo-",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            image.save(temporary_file, format="PNG")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, destination)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise

    return logo_filename


def _tenant_audit_actor(tenant_slug: str) -> str:
    identity = st.session_state.get(_tenant_key(tenant_slug, "internal", "identity"))
    if isinstance(identity, Mapping) and identity.get("tenant_slug") == tenant_slug:
        username = identity.get("username")
        if isinstance(username, str) and username.strip():
            return username.strip()
    if _tenant_access_is_authenticated("executive", tenant_slug):
        return "tenant_executive"
    if _tenant_access_is_authenticated("staff", tenant_slug):
        return "tenant_staff"
    return "tenant_user"


def _toggle_tenant_audit(tenant_slug: str, open_key: str) -> None:
    if st.session_state.get("_active_tenant_slug") != tenant_slug:
        return
    if st.session_state.get(open_key, False):
        st.session_state[open_key] = False
        return

    st.session_state[open_key] = True
    if not (
        _tenant_access_is_authenticated("staff", tenant_slug)
        or _tenant_access_is_authenticated("executive", tenant_slug)
    ):
        return
    try:
        db.log_tenant_activity(
            tenant_slug,
            _tenant_audit_actor(tenant_slug),
            "audit_log_opened",
            "Opened the tenant activity log.",
        )
        st.session_state.pop(_tenant_key(tenant_slug, "audit", "error"), None)
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception("Could not record audit log access for %s.", tenant_slug)
        st.session_state[_tenant_key(tenant_slug, "audit", "error")] = (
            "Audit log access could not be recorded."
        )


def _open_tenant_audit_entry(tenant_slug: str, activity_id: int) -> None:
    if st.session_state.get("_active_tenant_slug") != tenant_slug or not (
        _tenant_access_is_authenticated("staff", tenant_slug)
        or _tenant_access_is_authenticated("executive", tenant_slug)
    ):
        return
    st.session_state[_tenant_key(tenant_slug, "audit", "selected_id")] = activity_id
    try:
        db.log_tenant_activity(
            tenant_slug,
            _tenant_audit_actor(tenant_slug),
            "audit_entry_opened",
            f"Opened tenant audit entry {activity_id}.",
        )
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception("Could not record audit entry access for %s.", tenant_slug)


def _delete_tenant_audit_entry(tenant_slug: str, activity_id: int) -> None:
    if st.session_state.get(
        "_active_tenant_slug"
    ) != tenant_slug or not _tenant_access_is_authenticated("executive", tenant_slug):
        st.session_state[_tenant_key(tenant_slug, "audit", "error")] = (
            "Executive tenant access is required to delete audit records."
        )
        return
    try:
        deleted = db.delete_tenant_activity(
            activity_id,
            tenant_slug,
            actor=_tenant_audit_actor(tenant_slug),
        )
    except (sqlite3.Error, RuntimeError, TypeError, ValueError):
        logging.exception(
            "Could not delete audit entry %s for tenant %s.",
            activity_id,
            tenant_slug,
        )
        st.session_state[_tenant_key(tenant_slug, "audit", "error")] = (
            "The audit entry could not be deleted."
        )
        return

    if deleted:
        st.session_state.pop(_tenant_key(tenant_slug, "audit", "selected_id"), None)
        st.session_state.pop(_tenant_key(tenant_slug, "audit", "error"), None)
    else:
        st.session_state[_tenant_key(tenant_slug, "audit", "error")] = (
            "That audit entry is no longer available for this tenant."
        )


def _render_tenant_audit_drawer(tenant_slug: str) -> None:
    open_key = _tenant_key(tenant_slug, "audit", "open")
    if not st.session_state.get(open_key, False):
        return

    with st.expander("Tenant Activity Log", expanded=True):
        st.caption("Activity records are scoped to this tenant.")
        is_staff = _tenant_access_is_authenticated("staff", tenant_slug)
        is_executive = _tenant_access_is_authenticated("executive", tenant_slug)
        if not (is_staff or is_executive):
            st.info(
                "Sign in to this tenant's internal portal to view activity records."
            )
            return

        error_key = _tenant_key(tenant_slug, "audit", "error")
        error_message = st.session_state.get(error_key)
        if isinstance(error_message, str) and error_message:
            st.error(error_message)

        try:
            activities = db.get_tenant_activities(tenant_slug)
        except (sqlite3.Error, RuntimeError, ValueError):
            logging.exception("Could not load audit trail for tenant %s.", tenant_slug)
            st.error("The tenant activity log is temporarily unavailable.")
            return

        if not activities:
            st.info("No activity has been recorded for this tenant yet.")
            return

        selected_key = _tenant_key(tenant_slug, "audit", "selected_id")
        selected_id = st.session_state.get(selected_key)
        for activity in activities:
            activity_id = activity["id"]
            try:
                timestamp = datetime.fromisoformat(activity["timestamp"])
                date_text = timestamp.strftime("%Y-%m-%d")
                time_text = timestamp.strftime("%H:%M:%S %z").strip()
                year_text = timestamp.strftime("%Y")
            except (TypeError, ValueError):
                logging.error("Audit record %s has an invalid timestamp.", activity_id)
                date_text = time_text = year_text = "Unknown"

            with st.container():
                summary, open_column, delete_column = st.columns([6, 1, 1])
                summary.write(
                    f"{date_text} · {time_text} · {year_text}\n"
                    f"{activity['action_type']} · {activity['actor']}"
                )
                open_column.button(
                    "Open",
                    key=_tenant_key(tenant_slug, "audit", f"open_entry_{activity_id}"),
                    on_click=_open_tenant_audit_entry,
                    args=(tenant_slug, activity_id),
                    help="Open this activity's details.",
                )
                delete_column.button(
                    "Delete",
                    key=_tenant_key(
                        tenant_slug, "audit", f"delete_entry_{activity_id}"
                    ),
                    on_click=_delete_tenant_audit_entry,
                    args=(tenant_slug, activity_id),
                    disabled=not is_executive,
                    help=(
                        "Executive tenant access is required to delete audit records."
                        if not is_executive
                        else "Delete this activity record."
                    ),
                )
                if selected_id == activity_id:
                    st.write("**Date:**", date_text)
                    st.write("**Time:**", time_text)
                    st.write("**Year:**", year_text)
                    st.write("**Actor:**", activity["actor"])
                    st.write("**Action:**", activity["action_type"])
                    st.write("**Details:**", activity["details"])


def render_sovereign_tenant_header(tenant_data: Mapping[str, Any]) -> None:
    tenant_slug = str(tenant_data.get("tenant_slug") or "").strip().lower()
    institution_name = str(
        tenant_data.get("full_corporation_name") or tenant_slug or "Client Institution"
    ).strip()
    safe_name = html.escape(institution_name)

    st.markdown(
        """
        <style>
        .sovereign-tenant-banner {
            background: linear-gradient(135deg, #0a192f 0%, #14283f 100%);
            border: 1px solid rgba(255, 182, 193, 0.4);
            border-radius: 16px;
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.22);
            margin: 0.5rem 0 1.5rem;
            padding: 1.5rem 1.75rem;
        }
        .sovereign-tenant-name {
            color: #FFB6C1;
            font-size: clamp(1.5rem, 3vw, 2.4rem);
            font-weight: 850;
            letter-spacing: 0.01em;
            line-height: 1.2;
            margin: 0 0 0.45rem;
            overflow-wrap: anywhere;
        }
        .sovereign-tenant-subtitle {
            color: #FFB6C1;
            font-size: 1rem;
            font-weight: 600;
            margin: 0 0 1rem;
        }
        .sovereign-compliance-badge {
            border: 1px solid rgba(255, 182, 193, 0.65);
            border-radius: 999px;
            color: #FFB6C1;
            display: inline-block;
            font-size: 0.82rem;
            font-weight: 750;
            line-height: 1.4;
            padding: 0.4rem 0.75rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    left, right = st.columns([5, 1])
    with left:
        st.markdown(
            f"""
            <section class="sovereign-tenant-banner">
                <h1 class="sovereign-tenant-name">{safe_name}</h1>
                <p class="sovereign-tenant-subtitle">
                    Sovereign Enterprise Intake &amp; Governance Portal
                </p>
                <span class="sovereign-compliance-badge">
                    NEXUSVAULT_TECH Sovereign Enterprise Engine • NITDA / NDPA Compliant
                </span>
            </section>
            """,
            unsafe_allow_html=True,
        )

    logo_filename = tenant_data.get("logo_path")
    if (
        tenant_slug
        and isinstance(logo_filename, str)
        and logo_filename == f"{tenant_slug}.png"
    ):
        logo_directory = _tenant_logo_directory()
        logo_path = logo_directory / logo_filename
        try:
            if not logo_path.is_symlink() and logo_path.is_file():
                if logo_path.resolve().parent != logo_directory.resolve():
                    raise RuntimeError(
                        "Tenant logo resolves outside its configured directory."
                    )
                with right:
                    st.image(str(logo_path), width=140)
        except (OSError, RuntimeError):
            logging.exception("Could not verify the tenant logo for %s.", tenant_slug)
            st.warning("The institution logo could not be loaded.")

    if not tenant_slug:
        return
    open_key = _tenant_key(tenant_slug, "audit", "open")
    st.button(
        "Audit Log / Ctrl+H",
        key=_tenant_key(tenant_slug, "audit", "toggle"),
        on_click=_toggle_tenant_audit,
        args=(tenant_slug, open_key),
        help="Open or close this tenant's activity log.",
    )
    st.markdown(
        """
        <script>
        (() => {
            const parentDocument = window.parent.document;
            if (parentDocument.__nexusVaultAuditShortcutInstalled) return;
            parentDocument.__nexusVaultAuditShortcutInstalled = true;
            parentDocument.addEventListener("keydown", (event) => {
                if (!(event.ctrlKey || event.metaKey) ||
                    event.key.toLowerCase() !== "h") return;
                event.preventDefault();
                const auditButton = Array.from(
                    parentDocument.querySelectorAll("button")
                ).find((button) =>
                    button.innerText.trim() === "Audit Log / Ctrl+H"
                );
                if (auditButton) auditButton.click();
            }, true);
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )
    _render_tenant_audit_drawer(tenant_slug)


def _render_home() -> None:
    inject_sovereign_workspace_css()
    st.session_state["_primary_workspace"] = "Onboarding Portal"
    st.session_state["_primary_workspace_selection"] = "Onboarding Portal"

    if "custom_portal_heading" not in st.session_state:
        st.session_state["custom_portal_heading"] = (
            'NEXUSVAULT TECHNOLOGIES "SUPER INTELLIGENCE - '
            'AGENTIC AI PROPOSAL INTAKE PORTAL".'
        )

    if st.session_state.get("onboarding_submitted", False):
        st.session_state.pop("onboarding_success_message", None)
        tenant_id = str(st.session_state.get("onboarded_tenant_id", ""))
        if not tenant_id:
            logging.error("Onboarded tenant lifecycle ID is missing from the session.")
            st.error("Unable to load the onboarding lifecycle status.")
            return

        database = NexusDatabaseAdapter()
        engine = NexusTenantLifecycleEngine(database)
        tenant_row = database.get_tenant(tenant_id)
        if tenant_row is None:
            logging.error("Onboarded tenant %s was not found in nv_tenants.", tenant_id)
            st.error("Unable to load the onboarding lifecycle status.")
            return

        tenant_slug = str(tenant_row["slug"])
        vendor_url = _tenant_portal_url("vendor", tenant_slug, "unsolicited")
        render_tenant_banner(tenant_row, engine)
        if str(tenant_row["status"]).strip().upper() == "DEMO_ACTIVE":
            org_url = _tenant_portal_url("internal", tenant_slug)
            st.markdown(
                textwrap.dedent(
                    """
                    <div style="background: linear-gradient(135deg, #064e3b 0%, #0f172a 100%); border: 1px solid #10b981; border-left: 5px solid #34d399; border-radius: 12px; padding: 24px; color: #f8fafc; margin-top: 16px; margin-bottom: 16px;">
                        <h3 style="color: #f8fafc; margin: 0 0 12px 0;">✅ Organisational Profile Provisioned — 14-Day Free Trial Initiated</h3>
                        <p style="color: #f8fafc; margin: 0; line-height: 1.7;">
                            Your organisational credentials have been profiled for a <strong>14-day free trial</strong>, subject to final system activation. Please copy and securely retain your dedicated <strong>Organisational URL</strong> below, and take note of the following operational activation protocols across your <strong>solicited and unsolicited</strong> gateways:
                        </p>
                    </div>
                    """
                ).strip(),
                unsafe_allow_html=True,
            )
            st.code(org_url, language=None)
            st.markdown(
                textwrap.dedent(
                    """
                    <div style="background: linear-gradient(135deg, #064e3b 0%, #0f172a 100%); border: 1px solid #10b981; border-left: 5px solid #34d399; border-radius: 12px; padding: 24px; color: #f8fafc; margin-top: 16px; margin-bottom: 16px;">
                        <ol style="color: #f8fafc; margin: 0; padding-left: 20px; line-height: 1.7;">
                            <li><strong>Unsolicited Proposals &amp; Vendors Portal:</strong> Your public portal for receiving, indexing, and standardizing unsolicited proposals and vendor pre-qualifications becomes active immediately upon <strong>Developer Activation</strong>.</li>
                            <li><strong>Solicited Tenders Portal:</strong> Your formal competitive tender submission gateway becomes active once you input specific tender parameters and activate them within your <strong>Internal Administrative Workspace</strong>.</li>
                            <li><strong>Desk Officer &amp; Registry Workspace:</strong> Your statutory evaluation, vetting, and registry command center—governing both solicited bids and unsolicited submissions—becomes active upon <strong>Full Developer Activation</strong>.</li>
                        </ol>
                    </div>
                    """
                ).strip(),
                unsafe_allow_html=True,
            )
        st.caption("Production unsolicited portal URL (available after activation)")
        st.code(vendor_url, language="text")
        if st.button("Return to Onboarding Portal", use_container_width=True):
            st.session_state["onboarding_submitted"] = False
            st.rerun()
        return

    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap');

            .stApp {
                background: radial-gradient(circle at 50% 0%, #0d1b2a 0%, #070d19 70%) !important;
                color: #f8fafc !important;
                font-family: 'Plus Jakarta Sans', sans-serif !important;
            }

            .onboarding-title-banner {
                text-align: center;
                margin: 35px 0;
                padding: 16px;
                background: rgba(15, 23, 42, 0.6);
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
            }

            .onboarding-title-banner h2 {
                color: #38bdf8 !important;
                font-size: 28px !important;
                font-weight: 900 !important;
                letter-spacing: 2px !important;
                text-transform: uppercase !important;
                margin: 0 !important;
                text-shadow: 0 0 15px rgba(56, 189, 248, 0.4);
            }

            .section-hdr {
                color: #38bdf8 !important;
                font-size: 20px !important;
                font-weight: 800 !important;
                letter-spacing: 0.3px !important;
                border-left: 4px solid #38bdf8;
                padding-left: 12px;
                margin: 22px 0 16px;
                text-shadow: 0 0 12px rgba(56, 189, 248, 0.2);
            }

            label, div[data-baseweb="select"] span {
                color: #f8fafc !important;
                font-family: 'Plus Jakarta Sans', sans-serif !important;
                font-weight: 600 !important;
            }

            div[data-baseweb="select"] > div {
                background-color: rgba(15, 23, 42, 0.75) !important;
                border: 1px solid rgba(255, 255, 255, 0.1) !important;
                color: #FF5C8A !important;
                border-radius: 10px !important;
                backdrop-filter: blur(10px) !important;
            }

            .marquee-container {
                margin: 20px 0 15px;
                overflow: hidden;
                white-space: nowrap;
                background: rgba(15, 23, 42, 0.85);
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 8px;
                padding: 10px 0;
            }

            .marquee-text {
                display: inline-block;
                padding-left: 100%;
                animation: marquee 18s linear infinite;
                color: #FF5C8A;
                font-weight: 900;
                font-size: 20px;
                letter-spacing: 1px;
            }

            @keyframes marquee {
                0% { transform: translate(0, 0); }
                100% { transform: translate(-100%, 0); }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    safe_heading = html.escape(str(st.session_state["custom_portal_heading"]))
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, rgba(10, 25, 47, 0.85) 0%, rgba(13, 33, 55, 0.85) 100%);
                    backdrop-filter: blur(16px); padding: 32px 36px; border-radius: 16px;
                    border: 1px solid rgba(56, 189, 248, 0.25);
                    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5), 0 0 20px rgba(56, 189, 248, 0.1);
                    margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center;
                        flex-wrap: wrap; gap: 20px;">
                <div style="flex: 1; min-width: 320px;">
                    <h1 style="color: #FF5C8A !important; color: #FF5C8A; margin: 0 0 10px 0; font-size: 25px;
                               font-weight: 900; letter-spacing: 0.4px; line-height: 1.3;
                               font-family: 'Plus Jakarta Sans', sans-serif;">
                        🛡️ {safe_heading}
                    </h1>
                    <p style="color: #cbd5e1 !important; margin: 0 0 14px 0; font-size: 15px;
                              font-weight: 500; line-height: 1.5;
                              font-family: 'Plus Jakarta Sans', sans-serif;">
                        Initialize your secure organizational node, configure your domain scope,
                        and deploy your sovereign enterprise proposal intake gateway.
                    </p>
                    <div style="display: inline-flex; align-items: center;
                                background: rgba(56, 189, 248, 0.12);
                                border: 1px solid rgba(56, 189, 248, 0.4); border-radius: 8px;
                                padding: 6px 14px; gap: 8px;">
                        <span style="color: #00FF66; font-size: inherit; font-weight: bold; text-align: center;">
                            🔒 NEXUSVAULT_TECH Sovereign Enterprise Engine • NITDA / NDPA Compliant
                        </span>
                    </div>
                </div>
                <div style="display: flex; align-items: center;
                            background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(10px);
                            border: 1px solid rgba(0, 135, 81, 0.5); border-radius: 12px;
                            padding: 12px 20px; gap: 14px;">
                    <svg width="42" height="28" viewBox="0 0 3 2" style="border-radius: 4px;">
                        <rect width="1" height="2" x="0" fill="#008751"/>
                        <rect width="1" height="2" x="1" fill="#FFFFFF"/>
                        <rect width="1" height="2" x="2" fill="#008751"/>
                    </svg>
                    <div>
                        <div style="color: #FF5C8A; font-size: 12px; font-weight: 800;
                                    font-family: 'Plus Jakarta Sans', sans-serif;">FEDERAL REPUBLIC</div>
                        <div style="color: #34d399; font-size: 10px; font-weight: 700;
                                    font-family: 'Plus Jakarta Sans', sans-serif;">OF NIGERIA</div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        textwrap.dedent(
            """
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); border-left: 4px solid #38bdf8; border-radius: 12px; padding: 24px; color: #f8fafc; margin-bottom: 24px;">
                <h3 style="color: #f8fafc; margin: 0 0 12px 0;">About NexusVault</h3>
                <p style="color: #f8fafc; margin: 0; line-height: 1.7;">
                    NexusVault is a pioneering <strong>Digital Technology company</strong> that engineered the <strong>NexusVault Sovereign GovTech Portal</strong>—a first-of-its-kind <strong>Agentic AI Proposal Intake &amp; Bid-Evaluation System</strong> engineered to streamline both solicited tender workflows and unsolicited proposal intake, enforce strict <strong>BPP statutory compliance</strong>, and guarantee <strong>cryptographic auditability</strong> across public and institutional procurement lifecycles. By standardizing how solicited bids and unsolicited proposals are received, structured, and evaluated, the platform eliminates ad-hoc paper bottlenecks and elevates organisational efficiency across every administrative tier. Powered by autonomous AI vetting agents, NexusVault automatically parses vendor compliance credentials (CAC, Tax Clearance, PENCOM, ITF, NSITF, BPP IRR), flags statutory discrepancies in real time, and generates objective scoring matrices for evaluation committees—transforming weeks of manual registry verification into a tamper-evident, single-screen executive workflow.
                </p>
            </div>
            """
        ).strip(),
        unsafe_allow_html=True,
    )
    tab_new_onboard, tab_returning_login = st.tabs(
        [
            "🆕 New Organizational Onboarding",
            "🔑 Returning Client Login / Resume Workspace",
        ]
    )

    with tab_returning_login:
        st.markdown(
            """
            <div style="background:rgba(15,23,42,0.78);border:1px solid rgba(56,189,248,0.35);
                        border-radius:12px;padding:1.25rem 1.4rem;margin:0.75rem 0 1.1rem 0;">
                <div style="font-size:0.78rem;font-weight:800;letter-spacing:0.12em;color:#38BDF8;text-transform:uppercase;">
                    CONTINUATION &amp; DEFERRED ACTIVATION PORTAL
                </div>
                <div style="font-size:1.05rem;font-weight:700;color:#F8FAFC;margin-top:0.25rem;">
                    Resume Your Provisioned Organizational Slug or Complete Subscription Activation
                </div>
                <div style="font-size:0.86rem;color:#CBD5E1;margin-top:0.35rem;">
                    If you previously selected <strong>LATER</strong> during onboarding, enter your
                    <strong>Organizational Workspace Slug</strong> or <strong>Registered Admin Email</strong> below
                    to jump straight back to your saved workspace.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        resume_identifier = st.text_input(
            "Organizational Workspace Slug or Registered Admin Email *",
            placeholder="e.g., federalministry_a1b2c3d4 or admin@organization.gov.ng",
            key="returning_tenant_identifier_input",
        )
        if st.button(
            "Access Provisioned Workspace & Subscription Portal",
            type="primary",
            use_container_width=True,
            key="btn_returning_tenant_resume",
        ):
            ident = resume_identifier.strip()
            if not ident:
                st.warning("Please enter your Organizational Workspace Slug or Registered Admin Email.")
            else:
                try:
                    resume_db = NexusDatabaseAdapter()
                    resume_engine = NexusTenantLifecycleEngine(resume_db)
                    matched_tenant = None
                    if hasattr(resume_engine, "resume_login"):
                        try:
                            matched_tenant = resume_engine.resume_login(ident)
                        except Exception:
                            matched_tenant = None
                    if matched_tenant is None and hasattr(resume_db, "get_tenant_by_slug"):
                        matched_tenant = resume_db.get_tenant_by_slug(ident.lower())
                    if matched_tenant is None and hasattr(resume_db, "get_tenant_by_email"):
                        matched_tenant = resume_db.get_tenant_by_email(ident.lower())
                    if matched_tenant is None and hasattr(resume_db, "list_tenants"):
                        for candidate in resume_db.list_tenants():
                            c_slug = str(candidate.get("slug", "")).strip().lower()
                            c_email = str(candidate.get("admin_email", "")).strip().lower()
                            if ident.lower() in {c_slug, c_email}:
                                matched_tenant = candidate
                                break
                    if matched_tenant is None:
                        st.error(
                            "No provisioned organizational workspace matched that slug or admin email. "
                            "Please verify your credentials or complete New Organizational Onboarding."
                        )
                    else:
                        st.session_state["onboarded_tenant_id"] = str(matched_tenant["tenant_id"])
                        st.session_state["onboarded_tenant_slug"] = str(matched_tenant["slug"])
                        st.session_state["corp_name"] = str(matched_tenant.get("org_name", ""))
                        st.session_state["admin_email"] = str(matched_tenant.get("admin_email", ""))
                        st.session_state["show_tenant_checkout"] = False
                        st.session_state["onboarding_submitted"] = True
                        st.rerun()
                except Exception as exc:
                    logging.exception("Returning client resume login failed.")
                    st.error(f"Unable to resume tenant session: {exc}")

    with tab_new_onboard:
        st.markdown(
            """
            <div class="onboarding-title-banner">
                <h2>👉 ONBOARDING MODULE 👇</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )

        confirm_final_onboard = False
        if st.session_state.get("onboarding_review_mode", False) and not st.session_state.get("onboarding_submitted", False):
            draft = st.session_state.get("onboarding_draft_payload", {})
            st.markdown(
                """
                <div style="background:linear-gradient(135deg,#0B192C 0%,#132A46 100%);
                            border:1.5px solid #38BDF8;border-radius:12px;padding:1.25rem 1.4rem;margin-bottom:1rem;">
                    <div style="font-size:0.75rem;font-weight:800;letter-spacing:0.12em;color:#38BDF8;text-transform:uppercase;">
                        PRE-SUBMISSION CREDENTIAL VERIFICATION
                    </div>
                    <div style="font-size:1.08rem;font-weight:800;color:#FFFFFF;margin-top:0.25rem;">
                        Review Your Organizational Credentials Before Final Activation Submission
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.table(
                [
                    {"Credential Field": "Entity Category", "Entered Value": draft.get("entity_type", "")},
                    {"Credential Field": "Organizational Entity Name", "Entered Value": draft.get("org", "")},
                    {"Credential Field": "Official Corporate Email", "Entered Value": draft.get("email", "")},
                    {"Credential Field": "Designated Admin Email", "Entered Value": draft.get("admin_email", "")},
                    {"Credential Field": "Official Phone Line", "Entered Value": draft.get("phone", "")},
                    {"Credential Field": "Headquarters Address", "Entered Value": draft.get("address", "")},
                    {"Credential Field": "Custom Portal Heading", "Entered Value": draft.get("custom_title", "")},
                    {"Credential Field": "Selected SaaS Sovereign Tier", "Entered Value": draft.get("sub_package", "")},
                ]
            )
            col_edit_btn, col_confirm_btn = st.columns(2)
            with col_edit_btn:
                if st.button("✏️ Edit Organizational Credentials", use_container_width=True, key="btn_edit_onboard_draft"):
                    st.session_state["onboarding_review_mode"] = False
                    st.rerun()
            with col_confirm_btn:
                confirm_final_onboard = st.button(
                    "✅ Confirm & Submit Organizational Node for Activation",
                    type="primary",
                    use_container_width=True,
                    key="btn_confirm_final_onboard",
                )
        review_active = bool(
            st.session_state.get("onboarding_review_mode", False)
            and not st.session_state.get("onboarding_submitted", False)
        )
        submitted = False
        preview_before_submit = False
        uploaded_logo = None
        if review_active:
            uploaded_logo = st.session_state.get("onboarding_draft_logo")

        if not review_active:
            with st.form("corporate_onboarding_form"):
                st.markdown(
                    "<div class='section-hdr'>🏢 Step 1: Organizational Classification & "
                    "Domain Setup</div>",
                    unsafe_allow_html=True,
                )
                entity_type = st.selectbox(
                    "Select Organization / Entity Category*",
                    [
                        "Public University / Polytechnic / Research Institute (Academic Sector)",
                        "Multinational Funder / UN Agency / International NGO (Humanitarian Sector)",
                        "National Assembly / Parliament / Legislative Directorate",
                        "Federal Ministry, Department, or Agency (MDA)",
                        "State Ministry, Department, or Agency (MDA)",
                        "Private Limited Company / Enterprise (Commercial Sector)",
                        "Non-Profit Foundation / Civil Society Organization",
                    ],
                )

                col_a, col_b = st.columns(2)
                with col_a:
                    corp_name = st.text_input(
                        "Organizational Entity Name*",
                        placeholder="e.g., Federal Ministry of Technology",
                    )
                    corp_email = st.text_input(
                        "Official Dispatch Email*",
                        placeholder="contact@entity.gov.ng",
                    )

                with col_b:
                    corp_phone = st.text_input(
                        "Official Phone / SMS Gateway Contact*",
                        placeholder="+234 803 000 0000",
                    )
                    corp_address = st.text_input(
                        "Institutional Headquarters Address*",
                        placeholder="Central Area, Abuja",
                    )
                    admin_email = st.text_input(
                        "Executive Chief Notification Node",
                        placeholder="executive-office@entity.org",
                    )

                st.markdown(
                    "<div class='section-hdr'>🎨 Step 2: Branding & Custom Portal "
                    "Heading</div>",
                    unsafe_allow_html=True,
                )
                col_c, col_d = st.columns(2)
                with col_c:
                    custom_title_input = st.text_input(
                        "Custom Portal Banner Title",
                        value=st.session_state["custom_portal_heading"],
                    )
                    sub_package = st.selectbox(
                        "SaaS Sovereign Tier*",
                        [
                            "Sovereign Legislative & Statutory Node",
                            "Custom Government Parastatal Node",
                            "Enterprise Commercial Node",
                            "NGO & Donor Grant Node",
                            "Sovereign Academic Research Node",
                        ],
                    )
                with col_d:
                    uploaded_logo = st.file_uploader(
                        "Upload Official Institutional Branding Logo (PNG/JPG)",
                        type=["png", "jpg", "jpeg"],
                    )

                preview_before_submit = st.checkbox(
                    "🔍 Review & Verify Credentials on Summary Card Before Final Commit (Uncheck to Submit Immediately)",
                    value=False,
                )
                submitted = st.form_submit_button(
                    "Submit Organizational Node for Approval and Activation",
                    use_container_width=True,
                )

        if submitted or confirm_final_onboard:
            if confirm_final_onboard and st.session_state.get("onboarding_draft_payload"):
                _d = st.session_state["onboarding_draft_payload"]
                org = _d["org"]
                email = _d["email"]
                phone = _d["phone"]
                address = _d["address"]
                entity_type = _d["entity_type"]
                admin_email = _d["admin_email"]
                custom_title_input = _d["custom_title"]
                sub_package = _d["sub_package"]
            else:
                org = corp_name.strip()
                email = corp_email.strip()
                phone = corp_phone.strip()
                address = corp_address.strip()
            if not org or not email or not phone or not address:
                st.error(
                    "⚠️ Please fill in all required organizational entity fields "
                    "marked with an asterisk (*)."
                )
            elif submitted and preview_before_submit and not confirm_final_onboard:
                st.session_state["onboarding_draft_payload"] = {
                    "entity_type": entity_type,
                    "org": org,
                    "email": email,
                    "admin_email": admin_email.strip() or email,
                    "phone": phone,
                    "address": address,
                    "custom_title": custom_title_input.strip(),
                    "sub_package": sub_package,
                }
                st.session_state["onboarding_draft_logo"] = uploaded_logo
                st.session_state["onboarding_review_mode"] = True
                st.rerun()
            else:
                st.session_state["onboarding_review_mode"] = False
                client_id = str(uuid.uuid4())[:8]
                slug_prefix = re.sub(r"[^a-zA-Z0-9]", "", org.lower())[:15] or "tenant"
                tenant_slug = f"{slug_prefix}_{client_id}"
                logo_filename = ""
                logo_file_path: Path | None = None
                try:
                    if uploaded_logo is not None:
                        logo_filename = _store_tenant_logo(tenant_slug, uploaded_logo)
                        logo_file_path = _tenant_logo_directory() / logo_filename
                    db.create_tenant_onboarding(
                        {
                            "tenant_slug": tenant_slug,
                            "full_corporation_name": org,
                            "institution_category": entity_type,
                            "logo_path": logo_filename,
                            "cac_registration_number": "N/A",
                            "admin_email": admin_email.strip() or email,
                            "admin_phone": phone,
                        }
                    )
                    lifecycle_database = NexusDatabaseAdapter()
                    lifecycle_engine = NexusTenantLifecycleEngine(lifecycle_database)
                    lifecycle_tenant = lifecycle_engine.register_tenant(
                        org,
                        admin_email.strip() or email,
                    )
                except Exception as exc:
                    logging.exception("Tenant onboarding failed.")
                    if logo_file_path is not None:
                        try:
                            logo_file_path.unlink(missing_ok=True)
                        except OSError:
                            logging.exception(
                                "Could not remove the unregistered logo for tenant %s.",
                                tenant_slug,
                            )
                    st.error(f"Tenant onboarding failed: {exc}")
                else:
                    st.session_state["current_client_id"] = client_id
                    st.session_state["entity_type"] = entity_type
                    st.session_state["corp_name"] = org
                    st.session_state["corp_email"] = email
                    st.session_state["corp_phone"] = phone
                    st.session_state["corp_address"] = address
                    st.session_state["sub_package"] = sub_package
                    st.session_state["admin_email"] = admin_email.strip() or email
                    st.session_state["custom_portal_heading"] = custom_title_input.strip()
                    st.session_state["onboarded_tenant_slug"] = lifecycle_tenant["slug"]
                    st.session_state["onboarded_tenant_id"] = lifecycle_tenant["tenant_id"]
                    st.session_state["onboarding_submitted"] = True
                    st.rerun()

    st.markdown(
        """
        <div class="marquee-container">
            <div class="marquee-text">
                CONSOLIDATING THE DIGITAL ECONOMIC VISION OF THE GOVERNMENT THROUGH INNOVATIVE TECHNOLOGIES
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.markdown(
        "<div style='color: #00FF66; font-weight: bold; text-align: center;'>NEXUSVAULT_TECH Sovereign Enterprise Engine • NITDA / NDPA Compliant</div>",
        unsafe_allow_html=True,
    )


def _render_route_error(message: str) -> None:
    st.title("Access unavailable")
    st.error(message)
    st.caption("Use a valid tenant-issued link or contact your platform administrator.")


def _send_tenant_activation_notification(tenant: Mapping[str, Any]) -> bool:
    recipient = str(tenant.get("admin_email") or "").strip()
    tenant_slug = str(tenant.get("tenant_slug") or "").strip()
    institution_name = str(tenant.get("full_corporation_name") or tenant_slug).strip()
    if not recipient:
        logging.warning(
            "Tenant %s has no onboarding email for activation notification.",
            tenant_slug,
        )
        return False

    internal_url = _tenant_portal_url("internal", tenant_slug)
    vendor_url = _tenant_portal_url("vendor", tenant_slug, "unsolicited")
    subject = f"Institutional node activated: {institution_name}"
    body = (
        f"Hello {institution_name},\n\n"
        "Your NexusVault institutional node has been activated.\n"
        f"Tenant slug: {tenant_slug}\n"
        f"Internal portal: {internal_url}\n"
        f"Open unsolicited submissions: {vendor_url}\n\n"
        "For security, passwords and shared access keys are not included in email. "
        "Use the access credentials provided to your authorized administrators."
    )
    try:
        import notifications
    except ImportError:
        logging.exception(
            "Tenant activation mail service is unavailable for %s.",
            tenant_slug,
        )
        sent = False
    else:
        sent = notifications.send_email_notification(
            subject,
            body,
            recipient,
        )[0]

    try:
        db.log_tenant_activity(
            tenant_slug,
            "developer",
            (
                "tenant_activation_notification_sent"
                if sent
                else "tenant_activation_notification_failed"
            ),
            (
                "Institutional activation details were emailed to the onboarding "
                "contact."
                if sent
                else "Activation email was not delivered; manual follow-up is required."
            ),
        )
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception(
            "Could not audit activation notification status for tenant %s.",
            tenant_slug,
        )
    return bool(sent)


def _render_platform_developer_console() -> None:
    st.markdown("## Sovereign Developer Command Console")
    st.markdown("Client tenant, archive, and platform broadcast management.")

    section = st.selectbox(
        "Platform operations",
        [
            "Tenant Activation",
            "Tenant Deactivation",
            "Tenant Deletion & Recycle Bin",
            "Slug & URL Registry",
            "Platform Broadcasts",
            "📋 Activity Audit Trail",
        ],
        key="developer_platform_section",
    )
    try:
        tenants = db.list_tenants() if section in {
            "Tenant Activation", "Tenant Deactivation", "Tenant Deletion & Recycle Bin",
            "Slug & URL Registry", "📋 Activity Audit Trail",
        } else []
        archived_tenants = (
            db.list_archived_tenants() if section == "Tenant Deletion & Recycle Bin" else []
        )
        recycle_bin_tenants = (
            db.list_recycle_bin_tenants() if section == "Tenant Deletion & Recycle Bin" else []
        )
        current_broadcast = (
            db.get_general_broadcast() if section == "Platform Broadcasts" else None
        )
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception("Developer console data failed to load.")
        st.error("Developer console data is unavailable. Please try again later.")
        return

    if section == "Platform Broadcasts" and "developer_broadcast_message" not in st.session_state:
        st.session_state["developer_broadcast_message"] = (
            current_broadcast["message"] if current_broadcast else ""
        )

    activation_feedback = st.session_state.pop(
        "_developer_activation_feedback",
        None,
    )
    if isinstance(activation_feedback, tuple) and len(activation_feedback) == 2:
        feedback_level, feedback_message = activation_feedback
        if feedback_level == "success":
            st.success(feedback_message)
        else:
            st.warning(feedback_message)

    if section == "Tenant Activation":
        activation_candidates = [
            tenant
            for tenant in tenants
            if str(tenant.get("status") or "").strip().upper()
            in {"PENDING", "PENDING ACTIVATION", "INACTIVE", "SUSPENDED"}
        ]
        if not activation_candidates:
            st.info("There are no pending or inactive institutional nodes.")
        for tenant in activation_candidates:
            slug = tenant["tenant_slug"]
            name = tenant.get("full_corporation_name") or slug
            status = tenant.get("status") or "Unknown"
            with st.expander(f"Tenant: {name} ({status})"):
                st.write(f"**Tenant slug:** `{slug}`")
                st.write(
                    "**Institution category:** "
                    f"{tenant.get('institution_category') or 'Not configured'}"
                )
                st.write(
                    "**Administrator contact:** "
                    f"{tenant.get('admin_email') or 'Not provided'} · "
                    f"{tenant.get('admin_phone') or 'Not provided'}"
                )
                if st.button(
                    "Activate Institutional Node",
                    key=f"activate_tenant_{slug}",
                    type="primary",
                ):
                    try:
                        activated = db.activate_tenant(slug)
                    except Exception as exc:
                        logging.exception("Tenant activation failed for slug %s.", slug)
                        st.error(f"Tenant {name} could not be activated: {exc}")
                    else:
                        if activated:
                            notification_sent = _send_tenant_activation_notification(
                                activated
                            )
                            st.session_state["_developer_activation_feedback"] = (
                                (
                                    "success",
                                    f"Tenant {name} activated and the "
                                    "activation details were emailed.",
                                )
                                if notification_sent
                                else (
                                    "warning",
                                    f"Tenant {name} activated, but the "
                                    "activation email was not delivered. "
                                    "Confirm SMTP settings and contact the "
                                    "onboarding administrator.",
                                )
                            )
                            st.rerun()
                        else:
                            st.error(
                                f"Tenant {name} is already active, deleted, "
                                "or no longer exists."
                            )

    if section == "Tenant Deactivation":
        active_tenants = [
            tenant
            for tenant in tenants
            if str(tenant.get("status") or "").strip().upper() == "ACTIVE"
        ]
        if not active_tenants:
            st.info("There are no active institutional nodes to deactivate.")
        for tenant in active_tenants:
            slug = tenant["tenant_slug"]
            name = tenant.get("full_corporation_name") or slug
            with st.expander(f"{name} · {slug}"):
                st.warning("Deactivation immediately blocks all tenant portal access.")
                confirmed = st.checkbox(
                    f"Confirm immediate access revocation for {name}",
                    key=f"confirm_deactivate_tenant_{slug}",
                )
                if st.button(
                    "Deactivate Tenant",
                    key=f"deactivate_tenant_{slug}",
                    disabled=not confirmed,
                    type="primary",
                ):
                    try:
                        deactivated = db.deactivate_tenant(slug)
                    except Exception as exc:
                        logging.exception(
                            "Tenant deactivation failed for slug %s.", slug
                        )
                        st.error(f"Tenant {name} could not be deactivated: {exc}")
                    else:
                        if deactivated:
                            st.success(f"Tenant {name} access has been revoked.")
                            st.rerun()
                        else:
                            st.error(
                                f"Tenant {name} is no longer active or has been deleted."
                            )

    if section == "Tenant Deletion & Recycle Bin":
        st.markdown("### Tenant Deletion")
        for tenant in tenants:
            slug = tenant["tenant_slug"]
            name = tenant.get("full_corporation_name") or slug
            with st.expander(f"{name} · {slug}"):
                st.warning(
                    "This moves the tenant to the Recycle Bin and blocks access. "
                    "Tenant data is retained until permanent purge."
                )
                confirmed = st.checkbox(
                    f"Confirm moving {name} to the Recycle Bin",
                    key=f"confirm_soft_delete_tenant_{slug}",
                )
                if st.button(
                    "Move Tenant to Recycle Bin",
                    key=f"soft_delete_tenant_{slug}",
                    disabled=not confirmed,
                ):
                    try:
                        deleted = db.soft_delete_tenant(slug)
                    except (sqlite3.Error, RuntimeError, ValueError):
                        logging.exception("Could not soft-delete tenant %s.", slug)
                        st.error(
                            f"Tenant {name} could not be moved to the Recycle Bin."
                        )
                    else:
                        if deleted:
                            st.success(f"Tenant {name} moved to the Recycle Bin.")
                            st.rerun()
                        else:
                            st.error(f"Tenant {name} no longer exists.")

        st.markdown("### Recycle Bin")
        soft_deleted_slugs = {
            str(tenant["tenant_slug"]) for tenant in recycle_bin_tenants
        }
        for tenant in recycle_bin_tenants:
            slug = str(tenant["tenant_slug"])
            name = tenant.get("full_corporation_name") or slug
            with st.expander(f"{name} · {slug} (deleted {tenant['deleted_at']})"):
                st.write(f"**Prior status:** `{tenant.get('status') or 'Unknown'}`")
                st.write(
                    "**Administrator contact:** "
                    f"{tenant.get('admin_email') or 'Not provided'} · "
                    f"{tenant.get('admin_phone') or 'Not provided'}"
                )
                if st.button(
                    "Restore Tenant",
                    key=f"restore_soft_deleted_tenant_{slug}",
                    type="primary",
                ):
                    try:
                        restored = db.restore_tenant(slug)
                    except (sqlite3.Error, RuntimeError, ValueError):
                        logging.exception("Could not restore tenant %s.", slug)
                        st.error(f"Tenant {name} could not be restored.")
                    else:
                        if restored:
                            st.success(f"Tenant {name} restored with its prior status.")
                            st.rerun()
                        else:
                            st.error("Tenant is no longer in the Recycle Bin.")

                st.error(
                    "Permanent purge cannot be undone. This deletes tenant-scoped "
                    "database records and encrypted dossiers."
                )
                purge_checked = st.checkbox(
                    f"I understand this permanently deletes {name} and its data",
                    key=f"confirm_purge_soft_deleted_tenant_{slug}",
                )
                purge_slug = st.text_input(
                    f"Type tenant slug to confirm: {slug}",
                    key=f"confirm_purge_soft_deleted_tenant_slug_{slug}",
                )
                if st.button(
                    "Permanently Purge Tenant",
                    key=f"purge_soft_deleted_tenant_{slug}",
                    disabled=not (purge_checked and purge_slug.strip().lower() == slug),
                    type="primary",
                ):
                    try:
                        purged = db.purge_tenant_permanently(slug)
                    except (sqlite3.Error, RuntimeError, ValueError):
                        logging.exception(
                            "Could not permanently purge tenant %s.", slug
                        )
                        st.error(f"Tenant {name} could not be permanently purged.")
                    else:
                        if not purged:
                            st.error("Tenant is no longer in the Recycle Bin.")
                        else:
                            try:
                                from sector_logic import purge_tenant_dossiers

                                removed_dossiers = purge_tenant_dossiers(slug)
                            except (OSError, RuntimeError, ValueError):
                                logging.exception(
                                    "Tenant %s database records were purged, but "
                                    "encrypted dossier cleanup failed.",
                                    slug,
                                )
                                st.error(
                                    "Tenant database records were purged, but "
                                    "encrypted dossier cleanup failed. Review server "
                                    "logs and remove the remaining files."
                                )
                            else:
                                st.success(
                                    f"Tenant {name} permanently purged, including "
                                    f"{removed_dossiers} encrypted dossier file(s)."
                                )
                                st.rerun()

        legacy_archives = [
            archived
            for archived in archived_tenants
            if str(archived["tenant_slug"]) not in soft_deleted_slugs
        ]
        if legacy_archives:
            st.markdown("### Legacy Archived Tenants")
            st.caption(
                "These entries predate soft deletion and are retained for "
                "backward-compatible restoration."
            )
        for archived in legacy_archives:
            tenant_data = archived["tenant_data"]
            slug = str(archived["tenant_slug"])
            name = tenant_data.get("full_corporation_name") or slug
            with st.expander(f"{name} · {slug} (legacy archive)"):
                st.json(tenant_data)
                if st.button(
                    "Restore Tenant",
                    key=f"restore_legacy_archived_tenant_{slug}",
                ):
                    try:
                        restored = db.restore_archived_tenant(slug)
                    except (sqlite3.Error, RuntimeError, ValueError):
                        logging.exception("Could not restore legacy tenant %s.", slug)
                        st.error(f"Tenant {name} could not be restored.")
                    else:
                        if restored:
                            st.success(f"Tenant {name} restored.")
                            st.rerun()
                        else:
                            st.error("Archived tenant no longer exists.")
                purge_checked = st.checkbox(
                    f"I understand this permanently deletes {name} and its data",
                    key=f"confirm_legacy_purge_tenant_{slug}",
                )
                purge_slug = st.text_input(
                    f"Type tenant slug to confirm: {slug}",
                    key=f"confirm_legacy_purge_tenant_slug_{slug}",
                )
                if st.button(
                    "Permanently Purge Tenant",
                    key=f"purge_legacy_archived_tenant_{slug}",
                    disabled=not (purge_checked and purge_slug.strip().lower() == slug),
                    type="primary",
                ):
                    try:
                        purged = db.purge_archived_tenant(slug)
                    except (sqlite3.Error, RuntimeError, ValueError):
                        logging.exception(
                            "Could not permanently purge legacy tenant %s.", slug
                        )
                        st.error(f"Tenant {name} could not be permanently purged.")
                    else:
                        if not purged:
                            st.error("Archived tenant no longer exists.")
                        else:
                            try:
                                from sector_logic import purge_tenant_dossiers

                                removed_dossiers = purge_tenant_dossiers(slug)
                            except (OSError, RuntimeError, ValueError):
                                logging.exception(
                                    "Legacy tenant %s was purged from the database, "
                                    "but encrypted dossier cleanup failed.",
                                    slug,
                                )
                                st.error(
                                    "Tenant database records were purged, but "
                                    "encrypted dossier cleanup failed. Review server "
                                    "logs and remove the remaining files."
                                )
                            else:
                                st.success(
                                    f"Tenant {name} permanently purged, including "
                                    f"{removed_dossiers} encrypted dossier file(s)."
                                )
                                st.rerun()

    if section == "Slug & URL Registry":
        st.markdown("### Production Tenant URL Registry")
        registry_rows = []
        for tenant in tenants:
            tenant_slug = str(tenant["tenant_slug"])
            status = str(tenant.get("status") or "Unknown")
            registry_rows.append(
                {
                    "Institution": tenant.get("full_corporation_name") or tenant_slug,
                    "Tenant slug": tenant_slug,
                    "Status": status,
                    "Internal portal": _tenant_portal_url("internal", tenant_slug),
                    "Public unsolicited portal": _tenant_portal_url(
                        "vendor",
                        tenant_slug,
                        "unsolicited",
                    ),
                    "Solicited portal (published window required)": _tenant_portal_url(
                        "vendor",
                        tenant_slug,
                        "solicited",
                    ),
                }
            )
        if registry_rows:
            st.dataframe(
                registry_rows,
                use_container_width=True,
                hide_index=True,
            )
            st.caption(
                "Copy any slug or full production URL with the copy control on its "
                "code block. Solicited links remain locked until a tender window is "
                "published and unexpired."
            )
            for row in registry_rows:
                with st.expander(
                    f"{row['Institution']} · {row['Tenant slug']} · {row['Status']}"
                ):
                    st.write("Tenant slug")
                    st.code(row["Tenant slug"], language="text")
                    for label in (
                        "Internal portal",
                        "Public unsolicited portal",
                        "Solicited portal (published window required)",
                    ):
                        st.write(label)
                        st.code(row[label], language="text")
        else:
            st.info("No tenant URLs are available to copy.")

    if section == "Platform Broadcasts":
        st.markdown("### Global Tenant Administrator Broadcast")
        st.caption(
            "Changes are saved automatically and appear on authenticated internal "
            "tenant dashboards. Leave the field blank to clear the broadcast."
        )
        st.text_area(
            "Broadcast message",
            key="developer_broadcast_message",
            max_chars=2_000,
            height=180,
            on_change=_persist_general_broadcast,
        )
        if current_broadcast is not None:
            st.caption(
                f"Currently published · Updated {current_broadcast['updated_at']}"
            )

    if section == "📋 Activity Audit Trail":
        st.markdown("### Client Tenant Activity & Audit Trail")
        try:
            tenant_slugs = sorted(
                {tenant["tenant_slug"] for tenant in tenants}
                | set(db.get_tenant_activity_slugs())
            )
        except (sqlite3.Error, RuntimeError, ValueError):
            logging.exception("Could not load tenant activity filters.")
            st.error("Tenant activity filters are unavailable.")
            return
        selected_tenant = st.selectbox(
            "Filter by Client Tenant slug",
            ["All tenants", *tenant_slugs],
            key="tenant_activity_filter",
        )
        activity_tenant = None if selected_tenant == "All tenants" else selected_tenant
        try:
            total, latest_activities = db.get_tenant_activity_page(
                activity_tenant, limit=3
            )
            total_pages = max(1, (total + 49) // 50)
            page_key = f"tenant_activity_page_{selected_tenant}"
            if st.session_state.get(page_key, 1) > total_pages:
                st.session_state[page_key] = total_pages
            page = int(st.number_input(
                "Activity page",
                min_value=1,
                max_value=total_pages,
                value=1,
                key=page_key,
            ))
            _, activities = db.get_tenant_activity_page(
                activity_tenant, limit=50, offset=(page - 1) * 50
            )
        except (sqlite3.Error, RuntimeError, ValueError):
            logging.exception("Could not load tenant activity history.")
            st.error("Tenant activity history is unavailable.")
            return

        total_col, recent_col = st.columns(2)
        total_col.metric("Total logged actions", total)
        latest_timestamp = (
            f"{latest_activities[0]['date']} {latest_activities[0]['time']}"
            if latest_activities
            else "No activity"
        )
        recent_col.metric("Most recent activity", latest_timestamp)
        recent_timestamps = [
            f"{activity['date']} {activity['time']}" for activity in latest_activities
        ]
        st.caption(
            "Recent activity timestamps: "
            + (", ".join(recent_timestamps) if recent_timestamps else "None")
        )

        if not activities:
            st.info("No tenant activity has been logged for this selection.")
        else:
            st.dataframe(
                [
                    {
                        "Tenant Slug": activity["tenant_slug"],
                        "Activity Type": activity["activity_type"],
                        "Description": activity["description"],
                        "Performed By": activity["performed_by"],
                        "Date": activity["date"],
                        "Time": activity["time"],
                        "Month": activity["month"],
                        "Year": activity["year"],
                    }
                    for activity in activities
                ],
                use_container_width=True,
            )


def _render_platform_support_feedback() -> None:
    try:
        total, unanswered_count, _ = db.get_platform_support_ticket_page(limit=1)
        total_pages = max(1, (total + 49) // 50)
        page_key = "developer_support_page"
        if st.session_state.get(page_key, 1) > total_pages:
            st.session_state[page_key] = total_pages
        page = int(st.number_input(
            "Support history page",
            min_value=1,
            max_value=total_pages,
            value=1,
            key=page_key,
        ))
        _, unanswered_count, tickets = db.get_platform_support_ticket_page(
            limit=50, offset=(page - 1) * 50
        )
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception("Developer support ticket data failed to load.")
        st.error("Support and feedback data is unavailable.")
        return

    st.caption(f"Showing page {page} of {total_pages} · {total} total inquiries")
    if _render_tenant_feedback_tab is not None:
        _render_tenant_feedback_tab(
            tickets,
            unanswered_count,
            respond_to_ticket=db.respond_to_tenant_support_ticket,
        )
        return

    if _DEVELOPER_UI_IMPORT_ERROR is not None:
        st.warning(
            "The enhanced feedback view is unavailable; using the platform "
            f"ticket view instead. {_DEVELOPER_UI_IMPORT_ERROR}"
        )
    if not tickets:
        st.info("No tenant support inquiries have been recorded.")
        return
    for ticket in tickets:
        with st.expander(
            f"{ticket['status']} · {ticket['org_name']} · "
            f"{ticket['created_at']}"
        ):
            st.markdown(f"**From:** {ticket['sender_email']}")
            st.markdown(f"**Inquiry:**\n\n> {ticket['message']}")
            if ticket["response"]:
                st.info(ticket["response"])
            elif st.session_state.get("dev_authenticated") is True:
                reply = st.text_area(
                    "Executive response",
                    key=f"platform_support_reply_{ticket['ticket_id']}",
                )
                if st.button(
                    "Send executive response",
                    key=f"platform_support_respond_{ticket['ticket_id']}",
                    disabled=not reply.strip(),
                ):
                    try:
                        responded = db.respond_to_tenant_support_ticket(
                            ticket["ticket_id"],
                            reply,
                        )
                    except (sqlite3.Error, RuntimeError, ValueError):
                        logging.exception(
                            "Could not respond to tenant support ticket %s.",
                            ticket["ticket_id"],
                        )
                        st.error("The executive response could not be recorded.")
                    else:
                        if responded:
                            st.success("Executive response recorded.")
                            st.rerun()
                        else:
                            st.warning(
                                "This inquiry has already been answered or removed."
                            )


def _render_executive_knowledge_base() -> None:
    st.markdown("## Executive Knowledge Base")
    if _DEVELOPER_KB_IMPORT_ERROR is not None:
        st.error(
            "The Executive Knowledge Base is unavailable: "
            f"{_DEVELOPER_KB_IMPORT_ERROR}"
        )
        return
    if not NEXUSVAULT_EXECUTIVE_KB:
        st.error("The Executive Knowledge Base contains no entries.")
        return

    topic = st.selectbox(
        "Select executive knowledge-base topic",
        list(NEXUSVAULT_EXECUTIVE_KB),
        key="executive_knowledge_base_topic",
    )
    topic_data = NEXUSVAULT_EXECUTIVE_KB[topic]
    if "documentation" in topic_data:
        render_executive_document(topic_data["documentation"])
    else:
        st.subheader(topic)
        st.caption(f"{topic_data['category']} · {topic_data['status_badge']}")
        st.markdown(topic_data["summary"])
        for index, qa in enumerate(topic_data["qa_pairs"], start=1):
            with st.expander(f"Q{index}: {qa['question']}"):
                st.markdown(qa["answer"])


def render_developer_console() -> None:
    if not _guard_session_interaction():
        st.rerun()
    if st.session_state.get("dev_authenticated") is not True:
        st.error("Developer authentication is required.")
        return

    workspace = st.selectbox(
        "Developer workspace",
        [
            "Developer Console",
            "Support & Feedback Gateway",
            "Executive Knowledge Base",
            "Tenant UI Slide Deck",
            "SaaS Master Console",
        ],
        key="developer_workspace_section",
    )
    if workspace == "Developer Console":
        _render_platform_developer_console()
        st.divider()
        if render_report_export_widget is None:
            detail = (
                f" {_REPORT_EXPORTER_IMPORT_ERROR}"
                if _REPORT_EXPORTER_IMPORT_ERROR is not None
                else ""
            )
            st.error(f"The Executive Report Exporter is unavailable.{detail}")
        else:
            render_report_export_widget(tenant_slug=None)
        with st.container():
            if render_pdf_export_widget is None:
                detail = (
                    f" {_PDF_EXPORTER_IMPORT_ERROR}"
                    if _PDF_EXPORTER_IMPORT_ERROR is not None
                    else ""
                )
                st.error(f"The Executive PDF Briefing exporter is unavailable.{detail}")
            else:
                render_pdf_export_widget(tenant_slug=None)
    elif workspace == "Support & Feedback Gateway":
        _render_platform_support_feedback()
    elif workspace == "Executive Knowledge Base":
        _render_executive_knowledge_base()
    elif workspace == "Tenant UI Slide Deck":
        if _render_seminar_training_suite is None:
            detail = (
                f" {_DEVELOPER_UI_IMPORT_ERROR}"
                if _DEVELOPER_UI_IMPORT_ERROR is not None
                else ""
            )
            st.error(f"The Tenant UI Slide Deck is unavailable.{detail}")
        else:
            _render_seminar_training_suite()
    elif workspace == "SaaS Master Console":
        if _render_developer_master_console is None:
            detail = (
                f" {_MASTER_CONSOLE_IMPORT_ERROR}"
                if _MASTER_CONSOLE_IMPORT_ERROR is not None
                else ""
            )
            st.error(f"The SaaS Master Console is unavailable.{detail}")
        else:
            _render_developer_master_console()


session_expired_notice = st.session_state.pop("session_expired_msg", None)
if isinstance(session_expired_notice, str) and session_expired_notice:
    st.warning(session_expired_notice)

if st.query_params.get("mode") == "dev" and _raw_portal is None:
    inject_sovereign_workspace_css()
    _sync_tenant_session(None, "dev")
    st.session_state.pop("dev_grant_input", None)
    st.session_state["_primary_workspace"] = "Developer Console"
    st.session_state["_primary_workspace_selection"] = "Developer Console"
    st.sidebar.radio(
        "Application Workspace",
        ["Onboarding Portal", "Developer Console"],
        key="_primary_workspace_selection",
        on_change=_handle_primary_workspace_change,
    )
    configured_password = _configured_developer_password()
    if not configured_password:
        st.error(
            "Developer access is unavailable: configure "
            "NEXUSVAULT_DEVELOPER_GRANT_PASSWORD."
        )
        st.stop()

    st.markdown("## NexusVault Developer Authentication")
    with st.container():
        st.text_input(
            "Enter Developer Grant Password",
            type="password",
            key="dev_password_input",
        )
        st.button("Authenticate", on_click=_handle_developer_login)

    feedback = st.session_state.pop("dev_login_feedback", None)
    if feedback == "success":
        st.success("Developer access granted.")
    elif feedback == "audit_error":
        st.error("Developer access could not be verified and recorded.")
    elif feedback == "invalid":
        st.error("Invalid developer credentials.")

    if st.session_state.get("dev_authenticated", False):
        render_developer_console()
        st.stop()
    else:
        st.warning("Restricted Developer Console. Please authenticate to continue.")
        st.stop()
else:
    for key in (
        "dev_authenticated",
        "dev_password_input",
        "dev_grant_input",
        "dev_login_feedback",
    ):
        st.session_state.pop(key, None)
    try:
        _portal, _tenant_slug, _intake_type = _parse_route()
    except ValueError as exc:
        _sync_tenant_session(None, None)
        _render_route_error(str(exc))
    else:
        _sync_tenant_session(_tenant_slug, _portal)
        if _portal == "home":
            _render_home()
        else:
            try:
                db.init_db()
                _tenant = db.get_tenant_by_slug(_tenant_slug)
            except (sqlite3.Error, RuntimeError):
                logging.exception("Tenant lookup failed.")
                _render_route_error(
                    "Tenant access could not be verified. Please try again later."
                )
            else:
                if (
                    _tenant is None
                    or str(_tenant.get("status", "")).strip().upper() != "ACTIVE"
                    or bool(_tenant.get("is_deleted"))
                ):
                    _sync_tenant_session(None, None)
                    _render_route_error(
                        "The requested tenant was not found or is inactive."
                    )
                else:
                    render_sovereign_tenant_header(_tenant)
                    if _portal == "vendor":
                        _render_vendor_portal(_tenant_slug, _intake_type)
                    elif _portal == "internal":
                        _render_internal_portal(_tenant, _tenant_slug)
                    elif _portal == "frontdesk":
                        _render_frontdesk_portal(_tenant, _tenant_slug)
                    elif _portal == "admin":
                        _render_master_admin_portal(_tenant, _tenant_slug)

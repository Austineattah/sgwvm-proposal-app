import hashlib
import hmac
import json
import logging
import os
import re
import sqlite3
from collections.abc import Mapping
from typing import Any

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

import database as db


st.set_page_config(
    page_title="NEXUSVAULT Sovereign Enterprise Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
}
_TENANT_SESSION_PREFIX = "tenant:"
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
    elif portal == "internal":
        if tenant_slug is None:
            raise ValueError("Internal staff links must include a tenant.")
        if intake_type is not None:
            raise ValueError("The internal portal does not accept a vendor type.")
    else:
        raise ValueError("Unsupported portal. Use portal=vendor or portal=internal.")

    tenant_slug = tenant_slug.lower()
    if not _TENANT_SLUG_PATTERN.fullmatch(tenant_slug):
        raise ValueError("The tenant identifier is invalid.")

    return portal, tenant_slug, intake_type


def _tenant_key(tenant_slug: str, surface: str, name: str) -> str:
    return f"{_TENANT_SESSION_PREFIX}{tenant_slug}:{surface}:{name}"


def _sync_tenant_session(tenant_slug: str | None) -> None:
    previous_slug = st.session_state.get("_active_tenant_slug")
    has_active_tenant = "_active_tenant_slug" in st.session_state
    if has_active_tenant and previous_slug == tenant_slug:
        for key in _LEGACY_TENANT_SESSION_KEYS:
            st.session_state.pop(key, None)
        return

    for key in list(st.session_state.keys()):
        if (
            isinstance(key, str)
            and key.startswith(_TENANT_SESSION_PREFIX)
        ) or key in _LEGACY_TENANT_SESSION_KEYS:
            del st.session_state[key]

    st.session_state["_active_tenant_slug"] = tenant_slug


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
    users = _configured_staff_users()
    account = users.get(username.strip().lower())
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
        or not _verify_password(password, password_hash)
    ):
        return None

    return {
        "username": username.strip().lower(),
        "role": role.strip().lower(),
        "tenant_slug": tenant_slug,
    }


def _handle_internal_login(tenant_slug: str) -> None:
    username_key = _tenant_key(tenant_slug, "internal", "username")
    password_key = _tenant_key(tenant_slug, "internal", "password")
    identity_key = _tenant_key(tenant_slug, "internal", "identity")
    failed_key = _tenant_key(tenant_slug, "internal", "login_failed")

    identity = _authenticate_internal_user(
        tenant_slug,
        str(st.session_state.get(username_key, "")),
        str(st.session_state.get(password_key, "")),
    )
    st.session_state[password_key] = ""
    if identity is None:
        st.session_state[failed_key] = True
        st.session_state.pop(identity_key, None)
        return

    st.session_state[failed_key] = False
    st.session_state[identity_key] = identity


def _render_internal_portal(tenant: Mapping[str, Any], tenant_slug: str) -> None:
    identity_key = _tenant_key(tenant_slug, "internal", "identity")
    failed_key = _tenant_key(tenant_slug, "internal", "login_failed")
    identity = st.session_state.get(identity_key)

    st.title("Internal Directorate Access")
    st.caption(str(tenant.get("full_corporation_name") or tenant_slug))

    if (
        not isinstance(identity, Mapping)
        or identity.get("tenant_slug") != tenant_slug
        or identity.get("role") not in _ALLOWED_INTERNAL_ROLES
    ):
        users = _configured_staff_users()
        if not users:
            st.error(
                "Internal access is unavailable: no staff credentials are configured."
            )
            return

        with st.form(key=_tenant_key(tenant_slug, "internal", "login_form")):
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
            st.error("Sign-in failed or this account is not authorized for this tenant.")
        return

    st.success(
        f"Authenticated as {identity['username']} ({identity['role']})."
    )
    st.subheader("Tenant profile")
    st.write("Institution category:", tenant.get("institution_category") or "Not configured")
    st.write("Executive title:", tenant.get("apex_title") or "Not configured")

    if st.button(
        "Sign out",
        key=_tenant_key(tenant_slug, "internal", "logout"),
    ):
        st.session_state.pop(identity_key, None)
        st.rerun()


def _render_vendor_portal(
    tenant_slug: str,
) -> None:
    from sector_logic import render_unified_vendor_portal

    render_unified_vendor_portal(
        tenant_slug=tenant_slug,
        key_prefix=f"tenant:{tenant_slug}:vendor",
    )


def _render_home() -> None:
    st.title("NEXUSVAULT Sovereign Enterprise Portal")
    st.info(
        "Open a tenant-issued vendor link to submit a proposal, or use your "
        "authorized internal access link."
    )
    st.code(
        "?portal=vendor&tenant=<slug>\n"
        "?portal=internal&tenant=<slug>",
        language="text",
    )


def _render_route_error(message: str) -> None:
    st.title("Access unavailable")
    st.error(message)
    st.caption("Use a valid tenant-issued link or contact your platform administrator.")


try:
    _portal, _tenant_slug, _intake_type = _parse_route()
except ValueError as exc:
    _sync_tenant_session(None)
    _render_route_error(str(exc))
else:
    _sync_tenant_session(_tenant_slug)
    if _portal == "home":
        _render_home()
    else:
        try:
            db.init_db()
            _tenant = db.get_tenant_by_slug(_tenant_slug)
        except (sqlite3.Error, RuntimeError):
            logging.exception("Tenant lookup failed.")
            _render_route_error("Tenant access could not be verified. Please try again later.")
        else:
            if (
                _tenant is None
                or str(_tenant.get("status", "")).strip().upper() != "ACTIVE"
            ):
                _render_route_error("The requested tenant was not found or is inactive.")
            elif _portal == "vendor":
                _render_vendor_portal(_tenant_slug)
            elif _portal == "internal":
                _render_internal_portal(_tenant, _tenant_slug)

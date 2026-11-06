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
import requests
from PIL import Image, UnidentifiedImageError
from cryptography.fernet import Fernet, InvalidToken

from streamlit.errors import StreamlitSecretNotFoundError

import database as db


PRODUCTION_BASE_URL = "https://nexusvault-proposal-enterprise-connect.streamlit.app"


st.set_page_config(
    page_title="NEXUSVAULT Sovereign Enterprise Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


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
        ) or key in _LEGACY_TENANT_SESSION_KEYS | _TENANT_SCOPED_AUTH_KEYS:
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


def _configured_developer_password() -> str | None:
    password = os.environ.get("NEXUSVAULT_DEVELOPER_GRANT_PASSWORD")
    if isinstance(password, str) and password.strip():
        return password.strip()
    try:
        password = st.secrets.get("NEXUSVAULT_DEVELOPER_GRANT_PASSWORD")
    except (KeyError, StreamlitSecretNotFoundError):
        return ""
    return password.strip() if isinstance(password, str) and password.strip() else ""


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
    if identity is None:
        st.session_state[failed_key] = True
        st.session_state.pop(identity_key, None)
        return

    st.session_state[failed_key] = False
    st.session_state[identity_key] = identity


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
        os.environ.get("PREMBLY_API_KEY")
        or os.environ.get("PREMBLY_SECRET_KEY")
        or ""
    ).strip()
    app_id = (os.environ.get("PREMBLY_APP_ID") or "").strip()
    if api_key and app_id:
        return api_key, app_id
    try:
        secrets = st.secrets
        api_key = api_key or str(
            secrets.get("PREMBLY_API_KEY")
            or secrets.get("PREMBLY_SECRET_KEY")
            or ""
        ).strip()
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
        else "FAILED"
        if company_status in {"INACTIVE", "DORMANT", "DISSOLVED", "CANCELLED"}
        else "MANUAL_REVIEW"
    )
    cac_check.update(
        {
            "verification_status": verification_status,
            "registry_source": "Prembly CAC registry",
            "result_details": (
                f"Prembly returned company status {company_status}."
            ),
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
                    "credential_reference": _masked_compliance_reference(
                        registry_tin
                    ),
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
        check.get("verification_status") == "PROVIDED_UNVERIFIED"
        for check in checks
    )
    missing = sum(
        check.get("verification_status") == "MISSING"
        for check in checks
    )
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
        st.write("CAC reference:", _masked_compliance_reference(
            str(proposal["cac_registration_number"])
        ))
    if proposal.get("tax_identification_number"):
        st.write("TIN reference:", _masked_compliance_reference(
            str(proposal["tax_identification_number"])
        ))

    inferred_sector = "Other / Not specified"
    title_lower = str(proposal["proposal_title"]).casefold()
    if any(term in title_lower for term in ("food", "consumable", "medicine", "drug")):
        inferred_sector = "Food / Consumables"
    elif any(term in title_lower for term in ("engineering", "construction", "bridge", "road", "infrastructure")):
        inferred_sector = "Engineering / Infrastructure"
    elif any(term in title_lower for term in ("security", "guard", "surveillance")):
        inferred_sector = "Private Security"
    elif any(term in title_lower for term in ("software", "digital", "ict", "technology", "data")):
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
            cac_check = next(
                check for check in checks if check["check_name"] == "CAC"
            )
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
    summary_key = _tenant_key(tenant_slug, "internal", f"appraisal_summary_{selected_id}")
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
            str(dossier.get("executive_summary") or st.session_state.get(summary_key, "")),
        ]
    )
    st.download_button(
        "Download / Print Dossier Packet",
        data="\n".join(packet_lines),
        file_name=f"{selected_id}-departmental-dossier.txt",
        mime="text/plain",
        key=_tenant_key(tenant_slug, "internal", f"download_dossier_{selected_id}"),
    )
    st.caption("Open the downloaded dossier packet and use your browser/OS print command.")
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
                    else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    if Path(source_filename).suffix.lower() == ".docx"
                    else "application/octet-stream"
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
        ("ict", "technology", "digital", "software", "cybersecurity", "data", "network"),
    ),
    (
        "Works and Infrastructure",
        ("construction", "building", "road", "infrastructure", "facility", "water", "power"),
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
        (sum(keyword in normalized_title for keyword in keywords), directorate, keywords)
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
            item.get("name")
            if isinstance(item, Mapping)
            else item
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

    matched_terms = [
        keyword for keyword in keywords if keyword in normalized_title
    ]
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
    st.subheader("TSA & Remita Gateway Configuration")
    st.caption(
        "Settings are stored for this tenant only. This configures endpoints and "
        "fee metadata; it does not connect to or verify payments with a live gateway."
    )
    try:
        config = db.get_tenant_gateway_config(tenant_slug)
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception("Could not load gateway settings for %s.", tenant_slug)
        st.error("Gateway settings could not be loaded.")
        return

    tsa_default = str(config.get("tsa_endpoint") or "") if config else ""
    remita_default = str(config.get("remita_endpoint") or "") if config else ""
    service_head_default = (
        str(config.get("service_head") or "Tender Fee/Bidding Document Fee")
        if config
        else "Tender Fee/Bidding Document Fee"
    )
    fee_default = (
        f"{Decimal(config['fee_amount_minor']) / 100:.2f}"
        if config
        else "0.00"
    )
    with st.form(
        key=_tenant_key(tenant_slug, "executive", "gateway_form"),
        clear_on_submit=True,
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
        save_config = st.form_submit_button(
            "Save tenant gateway configuration",
            type="primary",
        )

    if save_config:
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
            saved = db.save_tenant_gateway_config(
                tenant_slug=tenant_slug,
                tsa_endpoint=tsa_url,
                tsa_key_ciphertext=tsa_ciphertext,
                remita_endpoint=remita_url,
                remita_merchant_key_ciphertext=remita_ciphertext,
                service_head=service_head,
                fee_amount_minor=fee_minor,
                updated_by=actor,
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
            st.success(
                "Tenant gateway configuration saved. Credential values are not "
                "displayed after saving."
            )
            config = saved

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
        st.caption(
            f"Last updated {config['updated_at']} by {config['updated_by']}."
        )


def _render_executive_financial_tab(tenant_slug: str) -> None:
    st.subheader("DFA Financial Reconciliation")
    st.caption(
        "Tenant-local payment reference ledger sourced from recorded clearance "
        "passes and provider verification events. Paystack is the current live "
        "verification source; the configured TSA/Remita endpoints are not connected."
    )
    try:
        ledger = db.get_tenant_financial_ledger(tenant_slug)
        config = db.get_tenant_gateway_config(tenant_slug)
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception("Could not load financial ledger for %s.", tenant_slug)
        st.error("The financial ledger could not be loaded.")
        return

    verified = [
        row
        for row in ledger
        if row["amount_minor"] is not None
    ]
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
                    logging.exception("Tender auto-lock update failed for %s.", tenant_slug)
                    st.error(f"Auto-lock could not be updated: {exc}")
                else:
                    if changed:
                        st.rerun()
                    st.error("The tender was not found for this tenant.")


def _render_executive_committee_tab(tenant_slug: str, actor: str) -> None:
    st.subheader("Committee Slot Provisioning")
    st.caption(
        "Provisioning replaces the existing roster and resets all COI state. "
        "Access credentials are encrypted at rest and shown only after creation."
    )
    encryption_key = _physical_document_encryption_key()
    roster_count = st.selectbox(
        "Committee member slots",
        options=list(range(10, 16)),
        key=_tenant_key(tenant_slug, "executive", "committee_count"),
    )
    member_values: list[tuple[str, str]] = []
    with st.form(key=_tenant_key(tenant_slug, "executive", "committee_form")):
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
        provision = st.form_submit_button(
            "Provision committee and credentials",
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
                        "encrypted_access_token": fernet.encrypt(
                            token.encode("utf-8")
                        ),
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
                st.success(
                    f"Provisioned {len(credentials)} committee member slots."
                )

    credentials = st.session_state.get(
        _tenant_key(tenant_slug, "executive", "committee_credentials")
    )
    if isinstance(credentials, list) and credentials:
        with st.expander("New committee credentials — copy and distribute securely"):
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
                with st.form(
                    key=_tenant_key(
                        tenant_slug,
                        "executive",
                        f"coi_form_{member['member_id']}",
                    )
                ):
                    attested = st.checkbox(
                        "I confirm the member's signed COI declaration was received.",
                        key=_tenant_key(
                            tenant_slug,
                            "executive",
                            f"coi_attested_{member['member_id']}",
                        ),
                    )
                    record_signoff = st.form_submit_button(
                        "Record received COI sign-off",
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
            "Recommended Winner"
            if row["Equal-weight avg"] == top_score
            else ""
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


def _handle_committee_login(tenant_slug: str) -> None:
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


def _render_committee_workspace(tenant_slug: str) -> None:
    st.header("Committee Evaluation Workspace")
    identity_key = _tenant_key(tenant_slug, "committee", "identity")
    identity = st.session_state.get(identity_key)
    if (
        not isinstance(identity, Mapping)
        or identity.get("tenant_slug") != tenant_slug
        or not identity.get("member_id")
    ):
        st.caption(
            "Use the secure access token issued to your committee member account."
        )
        token_key = _tenant_key(tenant_slug, "committee", "access_token")
        encryption_key = _physical_document_encryption_key()
        if encryption_key is None:
            st.error(
                "Committee access is unavailable because the dossier encryption "
                "key is not configured."
            )
            return
        with st.form(key=_tenant_key(tenant_slug, "committee", "login_form")):
            st.text_input("Committee access token", type="password", key=token_key)
            st.form_submit_button(
                "Open committee workspace",
                type="primary",
                on_click=_handle_committee_login,
                args=(tenant_slug,),
            )
        login_error = st.session_state.pop(
            _tenant_key(tenant_slug, "committee", "login_error"),
            None,
        )
        if isinstance(login_error, str) and login_error:
            st.error(login_error)
        return

    st.success(f"Authenticated committee member: {identity['name']}")
    try:
        proposals = db.get_tenant_governance_proposals(tenant_slug)
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
                st.session_state[_tenant_key(
                    tenant_slug,
                    "committee",
                    "workspace_feedback",
                )] = "COI attestation recorded. Proposal review is now unlocked."
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
    with st.form(
        key=_tenant_key(tenant_slug, "committee", f"evaluation_{tracking_id}")
    ):
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
        submitted = st.form_submit_button("Save proposal evaluation", type="primary")
    if submitted:
        scores = {
            name: int(st.session_state[key])
            for name, key in score_keys.items()
        }
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

    if st.button(
        "Sign out of committee workspace",
        key=_tenant_key(tenant_slug, "committee", "logout"),
    ):
        st.session_state.pop(identity_key, None)
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
            st.info("No committee members or proposal-scoped COI records are available.")

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
                placeholder=(
                    "Analyze risk profiles for physical security proposals"
                ),
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
                "Pushed to Apex": bool(
                    proposal.get("appraisal_pushed_to_apex")
                ),
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
                st.write(departmental_dossier.get("appraisal_notes") or "Not submitted.")
                st.markdown("**Executive summary**")
                st.write(
                    departmental_dossier.get("executive_summary")
                    or "Not generated."
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
            "TSA & Remita Gateway",
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


def _render_internal_portal(tenant: Mapping[str, Any], tenant_slug: str) -> None:
    st.title("Internal Directorate Access")
    st.caption(str(tenant.get("full_corporation_name") or tenant_slug))

    staff_tab, executive_tab, committee_tab = st.tabs(
        [
            "Desk Operations · Staff",
            "Executive Management",
            "Committee Workspace",
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
            if st.button(
                "Sign out of executive management",
                key=_tenant_key(tenant_slug, "internal", "executive_logout"),
            ):
                st.session_state.pop("tenant_exec_auth", None)
                st.session_state.pop("tenant_exec_auth_slug", None)
                st.rerun()

    with committee_tab:
        _render_committee_workspace(tenant_slug)


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
    identity = st.session_state.get(
        _tenant_key(tenant_slug, "internal", "identity")
    )
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
        logging.exception(
            "Could not record audit entry access for %s.", tenant_slug
        )


def _delete_tenant_audit_entry(tenant_slug: str, activity_id: int) -> None:
    if (
        st.session_state.get("_active_tenant_slug") != tenant_slug
        or not _tenant_access_is_authenticated("executive", tenant_slug)
    ):
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
                logging.error(
                    "Audit record %s has an invalid timestamp.", activity_id
                )
                date_text = time_text = year_text = "Unknown"

            with st.container():
                summary, open_column, delete_column = st.columns([6, 1, 1])
                summary.write(
                    f"{date_text} · {time_text} · {year_text}\n"
                    f"{activity['action_type']} · {activity['actor']}"
                )
                open_column.button(
                    "Open",
                    key=_tenant_key(
                        tenant_slug, "audit", f"open_entry_{activity_id}"
                    ),
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
    if "custom_portal_heading" not in st.session_state:
        st.session_state["custom_portal_heading"] = (
            'NEXUSVAULT TECHNOLOGIES "SUPER INTELLIGENCE - '
            'AGENTIC AI PROPOSAL INTAKE PORTAL".'
        )

    if st.session_state.get("onboarding_submitted", False):
        tenant_slug = str(st.session_state.get("onboarded_tenant_slug", ""))
        vendor_url = _tenant_portal_url("vendor", tenant_slug, "unsolicited")
        st.markdown(
            f"""
            <section style="background: linear-gradient(135deg, #061a36 0%, #0b2d5c 100%);
                            border: 1px solid rgba(147, 197, 253, 0.65);
                            border-radius: 16px; padding: 2.2rem;
                            margin: 2rem auto; max-width: 860px;
                            box-shadow: 0 18px 48px rgba(4, 17, 40, 0.35);">
                <h2 style="color: #bfdbfe; margin: 0 0 1.2rem; text-align: center;">
                    NEXUSVAULT INSTITUTIONAL ONBOARDING
                </h2>
                <div style="background: rgba(255, 255, 255, 0.07);
                            border: 1px solid rgba(191, 219, 254, 0.3);
                            border-radius: 12px; padding: 1.4rem; text-align: center;">
                    <p style="color: #eff6ff; font-size: 1.2rem; font-weight: 800;
                              letter-spacing: 0.04em; margin: 0;">
                        YOUR INSTITUTIONAL CREDENTIALS HAVE BEEN ONBOARDED,
                        AWAITING ACTIVATION SHORTLY
                    </p>
                </div>
                <p style="color: #dbeafe; text-align: center; margin: 1.2rem 0 0;">
                    Status: Pending Activation · Tenant: {html.escape(tenant_slug)}
                </p>
                <p style="color: #bfdbfe; text-align: center; margin: 0.6rem 0 0;">
                    Public submissions become available after institutional activation.
                </p>
            </section>
            """,
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
        """
        <div class="onboarding-title-banner">
            <h2>👉 ONBOARDING MODULE 👇</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

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

        submitted = st.form_submit_button(
            "Submit Organizational Node for Approval and Activation",
            use_container_width=True,
        )

    if submitted:
        org = corp_name.strip()
        email = corp_email.strip()
        phone = corp_phone.strip()
        address = corp_address.strip()
        if not org or not email or not phone or not address:
            st.error(
                "⚠️ Please fill in all required organizational entity fields "
                "marked with an asterisk (*)."
            )
        else:
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
            except (OSError, sqlite3.Error, RuntimeError, ValueError) as exc:
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
                st.session_state["onboarded_tenant_slug"] = tenant_slug
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
    st.markdown("<div style='color: #00FF66; font-weight: bold; text-align: center;'>NEXUSVAULT_TECH Sovereign Enterprise Engine • NITDA / NDPA Compliant</div>", unsafe_allow_html=True)


def _render_route_error(message: str) -> None:
    st.title("Access unavailable")
    st.error(message)
    st.caption("Use a valid tenant-issued link or contact your platform administrator.")


def _send_tenant_activation_notification(tenant: Mapping[str, Any]) -> bool:
    recipient = str(tenant.get("admin_email") or "").strip()
    tenant_slug = str(tenant.get("tenant_slug") or "").strip()
    institution_name = str(
        tenant.get("full_corporation_name") or tenant_slug
    ).strip()
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




def render_developer_console() -> None:
    st.markdown("## Sovereign Developer Command Console")
    st.markdown(
        "Client tenant, archive, and platform broadcast management."
    )

    try:
        tenants = db.list_tenants()
        archived_tenants = db.list_archived_tenants()
        recycle_bin_tenants = db.list_recycle_bin_tenants()
        current_broadcast = db.get_general_broadcast()
        all_activities = db.get_all_tenant_activities()
    except (sqlite3.Error, RuntimeError, ValueError):
        logging.exception("Developer console data failed to load.")
        st.error("Developer console data is unavailable. Please try again later.")
        return

    if "developer_broadcast_message" not in st.session_state:
        st.session_state["developer_broadcast_message"] = (
            current_broadcast["message"] if current_broadcast else ""
        )

    (
        activation_tab,
        deactivation_tab,
        deletion_tab,
        copy_tab,
        settings_tab,
        activity_tab,
    ) = st.tabs(
        [
            "Tenant Activation",
            "Tenant Deactivation",
            "Tenant Deletion & Recycle Bin",
            "Slug & URL Registry",
            "Platform Broadcasts",
            "📋 Activity Audit Trail",
        ]
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

    with activation_tab:
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
                    except (sqlite3.Error, RuntimeError, ValueError):
                        logging.exception(
                            "Tenant activation failed for slug %s.", slug
                        )
                        st.error(f"Tenant {name} could not be activated.")
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

    with deactivation_tab:
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
                st.warning(
                    "Deactivation immediately blocks all tenant portal access."
                )
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
                    except (sqlite3.Error, RuntimeError, ValueError):
                        logging.exception(
                            "Tenant deactivation failed for slug %s.", slug
                        )
                        st.error(f"Tenant {name} could not be deactivated.")
                    else:
                        if deactivated:
                            st.success(f"Tenant {name} access has been revoked.")
                            st.rerun()
                        else:
                            st.error(
                                f"Tenant {name} is no longer active or has been deleted."
                            )

    with deletion_tab:
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
                            st.success(
                                f"Tenant {name} restored with its prior status."
                            )
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
                    disabled=not (
                        purge_checked and purge_slug.strip().lower() == slug
                    ),
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
                    disabled=not (
                        purge_checked and purge_slug.strip().lower() == slug
                    ),
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

    with copy_tab:
        st.markdown("### Production Tenant URL Registry")
        registry_rows = []
        for tenant in tenants:
            tenant_slug = str(tenant["tenant_slug"])
            status = str(tenant.get("status") or "Unknown")
            registry_rows.append(
                {
                    "Institution": tenant.get("full_corporation_name")
                    or tenant_slug,
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

    with settings_tab:
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
            st.caption(f"Currently published · Updated {current_broadcast['updated_at']}")

    with activity_tab:
        st.markdown("### Client Tenant Activity & Audit Trail")
        tenant_slugs = sorted(
            {
                tenant["tenant_slug"]
                for tenant in tenants
            }
            | {
                activity["tenant_slug"]
                for activity in all_activities
            }
        )
        selected_tenant = st.selectbox(
            "Filter by Client Tenant slug",
            ["All tenants", *tenant_slugs],
            key="tenant_activity_filter",
        )
        activities = (
            all_activities
            if selected_tenant == "All tenants"
            else [
                activity
                for activity in all_activities
                if activity["tenant_slug"] == selected_tenant
            ]
        )

        total_col, recent_col = st.columns(2)
        total_col.metric("Total logged actions", len(activities))
        latest_timestamp = (
            f"{activities[0]['date']} {activities[0]['time']}"
            if activities
            else "No activity"
        )
        recent_col.metric("Most recent activity", latest_timestamp)
        recent_timestamps = [
            f"{activity['date']} {activity['time']}"
            for activity in activities[:3]
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

if st.query_params.get("mode") == "dev":
    configured_password = _configured_developer_password()
    if not configured_password:
        st.error(
            "Developer access is unavailable: configure "
            "NEXUSVAULT_DEVELOPER_GRANT_PASSWORD."
        )
        st.stop()

    st.markdown("## NexusVault Developer Authentication")
    with st.form(key="developer_authentication_form"):
        dev_pass = st.text_input(
            "Enter Developer Grant Password",
            type="password",
            key="dev_grant_input",
        )
        submitted = st.form_submit_button("Authenticate")

    if submitted:
        submitted_password = dev_pass.strip()
        authenticated = bool(submitted_password) and hmac.compare_digest(
            submitted_password,
            configured_password,
        )
        st.session_state["dev_authenticated"] = authenticated
        if authenticated:
            st.success("Developer access granted.")
        else:
            st.error("Invalid developer credentials.")

    if st.session_state.get("dev_authenticated", False):
        render_developer_console()
        st.stop()
    else:
        st.warning("Restricted Developer Console. Please authenticate to continue.")
        st.stop()
else:
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
                _render_route_error(
                    "Tenant access could not be verified. Please try again later."
                )
            else:
                if (
                    _tenant is None
                    or str(_tenant.get("status", "")).strip().upper() != "ACTIVE"
                    or bool(_tenant.get("is_deleted"))
                ):
                    _sync_tenant_session(None)
                    _render_route_error(
                        "The requested tenant was not found or is inactive."
                    )
                else:
                    render_sovereign_tenant_header(_tenant)
                    if _portal == "vendor":
                        _render_vendor_portal(_tenant_slug, _intake_type)
                    elif _portal == "internal":
                        _render_internal_portal(_tenant, _tenant_slug)

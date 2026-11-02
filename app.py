import hashlib
import html
import hmac
import json
import logging
import os
import re
import sqlite3
import uuid
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
    if "custom_portal_heading" not in st.session_state:
        st.session_state["custom_portal_heading"] = (
            'NEXUSVAULT TECHNOLOGIES "SUPER INTELLIGENCE - '
            'AGENTIC AI PROPOSAL INTAKE PORTAL"'
        )

    if st.session_state.get("onboarding_submitted", False):
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                        border: 2px solid #38bdf8; padding: 40px; border-radius: 16px;
                        text-align: center; margin: 40px auto; max-width: 800px;
                        box-shadow: 0 20px 25px -5px rgba(56, 189, 248, 0.3);">
                <h2 style="color: #38bdf8; margin-bottom: 20px; font-family: monospace;
                           font-size: 1.8rem;">NEXUSVAULT AGENTIC AI ENTERPRISE PORTAL</h2>
                <div style="background: rgba(56, 189, 248, 0.12); border: 2px dashed #38bdf8;
                            padding: 25px; border-radius: 10px; margin: 20px 0;">
                    <p style="color: #f8fafc; font-size: 1.35rem; font-weight: 800;
                              letter-spacing: 1.5px; margin: 0;">
                        YOUR SUBMISSION HAS BEEN ACKNOWLEDGED.
                    </p>
                </div>
                <p style="color: #94a3b8; font-size: 1.05rem; margin-top: 20px;
                          line-height: 1.6;">
                    Your sovereign tenant workspace is ready for vendor access.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.success("Vendor portal link")
        st.code(
            f"?portal=vendor&tenant={st.session_state['onboarded_tenant_slug']}",
            language="text",
        )
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
                color: #ffffff !important;
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
                color: #38bdf8;
                font-weight: 800;
                font-size: 15px;
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
                    <h1 style="color: #ffffff !important; margin: 0 0 10px 0; font-size: 25px;
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
                        <span style="color: #38bdf8; font-size: 13px; font-weight: 800;">
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
                        <div style="color: #ffffff; font-size: 12px; font-weight: 800;
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
            <h2>✨ ONBOARDING MODULE ✨</h2>
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
            try:
                db.create_tenant_onboarding(
                    {
                        "tenant_slug": tenant_slug,
                        "full_corporation_name": org,
                        "cac_registration_number": "N/A",
                        "admin_email": admin_email.strip() or email,
                        "admin_phone": phone,
                    }
                )
            except (sqlite3.Error, RuntimeError, ValueError) as exc:
                logging.exception("Tenant onboarding failed.")
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
                st.success(
                    "🎉 Organizational node created and activated successfully."
                )
                st.code(
                    f"?portal=vendor&tenant={tenant_slug}",
                    language="text",
                )
                st.balloons()

    st.markdown(
        """
        <div class="marquee-container">
            <div class="marquee-text">
                🌟 ADVANCING THE DIGITAL ECONOMIC DRIVE OF THE FEDERAL GOVERNMENT THROUGH TECHNOLOGY. 🌟
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.markdown(
        "<p style='color: #64748b; font-size: 12px;'>"
        "NEXUSVAULT_TECH Sovereign Enterprise Engine • NITDA / NDPA Compliant"
        "</p>",
        unsafe_allow_html=True,
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

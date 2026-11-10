"""Validated SMTP delivery for tenant activation notifications."""

import logging
import os
import smtplib
import ssl
from collections.abc import Mapping
from email.message import EmailMessage

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

logger = logging.getLogger(__name__)


def _setting(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    try:
        secrets = st.secrets
        nested = secrets.get("smtp", {})
        for name in names:
            value = secrets.get(name)
            if value is None and isinstance(nested, Mapping):
                value = nested.get(name, nested.get(name.lower()))
            if value is not None and str(value).strip():
                return str(value).strip()
    except (KeyError, StreamlitSecretNotFoundError):
        pass
    return default


def get_smtp_config() -> dict:
    return {
        "server": _setting("SMTP_SERVER"),
        "port": int(_setting("SMTP_PORT", default="587")),
        "user": _setting("SMTP_USER", "SENDER_EMAIL"),
        "password": _setting("SMTP_PASSWORD", "SENDER_PASSWORD"),
        "sender": _setting("SMTP_SENDER", "SENDER_EMAIL"),
    }


def validate_smtp_configuration() -> tuple[bool, str]:
    try:
        config = get_smtp_config()
    except (TypeError, ValueError):
        return False, "SMTP_PORT must be an integer between 1 and 65535."
    if not 1 <= config["port"] <= 65535:
        return False, "SMTP_PORT must be an integer between 1 and 65535."
    missing = [key for key, value in config.items() if key != "port" and not value]
    if missing:
        return False, f"Missing required SMTP configuration keys: {', '.join(missing)}"
    return True, "SMTP configuration structure is valid."


def send_tenant_activation_email(
    recipient_email: str,
    tenant_name: str,
    activation_code: str,
    *,
    internal_url: str = "",
    vendor_url: str = "",
) -> tuple[bool, str]:
    try:
        valid, error = validate_smtp_configuration()
        if not valid:
            return False, error
        config = get_smtp_config()
        if not isinstance(recipient_email, str) or not recipient_email.strip():
            return False, "The onboarding email address is missing."
        message = EmailMessage()
        message["Subject"] = f"Institutional node activated: {tenant_name}"
        message["From"] = config["sender"]
        message["To"] = recipient_email.strip()
        message.set_content(
            f"Hello {tenant_name},\n\n"
            "Your NexusVault institutional node has been activated.\n"
            f"Tenant slug: {activation_code}\n"
            + (f"Internal portal: {internal_url}\n" if internal_url else "")
            + (f"Open unsolicited submissions: {vendor_url}\n" if vendor_url else "")
            + "\nFor security, passwords and shared access keys are not included in email. "
            "Use the access credentials provided to your authorized administrators."
        )
        context = ssl.create_default_context()
        if config["port"] == 465:
            connection = smtplib.SMTP_SSL(
                config["server"], config["port"], timeout=15, context=context
            )
        else:
            connection = smtplib.SMTP(config["server"], config["port"], timeout=15)
        with connection as server:
            if config["port"] != 465:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
            server.login(config["user"], config["password"])
            refused = server.send_message(message)
            if refused:
                return False, "The SMTP server refused the activation recipient."
    except smtplib.SMTPAuthenticationError:
        logger.warning("SMTP authentication failed during tenant activation.")
        return False, "SMTP authentication failed."
    except smtplib.SMTPConnectError:
        logger.warning("SMTP connection failed during tenant activation.")
        return False, "SMTP connection failed."
    except Exception:
        logger.warning("Activation email delivery failed.")
        return (
            False,
            "Activation email delivery failed; check SMTP configuration and connectivity.",
        )
    return True, "Activation email accepted by the SMTP server."

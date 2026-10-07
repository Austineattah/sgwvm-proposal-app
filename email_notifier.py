import logging
import smtplib
import ssl
from email.message import EmailMessage

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


def _smtp_settings():
    """Read SMTP settings from Streamlit secrets without exposing secret values."""
    try:
        secrets = st.secrets
        settings = {
            "server": secrets.get("SMTP_SERVER"),
            "port": secrets.get("SMTP_PORT"),
            "sender_email": secrets.get("SENDER_EMAIL"),
            "sender_password": secrets.get("SENDER_PASSWORD"),
        }
    except (KeyError, StreamlitSecretNotFoundError):
        return None, "SMTP secrets are not configured."

    if not all(settings.values()):
        return None, "SMTP secrets are not configured."

    try:
        settings["port"] = int(settings["port"])
    except (TypeError, ValueError):
        return None, "SMTP_PORT must be a valid integer."

    return settings, ""


def send_vendor_acknowledgment(
    vendor_email: str,
    vendor_name: str,
    proposal_id: str | int,
) -> tuple[bool, str]:
    """Send a vendor receipt acknowledgment; return a graceful result on failure."""
    settings, error_message = _smtp_settings()
    if settings is None:
        logging.warning("%s", error_message)
        return False, error_message

    if not vendor_email or not vendor_email.strip():
        return False, "Vendor email address is missing."

    message = EmailMessage()
    message["Subject"] = f"Proposal received: {proposal_id}"
    message["From"] = settings["sender_email"]
    message["To"] = vendor_email.strip()
    message.set_content(
        f"Hello {vendor_name or 'Vendor'},\n\n"
        "Your proposal has been received and queued for review.\n"
        f"Proposal reference: {proposal_id}\n\n"
        "Thank you."
    )

    try:
        context = ssl.create_default_context()
        if settings["port"] == 465:
            with smtplib.SMTP_SSL(
                settings["server"],
                settings["port"],
                timeout=15,
                context=context,
            ) as server:
                server.login(
                    settings["sender_email"],
                    settings["sender_password"],
                )
                server.send_message(message)
        else:
            with smtplib.SMTP(
                settings["server"],
                settings["port"],
                timeout=15,
            ) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(
                    settings["sender_email"],
                    settings["sender_password"],
                )
                server.send_message(message)
    except Exception as exc:
        logging.warning("Vendor acknowledgment email failed: %s", exc)
        return False, "Vendor acknowledgment email could not be sent."

    return True, "Vendor acknowledgment email sent."

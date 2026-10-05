import json
import logging
import os
import smtplib
from collections.abc import Mapping
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from pathlib import Path
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

try:
    import streamlit as st
    from streamlit.errors import StreamlitSecretNotFoundError
except ImportError:
    st = None
    StreamlitSecretNotFoundError = KeyError


def get_setting(name):
    value = os.getenv(name)
    if value:
        return value
    if st is not None:
        try:
            smtp_settings = st.secrets.get("smtp", {})
            if isinstance(smtp_settings, Mapping):
                smtp_value = smtp_settings.get(name)
                if smtp_value is None:
                    smtp_value = smtp_settings.get(name.lower())
                if smtp_value:
                    return smtp_value
            return st.secrets.get(name)
        except (KeyError, StreamlitSecretNotFoundError):
            pass
    return None


def get_smtp_settings():
    settings = {
        "SMTP_SERVER": get_setting("SMTP_SERVER"),
        "SMTP_PORT": get_setting("SMTP_PORT"),
        "SENDER_EMAIL": get_setting("SENDER_EMAIL"),
        "SENDER_PASSWORD": get_setting("SENDER_PASSWORD"),
    }
    missing = [key for key, value in settings.items() if not value]
    if missing:
        logging.warning(
            "Email notification skipped; configure these environment variables "
            "or Streamlit secrets: %s",
            ", ".join(missing),
        )
        return None
    try:
        settings["SMTP_PORT"] = int(settings["SMTP_PORT"])
    except (TypeError, ValueError):
        logging.warning("Email notification skipped; SMTP_PORT must be an integer.")
        return None
    return settings


def get_org_branding():
    root_dir = Path(__file__).resolve().parent
    try:
        with (root_dir / "org_config.json").open(encoding="utf-8") as config_file:
            config = json.load(config_file)
        if not isinstance(config, dict):
            raise ValueError("org_config.json must contain a JSON object.")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Could not load organization branding: {exc}")
        config = {}

    org_name = config.get("org_name", "SGWVM Technology")
    if not isinstance(org_name, str) or not org_name.strip():
        org_name = "SGWVM Technology"
    logo_value = config.get("logo_path", "assets/logo.png")
    if not isinstance(logo_value, str):
        logo_value = "assets/logo.png"
    logo_path = Path(logo_value)
    if not logo_path.is_absolute():
        logo_path = root_dir / logo_path

    try:
        logo_data = logo_path.read_bytes() if logo_path.is_file() else None
    except OSError as exc:
        print(f"Could not read organization logo: {exc}")
        logo_data = None
    return org_name.strip(), logo_data


def send_email_notification(subject: str, body: str, recipient_email: str):
    """Sends an email notification via Gmail SMTP."""
    try:
        settings = get_smtp_settings()
        if settings is None:
            return False, "SMTP configuration is missing or invalid."
        server = settings["SMTP_SERVER"]
        port = settings["SMTP_PORT"]
        sender = settings["SENDER_EMAIL"]
        password = settings["SENDER_PASSWORD"]

        org_name, logo_data = get_org_branding()
        msg = MIMEMultipart("related")
        alternative = MIMEMultipart("alternative")
        msg.attach(alternative)
        msg["From"] = f"{org_name} <{sender}>"
        msg["To"] = recipient_email
        msg["Subject"] = subject
        alternative.attach(MIMEText(body, "plain"))
        logo_html = (
            '<img src="cid:org-logo" alt="Organization logo" '
            'style="max-width:180px;">'
            if logo_data
            else ""
        )
        html_body = (
            "<html><body>"
            f"{logo_html}<p><strong>{escape(org_name)}</strong></p>"
            f"<p>{escape(body).replace(chr(10), '<br>')}</p>"
            "</body></html>"
        )
        alternative.attach(MIMEText(html_body, "html", "utf-8"))
        if logo_data:
            try:
                logo = MIMEImage(logo_data)
                logo.add_header("Content-ID", "<org-logo>")
                logo.add_header("Content-Disposition", "inline", filename="org-logo")
                msg.attach(logo)
            except TypeError as exc:
                print(f"Could not attach organization logo: {exc}")

        with smtplib.SMTP(server, port) as smtp:
            smtp.starttls()
            smtp.login(sender, password)
            smtp.send_message(msg)
        return True, "Email sent successfully!"
    except Exception as e:
        return False, str(e)


def send_sms_notification(body: str, recipient_phone: str):
    """Sends an SMS notification via Twilio."""
    try:
        account_sid = get_setting("TWILIO_ACCOUNT_SID")
        auth_token = get_setting("TWILIO_AUTH_TOKEN")
        twilio_number = get_setting("TWILIO_PHONE_NUMBER")
        if not all((account_sid, auth_token, twilio_number)):
            logging.warning(
                "SMS notification skipped; configure TWILIO_ACCOUNT_SID, "
                "TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER in environment "
                "variables or Streamlit secrets."
            )
            return False, "Twilio configuration is missing."

        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=body, from_=twilio_number, to=recipient_phone
        )
        return True, f"SMS sent successfully! SID: {message.sid}"
    except Exception as e:
        return False, str(e)

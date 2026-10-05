import os
import requests
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

PREMBLY_BASE_URL = "https://api.prembly.com/identitypass/verification/cac"


def _get_credential(name):
    value = os.getenv(name)
    if value:
        return value
    try:
        return st.secrets[name]
    except (KeyError, StreamlitSecretNotFoundError):
        return ""


def verify_cac_company(rc_number):
    """
    Verifies a Nigerian business entity via Prembly CAC KYB API.
    Returns a dictionary with status, company_name, and message.
    """
    if not rc_number or not rc_number.strip():
        return {"status": False, "message": "No RC Number provided."}

    app_id = _get_credential("PREMBLY_APP_ID")
    secret_key = _get_credential("PREMBLY_SECRET_KEY")
    if not app_id or not secret_key:
        return {
            "status": False,
            "company_name": None,
            "message": "Prembly API credentials are not configured; verification was not performed.",
        }

    headers = {
        "x-api-key": secret_key,
        "app-id": app_id,
        "Content-Type": "application/json",
    }

    payload = {"rc_number": rc_number.strip()}

    try:
        response = requests.post(
            PREMBLY_BASE_URL, json=payload, headers=headers, timeout=10
        )
        res_data = response.json()

        if response.status_code == 200 and res_data.get("status"):
            company_data = res_data.get("data", {})
            return {
                "status": True,
                "company_name": company_data.get("company_name", "Verified Company"),
                "message": "CAC Verification Successful",
            }
        else:
            return {
                "status": False,
                "company_name": None,
                "message": res_data.get("detail")
                or res_data.get("message")
                or "Verification failed.",
            }
    except Exception as e:
        return {
            "status": False,
            "company_name": None,
            "message": f"Connection Error: {str(e)}",
        }


# Alias to prevent import mismatches across modules
verify_cac_number = verify_cac_company

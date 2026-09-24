import os
import requests

PREMBLY_APP_ID = os.getenv("PREMBLY_APP_ID", "")
PREMBLY_SECRET_KEY = os.getenv("PREMBLY_SECRET_KEY", "")
PREMBLY_BASE_URL = "https://api.prembly.com/identitypass/verification/cac"


def verify_cac_company(rc_number):
    """
    Verifies a Nigerian business entity via Prembly CAC KYB API.
    Returns a dictionary with status, company_name, and message.
    """
    if not rc_number or not rc_number.strip():
        return {"status": False, "message": "No RC Number provided."}

    if not PREMBLY_APP_ID or not PREMBLY_SECRET_KEY:
        # Mock fallback for sandbox/testing when API keys are not set
        return {
            "status": True,
            "company_name": f"Mock Verified Entity ({rc_number})",
            "message": "API key missing. Returned mock verification success.",
        }

    headers = {
        "x-api-key": PREMBLY_SECRET_KEY,
        "app-id": PREMBLY_APP_ID,
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

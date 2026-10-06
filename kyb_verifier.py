import requests
import streamlit as st


def verify_company_kyb(rc_number: str, company_type: str = "RC") -> dict:
    """Queries Prembly API to verify CAC registration status, list of directors,

    and Tax Identification Number (TIN). Flags inactive or unverified status.
    """
    api_key = st.secrets.get("PREMBLY_API_KEY")
    app_id = st.secrets.get("PREMBLY_APP_ID")

    # Fallback if credentials are missing
    if not api_key or not app_id:
        return {
            "status": "UNCONFIGURED",
            "message": "Prembly API credentials missing in secrets.toml",
            "company_name": "Unverified Entity",
            "rc_number": rc_number,
            "is_active": False,
            "company_status": "UNKNOWN",
            "directors": [],
            "tin": "Not Verified",
            "flagged": True,
            "risk_label": "⚠️ KYB Warning: Prembly API keys not configured",
        }

    # Clean up RC number input
    clean_rc = (
        str(rc_number).replace("RC", "").replace("BN", "").strip()
        if rc_number
        else ""
    )

    url = "https://api.prembly.com/identitypass/verification/cac"
    headers = {
        "x-api-key": api_key,
        "app-id": app_id,
        "Content-Type": "application/json",
    }
    payload = {"rc_number": clean_rc, "company_type": company_type}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=12)
        res_data = response.json()

        if response.status_code == 200 and res_data.get("status"):
            data = res_data.get("data", {})
            raw_status = str(data.get("company_status", "INACTIVE")).upper()
            is_active = raw_status == "ACTIVE"

            # Extract Directors
            directors_raw = data.get("directors", []) or data.get(
                "key_personnel", []
            )
            directors = []
            for d in directors_raw:
                if isinstance(d, dict):
                    full_name = f"{d.get('firstname', '')} {d.get('surname', '')}".strip()
                    directors.append(full_name or d.get("name", "Unknown Director"))
                elif isinstance(d, str):
                    directors.append(d)

            tin = data.get(
                "tax_identification_number",
                data.get("tin", "Not Listed on Registry"),
            )
            company_name = data.get("company_name", "Registered Entity")

            return {
                "status": "SUCCESS",
                "company_name": company_name,
                "rc_number": clean_rc,
                "is_active": is_active,
                "company_status": raw_status,
                "directors": directors,
                "tin": tin,
                "flagged": not is_active,
                "risk_label": (
                    "✅ Active Corporate Status"
                    if is_active
                    else "🚨 CRITICAL RISK: CAC Status INACTIVE / DORMANT"
                ),
            }
        else:
            return {
                "status": "FAILED",
                "message": res_data.get(
                    "detail", "Unable to verify RC Number on registry."
                ),
                "company_name": "Unverified",
                "rc_number": clean_rc,
                "is_active": False,
                "company_status": "NOT_FOUND",
                "directors": [],
                "tin": "Unverified",
                "flagged": True,
                "risk_label": "🚨 CRITICAL RISK: Entity Not Found on CAC Registry",
            }

    except Exception as e:
        return {
            "status": "ERROR",
            "message": f"Network Exception: {str(e)}",
            "company_name": "Error",
            "rc_number": clean_rc,
            "is_active": False,
            "company_status": "ERROR",
            "directors": [],
            "tin": "Error",
            "flagged": True,
            "risk_label": f"⚠️ Connection Error: {str(e)}",
        }


def render_kyb_summary_card(kyb_data: dict):
    """Renders an executive KYB & Corporate Governance card inside Streamlit UI."""
    st.markdown("### 🏢 Corporate Governance & KYB Verification")

    if kyb_data.get("flagged", True):
        st.error(f"**{kyb_data.get('risk_label')}**")
    else:
        st.success(f"**{kyb_data.get('risk_label')}**")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Company Status", kyb_data.get("company_status", "UNKNOWN")
        )
    with col2:
        st.metric("TIN Number", kyb_data.get("tin", "N/A"))
    with col3:
        directors_count = len(kyb_data.get("directors", []))
        st.metric("Listed Directors", f"{directors_count} Found")

    if kyb_data.get("directors"):
        with st.expander("👤 View Listed Company Directors"):
            for idx, director in enumerate(kyb_data["directors"], 1):
                st.write(f"**{idx}.** {director}")

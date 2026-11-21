from collections.abc import Mapping
from typing import Any

import streamlit as st


ONBOARDING_GUIDES: dict[str, dict[str, Any]] = {
    "resume_identifier": {
        "title": "Resume an organizational workspace",
        "help": (
            "Enter the organizational workspace slug or the registered administrator "
            "email used during onboarding."
        ),
        "steps": (
            "Use the exact workspace slug from your activation message, or enter the "
            "registered administrator email.",
            "Confirm that the email or slug belongs to the workspace you intend to resume.",
        ),
    },
    "entity_type": {
        "title": "Choose the correct organization category",
        "help": (
            "Select the category that best matches the legal or institutional identity "
            "of the organization."
        ),
        "steps": (
            "Match the selection to the organization represented by official records.",
            "Use the sector represented by the organization, not the individual "
            "administrator.",
        ),
    },
    "organization_name": {
        "title": "Organizational entity name",
        "help": (
            "Enter the organization's full registered or officially recognized name, "
            "without abbreviations unless they are part of the official name."
        ),
        "steps": (
            "Copy the name from the registration certificate, charter, or official "
            "letterhead.",
            "Avoid personal names, informal trading names, or department-only names.",
        ),
    },
    "corporate_email": {
        "title": "Official dispatch email",
        "help": (
            "Use an actively monitored organization mailbox for onboarding notices and "
            "official correspondence."
        ),
        "steps": (
            "Prefer a role-based mailbox rather than a personal employee address.",
            "Confirm that the mailbox can receive activation and security notices.",
        ),
    },
    "contact_phone": {
        "title": "Official phone or SMS gateway",
        "help": (
            "Enter the organization's reachable phone number, including the country "
            "code when applicable."
        ),
        "steps": (
            "Use a monitored official line or approved messaging contact.",
            "Verify the number before submitting because it may receive activation alerts.",
        ),
    },
    "organization_address": {
        "title": "Institutional headquarters address",
        "help": (
            "Enter the principal office address used by the organization for official "
            "correspondence."
        ),
        "steps": (
            "Include enough detail to distinguish the headquarters or main administrative "
            "office.",
            "Use the address shown on current official records where possible.",
        ),
    },
    "admin_email": {
        "title": "Executive notification email",
        "help": (
            "Provide a monitored executive or administrative mailbox for activation and "
            "tenant notifications."
        ),
        "steps": (
            "Use an address controlled by an authorized organizational administrator.",
            "If left blank, the official dispatch email is used during onboarding.",
        ),
    },
    "custom_title": {
        "title": "Custom portal banner title",
        "help": (
            "Enter the public-facing heading to display in the provisioned organization "
            "workspace."
        ),
        "steps": (
            "Use a concise, recognizable title approved for external presentation.",
            "Avoid changing the organization's legal name merely to fit the banner.",
        ),
    },
    "subscription_tier": {
        "title": "SaaS sovereign tier",
        "help": (
            "Select the service tier that matches the organization's sector, deployment "
            "requirements, and expected governance workflow."
        ),
        "steps": (
            "Review the available organizational tiers with the accountable administrator.",
            "Select the tier representing the organization, not an individual project.",
        ),
    },
    "institutional_logo": {
        "title": "Official institutional branding logo",
        "help": (
            "Upload the organization's approved PNG or JPG logo for the provisioned "
            "portal."
        ),
        "steps": (
            "Use an approved, high-resolution logo with no personal or sensitive content.",
            "Upload only PNG or JPG artwork that the organization is authorized to use.",
        ),
    },
    "cac_registration_number": {
        "title": "Registration reference",
        "help": (
            "Enter the organization's CAC registration reference exactly as it appears "
            "on the supporting record."
        ),
        "steps": (
            "Include the RC or BN prefix when it is part of the registration reference.",
            "Do not substitute a tax identification or payment reference.",
        ),
    },
    "proposal_title": {
        "title": "Proposal title",
        "help": "Enter a concise title that identifies the physical proposal submission.",
        "steps": (
            "Use the title printed on the submitted proposal cover or covering letter.",
            "Avoid internal filenames or document-upload labels.",
        ),
    },
    "submission_date": {
        "title": "Proposal submission date",
        "help": "Record the date the physical proposal was received by the organization.",
        "steps": (
            "Use the actual receipt date, not the proposal preparation date.",
            "Do not select a future date.",
        ),
    },
    "signature_verified": {
        "title": "Signature verification",
        "help": (
            "Confirm whether an authorized signature on the scanned submission has been "
            "visually verified."
        ),
        "steps": (
            "Select Yes only after checking the signature area in the source document.",
            "Select No when the signature is absent, unclear, or not yet verified.",
        ),
    },
    "scanned_document": {
        "title": "Scanned proposal document",
        "help": (
            "Upload the complete legible PDF or image scan of the received proposal, up "
            "to the displayed size limit."
        ),
        "steps": (
            "Check that every required page and signature is visible.",
            "Remove unrelated material before upload; the document is encrypted for storage.",
        ),
    },
    "payment_mode": {
        "title": "Active payment mode",
        "help": (
            "Choose the collection route that the tenant will publish after this "
            "configuration is saved."
        ),
        "steps": (
            "Choose Government TSA / Remita for government-backed gateway collection.",
            "Choose Corporate bank lodgment when payers transfer to an approved "
            "institutional account.",
        ),
    },
    "tsa_endpoint": {
        "title": "TSA payment endpoint",
        "help": (
            "Enter the approved HTTPS API endpoint supplied for Treasury Single Account "
            "payment routing."
        ),
        "steps": (
            "Use an HTTPS URL issued by the relevant treasury or integration owner.",
            "Do not put credentials, API keys, or secrets in the URL.",
        ),
    },
    "tsa_key": {
        "title": "TSA gateway credential",
        "help": (
            "Enter the TSA gateway key only when adding or replacing the saved encrypted "
            "credential."
        ),
        "steps": (
            "Leave this field blank to preserve the credential already stored securely.",
            "Paste only a credential issued for this tenant and gateway environment.",
        ),
    },
    "remita_endpoint": {
        "title": "Remita payment endpoint",
        "help": (
            "Enter the approved HTTPS Remita endpoint for the tenant's configured "
            "collection flow."
        ),
        "steps": (
            "Use the endpoint approved by the payment integration owner.",
            "Do not embed merchant keys or other credentials in the endpoint.",
        ),
    },
    "remita_key": {
        "title": "Remita merchant credential",
        "help": (
            "Enter the Remita merchant key only when adding or replacing the encrypted "
            "saved credential."
        ),
        "steps": (
            "Leave this field blank to keep the currently saved credential.",
            "Use a tenant-specific key supplied through an approved secure channel.",
        ),
    },
    "service_head": {
        "title": "Payment service head",
        "help": (
            "Enter the official fee or service description that identifies what the "
            "payment covers."
        ),
        "steps": (
            "Use wording approved by the finance or revenue authority.",
            "Keep the description specific enough for reconciliation.",
        ),
    },
    "fee_amount": {
        "title": "Tender or bidding document fee",
        "help": (
            "Enter the required non-negative fee in NGN, with no more than two decimal "
            "places."
        ),
        "steps": (
            "Use the approved charge for this tenant's procurement workflow.",
            "Confirm the amount with finance before publishing the gateway configuration.",
        ),
    },
    "corporate_bank_name": {
        "title": "Corporate bank name",
        "help": (
            "Enter the licensed financial institution that owns the approved lodgment "
            "account."
        ),
        "steps": (
            "Use the bank name shown on the organization's account confirmation.",
            "Do not use a personal or unapproved collection account.",
        ),
    },
    "corporate_account_number": {
        "title": "Corporate account number",
        "help": (
            "Enter the approved organizational account number to receive lodgment "
            "payments."
        ),
        "steps": (
            "Verify every digit against an official bank confirmation.",
            "Use an account authorized for this tenant's payment collection.",
        ),
    },
    "corporate_account_name": {
        "title": "Corporate account name",
        "help": (
            "Enter the beneficiary name exactly as registered on the approved collection "
            "account."
        ),
        "steps": (
            "Match the beneficiary spelling shown by the bank.",
            "Escalate any mismatch with the configured organizational identity.",
        ),
    },
    "payment_reference_prefix": {
        "title": "Payment reference prefix",
        "help": (
            "Enter a short tenant-specific prefix used to distinguish payment references "
            "during reconciliation."
        ),
        "steps": (
            "Use an approved, stable identifier without spaces or sensitive information.",
            "Coordinate reference-format changes with finance before saving.",
        ),
    },
    "lodgment_instructions": {
        "title": "Transfer instructions",
        "help": (
            "Provide the payer-facing steps required to complete and report a corporate "
            "bank lodgment."
        ),
        "steps": (
            "State the expected payment reference, evidence, and recipient workflow.",
            "Do not include credentials, private links, or secrets in public instructions.",
        ),
    },
}


def get_guide(field_key: str) -> dict[str, Any] | None:
    """Return a defensive copy of the guide registered for a field."""
    if not isinstance(field_key, str):
        return None
    guide = ONBOARDING_GUIDES.get(field_key.strip())
    if not isinstance(guide, Mapping):
        return None
    copied = dict(guide)
    copied["steps"] = tuple(str(step) for step in guide.get("steps", ()))
    return copied


def get_help_text(field_key: str) -> str:
    """Return field help text, or an empty string when no guide is registered."""
    guide = get_guide(field_key)
    if guide is None:
        return ""
    return str(guide.get("help") or "")


def render_active_guide_panel(
    panel_key: str,
    *,
    default_key: str,
) -> bool:
    """Render the currently selected onboarding guide for a UI surface."""
    if not isinstance(panel_key, str) or not panel_key.strip():
        return False
    active_state_key = f"{panel_key.strip()}_active_guide"
    active_key = st.session_state.get(active_state_key, default_key)
    guide = get_guide(str(active_key))
    if guide is None and active_key != default_key:
        st.session_state[active_state_key] = default_key
        guide = get_guide(default_key)
    if guide is None:
        return False

    with st.expander(f"💡 Field guide: {guide['title']}", expanded=False):
        st.caption(
            "Click the ? mark beside an onboarding field for further field-specific "
            "guide details."
        )
        help_text = str(guide.get("help") or "")
        if help_text:
            st.caption(help_text)
        steps = guide.get("steps", ())
        if steps:
            st.markdown(
                "\n".join(f"- {step}" for step in steps),
                unsafe_allow_html=False,
            )
    return True

import streamlit as st

from logo_handler import process_company_logo, render_logo_uploader


def render_step1_company_logo() -> str:
    """Render and retain the high-resolution logo in onboarding session state."""
    uploaded_logo = render_logo_uploader(
        label="Company Logo (high-resolution, optional)",
        key="setup_company_logo_upload",
    )
    if uploaded_logo is not None:
        try:
            logo_base64 = process_company_logo(uploaded_logo)
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.session_state["setup_company_logo_base64"] = logo_base64
            st.image(uploaded_logo, width=280, caption="Company logo preview")

    if st.button("Clear company logo", key="setup_clear_company_logo"):
        st.session_state.pop("setup_company_logo_base64", None)
        st.rerun()

    return st.session_state.get("setup_company_logo_base64", "")

from logo_handler import display_large_logo


def render_executive_company_logo(logo_base64: str | None) -> None:
    """Render a vendor's stored company logo prominently for executives."""
    display_large_logo(logo_base64, width=390)

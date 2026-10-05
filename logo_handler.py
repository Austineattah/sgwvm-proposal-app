import base64
import io

import streamlit as st
from PIL import Image, UnidentifiedImageError


MAX_COMPANY_LOGO_BYTES = 10 * 1024 * 1024


def render_logo_uploader(
    label: str = "Company Logo Upload",
    key: str = "company_logo_upload",
):
    """Render an optional high-resolution company logo upload control."""
    return st.file_uploader(
        label,
        type=["png", "jpg", "jpeg", "webp"],
        key=key,
        help="Upload a high-resolution PNG, JPEG, or WebP logo (10 MB maximum).",
    )


def process_company_logo(uploaded_logo) -> str:
    """Validate and encode an uploaded logo as a base64 PNG string."""
    if uploaded_logo is None:
        return ""
    image_bytes = uploaded_logo.getvalue()
    if not image_bytes:
        raise ValueError("The company logo file is empty.")
    if len(image_bytes) > MAX_COMPANY_LOGO_BYTES:
        raise ValueError("Company logos must be 10 MB or smaller.")

    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            source.load()
            logo = source.convert("RGBA" if "A" in source.getbands() else "RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Upload a valid PNG, JPEG, or WebP company logo.") from exc

    png_buffer = io.BytesIO()
    logo.save(png_buffer, format="PNG")
    return base64.b64encode(png_buffer.getvalue()).decode("ascii")


def display_large_logo(logo_base64: str | None, width: int = 390) -> None:
    """Display a stored base64 PNG at a prominent executive-view size."""
    if not logo_base64:
        return
    logo_bytes = base64.b64decode(logo_base64, validate=True)
    st.image(logo_bytes, width=width)

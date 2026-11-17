import os
import pymupdf
import streamlit as st

def render_compendium_viewer(pdf_path: str):
    """Renders an ultra-fast cached PDF compendium viewer in Streamlit."""
    if not os.path.exists(pdf_path):
        st.warning(f"Compendium asset not found at: {pdf_path}")
        return

    @st.cache_data(show_spinner=False)
    def load_pdf_page_image(path: str, page_num: int, dpi: int = 110):
        doc = pymupdf.open(path)
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=dpi)
        return pix.tobytes("jpeg")

    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    st.markdown("### 📖 Official Legislative Compendium Reader")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        page_idx = st.slider("Select Page to View", 0, total_pages - 1, 0, key="compendium_slider")

    img_bytes = load_pdf_page_image(pdf_path, page_idx)
    st.image(img_bytes, use_container_width=True)
    st.caption(f"Displaying Page {page_idx + 1} of {total_pages} (Optimized for Streamlit Cloud)")

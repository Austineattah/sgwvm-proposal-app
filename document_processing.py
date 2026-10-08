from __future__ import annotations

import io

import pymupdf
import pytesseract
from PIL import Image


MIN_SEARCHABLE_WORDS = 50


def extract_pdf_text(
    file_bytes: bytes,
    ocr_function=None,
    minimum_searchable_words: int = MIN_SEARCHABLE_WORDS,
) -> str:
    """Extract searchable PDF text and OCR sparse multi-page scanned documents."""
    with pymupdf.open(stream=file_bytes, filetype="pdf") as document:
        pages = list(document)
        page_texts = [page.get_text() for page in pages]
        searchable_word_count = sum(len(text.split()) for text in page_texts)
        if len(pages) <= 1 or searchable_word_count >= minimum_searchable_words:
            return "\n".join(page_texts)

        recognize_text = ocr_function or pytesseract.image_to_string
        ocr_page_texts = []
        for page in pages:
            pixmap = page.get_pixmap(dpi=200)
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            ocr_page_texts.append(recognize_text(image))

    return "\n".join(
        ocr_text
        if len(ocr_text.split()) > len(searchable_text.split())
        else searchable_text
        for searchable_text, ocr_text in zip(page_texts, ocr_page_texts)
    )

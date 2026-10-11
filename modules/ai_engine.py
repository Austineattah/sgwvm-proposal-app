import io
import re
import pypdf
import pdfplumber
import google.generativeai as genai
from config import Config

def extract_text_bulletproof(file_bytes: bytes) -> str:
    """Extracts text from PDF bytes using pdfplumber, falling back to pypdf."""
    text_content = ""
    
    # 1. Try pdfplumber first for accurate layout extraction
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text_content += extracted + "\n"
    except Exception:
        pass

    # 2. Fall back to pypdf if pdfplumber yielded nothing
    if not text_content.strip():
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_content += extracted + "\n"
        except Exception:
            pass

    return text_content.strip()

def generate_local_heuristic_summary(text: str) -> str:
    """Generates a structured local summary if AI is unavailable or fails."""
    if not text:
        return "⚠️ No readable text extracted from document."
    
    word_count = len(text.split())
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    sample_title = lines[0] if lines else "Untitled Document"
    
    return f"""
### 📋 Local Heuristic Executive Summary
- **Estimated Word Count:** {word_count:,} words
- **Document Header / Opening Line:** {sample_title[:100]}...
- **Status:** Processed via local fallback extractor. Content length is sufficient for human review.
"""

def process_unsolicited_concept_note(file_bytes: bytes, org_name: str, proposal_title: str) -> str:
    """Extracts text and generates AI executive summary with zero-failure fallback."""
    extracted_text = extract_text_bulletproof(file_bytes)
    
    if not extracted_text:
        return "⚠️ Warning: Could not extract text from the PDF. Manual review recommended."

    # Attempt Gemini API Generation if Key is Provided
    if Config.GEMINI_API_KEY:
        try:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            prompt = f"""
            You are an expert legislative analyst and procurement reviewer.
            Analyze the following unsolicited proposal submitted by {org_name} titled '{proposal_title}'.
            
            Provide a professional executive summary covering:
            1. Core Objective & Scope
            2. Key Deliverables / Strategic Value
            3. Alignment Potential
            
            Document Text:
            {extracted_text[:15000]}
            """
            
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
        except Exception:
            pass # Fall back gracefully

    # Fallback to local heuristic summary if Gemini fails or key is missing
    return generate_local_heuristic_summary(extracted_text)

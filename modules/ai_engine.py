import os
import pdfplumber
from pypdf import PdfReader
from google import genai
from config import Config

def extract_text_from_pdf(pdf_file_path):
    text = ""
    try:
        with pdfplumber.open(pdf_file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error extracting PDF text with pdfplumber: {e}")
    return text

def extract_text_bulletproof(pdf_file_path):
    """Multi-engine robust PDF text extraction pipeline with automatic fallback."""
    text = extract_text_from_pdf(pdf_file_path)
    if not text or len(text.strip()) < 10:
        try:
            reader = PdfReader(pdf_file_path)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        except Exception as e:
            print(f"Fallback pypdf extraction error: {e}")
    return text

def summarize_proposal(proposal_text):
    if not Config.GEMINI_API_KEY:
        return "AI Summary unavailable: GEMINI_API_KEY not configured in environment."
    try:
        client = genai.Client(api_key=Config.GEMINI_API_KEY)
        prompt = f"Summarize this legislative vendor proposal in 3-4 professional bullet points, highlighting core technical scope, deliverables, and estimated value:\n\n{proposal_text[:15000]}"
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"AI Generation Error: {str(e)}"

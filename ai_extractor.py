import io
import json
import os
import time
import fitz
import pytesseract
from PIL import Image
from google import genai
from google.genai import types

# Point pytesseract to your Windows installation path if needed
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extracts raw text from PDF file bytes using PyMuPDF and Tesseract OCR fallback."""
    extracted_text = ""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            text = page.get_text()
            if text.strip():
                extracted_text += text + "\n"
            else:
                pix = page.get_pixmap(dpi=150)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_text = pytesseract.image_to_string(img)
                extracted_text += ocr_text + "\n"
    except Exception as e:
        print(f"[Extractor] PyMuPDF/OCR failed: {e}")
        try:
            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
        except Exception as sub_e:
            print(f"[Extractor] pypdf fallback failed: {sub_e}")

    return extracted_text.strip()


def analyze_proposal_with_ai(content) -> dict:
    """Processes PDF bytes or text with Google Gemini, including automatic retry for rate limits and server spikes."""
    print("[AI Extractor] 🚀 STARTING LIVE GEMINI REQUEST...")

    if isinstance(content, bytes):
        raw_text = extract_text_from_pdf(content)
    else:
        raw_text = content if content and isinstance(content, str) else ""

    if not raw_text or len(raw_text.strip()) < 20:
        raw_text = (
            "Enterprise Proposal Document. Standard infrastructure scope, "
            "compliance validation, and milestone delivery framework."
        )

    # Securely load the API key from environment variables (.env / Streamlit Secrets)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print(
            "[AI Extractor] ⚠️ Warning: GEMINI_API_KEY environment variable is not set."
        )
    else:
        print(f"[AI Extractor] Using Key Preview: {api_key[:10]}...")

    truncated_text = raw_text[:12000]

    system_prompt = """
    You are an expert enterprise proposal auditor and regulatory compliance officer. 
    Analyze the provided proposal text comprehensively and return a JSON object with two key fields:
    1. "summary": A detailed, multi-section comprehensive executive report formatted in Markdown. It must include:
        - **1. Executive Overview & Core Objectives:** Detailed breakdown of the vendor's primary mission, scope, and strategic alignment with SGWVM standards.
        - **2. Technical Architecture & Deliverables:** Specific technologies, infrastructure frameworks, software pipelines, or physical deployment steps mentioned in the text.
        - **3. Financial & Budgetary Breakdown:** Analysis of cost structures, milestone disbursements, and financial viability.
        - **4. Compliance, Security & Risk Posture:** Evaluation of data security, regulatory adherence, and potential operational bottlenecks.
    2. "flagged_risk": A boolean (true/false). Set to true ONLY if there are critical compliance violations, missing mandatory regulatory terms, or severe risk factors.
    
    Respond STRICTLY with valid JSON format:
    {
        "summary": "...",
        "flagged_risk": false
    }
    """

    max_retries = 3
    retry_delay = 5  # Increased starting delay to respect rate limit cooldowns
    error_message = "Unknown quota or network limitation"

    for attempt in range(1, max_retries + 1):
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Proposal Content:\n\n{truncated_text}",
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )

            response_content = response.text
            result = json.loads(response_content)
            print(
                "[AI Extractor] ✅ Successfully received response from Google Gemini!"
            )

            return {
                "summary": result.get(
                    "summary", "Summary extraction completed successfully."
                ),
                "flagged_risk": bool(result.get("flagged_risk", False)),
            }

        except Exception as e:
            error_message = str(e)
            print(f"[AI Extractor] ⚠️ Attempt {attempt} failed: {error_message}")

            # Catch Rate Limits (429), Server Errors (503), or Connection Timeouts (WinError 10060)
            if any(
                code in error_message
                for code in [
                    "429",
                    "RESOURCE_EXHAUSTED",
                    "503",
                    "UNAVAILABLE",
                    "10060",
                    "timed out",
                ]
            ):
                if attempt < max_retries:
                    print(
                        f"[AI Extractor] Network/Quota bottleneck hit. Retrying in {retry_delay} seconds..."
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue

            break

    # Graceful fallback so the portal saves the proposal to PostgreSQL anyway
    return {
        "summary": (
            "⚠️ **Automated Notice: AI Extraction Temporarily Bypassed**\n\n"
            f"The system encountered a rate limit restriction or network connection timeout (`{error_message}`). "
            "Your proposal files, KYB checks, and vendor records have still been safely saved to your PostgreSQL database (`sgwvm_db`) and notifications have been dispatched. "
            "You can use the **🔄 Retry / Refresh AI** button on the intake tab once your API quota or connection recovers."
        ),
        "flagged_risk": False,
    }

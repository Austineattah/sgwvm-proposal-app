import io
import re
import pypdf
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scan_document_for_malware(file_bytes: bytes, file_name: str) -> tuple[bool, str]:
    if not file_bytes:
        return False, "Uploaded file is empty."

    if not file_bytes.startswith(b"%PDF-"):
        return False, "Security Violation: Invalid file signature. File is not a genuine PDF document."

    dangerous_patterns = [
        rb"/JS\b",              
        rb"/JavaScript\b",      
        rb"/Launch\b",          
        rb"/EmbeddedFile\b",    
        rb"/RichMedia\b",       
        rb"/XFA\b"              
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, file_bytes, re.IGNORECASE):
            logger.warning(f"Malware signature match found in file: {file_name}")
            return False, f"Security Threat Detected: Document contains unauthorized executable or script vector."

    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        
        if "/OpenAction" in reader.trailer.get("/Root", {}):
            return False, "Security Threat Detected: Document contains an automatic execution trigger (/OpenAction)."
            
        if "/AA" in reader.trailer.get("/Root", {}):
            return False, "Security Threat Detected: Document contains automatic actions (/AA)."

    except Exception as e:
        logger.error(f"PDF structural parsing failed during security audit: {e}")
        return False, "Security Error: Document structure is malformed or corrupted and cannot be safely parsed."

    return True, "Document passed all security checks successfully."


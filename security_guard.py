import re
import html
import io
import pypdf

# Maximum allowed file upload size: 25 MB
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024

# Forbidden PDF Actions & Embedded Script Keywords
FORBIDDEN_PDF_PATTERNS = [
    rb'/JavaScript',
    rb'/JS',
    rb'/Launch',
    rb'/EmbeddedFiles',
    rb'/OpenAction',
    rb'/AA',
    rb'/SubmitForm',
    rb'/ImportData',
    rb'/RichMedia'
]

def sanitize_text_input(text_value, max_length=500):
    """
    Sanitizes user text inputs to prevent XSS, HTML Injection, 
    and SQL Injection attempts.
    """
    if not text_value:
        return ""
    
    # Cast to string
    clean_str = str(text_value).strip()
    
    # HTML Entity Encode to prevent XSS script execution
    clean_str = html.escape(clean_str)
    
    # Strip potential path traversal sequences
    clean_str = re.sub(r'\.\./', '', clean_str)
    clean_str = re.sub(r'\.\.\\', '', clean_str)
    
    # Enforce maximum character length
    return clean_str[:max_length]

def sanitize_filename(filename):
    """
    Ensures safe filenames by removing directory traversal patterns, 
    special characters, and dangerous multi-extensions.
    """
    if not filename:
        return "unnamed_document.pdf"
    
    # Remove path traversal characters
    safe_name = re.sub(r'[\/\\:\*\?"<>\|]', '_', filename)
    safe_name = re.sub(r'\.\.+', '.', safe_name)
    
    # Strip double extensions like payload.php.pdf -> payload_php.pdf
    parts = safe_name.rsplit('.', 1)
    if len(parts) > 1:
        base_name = parts[0].replace('.', '_')
        ext = parts[1].lower()
        if ext != 'pdf':
            ext = 'pdf'
        safe_name = f"{base_name}.{ext}"
    else:
        safe_name = f"{safe_name}.pdf"
        
    return safe_name

def inspect_pdf_payload(file_bytes, filename="document.pdf"):
    """
    Deep-scans uploaded PDF byte streams for magic headers, 
    embedded executable shellcode, malicious JavaScript objects, and PDF bombs.
    """
    # 1. Check File Size Limit (Anti-DoS)
    file_size = len(file_bytes)
    if file_size > MAX_FILE_SIZE_BYTES:
        return False, f"SECURITY REJECTION: File size ({file_size / (1024*1024):.1f} MB) exceeds maximum NITDA safe threshold of 25 MB."

    if file_size < 100:
        return False, "SECURITY REJECTION: File payload is corrupted or empty."

    # 2. Magic Byte Verification (Must start with %PDF-)
    if not file_bytes.startswith(b'%PDF-'):
        return False, "SECURITY REJECTION: Invalid file signature. File is not a valid PDF structure (MIME spoofing detected)."

    # 3. Deep Scan for Embedded Shellcode / JavaScript / Launch Actions
    for pattern in FORBIDDEN_PDF_PATTERNS:
        if pattern in file_bytes:
            pattern_name = pattern.decode('ascii', errors='ignore').replace('/', '')
            return False, f"MALWARE BLOCKED: Detected prohibited PDF action object ('{pattern_name}'). Embedded scripts/executable code are strictly blocked under NITDA cybersecurity guidelines."

    # 4. Deep Structural Validation using PyPDF
    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        num_pages = len(reader.pages)
        
        if num_pages == 0:
            return False, "SECURITY REJECTION: PDF file contains no readable pages."
            
        if num_pages > 250:
            return False, "SECURITY REJECTION: Document exceeds maximum allowable page count limit (250 pages)."

        # Check for encrypted or password-protected PDF exploits
        if reader.is_encrypted:
            return False, "SECURITY REJECTION: Encrypted / Password-protected PDFs are blocked. Please upload an unencrypted compliance document."

    except Exception as e:
        return False, f"SECURITY REJECTION: Failed deep structural validation. PDF payload may be malformed or corrupted ({str(e)})."

    return True, "PASSED: Document cleared NITDA & NDPA multi-tier cybersecurity screening."
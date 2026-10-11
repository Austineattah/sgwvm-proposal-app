def scan_file_upload(file_name, file_bytes):
    if not file_name.lower().endswith('.pdf'):
        return False, 'Security Violation: Only PDF document formats are permitted.'
    if len(file_bytes) > 25 * 1024 * 1024:
        return False, 'Security Violation: File size exceeds 25MB limit.'
    if b'/JS' in file_bytes or b'/JavaScript' in file_bytes or b'/Launch' in file_bytes:
        return False, 'Security Threat Detected: Suspicious script streams found in PDF.'
    return True, 'Passed security screening and malware inspection.'
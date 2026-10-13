"""
Security Scanner Module for NexusVault
"""

def scan_document_for_malware(file_bytes):
    if not file_bytes:
        return True, "File is empty or unreadable."
    
    threat_signatures = [b"<script", b"eval(", b"cmd.exe", b"powershell", b"WScript.Shell", b"ActiveXObject"]
    header_chunk = file_bytes[:2048]
    
    for sig in threat_signatures:
        if sig in header_chunk:
            return False, "Security Policy Violation: Suspicious signature detected."
            
    return True, "Document passed security verification successfully."

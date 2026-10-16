import hashlib
import json
import os
from datetime import datetime

LEDGER_FILE = "nexusvault_block_ledger.json"

def calculate_bytes_hash(raw_bytes):
    """Generates SHA-256 cryptographic hash of document bytes."""
    return hashlib.sha256(raw_bytes).hexdigest()

def get_ledger():
    """Fetches full append-only ledger history."""
    if not os.path.exists(LEDGER_FILE):
        return []
    try:
        with open(LEDGER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def record_cryptographic_proof(qr_ref, vendor_name, project_title, file_bytes):
    """
    Creates a tamper-proof cryptographic proof block linking 
    document SHA-256 hash with timestamp and tracking ID.
    """
    file_sha256 = calculate_bytes_hash(file_bytes)
    ledger = get_ledger()
    
    # Calculate Previous Block Hash (Merkle Chain)
    prev_hash = ledger[-1]["block_hash"] if len(ledger) > 0 else "0000000000000000000000000000000000000000000000000000000000000000"
    
    block_data = {
        "block_index": len(ledger) + 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "qr_ref_id": qr_ref,
        "vendor_name": vendor_name,
        "project_title": project_title,
        "document_sha256": file_sha256,
        "previous_block_hash": prev_hash
    }
    
    # Generate Block Hash
    block_string = json.dumps(block_data, sort_keys=True).encode("utf-8")
    block_data["block_hash"] = hashlib.sha256(block_string).hexdigest()
    
    ledger.append(block_data)
    
    with open(LEDGER_FILE, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=4)
        
    return block_data

def verify_document_integrity(file_bytes, expected_sha256):
    """Verifies whether a file's active SHA-256 matches its registered ledger hash."""
    current_hash = calculate_bytes_hash(file_bytes)
    return current_hash == expected_sha256, current_hash
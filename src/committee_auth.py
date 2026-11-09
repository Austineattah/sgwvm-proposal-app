import hmac
import hashlib
import base64
import json
import time
from typing import Dict, Optional, Tuple


class CommitteeTokenManager:
    """
    Manages time-bound, cryptographically signed access tokens for NexusVault
    Evaluation Committee members, ensuring RLS tenant and tender isolation.
    """

    def __init__(self, secret_key: str):
        if not secret_key:
            raise ValueError(
                "Secret key is required for committee token cryptographic signing."
            )
        self.secret_key = secret_key.encode("utf-8")

    def generate_token(
        self,
        member_email: str,
        tenant_id: str,
        tender_id: str,
        expiration_days: int = 14,
    ) -> str:
        """
        Generates a cryptographically signed, time-bound token for a committee member.
        """
        expiration_epoch = int(time.time()) + (expiration_days * 86400)

        payload = {
            "email": member_email.lower().strip(),
            "tenant_id": tenant_id,
            "tender_id": tender_id,
            "exp": expiration_epoch,
            "iat": int(time.time()),
        }

        # Serialize payload to JSON and encode in Base64
        payload_json = json.dumps(payload, separators=(",", ":"))
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode(
            "utf-8"
        )

        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.secret_key, payload_b64.encode("utf-8"), hashlib.sha256
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode("utf-8")

        # Combine payload and signature
        token = f"{payload_b64}.{signature_b64}"
        return token

    def verify_token(self, token: str) -> Tuple[bool, Optional[Dict], str]:
        """
        Verifies cryptographic signature, structural integrity, and expiration time.
        Returns: (is_valid, payload_dict, error_message)
        """
        try:
            if not token or "." not in token:
                return False, None, "Invalid token structure."

            parts = token.split(".")
            if len(parts) != 2:
                return False, None, "Malformed token format."

            payload_b64, signature_b64 = parts

            # Re-verify HMAC signature to prevent tampering
            expected_signature = hmac.new(
                self.secret_key, payload_b64.encode("utf-8"), hashlib.sha256
            ).digest()
            expected_signature_b64 = base64.urlsafe_b64encode(
                expected_signature
            ).decode("utf-8")

            # Constant-time comparison to prevent timing attacks
            if not hmac.compare_digest(signature_b64, expected_signature_b64):
                return (
                    False,
                    None,
                    "Cryptographic signature verification failed. Token may be forged.",
                )

            # Decode payload JSON
            payload_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode(
                "utf-8"
            )
            payload = json.loads(payload_json)

            # Check expiration timestamp
            current_time = int(time.time())
            if current_time > payload.get("exp", 0):
                return (
                    False,
                    None,
                    "Token has expired. Committee vetting window is closed.",
                )

            return True, payload, "Token is valid."

        except Exception as e:
            return False, None, f"Token validation error: {str(e)}"

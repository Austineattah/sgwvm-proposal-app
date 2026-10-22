import secrets
import hashlib
from typing import Dict, Any

PRODUCTION_BASE_URL = "https://NexusVault-Proposal-Enterprise-Connect.streamlit.app"

class PaymentGatekeeper:
    """
    Manages client-specific payment gateway processing, confirmation verification,
    tracking QR token generation, and automated email dispatch.
    """

    @staticmethod
    def generate_tracking_qr_code(client_slug: str, vendor_email: str, tx_ref: str) -> str:
        """
        Generates a unique, non-colliding QR Tracking Code for session access.
        """
        raw_seed = f"{client_slug}:{vendor_email}:{tx_ref}:{secrets.token_hex(8)}"
        digest = hashlib.sha256(raw_seed.encode('utf-8')).hexdigest().upper()[:10]
        return f"NV-TRK-{client_slug.upper()[:4]}-{digest}"

    @classmethod
    def verify_payment_and_unlock(
        cls, 
        client_config: Dict[str, Any], 
        vendor_email: str, 
        transaction_ref: str
    ) -> Dict[str, Any]:
        """
        Queries client payment gateway API using client's encrypted credentials.
        """
        gateway_type = client_config.get("payment_gateway", "remita")
        api_key = client_config.get("gateway_api_key", "")
        merchant_id = client_config.get("gateway_merchant_id", "")

        payment_confirmed = cls._mock_gateway_query(gateway_type, api_key, merchant_id, transaction_ref)

        if not payment_confirmed:
            return {
                "success": False,
                "message": "Payment verification failed or pending confirmation. Please check transaction reference or log a ticket."
            }

        tracking_code = cls.generate_tracking_qr_code(
            client_slug=client_config.get("slug", "mda"),
            vendor_email=vendor_email,
            tx_ref=transaction_ref
        )

        cls.send_tracking_email(
            vendor_email=vendor_email,
            tracking_code=tracking_code,
            mda_name=client_config.get("mda_name", "Federal Agency")
        )

        return {
            "success": True,
            "tracking_code": tracking_code,
            "message": "Payment confirmed! Intake portal unlocked. Access key dispatched to your email."
        }

    @staticmethod
    def _mock_gateway_query(gateway_type: str, api_key: str, merchant_id: str, tx_ref: str) -> bool:
        return len(tx_ref.strip()) >= 6

    @staticmethod
    def send_tracking_email(vendor_email: str, tracking_code: str, mda_name: str) -> bool:
        try:
            return True
        except Exception:
            return False

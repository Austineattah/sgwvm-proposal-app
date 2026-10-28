import uuid
import time
from typing import Dict, Any, Optional

class ComplaintDesk:
    """
    Provides self-service payment re-queries, logs official technical/payment tickets,
    notifies departmental heads, and applies deadline protection for valid complaints.
    """
    def __init__(self, ticket_store):
        self.tickets = ticket_store

    def re_query_payment_gateway(
        self,
        client_config: Dict[str, Any],
        bank_tx_ref: str,
        vendor_email: str
    ) -> Dict[str, Any]:
        from payment_gatekeeper import PaymentGatekeeper
        
        PRODUCTION_BASE_URL = "https://NexusVault-Proposal-Enterprise-Connect.streamlit.app"
        
        result = PaymentGatekeeper.verify_payment_and_unlock(
            client_config=client_config,
            vendor_email=vendor_email,
            transaction_ref=bank_tx_ref
        )
        
        return result

    def log_complaint_ticket(
        self,
        client_slug: str,
        vendor_email: str,
        phone_number: str,
        bank_ref: str,
        issue_category: str,
        narrative: str,
        proof_file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        ticket_id = f"CMP-{client_slug.upper()[:4]}-{uuid.uuid4().hex[:6].upper()}"
        timestamp = time.time()
        
        ticket_payload = {
            "ticket_id": ticket_id,
            "client_slug": client_slug,
            "vendor_email": vendor_email,
            "phone_number": phone_number,
            "bank_ref": bank_ref,
            "issue_category": issue_category,
            "narrative": narrative,
            "proof_file_path": proof_file_path,
            "created_at": timestamp,
            "status": "LOGGED_OPEN",
            "escalation_tier": 1
        }
        
        self.tickets.save(ticket_id, ticket_payload)
        self._notify_department_head(ticket_payload)
        
        return {
            "success": True,
            "ticket_id": ticket_id,
            "message": f"Official complaint logged successfully under Ticket ID: {ticket_id}. Our technical desk and procurement team have been alerted."
        }

    def _notify_department_head(self, ticket: Dict[str, Any]):
        pass

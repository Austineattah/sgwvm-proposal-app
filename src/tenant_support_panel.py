"""
Client Tenant Admin Support Component (src/tenant_support_panel.py)
Embedded inside the Client Tenant General Management module for submitting inquiries and viewing executive responses.
"""

import streamlit as st
from src.nexus_db_adapter import create_support_ticket, get_tenant_support_tickets

def render_client_tenant_support_panel(tenant_id: str, tenant_slug: str, org_name: str):
    st.markdown("### 💬 Institutional Support & Inquiry Gateway")
    st.caption("Submit questions, operational inquiries, or compliance notes directly to the Lead Architect / Sovereign Administration.")
    
    tab_new, tab_history = st.tabs(["📝 Submit Inquiry / Complaint", "📋 Communication History & Feedback"])
    
    with tab_new:
        with st.form("tenant_support_form", clear_on_submit=True):
            sender_email = st.text_input("Official Management Email:", placeholder="officer@institution.gov.ng")
            message = st.text_area("Inquiry / Complaint Details:", placeholder="Describe the operational issue or question regarding portal mechanics...")
            submitted = st.form_submit_button("📤 Submit Inquiry to Sovereign Console", use_container_width=True)
            
            if submitted:
                if sender_email.strip() and message.strip():
                    success = create_support_ticket(
                        tenant_id=tenant_id,
                        tenant_slug=tenant_slug,
                        org_name=org_name,
                        sender_email=sender_email.strip(),
                        message=message.strip()
                    )
                    if success:
                        st.success("Inquiry successfully logged! Sovereign Developer Console notified.")
                    else:
                        st.error("Failed to dispatch inquiry. Please retry.")
                else:
                    st.warning("Please provide your official email and message detail.")
                    
    with tab_history:
        tickets = get_tenant_support_tickets(tenant_slug)
        if not tickets:
            st.info("No prior support tickets or inquiries recorded for this institution.")
        else:
            for t in tickets:
                status_badge = "🔴 PENDING REVIEW" if t["status"] == "OPEN" else "🟢 ANSWERED"
                with st.expander(f"[{status_badge}] Inquiry from {t['sender_email']} — {t['created_at']}"):
                    st.markdown(f"**Submitted Question:**\n> {t['message']}")
                    if t["response"]:
                        st.success(f"**Lead Architect / Sovereign CEO Response ({t['responded_at']}):**\n\n{t['response']}")
                    else:
                        st.info("Awaiting response from Lead Architect (Augustine Attah).")

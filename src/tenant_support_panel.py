"""Tenant support inquiries and developer-response history."""

import logging
import sqlite3
from collections.abc import Callable, Mapping
from typing import Any

import streamlit as st

try:
    from src.nexus_db_adapter import (
        create_support_ticket as _create_support_ticket,
        get_tenant_support_tickets as _get_tenant_support_tickets,
    )
except ImportError as exc:
    _create_support_ticket = None
    _get_tenant_support_tickets = None
    _SUPPORT_ADAPTER_IMPORT_ERROR: ImportError | None = exc
else:
    _SUPPORT_ADAPTER_IMPORT_ERROR = None


CreateSupportTicket = Callable[..., bool | tuple[bool, str | None]]
GetSupportTickets = Callable[[str], list[Mapping[str, Any]]]


def render_client_tenant_support_panel(
    tenant_id: str,
    tenant_slug: str,
    org_name: str,
    *,
    create_ticket: CreateSupportTicket | None = None,
    get_tickets: GetSupportTickets | None = None,
) -> None:
    ticket_creator = create_ticket or _create_support_ticket
    ticket_reader = get_tickets or _get_tenant_support_tickets
    if ticket_creator is None or ticket_reader is None:
        detail = (
            f" {_SUPPORT_ADAPTER_IMPORT_ERROR}"
            if _SUPPORT_ADAPTER_IMPORT_ERROR is not None
            else ""
        )
        st.error(f"The support gateway is unavailable.{detail}")
        return

    st.markdown("### Institutional Support & Inquiry Gateway")
    st.caption(
        "Submit questions, operational inquiries, or compliance notes and review "
        "automated guidance or executive responses."
    )
    submit_tab, history_tab = st.tabs(
        ["Submit Inquiry / Complaint", "Communication History & Feedback"]
    )

    with submit_tab:
        with st.container():
            sender_email = st.text_input(
                "Official Management Email",
                placeholder="officer@institution.gov.ng",
                key=f"tenant_support_email_{tenant_slug}",
            )
            message = st.text_area(
                "Inquiry / Complaint Details",
                placeholder="Describe the operational issue or question.",
                key=f"tenant_support_message_{tenant_slug}",
            )
            submitted = st.button(
                "Submit Inquiry to Sovereign Console",
                use_container_width=True,
            )

        if submitted:
            if not sender_email.strip() or not message.strip():
                st.warning("Please provide your official email and inquiry details.")
            else:
                try:
                    result = ticket_creator(
                        tenant_id=tenant_id,
                        tenant_slug=tenant_slug,
                        org_name=org_name,
                        sender_email=sender_email.strip(),
                        message=message.strip(),
                    )
                except (OSError, RuntimeError, sqlite3.Error, TypeError, ValueError):
                    logging.exception(
                        "Could not submit a support inquiry for tenant %s.",
                        tenant_slug,
                    )
                    st.error("The inquiry could not be recorded. Please try again.")
                else:
                    automated_response = None
                    if isinstance(result, tuple) and len(result) == 2:
                        success, automated_response = result
                    else:
                        success = result is True
                    if success:
                        st.success("Your inquiry was recorded for this institution.")
                        if automated_response:
                            st.info(automated_response)
                    else:
                        st.error(
                            "The inquiry could not be recorded. Verify that this "
                            "institution is active and try again."
                        )

    with history_tab:
        try:
            tickets = ticket_reader(tenant_slug)
        except (OSError, RuntimeError, sqlite3.Error, TypeError, ValueError):
            logging.exception(
                "Could not load support history for tenant %s.",
                tenant_slug,
            )
            st.error("Support history is temporarily unavailable.")
            return

        if not tickets:
            st.info("No prior support inquiries are recorded for this institution.")
            return

        for ticket in tickets:
            status = str(ticket.get("status", "")).upper()
            status_badge = "PENDING REVIEW" if status == "OPEN" else "ANSWERED"
            ticket_id = ticket.get("ticket_id", "unknown")
            with st.expander(
                f"[{status_badge}] Inquiry from {ticket.get('sender_email', 'unknown')} "
                f"— {ticket.get('created_at', 'time unavailable')} "
                f"(Reference {ticket_id})"
            ):
                st.markdown(
                    f"**Submitted inquiry:**\n\n> {ticket.get('message', '')}"
                )
                response = ticket.get("response")
                if response:
                    responded_at = ticket.get("responded_at") or "recently"
                    st.success(f"**Response ({responded_at}):**\n\n{response}")
                else:
                    st.info("Awaiting a response from the Sovereign Administration.")

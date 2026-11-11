"""Generate tenant-scoped executive PDF briefings."""

import logging
import sqlite3
from collections.abc import Mapping
from datetime import datetime, timezone
from io import BytesIO

import pandas as pd
import streamlit as st
from fpdf import FPDF

from database import get_connection, init_db


_SEVERITY_RULES = {
    "CRITICAL": ("BREACH", "TAMPER", "UNAUTHORIZED"),
    "HIGH": ("LOGIN_FAILED", "ACCESS_DENIED", "LOCKOUT", "REVOKED"),
    "MEDIUM": ("SESSION_EXPIRED", "DENIED", "FAILED"),
}


def _authorized_report_scope(tenant_slug: str | None) -> str | None:
    if tenant_slug is not None:
        if not isinstance(tenant_slug, str) or not tenant_slug.strip():
            raise ValueError("tenant_slug must be a non-empty string.")
        normalized_slug = tenant_slug.strip().lower()
    else:
        normalized_slug = None

    if st.session_state.get("dev_authenticated") is True:
        return normalized_slug

    if normalized_slug is None:
        raise PermissionError("Only a platform administrator can export global reports.")

    executive_slug = st.session_state.get("tenant_exec_auth_slug")
    if (
        st.session_state.get("tenant_exec_auth") is True
        and isinstance(executive_slug, str)
        and executive_slug.strip().lower() == normalized_slug
    ):
        return normalized_slug

    for key in st.session_state.keys():
        if not isinstance(key, str) or not key.endswith(":identity"):
            continue
        identity = st.session_state.get(key)
        if not isinstance(identity, Mapping):
            continue
        identity_slug = identity.get("tenant_slug")
        role = identity.get("role") or identity.get("user_role")
        if (
            isinstance(identity_slug, str)
            and identity_slug.strip().lower() == normalized_slug
            and role == "executive"
        ):
            return normalized_slug

    raise PermissionError(
        "PDF briefing export requires platform or matching-tenant "
        "executive authentication."
    )


def _audit_severity(action_type: object) -> str:
    normalized_action = str(action_type or "").strip().upper()
    for severity, indicators in _SEVERITY_RULES.items():
        if any(indicator in normalized_action for indicator in indicators):
            return severity
    return "INFO"


def _pdf_text(value: object) -> str:
    text = str(value if value is not None else "")
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _write_table(pdf: FPDF, frame: pd.DataFrame, columns: list[str]) -> None:
    if frame.empty:
        pdf.set_font("Helvetica", size=10)
        pdf.cell(0, 8, "No records for this period.", new_x="LMARGIN", new_y="NEXT")
        return

    column_width = 190 / len(columns)
    pdf.set_font("Helvetica", "B", 9)
    for column in columns:
        pdf.cell(column_width, 7, _pdf_text(column)[:24], border=1)
    pdf.ln()

    pdf.set_font("Helvetica", size=9)
    for row in frame[columns].itertuples(index=False, name=None):
        for value in row:
            pdf.cell(column_width, 7, _pdf_text(value)[:24], border=1)
        pdf.ln()


def generate_executive_pdf_briefing(tenant_slug: str | None = None) -> bytes:
    """
    Create an authorized executive briefing with audit severity and ticket metrics.

    Audit severities are classified from action_type because the tenant audit
    schema does not store a separate severity field.
    """
    report_scope = _authorized_report_scope(tenant_slug)
    scope_clause = " WHERE tenant_slug = ?" if report_scope is not None else ""
    scope_params: tuple[str, ...] = (report_scope,) if report_scope is not None else ()

    init_db()
    with get_connection() as connection:
        audit = pd.read_sql_query(
            """
            SELECT action_type, actor_role, timestamp
            FROM tenant_audit_logs
            """
            + scope_clause
            + " ORDER BY timestamp DESC, log_id DESC LIMIT 1000",
            connection,
            params=scope_params,
        )
        tickets = pd.read_sql_query(
            """
            SELECT status, is_auto_responded, created_at, responded_at
            FROM tenant_support_tickets
            """
            + scope_clause
            + " ORDER BY created_at DESC, ticket_id DESC LIMIT 1000",
            connection,
            params=scope_params,
        )

    if not audit.empty:
        audit["severity"] = audit["action_type"].map(_audit_severity)
        severity_metrics = (
            audit.groupby("severity", as_index=False)
            .size()
            .rename(columns={"size": "event_count"})
            .sort_values("severity")
        )
    else:
        severity_metrics = pd.DataFrame(columns=["severity", "event_count"])

    if not tickets.empty:
        ticket_metrics = (
            tickets.groupby("status", dropna=False, as_index=False)
            .size()
            .rename(columns={"size": "ticket_count"})
            .sort_values("status")
        )
    else:
        ticket_metrics = pd.DataFrame(columns=["status", "ticket_count"])

    pdf = FPDF()
    pdf.set_title("NexusVault Executive PDF Briefing")
    pdf.set_author("NexusVault Digital Technologies")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(
        0,
        12,
        _pdf_text("NexusVault Executive PDF Briefing"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", size=10)
    scope_label = report_scope or "Global platform"
    pdf.cell(
        0,
        7,
        _pdf_text(f"Tenant scope: {scope_label}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        7,
        _pdf_text(
            "Generated: "
            + datetime.now(timezone.utc).isoformat(timespec="seconds")
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, "Security Audit Severity Summary", new_x="LMARGIN", new_y="NEXT")
    _write_table(pdf, severity_metrics, ["severity", "event_count"])

    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, "Support Ticket Status Summary", new_x="LMARGIN", new_y="NEXT")
    _write_table(pdf, ticket_metrics, ["status", "ticket_count"])

    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, "Recent Security Audit Actions", new_x="LMARGIN", new_y="NEXT")
    audit_detail = audit.head(50)[["severity", "action_type", "actor_role", "timestamp"]]
    _write_table(
        pdf,
        audit_detail,
        ["severity", "action_type", "actor_role", "timestamp"],
    )

    output = BytesIO()
    output.write(pdf.output())
    return output.getvalue()


def render_pdf_export_widget(tenant_slug: str | None = None) -> None:
    """Render a download widget for an authorized global or tenant report."""
    try:
        report_scope = _authorized_report_scope(tenant_slug)
    except (PermissionError, ValueError) as exc:
        st.error(str(exc))
        return

    st.markdown("### Executive PDF Briefing")
    st.markdown(
        "Compile audit severity and support ticket status metrics for the "
        "authorized report scope."
    )

    button_scope = report_scope or "global"
    if st.button(
        "Compile Executive PDF Briefing",
        type="primary",
        key=f"btn_export_pdf_{button_scope}",
    ):
        try:
            pdf_data = generate_executive_pdf_briefing(report_scope)
        except (
            ImportError,
            OSError,
            PermissionError,
            RuntimeError,
            sqlite3.Error,
            ValueError,
        ) as exc:
            logging.exception(
                "Could not generate an executive PDF briefing for scope %s.",
                button_scope,
            )
            st.error(f"Failed to generate PDF briefing: {exc}")
            return

        st.download_button(
            label="Download Executive PDF Briefing",
            data=pdf_data,
            file_name=f"NexusVault_Executive_Briefing_{button_scope}.pdf",
            mime="application/pdf",
            key=f"download_export_pdf_{button_scope}",
        )
        st.success("Executive PDF briefing compiled successfully.")

"""
NexusVault Enterprise Report Exporter Module
Compiles tenant configuration, security audit, and support metadata
into structured Excel workbooks for executive review.
"""

import io
import logging
import sqlite3
from collections.abc import Mapping

import pandas as pd
import streamlit as st

from database import get_connection, init_db


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
        "Executive report export requires platform or matching-tenant "
        "executive authentication."
    )


def generate_executive_excel_report(tenant_slug: str | None = None) -> bytes:
    """
    Compile a multi-sheet workbook from configuration, audit, and ticket metadata.

    Platform administrators may request global or tenant-scoped reports.
    Tenant executives may export only their own tenant's report.
    """
    report_scope = _authorized_report_scope(tenant_slug)
    output = io.BytesIO()
    scope_clause = " WHERE tenant_slug = ?" if report_scope is not None else ""
    scope_params: tuple[str, ...] = (report_scope,) if report_scope is not None else ()

    init_db()
    with get_connection() as connection:
        df_configs = pd.read_sql_query(
            """
            SELECT tenant_slug, service_head, fee_amount_minor, currency,
                   payment_mode, payment_reference_prefix, updated_at, updated_by
            FROM tenant_gateway_configs
            """
            + scope_clause
            + " ORDER BY tenant_slug",
            connection,
            params=scope_params,
        )
        df_audit = pd.read_sql_query(
            """
            SELECT log_id, tenant_slug, actor_role, action_type, timestamp
            FROM tenant_audit_logs
            """
            + scope_clause
            + " ORDER BY timestamp DESC, log_id DESC LIMIT 500",
            connection,
            params=scope_params,
        )
        df_support = pd.read_sql_query(
            """
            SELECT ticket_id, tenant_slug, status, is_auto_responded,
                   created_at, responded_at
            FROM tenant_support_tickets
            """
            + scope_clause
            + " ORDER BY created_at DESC, ticket_id DESC LIMIT 1000",
            connection,
            params=scope_params,
        )

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_configs.to_excel(writer, sheet_name="Tenant Configurations", index=False)
        df_audit.to_excel(writer, sheet_name="Security Audit Logs", index=False)
        df_support.to_excel(writer, sheet_name="Support Tickets", index=False)

    output.seek(0)
    return output.getvalue()


def render_report_export_widget(tenant_slug: str | None = None) -> None:
    """Render a download control restricted to an authorized report scope."""
    try:
        report_scope = _authorized_report_scope(tenant_slug)
    except (PermissionError, ValueError) as exc:
        st.error(str(exc))
        return

    st.markdown("### Executive Report & Audit Exporter")
    st.markdown(
        "Generate a multi-sheet Excel workbook containing tenant configuration, "
        "security audit metadata, and support ticket status."
    )

    button_scope = report_scope or "global"
    if st.button(
        "Compile & Download Executive Report (.xlsx)",
        type="primary",
        key=f"btn_export_excel_{button_scope}",
    ):
        try:
            excel_data = generate_executive_excel_report(report_scope)
        except (
            ImportError,
            OSError,
            PermissionError,
            RuntimeError,
            sqlite3.Error,
            ValueError,
        ) as exc:
            logging.exception(
                "Could not generate an executive report for scope %s.",
                button_scope,
            )
            st.error(f"Failed to generate report workbook: {exc}")
            return

        st.download_button(
            label="Download Excel Report",
            data=excel_data,
            file_name=f"NexusVault_Executive_Report_{button_scope}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"download_export_excel_{button_scope}",
        )
        st.success("Executive workbook compiled successfully.")

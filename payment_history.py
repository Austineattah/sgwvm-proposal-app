"""
payment_history.py
------------------
Append-only, multi-tenant Payment History registry and UI renderer.
Designed with a portable SQL adapter (SQLite fallback -> temporal Supabase Postgres ->
Galaxy Backbone sovereign PostgreSQL) so zero UI or query changes are required on migration.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:  # pragma: no cover
    psycopg2 = None
    RealDictCursor = None


WAT_TZ = timezone(timedelta(hours=1), name="WAT")
DEFAULT_SQLITE_PATH = Path("data") / "payment_history.db"
VALID_STATUSES = ("Success", "Unsuccessful", "Pending", "Refunded")


def _resolve_postgres_dsn() -> str:
    """Return normalized PostgreSQL DSN if configured for Supabase or Galaxy Backbone."""
    for env_key in ("PAYMENT_DB_URL", "SUPABASE_DB_URL", "DATABASE_URL"):
        raw = str(os.getenv(env_key) or "").strip()
        if raw.startswith("postgres://"):
            return raw.replace("postgres://", "postgresql://", 1)
        if raw.startswith("postgresql+psycopg2://"):
            return raw.replace("postgresql+psycopg2://", "postgresql://", 1)
        if raw.startswith("postgresql://"):
            return raw
    return ""


def _use_postgres() -> bool:
    return bool(_resolve_postgres_dsn() and psycopg2 is not None)


def _sqlite_path() -> Path:
    custom = str(os.getenv("PAYMENT_SQLITE_PATH") or "").strip()
    path = Path(custom) if custom else DEFAULT_SQLITE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect():
    if _use_postgres():
        return psycopg2.connect(_resolve_postgres_dsn(), cursor_factory=RealDictCursor)
    conn = sqlite3.connect(str(_sqlite_path()))
    conn.row_factory = sqlite3.Row
    return conn


def init_payment_history_store() -> None:
    """Create the append-only payment_history ledger table and indexes if absent."""
    ddl_table = """
    CREATE TABLE IF NOT EXISTS payment_history (
        payment_id VARCHAR(64) PRIMARY KEY,
        transaction_ref VARCHAR(128) UNIQUE NOT NULL,
        org_id VARCHAR(128) NOT NULL,
        organization_name VARCHAR(255) NOT NULL,
        payment_date VARCHAR(16) NOT NULL,
        payment_time VARCHAR(24) NOT NULL,
        created_at_utc VARCHAR(40) NOT NULL,
        amount NUMERIC(14, 2) NOT NULL,
        currency VARCHAR(12) NOT NULL DEFAULT 'NGN',
        status VARCHAR(32) NOT NULL,
        payment_method VARCHAR(64) NOT NULL DEFAULT 'Bank Transfer',
        plan_or_purpose VARCHAR(255) NOT NULL DEFAULT 'Subscription Activation',
        failure_reason TEXT NOT NULL DEFAULT '',
        recorded_by VARCHAR(128) NOT NULL DEFAULT 'system'
    );
    """
    ddl_idx_org = "CREATE INDEX IF NOT EXISTS idx_payment_history_org_id ON payment_history (org_id);"
    ddl_idx_date = "CREATE INDEX IF NOT EXISTS idx_payment_history_date ON payment_history (payment_date);"

    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(ddl_table)
        cur.execute(ddl_idx_org)
        cur.execute(ddl_idx_date)
        conn.commit()


def _normalize_amount(amount: Any) -> str:
    try:
        dec = Decimal(str(amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid payment amount: {amount!r}") from exc
    if dec < Decimal("0.00"):
        raise ValueError("Payment amount cannot be negative.")
    return f"{dec:.2f}"


def record_payment_event(
    *,
    org_id: str,
    organization_name: str,
    amount: Any,
    status: str,
    currency: str = "NGN",
    payment_method: str = "Bank Transfer",
    plan_or_purpose: str = "Subscription Activation",
    transaction_ref: Optional[str] = None,
    failure_reason: str = "",
    recorded_by: str = "system",
    occurred_at_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Append an immutable payment attempt record (idempotent on transaction_ref)."""
    init_payment_history_store()

    clean_org_id = str(org_id or "").strip()
    clean_org_name = str(organization_name or "").strip()
    if not clean_org_id or not clean_org_name:
        raise ValueError("org_id and organization_name are required.")

    clean_status = str(status or "").strip().title()
    if clean_status not in VALID_STATUSES:
        raise ValueError(f"status must be one of {VALID_STATUSES}, got {status!r}")

    norm_amount = _normalize_amount(amount)
    clean_currency = str(currency or "NGN").strip().upper()[:12]

    ts_utc = occurred_at_utc or datetime.now(timezone.utc)
    if ts_utc.tzinfo is None:
        ts_utc = ts_utc.replace(tzinfo=timezone.utc)
    ts_wat = ts_utc.astimezone(WAT_TZ)

    payment_id = f"PAY-{ts_utc.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    tx_ref = (
        str(transaction_ref).strip()
        if transaction_ref and str(transaction_ref).strip()
        else f"TXN-{ts_utc.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    )

    record = {
        "payment_id": payment_id,
        "transaction_ref": tx_ref,
        "org_id": clean_org_id,
        "organization_name": clean_org_name,
        "payment_date": ts_wat.strftime("%Y-%m-%d"),
        "payment_time": ts_wat.strftime("%H:%M:%S WAT"),
        "created_at_utc": ts_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "amount": norm_amount,
        "currency": clean_currency,
        "status": clean_status,
        "payment_method": str(payment_method or "Bank Transfer").strip()[:64],
        "plan_or_purpose": str(plan_or_purpose or "Subscription Activation").strip()[:255],
        "failure_reason": "" if clean_status == "Success" else str(failure_reason or "").strip(),
        "recorded_by": str(recorded_by or "system").strip()[:128],
    }

    placeholder = "%s" if _use_postgres() else "?"
    cols = list(record.keys())
    placeholders = ", ".join([placeholder] * len(cols))
    col_list = ", ".join(cols)

    if _use_postgres():
        sql = f"""
        INSERT INTO payment_history ({col_list})
        VALUES ({placeholders})
        ON CONFLICT (transaction_ref) DO NOTHING;
        """
    else:
        sql = f"""
        INSERT OR IGNORE INTO payment_history ({col_list})
        VALUES ({placeholders});
        """

    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(sql, [record[c] for c in cols])
        conn.commit()

    return record


def fetch_payment_history(
    *,
    org_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """Fetch payment history rows ordered newest-first, enforcing org_id when provided."""
    init_payment_history_store()
    placeholder = "%s" if _use_postgres() else "?"

    clauses: List[str] = []
    params: List[Any] = []

    if org_id:
        clauses.append(f"org_id = {placeholder}")
        params.append(str(org_id).strip())
    if status_filter and status_filter != "All":
        clauses.append(f"status = {placeholder}")
        params.append(status_filter)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
    SELECT
        payment_id,
        transaction_ref,
        org_id,
        organization_name,
        payment_date,
        payment_time,
        created_at_utc,
        amount,
        currency,
        status,
        payment_method,
        plan_or_purpose,
        failure_reason,
        recorded_by
    FROM payment_history
    {where_sql}
    ORDER BY created_at_utc DESC
    LIMIT {int(limit)};
    """

    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()

    results: List[Dict[str, Any]] = []
    for r in rows:
        item = dict(r)
        item["amount"] = float(Decimal(str(item["amount"])))
        results.append(item)
    return results


def storage_backend_label() -> str:
    if _use_postgres():
        return "PostgreSQL (Temporal Cloud / Galaxy Backbone Ready)"
    return f"Local SQLite Ledger ({_sqlite_path().as_posix()}) — Galaxy Backbone Portable"


def render_payment_history_tab(
    *,
    role: str = "tenant",
    org_id: Optional[str] = None,
    organization_name: Optional[str] = None,
    actor: str = "system",
    known_organizations: Optional[List[Dict[str, str]]] = None,
) -> None:
    """
    Render the Payment History tab for either:
      - role='tenant'    : Strictly scoped to the authenticated organization (org_id).
      - role='developer' : Full multi-tenant audit registry with filtering & manual ledger entry.
    """
    is_dev = role == "developer"
    scope_org_id = None if is_dev else str(org_id or "").strip()

    st.subheader("💳 Payment History & Settlement Ledger")
    st.caption(f"Storage Adapter: **{storage_backend_label()}**")

    if not is_dev and not scope_org_id:
        st.warning("Active organization context is required to load tenant payment history.")
        return

    rows = fetch_payment_history(org_id=scope_org_id)
    df = pd.DataFrame(rows)

    # Top KPI Summary Strip
    c1, c2, c3, c4 = st.columns(4)
    if df.empty:
        c1.metric("Total Transactions", 0)
        c2.metric("Successful", 0)
        c3.metric("Unsuccessful", 0)
        c4.metric("Settled Volume (NGN)", "₦0.00")
    else:
        success_df = df[df["status"] == "Success"]
        unsuccessful_df = df[df["status"] == "Unsuccessful"]
        ngn_settled = success_df[success_df["currency"] == "NGN"]["amount"].sum()
        c1.metric("Total Transactions", int(len(df)))
        c2.metric("Successful", int(len(success_df)))
        c3.metric("Unsuccessful", int(len(unsuccessful_df)))
        c4.metric("Settled Volume (NGN)", f"₦{ngn_settled:,.2f}")

    # Filter Bar
    f_cols = st.columns([1.2, 1.5, 1.3] if is_dev else [1.2, 1.8])
    key_prefix = f"pay_hist_{role}_{scope_org_id or 'all'}"
    status_choice = f_cols[0].selectbox(
        "Status",
        options=["All", "Success", "Unsuccessful", "Pending", "Refunded"],
        key=f"{key_prefix}_status",
    )
    search_query = f_cols[1].text_input(
        "Search Reference / Organization / Purpose",
        placeholder="e.g. TXN-2026 or Ministry of...",
        key=f"{key_prefix}_search",
    ).strip().lower()

    selected_org_filter = "All Organizations"
    if is_dev:
        org_options = ["All Organizations"]
        if not df.empty:
            org_options.extend(sorted(df["organization_name"].dropna().unique().tolist()))
        selected_org_filter = f_cols[2].selectbox(
            "Organization",
            options=org_options,
            key=f"{key_prefix}_org",
        )

    if not df.empty:
        filtered = df.copy()
        if status_choice != "All":
            filtered = filtered[filtered["status"] == status_choice]
        if is_dev and selected_org_filter != "All Organizations":
            filtered = filtered[filtered["organization_name"] == selected_org_filter]
        if search_query:
            mask = (
                filtered["transaction_ref"].str.lower().str.contains(search_query, na=False)
                | filtered["organization_name"].str.lower().str.contains(search_query, na=False)
                | filtered["plan_or_purpose"].str.lower().str.contains(search_query, na=False)
                | filtered["payment_id"].str.lower().str.contains(search_query, na=False)
            )
            filtered = filtered[mask]

        if filtered.empty:
            st.info("No payment transactions match the selected filters.")
        else:
            display_df = pd.DataFrame(
                {
                    "Date": filtered["payment_date"],
                    "Time": filtered["payment_time"],
                    "Organization": filtered["organization_name"],
                    "Amount": filtered.apply(
                        lambda r: f"{r['currency']} {r['amount']:,.2f}", axis=1
                    ),
                    "Status": filtered["status"].apply(
                        lambda s: "✅ Success"
                        if s == "Success"
                        else ("❌ Unsuccessful" if s == "Unsuccessful" else f"⏳ {s}")
                    ),
                    "Channel": filtered["payment_method"],
                    "Purpose / Tier": filtered["plan_or_purpose"],
                    "Transaction Ref": filtered["transaction_ref"],
                    "Failure / Audit Note": filtered["failure_reason"],
                }
            )
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            csv_bytes = filtered.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Export Audit Ledger (CSV)",
                data=csv_bytes,
                file_name=f"payment_history_{scope_org_id or 'all_tenants'}.csv",
                mime="text/csv",
                key=f"{key_prefix}_export_csv",
            )
    else:
        st.info("No payment history records have been logged yet.")

    # Developer-only manual / reconciliation ledger recorder
    if is_dev:
        with st.expander("➕ Record / Reconcile Payment Entry (Developer Ledger)", expanded=False):
            with st.form(key=f"{key_prefix}_record_form", clear_on_submit=True):
                r1, r2 = st.columns(2)
                if known_organizations:
                    org_map = {
                        f"{o['organization_name']} ({o['org_id']})": o
                        for o in known_organizations
                        if o.get("org_id") and o.get("organization_name")
                    }
                else:
                    org_map = {}

                if org_map:
                    picked_label = r1.selectbox(
                        "Select Registered Organization",
                        options=["-- Custom / Manual Entry --"] + list(org_map.keys()),
                    )
                else:
                    picked_label = "-- Custom / Manual Entry --"

                manual_org_id = r1.text_input(
                    "Organization Slug / ID",
                    value=org_map[picked_label]["org_id"] if picked_label in org_map else "",
                    placeholder="e.g. fed-min-works",
                )
                manual_org_name = r2.text_input(
                    "Organization Name",
                    value=org_map[picked_label]["organization_name"] if picked_label in org_map else "",
                    placeholder="e.g. Federal Ministry of Works",
                )

                r3, r4, r5 = st.columns(3)
                manual_amount = r3.number_input("Amount", min_value=0.0, value=250000.0, step=1000.0)
                manual_currency = r4.selectbox("Currency", options=["NGN", "USD", "GBP", "EUR"])
                manual_status = r5.selectbox("Payment Status", options=["Success", "Unsuccessful", "Pending", "Refunded"])

                r6, r7 = st.columns(2)
                manual_method = r6.selectbox(
                    "Payment Channel",
                    options=["Remita TSA", "Corporate Bank Transfer", "Card Gateway", "USSD", "Enterprise Invoice"],
                )
                manual_purpose = r7.text_input(
                    "Subscription Tier / Purpose",
                    value="Enterprise Onboarding & Annual License",
                )
                manual_ref = st.text_input(
                    "Gateway / RRR Reference (optional — auto-generated if blank)",
                    placeholder="e.g. RRR-3409-8821-0019",
                )
                manual_note = st.text_input(
                    "Failure Reason (required if Unsuccessful)",
                    placeholder="e.g. Issuer timeout / Insufficient balance",
                )

                submitted = st.form_submit_button("Append to Payment Ledger", type="primary")
                if submitted:
                    try:
                        created = record_payment_event(
                            org_id=manual_org_id,
                            organization_name=manual_org_name,
                            amount=manual_amount,
                            status=manual_status,
                            currency=manual_currency,
                            payment_method=manual_method,
                            plan_or_purpose=manual_purpose,
                            transaction_ref=manual_ref or None,
                            failure_reason=manual_note,
                            recorded_by=actor or "developer_master",
                        )
                        st.success(
                            f"Recorded {created['status']} transaction `{created['transaction_ref']}` "
                            f"for {created['organization_name']} ({created['currency']} {float(created['amount']):,.2f})."
                        )
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import html
from typing import Any

from src.nexus_tenant_engine import NexusTenantLifecycleEngine, TenantStatus

ONE_OFF_SETUP_ITEMS: list[tuple[str, str, int]] = [
    (
        "Tenant Provisioning & RLS",
        "Database schema isolation (tenant_id), RLS security, Galaxy Backbone node.",
        15_000_000,
    ),
    (
        "Agentic AI Configuration Tuning",
        "LLM document parsing engine for client formats & scoring grids.",
        10_000_000,
    ),
    (
        "Gateway Integration",
        "Remita TSA / commercial bank automated settlement API verification.",
        5_000_000,
    ),
    (
        "Staff Onboarding",
        "Training for desk officers, evaluators, and executive oversight directors.",
        5_000_000,
    ),
]
ONE_OFF_SETUP_TOTAL_NGN: int = 35_000_000

SAAS_TIERS: dict[str, dict[str, Any]] = {
    "Tier 1: Apex Federal": {
        "annual_fee": 65_000_000,
        "partitioning": "Unlimited Directorates",
        "monthly_submissions": "Unlimited",
        "ai_engine": "Advanced Multi-Doc Parsing",
        "sla": "99.9% Uptime (24/7 Priority)",
    },
    "Tier 2: Major Parastatal": {
        "annual_fee": 35_000_000,
        "partitioning": "Up to 10 Departments",
        "monthly_submissions": "Up to 10,000 / month",
        "ai_engine": "Standard Summarization",
        "sla": "99.5% Uptime (Business Hrs)",
    },
    "Tier 3: Enterprise / NGO": {
        "annual_fee": 20_000_000,
        "partitioning": "Single Organization",
        "monthly_submissions": "Up to 2,500 / month",
        "ai_engine": "Standard Summarization",
        "sla": "99.0% Uptime",
    },
}

TRANSACTION_SPLIT_MATRIX: list[tuple[str, str, str, str]] = [
    ("High-Value Procurement / Tenders", "₦25,000 – ₦100,000 / file", "80% (Direct TSA)", "20% (Tech Share)"),
    ("Standard Applications / Permits", "₦10,000 – ₦25,000 / file", "85% (Direct TSA)", "15% (Tech Share)"),
    ("Grant & NGO Applications", "₦5,000 – ₦15,000 / file", "75% (Client Ops)", "25% (Tech Share)"),
]


def _format_ngn(amount: int) -> str:
    return f"₦{amount:,.0f}"


def _resolve_default_tier_index(sub_package: str) -> int:
    normalized = (sub_package or "").strip().lower()
    tier_names = list(SAAS_TIERS.keys())
    if "apex" in normalized or "federal" in normalized:
        return 0
    if "parastatal" in normalized or "major" in normalized or "pro" in normalized:
        return 1
    if "enterprise" in normalized or "ngo" in normalized or "starter" in normalized:
        return 2
    return 0 if not tier_names else 1


def _build_proforma_invoice_text(
    *,
    invoice_ref: str,
    org_name: str,
    tenant_id: str,
    slug: str,
    admin_email: str,
    selected_tier: str,
    tier_fee: int,
    deployment_option: str,
    total_due_today: int,
) -> str:
    issued_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    setup_lines = "\n".join(
        f"  - {comp}: {_format_ngn(fee)} ({scope})"
        for comp, scope, fee in ONE_OFF_SETUP_ITEMS
    )
    return (
        "====================================================================\n"
        "NEXUSVAULT SOVEREIGN INTELLIGENCE — COMMERCIAL PROFORMA INVOICE\n"
        "Issued by: NexusVault Digital Technology Limited\n"
        "Address: Plot 119, First Avenue Efab Estate Lokogoma, Abuja\n"
        "====================================================================\n"
        f"Invoice Reference : {invoice_ref}\n"
        f"Issue Timestamp   : {issued_at}\n"
        f"Organization      : {org_name}\n"
        f"Tenant ID         : {tenant_id}\n"
        f"Workspace Slug    : {slug}\n"
        f"Admin Contact     : {admin_email}\n"
        "--------------------------------------------------------------------\n"
        "1. SYSTEM INTEGRATION & ONE-OFF SETUP PACKAGE\n"
        f"{setup_lines}\n"
        f"   Subtotal One-Off Setup Package: {_format_ngn(ONE_OFF_SETUP_TOTAL_NGN)}\n\n"
        "2. SELECTED ANNUAL SAAS LICENSING TIER\n"
        f"   Selected Tier : {selected_tier}\n"
        f"   Annual Fee    : {_format_ngn(tier_fee)} / year\n\n"
        "3. SELECTED COMMERCIAL DEPLOYMENT MODEL\n"
        f"   Model         : {deployment_option}\n"
        f"   IMMEDIATE SETTLEMENT DUE TODAY: {_format_ngn(total_due_today)}\n"
        "--------------------------------------------------------------------\n"
        "CORPORATE SETTLEMENT INSTRUCTIONS (EXCLUSIVE INSTITUTIONAL GATEWAY)\n"
        "  Beneficiary Name : NexusVault Digital Technology Limited (NexusVault Escrow)\n"
        "  Settlement Mode  : Corporate Wire / NIP Institutional Transfer\n"
        "  Mandatory Narration: "
        f"{invoice_ref} | {slug}\n"
        "====================================================================\n"
    )


def render_tenant_checkout(
    tenant: Mapping[str, Any],
    engine: NexusTenantLifecycleEngine,
) -> None:
    import streamlit as st

    tenant_id = str(tenant.get("tenant_id") or "").strip()
    if not tenant_id:
        st.error("Unable to initialize commercial gateway: missing tenant identifier.")
        return

    org_name = str(tenant.get("org_name") or "Registered Organization").strip()
    slug = str(tenant.get("slug") or "workspace").strip()
    admin_email = str(tenant.get("admin_email") or "admin@organization.gov.ng").strip()
    raw_status = tenant.get("status", TenantStatus.PAYMENT_PENDING)
    status_label = raw_status.value if isinstance(raw_status, TenantStatus) else str(raw_status)
    invoice_ref = f"NV-INV-{slug.upper()}-{tenant_id[:8].upper()}"
    st.session_state["checkout_invoice_ref"] = invoice_ref

    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#071324 0%,#0E243D 100%);
                    border:1px solid #38BDF8;border-radius:14px;padding:1.35rem 1.5rem;
                    margin-bottom:1.25rem;color:#F8FAFC;">
            <div style="font-size:0.74rem;letter-spacing:0.14em;font-weight:800;color:#38BDF8;text-transform:uppercase;">
                NEXUSVAULT COMMERCIAL SUBSCRIPTION &amp; DEPLOYMENT GATEWAY
            </div>
            <div style="font-size:1.35rem;font-weight:800;margin:0.35rem 0;">
                {html.escape(org_name)} — Institutional Licensing &amp; Settlement
            </div>
            <div style="font-size:0.86rem;color:#CBD5E1;">
                <strong>Tenant ID:</strong> <code>{html.escape(tenant_id)}</code> &nbsp;|&nbsp;
                <strong>Workspace Slug:</strong> <code>{html.escape(slug)}</code> &nbsp;|&nbsp;
                <strong>Lifecycle State:</strong> <code>{html.escape(status_label)}</code>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. SYSTEM INTEGRATION & ONE-OFF SETUP FEES
    st.markdown("### 1. System Integration & One-Off Setup Fees")
    setup_rows = [
        {
            "Deployment Component": comp,
            "Scope & Operational Deliverables": scope,
            "Fee (NGN)": _format_ngn(fee),
        }
        for comp, scope, fee in ONE_OFF_SETUP_ITEMS
    ]
    setup_rows.append(
        {
            "Deployment Component": "TOTAL ONE-OFF SETUP PACKAGE",
            "Scope & Operational Deliverables": "Complete Enterprise Infrastructure & Provisioning",
            "Fee (NGN)": _format_ngn(ONE_OFF_SETUP_TOTAL_NGN),
        }
    )
    st.table(setup_rows)

    # 2. ANNUAL RECURRING SUBSCRIPTION TIERS (SAAS LICENSING)
    st.markdown("### 2. Annual Recurring Subscription Tiers (SaaS Licensing)")
    tier_rows = [
        {
            "Subscription Tier": name,
            "Annual Platform Fee": f"{_format_ngn(meta['annual_fee'])} / year",
            "Tenant Partitioning": meta["partitioning"],
            "Monthly Submissions": meta["monthly_submissions"],
            "AI Document Engine": meta["ai_engine"],
            "SLA & Support": meta["sla"],
        }
        for name, meta in SAAS_TIERS.items()
    ]
    st.table(tier_rows)

    tier_options = list(SAAS_TIERS.keys())
    default_idx = _resolve_default_tier_index(str(tenant.get("sub_package") or ""))
    selected_tier = st.radio(
        "Select Institutional SaaS Subscription Tier:",
        options=tier_options,
        index=default_idx,
        key="checkout_selected_tier",
    )
    selected_tier_fee = int(SAAS_TIERS[selected_tier]["annual_fee"])

    # 3. AUTOMATED REMITA TSA TRANSACTION FEE SPLIT MATRIX
    st.markdown("### 3. Automated Transaction Fee Split Matrix (Reference Schedule)")
    st.caption(
        "Statutory submission fees settle automatically at gateway split: Client portion sweeps directly to Client/TSA, "
        "while NexusVault technology commission routes to NexusVault corporate settlement."
    )
    split_rows = [
        {
            "Submission Category": cat,
            "Statutory Fee Range": fee_range,
            "Client Share": client_share,
            "NexusVault Share": nv_share,
        }
        for cat, fee_range, client_share, nv_share in TRANSACTION_SPLIT_MATRIX
    ]
    st.table(split_rows)

    # 4. COMMERCIAL DEPLOYMENT OPTIONS
    st.markdown("### 4. Commercial Deployment Options")
    option_a_label = (
        "Option A (CapEx Enterprise): 100% upfront setup (₦35,000,000) & annual SaaS license. "
        "Client retains 100% of statutory fees, paying NexusVault a flat ₦500 per transaction fee."
    )
    option_b_label = (
        "Option B (Zero-Upfront OpEx Revenue Share): Setup & SaaS fees waived/amortized over 24 months (₦0 upfront). "
        "NexusVault receives a 25% transaction split on incoming vendor/applicant submissions."
    )
    deployment_option = st.radio(
        "Choose Commercial Deployment Model:",
        options=[option_a_label, option_b_label],
        key="checkout_deployment_option",
    )
    is_capex = deployment_option.startswith("Option A")
    total_due_today = (ONE_OFF_SETUP_TOTAL_NGN + selected_tier_fee) if is_capex else 0

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("One-Off Setup Package", _format_ngn(ONE_OFF_SETUP_TOTAL_NGN if is_capex else 0))
    col_m2.metric("Annual SaaS License", _format_ngn(selected_tier_fee if is_capex else 0))
    col_m3.metric("Total Upfront Due Today", _format_ngn(total_due_today))

    invoice_text = _build_proforma_invoice_text(
        invoice_ref=invoice_ref,
        org_name=org_name,
        tenant_id=tenant_id,
        slug=slug,
        admin_email=admin_email,
        selected_tier=selected_tier,
        tier_fee=selected_tier_fee,
        deployment_option="Option A (CapEx Enterprise)" if is_capex else "Option B (Zero-Upfront OpEx Revenue Share)",
        total_due_today=total_due_today,
    )
    st.download_button(
        label="Download Commercial Proforma Invoice (.txt)",
        data=invoice_text.encode("utf-8"),
        file_name=f"{invoice_ref}.txt",
        mime="text/plain",
        key=f"dl_proforma_{tenant_id}",
    )

    # 5. EXCLUSIVE ORGANIZATIONAL SETTLEMENT & ACTIVATION
    st.markdown("### 5. Exclusive Organizational Settlement & Workspace Activation")
    tab_wire, tab_po = st.tabs(
        [
            "Corporate Wire / NIP Bank Settlement",
            "Sovereign Purchase Order (PO) / OpEx Mandate",
        ]
    )

    with tab_wire:
        st.info(
            f"**Beneficiary:** NexusVault Digital Technology Limited (NexusVault Institutional Settlement) | "
            f"**Mandatory Payment Narration:** `{invoice_ref}` | "
            f"**Amount Due:** `{_format_ngn(total_due_today)}`"
        )
        wire_bank = st.text_input(
            "Remitting Commercial Bank Name *",
            placeholder="e.g., Zenith Bank / FirstBank / GTBank / CBN TSA",
            key=f"wire_bank_{tenant_id}",
        )
        wire_ref = st.text_input(
            "NIP / Corporate Wire Transaction Reference *",
            placeholder="e.g., NIP-2026-88492019",
            key=f"wire_ref_{tenant_id}",
        )
        wire_proof = st.file_uploader(
            "Upload Bank Wire Advice / Teller Receipt (PDF, PNG, JPG) *",
            type=["pdf", "png", "jpg", "jpeg"],
            key=f"wire_proof_{tenant_id}",
        )
        if st.button(
            "Submit Wire Settlement & Activate Workspace",
            type="primary",
            key=f"btn_submit_wire_{tenant_id}",
        ):
            if not wire_bank.strip() or not wire_ref.strip() or wire_proof is None:
                st.warning(
                    "Please enter the remitting bank name, wire transaction reference, and upload the settlement receipt."
                )
            else:
                try:
                    updated = engine.confirm_payment(tenant_id)
                    st.session_state["checkout_settlement_receipt"] = {
                        "mode": "CORPORATE_WIRE",
                        "invoice_ref": invoice_ref,
                        "bank": wire_bank.strip(),
                        "reference": wire_ref.strip(),
                        "filename": wire_proof.name,
                        "tier": selected_tier,
                        "deployment": "CapEx" if is_capex else "OpEx",
                        "amount_ngn": total_due_today,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    st.session_state["show_tenant_checkout"] = False
                    st.success(
                        f"Settlement verified for {updated.get('org_name', org_name)}. "
                        "Workspace status is now SUBSCRIBED."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"Workspace activation error: {exc}")

    with tab_po:
        st.info(
            "Use this channel to execute a **Zero-Upfront OpEx Revenue Share Mandate (Option B)** "
            "or lodge an approved **Sovereign Purchase Order (PO)** for CapEx treasury clearance."
        )
        signatory_name = st.text_input(
            "Authorized Executive Signatory Name & Title *",
            placeholder="e.g., Dr. A. B. Chukwu — Director of Procurement / Permanent Secretary",
            key=f"po_signatory_{tenant_id}",
        )
        po_reference = st.text_input(
            "Purchase Order / Mandate Reference Number *",
            placeholder="e.g., PO/NV/2026/0041",
            key=f"po_ref_{tenant_id}",
        )
        po_document = st.file_uploader(
            "Upload Signed Purchase Order or OpEx Revenue-Share Mandate (PDF, PNG, JPG) *",
            type=["pdf", "png", "jpg", "jpeg"],
            key=f"po_doc_{tenant_id}",
        )
        if st.button(
            "Execute OpEx Mandate / Submit Purchase Order",
            type="primary",
            key=f"btn_submit_po_{tenant_id}",
        ):
            if not signatory_name.strip() or not po_reference.strip() or po_document is None:
                st.warning(
                    "Please provide the authorized signatory, PO/Mandate reference number, and upload the signed document."
                )
            elif not is_capex:
                try:
                    updated = engine.confirm_payment(tenant_id)
                    st.session_state["checkout_settlement_receipt"] = {
                        "mode": "OPEX_MANDATE",
                        "invoice_ref": invoice_ref,
                        "signatory": signatory_name.strip(),
                        "reference": po_reference.strip(),
                        "filename": po_document.name,
                        "tier": selected_tier,
                        "deployment": "OpEx (24-Month Amortization / 25% Split)",
                        "amount_ngn": 0,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    st.session_state["show_tenant_checkout"] = False
                    st.success(
                        f"OpEx Revenue-Share Mandate accepted for {updated.get('org_name', org_name)}. "
                        "Workspace is now SUBSCRIBED and active."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"OpEx mandate activation error: {exc}")
            else:
                st.session_state["checkout_settlement_receipt"] = {
                    "mode": "CAPEX_PO_LODGED",
                    "invoice_ref": invoice_ref,
                    "signatory": signatory_name.strip(),
                    "reference": po_reference.strip(),
                    "filename": po_document.name,
                    "tier": selected_tier,
                    "deployment": "CapEx (Awaiting Treasury Wire)",
                    "amount_ngn": total_due_today,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                st.warning(
                    f"Purchase Order `{po_reference.strip()}` lodged under `PAYMENT_PENDING — AWAITING TREASURY WIRE CLEARANCE`. "
                    "Once treasury completes the wire transfer, upload the wire advice in the first tab for instant activation."
                )

    st.markdown("---")
    if st.button("Back to Tenant Status Overview", key=f"btn_back_overview_{tenant_id}"):
        st.session_state["show_tenant_checkout"] = False
        st.rerun()

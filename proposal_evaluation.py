import re
from datetime import date
from typing import Any

from bid_pricing_ingestion import BoQLineItem, evaluate_boq_pricing
from ownership_conflict import BidOwnershipRecord, detect_ownership_conflicts
from statutory_compliance import (
    StatutoryItemInput,
    build_kyb_statutory_seed,
    evaluate_statutory_matrix,
)

_BUDGET_LABEL = re.compile(
    r"^\s*(?:(?:estimated|proposed|project)\s+)*"
    r"(?:budget|cost|price|amount|financial\s+terms)"
    r"\s*[:\-]\s*(.+?)\s*$",
    re.IGNORECASE,
)
_EXPLICIT_AMOUNT = re.compile(
    r"(?:[$₦€£]\s*|\b(?:USD|NGN|GBP|EUR)\s*)"
    r"\d[\d,]*(?:\.\d+)?"
    r"|\d[\d,]*(?:\.\d+)?\s*\b(?:USD|NGN|GBP|EUR)\b",
    re.IGNORECASE,
)
_NON_BUDGET_VALUES = {
    "",
    "n/a",
    "na",
    "none",
    "not provided",
    "not specified",
    "to be determined",
}
NO_BUDGET_MESSAGE = "No explicit budget found in document"


def extract_budget_evidence(document_text: str | None) -> str:
    """Return the first labeled budget or financial note found in extracted text."""
    if not isinstance(document_text, str) or not document_text:
        return ""
    for line in document_text.splitlines():
        match = _BUDGET_LABEL.search(line)
        if match and match.group(1).strip():
            return match.group(1).strip()
    return ""


def has_explicit_budget_amount(value: str | None) -> bool:
    """Check for a currency-qualified amount or a number-only labeled amount."""
    if not isinstance(value, str) or not value:
        return False
    return bool(
        _EXPLICIT_AMOUNT.search(value)
        or re.fullmatch(r"\s*\d[\d,]*(?:\.\d+)?\s*", value)
    )


def assess_budget(
    document_text: str,
    model_has_budget: bool | None = None,
    model_budget_display: str = "",
) -> tuple[bool, str, str | None]:
    """Apply document-evidence policy and force Conditional when budget is absent."""
    evidence = extract_budget_evidence(document_text)
    evidence_is_amount = has_explicit_budget_amount(evidence)
    note = "" if evidence.lower() in _NON_BUDGET_VALUES else evidence

    if model_has_budget is None:
        has_budget = evidence_is_amount
        display = evidence if has_budget else note or NO_BUDGET_MESSAGE
    else:
        model_display = model_budget_display.strip()
        model_has_amount = has_explicit_budget_amount(model_display)
        has_budget = model_has_budget and model_has_amount
        if has_budget:
            display = model_display
        elif model_has_amount:
            display = note if note and not evidence_is_amount else NO_BUDGET_MESSAGE
        else:
            display = model_display or note or NO_BUDGET_MESSAGE

    return has_budget, display, None if has_budget else "Conditional"


def is_critical_kyb_result(kyb_data: dict) -> bool:
    """Return true when registry data explicitly indicates inactive status."""
    status = str(kyb_data.get("status", "")).upper()
    company_status = str(kyb_data.get("company_status", "")).upper()
    return (
        kyb_data.get("is_active") is False
        or status == "INACTIVE"
        or company_status == "INACTIVE"
    )


def evaluate_bid_integrity_package(
    *,
    document_text: str = "",
    model_has_budget: bool | None = None,
    model_budget_display: str = "",
    kyb_data: dict[str, Any] | None = None,
    statutory_records: list[StatutoryItemInput | dict[str, Any]] | None = None,
    required_statutory_codes: list[str] | tuple[str, ...] | None = None,
    as_of_date: date | str | None = None,
    expiring_within_days: int = 30,
    competing_bids: list[BidOwnershipRecord | dict[str, Any]] | None = None,
    boq_items: list[BoQLineItem | dict[str, Any]] | None = None,
    stated_subtotal: float | None = None,
    stated_grand_total: float | None = None,
    vat_rate: float = 0.0,
    peer_unit_prices_by_item: dict[str, list[float]] | None = None,
) -> dict[str, Any]:
    """Aggregate budget evidence, KYB/statutory matrix, ownership conflicts, and BoQ math."""
    has_budget, budget_display, budget_override_status = assess_budget(
        document_text=document_text,
        model_has_budget=model_has_budget,
        model_budget_display=model_budget_display,
    )

    critical_kyb = is_critical_kyb_result(kyb_data) if isinstance(kyb_data, dict) else False

    merged_records: list[StatutoryItemInput | dict[str, Any]] = []
    if isinstance(kyb_data, dict) and kyb_data:
        merged_records.extend(build_kyb_statutory_seed(kyb_data))
    if statutory_records:
        merged_records.extend(statutory_records)

    statutory_report = None
    if merged_records or required_statutory_codes is not None:
        statutory_report = evaluate_statutory_matrix(
            records=merged_records,
            required_codes=required_statutory_codes,
            as_of_date=as_of_date,
            expiring_within_days=expiring_within_days,
        )

    conflict_report = None
    if competing_bids:
        conflict_report = detect_ownership_conflicts(competing_bids)

    boq_report = None
    if boq_items is not None or stated_subtotal is not None or stated_grand_total is not None:
        boq_report = evaluate_boq_pricing(
            items=boq_items or [],
            stated_subtotal=stated_subtotal,
            stated_grand_total=stated_grand_total,
            vat_rate=vat_rate,
            peer_unit_prices_by_item=peer_unit_prices_by_item,
        )

    blocking_flags: list[str] = []
    review_flags: list[str] = []

    if critical_kyb:
        blocking_flags.append("CRITICAL_KYB_STATUS")

    if statutory_report is not None:
        if statutory_report.overall_status == "NON_COMPLIANT":
            blocking_flags.append("STATUTORY_NON_COMPLIANT")
        elif statutory_report.overall_status == "CONDITIONAL":
            review_flags.append("STATUTORY_CONDITIONAL")

    if conflict_report is not None and conflict_report.has_conflicts:
        severities = {f.severity for f in conflict_report.findings}
        if "CRITICAL" in severities or "HIGH" in severities:
            blocking_flags.append("OWNERSHIP_CONFLICT_HIGH")
        else:
            review_flags.append("OWNERSHIP_CONFLICT_REVIEW")

    if boq_report is not None and boq_report.has_anomalies:
        blocking_codes = {
            "LINE_MATH_MISMATCH",
            "SUBTOTAL_MISMATCH",
            "GRAND_TOTAL_MISMATCH",
            "NEGATIVE_PRICING_VALUE",
        }
        if any(f.code in blocking_codes for f in boq_report.findings):
            blocking_flags.append("BOQ_MATH_MISMATCH")
        else:
            review_flags.append("BOQ_PRICE_OUTLIER")

    if budget_override_status == "Conditional":
        review_flags.append("BUDGET_CONDITIONAL")

    if blocking_flags:
        package_status = "BLOCKED"
    elif review_flags:
        package_status = "REVIEW_REQUIRED"
    else:
        package_status = "CLEAR"

    return {
        "package_status": package_status,
        "blocking_flags": blocking_flags,
        "review_flags": review_flags,
        "budget": {
            "has_budget": has_budget,
            "display": budget_display,
            "override_status": budget_override_status,
        },
        "critical_kyb": critical_kyb,
        "statutory": statutory_report.to_dict() if statutory_report is not None else None,
        "ownership_conflicts": conflict_report.to_dict() if conflict_report is not None else None,
        "boq_pricing": boq_report.to_dict() if boq_report is not None else None,
    }

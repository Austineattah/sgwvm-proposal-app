import re


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


def extract_budget_evidence(document_text: str) -> str:
    """Return the first labeled budget or financial note found in extracted text."""
    for line in document_text.splitlines():
        match = _BUDGET_LABEL.search(line)
        if match and match.group(1).strip():
            return match.group(1).strip()
    return ""


def has_explicit_budget_amount(value: str) -> bool:
    """Check for a currency-qualified amount or a number-only labeled amount."""
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

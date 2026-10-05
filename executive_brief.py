import re


FIELD_PATTERNS = {
    "company": r"(?:company|vendor|organisation|organization)\s*(?:name)?\s*[:\-]\s*(.+)",
    "rc_number": r"(?:rc|cac|rc number|cac number|registration number)\s*[:\-]\s*(.+)",
    "scope": r"(?:project\s+)?scope(?:\s+of\s+work)?\s*[:\-]\s*(.+)",
    "budget": r"(?:proposed\s+)?budget\s*[:\-]\s*(.+)",
    "timeline": r"(?:proposed\s+)?(?:project\s+)?timeline\s*[:\-]\s*(.+)",
}


def _extract_labeled_value(text: str, field: str) -> str:
    pattern = re.compile(FIELD_PATTERNS[field], re.IGNORECASE)
    for line in text.splitlines():
        match = pattern.search(line.strip())
        if match:
            return match.group(1).strip().rstrip(" ;,")
    return ""


def generate_executive_action_brief(
    extracted_text: str,
    company_name: str,
    rc_number: str,
    scope: str,
    budget,
    proposed_timeline: str = "",
) -> dict[str, str]:
    """Build a deterministic executive brief from extracted text and intake fields."""
    text = extracted_text if isinstance(extracted_text, str) else ""
    fields = {
        "company": _extract_labeled_value(text, "company") or company_name.strip(),
        "rc_number": _extract_labeled_value(text, "rc_number") or rc_number.strip(),
        "scope": _extract_labeled_value(text, "scope") or scope.strip(),
        "budget": _extract_labeled_value(text, "budget"),
        "timeline": _extract_labeled_value(text, "timeline")
        or proposed_timeline.strip(),
    }
    if not fields["budget"]:
        fields["budget"] = (
            f"{float(budget):,.2f}" if budget not in (None, "") else "Not provided"
        )

    evidence = text.lower()
    concerns = (
        "not feasible",
        "infeasible",
        "unfunded",
        "unavailable resources",
        "critical risk",
        "cannot be completed",
    )
    required_fields = ("scope", "budget", "timeline")
    completeness = sum(bool(fields[field]) for field in required_fields)
    has_concern = any(term in evidence for term in concerns)
    if has_concern:
        feasibility = "Low"
        rationale = "The proposal text contains an explicit feasibility or delivery concern."
    elif completeness == len(required_fields):
        feasibility = "Moderate"
        rationale = "Scope, budget, and timeline are present; detailed due diligence is still required."
    elif completeness:
        feasibility = "Low"
        rationale = "One or more key feasibility inputs are missing from the submission."
    else:
        feasibility = "Insufficient Information"
        rationale = "The submission does not provide enough scope, budget, or timeline detail."

    brief = "\n".join(
        (
            "EXECUTIVE ACTION BRIEF",
            f"Company: {fields['company'] or 'Not identified'}",
            f"RC Number: {fields['rc_number'] or 'Not identified'}",
            f"Scope: {fields['scope'] or 'Not identified'}",
            f"Budget: {fields['budget']}",
            f"Proposed Timeline: {fields['timeline'] or 'Not provided'}",
            f"Feasibility Rating: {feasibility}",
            f"Assessment: {rationale}",
        )
    )
    return {
        "summary": brief,
        "feasibility_rating": feasibility,
        **fields,
    }

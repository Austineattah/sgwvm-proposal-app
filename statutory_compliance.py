from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any

DEFAULT_STATUTORY_CODES: tuple[str, ...] = (
    "CAC_STATUS",
    "TAX_TCC",
    "PENCOM",
    "ITF",
    "NSITF",
    "BPP_SECTOR",
)

STATUTORY_LABELS: dict[str, str] = {
    "CAC_STATUS": "CAC Registration & Corporate Status (RC/BN)",
    "TAX_TCC": "Tax Clearance Certificate (TCC / TIN)",
    "PENCOM": "PENCOM Pension Compliance Certificate",
    "ITF": "Industrial Training Fund (ITF) Compliance Certificate",
    "NSITF": "NSITF Social Insurance Compliance Certificate",
    "BPP_SECTOR": "BPP / Sectoral Registration & Statutory Attestation",
}

_CODE_ALIASES: dict[str, str] = {
    "CAC": "CAC_STATUS",
    "CAC_STATUS": "CAC_STATUS",
    "CAC_REG": "CAC_STATUS",
    "RC": "CAC_STATUS",
    "BN": "CAC_STATUS",
    "TAX": "TAX_TCC",
    "TCC": "TAX_TCC",
    "TIN": "TAX_TCC",
    "TAX_CLEARANCE": "TAX_TCC",
    "TAX_TCC": "TAX_TCC",
    "FIRS": "TAX_TCC",
    "PENCOM": "PENCOM",
    "PENSION": "PENCOM",
    "ITF": "ITF",
    "INDUSTRIAL_TRAINING_FUND": "ITF",
    "NSITF": "NSITF",
    "SOCIAL_SECURITY": "NSITF",
    "BPP": "BPP_SECTOR",
    "SECTOR": "BPP_SECTOR",
    "SECTORAL": "BPP_SECTOR",
    "BPP_SECTOR": "BPP_SECTOR",
}


@dataclass
class StatutoryItemInput:
    code: str
    label: str = ""
    reference_number: str = ""
    issue_date: date | str | None = None
    expiry_date: date | str | None = None
    verified: bool | None = None
    status_hint: str = ""
    required: bool = True
    exempt: bool = False
    exemption_reason: str = ""
    notes: str = ""


@dataclass
class EvaluatedStatutoryItem:
    code: str
    label: str
    required: bool
    status: str
    blocking: bool
    needs_review: bool
    reference_number: str = ""
    expiry_date: str | None = None
    days_to_expiry: int | None = None
    reason: str = ""
    exemption_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StatutoryComplianceReport:
    overall_status: str
    is_compliant: bool
    as_of_date: str
    items: list[EvaluatedStatutoryItem] = field(default_factory=list)
    blocking_codes: list[str] = field(default_factory=list)
    review_codes: list[str] = field(default_factory=list)
    summary_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "is_compliant": self.is_compliant,
            "as_of_date": self.as_of_date,
            "items": [item.to_dict() for item in self.items],
            "blocking_codes": list(self.blocking_codes),
            "review_codes": list(self.review_codes),
            "summary_counts": dict(self.summary_counts),
        }


def normalize_statutory_code(code: str) -> str:
    """Normalize aliases (e.g., 'TCC', 'TIN', 'CAC', 'BPP') to canonical statutory codes."""
    raw = str(code or "").strip().upper().replace("-", "_").replace(" ", "_")
    return _CODE_ALIASES.get(raw, raw or "UNKNOWN")


def _parse_date(value: date | str | None) -> date | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _coerce_item(entry: StatutoryItemInput | dict[str, Any]) -> StatutoryItemInput:
    if isinstance(entry, StatutoryItemInput):
        return entry
    if not isinstance(entry, dict):
        raise TypeError("Expected StatutoryItemInput or dict for statutory record entry.")
    ref_val = entry.get("reference_number")
    if ref_val is None:
        ref_val = entry.get("reference")
    if ref_val is None:
        ref_val = entry.get("ref")
    status_val = entry.get("status_hint")
    if status_val is None:
        status_val = entry.get("status")
    return StatutoryItemInput(
        code=str(entry.get("code") or "").strip(),
        label=str(entry.get("label") or "").strip(),
        reference_number=str(ref_val or "").strip(),
        issue_date=entry.get("issue_date"),
        expiry_date=entry.get("expiry_date"),
        verified=entry.get("verified"),
        status_hint=str(status_val or "").strip(),
        required=bool(entry.get("required", True)),
        exempt=bool(entry.get("exempt", False)),
        exemption_reason=str(entry.get("exemption_reason") or "").strip(),
        notes=str(entry.get("notes") or "").strip(),
    )


def build_kyb_statutory_seed(kyb_data: dict[str, Any]) -> list[StatutoryItemInput]:
    """Build initial CAC_STATUS and TIN/TCC seed items from an existing KYB dictionary."""
    if not isinstance(kyb_data, dict) or not kyb_data:
        return []

    seeds: list[StatutoryItemInput] = []
    rc_num = str(kyb_data.get("rc_number") or "").strip()
    company_status = str(kyb_data.get("company_status") or "").strip().upper()
    is_active_raw = kyb_data.get("is_active")
    flagged = bool(kyb_data.get("flagged", False))

    if is_active_raw is True or company_status == "ACTIVE":
        cac_verified: bool | None = True
    elif is_active_raw is False or company_status in {"INACTIVE", "NOT_FOUND", "DORMANT", "ERROR"}:
        cac_verified = False
    else:
        cac_verified = False if flagged else None

    seeds.append(
        StatutoryItemInput(
            code="CAC_STATUS",
            label=STATUTORY_LABELS["CAC_STATUS"],
            reference_number=rc_num,
            verified=cac_verified,
            status_hint=company_status or ("VERIFIED" if cac_verified else "UNVERIFIED"),
            required=True,
            notes=str(kyb_data.get("risk_label") or kyb_data.get("message") or ""),
        )
    )

    tin_val = str(kyb_data.get("tin") or "").strip()
    tin_invalid_tokens = {"", "NOT VERIFIED", "NOT LISTED ON REGISTRY", "UNVERIFIED", "ERROR", "NONE", "N/A"}
    if tin_val and tin_val.upper() not in tin_invalid_tokens:
        seeds.append(
            StatutoryItemInput(
                code="TAX_TCC",
                label=STATUTORY_LABELS["TAX_TCC"],
                reference_number=tin_val,
                verified=None,
                status_hint="TIN_ON_FILE",
                required=True,
                notes="TIN observed from KYB record; TCC validity/expiry requires confirmation.",
            )
        )

    return seeds


def evaluate_statutory_matrix(
    records: list[StatutoryItemInput | dict[str, Any]],
    required_codes: list[str] | tuple[str, ...] | None = None,
    as_of_date: date | str | None = None,
    expiring_within_days: int = 30,
) -> StatutoryComplianceReport:
    """Evaluate Nigerian statutory compliance items deterministically with audit-ready flags."""
    eval_date = _parse_date(as_of_date) or date.today()
    window_days = max(0, int(expiring_within_days))

    if required_codes is None:
        req_set = set(DEFAULT_STATUTORY_CODES)
        ordered_codes = list(DEFAULT_STATUTORY_CODES)
    else:
        ordered_codes = []
        for c in required_codes:
            nc = normalize_statutory_code(c)
            if nc not in ordered_codes:
                ordered_codes.append(nc)
        req_set = set(ordered_codes)

    by_code: dict[str, StatutoryItemInput] = {}
    for raw_entry in records or []:
        if raw_entry is None:
            continue
        item = _coerce_item(raw_entry)
        if not item.code:
            continue
        nc = normalize_statutory_code(item.code)
        item.code = nc
        if not item.label:
            item.label = STATUTORY_LABELS.get(nc, nc)
        if nc in req_set:
            item.required = True
        if nc not in ordered_codes:
            ordered_codes.append(nc)
        by_code[nc] = item

    evaluated_items: list[EvaluatedStatutoryItem] = []
    blocking_codes: list[str] = []
    review_codes: list[str] = []

    for code in ordered_codes:
        is_req = code in req_set
        label = STATUTORY_LABELS.get(code, code)
        rec = by_code.get(code)

        if rec is None:
            if is_req:
                evaluated_items.append(
                    EvaluatedStatutoryItem(
                        code=code,
                        label=label,
                        required=True,
                        status="MISSING",
                        blocking=True,
                        needs_review=True,
                        reason="Required statutory item not provided.",
                    )
                )
                blocking_codes.append(code)
                review_codes.append(code)
            else:
                evaluated_items.append(
                    EvaluatedStatutoryItem(
                        code=code,
                        label=label,
                        required=False,
                        status="OPTIONAL_MISSING",
                        blocking=False,
                        needs_review=False,
                        reason="Optional statutory item not provided.",
                    )
                )
            continue

        item_required = is_req or bool(rec.required)
        item_label = rec.label or label
        ref_num = str(rec.reference_number or "").strip()
        exp_dt = _parse_date(rec.expiry_date)
        exp_str = exp_dt.isoformat() if exp_dt else None
        days_left = (exp_dt - eval_date).days if exp_dt else None
        hint = str(rec.status_hint or "").strip().upper()
        exemption_reason = str(rec.exemption_reason or "").strip()

        has_evidence = bool(ref_num or exp_dt or hint or rec.verified is not None or rec.exempt)
        if not has_evidence:
            if item_required:
                evaluated_items.append(
                    EvaluatedStatutoryItem(
                        code=code,
                        label=item_label,
                        required=True,
                        status="MISSING",
                        blocking=True,
                        needs_review=True,
                        reason="Required statutory item has no reference, status, or expiry evidence.",
                    )
                )
                blocking_codes.append(code)
                review_codes.append(code)
            else:
                evaluated_items.append(
                    EvaluatedStatutoryItem(
                        code=code,
                        label=item_label,
                        required=False,
                        status="OPTIONAL_MISSING",
                        blocking=False,
                        needs_review=False,
                        reason="Optional statutory item not provided.",
                    )
                )
            continue

        if rec.exempt:
            if exemption_reason:
                evaluated_items.append(
                    EvaluatedStatutoryItem(
                        code=code,
                        label=item_label,
                        required=item_required,
                        status="EXEMPT",
                        blocking=False,
                        needs_review=True,
                        reference_number=ref_num,
                        expiry_date=exp_str,
                        days_to_expiry=days_left,
                        reason="Documented statutory exemption/waiver requires governance review.",
                        exemption_reason=exemption_reason,
                    )
                )
                review_codes.append(code)
            else:
                evaluated_items.append(
                    EvaluatedStatutoryItem(
                        code=code,
                        label=item_label,
                        required=item_required,
                        status="UNVERIFIED",
                        blocking=item_required,
                        needs_review=True,
                        reference_number=ref_num,
                        expiry_date=exp_str,
                        days_to_expiry=days_left,
                        reason="Exemption flag set without a documented exemption reason.",
                    )
                )
                if item_required:
                    blocking_codes.append(code)
                review_codes.append(code)
            continue

        if exp_dt is not None and exp_dt < eval_date:
            evaluated_items.append(
                EvaluatedStatutoryItem(
                    code=code,
                    label=item_label,
                    required=item_required,
                    status="EXPIRED",
                    blocking=item_required,
                    needs_review=True,
                    reference_number=ref_num,
                    expiry_date=exp_str,
                    days_to_expiry=days_left,
                    reason=f"Statutory document expired on {exp_str} (as of {eval_date.isoformat()}).",
                )
            )
            if item_required:
                blocking_codes.append(code)
            review_codes.append(code)
            continue

        if rec.verified is False or hint in {"EXPIRED", "INVALID", "NOT_FOUND", "INACTIVE", "REJECTED", "FAILED", "ERROR"}:
            evaluated_items.append(
                EvaluatedStatutoryItem(
                    code=code,
                    label=item_label,
                    required=item_required,
                    status="UNVERIFIED",
                    blocking=item_required,
                    needs_review=True,
                    reference_number=ref_num,
                    expiry_date=exp_str,
                    days_to_expiry=days_left,
                    reason=rec.notes or f"Statutory item unverified (status hint: {hint or 'unverified'}).",
                )
            )
            if item_required:
                blocking_codes.append(code)
            review_codes.append(code)
            continue

        if rec.verified is True or hint in {"VERIFIED", "VALID", "ACTIVE", "COMPLIANT"}:
            if days_left is not None and days_left <= window_days:
                evaluated_items.append(
                    EvaluatedStatutoryItem(
                        code=code,
                        label=item_label,
                        required=item_required,
                        status="EXPIRING_SOON",
                        blocking=False,
                        needs_review=True,
                        reference_number=ref_num,
                        expiry_date=exp_str,
                        days_to_expiry=days_left,
                        reason=f"Verified, but expires in {days_left} day(s) on {exp_str}.",
                    )
                )
                review_codes.append(code)
            else:
                evaluated_items.append(
                    EvaluatedStatutoryItem(
                        code=code,
                        label=item_label,
                        required=item_required,
                        status="VERIFIED",
                        blocking=False,
                        needs_review=False,
                        reference_number=ref_num,
                        expiry_date=exp_str,
                        days_to_expiry=days_left,
                        reason="Verified and valid as of evaluation date.",
                    )
                )
            continue

        evaluated_items.append(
            EvaluatedStatutoryItem(
                code=code,
                label=item_label,
                required=item_required,
                status="UNVERIFIED",
                blocking=item_required,
                needs_review=True,
                reference_number=ref_num,
                expiry_date=exp_str,
                days_to_expiry=days_left,
                reason=rec.notes or "Awaiting verification confirmation.",
            )
        )
        if item_required:
            blocking_codes.append(code)
        review_codes.append(code)

    summary_counts: dict[str, int] = {}
    for item in evaluated_items:
        summary_counts[item.status] = summary_counts.get(item.status, 0) + 1

    if blocking_codes:
        overall_status = "NON_COMPLIANT"
        is_compliant = False
    elif review_codes:
        overall_status = "CONDITIONAL"
        is_compliant = False
    else:
        overall_status = "COMPLIANT"
        is_compliant = True

    return StatutoryComplianceReport(
        overall_status=overall_status,
        is_compliant=is_compliant,
        as_of_date=eval_date.isoformat(),
        items=evaluated_items,
        blocking_codes=blocking_codes,
        review_codes=review_codes,
        summary_counts=summary_counts,
    )
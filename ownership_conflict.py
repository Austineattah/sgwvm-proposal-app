from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any

_HONORIFICS = {
    "mr", "mrs", "ms", "miss", "dr", "prof", "eng", "engr",
    "chief", "alhaji", "hajia", "barr", "esq", "sen", "hon",
    "arc", "pharm", "surv", "qs", "sir", "dame", "rev", "pst",
}


@dataclass
class PrincipalEntry:
    name: str
    role: str = ""
    ownership_pct: float | None = None
    control_type: str = ""


@dataclass
class BidOwnershipRecord:
    bid_id: str
    vendor_name: str
    rc_number: str = ""
    tin: str = ""
    directors: list[PrincipalEntry | dict[str, Any] | str] = field(default_factory=list)
    beneficial_owners: list[PrincipalEntry | dict[str, Any] | str] = field(default_factory=list)


@dataclass
class OwnershipConflictFinding:
    conflict_type: str
    severity: str
    matched_key: str
    display_label: str
    involved_bids: list[str]
    involved_vendors: list[str]
    reason: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OwnershipConflictReport:
    total_bids_analyzed: int
    has_conflicts: bool
    findings: list[OwnershipConflictFinding] = field(default_factory=list)
    flagged_bid_ids: list[str] = field(default_factory=list)
    summary_by_severity: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_bids_analyzed": self.total_bids_analyzed,
            "has_conflicts": self.has_conflicts,
            "findings": [f.to_dict() for f in self.findings],
            "flagged_bid_ids": list(self.flagged_bid_ids),
            "summary_by_severity": dict(self.summary_by_severity),
        }


def normalize_person_name(name: str) -> str:
    """Normalize a principal's name by removing honorifics/punctuation and collapsing tokens."""
    cleaned = re.sub(r"[^a-z0-9\s]", " ", str(name or "").lower())
    tokens = [tok for tok in cleaned.split() if tok and tok not in _HONORIFICS]
    return " ".join(tokens)


def _name_match_key(norm_name: str) -> str:
    """Order-insensitive token key so 'Adebayo Musa' and 'Musa Adebayo' share a key."""
    tokens = sorted(norm_name.split())
    return "|".join(tokens)


def _initial_signature(norm_name: str) -> str:
    """Match 'A. Musa' / 'A Musa' with 'Adebayo Musa' using surname + first initial."""
    tokens = norm_name.split()
    if len(tokens) < 2:
        return ""
    first_init = tokens[0][0]
    last_tok = tokens[-1]
    return f"{last_tok}:{first_init}"


def normalize_registration_id(value: str) -> str:
    """Normalize RC/BN/TIN identifiers for exact cross-bid comparison."""
    raw = re.sub(r"[^a-z0-9]", "", str(value or "").upper())
    if raw.startswith("RC") and len(raw) > 2:
        raw = raw[2:]
    elif raw.startswith("BN") and len(raw) > 2:
        raw = raw[2:]
    return raw.lstrip("0") or raw


def _coerce_principal(entry: PrincipalEntry | dict[str, Any] | str, default_role: str) -> PrincipalEntry | None:
    if isinstance(entry, PrincipalEntry):
        name = str(entry.name or "").strip()
        if not name:
            return None
        return PrincipalEntry(
            name=name,
            role=str(entry.role or default_role).strip(),
            ownership_pct=entry.ownership_pct,
            control_type=str(entry.control_type or "").strip(),
        )
    if isinstance(entry, str):
        name = entry.strip()
        return PrincipalEntry(name=name, role=default_role) if name else None
    if isinstance(entry, dict):
        name = str(entry.get("name") or entry.get("full_name") or "").strip()
        if not name:
            return None
        pct_raw = entry.get("ownership_pct", entry.get("shareholding_pct"))
        pct_val: float | None = None
        if pct_raw is not None and pct_raw != "":
            try:
                pct_val = float(pct_raw)
            except (TypeError, ValueError):
                pct_val = None
        return PrincipalEntry(
            name=name,
            role=str(entry.get("role") or default_role).strip(),
            ownership_pct=pct_val,
            control_type=str(entry.get("control_type") or "").strip(),
        )
    return None


def _coerce_bid(record: BidOwnershipRecord | dict[str, Any]) -> BidOwnershipRecord:
    if isinstance(record, BidOwnershipRecord):
        return record
    if not isinstance(record, dict):
        raise TypeError("Expected BidOwnershipRecord or dict for bid record.")
    return BidOwnershipRecord(
        bid_id=str(record.get("bid_id") or record.get("id") or "").strip(),
        vendor_name=str(record.get("vendor_name") or record.get("company_name") or "Unknown Vendor").strip(),
        rc_number=str(record.get("rc_number") or "").strip(),
        tin=str(record.get("tin") or "").strip(),
        directors=list(record.get("directors") or []),
        beneficial_owners=list(record.get("beneficial_owners") or record.get("psc") or []),
    )


def detect_ownership_conflicts(
    bids: list[BidOwnershipRecord | dict[str, Any]],
) -> OwnershipConflictReport:
    """Detect cross-bid director, beneficial owner/PSC, role-overlap, and ID collisions."""
    coerced_bids = [_coerce_bid(b) for b in (bids or [])]
    findings: list[OwnershipConflictFinding] = []
    flagged_set: set[str] = set()

    # 1. Shared RC/BN or TIN across distinct bids
    id_buckets: dict[tuple[str, str], list[tuple[str, str, str]]] = {}
    for idx, bid in enumerate(coerced_bids):
        bid_key = bid.bid_id or f"BID-{idx + 1}"
        for id_type, raw_id in (("RC_NUMBER", bid.rc_number), ("TIN", bid.tin)):
            norm_id = normalize_registration_id(raw_id)
            if norm_id and norm_id.upper() not in {"NA", "NONE", "UNVERIFIED", "NOTVERIFIED", "ERROR"}:
                id_buckets.setdefault((id_type, norm_id), []).append((bid_key, bid.vendor_name, raw_id))

    for (id_type, norm_id), entries in id_buckets.items():
        distinct_bids = {item[0] for item in entries}
        if len(distinct_bids) > 1:
            bids_list = sorted(distinct_bids)
            vendors_list = sorted({item[1] for item in entries})
            raw_vals = sorted({item[2] for item in entries if item[2]})
            findings.append(
                OwnershipConflictFinding(
                    conflict_type=f"SHARED_{id_type}",
                    severity="CRITICAL" if id_type == "RC_NUMBER" else "HIGH",
                    matched_key=f"{id_type}:{norm_id}",
                    display_label=f"{id_type} ({', '.join(raw_vals) or norm_id})",
                    involved_bids=bids_list,
                    involved_vendors=vendors_list,
                    reason=f"Identical {id_type} appears across {len(bids_list)} competing bids; requires governance review.",
                    details={"raw_values": raw_vals},
                )
            )
            flagged_set.update(bids_list)

    # 2. Collect principal appearances per bid (director vs beneficial_owner)
    principal_rows: list[dict[str, Any]] = []
    for idx, bid in enumerate(coerced_bids):
        bid_key = bid.bid_id or f"BID-{idx + 1}"
        for p_raw in bid.directors:
            p = _coerce_principal(p_raw, "DIRECTOR")
            if p:
                norm_n = normalize_person_name(p.name)
                if norm_n:
                    principal_rows.append({
                        "category": "DIRECTOR",
                        "bid_id": bid_key,
                        "vendor_name": bid.vendor_name,
                        "raw_name": p.name,
                        "norm_name": norm_n,
                        "token_key": _name_match_key(norm_n),
                        "init_key": _initial_signature(norm_n),
                        "ownership_pct": p.ownership_pct,
                        "control_type": p.control_type,
                    })
        for p_raw in bid.beneficial_owners:
            p = _coerce_principal(p_raw, "BENEFICIAL_OWNER")
            if p:
                norm_n = normalize_person_name(p.name)
                if norm_n:
                    principal_rows.append({
                        "category": "BENEFICIAL_OWNER",
                        "bid_id": bid_key,
                        "vendor_name": bid.vendor_name,
                        "raw_name": p.name,
                        "norm_name": norm_n,
                        "token_key": _name_match_key(norm_n),
                        "init_key": _initial_signature(norm_n),
                        "ownership_pct": p.ownership_pct,
                        "control_type": p.control_type,
                    })

    # Shared exact/token-normalized Director across bids
    dir_groups: dict[str, list[dict[str, Any]]] = {}
    for row in principal_rows:
        if row["category"] == "DIRECTOR" and row["token_key"]:
            dir_groups.setdefault(row["token_key"], []).append(row)

    matched_dir_keys: set[str] = set()
    for t_key, rows in dir_groups.items():
        distinct_bids = {r["bid_id"] for r in rows}
        if len(distinct_bids) > 1:
            bids_list = sorted(distinct_bids)
            vendors_list = sorted({r["vendor_name"] for r in rows})
            names_list = sorted({r["raw_name"] for r in rows})
            findings.append(
                OwnershipConflictFinding(
                    conflict_type="SHARED_DIRECTOR",
                    severity="HIGH",
                    matched_key=f"DIRECTOR:{t_key}",
                    display_label=", ".join(names_list),
                    involved_bids=bids_list,
                    involved_vendors=vendors_list,
                    reason=f"Shared director across {len(bids_list)} bids ({', '.join(names_list)}).",
                    details={"names": names_list},
                )
            )
            flagged_set.update(bids_list)
            matched_dir_keys.add(t_key)

    # Shared exact/token-normalized Beneficial Owner / PSC across bids
    bo_groups: dict[str, list[dict[str, Any]]] = {}
    for row in principal_rows:
        if row["category"] == "BENEFICIAL_OWNER" and row["token_key"]:
            bo_groups.setdefault(row["token_key"], []).append(row)

    matched_bo_keys: set[str] = set()
    for t_key, rows in bo_groups.items():
        distinct_bids = {r["bid_id"] for r in rows}
        if len(distinct_bids) > 1:
            bids_list = sorted(distinct_bids)
            vendors_list = sorted({r["vendor_name"] for r in rows})
            names_list = sorted({r["raw_name"] for r in rows})
            pcts = [r["ownership_pct"] for r in rows if r["ownership_pct"] is not None]
            findings.append(
                OwnershipConflictFinding(
                    conflict_type="SHARED_BENEFICIAL_OWNER",
                    severity="HIGH",
                    matched_key=f"BO:{t_key}",
                    display_label=", ".join(names_list),
                    involved_bids=bids_list,
                    involved_vendors=vendors_list,
                    reason=f"Shared beneficial owner / PSC across {len(bids_list)} bids ({', '.join(names_list)}).",
                    details={"names": names_list, "ownership_percentages": pcts},
                )
            )
            flagged_set.update(bids_list)
            matched_bo_keys.add(t_key)

    # Cross-role overlap: same principal as Beneficial Owner on one bid and Director on another bid
    all_person_groups: dict[str, list[dict[str, Any]]] = {}
    for row in principal_rows:
        if row["token_key"]:
            all_person_groups.setdefault(row["token_key"], []).append(row)

    for t_key, rows in all_person_groups.items():
        distinct_bids = {r["bid_id"] for r in rows}
        categories = {r["category"] for r in rows}
        if len(distinct_bids) > 1 and "DIRECTOR" in categories and "BENEFICIAL_OWNER" in categories:
            # Avoid duplicate when both exact same-role groups already covered the pair
            if not (t_key in matched_dir_keys and t_key in matched_bo_keys):
                bids_list = sorted(distinct_bids)
                vendors_list = sorted({r["vendor_name"] for r in rows})
                names_list = sorted({r["raw_name"] for r in rows})
                findings.append(
                    OwnershipConflictFinding(
                        conflict_type="CROSS_ROLE_DIRECTOR_BO",
                        severity="HIGH",
                        matched_key=f"CROSS_ROLE:{t_key}",
                        display_label=", ".join(names_list),
                        involved_bids=bids_list,
                        involved_vendors=vendors_list,
                        reason=f"Principal appears as both Beneficial Owner/PSC and Director across {len(bids_list)} bids.",
                        details={"names": names_list},
                    )
                )
                flagged_set.update(bids_list)

    # Medium-severity initial + surname match across distinct bids not already flagged by token_key
    init_groups: dict[str, list[dict[str, Any]]] = {}
    for row in principal_rows:
        if row["init_key"]:
            init_groups.setdefault(row["init_key"], []).append(row)

    for i_key, rows in init_groups.items():
        distinct_bids = {r["bid_id"] for r in rows}
        token_keys = {r["token_key"] for r in rows}
        if len(distinct_bids) > 1 and len(token_keys) > 1:
            bids_list = sorted(distinct_bids)
            vendors_list = sorted({r["vendor_name"] for r in rows})
            names_list = sorted({r["raw_name"] for r in rows})
            findings.append(
                OwnershipConflictFinding(
                    conflict_type="PARTIAL_NAME_OVERLAP",
                    severity="MEDIUM",
                    matched_key=f"INIT:{i_key}",
                    display_label=", ".join(names_list),
                    involved_bids=bids_list,
                    involved_vendors=vendors_list,
                    reason=f"Possible surname + initial overlap across {len(bids_list)} bids ({', '.join(names_list)}); verify identity.",
                    details={"names": names_list},
                )
            )
            flagged_set.update(bids_list)

    summary_by_severity: dict[str, int] = {}
    for f in findings:
        summary_by_severity[f.severity] = summary_by_severity.get(f.severity, 0) + 1

    return OwnershipConflictReport(
        total_bids_analyzed=len(coerced_bids),
        has_conflicts=bool(findings),
        findings=findings,
        flagged_bid_ids=sorted(flagged_set),
        summary_by_severity=summary_by_severity,
    )
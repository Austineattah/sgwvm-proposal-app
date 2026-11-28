from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.international_staging import format_country_currency, get_country_profile


@dataclass(frozen=True)
class ProcurementStageSpec:
    stage_key: str
    title: str
    owner_role: str
    requires_kyc_gate: bool


@dataclass(frozen=True)
class CountryProcurementConfig:
    country_code: str
    regime_code: str
    direct_threshold_amount: float
    competitive_threshold_amount: float
    mandatory_kyc_items: tuple[str, ...]
    stages: tuple[ProcurementStageSpec, ...]


DEFAULT_KYC_ITEMS: tuple[str, ...] = (
    "Corporate Registration & Beneficial Ownership Disclosure",
    "Tax Clearance / Good Standing Certificate",
    "Conflict of Interest & Anti-Corruption Attestation",
    "Authorized Signatory & KYC Identity Verification",
)

COUNTRY_PROCUREMENT_CONFIGS: dict[str, CountryProcurementConfig] = {
    "NG": CountryProcurementConfig(
        country_code="NG",
        regime_code="NG_PPA_BPP_STAGE_GATE",
        direct_threshold_amount=5000000.0,
        competitive_threshold_amount=50000000.0,
        mandatory_kyc_items=(
            "CAC Certificate of Incorporation & Status Report",
            "FIRS Tax Clearance Certificate (TCC) & TIN",
            "PENCOM & ITF Compliance Certificates",
            "BPP Interim Registration / Conflict of Interest Attestation",
        ),
        stages=(
            ProcurementStageSpec("kyc_intake", "1. KYC & Statutory Vetting", "Desk Operator", True),
            ProcurementStageSpec("technical_eval", "2. Technical Bid Review", "Evaluation Committee", True),
            ProcurementStageSpec("financial_eval", "3. Financial Evaluation", "Procurement Committee", True),
            ProcurementStageSpec("award_registry", "4. Award & Registry", "Client Admin", True),
        ),
    ),
}


def get_procurement_config(country_code: Any = "NG") -> CountryProcurementConfig:
    profile = get_country_profile(country_code, fallback="NG")
    existing = COUNTRY_PROCUREMENT_CONFIGS.get(profile.code)
    if existing is not None:
        return existing
    return CountryProcurementConfig(
        country_code=profile.code,
        regime_code=profile.procurement_regime,
        direct_threshold_amount=10000.0,
        competitive_threshold_amount=100000.0,
        mandatory_kyc_items=DEFAULT_KYC_ITEMS,
        stages=tuple(
            ProcurementStageSpec(
                stage_key=f"stage_{idx + 1}",
                title=label,
                owner_role="Procurement Desk" if idx == 0 else ("Evaluation Committee" if idx < len(profile.intake_stages) - 1 else "Client Admin"),
                requires_kyc_gate=(idx == 0),
            )
            for idx, label in enumerate(profile.intake_stages)
        ),
    )


def summarize_thresholds(country_code: Any = "NG") -> dict[str, str]:
    cfg = get_procurement_config(country_code)
    return {
        "direct_limit": format_country_currency(cfg.direct_threshold_amount, cfg.country_code, decimals=0),
        "competitive_limit": format_country_currency(cfg.competitive_threshold_amount, cfg.country_code, decimals=0),
    }

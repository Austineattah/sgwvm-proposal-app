from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CountryProfile:
    code: str
    name: str
    dial_code: str
    timezone: str
    currency_code: str
    currency_symbol: str
    currency_name: str
    default_language: str
    supported_languages: tuple[str, ...]
    corporate_id_label: str
    tax_id_label: str
    compliance_badge: str
    procurement_regime: str
    intake_stages: tuple[str, ...]


COUNTRY_PROFILES: dict[str, CountryProfile] = {
    "NG": CountryProfile(
        code="NG",
        name="Nigeria",
        dial_code="+234",
        timezone="Africa/Lagos",
        currency_code="NGN",
        currency_symbol="\u20a6",
        currency_name="Nigerian Naira",
        default_language="en",
        supported_languages=("en", "fr"),
        corporate_id_label="CAC RC / BN Number",
        tax_id_label="FIRS TIN",
        compliance_badge="NEXUSVAULT_TECH Sovereign Enterprise Engine ? NITDA / NDPA Compliant",
        procurement_regime="NG_PPA_BPP_STAGE_GATE",
        intake_stages=("1. KYC & Statutory Vetting", "2. Technical Bid Review", "3. Financial Evaluation", "4. Award & Registry"),
    ),
    "GH": CountryProfile(
        code="GH",
        name="Ghana",
        dial_code="+233",
        timezone="Africa/Accra",
        currency_code="GHS",
        currency_symbol="GH\u20b5",
        currency_name="Ghanaian Cedi",
        default_language="en",
        supported_languages=("en", "fr"),
        corporate_id_label="ORC Registration Number",
        tax_id_label="GRA TIN",
        compliance_badge="NEXUSVAULT_TECH Enterprise Engine ? Ghana Data Protection Act Compliant",
        procurement_regime="GH_PPA_STAGE_GATE",
        intake_stages=("1. Vendor & PPA Registration", "2. Technical Qualification", "3. Commercial Evaluation", "4. Contract Award"),
    ),
    "KE": CountryProfile(
        code="KE",
        name="Kenya",
        dial_code="+254",
        timezone="Africa/Nairobi",
        currency_code="KES",
        currency_symbol="KSh",
        currency_name="Kenyan Shilling",
        default_language="en",
        supported_languages=("en", "fr"),
        corporate_id_label="BRS Registration Number",
        tax_id_label="KRA PIN",
        compliance_badge="NEXUSVAULT_TECH Enterprise Engine ? Kenya ODPC / PPADA Compliant",
        procurement_regime="KE_PPADA_STAGE_GATE",
        intake_stages=("1. KYC & KRA Compliance", "2. Preliminary & Technical", "3. Financial Bid Analysis", "4. Notification & Award"),
    ),
    "ZA": CountryProfile(
        code="ZA",
        name="South Africa",
        dial_code="+27",
        timezone="Africa/Johannesburg",
        currency_code="ZAR",
        currency_symbol="R",
        currency_name="South African Rand",
        default_language="en",
        supported_languages=("en",),
        corporate_id_label="CIPC Registration Number",
        tax_id_label="SARS Tax Reference",
        compliance_badge="NEXUSVAULT_TECH Enterprise Engine ? POPIA Compliant",
        procurement_regime="ZA_PFMA_STAGE_GATE",
        intake_stages=("1. CSD & POPIA Verification", "2. Functionality & B-BBEE", "3. Price & Preference Points", "4. Adjudication & Award"),
    ),
    "GB": CountryProfile(
        code="GB",
        name="United Kingdom",
        dial_code="+44",
        timezone="Europe/London",
        currency_code="GBP",
        currency_symbol="\u20a6",
        currency_name="British Pound Sterling",
        default_language="en",
        supported_languages=("en", "fr"),
        corporate_id_label="Companies House Number",
        tax_id_label="HMRC UTR / VAT",
        compliance_badge="NEXUSVAULT_TECH Enterprise Engine ? UK GDPR / Procurement Act Compliant",
        procurement_regime="GB_PA23_STAGE_GATE",
        intake_stages=("1. Supplier Exclusion & KYC", "2. Selection & Technical", "3. Tender Assessment", "4. Contract Award Notice"),
    ),
    "US": CountryProfile(
        code="US",
        name="United States",
        dial_code="+1",
        timezone="America/New_York",
        currency_code="USD",
        currency_symbol="$",
        currency_name="US Dollar",
        default_language="en",
        supported_languages=("en", "es"),
        corporate_id_label="State Entity / UEI Number",
        tax_id_label="IRS EIN",
        compliance_badge="NEXUSVAULT_TECH Enterprise Engine ? SOC2 / NIST Aligned",
        procurement_regime="US_FAR_STAGE_GATE",
        intake_stages=("1. SAM / KYC Responsibility", "2. Technical Capability", "3. Cost & Price Analysis", "4. Contracting Officer Award"),
    ),
    "AE": CountryProfile(
        code="AE",
        name="United Arab Emirates",
        dial_code="+971",
        timezone="Asia/Dubai",
        currency_code="AED",
        currency_symbol="AED ",
        currency_name="UAE Dirham",
        default_language="en",
        supported_languages=("en", "ar"),
        corporate_id_label="Commercial Trade License No.",
        tax_id_label="FTA TRN",
        compliance_badge="NEXUSVAULT_TECH Enterprise Engine ? UAE PDPL Compliant",
        procurement_regime="AE_FEDERAL_STAGE_GATE",
        intake_stages=("1. Trade License & KYC", "2. Technical Bid Evaluation", "3. Financial Bid Opening", "4. Approval & Award"),
    ),
    "FR": CountryProfile(
        code="FR",
        name="France",
        dial_code="+33",
        timezone="Europe/Paris",
        currency_code="EUR",
        currency_symbol="\u20ac",
        currency_name="Euro",
        default_language="fr",
        supported_languages=("fr", "en"),
        corporate_id_label="SIREN / SIRET Number",
        tax_id_label="Num?ro TVA Intracommunautaire",
        compliance_badge="NEXUSVAULT_TECH Enterprise Engine ? RGPD / Code de la Commande Publique",
        procurement_regime="FR_CCP_STAGE_GATE",
        intake_stages=("1. Candidature & RGPD/KYC", "2. Analyse des Offres Techniques", "3. Analyse Financi?re", "4. Attribution du March?"),
    ),
    "CI": CountryProfile(
        code="CI",
        name="C?te d'Ivoire",
        dial_code="+225",
        timezone="Africa/Abidjan",
        currency_code="XOF",
        currency_symbol="CFA ",
        currency_name="West African CFA Franc",
        default_language="fr",
        supported_languages=("fr", "en"),
        corporate_id_label="RCCM Number",
        tax_id_label="Compte Contribuable (NCC)",
        compliance_badge="NEXUSVAULT_TECH Enterprise Engine ? ARTCI / UEMOA Compliant",
        procurement_regime="CI_CMP_STAGE_GATE",
        intake_stages=("1. KYC & Conformit? Fiscale", "2. ?valuation Technique", "3. ?valuation Financi?re", "4. Attribution & Visa"),
    ),
}


def normalize_country_code(raw: Any, fallback: str = "NG") -> str:
    cleaned = str(raw or "").strip().upper()
    if cleaned in COUNTRY_PROFILES:
        return cleaned
    return fallback if fallback in COUNTRY_PROFILES else "NG"


def get_country_profile(raw: Any, fallback: str = "NG") -> CountryProfile:
    code = normalize_country_code(raw, fallback=fallback)
    return COUNTRY_PROFILES[code]


def format_country_currency(
    amount: float | int,
    country_code: Any = "NG",
    decimals: int = 2,
) -> str:
    profile = get_country_profile(country_code)
    val = float(amount)
    formatted = f"{val:,.{decimals}f}"
    return f"{profile.currency_symbol}{formatted} ({profile.currency_code})"

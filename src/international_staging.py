from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_ENTITY_CATEGORIES: tuple[str, ...] = (
    "Public University / Polytechnic / Research Institute (Academic Sector)",
    "Multinational Funder / UN Agency / International NGO (Humanitarian Sector)",
    "National Assembly / Parliament / Legislative Directorate",
    "Federal Ministry, Department, or Agency (MDA)",
    "State Ministry, Department, or Agency (MDA)",
    "Private Limited Company / Enterprise (Commercial Sector)",
    "Non-Profit Foundation / Civil Society Organization",
)

DEFAULT_ADMIN_TIERS: tuple[str, ...] = (
    "Sovereign Legislative & Statutory Node",
    "Custom Government Parastatal Node",
    "Enterprise Commercial Node",
    "NGO & Donor Grant Node",
    "Sovereign Academic Research Node",
)


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
    entity_categories: tuple[str, ...] = DEFAULT_ENTITY_CATEGORIES
    admin_tiers: tuple[str, ...] = DEFAULT_ADMIN_TIERS
    example_org: str = "Federal Ministry of Technology"
    example_email: str = "contact@entity.gov.ng"
    example_phone: str = "+234 803 000 0000"
    example_address: str = "Central Area, Abuja"


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
        entity_categories=DEFAULT_ENTITY_CATEGORIES,
        admin_tiers=DEFAULT_ADMIN_TIERS,
        example_org="Federal Ministry of Technology",
        example_email="contact@entity.gov.ng",
        example_phone="+234 803 000 0000",
        example_address="Central Area, Abuja",
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
        example_org="Ministry of Communications and Digitalisation",
        example_email="procurement@entity.gov.gh",
        example_phone="+233 24 000 0000",
        example_address="Ridge, Accra",
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
        example_org="Ministry of Information, Communications and the Digital Economy",
        example_email="procurement@entity.go.ke",
        example_phone="+254 700 000 000",
        example_address="Upper Hill, Nairobi",
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
        example_org="Department of Communications and Digital Technologies",
        example_email="tenders@entity.gov.za",
        example_phone="+27 12 000 0000",
        example_address="Pretoria Central, Pretoria",
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
        example_org="Department for Science, Innovation and Technology",
        example_email="procurement@entity.gov.uk",
        example_phone="+44 20 7946 0000",
        example_address="Whitehall, London",
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
        example_org="Federal Digital Procurement Directorate",
        example_email="procurement@entity.gov",
        example_phone="+1 202 555 0100",
        example_address="Washington, DC",
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
        example_org="Digital Government Procurement Authority",
        example_email="tenders@entity.gov.ae",
        example_phone="+971 4 000 0000",
        example_address="Dubai Internet City, Dubai",
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
        entity_categories=(
            "Ministère / Administration de l'État (État central)",
            "Établissement public national (EPA / EPIC)",
            "Collectivité territoriale (Région / Département / Commune)",
            "Assemblée nationale / Sénat / Direction parlementaire",
            "Société par actions simplifiée (SAS / SASU) / Société anonyme (SA)",
            "Société à responsabilité limitée (SARL / EURL)",
            "Association loi 1901 / Fondation / ONG",
        ),
        admin_tiers=(
            "Nœud Souverain Parlementaire & Statutaire",
            "Nœud Administration Publique & Établissement Public",
            "Nœud Entreprise Commerciale (SIREN/SIRET)",
            "Nœud ONG, Fondation & Subvention",
            "Nœud Universitaire & Recherche Publique",
        ),
        example_org="Ministère de la Transformation et de la Fonction Publiques",
        example_email="marches@entite.gouv.fr",
        example_phone="+33 1 42 75 00 00",
        example_address="20 Avenue de Ségur, 75007 Paris",
    ),
    "DE": CountryProfile(
        code="DE",
        name="Germany",
        dial_code="+49",
        timezone="Europe/Berlin",
        currency_code="EUR",
        currency_symbol="\u20ac",
        currency_name="Euro",
        default_language="de",
        supported_languages=("de", "en", "fr"),
        corporate_id_label="HRB / HRA (Handelsregister)",
        tax_id_label="USt-IdNr. / Steuernummer",
        compliance_badge="NEXUSVAULT_TECH Enterprise Engine - DSGVO / GWB Vergaberecht",
        procurement_regime="DE_GWB_STAGE_GATE",
        intake_stages=(
            "1. Eignungsprüfung & DSGVO/KYC",
            "2. Technische Angebotsprüfung",
            "3. Wirtschaftliche Prüfung",
            "4. Zuschlag & Prüfprotokoll",
        ),
        entity_categories=(
            "Bundesministerium / Behörde / Körperschaft des öffentlichen Rechts",
            "Bundesland / Kommune / Öffentlicher Auftraggeber",
            "Bundes- oder Landesunternehmen / Öffentlicher Versorger",
            "Bundestag / Bundesrat / Parlamentarische Stelle",
            "GmbH / UG (haftungsbeschränkt) / AG",
            "GmbH & Co. KG / OHG / Partnerschaftsgesellschaft",
            "Stiftung / Eingetragener Verein (e.V.) / NGO",
        ),
        admin_tiers=(
            "Souveräner Parlamentarischer & Statutarischer Knoten",
            "Öffentliche Verwaltung & Körperschaftsknoten",
            "Wirtschaftsunternehmen (HRB/HRA & USt-IdNr.)",
            "Stiftung, Verein & Fördermittelknoten",
            "Wissenschaftlicher & Öffentlicher Forschungsknoten",
        ),
        example_org="Bundesministerium für Digitales und Verwaltung",
        example_email="vergabe@behoerde.de",
        example_phone="+49 30 18000 0000",
        example_address="Wilhelmstraße 79, 10117 Berlin",
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
        entity_categories=(
            "Ministère / Direction Générale de l'État",
            "Établissement Public National (EPN)",
            "Collectivité Territoriale / District / Commune",
            "Assemblée Nationale / Sénat",
            "Société Anonyme (SA) / Société à Responsabilité Limitée (SARL)",
            "ONG / Fondation / Organisation Internationale",
            "Université / Institut de Recherche Publique",
        ),
        admin_tiers=(
            "Nœud Souverain Parlementaire & Statutaire",
            "Nœud Ministère & Établissement Public (EPN)",
            "Nœud Entreprise Commerciale (RCCM)",
            "Nœud ONG & Bailleur de Fonds",
            "Nœud Académique & Recherche",
        ),
        example_org="Ministère de la Transition Numérique et de la Digitalisation",
        example_email="passation@entite.gouv.ci",
        example_phone="+225 27 20 00 00 00",
        example_address="Plateau, Abidjan",
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

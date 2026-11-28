from __future__ import annotations

from typing import Any

LANGUAGE_LABELS: dict[str, str] = {
    "en": "English (EN)",
    "fr": "Français (FR)",
    "es": "Español (ES)",
    "ar": "العربية (AR)",
}

RTL_LANGUAGES: set[str] = {"ar"}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "country_reference_label": "Country Reference",
        "language_reference_label": "Language Stage",
        "jurisdiction_label": "Jurisdiction",
        "currency_label": "Currency",
        "language_label": "Language",
        "ids_label": "IDs",
        "stage_gate_label": "Stage Gate",
        "hero_subtitle": "Configure organizational scope and deploy a transparent, auditable proposal and KYC intake gateway.",
    },
    "fr": {
        "country_reference_label": "Référence Pays",
        "language_reference_label": "Langue d'Interface",
        "jurisdiction_label": "Juridiction",
        "currency_label": "Devise",
        "language_label": "Langue",
        "ids_label": "Identifiants",
        "stage_gate_label": "Étapes de Passation",
        "hero_subtitle": "Configurez le périmètre organisationnel et déployez un portail d'offres et KYC auditable.",
    },
    "es": {
        "country_reference_label": "Referencia de País",
        "language_reference_label": "Idioma Operativo",
        "jurisdiction_label": "Jurisdicción",
        "currency_label": "Moneda",
        "language_label": "Idioma",
        "ids_label": "Identificadores",
        "stage_gate_label": "Etapas de Licitación",
        "hero_subtitle": "Configure el alcance organizacional y despliegue una puerta de propuestas y KYC auditable.",
    },
    "ar": {
        "country_reference_label": "مرجع الدولة",
        "language_reference_label": "لغة الواجهة",
        "jurisdiction_label": "الاختصاص القضائي",
        "currency_label": "العملة",
        "language_label": "اللغة",
        "ids_label": "المعرّفات",
        "stage_gate_label": "مراحل المشتريات",
        "hero_subtitle": "تهيئة النطاق المؤسسي وتشغيل بوابة شفافة وقابلة للتدقيق للعروض والتحقق من الهوية KYC.",
    },
}


def normalize_language_code(raw: Any, fallback: str = "en") -> str:
    cleaned = str(raw or "").strip().lower()
    if "-" in cleaned:
        cleaned = cleaned.split("-", 1)[0]
    if cleaned in TRANSLATIONS:
        return cleaned
    return fallback if fallback in TRANSLATIONS else "en"


def is_rtl_language(lang_code: Any) -> bool:
    return normalize_language_code(lang_code) in RTL_LANGUAGES


def get_text(key: str, lang_code: Any = "en", **kwargs: Any) -> str:
    lang = normalize_language_code(lang_code)
    template = TRANSLATIONS.get(lang, {}).get(key) or TRANSLATIONS["en"].get(key) or key
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template

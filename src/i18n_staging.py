from __future__ import annotations

from typing import Any

LANGUAGE_LABELS: dict[str, str] = {
    "en": "English (EN)",
    "fr": "Fran\u00e7ais (FR)",
    "de": "Deutsch",
    "es": "Espa\u00f1ol (ES)",
    "ar": "\u0627\u0644\u0639\u0631\u0628\u064a\u0629 (AR)",
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
        "onboarding_step1_heading": "Step 1: Organizational Classification & Domain Setup",
        "entity_category_label": "Select Organization / Entity Category*",
        "org_name_label": "Organizational Entity Name*",
        "dispatch_email_label": "Official Dispatch Email*",
        "phone_contact_label": "Official Phone / SMS Gateway Contact*",
        "hq_address_label": "Institutional Headquarters Address*",
        "admin_email_label": "Executive Chief Notification Node (EG, Director, Perm Sec. etc.)",
        "onboarding_step2_heading": "Step 2: Branding & Custom Portal Heading",
        "custom_title_label": "Custom Portal Banner Title",
        "tier_label": "SaaS Sovereign Tier*",
        "logo_upload_label": "Upload Official Institutional Branding Logo (PNG/JPG)",
        "benefits_button_label": 'Potential Institutional Benefits',
        "about_org_button_label": 'About the Organisation',
        "benefits_heading": 'Potential Benefits of the NexusVault Platform to Institutions',
        "benefit_reputation_title": 'Enhanced Organizational Reputation & Digital Leadership:',
        "benefit_reputation_body": 'Launching a transparent digital bidding and proposal portal elevates institutional credibility and builds public and vendor trust.',
        "benefit_governance_title": 'Structured Governance & Audit Readiness:',
        "benefit_governance_body": 'Standardized intake stages, traceable records, and clear accountability reduce bottlenecks across review teams.',
        "benefit_compliance_title": 'KYC & Anti-Duplication Safeguards:',
        "benefit_compliance_body": 'Automated entity checks and structured documentation help prevent duplicate submissions and compliance gaps.',
        "entity_categories": ['Government Ministry / Agency / Statutory Body', 'State-Owned Enterprise / Public Utility', 'Private Corporation / Enterprise', 'Non-Profit Foundation / Civil Society Organization'],
        "hide_panel_label": 'Hide Panel',
        "switch_to_about_org": 'Switch to: About the Organisation',
        "switch_to_benefits": 'Switch to: Potential Institutional Benefits',
        "back_to_onboarding": 'Back to Onboarding View',
        "benefit_volume_title": 'Expanded Vendor Volume & Revenue Generation Potential:',
        "benefit_volume_body": 'By simplifying digital submission and removing geographic barriers, heavy courier costs, and physical access hurdles, the portal enables broader vendor participation from anywhere-increasing bidding volume, competitive tension, and revenue generation potential for the institution.',
        "about_org_heading": 'About NexusVault Digital Technology',
        "about_org_body": '<strong>NexusVault Digital Technology Company</strong> delivers sovereign proposal intake, compliance vetting, and bid-evaluation workflows with structured governance and auditability across public and enterprise tiers.',
    },
    "fr": {
        "country_reference_label": "R\u00e9f\u00e9rence Pays",
        "language_reference_label": "Langue d'Interface",
        "jurisdiction_label": "Juridiction",
        "currency_label": "Devise",
        "language_label": "Langue",
        "ids_label": "Identifiants",
        "stage_gate_label": "\u00c9tapes de Passation",
        "hero_subtitle": "Configurez le p\u00e9rim\u00e8tre organisationnel et d\u00e9ployez un portail d'offres et KYC auditable.",
        "onboarding_step1_heading": "\u00c9tape 1 : Classification Organisationnelle & Configuration du Domaine",
        "entity_category_label": "S\u00e9lectionner la Cat\u00e9gorie d'Organisation / d'Entit\u00e9*",
        "org_name_label": "Nom de l'Entit\u00e9 Organisationnelle*",
        "dispatch_email_label": "Adresse E-mail Officielle de Transmission*",
        "phone_contact_label": "T\u00e9l\u00e9phone Officiel / Contact Passerelle SMS*",
        "hq_address_label": "Adresse du Si\u00e8ge Institutionnel*",
        "admin_email_label": "Adresse de Notification de la Direction Ex\u00e9cutive (DG, Directeur, Sec. G\u00e9n., etc.)",
        "onboarding_step2_heading": "\u00c9tape 2 : Identit\u00e9 Visuelle & Titre Personnalis\u00e9 du Portail",
        "custom_title_label": "Titre Personnalis\u00e9 de la Banni\u00e8re du Portail",
        "tier_label": "Niveau Souverain SaaS*",
        "logo_upload_label": "T\u00e9l\u00e9verser le Logo Institutionnel Officiel (PNG/JPG)",
        "benefits_button_label": 'Avantages Institutionnels Potentiels',
        "about_org_button_label": "À propos de l'Organisation",
        "benefits_heading": 'Avantages Potentiels de la Plateforme NexusVault pour les Institutions',
        "benefit_reputation_title": 'Réputation Organisationnelle Renforcée & Leadership Numérique :',
        "benefit_reputation_body": "Le déploiement d'un portail numérique transparent d'appels d'offres et de propositions renforce la crédibilité institutionnelle et la confiance des parties prenantes.",
        "benefit_governance_title": "Gouvernance Structurée & Conformité Prête pour l'Audit :",
        "benefit_governance_body": "Les étapes de réception standardisées, la traçabilité des dossiers et la clarté des responsabilités réduisent les goulots d'étranglement.",
        "benefit_compliance_title": 'Garanties KYC & Prévention des Doublons :',
        "benefit_compliance_body": "Les vérifications d'entité structurées et le suivi documentaire limitent les soumissions en double et les écarts de conformité.",
        "entity_categories": ['Ministère / Agence Publique / Organisme Statutaire', 'Entreprise Publique / Service Public', 'Société Privée / Entreprise', 'Fondation à But Non Lucratif / Organisation de la Société Civile'],
        "hide_panel_label": 'Masquer le Panneau',
        "switch_to_about_org": "Passer à : À propos de l'Organisation",
        "switch_to_benefits": 'Passer à : Avantages Institutionnels Potentiels',
        "back_to_onboarding": "Retour à l'Intégration",
        "benefit_volume_title": 'Volume de Soumission Élargi & Potentiel de Génération de Revenus :',
        "benefit_volume_body": "En simplifiant la soumission numérique et en levant les barrières géographiques, les frais d'acheminement et les contraintes d'accès physique, le portail favorise une participation accrue des fournisseurs et renforce la concurrence.",
        "about_org_heading": 'À propos de NexusVault Digital Technology',
        "about_org_body": "<strong>NexusVault Digital Technology Company</strong> propose une plateforme de réception de propositions, de vérification de conformité et d'évaluation des offres avec une gouvernance structurée et une traçabilité prête pour l'audit.",
    },
    "de": {
        "country_reference_label": "L\u00e4nderreferenz",
        "language_reference_label": "Oberfl\u00e4chensprache",
        "language_label": "Sprache",
        "jurisdiction_label": "Rechtsraum",
        "currency_label": "W\u00e4hrung",
        "ids_label": "Gesetzliche Kennungen",
        "hero_subtitle": "Konfigurieren Sie den organisatorischen Rahmen und betreiben Sie ein transparentes, pr\u00fcfbares Angebots- und KYC-Portal.",
        "onboarding_step1_heading": "Schritt 1: Organisatorische Klassifizierung & Dom\u00e4neneinrichtung",
        "entity_category_label": "Organisations- / Rechtsformkategorie w\u00e4hlen*",
        "org_name_label": "Name der Organisationseinheit*",
        "benefits_button_label": "Potenzielle Institutionelle Vorteile",
        "about_org_button_label": "\u00dcber die Organisation",
        "benefits_heading": "Potenzielle Vorteile der NexusVault-Plattform f\u00fcr Institutionen",
        "benefit_reputation_title": "Gest\u00e4rkte Institutionelle Reputation & Digitale F\u00fchrung:",
        "benefit_reputation_body": "Ein transparentes digitales Vergabe- und Angebotsportal st\u00e4rkt die institutionelle Glaubw\u00fcrdigkeit sowie das Vertrauen von \u00d6ffentlichkeit und Anbietern.",
        "benefit_governance_title": "Strukturierte Governance & Pr\u00fcfungsbereitschaft:",
        "benefit_governance_body": "Standardisierte Pr\u00fcfphasen, nachvollziehbare Akten und klare Zust\u00e4ndigkeiten reduzieren Engp\u00e4sse im Pr\u00fcfprozess.",
        "benefit_compliance_title": "KYC-Schutz & Vermeidung von Dubletten:",
        "benefit_compliance_body": "Strukturierte Entit\u00e4tspr\u00fcftungen und Dokumentennachweise helfen, Mehrfacheinreichungen und Compliance-L\u00fccken zu vermeiden.",
        "entity_categories": [
            "Ministerium / Beh\u00f6rde / K\u00f6rperschaft des \u00f6ffentlichen Rechts",
            "Staatsunternehmen / \u00d6ffentlicher Versorger",
            "Privatunternehmen / Kapitalgesellschaft",
            "Stiftung / Gemeinn\u00fctzige Organisation",
        ],
        "hide_panel_label": 'Bereich ausblenden',
        "switch_to_about_org": 'Wechseln zu: Über die Organisation',
        "switch_to_benefits": 'Wechseln zu: Potenzielle Institutionelle Vorteile',
        "back_to_onboarding": 'Zurück zum Onboarding',
        "benefit_volume_title": 'Erhöhtes Anbietervolumen & Umsatzpotenzial:',
        "benefit_volume_body": 'Durch digitale Einreichung ohne geografische Hürden, hohe Versandkosten oder Zugangsbarrieren ermöglicht das Portal eine breitere Anbieterbeteiligung und stärkt den Wettbewerb.',
        "about_org_heading": 'Über NexusVault Digital Technology',
        "about_org_body": '<strong>NexusVault Digital Technology Company</strong> bietet Workflows für Angebotsannahme, Compliance-Prüfung und Vergabebewertung mit strukturierter Governance und lückenloser Nachvollziehbarkeit.',
    },
    "es": {
        "country_reference_label": "Referencia de Pa\u00eds",
        "language_reference_label": "Idioma Operativo",
        "jurisdiction_label": "Jurisdicci\u00f3n",
        "currency_label": "Moneda",
        "language_label": "Idioma",
        "ids_label": "Identificadores",
        "stage_gate_label": "Etapas de Licitaci\u00f3n",
        "hero_subtitle": "Configure el alcance organizacional y despliegue una puerta de propuestas y KYC auditable.",
        "onboarding_step1_heading": "Paso 1: Clasificaci\u00f3n Organizacional y Configuraci\u00f3n de Dominio",
        "entity_category_label": "Seleccionar Categor\u00eda de Organizaci\u00f3n / Entidad*",
        "org_name_label": "Nombre de la Entidad Organizacional*",
        "dispatch_email_label": "Correo Electr\u00f3nico Oficial de Despacho*",
        "phone_contact_label": "Tel\u00e9fono Oficial / Contacto de Pasarela SMS*",
        "hq_address_label": "Direcci\u00f3n de la Sede Institucional*",
        "admin_email_label": "Nodo de Notificaci\u00f3n Ejecutiva (Director General, Secretario, etc.)",
        "onboarding_step2_heading": "Paso 2: Identidad de Marca y T\u00edtulo del Portal",
        "custom_title_label": "T\u00edtulo Personalizado del Banner del Portal",
        "tier_label": "Nivel Soberano SaaS*",
        "logo_upload_label": "Subir Logotipo Institucional Oficial (PNG/JPG)",
    },
    "ar": {
        "country_reference_label": "\u0645\u0631\u062c\u0639 \u0627\u0644\u062f\u0648\u0644\u0629",
        "language_reference_label": "\u0644\u063a\u0629 \u0627\u0644\u0648\u0627\u062c\u0647\u0629",
        "jurisdiction_label": "\u0627\u0644\u0627\u062e\u062a\u0635\u0627\u0635 \u0627\u0644\u0642\u0636\u0627\u0626\u064a",
        "currency_label": "\u0627\u0644\u0639\u0645\u0644\u0629",
        "language_label": "\u0627\u0644\u0644\u063a\u0629",
        "ids_label": "\u0627\u0644\u0645\u0639\u0631\u0651\u0641\u0627\u062a",
        "stage_gate_label": "\u0645\u0631\u0627\u062d\u0644 \u0627\u0644\u0645\u0634\u062a\u0631\u064a\u0627\u062a",
        "hero_subtitle": "\u062a\u0647\u064a\u0626\u0629 \u0627\u0644\u0646\u0637\u0627\u0642 \u0627\u0644\u0645\u0624\u0633\u0633\u064a \u0648\u062a\u0634\u063a\u064a\u0644 \u0628\u0648\u0627\u0628\u0629 \u0634\u0641\u0627\u0641\u0629 \u0648\u0642\u0627\u0628\u0644\u0629 \u0644\u0644\u062a\u062f\u0642\u064a\u0642 \u0644\u0644\u0639\u0631\u0648\u0636 \u0648\u0627\u0644\u062a\u062d\u0642\u0642 \u0645\u0646 \u0627\u0644\u0647\u0648\u064a\u0629 KYC.",
        "onboarding_step1_heading": "\u0627\u0644\u062e\u0637\u0648\u0629 1: \u0627\u0644\u062a\u0635\u0646\u064a\u0641 \u0627\u0644\u0645\u0624\u0633\u0633\u064a \u0648\u0625\u0639\u062f\u0627\u062f \u0627\u0644\u0646\u0637\u0627\u0642",
        "entity_category_label": "\u0627\u062e\u062a\u0631 \u0641\u0626\u0629 \u0627\u0644\u0645\u0646\u0638\u0645\u0629 / \u0627\u0644\u0643\u064a\u0627\u0646*",
        "org_name_label": "\u0627\u0633\u0645 \u0627\u0644\u0643\u064a\u0627\u0646 \u0627\u0644\u0645\u0624\u0633\u0633\u064a*",
        "dispatch_email_label": "\u0627\u0644\u0628\u0631\u064a\u062f \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a \u0627\u0644\u0631\u0633\u0645\u064a \u0644\u0644\u0645\u0631\u0627\u0633\u0644\u0627\u062a*",
        "phone_contact_label": "\u0631\u0642\u0645 \u0627\u0644\u0647\u0627\u062a\u0641 \u0627\u0644\u0631\u0633\u0645\u064a / \u0628\u0648\u0627\u0628\u0629 \u0627\u0644\u0631\u0633\u0627\u0626\u0644 SMS*",
        "hq_address_label": "\u0639\u0646\u0648\u0627\u0646 \u0627\u0644\u0645\u0642\u0631 \u0627\u0644\u0631\u0626\u064a\u0633\u064a \u0644\u0644\u0645\u0624\u0633\u0633\u0629*",
        "admin_email_label": "\u062c\u0647\u0629 \u0627\u0644\u0625\u0634\u0639\u0627\u0631 \u0627\u0644\u062a\u0646\u0641\u064a\u0630\u064a\u0629 (\u0627\u0644\u0645\u062f\u064a\u0631 \u0627\u0644\u0639\u0627\u0645\u060c \u0627\u0644\u0623\u0645\u064a\u0646 \u0627\u0644\u0639\u0627\u0645\u060c \u0625\u0644\u062e.)",
        "onboarding_step2_heading": "\u0627\u0644\u062e\u0637\u0648\u0629 2: \u0627\u0644\u0647\u0648\u064a\u0629 \u0627\u0644\u0628\u0635\u0631\u064a\u0629 \u0648\u0639\u0646\u0648\u0627\u0646 \u0627\u0644\u0628\u0648\u0627\u0628\u0629 \u0627\u0644\u0645\u062e\u0635\u0635",
        "custom_title_label": "\u0639\u0646\u0648\u0627\u0646 \u0644\u0627\u0641\u062a\u0629 \u0627\u0644\u0628\u0648\u0627\u0628\u0629 \u0627\u0644\u0645\u062e\u0635\u0635",
        "tier_label": "\u0627\u0644\u0641\u0626\u0629 \u0627\u0644\u0633\u064a\u0627\u062f\u064a\u0629 SaaS*",
        "logo_upload_label": "\u0631\u0641\u0639 \u0627\u0644\u0634\u0639\u0627\u0631 \u0627\u0644\u0645\u0624\u0633\u0633\u064a \u0627\u0644\u0631\u0633\u0645\u064a (PNG/JPG)",
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

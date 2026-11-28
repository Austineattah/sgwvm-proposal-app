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
        "about_org_button_label": 'The Core Purpose of this Portal',
        "benefits_heading": 'Potential Benefits of the NexusVault Platform to Institutions',
        "benefit_reputation_title": 'Enhanced Organizational Reputation & Digital Leadership:',
        "benefit_reputation_body": 'Launching a transparent digital bidding and proposal portal elevates institutional credibility and builds public and vendor trust.',
        "benefit_governance_title": 'Structured Governance & Audit Readiness:',
        "benefit_governance_body": 'Standardized intake stages, traceable records, and clear accountability reduce bottlenecks across review teams.',
        "benefit_compliance_title": 'KYC & Anti-Duplication Safeguards:',
        "benefit_compliance_body": 'Automated entity checks and structured documentation help prevent duplicate submissions and compliance gaps.',
        "entity_categories": ['Public University / Polytechnic / Research Institute (Academic Sector)', 'Multinational Funder / UN Agency / International NGO (Humanitarian Sector)', 'National Assembly / Parliament / Legislative Directorate', 'Federal Ministry, Department, or Agency (MDA)', 'State Ministry, Department, or Agency (MDA)', 'Private Limited Company / Enterprise (Commercial Sector)', 'Non-Profit Foundation / Civil Society Organization'],
        "hide_panel_label": 'Hide Panel',
        "switch_to_about_org": 'Switch to: The Core Purpose of this Portal',
        "switch_to_benefits": 'Switch to: Potential Institutional Benefits',
        "back_to_onboarding": 'Back to Onboarding View',
        "benefit_volume_title": 'Expanded Vendor Volume & Revenue Generation Potential:',
        "benefit_volume_body": 'By simplifying digital submission and removing geographic barriers, heavy courier costs, and physical access hurdles, the portal enables broader domestic and international vendor participation from anywhere—increasing bidding volume, competitive tension, bid-security/application fee throughput, and revenue generation potential for the institution.',
        "benefit_transparency_title": 'Elimination of Collusion, Bid-Rigging & Off-Channel Leakage:',
        "benefit_transparency_body": 'Standardized sealed intake, timestamped submissions, and upfront published selection criteria reduce discretionary back-channeling, favoritism, and procurement leakage.<p style="color: #f8fafc; margin: 0 0 12px 0; line-height: 1.7;"><strong>Agentic AI Departmental Routing by Subject Heading:</strong> Automatically classifies and routes incoming proposals across the institution\'s departmental hierarchy based on subject headings—eliminating manual registry sorting, misdirected files, and administrative dispatch delays.</p><p style="color: #f8fafc; margin: 0 0 12px 0; line-height: 1.7;"><strong>Deterministic Bid-Integrity &amp; Commercial Schedule Auditing:</strong> Flags missing or expired compliance certificates, surfaces cross-bid beneficial-ownership or director overlaps, and audits Bill of Quantities (BoQ) figures for arithmetic mismatches and unit-price outliers before committee evaluation.</p><p style="color: #f8fafc; margin: 0 0 12px 0; line-height: 1.7;"><strong>Sovereign Multi-Tenant Isolation &amp; White-Label Autonomy:</strong> Provides each ministry, agency, legislature, university, NGO, or enterprise with a dedicated, isolated workspace, custom institutional branding, role-gated access, and 100% sovereign ownership of data, workflows, and audit trails.</p><p style="color: #f8fafc; margin: 0 0 12px 0; line-height: 1.7;"><strong>Multi-Jurisdictional &amp; Multi-Language Global Readiness:</strong> Supports Nigerian statutory and public-procurement alignment alongside adaptable country profiles, currencies, and multi-language interfaces for cross-border agencies, donor-backed programs, and international deployments.</p>',
        "about_org_heading": 'The Core Essence Of NexusVault AGENTIC AI PROPOSAL & KYC INTAKE PORTAL',
        "about_org_body": '<strong>NexusVault: Agentic AI Proposal &amp; KYC Intake Portal</strong> is a first-of-its-kind global portal designed to streamline how institutions receive solicited tenders and unsolicited proposals, verify entity identity and compliance (KYC), and conduct transparent evaluation from intake to award within a single, sovereign, and auditable gateway. Built with international governance standards and engineered with deep roots in Nigeria\'s public and institutional procurement landscape, the portal replaces what often takes weeks of manual review and heavy paperwork with a streamlined, verifiable digital workflow—simplified with automated intake, guided compliance checks, and clear audit trails.<br><br>Across both global and Nigerian operating environments, institutions face familiar vulnerabilities when proposal intake and vendor vetting rely on scattered emails, physical files, and disconnected spreadsheets: weeks lost to sorting documents and chasing missing records, inconsistent compliance checks, hidden conflicts of interest, and difficulty reconstructing how decisions were made. In Nigeria, where public and institutional stewardship demands strict alignment with Bureau of Public Procurement (BPP) principles, statutory entity credentials, and digital data-protection expectations, credibility depends on clear rules and verifiable proof at every stage. At the same time, cross-border agencies, donor-backed initiatives, and multi-jurisdictional enterprises require adaptable country profiles, clear multi-language interfaces, and standardized integrity controls that travel across borders without losing local compliance.<br><br>At the heart of the portal is an agentic AI and deterministic integrity workflow designed to streamline complex reviews while strengthening—never bypassing—institutional oversight. As proposals and KYC records enter the system, structured validation helps organize statutory and corporate credentials, flag missing items or expiries, surface potential beneficial-ownership or director overlaps across submissions, and highlight arithmetic or unit-price anomalies in commercial schedules. Evaluation committees and authorized administrators retain full decision authority, reviewing clear evidence, documented criteria, conflict-of-interest attestations, and immutable audit trails that protect fair competition, deter procurement leakage, and build lasting public and partner trust.<br><br>Institutions can participate directly by subscribing through the portal\'s structured onboarding lay-down process—configuring their jurisdiction, entity category, governance rules, and dedicated workspace step by step before going live. Whether used by a Nigerian ministry, agency, legislative body, or university—or adapted for international partners and multi-country deployments—the core purpose of this portal remains constant: to streamline what once took weeks of heavy paperwork and fragmented review into a transparent, defensible process where every proposal, every KYC check, and every evaluation milestone earns institutional trust.',
        "about_org_mission_title": 'Sovereign Procurement & Agentic AI Intelligence:',
        "about_org_mission_body": 'Replaces manual, paper-heavy intake and evaluation workflows with autonomous AI due diligence, structured compliance vetting, and objective committee scoring matrices.',
        "about_org_architecture_title": 'Sovereign Architecture & Multi-Tenant Isolation:',
        "about_org_architecture_body": 'Designed for government ministries, statutory agencies, public utilities, and enterprise tenants with isolated workspaces, localized statutory profiles, and role-gated execution.',
        "about_org_governance_title": 'Cryptographic Auditability & Transparent Awards:',
        "about_org_governance_body": 'Enforces upfront selection criteria, anti-tampering controls, documented committee award justifications, and end-to-end audit trails across every procurement stage.',
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
        "benefit_volume_body": "En simplifiant la soumission numérique et en levant les barrières géographiques, les frais d'acheminement et les contraintes d'accès physique, le portail favorise une participation élargie des fournisseurs d'où qu'ils soient—augmentant le volume des offres, l'intensité concurrentielle et le potentiel de génération de revenus pour l'institution.",
        "benefit_transparency_title": "Prévention de la Collusion, des Ententes & des Fuites Hors-Circuit :",
        "benefit_transparency_body": "La réception numérique horodatée, les procédures standardisées et la publication préalable des critères de sélection limitent les interventions discrétionnaires et les pertes de valeur.<p style=\"color: #f8fafc; margin: 0 0 12px 0; line-height: 1.7;\"><strong>Routage Départemental par IA Agentique selon l'Objet :</strong> Classe et oriente automatiquement les propositions entrantes au sein de la hiérarchie départementale selon leur intitulé d'objet—éliminant le tri manuel, les dossiers mal aiguillés et les retards de transmission.</p><p style=\"color: #f8fafc; margin: 0 0 12px 0; line-height: 1.7;\"><strong>Contrôle Déterministe de l'Intégrité des Offres &amp; Bordereaux :</strong> Signale les pièces manquantes ou expirées, détecte les recoupements de bénéficiaires effectifs ou d'administrateurs entre offres et audite les bordereaux (BoQ) pour repérer erreurs de calcul et écarts de prix unitaires avant l'évaluation.</p><p style=\"color: #f8fafc; margin: 0 0 12px 0; line-height: 1.7;\"><strong>Isolation Souveraine Multi-Locataires &amp; Autonomie en Marque Blanche :</strong> Offre à chaque ministère, agence, assemblée, université, ONG ou entreprise un espace isolé, une identité visuelle dédiée, des droits par rôle et une propriété souveraine à 100 % des données, flux et pistes d'audit.</p><p style=\"color: #f8fafc; margin: 0 0 12px 0; line-height: 1.7;\"><strong>Adaptabilité Multi-Juridictionnelle &amp; Multilingue à l'Échelle Mondiale :</strong> Allie l'alignement sur les exigences statutaires et des marchés publics au Nigeria à des profils pays adaptables, devises et interfaces multilingues pour les agences transfrontalières, programmes financés et déploiements internationaux.</p>",
        "about_org_heading": 'L\'Essence Fondamentale de NexusVault PORTAIL AGENTIQUE D\'IA POUR PROPOSITIONS & KYC',
        "about_org_body": '<strong>NexusVault : Portail Agentique d\'IA pour la Réception de Propositions et la Vérification KYC</strong> est une plateforme mondiale inédite conçue pour fluidifier la réception des appels d\'offres sollicités et des propositions non sollicitées, la vérification de l\'identité et de la conformité des entités (KYC) ainsi qu\'une évaluation transparente de la réception à l\'attribution au sein d\'un point d\'entrée unique, souverain et vérifiable. Conçu selon des standards internationaux de gouvernance et solidement ancré dans le contexte institutionnel et des marchés publics au Nigeria, le portail remplace des semaines d\'examen manuel et de lourde paperasse par un flux numérique structuré et vérifiable—simplifié par une réception automatisée, des contrôles de conformité guidés et des pistes d\'audit claires.<br><br>Dans les environnements mondiaux comme nigérians, les institutions rencontrent des failles connues lorsque la réception des dossiers et le contrôle des fournisseurs reposent sur des courriels dispersés, des dossiers physiques et des tableurs isolés : semaines perdues à trier des pièces et à relancer des documents manquants, vérifications inégales, conflits d\'intérêts masqués et difficulté à retracer les décisions. Au Nigeria, où la gestion publique et institutionnelle exige un alignement rigoureux sur les principes du Bureau of Public Procurement (BPP), les justificatifs statutaires et la protection des données, la crédibilité repose sur des règles claires et des preuves vérifiables à chaque étape. Parallèlement, les agences transfrontalières, initiatives financées par des bailleurs et entreprises multi-juridictionnelles ont besoin de profils pays adaptables, d\'interfaces multilingues et de contrôles d\'intégrité transférables sans sacrifier la conformité locale.<br><br>Au cour du portail se trouve un flux agentique d\'IA et de contrôle déterministe conçu pour simplifier les examens complexes tout en renforçant—sans jamais contourner—la supervision institutionnelle. A l\'arrivée des propositions et dossiers KYC, la validation structurée aide à organiser les justificatifs statutaires et d\'entreprise, signale les pièces manquantes ou expirées, détecte d\'éventuels recoupements de bénéficiaires effectifs ou d\'administrateurs et met en évidence les incohérences arithmétiques ou écarts de prix unitaires dans les bordereaux. Les comités d\'évaluation et administrateurs autorisés conservent l\'entière autorité décisionnelle, en s\'appuyant sur des preuves claires, des critères publiés, des attestations de conflit d\'intérêts et des pistes d\'audit immuables qui protègent la concurrence loyale, réduisent les fuites et renforcent la confiance.<br><br>Les institutions peuvent participer directement en souscrivant via le processus structuré d\'intégration et de paramétrage du portail—en configurant leur juridiction, leur catégorie d\'entité, leurs règles de gouvernance et leur espace dédié étape par étape avant la mise en service. Qu\'il soit utilisé par un ministère, une agence, un organe législatif ou une université au Nigeria—ou adapté à des partenaires internationaux et déploiements multi-pays—l\'objectif fondamental reste inchangé : transformer ce qui prenait autrefois des semaines de paperasse et d\'examen fragmenté en un processus transparent et défendable où chaque proposition, chaque contrôle KYC et chaque étape d\'évaluation mérite la confiance institutionnelle.',
        "about_org_mission_title": "Passation Souveraine & Intelligence Agentique :",
        "about_org_mission_body": "Remplace les processus manuels et papier par une vérification automatisée de la conformité, une diligence raisonnable assistée par IA et des matrices d'évaluation objectives pour les comités.",
        "about_org_architecture_title": "Architecture Souveraine & Isolation Multi-Locataires :",
        "about_org_architecture_body": "Conçu pour les ministères, organismes statutaires, services publics et entreprises avec des espaces isolés, des profils réglementaires localisés et des accès contrôlés par rôle.",
        "about_org_governance_title": "Auditabilité Cryptographique & Attributions Documentées :",
        "about_org_governance_body": "Impose la publication préalable des critères de sélection, des contrôles anti-altération, des justifications d'attribution motivées et une traçabilité complète à chaque étape."
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
        "benefit_volume_body": 'Durch digitale Einreichung ohne geografische Hürden, hohe Versandkosten oder Zugangsbarrieren ermöglicht das Portal eine breitere nationale und internationale Anbieterbeteiligung—und steigert so Angebotsvolumen, Wettbewerb sowie Gebühren- und Einnahmepotenzial der Institution.',
        "benefit_transparency_title": 'Schutz vor Kollusion, Absprachen & Kanalabweichungen:',
        "benefit_transparency_body": 'Zeitgestempelte digitale Eingänge, standardisierte Prüfpfade und vorab veröffentlichte Auswahlkriterien reduzieren Ermessensspielräume und Beschaffungsverluste.<p style="color: #f8fafc; margin: 0 0 12px 0; line-height: 1.7;"><strong>Agentisches KI-Abteilungsrouting nach Betreffzeile:</strong> Klassifiziert und leitet eingehende Angebote anhand ihrer Betreffzeile automatisch in die passende Abteilungshierarchie—und beseitigt manuelles Sortieren, Fehlzuweisungen und Verzögerungen bei der Weiterleitung.</p><p style="color: #f8fafc; margin: 0 0 12px 0; line-height: 1.7;"><strong>Deterministische Angebotsintegrität &amp; Leistungsverzeichnis-Prüfung:</strong> Markiert fehlende oder abgelaufene Nachweise, erkennt potenzielle Überschneidungen bei wirtschaftlich Berechtigten oder Geschäftsführern über Angebote hinweg und prüft Leistungsverzeichnisse auf Rechenfehler sowie Ausreißer bei Einheitspreisen vor der Bewertung.</p><p style="color: #f8fafc; margin: 0 0 12px 0; line-height: 1.7;"><strong>Souveräne Mandantentrennung &amp; White-Label-Autonomie:</strong> Stellt jedem Ministerium, jeder Behörde, jedem Legislativorgan, jeder Hochschule, NGO oder jedem Unternehmen einen isolierten Arbeitsbereich, eigenes Branding, rollengesteuerten Zugriff und 100 % souveränes Eigentum an Daten, Abläufen und Audit-Trails bereit.</p><p style="color: #f8fafc; margin: 0 0 12px 0; line-height: 1.7;"><strong>Multi-Jurisdiktionelle &amp; Mehrsprachige Weltweite Einsatzfähigkeit:</strong> Verbindet die Ausrichtung auf nigerianische Vorgaben und Vergabeprinzipien mit anpassbaren Länderprofilen, Währungen und mehrsprachigen Oberflächen für grenzüberschreitende Stellen, geberfinanzierte Vorhaben und internationale Einsätze.</p>',
        "about_org_heading": 'Der Kern von NexusVault AGENTISCHES KI-PORTAL FÜR ANGEBOTE & KYC-PRÜFUNG',
        "about_org_body": '<strong>NexusVault: Agentisches KI-Portal für Angebotsannahme &amp; KYC-Prüfung</strong> ist ein weltweit neuartiges Portal, das die Annahme öffentlicher Ausschreibungen und unaufgeforderter Angebote, die Prüfung von Identität und Compliance (KYC) sowie eine transparente Bewertung von der Einreichung bis zur Vergabe in einem einzigen, souveränen und prüfbaren Zugang bündelt. Entwickelt nach internationalen Governance-Standards und tief verankert im institutionellen Beschaffungsumfeld Nigerias ersetzt das Portal oft wochenlange manuelle Prüfungen und schwere Papierarbeit durch einen strukturierten, nachvollziehbaren digitalen Ablauf—vereinfacht durch automatisierte Annahme, geführte Compliance-Prüfungen und klare Audit-Trails.<br><br>Sowohl im globalen als auch im nigerianischen Umfeld entstehen Risiken, wenn Angebotseingang und Lieferantenprüfung über E-Mails, Aktenordner und getrennte Tabellen verstreut sind: Wochen gehen durch das Sortieren von Unterlagen und Nachfordern fehlender Nachweise verloren, Prüfungen fallen uneinheitlich aus, Interessenkonflikte bleiben verborgen und Entscheidungen sind schwer nachvollziehbar. In Nigeria, wo öffentliche und institutionelle Verantwortung eine strikte Ausrichtung an den Grundsätzen des Bureau of Public Procurement (BPP), gesetzliche Nachweise und Datenschutz verlangt, hängt Glaubwürdigkeit von klaren Regeln und prüfbaren Belegen in jeder Phase ab. Zugleich benötigen grenzüberschreitende Organisationen, geberfinanzierte Vorhaben und international tätige Unternehmen anpassbare Länderprofile, mehrsprachige Oberflächen und einheitliche Integritätsprüfungen ohne Verlust lokaler Konformität.<br><br>Im Kern des Portals arbeitet ein Zusammenspiel aus agentischer KI und deterministischen Integritätsprüfungen, das komplexe Prüfungen vereinfacht und die institutionelle Aufsicht stärkt—statt sie zu umgehen. Beim Eingang von Angeboten und KYC-Daten hilft eine strukturierte Validierung dabei, gesetzliche und gesellschaftsrechtliche Nachweise zu ordnen, fehlende oder abgelaufene Dokumente zu markieren, potenzielle Überschneidungen bei wirtschaftlich Berechtigten oder Geschäftsführern zwischen Angeboten zu erkennen sowie Rechenfehler oder Ausreißer bei Einheitspreisen in Leistungsverzeichnissen hervorzuheben. Bewertungskomitees und befugte Administratoren behalten die volle Entscheidungsgewalt auf Basis klarer Nachweise, veröffentlichter Kriterien, Interessenkonflikt-Erklärungen und unveränderlicher Audit-Trails, die fairen Wettbewerb schützen, Abflüsse eindämmen und Vertrauen sichern.<br><br>Institutionen können direkt teilnehmen, indem sie sich über den strukturierten Onboarding-Prozess des Portals anmelden und Jurisdiktion, Organisationskategorie, Governance-Regeln sowie ihren eigenen Arbeitsbereich Schritt für Schritt vor dem Livegang einrichten. Ob durch ein Ministerium, eine Behörde, ein Legislativorgan oder eine Universität in Nigeria—oder angepasst für internationale Partner und länderübergreifende Einsätze—der Kernzweck dieses Portals bleibt konstant: das, was früher wochenlange Papierarbeit und zersplitterte Prüfungen erforderte, in einen transparenten, belastbaren Prozess zu überführen, in dem jedes Angebot, jede KYC-Prüfung und jeder Bewertungsmeilenstein institutionelles Vertrauen verdient.',
        "about_org_mission_title": 'Sou­veräne Beschaffung & Agentenbasierte KI:',
        "about_org_mission_body": 'Ersetzt manuelle, papierintensive Abläufe durch automatisierte Compliance-Prüfungen, KI-gestützte Due Diligence und objektive Bewertungsmatrizen für Vergabegremien.',
        "about_org_architecture_title": 'Sou­veräne Architektur & Mandantentrennung:',
        "about_org_architecture_body": 'Entwickelt für Ministerien, Behörden, öffentliche Versorger und Unternehmen mit getrennten Mandantenbereichen, länderspezifischen Vorgaben und rollenbasiertem Zugriff.',
        "about_org_governance_title": 'Kryptografische Nachvollziehbarkeit & Begründete Zuschläge:',
        "about_org_governance_body": 'Sichert die Vorabveröffentlichung von Auswahlkriterien, Manipulationsschutz, dokumentierte Zuschlagsbegründungen und lückenlose Prüfpfade über alle Vergabephasen hinweg.'
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

"""
NexusVault Executive Training & Developer Console Knowledge Base (src/developer_kb.py)
Comprehensive Q&A reference library for live seminar briefings and stakeholder demonstrations.
"""

NEXUSVAULT_EXECUTIVE_KB = {
    "Committee Evaluation Workspace": {
        "category": "Security & Governance",
        "tenant_context": "Tenant Workspace: /tenant/gov_procurement_hq_99a",
        "status_badge": "SECURE CRYPTOGRAPHIC GATING ACTIVE",
        "summary": "Secure, role-based digital command center where statutory evaluation panels and desk officers vet, score, and process public sector bids.",
        "qa_pairs": [
            {
                "question": "Who generates and assigns committee access tokens?",
                "answer": (
                    "The authorized tenant executive provisions the committee roster and issues "
                    "signed access tokens from the tenant's Executive Management workspace. "
                    "The Head of Administration may perform this task when authorized for that "
                    "workspace. The application scopes roster and tender checks to the tenant."
                )
            },
            {
                "question": "What is the operational workflow for committee evaluation?",
                "answer": (
                    "1. **Committee Constitution:** Head of Administration accesses the Committee Management module.\n"
                    "2. **Member Profile Input:** Enter the evaluator's official name, official government/corporate email, "
                    "and select the target procurement tender batch.\n"
                    "3. **Cryptographic Signing:** Upon clicking 'Issue Access Token', the backend programmatically generates "
                    "an HMAC-SHA256 signed token binding the member's identity to their specific `tenant_id` and `tender_id`.\n"
                    "4. **Secure Dispatch:** The executive copies the displayed token and distributes it "
                    "securely to the evaluator; the issuance screen does not send it by email."
                )
            },
            {
                "question": "Are committee tokens permanent or lifecycle-long?",
                "answer": (
                    "Signed tokens are time-bound and tied to a tenant, tender and evaluator. "
                    "Issuance currently uses a 14-day default. The evaluation workspace also "
                    "requires an active tender and current roster membership on access and "
                    "revalidation; closing the tender blocks workspace access even if the token "
                    "has not expired. The signed-token sandbox does not perform those roster and "
                    "active-tender checks. Individual signed-token revocation is not currently "
                    "available."
                )
            },
            {
                "question": "Executive Committee Access Generation",
                "answer": (
                    "1. An authorized Head of Administration opens the tenant's Executive "
                    "Management workspace and provisions the committee roster.  \n"
                    "2. The system generates high-entropy roster credentials with "
                    "secrets.token_urlsafe(32), exceeding 16 characters, and stores them "
                    "encrypted for the active tenant.  \n"
                    "3. Copy and distribute credentials securely; plaintext credentials are "
                    "available only in the current Streamlit session. Signed tender tokens "
                    "are issued separately from the same workspace. The Developer Console "
                    "does not currently provide this committee-provisioning control."
                )
            },
            {
                "question": "Tender Review Committee Provisioning",
                "answer": (
                    "1. Select a current roster member and an active published tender in the "
                    "tenant's committee provisioning section.  \n"
                    "2. Issue a signed token bound to the evaluator's email, tenant and tender; "
                    "the current issuance default is 14 days.  \n"
                    "3. The evaluation workspace checks the active tender and roster again on "
                    "access and reruns. Closing the tender prevents workspace use, but does not "
                    "change the token's expiry or revoke it in the separate signed-token sandbox."
                )
            },
            {
                "question": "Mandatory Password Rotation Policy",
                "answer": (
                    "Before each major procurement review window, administrators should rotate "
                    "relevant credentials and securely distribute replacements. Re-provisioning "
                    "a roster replaces all members and resets COI state; rotating "
                    "DOSSIER_ENCRYPTION_KEY invalidates all existing signed committee tokens "
                    "and requires coordinated reissuance.  \n"
                    "This is an operational policy, not an automatically enforced rotation "
                    "schedule. The current security audit table is tenant_audit_logs, not "
                    "security_audit_events; token issuance and login attempts are recorded "
                    "there, but key rotation is not automatically recorded. Track rotation "
                    "through the organization's approved audit process."
                )
            },
            {
                "question": "Immediate Token Revocation",
                "answer": (
                    "1. Report a suspected compromise to the authorized platform administrator "
                    "and close the affected tender if evaluation access must be stopped.  \n"
                    "2. For immediate invalidation of signed committee tokens, rotate "
                    "DOSSIER_ENCRYPTION_KEY in the deployment configuration and securely "
                    "reissue tokens. This affects every token signed with the old key, not just "
                    "the compromised token.  \n"
                    "3. Ask active users to lock or sign out; the evaluation workspace clears its "
                    "cached authentication state when revalidation fails on a rerun. Streamlit "
                    "session state is not a cache stored in nexus_sovereign.db, and there is "
                    "currently no per-token signed-token revocation control or database-wide "
                    "session purge."
                )
            },
            {
                "category": "Committee Security & Access Management",
                "question": "What is the Committee Evaluation Workspace and what are its core functions?",
                "answer": (
                    "The Committee Evaluation Workspace is the secure, role-based digital command center within "
                    "NexusVault where statutory evaluation panels, administrative desk officers, and review "
                    "committees vet, score, and process incoming public sector proposals and contractor bids.\n\n"
                    "Because public procurement handles sensitive financial bids, corporate credentials, and statutory "
                    "compliance documents, this workspace operates behind strict security layers (such as Fernet "
                    "dossier encryption and Row-Level Security).\n\n"
                    "**Core Functions of the Committee Workspace:**\n"
                    "1. **Encrypted Dossier Review:** Authorized committee members use secure access tokens to decrypt "
                    "and examine full contractor proposal dossiers (technical specs, financial bids, and track record "
                    "portfolios) without exposing sensitive data to unauthorized viewers.\n"
                    "2. **Standardized Scoring & Compliance Auditing:** Provides structured evaluation matrices where "
                    "committee members grade submissions against public procurement standards (such as BPP and ICRC guidelines), "
                    "checking for tax compliance, corporate registration, and past performance.\n"
                    "3. **The Bridge to Contract Award:** Once a winning contractor is selected and approved within this workspace, "
                    "the system transitions the record into the Post-Award Verification Matrix, allowing the Head of "
                    "Administration to lock in project milestones, timelines, and phase-by-phase execution tracking.\n"
                    "4. **Immutable Audit Trails:** Every review, score, sign-off, or rejection made inside the workspace is "
                    "permanently logged in the system's audit trail (`tenant_audit_logs`) to ensure complete transparency, "
                    "accountability, and protection against administrative tampering or fraud.\n\n"
                    "In short, it is the secure internal engine that turns raw contractor submissions into legally vetted, "
                    "trackable public projects."
                )
            }
        ]
    },
    "Slug-Based Tenant Routing": {
        "category": "Architecture & Scoping",
        "tenant_context": "Tenant Workspace: /tenant/slug_isolation_engine",
        "status_badge": "ZERO SESSION BLEED ACTIVE",
        "summary": "Dynamic workspace isolation using URL query parameters (?tenant=slug) to scope tenant sessions without schema alterations.",
        "qa_pairs": [
            {
                "question": "How does slug-based routing protect tenant data isolation?",
                "answer": (
                    "By parsing URL query parameters (`?tenant=slug`), the platform automatically scopes all database "
                    "transactions to that specific organization's context. Master admin oversight tabs are completely "
                    "stripped out when viewing a client tenant slug, ensuring zero session-state bleed between master admin "
                    "views and client tenant workspaces."
                )
            },
            {
                "question": "What happens immediately after a client tenant completes onboarding?",
                "answer": (
                    "The routing engine routes them directly into their tenant-scoped workspace (`/tenant/{slug}`), "
                    "rendering identical layouts to the core enterprise portal while enforcing RLS isolation via existing database adapters."
                )
            }
        ]
    },
    "Tenant Lifecycle State Machine": {
        "category": "Lifecycle Management",
        "tenant_context": "Tenant Workspace: /tenant/lifecycle_engine",
        "status_badge": "IMMUTABLE STATE MACHINE VERIFIED",
        "summary": "Immutable state transition engine managing tenant onboarding progression from trial creation to active subscription or expiration.",
        "qa_pairs": [
            {
                "question": "What are the core states in the NexusVault tenant lifecycle?",
                "answer": (
                    "- **PENDING_ACTIVATION:** Onboarding completed, awaiting developer console review.\n"
                    "- **PAYMENT_PENDING:** Tenant clicked 'YES' to commence subscription; awaiting commercial payment gateway verification.\n"
                    "- **DEMO_ACTIVE:** Tenant clicked 'LATER'; temporary trial window assigned with slug reference.\n"
                    "- **SUBSCRIBED / ACTIVATED:** Manual override by Lead Architect or payment confirmation granted; full enterprise access.\n"
                    "- **EXPIRED:** Trial window or subscription lapsed without payment acknowledgment."
                )
            },
            {
                "question": "How does the Resume Login engine handle returning tenants?",
                "answer": (
                    "Tenants using 'Already Have an Account' can look up their workspace via **Tenant Email** or **Slug Reference**. "
                    "If status is `PAYMENT_PENDING` or `EXPIRED`, they are routed straight to commercial checkout. "
                    "If `DEMO_ACTIVE` or `SUBSCRIBED`, they enter their administrative dashboard directly."
                )
            }
        ]
    },
    "Conditional Vendor Activation": {
        "category": "Procurement Gating",
        "tenant_context": "Tenant Workspace: /tenant/vendor_compliance_gate",
        "status_badge": "COMPLIANCE GATING ENFORCED",
        "summary": "Administrative compliance gate ensuring solicited and unsolicited vendors cannot upload proposals until formally activated.",
        "qa_pairs": [
            {
                "question": "How is vendor activation enforced across portals?",
                "answer": (
                    "The system performs a strict database check (`is_activated == True`). If an internal admin officer has not "
                    "conditionally activated the vendor record, proposal upload forms are blocked and a pending compliance "
                    "status banner is displayed in accordance with NDPA/NITDA guidelines."
                )
            }
        ]
    },
    "Developer Console & Expiry Cron Watchdog": {
        "category": "Master Administration",
        "tenant_context": "Sovereign Master Node: /dev/console/admin",
        "status_badge": "RESTRICTED EXECUTIVE ACCESS",
        "summary": "Exclusive administrative command center for Lead Architect / CEO Augustine Attah to manage activations, trials, and automated alerts.",
        "qa_pairs": [
            {
                "question": "What master controls are available in the Developer Console?",
                "answer": (
                    "- **Manual Activation Override:** Master toggle (`GRANT ACTIVATION` / `REVOKE ACCESS`) setting `is_activated = True` in `nv_tenants`.\n"
                    "- **Trial Duration Assignment:** Numerical input to assign custom trial windows (e.g., 7, 14, 30 days).\n"
                    "- **5-Day Expiry Cron Watchdog:** Daily background scan checking `demo_expires_at` against current time, dispatching urgent email/portal warnings when remaining days are <= 5."
                )
            }
        ]
    },
    "🛡️ NEXUSVAULT TECHNOLOGIES: Super Intelligence — Agentic AI Proposal Intake & Governance Portal": {
        "category": "Executive Platform Briefing",
        "tenant_context": "Sovereign Executive Briefing",
        "status_badge": "EXECUTIVE KNOWLEDGE BASE",
        "summary": "Executive documentation for the NexusVault proposal intake and governance portal.",
        "qa_pairs": [],
        "documentation": """### 🛡️ NEXUSVAULT TECHNOLOGIES
**Super Intelligence — Agentic AI Proposal Intake & Governance Portal**

The **NexusVault Super Intelligence Portal** is an autonomous, enterprise-grade proposal intake, compliance vetting, and procurement governance engine. Engineered for organizations managing high-stakes solicited tenders and unsolicited commercial bids, NexusVault replaces fragmented manual reviews with an **AI-orchestrated, zero-trust evaluation pipeline**—accelerating decision cycles from weeks to minutes while enforcing strict institutional governance.

#### Core Functional Architecture

1. **Autonomous Agentic AI Evaluation & Intelligent Routing**
   - **Deep Semantic & Technical Auditing:** Autonomous AI agents ingest and dissect complex proposal documents—evaluating technical feasibility, scope alignment, regulatory compliance, and financial viability against defined benchmarks.
   - **Proactive Anomaly & Gap Detection:** Automatically flags missing contractual clauses, budget discrepancies, and structural omissions before human reviewers invest a single minute.
   - **Dynamic Hierarchical Departmental Routing:** Eliminates manual triage. The Agentic AI identifies the operational domain of every incoming submission and routes it directly into the dedicated workspace of the responsible departmental lead based on organizational role hierarchies.

2. **Dual-Layer Governance: Departmental Flow vs. Exclusive Tender Committee**
   - **Layer 1 — Hierarchical Departmental Workspaces:** Specialized department heads and technical leads review AI-enriched dossiers tailored strictly to their operational mandate, providing domain-level validation.
   - **Layer 2 — Exclusive Tender Committee:** An isolated, high-governance oversight chamber equipped with standardized scoring matrices, compliance gates, and executive audit controls to authorize final approvals and post-award verification.

3. **Dual-Track Vendor Intake Engine (Solicited & Unsolicited)**
   - **Solicited Procurement Workflows:** Purpose-built for formal Requests for Proposals (RFPs) and structured bidding cycles, enforcing strict pre-qualification rules, submission deadlines, and fixed budgetary ceilings.
   - **Unsolicited Innovation Pathways:** Provides a controlled, high-integrity intake gateway for external innovators, contractors, and strategic partners to submit spontaneous technical blueprints and commercial bids.

4. **Automated KYC & Zero-Trust Vendor Compliance Vetting**
   - **Entity & Credential Verification:** Validates corporate registration, tax compliance, ownership structures, and operational licenses prior to evaluation.
   - **Pre-Evaluation Risk Scoring:** Assigns automated vendor risk profiles to screen out non-compliant or unverified entities at the perimeter.

5. **Direct Mobile-First Onboarding & QR Chain-of-Custody**
   - **Frictionless Direct Submission:** Vendors and applicants onboard and submit directly from mobile or desktop browsers without middleman bottlenecks.
   - **Cryptographic QR Tracking:** Every validated submission is issued a unique, scannable **QR tracking credential**, establishing an unbroken chain of custody across every review milestone.

6. **Multi-Tenant Enterprise Isolation & Anti-Duplication Integrity**
   - **Strict Tenant Partitioning:** Enforces hard data isolation across independent organizations, subsidiaries, or directorates operating on the platform.
   - **Automated Anti-Duplication Controls:** Database-level uniqueness triggers block duplicate bids, overlapping vendor submissions, and redundant processing across active cycles.

#### Enterprise Security & Performance Foundation (Technical Annex)
- **End-to-End Cryptographic Protection:** Sensitive credentials and configuration layers are protected via symmetric encryption alongside strictly gated administrative and developer boundaries.
- **Tamper-Evident Audit Trails:** Every AI routing decision, committee score, and status transition is permanently written to immutable activity logs for full regulatory auditability.
- **High-Throughput Architecture:** Engineered with selective view rendering and index-backed pagination to guarantee sub-second responsiveness under heavy concurrent enterprise workloads.""",
    }
}

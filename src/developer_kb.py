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
                    "Tokens are generated and assigned by the **Head of Administration** "
                    "(or designated Procurement Officer) of that specific ministry or public organization "
                    "within the authenticated Enterprise Portal. For initial system bootstrapping or master overrides, "
                    "the Lead Architect / CEO (Augustine Attah) can also manage these via the Developer Console "
                    "under strict Row-Level Security (RLS) boundaries."
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
                    "4. **Secure Dispatch:** The system dispatches the secure login link/token directly to the evaluator's official email."
                )
            },
            {
                "question": "Are committee tokens permanent or lifecycle-long?",
                "answer": (
                    "**Strictly time-bound and task-specific—never lifecycle-long.** Making a committee token permanent "
                    "would introduce severe security vulnerabilities (insider threats or leaked credentials). "
                    "Instead, NexusVault enforces:\n"
                    "- **Tender-Specific Duration:** Configured to expire in 7 to 14 days, matching statutory procurement windows.\n"
                    "- **Automatic Expiration:** Invalidates automatically once the review concludes or countdown hits zero.\n"
                    "- **Manual Revocation:** Head of Administration can instantly revoke tokens at any time."
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
    }
}

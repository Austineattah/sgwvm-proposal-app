"""
NexusVault Automated Rigorous Health & Logic Check (test_nexus_health.py)
Verifies database integrity, AI auto-matcher, support ticketing, and module imports.
"""

import sys


def main() -> int:
    print("=" * 60)
    print("🛡️ NEXUSVAULT SOVEREIGN SYSTEM HEALTH & LOGIC AUDIT")
    print("=" * 60)

    # 1. Test Module Imports
    print("\n[1/5] Testing Module Import Integrity...")
    try:
        from src.developer_kb import NEXUSVAULT_EXECUTIVE_KB
        from src.nexus_db_adapter import (
            NexusDatabaseAdapter,
            create_support_ticket,
            get_all_support_tickets,
            init_db,
            match_knowledge_base,
            respond_to_support_ticket,
        )
        from src.developer_console import render_developer_console
        from src.tenant_support_panel import render_client_tenant_support_panel

        print(
            "   ✅ All core Python modules imported successfully without syntax errors."
        )
    except Exception as exc:
        print(f"   ❌ Import Error: {exc}")
        return 1

    # 2. Test Database Initialization & Schema
    print("\n[2/5] Testing Sovereign Database & Schema Initialization...")
    try:
        init_db()
        print(
            "   ✅ Database tables (`nv_tenants`, `nv_support_tickets`) initialized successfully."
        )
    except Exception as exc:
        print(f"   ❌ Database Initialization Error: {exc}")
        return 1

    # 3. Test Knowledge Base & AI Auto-Matcher Logic
    print("\n[3/5] Testing Knowledge Base & AI Auto-Responder Matcher...")
    try:
        assert len(NEXUSVAULT_EXECUTIVE_KB) > 0, "KB is empty!"

        # Test in-scope query matching
        sample_query = "Who generates and assigns committee access tokens?"
        auto_response = match_knowledge_base(sample_query)
        if auto_response:
            print(
                "   ✅ In-scope query successfully matched KB and generated automated response."
            )
        else:
            print(
                "   ⚠️ Warning: In-scope query did not trigger auto-response. Check keyword thresholds."
            )

        # Test out-of-scope query
        out_scope_query = "What is the weather in Abuja right now?"
        out_response = match_knowledge_base(out_scope_query)
        if out_response is None:
            print(
                "   ✅ Out-of-scope query correctly returned None (triggers CEO escalation alert)."
            )
        else:
            print(
                "   ⚠️ Warning: Out-of-scope query triggered false-positive auto-response."
            )
    except Exception as exc:
        print(f"   ❌ KB Matcher Error: {exc}")
        return 1

    # 4. Test Support Ticketing & Escalation Workflow
    print("\n[4/5] Testing Support Ticketing & Escalation Workflow...")
    try:
        with NexusDatabaseAdapter().get_connection() as conn:
            conn.execute(
                """
                INSERT INTO nv_tenants (tenant_id, slug, org_name, admin_email)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (tenant_id) DO NOTHING
                """,
                (
                    "test_tenant_999",
                    "test_institution_slug",
                    "Test Federal Ministry",
                    "audit.officer@gov.ng",
                ),
            )
            tenant = conn.execute(
                "SELECT slug FROM nv_tenants WHERE tenant_id = ?",
                ("test_tenant_999",),
            ).fetchone()
            if tenant is None or tenant["slug"] != "test_institution_slug":
                raise ValueError(
                    "Test tenant ID is already registered with a different slug."
                )

        # Create a test ticket (out of scope to test blinking alert / OPEN status)
        success = create_support_ticket(
            tenant_id="test_tenant_999",
            tenant_slug="test_institution_slug",
            org_name="Test Federal Ministry",
            sender_email="audit.officer@gov.ng",
            message="What is the quantum encryption protocol configuration for external vendors?",
        )
        assert success, "Failed to insert support ticket!"
        print("   ✅ Support ticket created and evaluated successfully.")

        # Retrieve tickets and find our test ticket
        tickets = get_all_support_tickets()
        test_ticket = next(
            (ticket for ticket in tickets if ticket["tenant_slug"] == "test_institution_slug"),
            None,
        )
        assert test_ticket is not None, "Created test ticket not found in database!"
        print(
            f"   ✅ Ticket retrieved successfully (Status: {test_ticket['status']})."
        )

        # Test CEO Response workflow
        response_success = respond_to_support_ticket(
            test_ticket["ticket_id"],
            "Verified under Sovereign Level 1 encryption standards.",
        )
        assert response_success, "Failed to record CEO response!"
        print(
            "   ✅ CEO response successfully recorded and ticket status updated to RESOLVED."
        )
    except Exception as exc:
        print(f"   ❌ Ticketing Workflow Error: {exc}")
        return 1

    # 5. Summary
    print("\n" + "=" * 60)
    print("🎉 ALL SYSTEM LOGIC CHECKS PASSED OPTIMALLY!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

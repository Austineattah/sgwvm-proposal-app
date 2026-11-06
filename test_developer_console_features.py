import hashlib
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import database
from cryptography.fernet import Fernet, InvalidToken


class DeveloperConsoleDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "console.db"
        self.database_patch = patch.object(database, "DB_FILE", self.database_path)
        self.database_patch.start()
        database.init_db()
        database.save_tenant(
            {
                "tenant_slug": "example_tenant",
                "full_corporation_name": "Example Tenant",
                "status": "Pending",
            }
        )

    def tearDown(self):
        self.database_patch.stop()
        self.temporary_directory.cleanup()

    def test_existing_tenant_schema_migrates_lifecycle_columns(self):
        legacy_path = Path(self.temporary_directory.name) / "legacy.db"
        connection = sqlite3.connect(legacy_path)
        try:
            connection.execute(
                """
                CREATE TABLE tenants (
                    tenant_slug TEXT PRIMARY KEY,
                    full_corporation_name TEXT,
                    institution_category TEXT,
                    apex_title TEXT,
                    sub_directorates_json TEXT,
                    logo_path TEXT,
                    status TEXT
                )
                """
            )
            connection.execute(
                "INSERT INTO tenants (tenant_slug, status) VALUES (?, ?)",
                ("legacy_tenant", "Pending"),
            )
            connection.commit()
        finally:
            connection.close()

        with patch.object(database, "DB_FILE", legacy_path):
            database.init_db()
            tenant = database.get_tenant_by_slug("legacy_tenant")

        self.assertEqual(tenant["status"], "Pending")
        self.assertEqual(tenant["is_deleted"], 0)
        self.assertIsNone(tenant["deleted_at"])
        self.assertIsNone(tenant["activated_at"])

    def test_vendor_activation_does_not_change_clearance_status(self):
        database.create_clearance_pass(
            {
                "qr_pass_id": "pass-example",
                "tenant_slug": "example_tenant",
                "rfq_code": "RFP-1",
                "vendor_name": "Example Vendor",
                "email": "vendor@example.test",
                "payment_reference": "payment-1",
                "proposal_title": "Example proposal",
                "clearance_status": "PAYMENT_VERIFIED",
            }
        )
        vendor = database.list_vendors()[0]

        self.assertTrue(database.activate_vendor(vendor["vendor_slug"]))
        self.assertEqual(database.list_vendors()[0]["status"], "Active")
        self.assertEqual(
            database.get_clearance_pass("pass-example", "example_tenant")[
                "clearance_status"
            ],
            "PAYMENT_VERIFIED",
        )

    def test_tenant_access_attempts_are_logged_without_secrets(self):
        database.log_tenant_access_attempt("example_tenant", "staff", True)
        database.log_tenant_access_attempt("example_tenant", "executive", False)

        logs = database.list_admin_access_logs("example_tenant")
        self.assertEqual(
            [row["action"] for row in logs],
            [
                "executive_access_key_rejected",
                "staff_access_key_accepted",
            ],
        )
        self.assertEqual(
            {row["actor"] for row in logs},
            {"tenant_access_key"},
        )
        with self.assertRaises(ValueError):
            database.log_tenant_access_attempt(
                "example_tenant",
                "platform",
                True,
            )

    def test_terminal_lockouts_are_persistent_and_role_scoped(self):
        self.assertEqual(
            database.get_tenant_role_lockout("example_tenant", "front_desk")[
                "failed_attempts"
            ],
            0,
        )
        for expected_attempts in (1, 2):
            state = database.record_tenant_role_login_failure(
                "example_tenant",
                "admin",
            )
            self.assertEqual(state["failed_attempts"], expected_attempts)
            self.assertFalse(state["is_locked_out"])

        self.assertFalse(
            database.get_tenant_role_lockout("example_tenant", "front_desk")[
                "is_locked_out"
            ]
        )
        locked_state = database.record_tenant_role_login_failure(
            "example_tenant",
            "admin",
        )
        self.assertEqual(locked_state["failed_attempts"], 3)
        self.assertTrue(locked_state["is_locked_out"])
        self.assertIsNotNone(locked_state["locked_out_at"])

        repeated_failure = database.record_tenant_role_login_failure(
            "example_tenant",
            "admin",
        )
        self.assertEqual(repeated_failure["failed_attempts"], 3)
        self.assertTrue(
            database.get_tenant_role_lockout("example_tenant", "admin")[
                "is_locked_out"
            ]
        )
        self.assertFalse(
            database.get_tenant_role_lockout("example_tenant", "front_desk")[
                "is_locked_out"
            ]
        )

    def test_terminal_lockout_clears_after_success_or_audited_admin_reset(self):
        database.record_tenant_role_login_failure("example_tenant", "front_desk")
        database.record_tenant_role_login_failure("example_tenant", "front_desk")
        self.assertTrue(
            database.record_tenant_role_login_success(
                "example_tenant",
                "front_desk",
            )
        )
        self.assertEqual(
            database.get_tenant_role_lockout("example_tenant", "front_desk")[
                "failed_attempts"
            ],
            0,
        )

        for _ in range(3):
            state = database.record_tenant_role_login_failure(
                "example_tenant",
                "front_desk",
            )
        self.assertTrue(state["is_locked_out"])

        database.reset_tenant_role_login_lockout(
            "example_tenant",
            "front_desk",
            "master_admin_recovery_key",
        )
        reset_state = database.get_tenant_role_lockout(
            "example_tenant",
            "front_desk",
        )
        self.assertEqual(reset_state["failed_attempts"], 0)
        self.assertFalse(reset_state["is_locked_out"])
        self.assertIsNone(reset_state["locked_out_at"])
        audit_logs = database.get_tenant_activities("example_tenant")
        self.assertEqual(audit_logs[0]["action_type"], "terminal_auth_lockout_reset")

    def test_onboarding_persists_tenant_logo_path(self):
        tenant = database.create_tenant_onboarding(
            {
                "tenant_slug": "branded_tenant",
                "full_corporation_name": "Branded Tenant",
                "admin_email": "admin@example.test",
                "admin_phone": "+2348000000000",
                "logo_path": "branded_tenant.png",
            }
        )

        self.assertEqual(tenant["full_corporation_name"], "Branded Tenant")
        self.assertEqual(tenant["logo_path"], "branded_tenant.png")
        self.assertEqual(
            database.get_tenant_by_slug("branded_tenant")["logo_path"],
            "branded_tenant.png",
        )
        pending = database.get_tenant_by_slug("branded_tenant")
        self.assertEqual(pending["status"], "Pending Activation")
        contact = database.get_tenant_activation_contact("branded_tenant")
        self.assertEqual(contact["admin_email"], "admin@example.test")
        self.assertEqual(contact["admin_phone"], "+2348000000000")
        activated = database.activate_tenant("branded_tenant")
        self.assertEqual(activated["status"], "Active")
        self.assertEqual(activated["admin_email"], "admin@example.test")
        self.assertIsNone(database.activate_tenant("branded_tenant"))
        activities = database.get_tenant_activities("branded_tenant")
        self.assertTrue(
            any(
                activity["action_type"] == "tenant_activated"
                for activity in activities
            )
        )

    def test_archive_restore_and_permanent_purge(self):
        database.create_clearance_pass(
            {
                "qr_pass_id": "pass-archive",
                "tenant_slug": "example_tenant",
                "rfq_code": "RFP-2",
                "vendor_name": "Archived Vendor",
                "email": "archive@example.test",
                "payment_reference": "payment-2",
                "proposal_title": "Archived proposal",
                "clearance_status": "PAYMENT_VERIFIED",
            }
        )
        database.log_admin_access("example_tenant", "login", "staff")

        self.assertTrue(database.archive_tenant("example_tenant"))
        self.assertIsNone(database.get_tenant_by_slug("example_tenant"))
        archived = database.list_archived_tenants()
        self.assertEqual(archived[0]["tenant_slug"], "example_tenant")
        self.assertEqual(
            archived[0]["tenant_data"]["full_corporation_name"],
            "Example Tenant",
        )

        self.assertTrue(database.restore_archived_tenant("example_tenant"))
        self.assertEqual(
            database.get_tenant_by_slug("example_tenant")["status"],
            "Pending",
        )
        self.assertEqual(
            len(database.list_admin_access_logs("example_tenant")),
            1,
        )
        self.assertEqual(len(database.list_vendors()), 1)

        self.assertTrue(database.archive_tenant("example_tenant"))
        self.assertTrue(database.purge_archived_tenant("example_tenant"))
        self.assertEqual(database.list_archived_tenants(), [])
        self.assertEqual(database.list_vendors(), [])
        self.assertIsNone(
            database.get_clearance_pass("pass-archive", "example_tenant")
        )
        self.assertEqual(database.list_admin_access_logs("example_tenant"), [])
        self.assertIn(
            "Tenant permanently purged",
            [
                activity["activity_type"]
                for activity in database.get_all_tenant_activities(
                    "example_tenant"
                )
            ],
        )

    def test_tenant_lifecycle_preserves_records_and_isolates_permanent_purge(self):
        database.save_tenant(
            {
                "tenant_slug": "other_tenant",
                "full_corporation_name": "Other Tenant",
                "status": "Active",
            }
        )
        example_pass = {
            "qr_pass_id": "pass-lifecycle-example",
            "tenant_slug": "example_tenant",
            "rfq_code": "RFP-3",
            "vendor_name": "Example Vendor",
            "email": "example@example.test",
            "payment_reference": "payment-example",
            "proposal_title": "Example proposal",
            "clearance_status": "PAYMENT_VERIFIED",
        }
        other_pass = {
            **example_pass,
            "qr_pass_id": "pass-lifecycle-other",
            "tenant_slug": "other_tenant",
            "payment_reference": "payment-other",
        }
        database.create_clearance_pass(example_pass)
        database.create_clearance_pass(other_pass)

        self.assertFalse(database.purge_tenant_permanently("example_tenant"))
        activated = database.activate_tenant("example_tenant")
        self.assertEqual(activated["status"], "Active")
        self.assertIsNotNone(database.get_tenant_by_slug("example_tenant")["activated_at"])
        self.assertTrue(database.deactivate_tenant("example_tenant"))
        self.assertEqual(
            database.get_tenant_by_slug("example_tenant")["status"],
            "Inactive",
        )

        self.assertTrue(database.soft_delete_tenant("example_tenant"))
        self.assertIsNone(database.get_tenant_by_slug("example_tenant"))
        self.assertNotIn(
            "example_tenant",
            {tenant["tenant_slug"] for tenant in database.list_tenants()},
        )
        with self.assertRaisesRegex(ValueError, "active tenant"):
            database.create_tenant_tender(
                tenant_slug="example_tenant",
                title="Should be rejected",
                description="Soft-deleted tenants cannot create tenders.",
                expiration_at=(
                    datetime.now(timezone.utc) + timedelta(days=1)
                ).isoformat(),
                auto_lock=True,
                created_by="tenant_executive",
            )
        recycled = database.list_recycle_bin_tenants()
        self.assertEqual(recycled[0]["tenant_slug"], "example_tenant")
        self.assertEqual(recycled[0]["status"], "Inactive")
        self.assertIsNotNone(recycled[0]["deleted_at"])
        self.assertTrue(database.restore_tenant("example_tenant"))
        self.assertEqual(
            database.get_tenant_by_slug("example_tenant")["status"],
            "Inactive",
        )
        self.assertTrue(database.activate_tenant("example_tenant"))
        lifecycle_actions = {
            event["action_type"]
            for event in database.get_tenant_activities("example_tenant")
        }
        self.assertTrue(
            {
                "tenant_activated",
                "tenant_deactivated",
                "tenant_soft_deleted",
                "tenant_restored",
            }.issubset(lifecycle_actions)
        )

        self.assertTrue(database.soft_delete_tenant("example_tenant"))
        self.assertTrue(database.purge_tenant_permanently("example_tenant"))
        self.assertIsNone(database.get_tenant_by_slug("example_tenant"))
        self.assertIsNone(
            database.get_clearance_pass("pass-lifecycle-example", "example_tenant")
        )
        self.assertIsNotNone(
            database.get_clearance_pass("pass-lifecycle-other", "other_tenant")
        )
        self.assertEqual(
            [
                event["action_type"]
                for event in database.get_tenant_activities("example_tenant")
            ],
            ["tenant_permanently_purged"],
        )

    def test_vendor_registration_is_stable_and_type_scoped(self):
        unsolicited_slug = database.register_vendor(
            "example_tenant",
            "Example Organization",
            "unsolicited",
        )
        self.assertEqual(
            unsolicited_slug,
            database.register_vendor(
                "example_tenant",
                "Example Organization",
                "unsolicited",
            ),
        )
        solicited_slug = database.register_vendor(
            "example_tenant",
            "Example Organization",
            "solicited",
        )
        self.assertNotEqual(unsolicited_slug, solicited_slug)
        self.assertEqual(
            {vendor["vendor_type"] for vendor in database.list_vendors()},
            {"solicited", "unsolicited"},
        )

    def test_general_broadcast_persists_and_can_be_cleared(self):
        self.assertIsNone(database.get_general_broadcast())

        database.set_general_broadcast("System maintenance tonight.")
        self.assertEqual(
            database.get_general_broadcast()["message"],
            "System maintenance tonight.",
        )

        database.set_general_broadcast("")
        self.assertIsNone(database.get_general_broadcast())

    def test_tenant_activity_log_is_formatted_filtered_and_newest_first(self):
        database.save_tenant(
            {
                "tenant_slug": "other_tenant",
                "full_corporation_name": "Other Tenant",
                "status": "Active",
            }
        )
        existing_activities = database.get_all_tenant_activities()
        first_id = database.log_legacy_tenant_activity(
            "EXAMPLE_TENANT",
            "Proposal reviewed",
            "The proposal passed initial review.",
            "reviewer",
        )
        other_id = database.log_legacy_tenant_activity(
            "other_tenant",
            "Tenant updated",
            "Tenant details updated.",
        )
        latest_id = database.log_legacy_tenant_activity(
            "example_tenant",
            "Proposal approved",
            "The proposal was approved.",
        )

        activities = database.get_all_tenant_activities()
        self.assertEqual(
            [activity["id"] for activity in activities[:3]],
            [latest_id, other_id, first_id],
        )
        self.assertEqual(
            [activity["id"] for activity in activities[3:]],
            [activity["id"] for activity in existing_activities],
        )
        example_activities = database.get_all_tenant_activities("EXAMPLE_TENANT")
        self.assertEqual(
            example_activities,
            [
                activity
                for activity in activities
                if activity["tenant_slug"] == "example_tenant"
            ],
        )
        self.assertEqual(activities[0]["performed_by"], "System/Admin")
        for activity in activities:
            timestamp = datetime.strptime(
                f"{activity['date']} {activity['time']}",
                "%Y-%m-%d %H:%M:%S",
            )
            self.assertEqual(activity["month"], timestamp.strftime("%B %Y"))
            self.assertEqual(activity["year"], timestamp.strftime("%Y"))

    def test_tenant_audit_log_is_timestamped_scoped_and_securely_deleted(self):
        database.save_tenant(
            {
                "tenant_slug": "other_tenant",
                "full_corporation_name": "Other Tenant",
                "status": "Active",
            }
        )
        existing_example_ids = {
            entry["id"]
            for entry in database.get_tenant_activities("example_tenant")
        }
        activity_id = database.log_tenant_activity(
            "example_tenant",
            "desk_officer",
            "proposal_received",
            "Received physical proposal RFP-2026-01.",
        )
        other_tenant_id = database.log_tenant_activity(
            "other_tenant",
            "executive",
            "proposal_recalled",
            "Recalled proposal RFP-2026-02.",
        )

        activities = database.get_tenant_activities("EXAMPLE_TENANT")
        self.assertIn(activity_id, [activity["id"] for activity in activities])
        entry = next(activity for activity in activities if activity["id"] == activity_id)
        self.assertEqual(entry["tenant_slug"], "example_tenant")
        self.assertEqual(entry["actor"], "desk_officer")
        self.assertEqual(entry["action_type"], "proposal_received")
        self.assertEqual(
            entry["details"],
            "Received physical proposal RFP-2026-01.",
        )
        timestamp = datetime.fromisoformat(entry["timestamp"])
        self.assertEqual(timestamp.tzinfo is not None, True)
        self.assertEqual(
            timestamp.strftime("%Y"),
            datetime.now().astimezone().strftime("%Y"),
        )

        self.assertFalse(
            database.delete_tenant_activity(activity_id, "other_tenant")
        )
        self.assertEqual(
            len(database.get_tenant_activities("other_tenant")),
            2,
        )
        self.assertTrue(
            database.delete_tenant_activity(
                activity_id,
                "example_tenant",
                actor="tenant_executive",
            )
        )
        remaining = database.get_tenant_activities("example_tenant")
        self.assertNotIn(activity_id, [activity["id"] for activity in remaining])
        self.assertTrue(
            existing_example_ids.issubset(
                {activity["id"] for activity in remaining}
            )
        )
        deletion_event = next(
            activity
            for activity in remaining
            if activity["action_type"] == "audit_entry_deleted"
        )
        self.assertIn(str(activity_id), deletion_event["details"])

    def test_permanent_purge_removes_only_tenant_dossier_files(self):
        import sector_logic

        dossier_root = Path(self.temporary_directory.name) / "dossiers"
        tenant_directory = dossier_root / "example_tenant"
        other_tenant_directory = dossier_root / "other_tenant"
        tenant_directory.mkdir(parents=True)
        other_tenant_directory.mkdir()
        (tenant_directory / "encrypted.fernet").write_bytes(b"encrypted")
        (other_tenant_directory / "preserved.fernet").write_bytes(b"preserved")

        with patch.dict(
            "os.environ",
            {"NEXUSVAULT_DOSSIER_DIR": str(dossier_root)},
        ):
            removed = sector_logic.purge_tenant_dossiers("example_tenant")

        self.assertEqual(removed, 1)
        self.assertFalse(tenant_directory.exists())
        self.assertTrue((other_tenant_directory / "preserved.fernet").exists())

    def test_physical_proposal_receipt_outbox_and_audit_are_tenant_scoped(self):
        database.save_tenant(
            {
                "tenant_slug": "example_tenant",
                "full_corporation_name": "Example Tenant",
                "status": "Active",
            }
        )
        database.save_tenant(
            {
                "tenant_slug": "other_tenant",
                "full_corporation_name": "Other Tenant",
                "status": "Active",
            }
        )
        proposal_data = {
            "organization_name": "Example Organization",
            "organization_address": "1 Example Road",
            "cac_registration_number": "RC123456",
            "contact_phone": "+2348000000000",
            "official_email": "contact@example.test",
            "proposal_title": "Digital records management platform",
            "submission_date": "2026-03-15",
            "signature_verified": True,
        }
        document_bytes = b"%PDF-1.7\nexample proposal document"
        encrypted_document = Fernet(Fernet.generate_key()).encrypt(document_bytes)

        result = database.create_physical_proposal(
            tenant_slug="example_tenant",
            proposal_data=proposal_data,
            document_bytes=document_bytes,
            document_ciphertext=encrypted_document,
            document_filename="proposal.pdf",
            routed_directorate="Information and Communications Technology",
            routing_basis="Local title-keyword match: digital",
            submitted_by="desk.officer",
        )

        expected_hash = database.generate_physical_proposal_receipt_hash(
            {
                **{
                    key: value
                    for key, value in proposal_data.items()
                    if key != "signature_verified"
                },
                "tenant_slug": "example_tenant",
                "signature_verified": True,
                "document_filename": "proposal.pdf",
            },
            document_bytes,
        )
        self.assertEqual(result["receipt_hash"], expected_hash)
        self.assertEqual(
            result["document_sha256"],
            hashlib.sha256(document_bytes).hexdigest(),
        )
        self.assertEqual(
            [row["tracking_id"] for row in database.get_physical_proposals("example_tenant")],
            [result["tracking_id"]],
        )
        self.assertEqual(database.get_physical_proposals("other_tenant"), [])

        outbox = database.get_proposal_notification_outbox(
            "example_tenant",
            result["tracking_id"],
        )
        self.assertEqual({row["channel"] for row in outbox}, {"sms", "email"})
        self.assertTrue(
            all(row["status"] == "SIMULATED_QUEUED" for row in outbox)
        )
        self.assertTrue(
            all(
                result["tracking_id"] in row["message"]
                and result["receipt_hash"] in row["message"]
                and "Your proposal is acknowledged and due attention will be accorded "
                "for possible action"
                in row["message"]
                for row in outbox
            )
        )
        self.assertEqual(
            database.get_proposal_notification_outbox(
                "other_tenant",
                result["tracking_id"],
            ),
            [],
        )
        activities = database.get_tenant_activities("example_tenant")
        self.assertTrue(
            any(
                activity["action_type"] == "physical_proposal_submitted"
                and result["tracking_id"] in activity["details"]
                for activity in activities
            )
        )

        with database.get_connection() as connection:
            stored_document = connection.execute(
                "SELECT document_ciphertext FROM physical_proposals WHERE tracking_id = ?",
                (result["tracking_id"],),
            ).fetchone()["document_ciphertext"]
        self.assertEqual(bytes(stored_document), encrypted_document)
        with self.assertRaises(InvalidToken):
            Fernet(Fernet.generate_key()).decrypt(bytes(stored_document))

    def test_physical_proposal_submission_rejects_inactive_tenants(self):
        with self.assertRaisesRegex(ValueError, "tenant is not active"):
            database.create_physical_proposal(
                tenant_slug="example_tenant",
                proposal_data={
                    "organization_name": "Example Organization",
                    "organization_address": "1 Example Road",
                    "cac_registration_number": "RC123456",
                    "contact_phone": "+2348000000000",
                    "official_email": "contact@example.test",
                    "proposal_title": "Digital records management platform",
                    "submission_date": "2026-03-15",
                    "signature_verified": False,
                },
                document_bytes=b"%PDF-1.7\nexample proposal document",
                document_ciphertext=b"encrypted document",
                document_filename="proposal.pdf",
                routed_directorate="Information and Communications Technology",
                routing_basis="Local title-keyword match: digital",
                submitted_by="desk.officer",
            )

    def test_gateway_credentials_are_encrypted_and_reads_are_tenant_scoped(self):
        database.save_tenant(
            {
                "tenant_slug": "example_tenant",
                "full_corporation_name": "Example Tenant",
                "status": "Active",
            }
        )
        key_ciphertext = Fernet(Fernet.generate_key()).encrypt(b"tsa-secret")
        remita_ciphertext = Fernet(Fernet.generate_key()).encrypt(b"remita-secret")
        saved = database.save_tenant_gateway_config(
            tenant_slug="example_tenant",
            tsa_endpoint="https://tsa.example.test/pay",
            tsa_key_ciphertext=key_ciphertext,
            remita_endpoint="https://remita.example.test/pay",
            remita_merchant_key_ciphertext=remita_ciphertext,
            service_head="Tender Fee/Bidding Document Fee",
            fee_amount_minor=125_000,
            updated_by="tenant_executive",
        )

        self.assertEqual(saved["fee_amount_minor"], 125_000)
        self.assertEqual(saved["currency"], "NGN")
        self.assertEqual(saved["tsa_key_configured"], 1)
        self.assertEqual(saved["remita_key_configured"], 1)
        self.assertNotIn("tsa_key_ciphertext", saved)
        self.assertNotIn("remita_merchant_key_ciphertext", saved)
        self.assertIsNone(database.get_tenant_gateway_config("other_tenant"))
        with database.get_connection() as connection:
            row = connection.execute(
                """
                SELECT tsa_key_ciphertext, remita_merchant_key_ciphertext
                FROM tenant_gateway_configs WHERE tenant_slug = ?
                """,
                ("example_tenant",),
            ).fetchone()
        self.assertEqual(bytes(row["tsa_key_ciphertext"]), key_ciphertext)
        self.assertEqual(
            bytes(row["remita_merchant_key_ciphertext"]),
            remita_ciphertext,
        )
        activities = database.get_tenant_activities("example_tenant")
        self.assertTrue(
            any(
                activity["action_type"] == "gateway_configuration_updated"
                for activity in activities
            )
        )

    def test_tenders_autolock_and_updates_are_tenant_scoped(self):
        database.save_tenant(
            {
                "tenant_slug": "example_tenant",
                "full_corporation_name": "Example Tenant",
                "status": "Active",
            }
        )
        tender = database.create_tenant_tender(
            tenant_slug="example_tenant",
            title="Road Maintenance Tender",
            description="Solicited tender.",
            expiration_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            auto_lock=True,
            created_by="tenant_executive",
            publish_now=True,
        )
        self.assertEqual(tender["publishing_status"], "PUBLISHED")
        self.assertEqual(
            [
                active["tender_id"]
                for active in database.get_active_solicited_tenders(
                    "example_tenant"
                )
            ],
            [tender["tender_id"]],
        )
        self.assertEqual(database.get_tenant_tenders("other_tenant"), [])
        self.assertEqual(database.get_active_solicited_tenders("other_tenant"), [])

        with database.get_connection() as connection:
            connection.execute(
                "UPDATE tenant_tenders SET expiration_at = ? WHERE tender_id = ?",
                (
                    (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
                    tender["tender_id"],
                ),
            )
        records = database.get_tenant_tenders("example_tenant")
        self.assertEqual(records[0]["publishing_status"], "LOCKED")
        self.assertEqual(database.get_active_solicited_tenders("example_tenant"), [])
        self.assertFalse(
            database.update_tenant_tender(
                "other_tenant",
                tender["tender_id"],
                "CANCELLED",
                True,
                "other_executive",
            )
        )
        with self.assertRaisesRegex(ValueError, "expired tender"):
            database.update_tenant_tender(
                "example_tenant",
                tender["tender_id"],
                "PUBLISHED",
                True,
                "tenant_executive",
            )
        self.assertTrue(
            any(
                activity["action_type"] == "tender_auto_locked"
                for activity in database.get_tenant_activities("example_tenant")
            )
        )

    def test_solicited_tender_is_not_public_until_explicitly_published(self):
        database.save_tenant(
            {
                "tenant_slug": "example_tenant",
                "full_corporation_name": "Example Tenant",
                "status": "Active",
            }
        )
        tender = database.create_tenant_tender(
            tenant_slug="example_tenant",
            title="Draft solicitation",
            description="Not yet public.",
            expiration_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            auto_lock=True,
            created_by="tenant_executive",
        )
        self.assertEqual(tender["publishing_status"], "DRAFT")
        self.assertEqual(database.get_active_solicited_tenders("example_tenant"), [])
        self.assertTrue(
            database.update_tenant_tender(
                "example_tenant",
                tender["tender_id"],
                "PUBLISHED",
                True,
                "tenant_executive",
            )
        )
        self.assertEqual(
            [
                row["tender_id"]
                for row in database.get_active_solicited_tenders("example_tenant")
            ],
            [tender["tender_id"]],
        )

    def test_verified_payment_ledger_retains_amount_and_is_tenant_scoped(self):
        import sector_logic

        database.save_tenant(
            {
                "tenant_slug": "example_tenant",
                "full_corporation_name": "Example Tenant",
                "status": "Active",
            }
        )
        database.save_tenant(
            {
                "tenant_slug": "other_tenant",
                "full_corporation_name": "Other Tenant",
                "status": "Active",
            }
        )
        with self.assertRaisesRegex(ValueError, "not currently published"):
            sector_logic._create_payment_verified_pass(
                tenant_slug="example_tenant",
                rfq_code="RFP-9",
                vendor_name="Example Vendor",
                vendor_email="vendor@example.test",
                payment_reference="RRR-9-unpublished",
                proposal_title="Example proposal",
                amount_minor=125_000,
            )
        tender = database.create_tenant_tender(
            tenant_slug="example_tenant",
            title="Road Maintenance Tender",
            description="Published solicitation.",
            expiration_at=(
                datetime.now(timezone.utc) + timedelta(days=1)
            ).isoformat(),
            auto_lock=True,
            created_by="tenant_executive",
            publish_now=True,
        )
        pass_id = sector_logic._create_payment_verified_pass(
            tenant_slug="example_tenant",
            rfq_code=tender["tender_id"],
            vendor_name="Example Vendor",
            vendor_email="vendor@example.test",
            payment_reference="RRR-9",
            proposal_title="Example proposal",
            amount_minor=125_000,
        )

        ledger = database.get_tenant_financial_ledger("example_tenant")
        self.assertEqual(len(ledger), 1)
        self.assertEqual(ledger[0]["amount_minor"], 125_000)
        self.assertEqual(ledger[0]["provider"], "Paystack")
        self.assertEqual(ledger[0]["qr_pass_id"], pass_id)
        self.assertEqual(database.get_tenant_financial_ledger("other_tenant"), [])
        with database.get_connection() as connection:
            connection.execute(
                "UPDATE tenant_tenders SET expiration_at = ? WHERE tender_id = ?",
                (
                    (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
                    tender["tender_id"],
                ),
            )
        self.assertFalse(
            sector_logic._mark_dossier_submitted(
                "example_tenant",
                pass_id,
            )
        )
        with self.assertRaisesRegex(ValueError, "no clearance pass"):
            database.record_tenant_payment_verification(
                tenant_slug="other_tenant",
                payment_reference="RRR-9",
                qr_pass_id="verified-pass",
                amount_minor=125_000,
                currency="NGN",
                provider="Paystack",
                vendor_email="vendor@example.test",
            )
        self.assertTrue(
            any(
                activity["action_type"] == "payment_provider_verified"
                for activity in database.get_tenant_activities("example_tenant")
            )
        )

    def test_committee_roster_coi_and_proposal_override_are_scoped(self):
        database.save_tenant(
            {
                "tenant_slug": "example_tenant",
                "full_corporation_name": "Example Tenant",
                "status": "Active",
            }
        )
        database.save_tenant(
            {
                "tenant_slug": "other_tenant",
                "full_corporation_name": "Other Tenant",
                "status": "Active",
            }
        )
        encryption = Fernet(Fernet.generate_key())
        roster = database.replace_tenant_committee(
            "example_tenant",
            [
                {
                    "member_id": f"member-{index}",
                    "name": f"Member {index}",
                    "email": f"member{index}@example.test",
                    "encrypted_access_token": encryption.encrypt(
                        f"token-{index}".encode()
                    ),
                }
                for index in range(10)
            ],
            "tenant_executive",
        )
        self.assertEqual(len(roster), 10)
        self.assertFalse(roster[0]["coi_signed"])
        self.assertNotIn("encrypted_access_token", roster[0])
        self.assertTrue(
            database.record_tenant_committee_coi_signoff(
                "example_tenant",
                "member-0",
                "tenant_executive",
            )
        )
        self.assertFalse(
            database.record_tenant_committee_coi_signoff(
                "other_tenant",
                "member-0",
                "other_executive",
            )
        )
        self.assertTrue(
            database.get_tenant_committee_members("example_tenant")[0]["coi_signed"]
        )
        with self.assertRaisesRegex(ValueError, "10 to 15"):
            database.replace_tenant_committee(
                "example_tenant",
                [],
                "tenant_executive",
            )

        proposal_data = {
            "organization_name": "Example Organization",
            "organization_address": "1 Example Road",
            "cac_registration_number": "RC123456",
            "contact_phone": "+2348000000000",
            "official_email": "contact@example.test",
            "proposal_title": "Digital records management platform",
            "submission_date": "2026-03-15",
            "signature_verified": True,
        }
        document = b"%PDF-1.7\nproposal"
        proposal = database.create_physical_proposal(
            "example_tenant",
            proposal_data,
            document,
            encryption.encrypt(document),
            "proposal.pdf",
            "ICT",
            "local rule",
            "desk.officer",
        )
        unsolicited = database.record_unsolicited_proposal(
            tenant_slug="example_tenant",
            submission_id="NV-UNSOL-EXAMPLE",
            organization_name="Unsolicited Organization",
            cac_registration_number="RC654321",
            proposal_title="Solar microgrid proposal",
            document_filename="solar.pdf",
            document_sha256=hashlib.sha256(document).hexdigest(),
        )
        database.create_clearance_pass(
            {
                "qr_pass_id": "pass-submitted",
                "tenant_slug": "example_tenant",
                "rfq_code": "TND-1",
                "vendor_name": "Solicited Organization",
                "email": "solicited@example.test",
                "payment_reference": "RRR-123",
                "proposal_title": "Bridge repair proposal",
                "clearance_status": "DOSSIER_SUBMITTED",
            }
        )
        hub_proposals = database.get_tenant_governance_proposals("example_tenant")
        self.assertEqual(
            {item["tracking_id"] for item in hub_proposals},
            {proposal["tracking_id"], unsolicited["submission_id"], "pass-submitted"},
        )
        self.assertTrue(
            database.set_tenant_proposal_governance_status(
                "example_tenant",
                proposal["tracking_id"],
                "STOPPED",
                "tenant_executive",
            )
        )
        self.assertFalse(
            database.set_tenant_proposal_governance_status(
                "other_tenant",
                proposal["tracking_id"],
                "RECALLED",
                "other_executive",
            )
        )
        proposal_statuses = {
            item["tracking_id"]: item["governance_status"]
            for item in database.get_tenant_governance_proposals("example_tenant")
        }
        self.assertEqual(proposal_statuses[proposal["tracking_id"]], "STOPPED")
        self.assertEqual(proposal_statuses[unsolicited["submission_id"]], "RECEIVED")
        self.assertEqual(database.get_tenant_governance_proposals("other_tenant"), [])

    def test_departmental_screening_appraisal_and_apex_handoff_are_scoped(self):
        database.save_tenant(
            {
                "tenant_slug": "example_tenant",
                "full_corporation_name": "Example Tenant",
                "status": "Active",
            }
        )
        database.save_tenant(
            {
                "tenant_slug": "other_tenant",
                "full_corporation_name": "Other Tenant",
                "status": "Active",
            }
        )
        proposal_data = {
            "organization_name": "Example Health Supplies",
            "organization_address": "1 Example Road",
            "cac_registration_number": "RC-123456",
            "contact_phone": "+2348000000000",
            "official_email": "contact@example.test",
            "proposal_title": "Food and consumables supply",
            "submission_date": "2026-03-15",
            "signature_verified": True,
        }
        source_document = b"%PDF-1.7\nexample proposal dossier"
        document_key = Fernet.generate_key()
        proposal = database.create_physical_proposal(
            tenant_slug="example_tenant",
            proposal_data=proposal_data,
            document_bytes=source_document,
            document_ciphertext=Fernet(document_key).encrypt(source_document),
            document_filename="proposal.pdf",
            routed_directorate="Health and Social Services",
            routing_basis="Local title-keyword match: food",
            submitted_by="desk.officer",
        )
        aggregated = database.get_tenant_governance_proposals("example_tenant")
        self.assertEqual(aggregated[0]["source_type"], "physical")
        self.assertEqual(aggregated[0]["tax_identification_number"], None)
        import sector_logic

        with patch.dict(
            "os.environ",
            {"NEXUSVAULT_DOSSIER_ENCRYPTION_KEY": document_key.decode("ascii")},
        ):
            filename, downloaded_document = (
                sector_logic.get_departmental_proposal_document(
                    "example_tenant",
                    proposal["tracking_id"],
                )
            )
            self.assertEqual(filename, "proposal.pdf")
            self.assertEqual(downloaded_document, source_document)
            with self.assertRaisesRegex(ValueError, "not available in this tenant"):
                sector_logic.get_departmental_proposal_document(
                    "other_tenant",
                    proposal["tracking_id"],
                )
        dossier = database.save_departmental_review_dossier(
            tenant_slug="example_tenant",
            tracking_id=proposal["tracking_id"],
            source_type="physical",
            organization_name="Example Health Supplies",
            proposal_title="Food and consumables supply",
            routed_directorate="Health and Social Services",
            submitted_at=proposal["submitted_at"],
        )
        self.assertEqual(dossier["sector"], "")
        queue = database.get_departmental_review_queue(
            "example_tenant",
            "Health and Social Services",
        )
        self.assertEqual([item["tracking_id"] for item in queue], [proposal["tracking_id"]])
        self.assertEqual(
            database.get_departmental_review_queue(
                "other_tenant",
                "Health and Social Services",
            ),
            [],
        )

        checks = [
            {
                "check_name": check_name,
                "verification_status": status,
                "registry_source": source,
                "credential_reference": reference,
                "result_details": detail,
            }
            for check_name, status, source, reference, detail in (
                (
                    "CAC",
                    "PROVIDED_UNVERIFIED",
                    "Local screening",
                    "***3456",
                    "Reference present, external registry not queried.",
                ),
                ("TIN", "MISSING", "Local screening", "", "No TIN captured."),
                ("KYB", "MISSING", "Local screening", "", "No KYB evidence."),
                ("EFCC", "MISSING", "Local screening", "", "No evidence."),
                ("PenCom", "MISSING", "Local screening", "", "No evidence."),
                (
                    "NAFDAC",
                    "MISSING",
                    "Local screening",
                    "",
                    "No license reference.",
                ),
                (
                    "COREN",
                    "NOT_APPLICABLE",
                    "Sector applicability",
                    "",
                    "Not an engineering sector.",
                ),
                (
                    "NSCDC",
                    "NOT_APPLICABLE",
                    "Sector applicability",
                    "",
                    "Not a security sector.",
                ),
                (
                    "NITDA",
                    "NOT_APPLICABLE",
                    "Sector applicability",
                    "",
                    "Not an ICT sector.",
                ),
            )
        ]
        saved_checks = database.save_statutory_compliance_checks(
            tenant_slug="example_tenant",
            tracking_id=proposal["tracking_id"],
            directorate="Health and Social Services",
            sector="Food / Consumables",
            checks=checks,
            checked_by="director.health",
        )
        self.assertEqual(len(saved_checks), 9)
        self.assertEqual(
            {check["check_name"] for check in saved_checks},
            {"CAC", "TIN", "KYB", "EFCC", "PenCom", "NAFDAC", "COREN", "NSCDC", "NITDA"},
        )
        self.assertEqual(
            database.get_departmental_review_dossier(
                "other_tenant",
                proposal["tracking_id"],
            ),
            None,
        )

        appraisal = database.save_departmental_appraisal(
            tenant_slug="example_tenant",
            tracking_id=proposal["tracking_id"],
            directorate="Health and Social Services",
            appraiser="director.health",
            appraisal_notes="Proceed subject to statutory verification.",
            executive_summary="Local screening completed; verification remains open.",
            signoff_status="Approved",
            push_to_apex=True,
        )
        self.assertEqual(appraisal["signoff_status"], "Approved")
        self.assertTrue(appraisal["pushed_to_apex"])
        self.assertEqual(
            database.list_departmental_appraisals("other_tenant"),
            [],
        )
        apex_proposal = database.get_tenant_governance_proposals(
            "example_tenant"
        )[0]
        self.assertEqual(apex_proposal["departmental_signoff_status"], "Approved")
        self.assertEqual(apex_proposal["appraisal_pushed_to_apex"], 1)
        activities = database.get_tenant_activities("example_tenant")
        self.assertTrue(
            any(
                activity["action_type"]
                == "departmental_compliance_screening_completed"
                for activity in activities
            )
        )
        self.assertTrue(
            any(
                activity["action_type"]
                == "departmental_appraisal_pushed_to_apex"
                for activity in activities
            )
        )

    def test_database_migrates_existing_unsolicited_proposal_table(self):
        database_path = Path(self.temporary_directory.name) / "legacy.db"
        with patch.object(database, "DB_FILE", database_path):
            with database.get_connection() as connection:
                connection.execute(
                    """
                    CREATE TABLE unsolicited_proposals (
                        submission_id TEXT PRIMARY KEY,
                        tenant_slug TEXT NOT NULL,
                        organization_name TEXT NOT NULL,
                        cac_registration_number TEXT NOT NULL,
                        proposal_title TEXT NOT NULL,
                        document_filename TEXT NOT NULL,
                        document_sha256 TEXT NOT NULL,
                        submitted_at TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO unsolicited_proposals (
                        submission_id, tenant_slug, organization_name,
                        cac_registration_number, proposal_title,
                        document_filename, document_sha256, submitted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "NV-UNSOL-LEGACY",
                        "example_tenant",
                        "Legacy Organization",
                        "RC-OLD",
                        "Legacy proposal",
                        "legacy.pdf",
                        "0" * 64,
                        "2026-01-01T00:00:00+00:00",
                    ),
                )
            database.init_db()
            with database.get_connection() as connection:
                columns = {
                    row["name"]: row
                    for row in connection.execute(
                        'PRAGMA table_info("unsolicited_proposals")'
                    ).fetchall()
                }
                migrated = connection.execute(
                    "SELECT tax_identification_number FROM unsolicited_proposals "
                    "WHERE submission_id = ?",
                    ("NV-UNSOL-LEGACY",),
                ).fetchone()
            self.assertIn("tax_identification_number", columns)
            self.assertEqual(columns["tax_identification_number"]["dflt_value"], "''")
            self.assertEqual(migrated["tax_identification_number"], "")

    def test_committee_coi_gate_evaluation_and_consolidation_are_tenant_scoped(self):
        database.save_tenant(
            {
                "tenant_slug": "example_tenant",
                "full_corporation_name": "Example Tenant",
                "status": "Active",
            }
        )
        database.save_tenant(
            {
                "tenant_slug": "other_tenant",
                "full_corporation_name": "Other Tenant",
                "status": "Active",
            }
        )
        key = Fernet.generate_key()
        fernet = Fernet(key)
        roster = database.replace_tenant_committee(
            "example_tenant",
            [
                {
                    "member_id": f"reviewer-{index}",
                    "name": f"Reviewer {index}",
                    "email": f"reviewer{index}@example.test",
                    "encrypted_access_token": fernet.encrypt(
                        f"token-{index}".encode()
                    ),
                }
                for index in range(10)
            ],
            "tenant_executive",
        )
        proposal_data = {
            "organization_name": "Example Organization",
            "organization_address": "1 Example Road",
            "cac_registration_number": "RC-123456",
            "contact_phone": "+2348000000000",
            "official_email": "contact@example.test",
            "proposal_title": "Example infrastructure project",
            "submission_date": "2026-03-15",
            "signature_verified": True,
        }
        proposal = database.create_physical_proposal(
            "example_tenant",
            proposal_data,
            b"%PDF-1.7\ncommittee proposal",
            fernet.encrypt(b"%PDF-1.7\ncommittee proposal"),
            "proposal.pdf",
            "Works Directorate",
            "Manual review",
            "desk.officer",
        )
        tracking_id = proposal["tracking_id"]
        identity = database.authenticate_tenant_committee_member(
            "example_tenant",
            "token-0",
            key,
        )
        self.assertEqual(identity["member_id"], roster[0]["member_id"])
        self.assertIsNone(
            database.authenticate_tenant_committee_member(
                "other_tenant",
                "token-0",
                key,
            )
        )
        self.assertIsNone(
            database.get_committee_coi_status(
                "example_tenant",
                "reviewer-0",
                tracking_id,
            )
        )
        with self.assertRaisesRegex(ValueError, "COI is required"):
            database.save_committee_proposal_evaluation(
                "example_tenant",
                "reviewer-0",
                tracking_id,
                {"technical": 80, "financial": 70, "compliance": 90},
                "Evaluation notes",
            )

        receipt = database.record_committee_coi_signoff(
            "example_tenant",
            "reviewer-0",
            tracking_id,
            "Reviewer 0",
        )
        self.assertEqual(receipt["declaration_status"], "Signed")
        self.assertEqual(len(receipt["digital_signature_hash"]), 64)
        with self.assertRaisesRegex(ValueError, "not provisioned for this tenant"):
            database.record_committee_coi_signoff(
                "other_tenant",
                "reviewer-0",
                tracking_id,
                "Reviewer 0",
            )

        database.save_committee_proposal_evaluation(
            "example_tenant",
            "reviewer-0",
            tracking_id,
            {"technical": 80, "financial": 70, "compliance": 90},
            "Evaluation notes",
        )
        database.record_committee_coi_signoff(
            "example_tenant",
            "reviewer-1",
            tracking_id,
            "Reviewer 1",
        )
        database.save_committee_proposal_evaluation(
            "example_tenant",
            "reviewer-1",
            tracking_id,
            {"technical": 100, "financial": 90, "compliance": 80},
            "Second evaluation",
        )
        consolidated = database.get_consolidated_committee_scores(
            "example_tenant",
            tracking_id,
        )
        self.assertEqual(consolidated["reviewer_count"], 2)
        self.assertEqual(consolidated["technical_average"], 90)
        self.assertEqual(consolidated["financial_average"], 80)
        self.assertEqual(consolidated["compliance_average"], 85)
        self.assertAlmostEqual(consolidated["weighted_average"], 85)
        self.assertAlmostEqual(consolidated["score_variance"], 25)
        self.assertEqual(
            database.get_consolidated_committee_scores(
                "other_tenant",
                tracking_id,
            )["reviewer_count"],
            0,
        )
        with self.assertRaisesRegex(ValueError, "between 0 and 100"):
            database.save_committee_proposal_evaluation(
                "example_tenant",
                "reviewer-0",
                tracking_id,
                {"technical": 101, "financial": 70, "compliance": 90},
                "",
            )
        actions = {
            activity["action_type"]
            for activity in database.get_tenant_activities("example_tenant")
        }
        self.assertIn("committee_proposal_coi_signed", actions)
        self.assertIn("committee_proposal_evaluation_saved", actions)


if __name__ == "__main__":
    unittest.main()

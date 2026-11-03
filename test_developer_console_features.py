import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database


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


if __name__ == "__main__":
    unittest.main()

"""Seam tests for T2 (issue #4): contacts — required fields, company
linking, multiple role tags, and role access.

Both operating roles (Founder and Producer) must be able to create,
read and edit parties; this is the positive counterpart of the
Founder Spike Note permission proof.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.tests.utils import make_test_user

FOUNDER = "founder@test.auraos.local"
PRODUCER = "producer@test.auraos.local"
# A System User with neither app role — the negative control.
OUTSIDER = "outsider@test.auraos.local"


def make_company(**overrides):
    doc = frappe.get_doc(
        {
            "doctype": "Party Company",
            "company_name": "Chungify Media",
            "tax_code": "0312345678",
            "bank_account_number": "0071000123456",
            "bank_name": "Vietcombank",
            **overrides,
        }
    )
    doc.insert()
    return doc


def make_contact(**overrides):
    doc = frappe.get_doc(
        {
            "doctype": "Party Contact",
            "full_name": "Nguyễn Văn A",
            "phone": "0901234567",
            **overrides,
        }
    )
    doc.insert()
    return doc


class TestPartyContact(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    # -- seeds --

    def test_party_roles_are_seeded(self):
        for role in ("Client", "Vendor", "Freelancer"):
            self.assertTrue(
                frappe.db.exists("Party Role", role),
                f"Party Role '{role}' should be seeded on install/migrate",
            )

    # -- required fields --

    def test_company_requires_company_name(self):
        with self.assertRaises(frappe.MandatoryError):
            frappe.get_doc(
                {"doctype": "Party Company", "tax_code": "0312345678"}
            ).insert()

    def test_contact_requires_full_name(self):
        with self.assertRaises(frappe.MandatoryError):
            frappe.get_doc(
                {"doctype": "Party Contact", "phone": "0901234567"}
            ).insert()

    def test_company_stores_tax_and_bank_info(self):
        company = make_company()
        reloaded = frappe.get_doc("Party Company", company.name)
        self.assertEqual(reloaded.tax_code, "0312345678")
        self.assertEqual(reloaded.bank_account_number, "0071000123456")
        self.assertEqual(reloaded.bank_name, "Vietcombank")

    # -- linking --

    def test_contact_links_to_company(self):
        company = make_company()
        contact = make_contact(company=company.name)
        reloaded = frappe.get_doc("Party Contact", contact.name)
        self.assertEqual(reloaded.company, company.name)

    def test_contact_rejects_unknown_company(self):
        with self.assertRaises(frappe.exceptions.LinkValidationError):
            make_contact(company="No Such Company")

    def test_company_with_contacts_cannot_be_deleted(self):
        company = make_company()
        make_contact(company=company.name)
        with self.assertRaises(frappe.exceptions.LinkExistsError):
            frappe.delete_doc("Party Company", company.name)

    # -- role tags --

    def test_contact_carries_multiple_role_tags(self):
        contact = make_contact(
            role_tags=[
                {"party_role": "Vendor"},
                {"party_role": "Freelancer"},
            ]
        )
        reloaded = frappe.get_doc("Party Contact", contact.name)
        self.assertEqual(
            sorted(row.party_role for row in reloaded.role_tags),
            ["Freelancer", "Vendor"],
        )

    def test_company_carries_role_tag(self):
        company = make_company(role_tags=[{"party_role": "Client"}])
        reloaded = frappe.get_doc("Party Company", company.name)
        self.assertEqual(
            [row.party_role for row in reloaded.role_tags], ["Client"]
        )

    # -- role access: both operating roles read AND write --

    def assert_role_can_read_write(self, user):
        frappe.set_user(user)
        for doctype in ("Party Company", "Party Contact"):
            for ptype in ("read", "write", "create"):
                self.assertTrue(
                    frappe.has_permission(doctype, ptype),
                    f"{user} should have {ptype} on {doctype}",
                )
        company = make_company(company_name=f"Access probe {user}")
        contact = make_contact(
            full_name=f"Probe {user}", company=company.name
        )
        # a full round trip: create above, then edit and list
        contact.phone = "0912345678"
        contact.save()
        # frappe.client.get_list backs GET /api/resource/<doctype> — the
        # REST list seam, not just the internal document API.
        from frappe.client import get_list

        self.assertIn(
            contact.name,
            [row["name"] for row in get_list("Party Contact", fields=["name"])],
        )

    def test_founder_can_read_write_parties(self):
        self.assert_role_can_read_write(FOUNDER)

    def test_producer_can_read_write_parties(self):
        self.assert_role_can_read_write(PRODUCER)

    def test_user_without_app_role_is_denied(self):
        from frappe.client import get_list

        frappe.set_user(OUTSIDER)
        for doctype in ("Party Company", "Party Contact"):
            self.assertFalse(frappe.has_permission(doctype, "read"))
            with self.assertRaises(frappe.PermissionError):
                get_list(doctype)

    def test_only_founder_can_manage_party_roles(self):
        frappe.set_user(PRODUCER)
        self.assertTrue(frappe.has_permission("Party Role", "read"))
        self.assertFalse(frappe.has_permission("Party Role", "create"))
        frappe.set_user(FOUNDER)
        self.assertTrue(frappe.has_permission("Party Role", "create"))

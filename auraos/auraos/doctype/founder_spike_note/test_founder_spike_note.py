"""Permission proof (spec's open verification item, retired here).

A producer-role session must not be able to read a founder-only DocType
through any access path: document API, list API, or global search.
These tests are the permanent regression harness for that guarantee;
every future founder-only DocType should copy this pattern.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import global_search

FOUNDER = "founder@test.auraos.local"
PRODUCER = "producer@test.auraos.local"

# Unique marker so global-search assertions cannot collide with other data.
SECRET = "chi-phi-bi-mat-8823"


def make_test_user(email, role):
    if not frappe.db.exists("User", email):
        frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": email.split("@")[0].title(),
                "user_type": "System User",
                "send_welcome_email": 0,
            }
        ).insert(ignore_permissions=True)
    user = frappe.get_doc("User", email)
    user.append_roles(role)
    user.save(ignore_permissions=True)


class TestFounderSpikeNote(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        note = frappe.get_doc(
            {
                "doctype": "Founder Spike Note",
                "title": f"Overhead spike {SECRET}",
                "note": f"Monthly overhead draft — {SECRET}",
            }
        ).insert(ignore_permissions=True)
        cls.note_name = note.name
        # Global search is normally flushed on commit; tests roll back,
        # so flush the pending buffer into __global_search explicitly.
        global_search.sync_global_search()

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    # -- positive control: the founder sees the note through every path --

    def test_founder_can_read_document(self):
        frappe.set_user(FOUNDER)
        doc = frappe.get_doc("Founder Spike Note", self.note_name)
        doc.check_permission("read")
        self.assertIn(SECRET, doc.title)

    def test_founder_can_list(self):
        frappe.set_user(FOUNDER)
        names = frappe.get_list("Founder Spike Note", pluck="name")
        self.assertIn(self.note_name, names)

    def test_founder_can_global_search(self):
        frappe.set_user(FOUNDER)
        results = global_search.search(SECRET)
        self.assertTrue(
            any(r.get("doctype") == "Founder Spike Note" for r in results),
            "positive control failed: founder should find the note in global search",
        )

    # -- the proof: a producer session is blind on every path --

    def test_producer_has_no_read_permission(self):
        frappe.set_user(PRODUCER)
        self.assertFalse(frappe.has_permission("Founder Spike Note", "read"))

    def test_producer_cannot_read_via_document_api(self):
        frappe.set_user(PRODUCER)
        doc = frappe.get_doc("Founder Spike Note", self.note_name)
        with self.assertRaises(frappe.PermissionError):
            doc.check_permission("read")

    def test_producer_cannot_read_via_rest_document_endpoint(self):
        # frappe.client.get backs GET /api/resource/<doctype>/<name>
        from frappe.client import get

        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            get("Founder Spike Note", name=self.note_name)

    def test_producer_cannot_list(self):
        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            frappe.get_list("Founder Spike Note")

    def test_producer_cannot_global_search(self):
        frappe.set_user(PRODUCER)
        results = global_search.search(SECRET)
        leaked = [r for r in results if r.get("doctype") == "Founder Spike Note"]
        self.assertEqual(
            leaked,
            [],
            "PERMISSION LEAK: producer found a founder-only note via global search",
        )

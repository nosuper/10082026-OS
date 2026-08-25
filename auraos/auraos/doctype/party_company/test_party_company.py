"""Seam tests for #118: creating a client inline from the deal form.

The deal form now offers "+ New client..." and inserts a Party Company
carrying nothing but its name. That path is a `frappe.client.insert`
from the browser - the same call the Contacts screen makes - so there is
no server code of its own to test. What there *is* to test is the two
assumptions the dialog is built on, because both live in the doctype
rather than in the screen, and both are silent when they change:

  - a producer may create one at all;
  - a name is the whole of what a company needs.

The second is the one worth having. Adding a `reqd` field to Party
Company would not break the Contacts screen, which asks for every field
anyway - it would break only the inline dialog, which asks for one, and
it would break it as a save that fails after the person has already left
the field. Here it fails as a red test naming the reason instead.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.tests.utils import make_test_user

PRODUCER = "producer@test.auraos.local"


class TestPartyCompanyInlineCreate(FrappeTestCase):
    def setUp(self):
        make_test_user(PRODUCER, "Producer")
        frappe.set_user(PRODUCER)

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_a_producer_creates_a_company_from_its_name_alone(self):
        """What the dialog sends, sent the way the dialog sends it."""
        doc = frappe.get_doc(
            {"doctype": "Party Company", "company_name": "Xưởng phim Bình Minh"}
        ).insert()

        self.assertTrue(doc.name.startswith("COM-"))
        self.assertEqual(doc.company_name, "Xưởng phim Bình Minh")

    def test_the_name_is_the_only_thing_a_company_requires(self):
        """A tripwire, deliberately, rather than a behaviour.

        The dialog sends one field. It can only keep doing that while one
        field is all the doctype demands, and nothing else in the app
        would notice that changing - the Contacts screen sends the lot.
        """
        required = [
            field.fieldname
            for field in frappe.get_meta("Party Company").fields
            if field.reqd
        ]
        self.assertEqual(
            required,
            ["company_name"],
            "Party Company has grown a required field beyond its name, and the "
            "deal form's inline '+ New client...' dialog sends only the name - "
            "so that dialog's save now fails, after the person has already "
            "moved on. Three repairs, in the order they are usually right: "
            "give the field a server-side default so the inline path can keep "
            "sending one field; or add the field to the dialog, accepting that "
            "'one field' becomes two; or stop offering the inline path and send "
            "people back to Contacts. Deleting this assertion is not one of "
            "them - it is the thing that told you.",
        )

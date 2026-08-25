"""Seam tests for the Settings vocabulary lists (T3.5, issue #29).

Runs via: bench --site <site> run-tests --app auraos

The rules themselves are proved framework-free in tests/test_vocabulary.py.
What needs a site is everything the pure module cannot see:

- **The producer really can manage sources** end to end - add, rename,
  remove - through the endpoints the Settings screen calls. This is the
  change that supersedes T3.2's founder-only guard.
- **The producer really cannot touch what stays founder-only**: project
  types, by either door (endpoint and DocType), and the margin floor.
- **A rename migrates.** The deals on a value follow it across, and the
  row's own name field follows too.
- **A removal refuses while the value is in use**, and the deal that
  held it is untouched by the attempt.
- **The two gates agree.** The seam and the DocType permissions are
  separate statements of the same rule; a drift between them is a bug
  even when neither alone looks wrong.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import (
    add_vocabulary_value,
    get_vocabularies,
    remove_vocabulary_value,
    rename_vocabulary_value,
    set_margin_floor,
)
from auraos.lib import vocabulary
from auraos.tests.utils import make_test_user

FOUNDER = "founder@test.auraos.local"
PRODUCER = "producer@test.auraos.local"
# A System User with neither app role - the negative control.
OUTSIDER = "outsider@test.auraos.local"


def make_deal(**overrides):
    company = frappe.db.exists("Party Company", {"company_name": "Chungify Media"})
    if not company:
        company = frappe.get_doc(
            {"doctype": "Party Company", "company_name": "Chungify Media"}
        ).insert(ignore_permissions=True).name
    return frappe.get_doc(
        {
            "doctype": "Deal",
            "title": "Vocabulary probe",
            "company": company,
            "deal_owner": FOUNDER,
            **overrides,
        }
    ).insert(ignore_permissions=True)


def values_of(rows, key):
    return [
        row["name"]
        for row in next(row for row in rows if row["key"] == key)["values"]
    ]


def view_of(rows, key):
    return next(row for row in rows if row["key"] == key)


class TestVocabularyApi(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)
        from auraos.setup.install import create_deal_vocabularies

        create_deal_vocabularies()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    # -- reading the lists --

    def test_both_operating_roles_read_every_list(self):
        # The values are already on the deal form; it is the manage flag
        # that differs, not the reading.
        for user in (FOUNDER, PRODUCER):
            frappe.set_user(user)
            rows = get_vocabularies()
            self.assertEqual(
                {row["key"] for row in rows}, set(vocabulary.VOCABULARIES)
            )
            self.assertIn("Zalo", values_of(rows, "source"))
            self.assertIn("TVC", values_of(rows, "project_type"))

    def test_manage_flags_are_the_settings_screen_sections(self):
        frappe.set_user(PRODUCER)
        rows = get_vocabularies()
        self.assertTrue(view_of(rows, "source")["can_manage"])
        self.assertFalse(view_of(rows, "project_type")["can_manage"])

        frappe.set_user(FOUNDER)
        rows = get_vocabularies()
        self.assertTrue(view_of(rows, "source")["can_manage"])
        self.assertTrue(view_of(rows, "project_type")["can_manage"])

    def test_a_role_less_session_reads_no_list(self):
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            get_vocabularies()

    def test_values_carry_how_many_deals_hold_them(self):
        make_deal(source="Expo")
        frappe.set_user(PRODUCER)
        row = next(
            row for row in view_of(get_vocabularies(), "source")["values"]
            if row["name"] == "Expo"
        )
        self.assertEqual(row["in_use"], 1)

    # -- the producer manages sources (supersedes T3.2's guard) --

    def test_producer_can_add_a_source(self):
        frappe.set_user(PRODUCER)
        rows = add_vocabulary_value("source", "TikTok")
        self.assertIn("TikTok", values_of(rows, "source"))
        self.assertTrue(frappe.db.exists("Deal Source", "TikTok"))

    def test_producer_can_rename_a_source(self):
        frappe.set_user(PRODUCER)
        add_vocabulary_value("source", "Hội chợ")
        rows = rename_vocabulary_value("source", "Hội chợ", "Trade show")
        self.assertIn("Trade show", values_of(rows, "source"))
        self.assertNotIn("Hội chợ", values_of(rows, "source"))

    def test_producer_can_remove_an_unused_source(self):
        frappe.set_user(PRODUCER)
        add_vocabulary_value("source", "Cold call")
        rows = remove_vocabulary_value("source", "Cold call")
        self.assertNotIn("Cold call", values_of(rows, "source"))
        self.assertFalse(frappe.db.exists("Deal Source", "Cold call"))

    def test_a_typed_value_keeps_its_accents(self):
        frappe.set_user(PRODUCER)
        rows = add_vocabulary_value("source", "  Giới thiệu  ")
        self.assertIn("Giới thiệu", values_of(rows, "source"))

    def test_an_empty_value_is_refused(self):
        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.ValidationError):
            add_vocabulary_value("source", "   ")

    def test_a_duplicate_value_is_refused(self):
        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.DuplicateEntryError):
            add_vocabulary_value("source", "Zalo")

    def test_an_unknown_list_is_refused_by_name(self):
        frappe.set_user(FOUNDER)
        with self.assertRaises(frappe.ValidationError):
            add_vocabulary_value("margin_floor", "80")

    # -- what the producer must not touch --

    def test_producer_cannot_add_a_project_type(self):
        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            add_vocabulary_value("project_type", "Feature film")
        self.assertFalse(frappe.db.exists("Project Type", "Feature film"))

    def test_producer_cannot_rename_a_project_type(self):
        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            rename_vocabulary_value("project_type", "TVC", "Ad film")
        self.assertTrue(frappe.db.exists("Project Type", "TVC"))

    def test_producer_cannot_remove_a_project_type(self):
        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            remove_vocabulary_value("project_type", "Documentary")
        self.assertTrue(frappe.db.exists("Project Type", "Documentary"))

    def test_producer_still_cannot_set_the_margin_floor(self):
        # T3.5 opened the Settings screen to the producer; the founder's
        # own number on that same screen did not move with it.
        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            set_margin_floor(40)

    def test_a_role_less_session_manages_nothing(self):
        frappe.set_user(OUTSIDER)
        for kind in vocabulary.VOCABULARIES:
            with self.assertRaises(frappe.PermissionError):
                add_vocabulary_value(kind, "Smuggled in")

    # -- rename migrates, and never merges --

    def test_renaming_carries_the_deals_on_the_value_across(self):
        frappe.set_user(FOUNDER)
        add_vocabulary_value("source", "Expo hall")
        deal = make_deal(source="Expo hall")
        rename_vocabulary_value("source", "Expo hall", "Trade fair")
        self.assertEqual(
            frappe.db.get_value("Deal", deal.name, "source"), "Trade fair"
        )
        self.assertFalse(frappe.db.exists("Deal Source", "Expo hall"))

    def test_a_renamed_row_is_named_by_its_own_field(self):
        # The lists autoname from their value field; a rename that left
        # the field behind would read "Expo" while being called
        # "Trade show" everywhere else.
        frappe.set_user(FOUNDER)
        add_vocabulary_value("source", "Roadshow")
        rename_vocabulary_value("source", "Roadshow", "Street show")
        self.assertEqual(
            frappe.db.get_value("Deal Source", "Street show", "source_name"),
            "Street show",
        )

    def test_renaming_onto_an_existing_value_is_refused(self):
        frappe.set_user(FOUNDER)
        with self.assertRaises(frappe.ValidationError):
            rename_vocabulary_value("source", "Expo", "Zalo")
        self.assertTrue(frappe.db.exists("Deal Source", "Expo"))
        self.assertTrue(frappe.db.exists("Deal Source", "Zalo"))

    def test_renaming_a_value_that_is_not_there_is_refused(self):
        frappe.set_user(FOUNDER)
        with self.assertRaises(frappe.DoesNotExistError):
            rename_vocabulary_value("source", "Carrier pigeon", "Pigeon")

    # -- removal refuses while the value is in use --

    def test_a_source_on_a_deal_cannot_be_removed(self):
        frappe.set_user(FOUNDER)
        add_vocabulary_value("source", "Newsletter")
        deal = make_deal(source="Newsletter")
        with self.assertRaises(frappe.ValidationError):
            remove_vocabulary_value("source", "Newsletter")
        # The value stays, and so does the deal's answer to where it
        # came from - the whole point of refusing.
        self.assertTrue(frappe.db.exists("Deal Source", "Newsletter"))
        self.assertEqual(
            frappe.db.get_value("Deal", deal.name, "source"), "Newsletter"
        )

    def test_the_refusal_names_the_value_and_counts_the_deals(self):
        frappe.set_user(FOUNDER)
        add_vocabulary_value("source", "Podcast")
        make_deal(source="Podcast")
        make_deal(source="Podcast")
        with self.assertRaises(frappe.ValidationError) as caught:
            remove_vocabulary_value("source", "Podcast")
        message = str(caught.exception)
        self.assertIn("Podcast", message)
        self.assertIn("2 deals", message)

    def test_a_project_type_on_a_deal_cannot_be_removed_either(self):
        frappe.set_user(FOUNDER)
        add_vocabulary_value("project_type", "Music video")
        make_deal(project_type="Music video")
        with self.assertRaises(frappe.ValidationError):
            remove_vocabulary_value("project_type", "Music video")

    def test_removing_a_value_that_is_not_there_is_refused(self):
        frappe.set_user(FOUNDER)
        with self.assertRaises(frappe.DoesNotExistError):
            remove_vocabulary_value("source", "Carrier pigeon")

    # -- the two gates say the same thing --

    def test_doctype_permissions_agree_with_the_seam(self):
        # The endpoint checks the seam and then writes through the
        # DocType's own permissions, so a role the seam allows but the
        # DocType refuses would fail only at runtime, on the founder's
        # screen. Assert the agreement instead.
        for vocab in vocabulary.VOCABULARIES.values():
            granted = {
                row.role
                for row in frappe.get_all(
                    "DocPerm",
                    filters={
                        "parent": vocab.doctype,
                        "create": 1,
                        "write": 1,
                        "delete": 1,
                        "permlevel": 0,
                    },
                    fields=["role"],
                )
            }
            for role in vocab.managed_by:
                self.assertIn(
                    role,
                    granted,
                    f"{role} manages {vocab.label} in the seam but has no "
                    f"create/write/delete on {vocab.doctype}",
                )
            for role in {"Founder", "Producer"} - set(vocab.managed_by):
                self.assertNotIn(
                    role,
                    granted,
                    f"{role} does not manage {vocab.label} in the seam but "
                    f"may still write {vocab.doctype} directly",
                )

    def test_session_scope_tells_the_nav_which_lists_it_manages(self):
        from auraos.api import session_scope

        frappe.set_user(PRODUCER)
        scope = session_scope()
        self.assertEqual(scope["manages_vocabularies"], ["source"])
        # The producer reaches the Settings screen for that list alone -
        # not for the numbers on it.
        self.assertFalse(scope["can_read_settings"])

        frappe.set_user(FOUNDER)
        scope = session_scope()
        self.assertEqual(
            scope["manages_vocabularies"], ["source", "project_type"]
        )
        self.assertTrue(scope["can_read_settings"])

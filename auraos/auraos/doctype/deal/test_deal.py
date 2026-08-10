"""Seam tests for T3 (issue #5): deal pipeline — stage transitions,
lost-reason enforcement, ownership, and stage history.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.tests.utils import make_test_user

FOUNDER = "founder@test.auraos.local"
PRODUCER = "producer@test.auraos.local"
# A System User with neither app role — the negative control.
OUTSIDER = "outsider@test.auraos.local"

STAGES = [
    "Brief Received",
    "De-brief",
    "Breakdown",
    "Quote Sent",
    "Negotiation",
    "Won",
    "Lost",
]

LOST_REASONS = ["Price", "Timing", "Silence", "Competitor", "Scope"]


def make_company(company_name="Chungify Media"):
    existing = frappe.db.exists("Party Company", {"company_name": company_name})
    if existing:
        return frappe.get_doc("Party Company", existing)
    return frappe.get_doc(
        {"doctype": "Party Company", "company_name": company_name}
    ).insert()


def make_deal(**overrides):
    overrides.setdefault("company", make_company().name)
    doc = frappe.get_doc(
        {
            "doctype": "Deal",
            "title": "TVC cho Chungify",
            "deal_owner": FOUNDER,
            **overrides,
        }
    )
    doc.insert()
    return doc


class TestDeal(FrappeTestCase):
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

    # -- required fields & defaults --

    def test_deal_requires_title(self):
        with self.assertRaises(frappe.MandatoryError):
            frappe.get_doc(
                {"doctype": "Deal", "deal_owner": FOUNDER}
            ).insert()

    def test_deal_requires_company(self):
        # T3 walkthrough decision: every deal names its client company.
        with self.assertRaises(frappe.MandatoryError):
            frappe.get_doc(
                {
                    "doctype": "Deal",
                    "title": "No client",
                    "deal_owner": FOUNDER,
                }
            ).insert()

    def test_new_deal_starts_at_brief_received(self):
        deal = make_deal()
        self.assertEqual(deal.stage, "Brief Received")

    def test_deal_links_company_contact_and_brief(self):
        company = make_company()
        contact = frappe.get_doc(
            {
                "doctype": "Party Contact",
                "full_name": "Nguyễn Văn A",
                "phone": "0901234567",
                "company": company.name,
            }
        ).insert()
        deal = make_deal(
            company=company.name,
            contact=contact.name,
            brief="30s TVC, quay 2 ngày, deadline cuối tháng",
        )
        reloaded = frappe.get_doc("Deal", deal.name)
        self.assertEqual(reloaded.company, company.name)
        self.assertEqual(reloaded.contact, contact.name)
        self.assertIn("TVC", reloaded.brief)

    # -- stage transitions & history --

    def test_stage_moves_forward_through_pipeline(self):
        deal = make_deal()
        for stage in STAGES[1:-2]:  # up to Negotiation
            deal.stage = stage
            deal.save()
        self.assertEqual(
            frappe.get_doc("Deal", deal.name).stage, "Negotiation"
        )

    def test_invalid_stage_is_rejected(self):
        deal = make_deal()
        deal.stage = "Daydreaming"
        with self.assertRaises(frappe.ValidationError):
            deal.save()

    def test_insert_logs_initial_stage(self):
        deal = frappe.get_doc("Deal", make_deal().name)
        self.assertEqual(len(deal.stage_history), 1)
        entry = deal.stage_history[0]
        self.assertFalse(entry.from_stage)
        self.assertEqual(entry.to_stage, "Brief Received")
        self.assertTrue(entry.changed_on)
        self.assertEqual(entry.changed_by, "Administrator")

    def test_stage_change_appends_history_with_timestamp(self):
        deal = make_deal()
        deal.stage = "De-brief"
        deal.save()
        deal.stage = "Breakdown"
        deal.save()
        history = frappe.get_doc("Deal", deal.name).stage_history
        self.assertEqual(
            [(h.from_stage or "", h.to_stage) for h in history],
            [
                ("", "Brief Received"),
                ("Brief Received", "De-brief"),
                ("De-brief", "Breakdown"),
            ],
        )
        self.assertTrue(all(h.changed_on for h in history))

    def test_saving_without_stage_change_adds_no_history(self):
        deal = make_deal()
        deal.brief = "updated brief"
        deal.save()
        self.assertEqual(
            len(frappe.get_doc("Deal", deal.name).stage_history), 1
        )

    # -- lost-reason enforcement --

    def test_lost_without_reason_is_rejected(self):
        deal = make_deal()
        deal.stage = "Lost"
        with self.assertRaises(frappe.ValidationError):
            deal.save()

    def test_lost_with_reason_and_note_is_stored(self):
        deal = make_deal()
        deal.stage = "Lost"
        deal.lost_reason = "Silence"
        deal.lost_note = "Quote sent, đọc không rep"
        deal.save()
        reloaded = frappe.get_doc("Deal", deal.name)
        self.assertEqual(reloaded.stage, "Lost")
        self.assertEqual(reloaded.lost_reason, "Silence")
        self.assertEqual(reloaded.lost_note, "Quote sent, đọc không rep")

    def test_every_agreed_lost_reason_is_accepted(self):
        for reason in LOST_REASONS:
            deal = make_deal(title=f"Lost to {reason}")
            deal.stage = "Lost"
            deal.lost_reason = reason
            deal.save()

    def test_unknown_lost_reason_is_rejected(self):
        deal = make_deal()
        deal.stage = "Lost"
        deal.lost_reason = "Bad luck"
        with self.assertRaises(frappe.ValidationError):
            deal.save()

    def test_reviving_a_lost_deal_clears_reason_and_note(self):
        deal = make_deal()
        deal.stage = "Lost"
        deal.lost_reason = "Price"
        deal.lost_note = "quá chát"
        deal.save()
        deal.stage = "Negotiation"
        deal.save()
        reloaded = frappe.get_doc("Deal", deal.name)
        self.assertFalse(reloaded.lost_reason)
        self.assertFalse(reloaded.lost_note)

    # -- ownership --

    def test_owner_is_required(self):
        with self.assertRaises(
            (frappe.MandatoryError, frappe.ValidationError)
        ):
            frappe.get_doc(
                {
                    "doctype": "Deal",
                    "title": "Ownerless",
                    "company": make_company().name,
                }
            ).insert()

    def test_owner_defaults_to_creating_operating_user(self):
        company = make_company()
        frappe.set_user(PRODUCER)
        deal = frappe.get_doc(
            {
                "doctype": "Deal",
                "title": "Producer's deal",
                "company": company.name,
            }
        )
        deal.insert()
        self.assertEqual(deal.deal_owner, PRODUCER)

    def test_owner_reassigns_between_founder_and_producer(self):
        deal = make_deal(deal_owner=FOUNDER)
        deal.deal_owner = PRODUCER
        deal.save()
        self.assertEqual(
            frappe.get_doc("Deal", deal.name).deal_owner, PRODUCER
        )

    def test_owner_without_operating_role_is_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            make_deal(deal_owner=OUTSIDER)

    # -- role access --

    def assert_role_can_read_write(self, user):
        frappe.set_user(user)
        for ptype in ("read", "write", "create"):
            self.assertTrue(
                frappe.has_permission("Deal", ptype),
                f"{user} should have {ptype} on Deal",
            )
        deal = make_deal(title=f"Access probe {user}", deal_owner=user)
        deal.stage = "De-brief"
        deal.save()
        from frappe.client import get_list

        self.assertIn(
            deal.name,
            [row["name"] for row in get_list("Deal", fields=["name"])],
        )

    def test_founder_can_read_write_deals(self):
        self.assert_role_can_read_write(FOUNDER)

    def test_producer_can_read_write_deals(self):
        self.assert_role_can_read_write(PRODUCER)

    def test_user_without_app_role_is_denied(self):
        from frappe.client import get_list

        frappe.set_user(OUTSIDER)
        self.assertFalse(frappe.has_permission("Deal", "read"))
        with self.assertRaises(frappe.PermissionError):
            get_list("Deal")

    # -- operating_users endpoint (owner dropdown on the board) --

    def test_operating_users_lists_both_operating_roles(self):
        from auraos.api import operating_users

        frappe.set_user(PRODUCER)
        names = [u["name"] for u in operating_users()]
        self.assertIn(FOUNDER, names)
        self.assertIn(PRODUCER, names)
        self.assertNotIn(OUTSIDER, names)

    def test_operating_users_denied_without_app_role(self):
        from auraos.api import operating_users

        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            operating_users()

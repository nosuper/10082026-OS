"""Seam tests for T7 (issue #9): won deal → job.

Three seams:

1. **Conversion completeness** — a job created from a won deal carries
   the breakdown, packages, client and links with nothing re-entered,
   and refuses to run twice or on a deal that was never won.
2. **Stage flow** — the fixed production stages, movable by both
   operating roles, with every move logged.
3. **Revision counter** — rounds accumulate on the job and round 3+ is
   flagged as a chargeable change order.

Plus the standing permission boundary: the commission carried onto the
job stays founder-only through the document API, the list API and
search.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import create_job_from_deal, log_job_revision
from auraos.auraos.doctype.deal.test_deal import (
    FOUNDER,
    OUTSIDER,
    PRODUCER,
    make_company,
)
from auraos.auraos.doctype.deal.test_deal_breakdown import make_breakdown_deal
from auraos.auraos.doctype.job.job import FREE_REVISION_ROUNDS, STAGES
from auraos.tests.utils import make_test_user

PACKAGES = [
    {"title": "Nhân sự", "description": "Crew for the shoot"},
    {"title": "Thiết bị", "description": "Camera and lighting"},
]


def won_deal(**overrides):
    """A deal with breakdown, packages and links, sitting at Won."""
    lines = overrides.pop("cost_lines", None)
    deal = make_breakdown_deal(
        packages=[dict(row) for row in PACKAGES],
        deal_links=[
            {"label": "Brief", "url": "https://drive.google.com/drive/folders/x"}
        ],
        **({"cost_lines": lines} if lines else {}),
        **overrides,
    )
    # Package membership is set after insert so the lines can name
    # packages that only exist on this deal.
    deal.cost_lines[0].package = "Nhân sự"
    deal.cost_lines[1].package = "Thiết bị"
    deal.stage = "Won"
    deal.save()
    return frappe.get_doc("Deal", deal.name)


class TestJobConversion(FrappeTestCase):
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

    def test_job_carries_the_whole_breakdown_with_no_re_entry(self):
        deal = won_deal()
        job = frappe.get_doc("Job", create_job_from_deal(deal.name)["name"])

        self.assertEqual(job.deal, deal.name)
        self.assertEqual(job.title, deal.title)
        self.assertEqual(job.company, deal.company)
        self.assertEqual(job.job_owner, deal.deal_owner)

        self.assertEqual(
            [(row.description, row.unit_price, row.tax_type, row.package)
             for row in job.cost_lines],
            [(row.description, row.unit_price, row.tax_type, row.package)
             for row in deal.cost_lines],
        )
        self.assertEqual(
            [(row.title, row.description, row.price) for row in job.packages],
            [(row.title, row.description, row.price) for row in deal.packages],
        )
        self.assertEqual(
            [(row.label, row.url) for row in job.job_links],
            [(row.label, row.url) for row in deal.deal_links],
        )
        self.assertEqual(job.quote_mf_pct, deal.quote_mf_pct)
        self.assertEqual(job.vat_pct, deal.vat_pct)
        self.assertEqual(job.quote_total, deal.quote_total)
        self.assertEqual(job.quote_subtotal, deal.quote_subtotal)

    def test_job_carries_the_client_contact(self):
        contact = frappe.get_doc(
            {
                "doctype": "Party Contact",
                "full_name": "Trần Thị B",
                "phone": "0912345678",
                "company": make_company().name,
            }
        ).insert()
        deal = won_deal(contact=contact.name)
        job = frappe.get_doc("Job", create_job_from_deal(deal.name)["name"])
        self.assertEqual(job.contact, contact.name)

    def test_conversion_refuses_a_deal_that_is_not_won(self):
        deal = make_breakdown_deal()
        self.assertNotEqual(deal.stage, "Won")
        with self.assertRaises(frappe.ValidationError):
            create_job_from_deal(deal.name)

    def test_a_deal_converts_only_once(self):
        deal = won_deal()
        create_job_from_deal(deal.name)
        with self.assertRaises(frappe.ValidationError):
            create_job_from_deal(deal.name)

    def test_conversion_of_a_missing_deal_fails(self):
        with self.assertRaises(frappe.DoesNotExistError):
            create_job_from_deal("DEAL-does-not-exist")

    def test_producer_may_convert_a_won_deal(self):
        deal = won_deal()
        frappe.set_user(PRODUCER)
        job = frappe.get_doc("Job", create_job_from_deal(deal.name)["name"])
        self.assertEqual(job.stage, STAGES[0])

    def test_outsider_cannot_convert_or_read_jobs(self):
        deal = won_deal()
        job_name = create_job_from_deal(deal.name)["name"]
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            create_job_from_deal(deal.name)
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc("Job", job_name).check_permission("read")

    # -- files location (story 29) --

    def test_files_location_is_stored_on_the_job(self):
        deal = won_deal()
        job = frappe.get_doc("Job", create_job_from_deal(deal.name)["name"])
        job.files_location = "//nas/jobs/" + job.name
        job.save()
        self.assertEqual(
            frappe.get_doc("Job", job.name).files_location,
            "//nas/jobs/" + job.name,
        )

    # -- the producer boundary carried onto the job --

    def test_producer_cannot_read_the_carried_commission(self):
        from frappe.client import get, get_list

        deal = won_deal(commission_pct=7)
        job_name = create_job_from_deal(deal.name)["name"]
        self.assertEqual(
            frappe.db.get_value("Job", job_name, "commission_pct"), 7
        )

        frappe.set_user(PRODUCER)
        # Frappe masks unreadable permlevel fields to None/0 rather than
        # dropping the key; the property that matters is that the stored
        # value never comes through.
        fetched = get("Job", name=job_name)
        self.assertFalse(
            fetched.get("commission_pct"),
            "PERMISSION LEAK: producer read commission_pct via the document API",
        )
        rows = get_list("Job", filters={"name": job_name}, fields=["name", "commission_pct"])
        self.assertTrue(rows)
        self.assertTrue(
            all(row.get("commission_pct") is None for row in rows),
            "PERMISSION LEAK: producer read commission_pct via the list API",
        )

    def test_no_founder_only_job_field_is_in_global_search(self):
        # Global search indexes whole fields; a permlevel-1 field that
        # also asked to be indexed would leak past the document API.
        meta = frappe.get_meta("Job")
        leaked = [
            df.fieldname
            for df in meta.fields
            if df.permlevel and df.get("in_global_search")
        ]
        self.assertEqual(leaked, [])

    def test_producer_conversion_still_carries_the_commission(self):
        """A producer's conversion must not silently reset the rate.

        Frappe strips permlevel-1 fields from anything a producer
        session writes, so the carry has to happen outside the normal
        write path (Job.carry_commission).
        """
        deal = won_deal(commission_pct=3)
        frappe.set_user(PRODUCER)
        job_name = create_job_from_deal(deal.name)["name"]
        frappe.set_user("Administrator")
        self.assertEqual(
            frappe.db.get_value("Job", job_name, "commission_pct"), 3
        )


class TestJobStages(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")

    def setUp(self):
        frappe.set_user("Administrator")
        self.job = frappe.get_doc(
            "Job", create_job_from_deal(won_deal().name)["name"]
        )

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def test_a_new_job_starts_in_pre_production(self):
        self.assertEqual(self.job.stage, "Pre-production")

    def test_the_stage_set_is_the_agreed_production_flow(self):
        self.assertEqual(
            STAGES,
            [
                "Pre-production",
                "Shoot",
                "Post",
                "Feedback",
                "Delivery",
                "Nghiệm thu",
                "Chờ thanh toán",
                "Done",
            ],
        )

    def test_both_operating_roles_move_stages(self):
        frappe.set_user(PRODUCER)
        job = frappe.get_doc("Job", self.job.name)
        job.stage = "Shoot"
        job.save()

        frappe.set_user(FOUNDER)
        job = frappe.get_doc("Job", job.name)
        job.stage = "Post"
        job.save()

        self.assertEqual(frappe.get_doc("Job", job.name).stage, "Post")

    def test_every_move_is_logged_with_who_and_when(self):
        for stage in STAGES[1:]:
            self.job.stage = stage
            self.job.save()

        history = frappe.get_doc("Job", self.job.name).stage_history
        self.assertEqual(
            [(row.from_stage, row.to_stage) for row in history],
            [(None, "Pre-production")]
            + list(zip(STAGES, STAGES[1:])),
        )
        self.assertTrue(all(row.changed_by and row.changed_on for row in history))

    def test_an_unknown_stage_is_rejected(self):
        self.job.stage = "Đi nhậu"
        with self.assertRaises(frappe.ValidationError):
            self.job.save()


class TestJobRevisions(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")
        self.job = frappe.get_doc(
            "Job", create_job_from_deal(won_deal().name)["name"]
        )
        self.job.stage = "Feedback"
        self.job.save()

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def test_a_fresh_job_has_no_revisions(self):
        self.assertEqual(self.job.revision_rounds, 0)
        self.assertFalse(self.job.change_order_due)

    def test_free_rounds_are_not_chargeable(self):
        for round_number in range(1, FREE_REVISION_ROUNDS + 1):
            job = log_job_revision(self.job.name, f"Sửa lần {round_number}")
            self.assertEqual(job["revision_rounds"], round_number)
            self.assertFalse(job["change_order_due"])

    def test_round_three_is_flagged_as_a_chargeable_change_order(self):
        for i in range(FREE_REVISION_ROUNDS):
            log_job_revision(self.job.name, f"Sửa lần {i + 1}")
        job = log_job_revision(self.job.name, "Khách đổi ý lần nữa")

        self.assertEqual(job["revision_rounds"], FREE_REVISION_ROUNDS + 1)
        self.assertTrue(job["change_order_due"])

        rows = frappe.get_doc("Job", self.job.name).revisions
        self.assertEqual([row.round for row in rows], [1, 2, 3])
        self.assertEqual(
            [bool(row.chargeable) for row in rows], [False, False, True]
        )

    def test_a_revision_records_its_note_author_and_time(self):
        frappe.set_user(PRODUCER)
        log_job_revision(self.job.name, "Khách muốn đổi nhạc")
        row = frappe.get_doc("Job", self.job.name).revisions[0]
        self.assertEqual(row.note, "Khách muốn đổi nhạc")
        self.assertEqual(row.logged_by, PRODUCER)
        self.assertTrue(row.requested_on)

    def test_an_empty_revision_note_is_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            log_job_revision(self.job.name, "   ")

    def test_outsider_cannot_log_a_revision(self):
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            log_job_revision(self.job.name, "sneaky")

    def test_the_counter_survives_hand_edited_rows(self):
        """The rounds and the flag are derived, never trusted from input."""
        job = frappe.get_doc("Job", self.job.name)
        for i in range(FREE_REVISION_ROUNDS + 1):
            job.append(
                "revisions",
                {"round": 99, "chargeable": 0, "note": f"lần {i + 1}"},
            )
        job.save()

        reloaded = frappe.get_doc("Job", job.name)
        self.assertEqual(
            [row.round for row in reloaded.revisions],
            list(range(1, FREE_REVISION_ROUNDS + 2)),
        )
        self.assertTrue(reloaded.revisions[-1].chargeable)
        self.assertTrue(reloaded.change_order_due)
        self.assertEqual(reloaded.revision_rounds, FREE_REVISION_ROUNDS + 1)

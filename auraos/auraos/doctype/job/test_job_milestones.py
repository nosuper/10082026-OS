"""Seam tests for T10 (issue #12): payment milestones & invoice requests.

Four seams, one per acceptance criterion:

1. **Milestones per job** — name, share and trigger stage, created with
   the job and editable afterwards.
2. **Amount derivation** — every amount follows the job's quoted total,
   whatever anyone types, and the shares never bill more than the client
   agreed to.
3. **The collection flow** — chưa yêu cầu → đã yêu cầu KT → đã xuất HĐ →
   đã thanh toán, with its timestamps, walkable in both directions.
4. **The nudge and the invoice request** — when money counts as overdue,
   and what the accountant is actually sent.

The rules themselves are pinned framework-free in tests/test_milestones.py;
these tests prove the job and the API go through them.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import (
    create_job_from_deal,
    get_payment_terms_days,
    job_milestones,
    milestone_invoice_request,
    overdue_milestones,
    save_job_milestones,
    set_milestone_status,
    set_payment_terms_days,
)
from auraos.auraos.doctype.deal.test_deal import (
    FOUNDER,
    OUTSIDER,
    PRODUCER,
    make_company,
)
from auraos.auraos.doctype.job.job import DEFAULT_MILESTONES, STAGES
from auraos.auraos.doctype.job.test_job import won_deal
from auraos.auraos.doctype.job_payment_milestone.job_payment_milestone import (
    DEFAULT_PAYMENT_TERMS_DAYS,
)
from auraos.lib.milestones import milestone_amounts
from auraos.lib.money import format_vnd, round_vnd
from auraos.tests.utils import make_test_user

# Deliberately not the house default: a test that passes because the
# number happens to match the default proves nothing about the setting.
TERMS_DAYS = 5


def make_job(**overrides):
    return frappe.get_doc("Job", create_job_from_deal(won_deal(**overrides).name)["name"])


def fell_due(job_name, milestone, days_ago):
    """Age a milestone's due date — the only way to reach the nudge
    window without waiting a week for the test to pass."""
    frappe.db.set_value(
        "Job Payment Milestone",
        milestone,
        "due_on",
        frappe.utils.add_to_date(frappe.utils.now_datetime(), days=-days_ago),
        update_modified=False,
    )


class MilestoneTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")
        frappe.db.set_single_value("AuraOS Settings", "payment_terms_days", TERMS_DAYS)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.set_single_value("AuraOS Settings", "payment_terms_days", TERMS_DAYS)
        super().tearDown()


class TestMilestonePlan(MilestoneTestCase):
    """Seam 1: milestones per job — name, %, trigger stage."""

    def test_a_new_job_is_already_tracking_the_standard_split(self):
        """Money-in should not wait for someone to remember to set it up."""
        job = make_job()
        self.assertEqual(
            [(row.title, row.pct, row.trigger_stage) for row in job.payment_milestones],
            [
                (row["title"], row["pct"], row["trigger_stage"])
                for row in DEFAULT_MILESTONES
            ],
        )

    def test_the_split_is_editable_per_job(self):
        job = make_job()
        result = save_job_milestones(
            job.name,
            [
                {"title": "Đặt cọc", "pct": 30, "trigger_stage": "Pre-production"},
                {"title": "Sau quay", "pct": 40, "trigger_stage": "Post-production"},
                {"title": "Nghiệm thu", "pct": 30, "trigger_stage": "Client sign-off"},
            ],
        )
        self.assertEqual(
            [(row["title"], row["pct"], row["trigger_stage"]) for row in result["milestones"]],
            [
                ("Đặt cọc", 30, "Pre-production"),
                ("Sau quay", 40, "Post-production"),
                ("Nghiệm thu", 30, "Client sign-off"),
            ],
        )

    def test_editing_the_plan_keeps_what_a_milestone_has_already_earned(self):
        """Renaming the deposit must not un-pay it."""
        job = make_job()
        deposit = job.payment_milestones[0]
        set_milestone_status(job.name, deposit.name, "Paid")

        result = save_job_milestones(
            job.name,
            [
                {
                    "name": deposit.name,
                    "title": "Đặt cọc",
                    "pct": 50,
                    "trigger_stage": "Pre-production",
                }
            ],
        )
        self.assertEqual(result["milestones"][0]["status"], "Paid")
        self.assertTrue(result["milestones"][0]["paid_on"])

    def test_a_milestone_left_out_of_the_plan_is_dropped(self):
        job = make_job()
        kept = job.payment_milestones[0]
        result = save_job_milestones(
            job.name,
            [{"name": kept.name, "title": kept.title, "pct": 100,
              "trigger_stage": kept.trigger_stage}],
        )
        self.assertEqual(len(result["milestones"]), 1)

    def test_the_saved_order_is_the_order_the_plan_was_sent_in(self):
        """A row added after another was deleted must not inherit a
        position a surviving row already holds."""
        job = make_job()
        kept = job.payment_milestones[1]
        save_job_milestones(
            job.name,
            [
                {
                    "name": kept.name,
                    "title": kept.title,
                    "pct": 40,
                    "trigger_stage": kept.trigger_stage,
                },
                {"title": "Nghiệm thu", "pct": 60, "trigger_stage": "Complete"},
            ],
        )
        rows = frappe.get_doc("Job", job.name).payment_milestones
        self.assertEqual([row.idx for row in rows], [1, 2])
        self.assertEqual([row.title for row in rows], [kept.title, "Nghiệm thu"])

    def test_a_job_can_have_no_milestones_at_all(self):
        job = make_job()
        self.assertEqual(save_job_milestones(job.name, [])["milestones"], [])

    def test_a_nameless_milestone_is_rejected(self):
        job = make_job()
        with self.assertRaises(frappe.ValidationError):
            save_job_milestones(job.name, [{"title": "  ", "pct": 50}])

    def test_a_trigger_stage_outside_the_production_flow_is_rejected(self):
        job = make_job()
        with self.assertRaises(frappe.ValidationError):
            save_job_milestones(
                job.name, [{"title": "Đặt cọc", "pct": 50, "trigger_stage": "Đi nhậu"}]
            )

    def test_the_producer_may_plan_the_money_in_too(self):
        """The producer runs the stages that make a payment due; the
        founder-only boundary is overhead and commission, not the
        client's own invoice."""
        job = make_job()
        frappe.set_user(PRODUCER)
        result = save_job_milestones(
            job.name, [{"title": "Đặt cọc", "pct": 100, "trigger_stage": "Delivery"}]
        )
        self.assertEqual(len(result["milestones"]), 1)

    def test_an_outsider_reaches_none_of_it(self):
        job = make_job()
        milestone = job.payment_milestones[0].name
        frappe.set_user(OUTSIDER)
        for call in (
            lambda: job_milestones(job.name),
            lambda: save_job_milestones(job.name, []),
            lambda: set_milestone_status(job.name, milestone, "Paid"),
            lambda: milestone_invoice_request(job.name, milestone),
            lambda: overdue_milestones(),
        ):
            with self.assertRaises(frappe.PermissionError):
                call()

    def test_milestones_of_a_missing_job_are_a_404_not_a_403(self):
        with self.assertRaises(frappe.DoesNotExistError):
            job_milestones("JOB-does-not-exist")

    def test_a_milestone_from_another_job_is_not_found(self):
        job = make_job()
        with self.assertRaises(frappe.DoesNotExistError):
            set_milestone_status(job.name, "not-a-row", "Paid")


class TestMilestoneAmounts(MilestoneTestCase):
    """Seam 2: amounts derived from the quote total."""

    def test_each_milestone_bills_its_share_of_the_quoted_total(self):
        job = make_job()
        self.assertEqual(
            [row.amount for row in job.payment_milestones],
            milestone_amounts(
                job.quote_total, [row.pct for row in job.payment_milestones]
            ),
        )

    def test_a_half_share_is_half_the_quote(self):
        job = make_job()
        deposit = job.payment_milestones[0]
        self.assertEqual(deposit.pct, 50)
        self.assertAlmostEqual(deposit.amount, round_vnd(job.quote_total) / 2, delta=1)

    def test_a_fully_allocated_job_bills_exactly_what_was_quoted(self):
        job = make_job()
        save_job_milestones(
            job.name,
            [
                {"title": "Đặt cọc", "pct": 33.33, "trigger_stage": "Pre-production"},
                {"title": "Sau quay", "pct": 33.33, "trigger_stage": "Production"},
                {"title": "Nghiệm thu", "pct": 33.34, "trigger_stage": "Complete"},
            ],
        )
        reloaded = frappe.get_doc("Job", job.name)
        self.assertEqual(
            sum(row.amount for row in reloaded.payment_milestones),
            reloaded.quote_total,
        )

    def test_an_amount_typed_onto_a_milestone_is_overwritten(self):
        """The derivation is the point — a hand-typed amount is a number
        that silently disagrees with the quote the client signed."""
        job = make_job()
        job.payment_milestones[0].amount = 1
        job.save()
        self.assertEqual(
            frappe.get_doc("Job", job.name).payment_milestones[0].amount,
            milestone_amounts(job.quote_total, [job.payment_milestones[0].pct])[0],
        )

    def test_changing_a_share_moves_its_amount(self):
        job = make_job()
        result = save_job_milestones(
            job.name,
            [{"title": "Toàn bộ", "pct": 100, "trigger_stage": "Complete"}],
        )
        self.assertEqual(result["milestones"][0]["amount"], round_vnd(job.quote_total))

    def test_milestones_cannot_bill_more_than_the_client_agreed_to(self):
        job = make_job()
        with self.assertRaises(frappe.ValidationError):
            save_job_milestones(
                job.name,
                [
                    {"title": "Đặt cọc", "pct": 60, "trigger_stage": "Pre-production"},
                    {"title": "Nghiệm thu", "pct": 60, "trigger_stage": "Complete"},
                ],
            )

    def test_a_half_planned_job_is_allowed(self):
        """Milestones get filled in over the life of a job; billing less
        than 100% so far is a plan in progress, not an error."""
        job = make_job()
        result = save_job_milestones(
            job.name, [{"title": "Đặt cọc", "pct": 30, "trigger_stage": "Pre-production"}]
        )
        self.assertEqual(result["milestones"][0]["pct"], 30)


class TestCollectionFlow(MilestoneTestCase):
    """Seam 3: the four-status flow and its timestamps."""

    def setUp(self):
        super().setUp()
        self.job = make_job()
        self.milestone = self.job.payment_milestones[0].name

    def test_a_new_milestone_has_not_been_asked_for(self):
        self.assertEqual(
            job_milestones(self.job.name)["milestones"][0]["status"], "Not requested"
        )

    def test_the_flow_runs_the_four_agreed_states(self):
        for status in ("Requested", "Invoiced", "Paid"):
            row = set_milestone_status(self.job.name, self.milestone, status)
            self.assertEqual(row["status"], status)

    def test_each_step_records_when_it_happened(self):
        row = set_milestone_status(self.job.name, self.milestone, "Invoiced")
        self.assertTrue(row["requested_on"])
        self.assertTrue(row["invoiced_on"])
        self.assertFalse(row["paid_on"])

    def test_a_step_already_taken_keeps_its_original_time(self):
        asked = set_milestone_status(self.job.name, self.milestone, "Requested")
        paid = set_milestone_status(self.job.name, self.milestone, "Paid")
        self.assertEqual(paid["requested_on"], asked["requested_on"])

    def test_a_status_set_by_accident_can_be_walked_back(self):
        """The T6 lesson: no one-way doors."""
        set_milestone_status(self.job.name, self.milestone, "Paid")
        row = set_milestone_status(self.job.name, self.milestone, "Requested")
        self.assertEqual(row["status"], "Requested")
        self.assertFalse(row["paid_on"])
        self.assertFalse(row["invoiced_on"])
        self.assertTrue(row["requested_on"])

    def test_an_unknown_status_is_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            set_milestone_status(self.job.name, self.milestone, "đã quên")

    def test_a_hand_typed_timestamp_is_overwritten(self):
        job = frappe.get_doc("Job", self.job.name)
        job.payment_milestones[0].paid_on = frappe.utils.now_datetime()
        job.save()
        self.assertFalse(frappe.get_doc("Job", self.job.name).payment_milestones[0].paid_on)


class TestOverdueNudge(MilestoneTestCase):
    """Seam 4a: when money counts as overdue."""

    def setUp(self):
        super().setUp()
        self.job = make_job()
        self.deposit = self.job.payment_milestones[0]

    def nudges_for_this_job(self):
        """The nudge endpoint spans every job the session can list, and
        the suite leaves other jobs behind; only ours is under test."""
        return [
            row
            for row in overdue_milestones()["milestones"]
            if row["job"] == self.job.name
        ]

    def test_a_milestone_falls_due_when_the_job_reaches_its_trigger_stage(self):
        # The deposit triggers on Pre-production, where a new job starts.
        self.assertTrue(job_milestones(self.job.name)["milestones"][0]["due_on"])

    def test_a_milestone_whose_stage_is_still_ahead_has_not_fallen_due(self):
        final = job_milestones(self.job.name)["milestones"][1]
        self.assertEqual(final["trigger_stage"], "Client sign-off")
        self.assertFalse(final["due_on"])

    def test_moving_the_job_on_makes_the_later_milestone_due(self):
        job = frappe.get_doc("Job", self.job.name)
        job.stage = "Client sign-off"
        job.save()
        self.assertTrue(job_milestones(self.job.name)["milestones"][1]["due_on"])

    def test_a_milestone_inside_the_payment_terms_does_not_nudge(self):
        self.assertEqual(self.nudges_for_this_job(), [])

    def test_money_uncollected_past_the_terms_nudges_the_founder(self):
        fell_due(self.job.name, self.deposit.name, days_ago=TERMS_DAYS + 3)

        nudges = self.nudges_for_this_job()
        self.assertEqual(len(nudges), 1)
        self.assertEqual(nudges[0]["job_title"], self.job.title)
        self.assertEqual(nudges[0]["amount"], self.deposit.amount)
        self.assertEqual(nudges[0]["days_overdue"], 3)
        # The job page reads the same row builder, so it shows the same
        # lateness rather than a blank number.
        page_row = job_milestones(self.job.name)["milestones"][0]
        self.assertTrue(page_row["overdue"])
        self.assertEqual(page_row["days_overdue"], 3)
        self.assertEqual(overdue_milestones()["payment_terms_days"], TERMS_DAYS)

    def test_a_paid_milestone_stops_nudging(self):
        fell_due(self.job.name, self.deposit.name, days_ago=TERMS_DAYS + 3)
        set_milestone_status(self.job.name, self.deposit.name, "Paid")
        self.assertEqual(self.nudges_for_this_job(), [])

    def test_an_invoiced_but_unpaid_milestone_still_nudges(self):
        """The invoice went out; the money did not come in."""
        fell_due(self.job.name, self.deposit.name, days_ago=TERMS_DAYS + 1)
        set_milestone_status(self.job.name, self.deposit.name, "Invoiced")
        self.assertEqual(len(self.nudges_for_this_job()), 1)

    def test_zero_payment_terms_turn_the_nudge_off(self):
        fell_due(self.job.name, self.deposit.name, days_ago=90)
        set_payment_terms_days(0)
        self.assertEqual(overdue_milestones()["milestones"], [])

    def test_the_payment_terms_are_the_founders_to_set(self):
        self.assertEqual(get_payment_terms_days(), TERMS_DAYS)
        set_payment_terms_days(14)
        self.assertEqual(get_payment_terms_days(), 14)

        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            set_payment_terms_days(1)

    def test_a_site_nobody_configured_still_chases_money(self):
        """The nudge must not depend on someone visiting Settings first —
        a Single's row is only written when its doc is saved, and an
        unset Int reads back as 0, which is the "never nudge" setting."""
        frappe.db.delete(
            "Singles", {"doctype": "AuraOS Settings", "field": "payment_terms_days"}
        )
        frappe.clear_document_cache("AuraOS Settings", "AuraOS Settings")
        self.assertEqual(get_payment_terms_days(), DEFAULT_PAYMENT_TERMS_DAYS)

    def test_dragging_a_job_back_un_dues_a_milestone_nobody_has_acted_on(self):
        job = frappe.get_doc("Job", self.job.name)
        job.stage = STAGES[-1]
        job.save()
        self.assertTrue(job_milestones(self.job.name)["milestones"][1]["due_on"])

        job = frappe.get_doc("Job", self.job.name)
        job.stage = "Production"
        job.save()
        self.assertFalse(job_milestones(self.job.name)["milestones"][1]["due_on"])

    def test_money_already_asked_for_stays_due_when_the_job_reopens(self):
        job = frappe.get_doc("Job", self.job.name)
        job.stage = STAGES[-1]
        job.save()
        final = frappe.get_doc("Job", self.job.name).payment_milestones[1]
        set_milestone_status(self.job.name, final.name, "Requested")

        job = frappe.get_doc("Job", self.job.name)
        job.stage = "Production"
        job.save()
        self.assertTrue(job_milestones(self.job.name)["milestones"][1]["due_on"])


class TestInvoiceRequest(MilestoneTestCase):
    """Seam 4b: the one-click text for the accountant."""

    def setUp(self):
        super().setUp()
        company = make_company()
        company.tax_code = "0312345678"
        company.address = "12 Nguyễn Huệ, Quận 1, TP.HCM"
        company.save()
        self.job = make_job()
        self.deposit = self.job.payment_milestones[0]

    def test_the_request_carries_the_client_tax_info_and_the_amount(self):
        text = milestone_invoice_request(self.job.name, self.deposit.name)["text"]

        self.assertIn("Chungify Media", text)
        self.assertIn("0312345678", text)
        self.assertIn("12 Nguyễn Huệ, Quận 1, TP.HCM", text)
        self.assertIn(self.job.title, text)
        self.assertIn(self.deposit.title, text)
        self.assertIn(format_vnd(self.deposit.amount), text)

    def test_the_request_splits_the_amount_out_of_its_vat(self):
        text = milestone_invoice_request(self.job.name, self.deposit.name)["text"]
        self.assertIn(f"VAT {round(self.job.vat_pct)}%", text)
        self.assertIn("Chưa VAT:", text)

    def test_asking_for_the_text_does_not_move_the_milestone_along(self):
        """Pasting into Zalo is a human act — marking it requested is a
        separate decision the founder can undo."""
        milestone_invoice_request(self.job.name, self.deposit.name)
        self.assertEqual(
            job_milestones(self.job.name)["milestones"][0]["status"], "Not requested"
        )

    def test_the_producer_may_generate_the_request(self):
        frappe.set_user(PRODUCER)
        text = milestone_invoice_request(self.job.name, self.deposit.name)["text"]
        self.assertIn("0312345678", text)

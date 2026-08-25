"""Seam tests for the break-even line (auraos.api.break_even, #14).

The arithmetic - which month a job lands in, what a surplus is, why a
flagged purchase sits outside the line - is pinned framework-free in
tests/test_breakeven.py. What only a site can prove is the wiring:

1. **The two sides come from where they already live.** A job's margin
   here is the very number `job_profitability` prints on the Reports
   screen, and a month's overhead here is the very number the tax card
   prints. Both are asserted against those endpoints rather than against
   a figure typed into this file, because a constant would pass while
   the two screens quietly diverged.
2. **The closed stage is one fact, not two.** `auraos.lib.breakeven`
   names the stage that ends a job, and it is framework-free by
   contract, so nothing stops it drifting from `job.STAGES` except this
   assertion.
3. **A job that has not finished spending is separated, never added
   quietly.** A surplus made of open jobs is an opinion about breaking
   even, and the confident half has to survive the trip over HTTP.
4. **Nothing in the payload proposes a floor.** #14 says show, don't
   suggest. The endpoint must not read `margin_floor_pct`, must not
   write it, and must not ship a key a screen could render as advice.
5. **It is founder-only and refused outright** - the payroll and the
   rent against what the company earns. The doctypes underneath grant no
   Producer row, but this endpoint reads every job through
   `frappe.get_all`, which skips the matrix by design, so the gate has
   to be here too.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import (
    break_even,
    create_job_from_deal,
    job_profitability,
    log_company_expense,
    period_tax_position,
)
from auraos.auraos.doctype.deal.test_deal import FOUNDER, PRODUCER
from auraos.auraos.doctype.job.job import CLOSED_STAGE, STAGES
from auraos.auraos.doctype.job.test_job import won_deal
from auraos.lib import breakeven
from auraos.tests.contract import (
    assert_counts,
    assert_iso_date,
    assert_keys,
    assert_money,
    assert_no_founder_chain,
)
from auraos.tests.utils import make_test_user

ACCOUNT = "Tài khoản ngân hàng"

# Wide enough to hold every job this suite makes, whatever day it runs.
# The window has to reach today, because a job is booked the moment it is
# created and these are created now.
WINDOW = ("2020-01-01", "2099-12-31")

# Every key a month row carries, and every key the range total carries.
# Listed once, so renaming one fails a test rather than a screen.
MONTH_KEYS = [
    "month",
    "overhead",
    "flagged_overhead",
    "overhead_count",
    "contribution",
    "final_contribution",
    "provisional_contribution",
    "job_count",
    "final_count",
    "surplus",
    "final_surplus",
    "coverage_pct",
    "covered",
]

TOTAL_KEYS = [key for key in MONTH_KEYS if key != "month"]


class BreakEvenTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        if not frappe.db.exists("Cash Account", ACCOUNT):
            frappe.get_doc(
                {"doctype": "Cash Account", "account_name": ACCOUNT}
            ).insert(ignore_permissions=True)

    def setUp(self):
        frappe.set_user(FOUNDER)

    def tearDown(self):
        frappe.set_user("Administrator")

    def a_job(self, stage=None):
        frappe.set_user("Administrator")
        job = frappe.get_doc("Job", create_job_from_deal(won_deal().name)["name"])
        if stage:
            job.stage = stage
            job.save()
        frappe.set_user(FOUNDER)
        return job

    def this_month(self, payload):
        """The month row every job in this suite lands in: today's."""
        month = frappe.utils.getdate(frappe.utils.today()).strftime("%Y-%m")
        rows = [row for row in payload["months"] if row["month"] == month]
        self.assertEqual(len(rows), 1, f"no row for {month}")
        return rows[0]

    # -- one derivation, two screens --

    def test_a_job_margin_here_is_the_margin_the_reports_screen_prints(self):
        """Asserted against the other endpoint, never against a constant.

        A number typed into this file would keep passing while the two
        screens diverged, which is the failure this test exists to catch.
        """
        job = self.a_job()

        margins = {row["name"]: row["margin"] for row in job_profitability(include_closed=1)}
        line = break_even(*WINDOW)
        booked = {row["job"]: row["margin"] for row in line["jobs"]}

        self.assertIn(job.name, booked)
        self.assertEqual(booked[job.name], margins[job.name])

    def test_a_month_overhead_here_is_the_overhead_the_tax_card_prints(self):
        """The same block, rendered twice - `auraos.lib.tax.overheads`."""
        today = frappe.utils.today()
        log_company_expense(9_000_000, spent_on=today, description="Thuê văn phòng")

        month = frappe.utils.get_first_day(today)
        card = period_tax_position(month, frappe.utils.get_last_day(today))
        line = break_even(month, frappe.utils.get_last_day(today))

        self.assertEqual(
            line["total"]["overhead"], card["overheads"]["paid_total"]
        )

    def test_the_stage_that_ends_a_job_is_one_fact(self):
        """`auraos.lib.breakeven` is framework-free by contract, so it
        names the closed stage rather than importing it. Nothing stops
        the two drifting except this."""
        self.assertEqual(breakeven.CLOSED_STAGE, CLOSED_STAGE)
        self.assertEqual(breakeven.CLOSED_STAGE, STAGES[-1])

    # -- what can still move --

    def test_an_open_job_is_not_counted_as_final(self):
        """A surplus made of open jobs is an opinion about breaking even,
        and the distinction has to survive the trip over HTTP."""
        open_job = self.a_job(stage=STAGES[1])
        closed_job = self.a_job(stage=CLOSED_STAGE)

        month = self.this_month(break_even(*WINDOW))
        booked = {row["job"]: row for row in break_even(*WINDOW)["jobs"]}

        self.assertFalse(booked[open_job.name]["is_final"])
        self.assertTrue(booked[closed_job.name]["is_final"])
        self.assertGreaterEqual(month["job_count"], 2)
        self.assertEqual(
            month["contribution"],
            month["final_contribution"] + month["provisional_contribution"],
        )

    # -- show, don't suggest --

    def test_nothing_in_the_payload_proposes_a_floor(self):
        """#14's own wording, asserted mechanically.

        A key called `recommended_floor` would be read as a
        recommendation the moment it existed, and the floor is the
        founder's judgement against things this app cannot see.
        """
        payload = break_even(*WINDOW)
        keys = set(payload) | set(payload["total"]) | set(MONTH_KEYS)
        forbidden = ("floor", "recommend", "suggest", "target", "advice")

        self.assertEqual(
            [key for key in keys if any(word in key for word in forbidden)], []
        )
        self.assertTrue(
            any(one["figure"] == "the margin floor" for one in payload["caveats"])
        )

    def test_both_bases_and_the_caveats_travel_in_the_payload(self):
        """A founder reading a surplus needs to know it may be made of a
        job that has not finished spending - and the words for that
        belong beside the number rather than in a screen that would have
        to invent them."""
        payload = break_even(*WINDOW)

        self.assertIn("the month the job was booked", payload["contribution_basis"])
        self.assertIn("the day the money left the account", payload["overhead_basis"])
        self.assertTrue(payload["caveats"])

    # -- the payload is a contract --

    def test_the_payload_is_the_shape_the_screen_was_written_against(self):
        """Issue #83's promise, held to this endpoint too: every key
        present, money as whole đồng, dates as ISO strings."""
        self.a_job()
        log_company_expense(9_000_000, spent_on=frappe.utils.today())
        payload = break_even(*WINDOW)

        assert_keys(
            self,
            payload,
            [
                "contribution_basis",
                "overhead_basis",
                "months",
                "total",
                "jobs",
                "unbooked",
                "flagged",
                "by_category",
                "caveats",
                "committed",
                "date_from",
                "date_to",
            ],
        )
        assert_iso_date(self, payload["date_from"], "date_from")
        assert_iso_date(self, payload["date_to"], "date_to")
        assert_keys(self, payload["total"], TOTAL_KEYS, "total")
        assert_money(
            self,
            payload["total"],
            "overhead",
            "flagged_overhead",
            "contribution",
            "final_contribution",
            "provisional_contribution",
            "surplus",
            "final_surplus",
            where="total",
        )
        assert_counts(
            self,
            payload["total"],
            "overhead_count",
            "job_count",
            "final_count",
            where="total",
        )

        month = self.this_month(payload)
        assert_keys(self, month, MONTH_KEYS, "month")
        assert_money(self, month, "overhead", "contribution", "surplus", where="month")

    def test_the_payload_carries_no_founder_profit_chain(self):
        """Founder-only is not a licence to leak the profit chain.

        This screen is the founder's, and it still has no business
        shipping commission, CM or TNDN: those are `deal_profit`'s, and a
        payload that cannot hold them cannot leak them if this endpoint's
        gate is ever loosened.
        """
        self.a_job()
        assert_no_founder_chain(self, break_even(*WINDOW), "break_even")

    # -- the boundary --

    def test_a_producer_is_refused_outright(self):
        """Not an empty payload - refused.

        The doctypes underneath grant no Producer row, but this endpoint
        reads every job through `frappe.get_all`, which skips the matrix
        by design. The gate has to be here as well as there.
        """
        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            break_even(*WINDOW)

    def test_a_range_is_required_rather_than_guessed(self):
        with self.assertRaises(frappe.ValidationError):
            break_even(None, None)

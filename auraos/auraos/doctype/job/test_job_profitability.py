"""Seam tests for per-job profitability (auraos.api.job_profitability).

The arithmetic is pinned framework-free in tests/test_reporting.py.
What only a site can prove is the wiring:

1. **It is the settlement comparison, totalled.** The quoted and actual
   cost on a profitability row are exactly the numbers the job's money
   screen already shows per category - one comparison, two surfaces.
2. **Money in is the milestones collected.** A milestone marked Paid is
   money in; one merely invoiced is not, and a job whose billing nobody
   has planned yet still reads.
3. **An overspent job says so.** Spending past the revenue turns the
   margin negative rather than flattening it at zero.
4. **Margin, never the profit chain.** A producer gets the whole row,
   and the row has no commission, CM, profit before tax, TNDN or net
   profit on it for anyone.
5. **The row is a contract** (issue #83). Now that a separate React
   frontend reads it over HTTP, the key set and the integer đồng are
   asserted as an interface rather than left to whatever the endpoint
   happens to return.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import (
    create_job_from_deal,
    job_milestones,
    job_money,
    job_profitability,
    log_job_expense,
    save_job_milestones,
    set_milestone_status,
)
from auraos.auraos.doctype.deal.test_deal import FOUNDER, OUTSIDER, PRODUCER
from auraos.auraos.doctype.job.job import STAGES
from auraos.tests.contract import (
    FOUNDER_ONLY,
    assert_keys,
    assert_money,
    assert_no_founder_chain,
)
from auraos.tests.utils import make_test_user
from auraos.auraos.doctype.job.test_job import won_deal

# Every key a row carries. Listed once: the boundary test proves a
# producer gets exactly this and no founder field, and the contract test
# proves the frontend gets exactly this and no renamed one.
ROW_KEYS = [
    "actual_cost",
    "client",
    "collected",
    "company",
    "margin",
    "margin_pct",
    "name",
    "quoted_cost",
    "quoted_total",
    "revenue_ex_vat",
    "stage",
    "title",
    "uncollected",
]

# Every đồng figure on the row - all of them whole numbers, none of them
# a float that a screen would have to round before printing.
MONEY_KEYS = (
    "quoted_total",
    "collected",
    "uncollected",
    "revenue_ex_vat",
    "quoted_cost",
    "actual_cost",
    "margin",
)

CATEGORY = "Thiết bị"


def profit_of(job):
    (row,) = job_profitability(job)
    return row


class ProfitabilityTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")
        self.job = create_job_from_deal(won_deal().name)["name"]
        self.doc = frappe.get_doc("Job", self.job)

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def revenue(self):
        """What the company keeps of the quoted price, VAT excluded."""
        return round(self.doc.quote_subtotal + self.doc.quote_mf_amount)


class TestJobProfitability(ProfitabilityTestCase):
    def test_a_row_names_the_job_the_client_and_where_it_stands(self):
        row = profit_of(self.job)

        self.assertEqual(row["name"], self.job)
        self.assertEqual(row["title"], self.doc.title)
        self.assertEqual(row["company"], self.doc.company)
        self.assertEqual(
            row["client"],
            frappe.db.get_value("Party Company", self.doc.company, "company_name"),
        )
        self.assertEqual(row["stage"], self.doc.stage)

    def test_a_job_nobody_has_spent_on_yet_keeps_its_whole_revenue(self):
        row = profit_of(self.job)

        self.assertEqual(row["quoted_total"], round(self.doc.quote_total))
        self.assertEqual(row["actual_cost"], 0)
        self.assertEqual(row["margin"], self.revenue())
        self.assertEqual(row["margin_pct"], 100.0)

    def test_quoted_and_actual_are_the_money_screens_own_comparison(self):
        """One comparison, two surfaces - job_money renders it per
        category, this totals it."""
        log_job_expense(self.job, 5_000_000, category=CATEGORY)

        money = job_money(self.job)
        row = profit_of(self.job)
        self.assertEqual(row["quoted_cost"], money["quoted_total"])
        self.assertEqual(row["actual_cost"], money["spent_total"])

    def test_spending_eats_into_the_margin(self):
        log_job_expense(self.job, 5_000_000, category=CATEGORY)

        row = profit_of(self.job)
        self.assertEqual(row["actual_cost"], 5_000_000)
        self.assertEqual(row["margin"], self.revenue() - 5_000_000)

    def test_a_job_that_overspent_reads_negative(self):
        log_job_expense(self.job, self.revenue() + 1_000_000, category=CATEGORY)

        row = profit_of(self.job)
        self.assertEqual(row["margin"], -1_000_000)
        self.assertLess(row["margin_pct"], 0)


class TestMoneyCollected(ProfitabilityTestCase):
    def paid_first_milestone(self):
        first = job_milestones(self.job)["milestones"][0]
        set_milestone_status(self.job, first["name"], "Paid")
        return first["amount"]

    def test_only_a_paid_milestone_counts_as_collected(self):
        first = job_milestones(self.job)["milestones"][0]
        set_milestone_status(self.job, first["name"], "Invoiced")
        self.assertEqual(profit_of(self.job)["collected"], 0)

        set_milestone_status(self.job, first["name"], "Paid")
        self.assertEqual(profit_of(self.job)["collected"], first["amount"])

    def test_what_is_left_is_the_quoted_total_less_what_came_in(self):
        amount = self.paid_first_milestone()

        row = profit_of(self.job)
        self.assertEqual(row["uncollected"], row["quoted_total"] - amount)
        self.assertEqual(row["collected"] + row["uncollected"], row["quoted_total"])

    def test_a_job_with_no_milestones_has_collected_nothing(self):
        """The billing plan is editable, and empty is a state a job
        passes through - not an error."""
        save_job_milestones(self.job, [])

        row = profit_of(self.job)
        self.assertEqual(row["collected"], 0)
        self.assertEqual(row["uncollected"], row["quoted_total"])

    def test_a_job_with_no_expenses_and_no_milestones_is_all_zeros(self):
        save_job_milestones(self.job, [])

        row = profit_of(self.job)
        self.assertEqual(row["collected"], 0)
        self.assertEqual(row["actual_cost"], 0)


class TestProfitabilityScope(ProfitabilityTestCase):
    def test_with_no_argument_every_open_job_is_answered(self):
        names = [row["name"] for row in job_profitability()]

        self.assertIn(self.job, names)
        self.assertEqual(len(names), len(set(names)))

    def test_a_finished_job_drops_off_the_open_list(self):
        self.doc.stage = STAGES[-1]
        self.doc.save()

        self.assertNotIn(self.job, [row["name"] for row in job_profitability()])
        # Asked for by name it still answers - a finished job is still
        # the one whose margin the founder wants to read.
        self.assertEqual(profit_of(self.job)["name"], self.job)

    def test_a_finished_job_is_answered_when_the_report_asks_for_it(self):
        """The margin report's reading: a closed job is the only one
        whose margin is final, so a ranking that dropped it would rank
        the studio on its unfinished work."""
        self.doc.stage = STAGES[-1]
        self.doc.save()

        names = [row["name"] for row in job_profitability(include_closed=1)]
        self.assertIn(self.job, names)
        self.assertEqual(len(names), len(set(names)))

    def test_the_widened_board_still_carries_the_open_jobs(self):
        """include_closed adds the finished ones, it does not swap the
        question for a closed-jobs-only one."""
        self.assertIn(self.job, [row["name"] for row in job_profitability(include_closed=1)])

    def test_a_row_says_which_of_the_two_it_is(self):
        """The screen tells them apart on the answer rather than by
        asking twice, so the stage has to come back on the row."""
        self.doc.stage = STAGES[-1]
        self.doc.save()

        (row,) = [
            row for row in job_profitability(include_closed=1) if row["name"] == self.job
        ]
        self.assertEqual(row["stage"], STAGES[-1])

    def test_the_flag_arrives_over_http_as_a_string(self):
        """Whitelisted arguments come off the query string, so "1" has
        to mean the same as 1 and "0" the same as 0."""
        self.doc.stage = STAGES[-1]
        self.doc.save()

        self.assertIn(self.job, [row["name"] for row in job_profitability(include_closed="1")])
        self.assertNotIn(
            self.job, [row["name"] for row in job_profitability(include_closed="0")]
        )

    def test_a_job_that_does_not_exist_is_missing_not_forbidden(self):
        with self.assertRaises(frappe.DoesNotExistError):
            job_profitability("JOB-does-not-exist")


class TestProfitabilityBoundary(ProfitabilityTestCase):
    def test_the_producer_reads_margin_and_none_of_the_profit_chain(self):
        """Margin and money in are producer-visible by decision; the
        founder's chain is a different question through a different
        door (deal_profit)."""
        log_job_expense(self.job, 5_000_000, category=CATEGORY)

        frappe.set_user(PRODUCER)
        row = profit_of(self.job)
        self.assertTrue(FOUNDER_ONLY.isdisjoint(row))
        assert_no_founder_chain(self, row, "producer profitability row")
        assert_keys(self, row, ROW_KEYS, "producer profitability row")

    def test_the_producer_reads_the_same_numbers_the_founder_does(self):
        log_job_expense(self.job, 5_000_000, category=CATEGORY)

        frappe.set_user(FOUNDER)
        founders = profit_of(self.job)
        frappe.set_user(PRODUCER)
        self.assertEqual(profit_of(self.job), founders)

    def test_an_outsider_reads_no_job_at_all(self):
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            job_profitability(self.job)
        with self.assertRaises(frappe.PermissionError):
            job_profitability()


class TestProfitabilityContract(ProfitabilityTestCase):
    """The row as the React frontend receives it (issue #83, spec #81).

    Shape only. Whether the margin is right belongs to lib/reporting and
    is pinned in tests/; what this file pins is that it is still called
    `margin` and still arrives as a number the frontend can print.
    """

    def test_the_row_carries_every_documented_key_and_no_other(self):
        log_job_expense(self.job, 5_000_000, category=CATEGORY)

        assert_keys(self, profit_of(self.job), ROW_KEYS, "profitability row")

    def test_every_figure_on_the_row_is_whole_dong(self):
        log_job_expense(self.job, 4_500_001, category=CATEGORY)
        first = job_milestones(self.job)["milestones"][0]
        set_milestone_status(self.job, first["name"], "Paid")

        assert_money(self, profit_of(self.job), *MONEY_KEYS, where="profitability row")

    def test_the_margin_percentage_is_a_number_the_screen_formats(self):
        """A percentage is not money, so it stays a float - and a job
        quoted at nothing has no percentage rather than a misleading 0."""
        row = profit_of(self.job)
        self.assertIs(type(row["margin_pct"]), float)

    def test_a_job_nothing_has_happened_to_yet_is_zeroed_not_absent(self):
        """The shape a job has on the day it is converted: every key
        present, every unspent figure a zero."""
        save_job_milestones(self.job, [])

        row = profit_of(self.job)
        assert_keys(self, row, ROW_KEYS, "untouched profitability row")
        assert_money(self, row, *MONEY_KEYS, where="untouched profitability row")
        self.assertEqual(row["collected"], 0)
        self.assertEqual(row["actual_cost"], 0)

    def test_the_row_carries_no_date_at_all(self):
        """Named rather than assumed. Spec #81 promises ISO dates where
        there are dates; this payload has none - not the job's stage
        date, not the last expense, not when the money came in - so a
        screen wanting "as of when" has to ask somewhere else.
        """
        row = profit_of(self.job)
        self.assertEqual([key for key in row if key.endswith(("_on", "_at"))], [])

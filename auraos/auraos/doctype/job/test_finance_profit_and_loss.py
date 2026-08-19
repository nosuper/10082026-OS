"""Contract tests for the profit and loss (auraos.api.finance_profit_and_loss).

The arithmetic is pinned framework-free in tests/test_finance.py. This
file is the seam: the endpoint composes the two reports that already
ship, and what only a site can prove is that the composition kept their
promises rather than making new ones.

1. **It is the two reports, not a third count.** A month's income here
   is the number finance_income prints for that month and a month's
   expense is the number finance_expenses prints. Nothing recounts a
   row, so nothing can disagree about one.
2. **Both permission checks still apply.** Each side carries its own,
   so a session that may not read one side gets no profit and loss at
   all rather than a profit and loss with that side missing - which
   would be a lie in the shape of a number.
3. **A period with no activity is zeroed, not broken.** A studio on day
   one reads zeros down the column and a dash where the margin would
   be, because a month nothing came in has no margin rather than a 0%
   one, and 0% would read as breaking even.
4. **No founder chain rides along.** Cash in and cash out; commission,
   CM, profit before tax, TNDN and net profit are a different door.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import (
    create_job_from_deal,
    finance_expenses,
    finance_income,
    finance_profit_and_loss,
    job_milestones,
    log_job_expense,
    set_milestone_status,
)
from auraos.auraos.doctype.deal.test_deal import FOUNDER, OUTSIDER, PRODUCER
from auraos.auraos.doctype.job.test_job import won_deal
from auraos.lib.finance import CASH_BASIS
from auraos.tests.contract import (
    assert_counts,
    assert_iso_date,
    assert_keys,
    assert_money,
    assert_no_founder_chain,
)
from auraos.tests.utils import make_test_user

REPORT_KEYS = ["date_from", "date_to", "basis", "months", "total"]
MONTH_KEYS = [
    "month",
    "month_start",
    "income",
    "expense",
    "profit",
    "margin_pct",
    "income_count",
    "expense_count",
]
TOTAL_KEYS = [
    "income",
    "expense",
    "profit",
    "margin_pct",
    "income_count",
    "expense_count",
]

# One of the categories won_deal() quotes, so an expense may name it.
CATEGORY = "Thiết bị"

# A window this company had not been founded in.
DEAD_RANGE = ("2019-01-01", "2019-02-28")


class ProfitAndLossTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")
        self.job = create_job_from_deal(won_deal().name)["name"]
        self.today = frappe.utils.nowdate()

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def collect_first_milestone(self):
        """Money in the bank today - the only kind this report counts."""
        first = job_milestones(self.job)["milestones"][0]
        set_milestone_status(self.job, first["name"], "Paid")

    def spend(self, amount=5_000_000):
        log_job_expense(self.job, amount, category=CATEGORY)

    def today_report(self):
        return finance_profit_and_loss(self.today, self.today)

    def today_month(self):
        (month,) = self.today_report()["months"]
        return month


class TestProfitAndLossShape(ProfitAndLossTestCase):
    def test_the_report_carries_its_range_its_basis_and_its_months(self):
        report = self.today_report()

        assert_keys(self, report, REPORT_KEYS, "finance_profit_and_loss")
        assert_iso_date(self, report["date_from"], "date_from")
        assert_iso_date(self, report["date_to"], "date_to")
        self.assertEqual(report["basis"], CASH_BASIS)

    def test_a_month_carries_both_sides_the_difference_and_the_counts(self):
        self.collect_first_milestone()
        self.spend()

        assert_keys(self, self.today_month(), MONTH_KEYS, "profit and loss month")
        assert_keys(self, self.today_report()["total"], TOTAL_KEYS, "profit and loss total")

    def test_every_amount_is_whole_dong_at_every_level(self):
        self.collect_first_milestone()
        self.spend()

        report = self.today_report()
        assert_money(self, report["total"], "income", "expense", "profit", where="total")
        assert_money(
            self, self.today_month(), "income", "expense", "profit", where="month"
        )
        assert_counts(
            self,
            report["total"],
            "income_count",
            "expense_count",
            where="total",
        )


class TestProfitAndLossIsTheTwoReports(ProfitAndLossTestCase):
    def test_the_income_side_is_the_income_report_to_the_dong(self):
        self.collect_first_milestone()

        income = finance_income(self.today, self.today)
        report = self.today_report()
        self.assertEqual(report["total"]["income"], income["total"])
        self.assertEqual(report["total"]["income_count"], income["count"])
        self.assertEqual(self.today_month()["income"], income["months"][0]["total"])

    def test_the_expense_side_is_the_expense_report_to_the_dong(self):
        self.spend()

        expenses = finance_expenses(self.today, self.today)
        report = self.today_report()
        self.assertEqual(report["total"]["expense"], expenses["total"])
        self.assertEqual(report["total"]["expense_count"], expenses["count"])
        self.assertEqual(self.today_month()["expense"], expenses["months"][0]["total"])

    def test_the_profit_is_the_one_less_the_other(self):
        self.collect_first_milestone()
        self.spend()

        month = self.today_month()
        self.assertEqual(month["profit"], month["income"] - month["expense"])

    def test_the_total_is_exactly_the_sum_of_the_printed_months(self):
        self.collect_first_milestone()
        self.spend()

        report = self.today_report()
        self.assertEqual(
            report["total"]["profit"], sum(month["profit"] for month in report["months"])
        )

    def test_a_month_that_spent_without_collecting_reads_negative(self):
        """Not flattened at zero - the studio really is down that money."""
        self.spend(9_000_000)

        self.assertEqual(self.today_month()["profit"], -9_000_000)


class TestProfitAndLossEmpty(ProfitAndLossTestCase):
    def test_a_period_with_no_activity_is_zeroed_rather_than_broken(self):
        report = finance_profit_and_loss(*DEAD_RANGE)

        self.assertEqual(report["total"]["income"], 0)
        self.assertEqual(report["total"]["expense"], 0)
        self.assertEqual(report["total"]["profit"], 0)
        for month in report["months"]:
            assert_keys(self, month, MONTH_KEYS, f"empty month {month['month']}")
            self.assertEqual((month["income"], month["expense"], month["profit"]), (0, 0, 0))

    def test_a_month_nothing_came_in_has_no_margin_rather_than_a_zero_one(self):
        """None, never 0. A 0% margin is a month that broke even, which
        is a different and much better piece of news."""
        report = finance_profit_and_loss(*DEAD_RANGE)

        self.assertIsNone(report["total"]["margin_pct"])
        for month in report["months"]:
            self.assertIsNone(month["margin_pct"])

    def test_a_report_without_a_range_is_refused_rather_than_guessed(self):
        with self.assertRaises(frappe.ValidationError):
            finance_profit_and_loss(self.today, None)


class TestProfitAndLossBoundary(ProfitAndLossTestCase):
    def test_the_producer_reads_it_and_none_of_the_profit_chain(self):
        """Money in and money out are producer-visible by the same
        decision that makes each side visible on its own screen."""
        self.collect_first_milestone()
        self.spend()

        frappe.set_user(PRODUCER)
        report = self.today_report()
        assert_keys(self, report, REPORT_KEYS, "producer profit and loss")
        assert_no_founder_chain(self, report, "producer profit and loss")
        assert_no_founder_chain(self, report["total"], "producer profit and loss total")
        assert_no_founder_chain(self, report["months"][0], "producer profit and loss month")

    def test_the_producer_reads_the_same_payload_the_founder_does(self):
        self.collect_first_milestone()
        self.spend()

        frappe.set_user(FOUNDER)
        founders = self.today_report()
        frappe.set_user(PRODUCER)
        self.assertEqual(self.today_report(), founders)

    def test_an_outsider_reads_no_profit_and_loss_at_all(self):
        """Refused outright rather than answered with one side blank -
        a half-built profit and loss is a wrong number, not a partial
        one."""
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            finance_profit_and_loss(self.today, self.today)

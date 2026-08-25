"""Contract tests for money out (auraos.api.finance_expenses).

The arithmetic is pinned framework-free in tests/test_finance.py. This
file is the seam spec #81 asks for: the payload as an interface, now
that the React frontend reads it over HTTP.

What is asserted here, and nothing more:

1. **The documented keys are all there**, down through months into the
   category rows and the paid-from split.
2. **Money is integer đồng** at every level.
3. **The range bounds are ISO dates.**
4. **Both paid-from sources are always present**, so a month where
   nobody touched their float still prints a zero rather than dropping
   a column out of the chart.
5. **A producer's copy has no founder chain in it**, asserted as a key
   set rather than by spot-checking names.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import create_job_from_deal, finance_expenses, log_job_expense
from auraos.auraos.doctype.deal.test_deal import FOUNDER, OUTSIDER, PRODUCER
from auraos.auraos.doctype.job.test_job import won_deal
from auraos.lib.settlement import FROM_ADVANCE, FROM_COMPANY
from auraos.tests.contract import (
    assert_counts,
    assert_iso_date,
    assert_keys,
    assert_money,
    assert_no_founder_chain,
)
from auraos.tests.utils import make_test_user

REPORT_KEYS = ["date_from", "date_to", "months", "categories", "paid_from", "total", "count"]
MONTH_KEYS = ["month", "month_start", "total", "count", "categories", "paid_from"]
CATEGORY_KEYS = ["category", "total"]
PAID_FROM_KEYS = [FROM_ADVANCE, FROM_COMPANY]

# One of the categories won_deal() quotes, so an expense may name it.
CATEGORY = "Thiết bị"

# A window this company had not been founded in.
DEAD_RANGE = ("2019-01-01", "2019-02-28")


class FinanceExpenseTestCase(FrappeTestCase):
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

    def spend(self, amount=5_000_000, paid_from=FROM_ADVANCE):
        log_job_expense(self.job, amount, category=CATEGORY, paid_from=paid_from)

    def today_report(self):
        return finance_expenses(self.today, self.today)

    def category_row(self, rows, title=CATEGORY):
        found = [row for row in rows if row["category"] == title]
        self.assertEqual(len(found), 1, f"{title} should be one rolled-up row")
        return found[0]


class TestExpenseShape(FinanceExpenseTestCase):
    def test_the_report_carries_its_range_its_months_and_its_rollups(self):
        self.spend()

        report = self.today_report()
        assert_keys(self, report, REPORT_KEYS, "finance_expenses")
        assert_iso_date(self, report["date_from"], "date_from")
        assert_iso_date(self, report["date_to"], "date_to")
        self.assertEqual(report["date_from"], self.today)
        self.assertEqual(report["date_to"], self.today)

    def test_a_month_carries_its_key_its_first_day_and_both_breakdowns(self):
        self.spend()

        (month,) = self.today_report()["months"]
        assert_keys(self, month, MONTH_KEYS, "month")
        self.assertEqual(month["month"], self.today[:7])
        assert_iso_date(self, month["month_start"], "month_start")
        self.assertEqual(month["month_start"], f"{self.today[:7]}-01")

    def test_a_category_row_names_the_quoted_entry_it_rolls_up(self):
        self.spend()

        report = self.today_report()
        row = self.category_row(report["categories"])
        assert_keys(self, row, CATEGORY_KEYS, "category row")
        (month,) = report["months"]
        assert_keys(self, self.category_row(month["categories"]), CATEGORY_KEYS, "month category row")

    def test_both_sources_of_money_are_always_named(self):
        """Whose money it was is a two-column chart. A month in which
        nobody spent their own float still has the column."""
        self.spend(paid_from=FROM_COMPANY)

        report = self.today_report()
        assert_keys(self, report["paid_from"], PAID_FROM_KEYS, "paid_from")
        (month,) = report["months"]
        assert_keys(self, month["paid_from"], PAID_FROM_KEYS, "month paid_from")

    def test_every_amount_is_whole_dong_at_every_level(self):
        self.spend(paid_from=FROM_ADVANCE)
        self.spend(amount=1_250_000, paid_from=FROM_COMPANY)

        report = self.today_report()
        assert_money(self, report, "total", where="finance_expenses")
        assert_counts(self, report, "count", where="finance_expenses")
        assert_money(self, report["paid_from"], *PAID_FROM_KEYS, where="paid_from")
        for row in report["categories"]:
            assert_money(self, row, "total", where="category row")
        for month in report["months"]:
            assert_money(self, month, "total", where="month")
            assert_counts(self, month, "count", where="month")
            assert_money(self, month["paid_from"], *PAID_FROM_KEYS, where="month paid_from")
            for row in month["categories"]:
                assert_money(self, row, "total", where="month category row")


class TestExpenseEmpty(FinanceExpenseTestCase):
    def test_a_range_nobody_spent_in_reads_as_zeros_not_as_nothing(self):
        report = finance_expenses(*DEAD_RANGE)

        assert_keys(self, report, REPORT_KEYS, "empty finance_expenses")
        self.assertEqual(report["total"], 0)
        self.assertEqual(report["count"], 0)
        self.assertEqual(report["categories"], [])
        self.assertEqual(report["paid_from"], {FROM_ADVANCE: 0, FROM_COMPANY: 0})

    def test_an_empty_month_is_still_a_month_with_every_key_on_it(self):
        months = finance_expenses(*DEAD_RANGE)["months"]

        self.assertEqual([month["month"] for month in months], ["2019-01", "2019-02"])
        for month in months:
            assert_keys(self, month, MONTH_KEYS, "empty month")
            self.assertEqual(month["categories"], [])
            self.assertEqual(month["paid_from"], {FROM_ADVANCE: 0, FROM_COMPANY: 0})
            assert_money(self, month, "total", where="empty month")

    def test_a_report_without_a_range_is_refused_rather_than_guessed(self):
        with self.assertRaises(frappe.ValidationError):
            finance_expenses(self.today, None)


class TestExpenseBoundary(FinanceExpenseTestCase):
    def test_the_producer_reads_money_out_and_none_of_the_profit_chain(self):
        """The producer logs the spend; reading it back is the same
        right. Commission, CM and the tax chain are not on this payload
        for anybody."""
        self.spend()

        frappe.set_user(PRODUCER)
        report = self.today_report()
        assert_keys(self, report, REPORT_KEYS, "producer finance_expenses")
        assert_no_founder_chain(self, report, "producer finance_expenses")
        (month,) = report["months"]
        assert_keys(self, month, MONTH_KEYS, "producer month")
        assert_keys(
            self,
            self.category_row(month["categories"]),
            CATEGORY_KEYS,
            "producer category row",
        )

    def test_the_producer_reads_the_same_payload_the_founder_does(self):
        self.spend()

        frappe.set_user(FOUNDER)
        founders = self.today_report()
        frappe.set_user(PRODUCER)
        self.assertEqual(self.today_report(), founders)

    def test_an_outsider_reads_no_spend_at_all(self):
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            finance_expenses(self.today, self.today)

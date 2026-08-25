"""Contract tests for money in (auraos.api.finance_income).

The arithmetic is pinned framework-free in tests/test_finance.py. This
file is the other seam spec #81 asks for: the payload itself, now that a
separate React frontend reads it over HTTP and a renamed key breaks a
screen rather than a test.

Four promises, and nothing else:

1. **The documented keys are all there**, down through months into the
   per-client rows.
2. **Money is integer đồng** at every level, so the frontend formats
   rather than parses.
3. **The range bounds are ISO dates**, and the basis the screen prints
   comes from the payload rather than from the screen's own belief.
4. **A producer's copy has no founder chain in it** - asserted as a key
   set, so a founder field added later cannot ride along.

An empty month is still a month. A studio with no income in January
must read as a zero, not as a year with January missing, so a range
nobody was paid in returns the zeroed shape rather than nothing.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import (
    create_job_from_deal,
    finance_income,
    job_milestones,
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

REPORT_KEYS = ["date_from", "date_to", "basis", "months", "total", "count"]
MONTH_KEYS = ["month", "month_start", "total", "count", "clients"]
CLIENT_KEYS = ["company", "company_name", "total", "count"]

# A window nobody in this company has ever been paid in - the studio's
# first year predates it.
DEAD_RANGE = ("2019-01-01", "2019-02-28")


class FinanceIncomeTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")
        self.job = frappe.get_doc("Job", create_job_from_deal(won_deal().name)["name"])
        self.today = frappe.utils.nowdate()

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def collect_first_milestone(self):
        """Money in the bank today - the only kind this report counts."""
        first = job_milestones(self.job.name)["milestones"][0]
        set_milestone_status(self.job.name, first["name"], "Paid")
        return first

    def today_report(self):
        return finance_income(self.today, self.today)

    def our_client_row(self, report):
        """This job's client, out of a report that spans every job."""
        (month,) = report["months"]
        rows = [row for row in month["clients"] if row["company"] == self.job.company]
        self.assertEqual(len(rows), 1, "the client should appear exactly once")
        return rows[0]


class TestIncomeShape(FinanceIncomeTestCase):
    def test_the_report_carries_its_range_its_basis_and_its_months(self):
        self.collect_first_milestone()

        report = self.today_report()
        assert_keys(self, report, REPORT_KEYS, "finance_income")
        assert_iso_date(self, report["date_from"], "date_from")
        assert_iso_date(self, report["date_to"], "date_to")
        self.assertEqual(report["date_from"], self.today)
        self.assertEqual(report["date_to"], self.today)

    def test_the_basis_is_stated_rather_than_assumed_by_the_screen(self):
        """The finance screen says "cash basis" on its face; it reads
        that claim off the payload rather than making it itself."""
        self.assertEqual(self.today_report()["basis"], CASH_BASIS)

    def test_a_month_carries_its_key_its_first_day_and_its_clients(self):
        self.collect_first_milestone()

        (month,) = self.today_report()["months"]
        assert_keys(self, month, MONTH_KEYS, "month")
        self.assertEqual(month["month"], self.today[:7])
        assert_iso_date(self, month["month_start"], "month_start")
        self.assertEqual(month["month_start"], f"{self.today[:7]}-01")

    def test_a_client_row_names_the_company_and_what_it_paid(self):
        self.collect_first_milestone()

        row = self.our_client_row(self.today_report())
        assert_keys(self, row, CLIENT_KEYS, "client row")
        self.assertEqual(
            row["company_name"],
            frappe.db.get_value("Party Company", self.job.company, "company_name"),
        )

    def test_every_amount_is_whole_dong_at_every_level(self):
        self.collect_first_milestone()

        report = self.today_report()
        assert_money(self, report, "total", where="finance_income")
        assert_counts(self, report, "count", where="finance_income")
        for month in report["months"]:
            assert_money(self, month, "total", where="month")
            assert_counts(self, month, "count", where="month")
            for row in month["clients"]:
                assert_money(self, row, "total", where="client row")
                assert_counts(self, row, "count", where="client row")


class TestIncomeEmpty(FinanceIncomeTestCase):
    def test_a_range_nobody_was_paid_in_reads_as_zeros_not_as_nothing(self):
        """A new company opening the finance screen sees a chart of
        empty months, not a broken page."""
        report = finance_income(*DEAD_RANGE)

        assert_keys(self, report, REPORT_KEYS, "empty finance_income")
        self.assertEqual(report["total"], 0)
        self.assertEqual(report["count"], 0)
        self.assertEqual([month["month"] for month in report["months"]], ["2019-01", "2019-02"])

    def test_an_empty_month_is_still_a_month_with_every_key_on_it(self):
        for month in finance_income(*DEAD_RANGE)["months"]:
            assert_keys(self, month, MONTH_KEYS, "empty month")
            self.assertEqual(month["clients"], [])
            assert_money(self, month, "total", where="empty month")
            assert_counts(self, month, "count", where="empty month")

    def test_a_report_without_a_range_is_refused_rather_than_guessed(self):
        with self.assertRaises(frappe.ValidationError):
            finance_income(None, self.today)


class TestIncomeBoundary(FinanceIncomeTestCase):
    def test_the_producer_reads_money_in_and_none_of_the_profit_chain(self):
        """Money in is producer-visible by decision - they run the
        stages that make it due. The founder's chain is a different
        question through a different door (deal_profit)."""
        self.collect_first_milestone()

        frappe.set_user(PRODUCER)
        report = self.today_report()
        assert_keys(self, report, REPORT_KEYS, "producer finance_income")
        assert_no_founder_chain(self, report, "producer finance_income")
        (month,) = report["months"]
        assert_keys(self, month, MONTH_KEYS, "producer month")
        assert_keys(self, self.our_client_row(report), CLIENT_KEYS, "producer client row")

    def test_the_producer_reads_the_same_payload_the_founder_does(self):
        self.collect_first_milestone()

        frappe.set_user(FOUNDER)
        founders = self.today_report()
        frappe.set_user(PRODUCER)
        self.assertEqual(self.today_report(), founders)

    def test_an_outsider_reads_no_income_at_all(self):
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            finance_income(self.today, self.today)

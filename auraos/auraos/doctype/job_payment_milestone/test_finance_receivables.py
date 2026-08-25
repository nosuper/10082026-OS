"""Contract tests for money owed (auraos.api.finance_receivables).

The ageing rules are pinned framework-free in tests/test_finance.py -
which bucket a debt lands in, and when a milestone counts as late. This
file is the seam spec #81 asks for: the payload as an interface between
two systems.

What is asserted here, and nothing more:

1. **The whole ladder, every time.** All five buckets are present in
   reading order whether or not anything sits on them, so the chart has
   the same five bars on a good month as on a bad one.
2. **The documented keys are all there**, down through buckets into the
   milestone rows.
3. **Money is integer đồng, `as_of` is an ISO date and a due date is an
   ISO timestamp**, so the frontend formats rather than parses.
4. **A producer's copy has no founder chain in it**, asserted as a key
   set rather than by spot-checking names.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import (
    create_job_from_deal,
    finance_receivables,
    job_milestones,
    set_milestone_status,
)
from auraos.auraos.doctype.deal.test_deal import FOUNDER, OUTSIDER, PRODUCER
from auraos.auraos.doctype.job.test_job import won_deal
from auraos.lib.finance import AGEING_BUCKETS
from auraos.tests.contract import (
    assert_counts,
    assert_iso_date,
    assert_iso_timestamp,
    assert_keys,
    assert_money,
    assert_no_founder_chain,
)
from auraos.tests.utils import make_test_user

REPORT_KEYS = [
    "as_of",
    "payment_terms_days",
    "buckets",
    "total",
    "count",
    "overdue_total",
    "overdue_count",
]
BUCKET_KEYS = ["bucket", "total", "count", "rows"]
ROW_KEYS = [
    "milestone",
    "title",
    "job",
    "job_title",
    "company",
    "company_name",
    "amount",
    "status",
    "due_on",
    "overdue",
    "days_overdue",
]


def rows_of(report):
    """Every milestone row on the report, whichever rung it sits on."""
    return [row for bucket in report["buckets"] for row in bucket["rows"]]


class ReceivablesTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")
        self.job = frappe.get_doc("Job", create_job_from_deal(won_deal().name)["name"])

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def our_rows(self, report=None):
        report = finance_receivables() if report is None else report
        return [row for row in rows_of(report) if row["job"] == self.job.name]

    def invoice_first_milestone(self):
        """A milestone asked for and not yet paid - the one kind of row
        this report exists to chase. The deposit falls due at
        Pre-production, which is where a converted job starts, so it is
        the row that carries a due date."""
        first = job_milestones(self.job.name)["milestones"][0]
        set_milestone_status(self.job.name, first["name"], "Invoiced")
        return first["name"]

    def row_for(self, milestone, report=None):
        (row,) = [
            row for row in self.our_rows(report) if row["milestone"] == milestone
        ]
        return row


class TestReceivablesShape(ReceivablesTestCase):
    def test_the_report_carries_the_day_the_terms_and_the_ladder(self):
        report = finance_receivables()

        assert_keys(self, report, REPORT_KEYS, "finance_receivables")
        assert_iso_date(self, report["as_of"], "as_of")
        self.assertEqual(report["as_of"], frappe.utils.nowdate())
        assert_counts(self, report, "payment_terms_days", where="finance_receivables")

    def test_all_five_rungs_are_present_in_reading_order(self):
        """Not only the rungs with debt on them: a chart with three bars
        one week and five the next reads as a different chart."""
        report = finance_receivables()

        self.assertEqual(
            [bucket["bucket"] for bucket in report["buckets"]], list(AGEING_BUCKETS)
        )
        for bucket in report["buckets"]:
            assert_keys(self, bucket, BUCKET_KEYS, "bucket")
            assert_money(self, bucket, "total", where="bucket")
            assert_counts(self, bucket, "count", where="bucket")

    def test_a_row_names_the_milestone_the_job_and_the_client(self):
        row = self.row_for(self.invoice_first_milestone())

        assert_keys(self, row, ROW_KEYS, "receivable row")
        self.assertEqual(row["job_title"], self.job.title)
        self.assertEqual(row["company"], self.job.company)
        self.assertEqual(
            row["company_name"],
            frappe.db.get_value("Party Company", self.job.company, "company_name"),
        )

    def test_the_lateness_verdict_is_a_flag_and_a_count_never_a_sentence(self):
        """`days_overdue: 12`, not "Quá hạn 12 ngày" - the wording is the
        frontend's job and its language is the frontend's choice."""
        row = self.row_for(self.invoice_first_milestone())

        self.assertIs(type(row["overdue"]), bool)
        assert_counts(self, row, "days_overdue", where="receivable row")

    def test_a_due_date_is_an_iso_timestamp_and_an_unreached_one_is_none(self):
        """A milestone whose trigger stage the job has not reached is
        still money owed on a signed job, so it sits on the ladder with
        an empty due date rather than disappearing off it."""
        due = self.row_for(self.invoice_first_milestone())
        assert_iso_timestamp(self, due["due_on"], "due_on")

        unreached = [row for row in self.our_rows() if row["due_on"] is None]
        self.assertTrue(unreached, "the later milestones are not due yet")
        for row in unreached:
            assert_keys(self, row, ROW_KEYS, "undated receivable row")

    def test_every_amount_is_whole_dong_at_every_level(self):
        self.invoice_first_milestone()

        report = finance_receivables()
        assert_money(self, report, "total", "overdue_total", where="finance_receivables")
        assert_counts(self, report, "count", "overdue_count", where="finance_receivables")
        for bucket in report["buckets"]:
            for row in bucket["rows"]:
                assert_money(self, row, "amount", where="receivable row")


class TestReceivablesEmpty(ReceivablesTestCase):
    def test_a_company_nobody_owes_reads_as_five_empty_rungs(self):
        """Rolled back with the test - the point is the shape a studio
        sees on the day it has collected everything."""
        frappe.db.delete("Job Payment Milestone")

        report = finance_receivables()
        assert_keys(self, report, REPORT_KEYS, "empty finance_receivables")
        self.assertEqual(report["total"], 0)
        self.assertEqual(report["count"], 0)
        self.assertEqual(report["overdue_total"], 0)
        self.assertEqual(report["overdue_count"], 0)
        for bucket in report["buckets"]:
            assert_keys(self, bucket, BUCKET_KEYS, "empty bucket")
            self.assertEqual(bucket["rows"], [])
            self.assertEqual(bucket["total"], 0)
            self.assertEqual(bucket["count"], 0)


class TestReceivablesBoundary(ReceivablesTestCase):
    def test_the_producer_reads_the_ledger_and_none_of_the_profit_chain(self):
        """What a client owes is the client's own invoice, not the
        founder's margin - the same decision that makes the milestone
        plan producer-visible."""
        milestone = self.invoice_first_milestone()

        frappe.set_user(PRODUCER)
        report = finance_receivables()
        assert_keys(self, report, REPORT_KEYS, "producer finance_receivables")
        assert_no_founder_chain(self, report, "producer finance_receivables")
        for bucket in report["buckets"]:
            assert_keys(self, bucket, BUCKET_KEYS, "producer bucket")
        assert_keys(
            self,
            self.row_for(milestone, report),
            ROW_KEYS,
            "producer receivable row",
        )

    def test_the_producer_reads_the_same_payload_the_founder_does(self):
        self.invoice_first_milestone()

        frappe.set_user(FOUNDER)
        founders = finance_receivables()
        frappe.set_user(PRODUCER)
        self.assertEqual(finance_receivables(), founders)

    def test_an_outsider_reads_no_debt_at_all(self):
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            finance_receivables()

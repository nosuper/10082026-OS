"""Seam tests for no-invoice exposure (#123, replacing #11's).

The arithmetic is pinned framework-free in tests/test_exposure.py. What
only a site can prove is the wiring, and the wiring is what #123
changed: exposure now comes from a Job Expense rather than from a
quoted cost line, and the link between them is what carries the tax
treatment across.

The tests that matter most are the ones that would have failed before:

1. **A quoted Không hoá đơn line nobody spent against is worth
   nothing.** That is the bug the founder reported - a 4.5 triệu meal
   line, priced and never bought, shown as a 900.000 liability.
2. **Money paid out against such a line is exposure**, at the amount
   actually paid rather than the amount quoted, so an overrun or a
   discount lands on its own.
3. **An expense naming no line is unattributed, not exposed.**
4. **An invoice number takes it off**, and there is no second expense
   anywhere - #11's covering expense added its amount to the job's cost
   and posted a ledger entry for money that never moved.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import (
    create_job_from_deal,
    log_job_expense,
    no_invoice_exposure,
)
from auraos.auraos.doctype.deal.test_deal import FOUNDER, OUTSIDER, PRODUCER
from auraos.auraos.doctype.job.job import STAGES
from auraos.auraos.doctype.job.test_job import won_deal
from auraos.tests.utils import make_test_user

NO_INVOICE_DESCRIPTION = "Ăn uống đoàn"
INVOICED_DESCRIPTION = "Studio"

REPORT_KEYS = [
    "basis",
    "covered_count",
    "covered_total",
    "lines",
    "rate_pct",
    "stated_count",
    "stated_total",
    "tndn_exposure",
    "unattributed_count",
    "unattributed_total",
    "uncovered_count",
    "uncovered_total",
]


class ExposureTestCase(FrappeTestCase):
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

    def line_named(self, description):
        (row,) = [r for r in self.job.cost_lines if r.description == description]
        return row

    def pay(self, amount, cost_line=None, invoice_no=None):
        expense = frappe.get_doc(
            {
                "doctype": "Job Expense",
                "job": self.job.name,
                "amount": amount,
                "spent_on": frappe.utils.nowdate(),
                "paid_from": "Company",
                "description": "Chi thật",
                "cost_line": cost_line.name if cost_line else None,
                "invoice_no": invoice_no,
            }
        )
        expense.insert()
        return expense

    def mine(self, report, key="lines"):
        return [row for row in report[key] if row["job"] == self.job.name]

    def report(self):
        frappe.set_user(FOUNDER)
        out = no_invoice_exposure()
        frappe.set_user("Administrator")
        return out


class TestExposureIsMoneyThatMoved(ExposureTestCase):
    def test_a_quoted_no_invoice_line_nobody_spent_against_is_worth_nothing(self):
        """The founder's report. The job carries the line from the
        moment it is created and nothing has been paid against it."""
        self.assertTrue(self.line_named(NO_INVOICE_DESCRIPTION))

        self.assertEqual(self.mine(self.report()), [])

    def test_money_paid_against_a_no_invoice_line_is_exposure(self):
        self.pay(850_000, self.line_named(NO_INVOICE_DESCRIPTION))

        (row,) = self.mine(self.report())
        self.assertEqual(row["amount"], 850_000)
        self.assertFalse(row["covered"])

    def test_the_amount_is_what_was_paid_not_what_was_quoted(self):
        """The founder's reason for the whole design: phát sinh and
        chiết khấu mean the real figure is the one that matters."""
        line = self.line_named(NO_INVOICE_DESCRIPTION)
        quoted = round(line.subtotal * (1 + (line.vendor_mf_pct or 0) / 100))
        self.pay(quoted + 2_000_000, line)

        (row,) = self.mine(self.report())
        self.assertEqual(row["amount"], quoted + 2_000_000)
        self.assertNotEqual(row["amount"], quoted)

    def test_money_paid_against_an_invoiced_line_carries_nothing(self):
        """The only way naming a line takes money out of the figure."""
        self.pay(5_000_000, self.line_named(INVOICED_DESCRIPTION))

        self.assertEqual(self.mine(self.report()), [])


class TestUnattributedSpending(ExposureTestCase):
    def test_an_expense_naming_no_line_counts_as_exposed(self):
        """The Gửi xe + cà phê đoàn case: real money, nobody has said
        what it is. The founder chose to count it, because understating
        is the error that costs money at an audit."""
        log_job_expense(self.job.name, 850_000)

        (row,) = self.mine(self.report())
        self.assertEqual(row["amount"], 850_000)
        self.assertEqual(row["treatment"], "unattributed")

    def test_pointing_it_at_an_invoiced_line_takes_it_out(self):
        """The tile is a prompt: the figure falls as the attributing
        gets done."""
        expense = self.pay(850_000)
        self.assertEqual(len(self.mine(self.report())), 1)

        expense.cost_line = self.line_named(INVOICED_DESCRIPTION).name
        expense.save()

        self.assertEqual(self.mine(self.report()), [])

    def test_pointing_it_at_a_no_invoice_line_keeps_it_but_states_it(self):
        expense = self.pay(850_000)
        expense.cost_line = self.line_named(NO_INVOICE_DESCRIPTION).name
        expense.save()

        (row,) = self.mine(self.report())
        self.assertEqual(row["treatment"], "stated")

    def test_the_two_halves_add_up_to_the_headline(self):
        self.pay(850_000)
        self.pay(4_500_000, self.line_named(NO_INVOICE_DESCRIPTION))

        out = self.report()
        self.assertEqual(
            out["stated_total"] + out["unattributed_total"], out["uncovered_total"]
        )


class TestCoveredIsRecordedNotASecondExpense(ExposureTestCase):
    def test_an_invoice_number_takes_the_exposure_off(self):
        expense = self.pay(850_000, self.line_named(NO_INVOICE_DESCRIPTION))
        before = self.report()
        self.assertEqual(len(self.mine(before)), 1)

        expense.invoice_no = "0001234"
        expense.save()

        out = self.report()
        self.assertEqual(self.mine(out), [])
        # A difference, not a figure (#144). `covered_count` is the whole
        # site's, and unlike the uncovered rows there is no per-job list to
        # scope it through - `lines` carries only the uncovered ones. So this
        # asserted "the site has exactly one covered payment" and read it as
        # "mine is covered", which was true only while nothing else on the
        # site had ever carried an invoice number. The e2e seed now does, and
        # the assertion failed there while passing in CI - a test that was
        # wrong the day it was written and could not say so until a populated
        # site ran it.
        self.assertEqual(out["covered_count"], before["covered_count"] + 1)
        self.assertEqual(out["covered_total"], before["covered_total"] + 850_000)

    def test_recording_the_invoice_adds_no_money_to_the_job(self):
        """#11 recorded the replacement invoice as a second Job Expense,
        which added its amount to the job's actual cost and posted a
        ledger entry for money that never moved. Paper is not money."""
        from auraos.api import job_money

        expense = self.pay(850_000, self.line_named(NO_INVOICE_DESCRIPTION))
        before = job_money(self.job.name)["spent_total"]

        expense.invoice_no = "0001234"
        expense.save()

        self.assertEqual(job_money(self.job.name)["spent_total"], before)

    def test_no_second_expense_exists_for_the_paperwork(self):
        expense = self.pay(850_000, self.line_named(NO_INVOICE_DESCRIPTION))
        expense.invoice_no = "0001234"
        expense.save()

        self.assertEqual(
            frappe.db.count("Job Expense", {"job": self.job.name}), 1
        )


class TestTheLinkIsGuarded(ExposureTestCase):
    def test_a_line_on_another_job_is_refused(self):
        other = frappe.get_doc("Job", create_job_from_deal(won_deal().name)["name"])
        (foreign,) = [
            r for r in other.cost_lines if r.description == NO_INVOICE_DESCRIPTION
        ]

        with self.assertRaises(frappe.ValidationError):
            self.pay(850_000, foreign)

    def test_a_line_that_does_not_exist_is_refused(self):
        with self.assertRaises(frappe.ValidationError):
            self.pay(850_000, frappe._dict(name="not-a-cost-line"))

    def test_an_invoiced_line_is_now_allowed(self):
        """Under #11 this field meant "is the replacement invoice for",
        which only made sense on a no-invoice line. It now means "spends
        against", which is true of every quoted line."""
        self.pay(5_000_000, self.line_named(INVOICED_DESCRIPTION))

    def test_an_expense_may_name_no_line_at_all(self):
        log_job_expense(self.job.name, 500_000)


class TestSpendingFreezesWhenTheJobCloses(ExposureTestCase):
    def test_an_expense_may_be_corrected_while_the_job_is_open(self):
        expense = self.pay(850_000, self.line_named(NO_INVOICE_DESCRIPTION))

        expense.amount = 900_000
        expense.category = None
        expense.save()

        self.assertEqual(frappe.db.get_value("Job Expense", expense.name, "amount"), 900_000)

    def test_a_closed_job_refuses_an_edit(self):
        """Cost lines freeze when the deal is won because they record
        what was sold; expenses freeze when the job closes because they
        record what it cost."""
        expense = self.pay(850_000, self.line_named(NO_INVOICE_DESCRIPTION))
        self.job.stage = STAGES[-1]
        self.job.save()

        expense.amount = 900_000
        with self.assertRaises(frappe.ValidationError):
            expense.save()

    def test_a_closed_job_refuses_a_new_expense(self):
        """Adding moves the recorded total exactly as editing does."""
        self.job.stage = STAGES[-1]
        self.job.save()

        with self.assertRaises(frappe.ValidationError):
            self.pay(500_000)

    def test_a_closed_job_refuses_a_deletion(self):
        """The one that matters most: on_trash walks the ledger entry
        back, so an ungated delete moves money on a closed job and
        leaves nothing saying it was adjusted."""
        expense = self.pay(850_000, self.line_named(NO_INVOICE_DESCRIPTION))
        self.job.stage = STAGES[-1]
        self.job.save()

        with self.assertRaises(frappe.ValidationError):
            expense.delete()

    def test_reopening_the_job_makes_it_correctable_again(self):
        expense = self.pay(850_000, self.line_named(NO_INVOICE_DESCRIPTION))
        self.job.stage = STAGES[-1]
        self.job.save()
        self.job.stage = STAGES[0]
        self.job.save()

        expense.amount = 900_000
        expense.save()
        self.assertEqual(frappe.db.get_value("Job Expense", expense.name, "amount"), 900_000)

    def test_deleting_a_closed_job_does_not_half_delete_it(self):
        """Asked by the ledger lane and worth pinning: `on_trash` now
        throws for a closed job, so if Frappe cascaded a Job delete into
        its expenses, deleting a closed job would fail partway - and a
        half-deleted job is worse than a refused one.

        It does not cascade: the link from Job Expense to Job means
        Frappe refuses the Job delete outright, before any expense is
        touched. Refused whole, which is the safe end. Pinned because
        the safety comes from Frappe's link check rather than from
        anything this file does, and that could change under us.
        """
        self.pay(850_000, self.line_named(NO_INVOICE_DESCRIPTION))
        self.job.stage = STAGES[-1]
        self.job.save()

        with self.assertRaises(frappe.LinkExistsError):
            frappe.delete_doc("Job", self.job.name)

        # Nothing was removed on the way to being refused.
        self.assertEqual(frappe.db.count("Job Expense", {"job": self.job.name}), 1)
        self.assertTrue(frappe.db.exists("Job", self.job.name))

    def test_the_refusal_names_the_job_and_says_how_to_proceed(self):
        expense = self.pay(850_000, self.line_named(NO_INVOICE_DESCRIPTION))
        self.job.stage = STAGES[-1]
        self.job.save()

        expense.amount = 900_000
        try:
            expense.save()
        except frappe.ValidationError as err:
            self.assertIn(self.job.name, str(err))
            self.assertIn("Reopen", str(err))
        else:
            self.fail("a closed job should refuse an edit")


class TestTheExposureIsFounderOnly(ExposureTestCase):
    def test_the_founder_reads_the_documented_shape(self):
        frappe.set_user(FOUNDER)
        self.assertEqual(sorted(no_invoice_exposure()), REPORT_KEYS)

    def test_a_producer_is_refused_outright(self):
        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            no_invoice_exposure()

    def test_an_outsider_is_refused_too(self):
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            no_invoice_exposure()

    def test_the_producer_who_records_the_spend_still_may_not_read_the_tax(self):
        """Logging what was paid is the producer's job; the tax it
        exposes the company to is not."""
        line = self.line_named(NO_INVOICE_DESCRIPTION)

        frappe.set_user(PRODUCER)
        self.pay(850_000, line)
        with self.assertRaises(frappe.PermissionError):
            no_invoice_exposure()

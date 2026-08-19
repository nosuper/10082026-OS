"""Seam tests for no-invoice cover (issue #11).

The arithmetic is pinned framework-free in tests/test_exposure.py. What
only a site can prove is the wiring, and the wiring is the whole design
decision here:

**The status is derived, never stored.** No doctype holds "đã thay thế".
A `Không hoá đơn` cost line is covered when, and only when, some expense
on the job says it covers it. So the tests that matter are the ones that
show the status following the expense around - appearing when the
expense is written, vanishing when it is deleted - because a stored flag
is a figure someone can edit into an opinion and a derived one is not.

**The line itself is never touched.** `Job.FROZEN_TABLES` makes a job's
cost lines a record of what was won, and this feature deliberately does
not punch a hole in that. Proven here rather than assumed: the covering
expense is written and the line's own row is byte-for-byte what it was.

**A link that cannot mean anything is refused.** A line on another job,
or a line that came with an invoice, are both rejected at save. An
ignored bad link would read on the founder's tile as an exposure that
has been dealt with, which is the one wrong answer that costs money.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import create_job_from_deal, log_job_expense, no_invoice_exposure
from auraos.auraos.doctype.deal.test_deal import FOUNDER, OUTSIDER, PRODUCER
from auraos.auraos.doctype.job.test_job import won_deal
from auraos.lib import exposure
from auraos.tests.utils import make_test_user

# "Ăn uống đoàn" in the shared breakdown fixture: 10 × 3 × 150.000, no
# vendor management fee, so the cash it hands over is 4.500.000.
NO_INVOICE_DESCRIPTION = "Ăn uống đoàn"
NO_INVOICE_CASH = 4_500_000


class NoInvoiceCoverTestCase(FrappeTestCase):
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

    def line_of(self, description):
        (row,) = [r for r in self.job.cost_lines if r.description == description]
        return row

    def no_invoice_line(self):
        return self.line_of(NO_INVOICE_DESCRIPTION)

    def cover_with(self, line, amount=NO_INVOICE_CASH):
        """Log an expense that is the replacement invoice for `line`."""
        expense = frappe.get_doc(
            {
                "doctype": "Job Expense",
                "job": self.job.name,
                "amount": amount,
                "spent_on": frappe.utils.nowdate(),
                "covers_cost_line": line.name,
            }
        )
        expense.insert()
        return expense

    def rows(self):
        """The job's no-invoice lines with their coverage resolved."""
        expenses = frappe.get_all(
            "Job Expense",
            filters={"job": self.job.name},
            fields=["name", "amount", "covers_cost_line"],
        )
        doc = frappe.get_doc("Job", self.job.name)
        return exposure.exposure_rows(
            [row.as_dict() for row in doc.cost_lines], expenses, job=doc.name
        )

    def only_row(self):
        (row,) = self.rows()
        return row


class TestCoverIsDerived(NoInvoiceCoverTestCase):
    def test_a_no_invoice_line_starts_uncovered(self):
        """Nobody has recorded a replacement invoice, so the company is
        carrying the whole cost."""
        row = self.only_row()

        self.assertEqual(row["description"], NO_INVOICE_DESCRIPTION)
        self.assertFalse(row["covered"])
        self.assertEqual(row["amount"], NO_INVOICE_CASH)

    def test_logging_the_covering_expense_covers_the_line(self):
        expense = self.cover_with(self.no_invoice_line())

        row = self.only_row()
        self.assertTrue(row["covered"])
        self.assertEqual(row["covering_expenses"], [expense.name])
        self.assertEqual(row["covering_total"], NO_INVOICE_CASH)

    def test_deleting_the_covering_expense_uncovers_the_line(self):
        """The status follows the paperwork because it *is* the
        paperwork. A stored flag would have been left behind here."""
        expense = self.cover_with(self.no_invoice_line())
        self.assertTrue(self.only_row()["covered"])

        expense.delete()

        self.assertFalse(self.only_row()["covered"])

    def test_two_expenses_may_cover_one_line(self):
        """A replacement invoice can arrive split across two receipts."""
        line = self.no_invoice_line()
        self.cover_with(line, amount=2_000_000)
        self.cover_with(line, amount=2_500_000)

        row = self.only_row()
        self.assertEqual(row["covering_count"], 2)
        self.assertEqual(row["covering_total"], NO_INVOICE_CASH)

    def test_a_part_covered_line_says_how_much_was_covered(self):
        self.cover_with(self.no_invoice_line(), amount=1_000_000)

        row = self.only_row()
        self.assertTrue(row["covered"])
        self.assertEqual(row["amount"], NO_INVOICE_CASH)
        self.assertEqual(row["covering_total"], 1_000_000)

    def test_an_ordinary_expense_covers_nothing(self):
        """Most spend on a shoot is not a replacement invoice."""
        log_job_expense(self.job.name, 500_000)

        self.assertFalse(self.only_row()["covered"])


class TestTheLineIsNeverTouched(NoInvoiceCoverTestCase):
    def test_covering_a_line_does_not_edit_the_carried_breakdown(self):
        """FROZEN_TABLES stays whole: this feature sidesteps the freeze
        rather than weakening it."""
        before = [row.as_dict() for row in self.job.cost_lines]

        self.cover_with(self.no_invoice_line())

        after = [row.as_dict() for row in frappe.get_doc("Job", self.job.name).cost_lines]
        self.assertEqual(
            [{k: v for k, v in row.items() if k != "modified"} for row in before],
            [{k: v for k, v in row.items() if k != "modified"} for row in after],
        )

    def test_the_cost_line_has_no_replacement_field_to_write(self):
        """The status lives on the expense. If a field ever appears here
        the derived guarantee is gone and this test should say so."""
        fields = {field.fieldname for field in self.no_invoice_line().meta.fields}

        self.assertNotIn("replacement_status", fields)
        self.assertNotIn("replacement_expense", fields)


class TestALinkThatCannotMeanAnything(NoInvoiceCoverTestCase):
    def test_a_line_on_another_job_is_refused(self):
        other = frappe.get_doc("Job", create_job_from_deal(won_deal().name)["name"])
        (foreign,) = [
            r for r in other.cost_lines if r.description == NO_INVOICE_DESCRIPTION
        ]

        with self.assertRaises(frappe.ValidationError):
            self.cover_with(foreign)

    def test_a_line_that_does_not_exist_is_refused(self):
        with self.assertRaises(frappe.ValidationError):
            self.cover_with(frappe._dict(name="not-a-cost-line"))

    def test_a_line_that_already_had_an_invoice_is_refused(self):
        """A Công ty line came with its paper. An expense claiming to
        replace it is a mistake about which line was meant, and a
        mistake swallowed here reads as an exposure dealt with."""
        with self.assertRaises(frappe.ValidationError):
            self.cover_with(self.line_of("Studio"))

    def test_the_refusal_names_the_line_and_its_tax_type(self):
        """So the person fixing it does not have to guess."""
        try:
            self.cover_with(self.line_of("Studio"))
        except frappe.ValidationError as err:
            self.assertIn("Studio", str(err))
            self.assertIn("Công ty", str(err))
        else:
            self.fail("covering an invoiced line should have been refused")

    def test_an_expense_that_covers_nothing_is_always_allowed(self):
        """The field is optional and most expenses leave it empty."""
        log_job_expense(self.job.name, 500_000)


class TestWhoMayRecordACover(NoInvoiceCoverTestCase):
    def test_a_producer_may_record_the_replacement_invoice(self):
        """Chasing the invoice is the producer's job; reading the tax it
        exposes the company to is the founder's. Recording that the
        paper arrived is deliberately not gated."""
        line = self.no_invoice_line()

        frappe.set_user(PRODUCER)
        self.cover_with(line)

        frappe.set_user("Administrator")
        self.assertTrue(self.only_row()["covered"])


# -- the founder's tile, and who cannot have it --
#
# The exposure is the company's tax position, so it sits behind the same
# boundary as the profit chain: refused outright, not blanked. The tests
# below assert the refusal rather than the absence of a word, so a screen
# that says plainly "this is founder-only" cannot fail its own check.

REPORT_KEYS = [
    "basis",
    "covered_count",
    "covered_total",
    "lines",
    "rate_pct",
    "tndn_exposure",
    "uncovered_count",
    "uncovered_total",
]


class ExposureEndpointTestCase(NoInvoiceCoverTestCase):
    def my_lines(self, report):
        """Only the rows belonging to this test's job.

        The endpoint answers for every job on the site, and a site has
        other jobs on it, so an assertion on the grand total would be an
        assertion about somebody else's fixtures.
        """
        return [row for row in report["lines"] if row["job"] == self.job.name]


class TestTheExposureReport(ExposureEndpointTestCase):
    def test_the_founder_reads_the_documented_shape(self):
        frappe.set_user(FOUNDER)
        report = no_invoice_exposure()

        self.assertEqual(sorted(report), REPORT_KEYS)

    def test_an_uncovered_line_is_on_it_with_the_cash_it_handed_over(self):
        frappe.set_user(FOUNDER)

        (row,) = self.my_lines(no_invoice_exposure())
        self.assertEqual(row["description"], NO_INVOICE_DESCRIPTION)
        self.assertEqual(row["amount"], NO_INVOICE_CASH)
        self.assertFalse(row["covered"])
        self.assertEqual(row["job_title"], self.job.title)

    def test_covering_the_line_takes_it_off_the_exposure(self):
        """The tile is derived, so recording the paperwork is the only
        thing anybody has to do."""
        frappe.set_user(FOUNDER)
        before = no_invoice_exposure()
        self.assertEqual(len(self.my_lines(before)), 1)

        frappe.set_user("Administrator")
        self.cover_with(self.no_invoice_line())

        frappe.set_user(FOUNDER)
        after = no_invoice_exposure()
        self.assertEqual(self.my_lines(after), [])
        self.assertEqual(
            after["uncovered_total"], before["uncovered_total"] - NO_INVOICE_CASH
        )

    def test_the_tax_is_the_rate_applied_to_the_uncovered_total(self):
        frappe.set_user(FOUNDER)
        report = no_invoice_exposure()

        self.assertEqual(report["rate_pct"], 20.0)
        self.assertEqual(
            report["tndn_exposure"], exposure.tndn_on(report["uncovered_total"])
        )

    def test_every_figure_is_whole_dong(self):
        frappe.set_user(FOUNDER)
        report = no_invoice_exposure()

        for key in ("uncovered_total", "tndn_exposure", "covered_total"):
            self.assertIsInstance(report[key], int, key)
        for row in report["lines"]:
            self.assertIsInstance(row["amount"], int)

    def test_a_job_with_no_no_invoice_lines_contributes_nothing(self):
        """Not an error, and not a row of zeros - simply absent."""
        frappe.set_user(FOUNDER)
        report = no_invoice_exposure()

        self.assertTrue(
            all(row["description"] == NO_INVOICE_DESCRIPTION for row in self.my_lines(report))
        )


class TestTheExposureIsFounderOnly(ExposureEndpointTestCase):
    def test_a_producer_is_refused_outright(self):
        """Refused, not blanked. A producer holding an empty report
        would read it as "nothing is exposed"."""
        frappe.set_user(PRODUCER)

        with self.assertRaises(frappe.PermissionError):
            no_invoice_exposure()

    def test_an_outsider_is_refused_too(self):
        frappe.set_user(OUTSIDER)

        with self.assertRaises(frappe.PermissionError):
            no_invoice_exposure()

    def test_the_producer_who_may_record_the_cover_still_may_not_read_the_tax(self):
        """The split this feature rests on: chasing the invoice is the
        producer's job, the tax it exposes the company to is not."""
        line = self.no_invoice_line()

        frappe.set_user(PRODUCER)
        self.cover_with(line)
        with self.assertRaises(frappe.PermissionError):
            no_invoice_exposure()

    def test_the_founder_reads_it_after_the_producer_recorded_the_cover(self):
        line = self.no_invoice_line()
        frappe.set_user(PRODUCER)
        self.cover_with(line)

        frappe.set_user(FOUNDER)
        self.assertEqual(self.my_lines(no_invoice_exposure()), [])

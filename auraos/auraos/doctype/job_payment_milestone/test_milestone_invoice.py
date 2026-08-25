"""The invoice a milestone was billed under (issue #98, spec #81).

An invoice and the money it bills are one record. So the number, the day
it went out and the VAT rate it was written on live on the milestone
being billed, and there is no second doctype holding the same money for
the two to disagree about.

Three things are asserted here, and nothing more:

1. **Issuing an invoice is a status change.** đã xuất HĐ already stamps
   the day; the number rides in on the same call, and the walk back that
   undoes the status undoes the whole invoice with it. The stamping rules
   themselves are pinned framework-free in tests/test_milestones.py.
2. **The payload states the basis rather than implying it.** The rate is
   a number on the row, not a percentage buried in a Vietnamese sentence,
   and an invoice already issued keeps reading at the rate it was issued
   under however the company's rate moves afterwards.
3. **The key set is the interface.** A milestone row and an invoice
   request are read by a separate frontend over HTTP, so a renamed field
   fails here rather than on a screen.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import (
    create_job_from_deal,
    job_milestones,
    milestone_invoice_request,
    save_job_milestones,
    set_milestone_status,
)
from auraos.auraos.doctype.deal.test_deal import FOUNDER, OUTSIDER, PRODUCER, make_company
from auraos.auraos.doctype.job.test_job import won_deal
from auraos.lib.milestones import INVOICED, PAID, REQUESTED
from auraos.patches import record_invoice_vat_basis
from auraos.tests.contract import (
    assert_keys,
    assert_money,
    assert_no_founder_chain,
)
from auraos.tests.utils import make_test_user

# The milestone row as every screen reads it. The invoice is three of
# these keys - number, date, basis - and no fourth record.
MILESTONE_KEYS = [
    "name",
    "idx",
    "title",
    "pct",
    "trigger_stage",
    "amount",
    "status",
    "due_on",
    "requested_on",
    "invoiced_on",
    "paid_on",
    "invoice_no",
    "invoice_vat_pct",
    "overdue",
    "days_overdue",
]

INVOICE_REQUEST_KEYS = [
    "text",
    "invoice_no",
    "invoiced_on",
    "amount",
    "vat_pct",
    "net",
    "vat",
]

NUMBER = "HD-2026-0142"


class MilestoneInvoiceTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")
        make_company()
        self.job = frappe.get_doc("Job", create_job_from_deal(won_deal().name)["name"])
        self.deposit = self.job.payment_milestones[0]

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def row(self):
        return job_milestones(self.job.name)["milestones"][0]

    def issue(self, invoice_no=NUMBER):
        return set_milestone_status(
            self.job.name, self.deposit.name, INVOICED, invoice_no=invoice_no
        )

    def make_it_look_invoiced_before_this_shipped(self):
        """An invoice with a date and no recorded rate - which is a
        stored 0, because the column cannot hold "nobody wrote it down"."""
        self.issue()
        frappe.db.set_value(
            "Job Payment Milestone",
            self.deposit.name,
            "invoice_vat_pct",
            0,
            update_modified=False,
        )
        frappe.clear_document_cache("Job", self.job.name)

    def set_company_vat(self, pct):
        """Move the rate the way only a data fix can.

        vat_pct is frozen on a won job, so this is the one route by which
        an issued invoice could ever find its basis changed underneath
        it - which is exactly the route worth testing.
        """
        frappe.db.set_value("Job", self.job.name, "vat_pct", pct, update_modified=False)
        frappe.clear_document_cache("Job", self.job.name)


class TestIssuingAnInvoice(MilestoneInvoiceTestCase):
    def test_issuing_an_invoice_records_its_number_its_day_and_its_basis(self):
        row = self.issue()

        self.assertEqual(row["status"], INVOICED)
        self.assertEqual(row["invoice_no"], NUMBER)
        self.assertTrue(row["invoiced_on"])
        self.assertEqual(row["invoice_vat_pct"], self.job.vat_pct)

    def test_the_invoice_is_stored_on_the_milestone_it_bills(self):
        """Read back off the job, not out of the reply that wrote it."""
        self.issue()
        stored = frappe.get_doc("Job", self.job.name).payment_milestones[0]
        self.assertEqual(stored.invoice_no, NUMBER)
        self.assertEqual(stored.invoice_vat_pct, self.job.vat_pct)

    def test_a_milestone_nobody_has_invoiced_carries_no_invoice(self):
        """Not a 0% one. A stored rate of 0 on a row with no issue date
        is a column that cannot be null, not an export invoice."""
        row = self.row()
        self.assertIsNone(row["invoice_no"])
        self.assertIsNone(row["invoice_vat_pct"])
        self.assertFalse(row["invoiced_on"])

    def test_marking_it_invoiced_without_a_number_still_records_the_basis(self):
        """The accountant's number sometimes arrives after the founder
        has marked it issued. The day and the rate are known either way,
        and a blank number says so rather than guessing one."""
        row = set_milestone_status(self.job.name, self.deposit.name, INVOICED)
        self.assertIsNone(row["invoice_no"])
        self.assertTrue(row["invoiced_on"])
        self.assertEqual(row["invoice_vat_pct"], self.job.vat_pct)

    def test_a_mistyped_number_is_corrected_without_moving_the_day(self):
        issued = self.issue()
        corrected = self.issue("HD-2026-0143")
        self.assertEqual(corrected["invoice_no"], "HD-2026-0143")
        self.assertEqual(corrected["invoiced_on"], issued["invoiced_on"])
        self.assertEqual(corrected["invoice_vat_pct"], issued["invoice_vat_pct"])

    def test_an_invoice_number_on_a_milestone_that_is_not_invoiced_is_refused(self):
        """Silently dropping it would leave the founder believing a
        number is on file that nothing recorded."""
        with self.assertRaises(frappe.ValidationError):
            set_milestone_status(
                self.job.name, self.deposit.name, REQUESTED, invoice_no=NUMBER
            )

    def test_walking_the_status_back_takes_the_whole_invoice_with_it(self):
        """The T6 lesson applied to the invoice: the door back out of đã
        xuất HĐ is the same door, and a number left behind on a milestone
        with no issue date is a number nobody issued."""
        self.issue()
        row = set_milestone_status(self.job.name, self.deposit.name, REQUESTED)
        self.assertIsNone(row["invoice_no"])
        self.assertIsNone(row["invoice_vat_pct"])
        self.assertFalse(row["invoiced_on"])

    def test_getting_paid_keeps_the_invoice_that_was_issued(self):
        self.issue()
        row = set_milestone_status(self.job.name, self.deposit.name, PAID)
        self.assertEqual(row["invoice_no"], NUMBER)
        self.assertEqual(row["invoice_vat_pct"], self.job.vat_pct)

    def test_a_client_who_pays_before_any_invoice_has_none_to_show(self):
        row = set_milestone_status(self.job.name, self.deposit.name, PAID)
        self.assertIsNone(row["invoice_no"])
        self.assertIsNone(row["invoice_vat_pct"])

    def test_replanning_the_milestones_keeps_the_invoice_already_issued(self):
        """Renaming the deposit must not un-invoice it, exactly as it
        must not un-pay it."""
        self.issue()
        result = save_job_milestones(
            self.job.name,
            [
                {
                    "name": self.deposit.name,
                    "title": "Đặt cọc",
                    "pct": 50,
                    "trigger_stage": "Pre-production",
                }
            ],
        )
        self.assertEqual(result["milestones"][0]["invoice_no"], NUMBER)
        self.assertEqual(
            result["milestones"][0]["invoice_vat_pct"], self.job.vat_pct
        )

    def test_a_hand_typed_invoice_number_never_stands_without_an_invoice(self):
        job = frappe.get_doc("Job", self.job.name)
        job.payment_milestones[0].invoice_no = NUMBER
        job.payment_milestones[0].invoice_vat_pct = 99
        job.save()
        self.assertIsNone(self.row()["invoice_no"])
        self.assertIsNone(self.row()["invoice_vat_pct"])
        stored = frappe.get_doc("Job", self.job.name).payment_milestones[0]
        self.assertFalse(stored.invoice_no)


class TestTheBasisIsExplicit(MilestoneInvoiceTestCase):
    def test_a_later_rate_change_does_not_restate_an_issued_invoice(self):
        """The client is holding an invoice. Moving the company's rate is
        news about the next one."""
        self.issue()
        issued_at = self.job.vat_pct
        self.set_company_vat(issued_at + 2)

        frappe.get_doc("Job", self.job.name).save()
        self.assertEqual(self.row()["invoice_vat_pct"], issued_at)

    def test_the_zalo_text_of_an_issued_invoice_is_written_at_its_own_rate(self):
        """Asking for the message again must reproduce the invoice the
        client holds, not a second version of it."""
        self.issue()
        issued_at = self.job.vat_pct
        self.set_company_vat(issued_at + 2)

        request = milestone_invoice_request(self.job.name, self.deposit.name)
        self.assertEqual(request["vat_pct"], issued_at)
        self.assertIn(f"VAT {round(issued_at)}%", request["text"])

    def test_an_invoice_not_yet_issued_is_priced_at_the_rate_today(self):
        request = milestone_invoice_request(self.job.name, self.deposit.name)
        self.assertEqual(request["vat_pct"], self.job.vat_pct)
        self.assertIsNone(request["invoice_no"])

    def test_no_save_quietly_fills_in_an_invoice_issued_before_this(self):
        """The rows that already existed when this shipped were issued at
        some rate nobody wrote down. Whatever fills that in has to be a
        deliberate act, not a save that happened to run today."""
        self.make_it_look_invoiced_before_this_shipped()

        frappe.get_doc("Job", self.job.name).save()
        row = self.row()
        self.assertTrue(row["invoiced_on"])
        self.assertEqual(row["invoice_vat_pct"], 0)

    def test_the_patch_gives_an_older_invoice_the_rate_it_was_written_at(self):
        """Once, on migrate, and from the job - whose rate is frozen at
        the day it was won, so this is the number that produced the
        request the accountant worked from, not a restatement."""
        self.make_it_look_invoiced_before_this_shipped()

        record_invoice_vat_basis.execute()
        frappe.clear_document_cache("Job", self.job.name)
        self.assertEqual(self.row()["invoice_vat_pct"], self.job.vat_pct)

    def test_the_request_splits_the_amount_on_the_basis_it_states(self):
        request = milestone_invoice_request(self.job.name, self.deposit.name)
        self.assertEqual(request["net"] + request["vat"], request["amount"])


class TestTheMilestonePayload(MilestoneInvoiceTestCase):
    """The key set is the interface between two systems."""

    def test_a_milestone_row_carries_exactly_the_documented_keys(self):
        assert_keys(self, self.row(), MILESTONE_KEYS, "milestone")

    def test_the_row_a_status_change_answers_with_is_the_same_shape(self):
        assert_keys(self, self.issue(), MILESTONE_KEYS, "issued milestone")

    def test_the_invoice_crosses_the_wire_as_values_not_as_prose(self):
        self.issue()
        row = self.row()
        # A moment, whatever Frappe hands back for a Datetime column -
        # the wire turns it into a timestamp the frontend can parse.
        self.assertIsNotNone(frappe.utils.get_datetime(row["invoiced_on"]))
        self.assertIsInstance(row["invoice_no"], str)
        self.assertIsInstance(row["invoice_vat_pct"], (int, float))
        self.assertNotIsInstance(row["invoice_vat_pct"], bool)

    def test_an_invoice_request_carries_exactly_the_documented_keys(self):
        self.issue()
        request = milestone_invoice_request(self.job.name, self.deposit.name)
        assert_keys(self, request, INVOICE_REQUEST_KEYS, "invoice request")
        assert_money(self, request, "amount", "net", "vat", where="invoice request")
        assert_no_founder_chain(self, request, "invoice request")

    def test_no_second_record_holds_the_same_money(self):
        """The invoice is three fields on the milestone it bills. A
        doctype of its own would be a second copy of an amount that must
        never be able to disagree with the quote it came from."""
        self.assertEqual(
            frappe.get_all(
                "DocType",
                filters={"module": "AuraOS", "name": ["like", "%Invoice%"]},
                pluck="name",
            ),
            [],
        )


class TestWhoMayIssueAnInvoice(MilestoneInvoiceTestCase):
    def test_the_producer_may_record_the_invoice_too(self):
        """Money-in is not founder-only: the producer runs the stages
        that make a payment due and already sends the request text."""
        frappe.set_user(PRODUCER)
        row = self.issue()
        self.assertEqual(row["invoice_no"], NUMBER)
        self.assertEqual(row["invoice_vat_pct"], self.job.vat_pct)

    def test_the_producer_reads_the_basis_rather_than_being_shown_a_blank(self):
        """Nothing is hidden for permission reasons - if a session may
        read the milestone it reads the whole invoice on it."""
        self.issue()
        frappe.set_user(PRODUCER)
        assert_keys(self, self.row(), MILESTONE_KEYS, "producer milestone")
        self.assertEqual(self.row()["invoice_no"], NUMBER)

    def test_an_outsider_may_not_issue_one(self):
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            self.issue()

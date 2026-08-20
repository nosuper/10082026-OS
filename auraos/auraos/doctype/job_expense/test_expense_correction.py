"""Seam tests for correcting a logged expense (#125).

The hole this closes is the one #121's spec could only describe: **the
exposure tile's number could go up and could not come down.**
`log_job_expense` has always accepted an invoice number, no screen ever
passed one, and there was no endpoint to update or delete an expense at
all - so the two things that take money out of the founder's tax figure,
recording the paper and fixing the attribution, were unreachable by
anybody using the app.

What only a site can prove, and what is proved here:

1. **Recording the invoice number moves money out of the exposure**, and
   into the covered half rather than out of the accounting altogether.
2. **Attributing a payment to a line that comes with paper takes it out
   entirely** - the other lever on the same figure, and the reason
   `cost_line` is editable here and not only at logging time.
3. **Correcting an amount reconciles the ledger by itself.** No posting
   call was added: `Job Expense.on_update` already hangs `post_payment`
   off the save and `auraos.lib.ledger.posting` answers a changed amount
   with REPOST. The entry keeps the account it was posted to, which is
   `restated`'s stated principle - where the money went is not something
   a later save is evidence about.
4. **A closed job refuses all of it**, in the doctype rather than in the
   endpoint, so the freeze #123 put on the record cannot drift away from
   the freeze the screen believes in.

The arithmetic of exposure itself is pinned framework-free in
tests/test_exposure.py, and the posting rules in tests/test_ledger.py.
Nothing here re-tests either.

**These are also the first tests of #123's freeze.** `reject_change_after_close`
argues in its own docstring that all three ways of changing a closed job's
spending have to be gated - edit, add and delete - because `on_trash` walks a
ledger entry back, and a freeze with a hole in it reads like a guarantee.
Nothing asserted any of it: there is no test in `auraos` that closes a job and
then touches its spending. Until #125 the rule was reachable only from the
Desk, which is presumably why. It is reachable from the app now, so the three
cases below are the first coverage that rule has ever had.

**On who may correct.** There is no per-job boundary in this app: `Job`
grants read and write to the Founder, Producer and System Manager roles
outright, and there is no `permission_query_conditions` hook, no
`has_permission` hook and no User Permission seeding anywhere in
`auraos`. So a producer may correct spending on any job, exactly as they
may log it on any job. This lane found that while going to assert the
opposite, and filed #143 rather than writing a test describing a product
we do not have; the founder ruled that it is the model, and **ADR-0003**
now records it along with the assignee model it becomes one day. The
positive is asserted in `TestWhoMayWriteAJobsMoney` (test_job_money.py),
which is where the correction endpoints below are pinned as open. The
boundary asserted here is the other one - somebody with no role at all
is refused.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import (
    create_job_from_deal,
    delete_job_expense,
    log_job_expense,
    no_invoice_exposure,
    update_job_expense,
)
from auraos.auraos.doctype.cash_account.cash_account import DEFAULT_FIELD
from auraos.auraos.doctype.deal.test_deal import FOUNDER, OUTSIDER, PRODUCER
from auraos.auraos.doctype.job.job import CLOSED_STAGE
from auraos.auraos.doctype.job.test_job import won_deal
from auraos.lib import ledger
from auraos.lib.settlement import FROM_COMPANY
from auraos.tests.utils import make_test_user

BANK = "Vietcombank - main"
PETTY = "Két tiền mặt"

# Two of the lines won_deal() quotes: one whose tax treatment says no
# invoice is coming, one that comes with paper.
NO_INVOICE_DESCRIPTION = "Ăn uống đoàn"
INVOICED_DESCRIPTION = "Studio"

# A category won_deal() quotes, so an expense may carry it.
CATEGORY = "Thiết bị"


class CorrectionTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")
        self.clear_money()
        frappe.get_doc({"doctype": "Cash Account", "account_name": BANK}).insert()
        self.job = frappe.get_doc("Job", create_job_from_deal(won_deal().name)["name"])

    def tearDown(self):
        frappe.set_user("Administrator")
        self.clear_money()
        super().tearDown()

    def clear_money(self):
        for entry in frappe.get_all("Cash Ledger Entry", pluck="name"):
            frappe.delete_doc("Cash Ledger Entry", entry, force=True)
        frappe.db.set_single_value("AuraOS Settings", DEFAULT_FIELD, None)
        for account in frappe.get_all("Cash Account", pluck="name"):
            frappe.delete_doc("Cash Account", account, force=True)

    def line_named(self, description):
        (row,) = [r for r in self.job.cost_lines if r.description == description]
        return row.name

    def spend(self, amount=3_000_000, **fields):
        """One expense, paid by the company so that it posts."""
        row = log_job_expense(
            self.job.name,
            amount,
            category=CATEGORY,
            description="Chi thật",
            paid_from=FROM_COMPANY,
            **fields,
        )
        return row["name"]

    def correct(self, name, **fields):
        """The endpoint states the row, so every call here states it."""
        stated = {
            "amount": 3_000_000,
            "category": CATEGORY,
            "description": "Chi thật",
            "cost_line": None,
            "invoice_no": None,
        }
        stated.update(fields)
        return update_job_expense(name, **stated)

    def report(self):
        frappe.set_user(FOUNDER)
        out = no_invoice_exposure()
        frappe.set_user("Administrator")
        return out

    def mine(self, report):
        return [row for row in report["lines"] if row["job"] == self.job.name]

    def entry_for(self, expense):
        name = ledger.entry_name(ledger.JOB_EXPENSE, expense)
        if not frappe.db.exists("Cash Ledger Entry", name):
            return None
        return frappe.get_doc("Cash Ledger Entry", name)

    def close_the_job(self):
        """Re-read before saving, the way test_cash_ledger does it: the
        doc this case has been holding since setUp is not what a save
        should be built on once other things have written to the site."""
        job = frappe.get_doc("Job", self.job.name)
        job.stage = CLOSED_STAGE
        job.save()
        self.job = job


class TestTheFigureCanNowComeDown(CorrectionTestCase):
    def test_recording_the_invoice_number_moves_the_money_to_covered(self):
        """The whole ticket, in one test. Paper obtained for spending
        that already happened is not a second payment - the amount stays
        on the job and leaves the tax figure."""
        line = self.line_named(NO_INVOICE_DESCRIPTION)
        expense = self.spend(850_000, cost_line=line)

        before = self.report()
        self.assertEqual(len(self.mine(before)), 1)
        exposed = before["uncovered_total"]
        covered = before["covered_total"]

        self.correct(expense, amount=850_000, cost_line=line, invoice_no="HD-2026-118")

        after = self.report()
        self.assertEqual(self.mine(after), [])
        self.assertEqual(after["uncovered_total"], exposed - 850_000)
        self.assertEqual(after["covered_total"], covered + 850_000)

    def test_the_tax_falls_with_it(self):
        """The figure the founder actually reads is the tax, and it is
        recomputed from the total rather than stored."""
        line = self.line_named(NO_INVOICE_DESCRIPTION)
        expense = self.spend(2_000_000, cost_line=line)
        before = self.report()

        self.correct(expense, amount=2_000_000, cost_line=line, invoice_no="HD-1")

        after = self.report()
        self.assertLess(after["tndn_exposure"], before["tndn_exposure"])
        self.assertEqual(
            after["tndn_exposure"],
            round(after["uncovered_total"] * after["rate_pct"] / 100),
        )

    def test_attributing_to_an_invoiced_line_takes_it_out_entirely(self):
        """The second lever: unattributed money counts as exposed until
        somebody says what it is, and saying so is a correction."""
        expense = self.spend(1_200_000)
        self.assertEqual(len(self.mine(self.report())), 1)

        self.correct(
            expense, amount=1_200_000, cost_line=self.line_named(INVOICED_DESCRIPTION)
        )

        self.assertEqual(self.mine(self.report()), [])

    def test_taking_the_invoice_number_off_puts_the_exposure_back(self):
        """Derived, not stored. An invoice number entered by mistake is
        a correction like any other, and the figure follows it back."""
        line = self.line_named(NO_INVOICE_DESCRIPTION)
        expense = self.spend(900_000, cost_line=line, invoice_no="HD-WRONG")
        self.assertEqual(self.mine(self.report()), [])

        self.correct(expense, amount=900_000, cost_line=line)

        (row,) = self.mine(self.report())
        self.assertEqual(row["amount"], 900_000)
        self.assertFalse(row["covered"])

    def test_a_correction_that_touches_neither_field_moves_nothing(self):
        """So the two tests above are about the two fields rather than
        about saving the row at all."""
        line = self.line_named(NO_INVOICE_DESCRIPTION)
        expense = self.spend(700_000, cost_line=line)
        before = self.report()

        self.correct(expense, amount=700_000, cost_line=line, description="Chi khác")

        self.assertEqual(self.report()["uncovered_total"], before["uncovered_total"])


class TestTheLedgerFollowsTheCorrection(CorrectionTestCase):
    def test_correcting_the_amount_restates_the_entry_rather_than_adding_one(self):
        expense = self.spend(3_000_000)
        self.assertEqual(self.entry_for(expense).amount, -3_000_000)

        self.correct(expense, amount=2_400_000)

        self.assertEqual(len(frappe.get_all("Cash Ledger Entry")), 1)
        self.assertEqual(self.entry_for(expense).amount, -2_400_000)

    def test_the_entry_keeps_the_account_it_was_posted_to(self):
        """Where the money went is not something a later save is
        evidence about - so a company that has since named a different
        default does not silently move history into it."""
        expense = self.spend(3_000_000)
        self.assertEqual(self.entry_for(expense).account, BANK)
        frappe.get_doc({"doctype": "Cash Account", "account_name": PETTY}).insert()
        frappe.db.set_single_value("AuraOS Settings", DEFAULT_FIELD, PETTY)

        self.correct(expense, amount=1_000_000)

        self.assertEqual(self.entry_for(expense).account, BANK)

    def test_deleting_takes_the_entry_back_out(self):
        expense = self.spend(3_000_000)
        self.assertIsNotNone(self.entry_for(expense))

        delete_job_expense(expense)

        self.assertIsNone(self.entry_for(expense))
        self.assertFalse(frappe.db.exists("Job Expense", expense))

    def test_deleting_leaves_no_exposure_behind_either(self):
        line = self.line_named(NO_INVOICE_DESCRIPTION)
        expense = self.spend(650_000, cost_line=line)
        self.assertEqual(len(self.mine(self.report())), 1)

        delete_job_expense(expense)

        self.assertEqual(self.mine(self.report()), [])


class TestAClosedJobRefusesBoth(CorrectionTestCase):
    def test_a_correction_is_refused_after_the_job_closes(self):
        expense = self.spend(3_000_000)
        self.close_the_job()

        with self.assertRaises(frappe.ValidationError):
            self.correct(expense, amount=1_000_000)

        self.assertEqual(frappe.db.get_value("Job Expense", expense, "amount"), 3_000_000)

    def test_a_delete_is_refused_after_the_job_closes(self):
        """The direction that matters most: on_trash walks the ledger
        entry back, so a freeze with a hole here would be the one that
        moves money and leaves nothing saying it was adjusted."""
        expense = self.spend(3_000_000)
        self.close_the_job()

        with self.assertRaises(frappe.ValidationError):
            delete_job_expense(expense)

        self.assertTrue(frappe.db.exists("Job Expense", expense))
        self.assertEqual(self.entry_for(expense).amount, -3_000_000)

    def test_reopening_the_job_makes_it_correctable_again(self):
        """The freeze is a state, not a one-way door: correcting a
        closed job's record is a deliberate, visible act rather than an
        impossible one."""
        expense = self.spend(3_000_000)
        self.close_the_job()
        job = frappe.get_doc("Job", self.job.name)
        job.stage = "Delivery"
        job.save()

        self.correct(expense, amount=1_000_000)

        self.assertEqual(frappe.db.get_value("Job Expense", expense, "amount"), 1_000_000)


class TestWhoMayCorrect(CorrectionTestCase):
    def test_a_producer_corrects_the_spending_they_logged(self):
        """Money out is not founder-only, and never has been: the person
        on the shoot is the one who knows the invoice arrived."""
        line = self.line_named(NO_INVOICE_DESCRIPTION)
        expense = self.spend(500_000, cost_line=line)

        frappe.set_user(PRODUCER)
        self.correct(expense, amount=500_000, cost_line=line, invoice_no="HD-9")
        frappe.set_user("Administrator")

        self.assertEqual(
            frappe.db.get_value("Job Expense", expense, "invoice_no"), "HD-9"
        )

    def test_somebody_with_no_role_may_not_correct(self):
        expense = self.spend(3_000_000)

        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            self.correct(expense, amount=1)

    def test_somebody_with_no_role_may_not_delete(self):
        expense = self.spend(3_000_000)

        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            delete_job_expense(expense)


class TestItStatesTheRow(CorrectionTestCase):
    def test_a_field_left_out_is_cleared_rather_than_kept(self):
        """Documented behaviour, asserted so it stays deliberate: the
        caller is a row editor holding every value, and an endpoint that
        quietly kept what it was not told about would make "clear this"
        unexpressible."""
        expense = self.spend(3_000_000, cost_line=self.line_named(INVOICED_DESCRIPTION))

        update_job_expense(expense, amount=3_000_000)

        row = frappe.get_doc("Job Expense", expense)
        self.assertIsNone(row.category)
        self.assertIsNone(row.description)
        self.assertIsNone(row.cost_line)

    def test_an_amount_of_nothing_is_refused_as_it_is_at_logging(self):
        expense = self.spend(3_000_000)

        with self.assertRaises(frappe.ValidationError):
            self.correct(expense, amount=0)

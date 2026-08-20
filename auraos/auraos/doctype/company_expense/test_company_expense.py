"""Seam tests for the company expense record (#14/#109).

The record that made a period tax figure possible to think about: until
it existed every cost in AuraOS belonged to a job, so the company's own
upkeep - rent, a client lunch, a printer - had nowhere to be written
down, and any TNDN figure computed from these tables omitted all of it.

The arithmetic and the entry's shape are pinned framework-free in
tests/test_ledger.py. What only a site can prove is here:

1. **Saving one posts to the cash ledger, under its own flow, with no
   job.** `Entry.job` has been optional since #99 and nothing used it;
   this is the first movement that has no job to name.
2. **Marking it for depreciation does not touch the ledger.** The flag
   says how the accountant may *treat* the cost, not whether money left
   the bank. It left. A flag that suppressed the posting would make the
   cash screens disagree with the bank statement.
3. **A producer cannot see it at all** - not through the ORM and not
   through the REST layer - because #14 asks for invisible via UI, API
   and search, and that is a permission matrix rather than an endpoint
   check. There is deliberately no Producer row in the doctype.
4. **VAT recorded on an invoice has to name the invoice**, and cannot
   exceed what was paid. Input VAT feeds a tax figure directly, so a
   typo here is the direction that costs money at an audit.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.auraos.doctype.deal.test_deal import FOUNDER, PRODUCER
from auraos.lib import ledger
from auraos.tests.utils import make_test_user

CATEGORY = "Chi phí tiếp khách"


class CompanyExpenseTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        if not frappe.db.exists("Company Expense Category", CATEGORY):
            frappe.get_doc(
                {"doctype": "Company Expense Category", "category_name": CATEGORY}
            ).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.set_user("Administrator")

    def log(self, **values):
        doc = frappe.get_doc(
            {
                "doctype": "Company Expense",
                "spent_on": "2026-08-10",
                "amount": 2_200_000,
                "category": CATEGORY,
                "description": "Cơm khách",
                **values,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc

    def entry_for(self, doc):
        name = ledger.entry_name(ledger.COMPANY_EXPENSE, doc.name)
        return frappe.db.get_value(
            "Cash Ledger Entry",
            name,
            ["amount", "flow", "job", "account"],
            as_dict=True,
        )

    def test_saving_one_posts_a_movement_with_no_job(self):
        doc = self.log()
        entry = self.entry_for(doc)
        self.assertIsNotNone(entry, "a company expense posted nothing")
        self.assertEqual(entry.amount, -2_200_000)
        self.assertEqual(entry.flow, ledger.COMPANY_EXPENSE)
        # The point of the fifth flow. Every other entry in the ledger
        # names a job; this one has none to name and must not invent one.
        self.assertIsNone(entry.job)

    def test_marking_it_for_depreciation_does_not_unpost_the_money(self):
        """The flag is about a tax return, not about the bank.

        The tempting reading - "not a cost this period, so not a
        movement this period" - would leave the cash screens short by
        the amount and disagreeing with the statement they exist to
        match.
        """
        doc = self.log(for_depreciation=1)
        entry = self.entry_for(doc)
        self.assertIsNotNone(entry, "a depreciated purchase posted nothing")
        self.assertEqual(entry.amount, -2_200_000)

        # And turning the flag on afterwards leaves it alone too.
        plain = self.log()
        plain.for_depreciation = 1
        plain.save(ignore_permissions=True)
        self.assertEqual(self.entry_for(plain).amount, -2_200_000)

    def test_deleting_one_takes_its_entry_back_out(self):
        doc = self.log()
        name = ledger.entry_name(ledger.COMPANY_EXPENSE, doc.name)
        doc.delete(ignore_permissions=True)
        self.assertFalse(frappe.db.exists("Cash Ledger Entry", name))

    def test_correcting_the_amount_reconciles_by_itself(self):
        """No posting call is added anywhere: `on_update` hangs the same
        `post_payment` off every save and `ledger.posting` answers a
        changed amount with REPOST."""
        doc = self.log()
        doc.amount = 3_300_000
        doc.save(ignore_permissions=True)
        self.assertEqual(self.entry_for(doc).amount, -3_300_000)

    def test_a_producer_cannot_read_one(self):
        """#14's third criterion, at the layer that decides it.

        There is no Producer row in the doctype's permissions, so this
        is refused by the framework rather than by any endpoint of ours
        - which is what makes it true of the REST API and the awesome
        bar as well as of a screen we wrote.
        """
        doc = self.log()
        frappe.set_user(PRODUCER)
        self.assertFalse(frappe.has_permission("Company Expense", "read"))
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc("Company Expense", doc.name).check_permission("read")

    def test_the_founder_can(self):
        """The other half of the same assertion: a gate that refused
        everybody would pass the test above and be useless."""
        doc = self.log()
        frappe.set_user(FOUNDER)
        self.assertTrue(frappe.has_permission("Company Expense", "read"))
        self.assertEqual(frappe.get_doc("Company Expense", doc.name).amount, 2_200_000)

    def test_vat_recorded_must_name_the_invoice_it_came_from(self):
        with self.assertRaises(frappe.ValidationError):
            self.log(invoice_vat_amount=200_000)

    def test_vat_cannot_exceed_what_was_paid(self):
        with self.assertRaises(frappe.ValidationError):
            self.log(invoice_no="INV-9", invoice_vat_amount=9_900_000)

    def test_an_invoice_date_defaults_to_the_day_it_was_paid(self):
        """The ordinary receipt has both dates the same.

        Demanded rather than defaulted, this field would put a blank on
        every coffee bill - and an expense left unrecorded because the
        form asked one question too many mismatches the accountant's
        return invisibly, where a mis-dated one mismatches it in a
        section the founder is reading.
        """
        doc = self.log(invoice_no="INV-9", invoice_vat_amount=200_000)
        self.assertEqual(str(frappe.get_doc("Company Expense", doc.name).invoice_date), "2026-08-10")

    def test_an_invoice_dated_differently_keeps_its_own_date(self):
        """Rent invoiced last month and paid this one - the case the
        default exists to be corrected in, and the reason input VAT can
        be dated by the invoice at all."""
        doc = self.log(
            invoice_no="INV-RENT", invoice_vat_amount=500_000, invoice_date="2026-07-28"
        )
        self.assertEqual(str(frappe.get_doc("Company Expense", doc.name).invoice_date), "2026-07-28")

    def test_no_invoice_means_no_invoice_date(self):
        """Nothing to date. A default here would invent an invoice that
        does not exist and put its VAT-less self in a VAT period."""
        doc = self.log()
        self.assertIsNone(frappe.get_doc("Company Expense", doc.name).invoice_date)

    def test_an_invoice_and_its_vat_are_kept_as_recorded(self):
        """Recorded, not derived - the supplier wrote this invoice, so
        the number on their paper is the fact, and reconstructing it by
        division could land a đồng away from what the accountant holds.
        """
        doc = self.log(invoice_no="INV-9", invoice_vat_amount=200_000)
        stored = frappe.get_doc("Company Expense", doc.name)
        self.assertEqual(stored.invoice_no, "INV-9")
        self.assertEqual(stored.invoice_vat_amount, 200_000)

"""Money the company spent on itself - rent, a client lunch, a printer.

The record #109 was missing. Every other expense in AuraOS belongs to a
job, which is why a period TNDN figure could not be computed: the whole
class of cost that keeps the company running had nowhere to be written
down. This is that place.

**No job, deliberately.** It is not an optional link left blank - a
`Job Expense` with no job would be a job expense that failed to say
which shoot it was for. Rent is not an unattributed shoot cost; it is a
different kind of money, and it posts to the ledger under its own flow.

**The VAT on the invoice is recorded, not derived, and that asymmetry is
the point.** For a milestone we *issue* the invoice, so the split is
ours to compute - `milestones.invoice_split` divides the VAT back out of
a VAT-inclusive amount and the two halves add back exactly. A purchase
invoice is somebody else's document: the supplier decided what the VAT
line says, and reconstructing it by division can land a đồng away from
the paper the accountant is holding. So the number on their invoice is
stored, for the same reason `invoice_vat_pct` is stored on a milestone -
it is a historical fact about a document rather than a cached
derivation. What is derived is the net, which is `amount` less that VAT.

**Always posts, including the ones marked for depreciation.** A job
expense asks whether the company paid, because a producer spending their
float moves no company money that day. An overhead has no float to come
out of - and `for_depreciation` is a statement about how a cost will be
*treated on a return*, not about whether money left the bank. It did. A
flag that suppressed the ledger entry would make the cash screens
disagree with the bank statement, which is the one thing they exist to
match.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from auraos.auraos.doctype.cash_account.cash_account import default_account
from auraos.auraos.doctype.cash_ledger_entry import cash_ledger_entry
from auraos.lib import ledger


class CompanyExpense(Document):
    def before_validate(self):
        # The company's default account unless the founder named another.
        # A company card and the bank are different places money leaves
        # from, and the founder records which - but not naming one is
        # not a reason to post nothing.
        if not self.paid_from:
            self.paid_from = default_account()

    def validate(self):
        self.validate_amount()
        self.validate_invoice()

    def on_update(self):
        # After the save, because an expense has no name to post against
        # until it has been written - the same order Job Expense uses.
        post_payment(self)

    def on_trash(self):
        # A deleted expense paid nobody, so the entry it earned comes
        # back out.
        post_payment(self, moved=False)

    def validate_amount(self):
        if not self.amount or float(self.amount) <= 0:
            frappe.throw(_("An expense needs an amount"), frappe.ValidationError)

    def validate_invoice(self):
        """The VAT figure and the invoice it came from travel together.

        A VAT amount with no invoice number is a deduction with no paper
        behind it, which is exactly the thing the accountant cannot use
        and the thing an audit asks for. The same rule the milestone
        side states from the other direction: a number nobody issued is
        not an invoice number.

        And VAT cannot exceed what was paid. A typo in this field feeds
        input VAT directly, where it would quietly reduce a tax figure -
        the direction that costs money at an audit rather than at the
        bank.
        """
        vat = float(self.invoice_vat_amount or 0)
        if vat and not (self.invoice_no or "").strip():
            frappe.throw(
                _("VAT on the invoice needs the invoice number it came from"),
                frappe.ValidationError,
            )
        if vat < 0:
            frappe.throw(_("VAT on the invoice cannot be negative"), frappe.ValidationError)
        if vat > float(self.amount or 0):
            frappe.throw(
                _("VAT cannot be more than the amount paid"), frappe.ValidationError
            )


def post_payment(expense, moved=True):
    """Record the money this overhead moved out of a company account.

    Hung off the save rather than off an endpoint, for the reason #100
    gives about every other flow: the endpoint is the door the screen
    happens to use, and a Desk edit walks straight past it.

    The account is the one on the record. Where the money went is
    decided once - an entry already on file keeps the account it was
    posted to - so correcting the account on a saved expense does not
    silently move history.
    """
    values = expense.as_dict()
    cash_ledger_entry.sync(
        flow=ledger.COMPANY_EXPENSE,
        source_name=expense.name,
        wanted=ledger.company_expense(values, expense.paid_from or default_account()),
        moved=moved,
    )

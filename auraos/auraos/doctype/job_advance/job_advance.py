"""An advance: company cash put in someone's hands for one job.

The founder records it; the producer spends it and logs the receipts.
What is left over is the float the two of them settle (T8, issue #10).
"""

import frappe
from frappe import _
from frappe.model.document import Document

from auraos.auraos.doctype.cash_account.cash_account import default_account
from auraos.auraos.doctype.cash_ledger_entry import cash_ledger_entry
from auraos.auraos.doctype.deal.deal import holds_operating_role
from auraos.lib import ledger


class JobAdvance(Document):
    def validate(self):
        self.validate_amount()
        self.validate_recipient()

    def on_update(self):
        # After the save: an advance has no name to post against until
        # it has been written.
        post_transfer(self)

    def on_trash(self):
        # An advance deleted was an advance never handed over.
        post_transfer(self, moved=False)

    def validate_amount(self):
        if not self.amount or float(self.amount) <= 0:
            frappe.throw(
                _("An advance needs an amount"), frappe.ValidationError
            )

    def validate_recipient(self):
        """Only the two operating roles can hold a float.

        A float is money the company is still owed; pointing one at a
        user who does not work here would open a float nobody is ever
        going to settle.
        """
        if not holds_operating_role(self.recipient):
            frappe.throw(
                _("An advance goes to someone holding the Founder or Producer role"),
                frappe.ValidationError,
            )


def post_transfer(advance, moved=True):
    """Record the cash this advance put in somebody's hands (#100).

    Hung off the save, not off auraos.api.record_job_advance: a founder
    correcting the amount in Desk moves the same money as the endpoint
    does, and a posting that lives in an endpoint is a posting a Desk
    save walks past.

    Money out the moment it is transferred, whatever the holder later
    spends it on. That is why an expense paid out of a float posts
    nothing of its own - the đồng left the company here - and why the
    float's settlement posts only the difference that comes back.
    """
    values = advance.as_dict()
    cash_ledger_entry.sync(
        flow=ledger.CREW_ADVANCE,
        source_name=advance.name,
        wanted=ledger.crew_advance(values, default_account()),
        moved=moved and ledger.transferred(values),
    )

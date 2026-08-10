"""An advance: company cash put in someone's hands for one job.

The founder records it; the producer spends it and logs the receipts.
What is left over is the float the two of them settle (T8, issue #10).
"""

import frappe
from frappe import _
from frappe.model.document import Document

from auraos.auraos.doctype.deal.deal import holds_operating_role


class JobAdvance(Document):
    def validate(self):
        self.validate_amount()
        self.validate_recipient()

    def validate_amount(self):
        if not self.amount or float(self.amount) <= 0:
            frappe.throw(
                _("An advance needs an amount"), frappe.ValidationError
            )

    def validate_recipient(self):
        """Only the two operating roles can hold a float.

        A float is money the company is still owed; pointing one at a
        user who does not work here would leave a balance nobody is
        ever going to settle.
        """
        if not holds_operating_role(self.recipient):
            frappe.throw(
                _("An advance goes to someone holding the Founder or Producer role"),
                frappe.ValidationError,
            )

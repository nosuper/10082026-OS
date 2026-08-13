"""The record of a float being closed: who paid whom, and what it covered.

Settling is one click on the job's money view (story 34), and this is
what that click leaves behind. It is a transfer that happened, so the
numbers are frozen after the fact: a float that turns out to be wrong
is corrected by advancing, spending or settling again - never by
rewriting a payment already made.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from auraos.lib.settlement import direction_of

FROZEN_FIELDS = ("job", "recipient", "amount", "direction", "advanced", "spent")


class JobSettlement(Document):
    def before_validate(self):
        if not self.settled_on:
            self.settled_on = frappe.utils.now_datetime()
        if not self.settled_by:
            self.settled_by = frappe.session.user

    def validate(self):
        self.validate_amount()
        # Derived, never input - and only once the amount is known to be
        # a real transfer, because "Even" is not one of the options.
        self.direction = direction_of(self.amount)
        self.reject_changes()

    def validate_amount(self):
        if not self.amount or float(self.amount) == 0:
            frappe.throw(
                _("A settlement moves money - an even float has nothing to settle"),
                frappe.ValidationError,
            )

    def reject_changes(self):
        before = self.get_doc_before_save()
        if not before:
            return
        for field in FROZEN_FIELDS:
            if self.get(field) != before.get(field):
                frappe.throw(
                    _(
                        "{0} records a transfer that already happened and cannot "
                        "be edited - settle again instead."
                    ).format(_(self.meta.get_label(field))),
                    frappe.ValidationError,
                )

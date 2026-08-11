"""One payment out on a job — the thing logged on a phone during a shoot.

Kept to what can be entered in seconds: an amount, a category, and a
photo of the receipt. Everything else has a default that is right often
enough not to be typed (T8, issue #10, story 31).
"""

import frappe
from frappe import _
from frappe.model.document import Document

from auraos.lib.settlement import FROM_ADVANCE


class JobExpense(Document):
    def before_validate(self):
        # Whoever is logging it is normally whoever paid it; the founder
        # recording someone else's spending overrides this.
        if not self.paid_by:
            self.paid_by = frappe.session.user
        if not self.paid_from:
            self.paid_from = FROM_ADVANCE

    def validate(self):
        self.validate_amount()
        self.validate_category()

    def validate_amount(self):
        if not self.amount or float(self.amount) <= 0:
            frappe.throw(_("An expense needs an amount"), frappe.ValidationError)

    def validate_category(self):
        """The category has to be one of the entries the job was quoted.

        That is the whole mechanism behind actual-vs-quoted per package
        (story 32): a category that could be anything would leave the
        comparison full of holes. Empty stays allowed — money gets spent
        on things nobody quoted, and a row called Uncategorised is far
        better than pretending it wasn't spent.
        """
        if not self.category:
            return
        allowed = frappe.get_doc("Job", self.job).expense_categories()
        if self.category not in allowed:
            frappe.throw(
                _("{0} is not a category on this job — its packages are: {1}").format(
                    self.category, ", ".join(allowed) or _("none")
                ),
                frappe.ValidationError,
            )

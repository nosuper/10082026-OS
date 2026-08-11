"""One founder-only overhead record for one calendar month."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class MonthlyOverhead(Document):
    def validate(self):
        if not self.month:
            frappe.throw(_("Month is required"), frappe.MandatoryError)
        month = getdate(self.month)
        self.month = month.replace(day=1)
        self.title = _("Monthly overhead {0}").format(month.strftime("%B %Y"))
        for item in self.items:
            if flt(item.amount) < 0:
                frappe.throw(_("Overhead amounts cannot be negative"))
        self.total = sum(flt(item.amount) for item in self.items)

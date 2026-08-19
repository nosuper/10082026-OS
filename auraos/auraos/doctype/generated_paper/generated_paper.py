import frappe
from frappe.model.document import Document
from frappe.utils import now

from auraos.lib import paper_status


class GeneratedPaper(Document):
    """One row per paper ever generated: what it was, for whom, and
    whether it has come back signed.

    The status is the only field on a registry row a human ever changes,
    so the two stamps beside it are written here rather than by whoever
    is doing the changing. The Desk, the API and a script all record the
    same thing, and "who told me this was signed" has one answer.
    """

    def validate(self):
        # A row written before the status field existed loads blank; the
        # backfill patch fills those, and this keeps a stray one from
        # being saved back as a fourth state nobody agreed to.
        self.status = paper_status.status_or_draft(self.status)
        if self.has_value_changed("status"):
            self.status_changed_by = frappe.session.user
            self.status_changed_on = now()

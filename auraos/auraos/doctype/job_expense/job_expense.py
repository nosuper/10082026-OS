"""One payment out on a job - the thing logged on a phone during a shoot.

Kept to what can be entered in seconds: an amount, a category, and a
photo of the receipt. Everything else has a default that is right often
enough not to be typed (T8, issue #10, story 31).
"""

import frappe
from frappe import _
from frappe.model.document import Document

from auraos.auraos.doctype.cash_account.cash_account import default_account
from auraos.auraos.doctype.cash_ledger_entry import cash_ledger_entry
from auraos.lib import exposure, ledger
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
        self.validate_cover()

    def on_update(self):
        # After the save, because an expense has no name to post against
        # until it has been written.
        post_payment(self)

    def on_trash(self):
        # A deleted expense paid nobody, so the entry it earned comes
        # back out - the same walk-back a milestone dragged out of đã
        # thanh toán gets.
        post_payment(self, moved=False)

    def validate_amount(self):
        if not self.amount or float(self.amount) <= 0:
            frappe.throw(_("An expense needs an amount"), frappe.ValidationError)

    def validate_category(self):
        """The category has to be one of the entries the job was quoted.

        That is the whole mechanism behind actual-vs-quoted per package
        (story 32): a category that could be anything would leave the
        comparison full of holes. Empty stays allowed - money gets spent
        on things nobody quoted, and a row called Uncategorised is far
        better than pretending it wasn't spent.
        """
        if not self.category:
            return
        allowed = frappe.get_doc("Job", self.job).expense_categories()
        if self.category not in allowed:
            frappe.throw(
                _("{0} is not a category on this job - its packages are: {1}").format(
                    self.category, ", ".join(allowed) or _("none")
                ),
                frappe.ValidationError,
            )

    def validate_cover(self):
        """A replacement invoice has to point at a line it could replace.

        `covers_cost_line` is what makes a no-invoice line count as
        covered, and the status is derived from it rather than stored -
        so this link is the only thing standing between the founder's
        exposure tile and a number somebody typed. It is worth being
        strict about.

        Two ways it can be wrong, and both are rejected rather than
        ignored, because an ignored link reads on the tile as an
        exposure that has been dealt with:

        1. **A line that is not on this job.** A cost line name is a
           child row, and a typo or a copied name would silently cover
           somebody else's line - or nothing at all.
        2. **A line that already had an invoice.** Công ty and Cá nhân
           lines came with their paper. There is nothing to replace, so
           an expense claiming to replace it is a mistake about which
           line was meant.

        Deliberately a Data field validated here rather than a Link: the
        target is a child row, and a Link to a child doctype is a Frappe
        oddity that would buy nothing this method is not already doing.
        """
        if not self.covers_cost_line:
            return
        lines = {row.name: row for row in frappe.get_doc("Job", self.job).cost_lines}
        line = lines.get(self.covers_cost_line)
        if line is None:
            frappe.throw(
                _("That cost line is not on job {0}, so this expense cannot replace it.").format(
                    self.job
                ),
                frappe.ValidationError,
            )
        if not exposure.is_no_invoice(line.as_dict()):
            frappe.throw(
                _(
                    "{0} is a {1} line, so it already has an invoice behind it "
                    "and there is nothing to replace."
                ).format(line.description or self.covers_cost_line, line.tax_type),
                frappe.ValidationError,
            )


def post_payment(expense, moved=True):
    """Record the money this expense moved out of a company account (#100).

    Hung off the save rather than off auraos.api.log_job_expense, for the
    reason a milestone's posting is hung off the Job's save: the endpoint
    is the door the phone happens to use, and a Desk edit walks straight
    past it.

    Every save asks the same question - what should the ledger say about
    this payment - and auraos.lib.ledger.posting answers "nothing" once
    it already says it, so saving twice is not paying twice. It is also
    what makes the correction work: an expense moved off Company and onto
    a float takes its entry back, because that money did not leave a
    company account today, it left it the day the advance was made.

    The account is the company's default. Where the money went is decided
    once - an entry already on file keeps the account it was posted to.
    """
    values = expense.as_dict()
    cash_ledger_entry.sync(
        flow=ledger.JOB_EXPENSE,
        source_name=expense.name,
        wanted=ledger.job_expense(values, default_account()),
        moved=moved and ledger.paid_by_company(values),
    )

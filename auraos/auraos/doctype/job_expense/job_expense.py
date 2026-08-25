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
from auraos.lib import ledger
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
        self.reject_change_after_close()
        self.validate_amount()
        self.validate_category()
        self.validate_cost_line()

    def on_update(self):
        # After the save, because an expense has no name to post against
        # until it has been written.
        post_payment(self)

    def on_trash(self):
        # Gated for the same reason a save is: deleting an expense moves
        # the recorded total exactly as editing one does, and it walks
        # the ledger entry back with it. A closed job whose spending can
        # be deleted but not corrected is the wrong way round.
        self.reject_change_after_close()
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

    def reject_change_after_close(self):
        """A closed job's spending is a record, not a draft.

        The same rule Job.FROZEN_TABLES applies to the carried breakdown,
        at the other end of the job: cost lines freeze when the deal is
        won because they record what was sold, and expenses freeze when
        the job closes because they record what it cost. In between,
        both the amount and the category are meant to be corrected -
        that is what makes the actual figure worth comparing against the
        quote.

        **All three ways of changing the record, not just editing.**
        Adding an expense to a closed job and deleting one from it move
        the recorded total exactly as correcting one does. An earlier
        version of this gated only the edit, which left a closed job
        where spending could be *deleted* but not *corrected* - and
        because `on_trash` walks the ledger entry back, that is the one
        direction that moves the money and leaves nothing saying it was
        adjusted. A freeze with a hole in it is worse than none, because
        it reads like a guarantee.

        Reopen the job to change any of it. That is a deliberate, visible
        act, which is what a correction to a closed record should be.
        """
        from auraos.auraos.doctype.job.job import CLOSED_STAGE

        if frappe.db.get_value("Job", self.job, "stage") != CLOSED_STAGE:
            return
        frappe.throw(
            _(
                "Job {0} is closed, so its spending can no longer be changed. "
                "Reopen the job to correct it."
            ).format(self.job),
            frappe.ValidationError,
        )

    def validate_cost_line(self):
        """The quoted line this spend belongs to, if it belongs to one.

        Optional, and that is the point rather than an oversight: money
        gets spent on things nobody quoted, and forcing every expense at
        a line would either invent a line or push real spending into the
        wrong one. An expense naming no line reads as uncategorised,
        which is a true statement about it.

        What it must not be is a line on somebody else's job. A cost
        line name is a child row, easy to paste wrong, and a link to
        another job's line would quietly attribute this money there -
        and, on a Không hoá đơn line, quietly move a tax exposure with
        it.

        Deliberately no tax-type check any more. Under #11 this field
        meant "is the replacement invoice for", which only made sense on
        a line with no invoice behind it. It now means "spends against",
        which is true of every quoted line whatever its tax treatment,
        and it is that link that carries Không hoá đơn from the plan to
        the money.
        """
        if not self.cost_line:
            return
        lines = {row.name for row in frappe.get_doc("Job", self.job).cost_lines}
        if self.cost_line not in lines:
            frappe.throw(
                _("That quoted line is not on job {0}.").format(self.job),
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

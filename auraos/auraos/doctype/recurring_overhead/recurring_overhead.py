"""A cost the company pays every month - rent, a salary, a subscription.

**A template, and deliberately not a payment.** #14's ask is that the
founder must not type rent twelve times a year. The obvious answer is a
scheduler that writes a `Company Expense` on the first of every month,
and it is the wrong one: a Company Expense posts to the cash ledger, so
an invented one makes the cash screens disagree with the bank statement -
the single thing they exist to match. This record says what is owed and
when; `auraos.lib.recurring` works out which months have come round
unrecorded; the founder confirms them in one act for the month. Twelve
forms a year become twelve clicks, and no đồng is ever posted that
nobody decided.

**No Producer row in the permissions**, like `Company Expense` and
`Company Expense Category`. This table is the payroll and the rent: it
says what the company is committed to and what the people in it are
paid, which is the most founder-only thing in the app. Invisible via UI,
API and search is a permission matrix rather than an endpoint check, and
the absence of a row here is what makes it one.

**No depreciation flag, because a recurring cost is a running cost.**
`Company Expense.for_depreciation` marks a purchase the accountant may
spread over years - a camera. A thing bought every month is not that by
definition, and a template that could produce one would be a
contradiction the founder had to spot rather than a shape the model
refuses.

**No `last_generated_on`.** Which months have been recorded is a fact
about the payments - each carries the template it came from and the month
it covers - and a stamp here would be a second copy of it. The copy is
what goes stale the moment somebody deletes a payment, and it would leave
a month permanently uncollectable with nothing on screen to explain why.

**Changing the amount never restates a payment.** The figure here is what
the company is committed to from now on. A month that came out different
is corrected on that month's payment, where the correction is visible
beside the money it changed.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from auraos.lib.finance import as_date


class RecurringOverhead(Document):
    def validate(self):
        self.validate_amount()
        self.validate_window()

    def validate_amount(self):
        if not self.amount or float(self.amount) <= 0:
            frappe.throw(
                _("A standing cost needs an amount"), frappe.ValidationError
            )

    def validate_window(self):
        """The last month cannot come before the first.

        Reversed, the template runs in no month at all - which is a
        template that silently does nothing, the failure that looks like
        a feature working quietly. Refused at the record rather than
        worked around in `auraos.lib.recurring`, because the module's job
        is to read a window and not to guess which end the founder meant.
        """
        start, end = as_date(self.starts_on), as_date(self.ends_on)
        if start and end and end < start:
            frappe.throw(
                _("The last month cannot come before the first"),
                frappe.ValidationError,
            )

"""A bank statement, recorded as it arrived (#150).

**The statement is not ours and is never derived.** Every figure here
was printed by the bank, and the reason to keep it beside the ledger is
that the two can disagree - so a statement that could be edited after
import would destroy the only thing it was imported for. The facts
freeze on insert; the reconciliation does not.

That split is the whole controller:

- **The facts** - the period, the four totals, and every column of every
  line except the match - refuse to change after insert.
- **The match** - which ledger entry a line is confirmed against, and by
  whom - is the one thing a person may set, unset and set again.

**Imported only if the statement agrees with itself.** `lib.statement`
walks the opening balance through every line and checks the bank's own
totals; a sheet that fails is refused with the disagreement named, which
is also the parser's alarm - a row silently dropped reads exactly like a
statement that does not add up.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from auraos.lib import statement

# What a line records about the bank's document, as opposed to what we
# decided about it afterwards. Frozen after insert.
LINE_FACTS = (
    "effective_on",
    "transacted_at",
    "sequence",
    "description",
    "withdrawn",
    "deposited",
    "running_balance",
)

# The same, on the statement itself.
STATEMENT_FACTS = (
    "account",
    "period_from",
    "period_to",
    "opening",
    "withdrawn",
    "deposited",
    "closing",
)


class BankStatement(Document):
    def validate(self):
        self.reject_a_second_import()
        self.reject_changed_facts()
        self.reject_a_statement_that_disagrees_with_itself()
        self.stamp_matches()

    def reject_a_second_import(self):
        """One statement per account per period.

        A bank hands out the same PDF every time it is asked, so
        importing twice is the ordinary accident rather than the exotic
        one - and two copies would double every unmatched figure while
        looking like a busy month.
        """
        if not self.is_new():
            return
        twin = frappe.db.exists(
            "Bank Statement",
            {
                "account": self.account,
                "period_from": self.period_from,
                "period_to": self.period_to,
                "name": ["!=", self.name or ""],
            },
        )
        if twin:
            frappe.throw(
                _("{0} already holds this account's statement for that period").format(
                    twin
                ),
                frappe.DuplicateEntryError,
            )

    def reject_changed_facts(self):
        previous = self.get_doc_before_save()
        if not previous:
            return
        for field in STATEMENT_FACTS:
            if (self.get(field) or None) != (previous.get(field) or None):
                frappe.throw(
                    _("A statement records what the bank sent; {0} cannot be changed.").format(
                        _(self.meta.get_label(field))
                    ),
                    frappe.ValidationError,
                )
        was = {row.name: row for row in previous.get("lines") or []}
        if len(self.get("lines") or []) != len(was):
            frappe.throw(
                _("A statement's lines are the bank's own; none may be added or removed."),
                frappe.ValidationError,
            )
        for row in self.get("lines") or []:
            before = was.get(row.name)
            if not before:
                frappe.throw(
                    _("A statement's lines are the bank's own; none may be added."),
                    frappe.ValidationError,
                )
            for field in LINE_FACTS:
                if (row.get(field) or None) != (before.get(field) or None):
                    frappe.throw(
                        _("Line {0} records what the bank sent; it cannot be edited.").format(
                            row.sequence or row.idx
                        ),
                        frappe.ValidationError,
                    )

    def reject_a_statement_that_disagrees_with_itself(self):
        if not self.is_new():
            return
        said = statement.complaints(self.summary(), self.read_lines())
        if said:
            frappe.throw(
                _("This statement does not agree with itself: {0}").format(
                    "; ".join(said)
                ),
                frappe.ValidationError,
            )

    def stamp_matches(self):
        """Who confirmed a match, and when. Cleared with the match.

        Written here rather than by the endpoint so that a match set from
        the Desk carries the same record as one set from the screen.
        """
        previous = self.get_doc_before_save()
        was = {row.name: row for row in (previous.get("lines") if previous else []) or []}
        now = frappe.utils.now_datetime()
        for row in self.get("lines") or []:
            before = was.get(row.name)
            unchanged = before is not None and (before.matched_entry or None) == (
                row.matched_entry or None
            )
            if unchanged:
                continue
            row.matched_on = now if row.matched_entry else None
            row.matched_by = frappe.session.user if row.matched_entry else None

    # -- what the pure module needs --

    def summary(self):
        return {
            "opening": int(self.opening or 0),
            "withdrawn": int(self.withdrawn or 0),
            "deposited": int(self.deposited or 0),
            "closing": int(self.closing or 0),
        }

    def read_lines(self):
        """The lines as `lib.statement` reads them, in the bank's order."""
        return [
            {
                "sequence": row.sequence,
                "withdrawn": int(row.withdrawn or 0),
                "deposited": int(row.deposited or 0),
                "amount": int(row.deposited or 0) - int(row.withdrawn or 0),
                "running_balance": int(row.running_balance or 0),
            }
            for row in self.get("lines") or []
        ]

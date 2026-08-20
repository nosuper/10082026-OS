"""Money moving between two of the company's own accounts (#151).

Found in the July bank statement: `RUT QUY TIEN MAT`, fifteen million
out of the bank and into the cash box. The ledger modelled four ways
money enters or leaves the company and no way for it to merely change
pockets - so after any withdrawal the bank read too high and the box too
low, and stayed that way until something else happened to correct them.

**One record, two entries, and they cannot be separated.** The pair is
the design: money leaves one account and arrives at another in the same
act, so the company holds exactly what it held before. A half posted
alone would either invent money or lose it in transit, and would look
sound on every screen that reads one account at a time.

**Two flows rather than one, for the ledger's primary key.** An entry's
name is `{flow code}-{source}`, and that name is the guarantee that
posting the same movement twice is a duplicate key rather than a second
row. Two entries from one Cash Transfer would collide there. The choice
was to widen the key's shape for every flow to serve this one, or to
spell one concept as two words; the second costs nothing structural and
reads honestly per account. See `auraos.lib.ledger.FLOWS`.

**Founder-only, decided here on the Company Expense precedent** rather
than by a founder ruling: that is the other record of money belonging to
no job, and it is founder-only by doctype permission. #143's "any
producer may write job money" was explicitly about *job* money. Revisable
the day the founder delegates cash handling - and this paragraph is
where whoever does that should start.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from auraos.auraos.doctype.cash_ledger_entry import cash_ledger_entry
from auraos.lib import ledger


class CashTransfer(Document):
    def validate(self):
        self.validate_accounts()
        self.reject_moved_accounts()
        self.validate_amount()

    def on_update(self):
        # After the save, because a transfer has no name to post against
        # until it has been written - the order every other flow uses.
        post_movement(self)

    def on_trash(self):
        # A deleted transfer moved nothing, so both entries come back
        # out. Both, or the company's total changes by the amount.
        post_movement(self, moved=False)

    def validate_accounts(self):
        if self.from_account == self.to_account:
            frappe.throw(
                _("Money cannot be moved to the account it came from"),
                frappe.ValidationError,
            )

    def reject_moved_accounts(self):
        """Which accounts the money moved between cannot be corrected.

        **Found by a seam test, and it is the ledger's rule showing
        through rather than a limit invented here.**
        `auraos.lib.ledger.restates` compares only the amount and the
        day, on the stated principle that the account an entry already
        carries is where the money went and no later save is evidence
        about that. So a redirected transfer re-posts nothing: the record
        would say the money went to one account while the ledger says
        another, and every balance on the screen would come from the
        ledger. **A record and its posting disagreeing silently is worse
        than either answer.**

        The amount stays correctable, which is not an inconsistency: the
        same rule says amount and date restate, and the seam test proves
        both halves move together when it does.

        A transfer sent to the wrong account is deleted and recorded
        again. `on_trash` takes both entries back out, so that path ends
        with the ledger correct - which the alternative does not.
        """
        previous = self.get_doc_before_save()
        if not previous:
            return
        for field in ("from_account", "to_account"):
            if (self.get(field) or None) != (previous.get(field) or None):
                frappe.throw(
                    _(
                        "A transfer's accounts cannot be changed once it is "
                        "recorded - the ledger keeps the account it posted to. "
                        "Delete this transfer and record it again."
                    ),
                    frappe.ValidationError,
                )

    def validate_amount(self):
        if not self.amount or float(self.amount) <= 0:
            frappe.throw(_("A transfer needs an amount"), frappe.ValidationError)


def post_movement(doc, moved=True):
    """Bring both halves of this movement into line with the ledger.

    Two `sync` calls, each an ordinary reconciliation: the reconciler
    already knows how to post, restate and unpost one entry, and neither
    side needs to know about the other. What must not happen is one call
    without the other, which is why they are here in one function rather
    than at two call sites.

    A record that does not describe a movement - the same account twice,
    no amount, no day - yields no pair, and both sides are told nothing
    moved, which takes any entries already on file back out.
    """
    values = doc.as_dict()
    pair = ledger.transfer(values)
    sides = (
        (ledger.TRANSFER_OUT, pair[0] if pair else None),
        (ledger.TRANSFER_IN, pair[1] if pair else None),
    )
    for flow, wanted in sides:
        cash_ledger_entry.sync(
            flow=flow,
            source_name=doc.name,
            wanted=wanted,
            moved=bool(moved and wanted),
        )

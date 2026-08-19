"""One movement of money, recorded - the Frappe side (#99).

The rules live in auraos.lib.ledger; this module is the adapter that
reads what the ledger already says, applies the reconciliation those
rules return, and keeps entries out of anybody's hands.

**Nobody types an entry.** The doctype grants no create or write to
either operating role: an entry exists because money moved on a record
that says so, and `sync` is the only way in. That is what lets #101 call
a balance derived rather than agreed - a figure nobody can reach cannot
be argued with.

**A movement can only be recorded once.** The name of an entry is its
origin (`ledger.entry_name`), so the primary key refuses a second entry
for the same milestone even in the window where two racing saves both
believe they are the first. Reconciliation is what usually stops it; this
is what stops it when reconciliation cannot see the other transaction.
"""

from dataclasses import asdict

import frappe
from frappe import _
from frappe.model.document import Document

from auraos.lib import ledger

# The stored shape of an entry, in the order auraos.lib.ledger.Entry
# declares it. One list, so a field added there fails loudly here rather
# than being silently dropped on the way to the database.
ENTRY_FIELDS = [
    "account",
    "amount",
    "entry_date",
    "flow",
    "source_doctype",
    "source_name",
    "job",
    "description",
]


class CashLedgerEntry(Document):
    def autoname(self):
        """The origin, spelled - see auraos.lib.ledger.entry_name."""
        if self.flow not in ledger.FLOWS or not self.source_name:
            frappe.throw(
                _("A ledger entry must name the movement it came from"),
                frappe.ValidationError,
            )
        self.name = ledger.entry_name(self.flow, self.source_name)

    def validate(self):
        # The word follows the sign, always. Storing them independently
        # would let a row claim money came in while its amount says it
        # went out, and a balance is read off the amount.
        try:
            self.direction = ledger.direction_of(self.amount)
        except ValueError as refused:
            frappe.throw(str(refused), frappe.ValidationError)


def sync(flow, source_name, wanted, moved):
    """Bring the ledger into line with one movement of money.

    Handed what should be on file and whether money moved at all; the
    decision itself is auraos.lib.ledger.posting, which is where the four
    cases are argued. Returns the action taken so a caller - or a test -
    can see that a second attempt did nothing.
    """
    name = ledger.entry_name(flow, source_name)
    existing = stored(name)
    action = ledger.posting(wanted, existing, moved)
    if action in (ledger.UNPOST, ledger.REPOST):
        _remove(name)
    if action == ledger.POST:
        _insert(wanted)
    if action == ledger.REPOST:
        _insert(ledger.restated(existing, wanted))
    return action


def backfill(wanted):
    """Post one movement that predates the ledger, or leave it alone (#100).

    Deliberately not `sync`: reconciliation restates an entry whose
    amount or day no longer match, and a backfill has no business doing
    that. Anything already on file was posted by the save path from the
    same record and is the more recent reading of it - a patch sweeping
    the whole history is filling in what was missed, not auditing what
    was not.

    Which is also what makes running it twice free.
    """
    if wanted is None or stored(ledger.entry_name(wanted.flow, wanted.source_name)):
        return None
    return _insert(wanted)


def stored(name):
    """The entry on file for one movement, as the rules read it."""
    row = frappe.db.get_value(
        "Cash Ledger Entry", name, ENTRY_FIELDS, as_dict=True
    )
    return ledger.Entry(**row) if row else None


def entries_for(account):
    """Every entry against one account, newest movement first.

    Read with get_all, so #101 sums the same rows this posts.
    """
    return frappe.get_all(
        "Cash Ledger Entry",
        filters={"account": account},
        fields=["name", "direction", *ENTRY_FIELDS],
        order_by="entry_date desc, creation desc",
    )


def _insert(entry):
    """Write one entry, treating a race as the success it is.

    Two saves recording the same milestone at the same instant both see
    an empty ledger and both post; the primary key lets exactly one
    through. The loser has nothing to do - the entry it wanted is there.
    """
    doc = frappe.get_doc({"doctype": "Cash Ledger Entry", **asdict(entry)})
    try:
        doc.insert(ignore_permissions=True)
    except frappe.DuplicateEntryError:
        return None
    return doc


def _remove(name):
    """Take back an entry for money that turned out not to have moved."""
    frappe.delete_doc(
        "Cash Ledger Entry", name, force=True, ignore_permissions=True
    )

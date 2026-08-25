"""Where the company keeps its money - the Frappe side (#99).

A cash account is a name and nothing else: a bank account, the cash box,
a wallet. It holds no balance, by decision - #101 derives that by summing
the account's ledger entries, and a stored figure would be a second
opinion about money that somebody could type over.

The first account a company creates becomes the account collections land
in, because otherwise the founder does the work the ticket describes -
naming where the money is kept - and nothing posts until they find a
second setting they were never told about. It is written into AuraOS
Settings rather than inferred, so it is visible, changeable, and never
moves on its own when a second account appears.
"""

import frappe
from frappe.model.document import Document

from auraos.settings import setting

# Where the standing choice lives. On AuraOS Settings with the payment
# terms and the margin floor, because "where does money land by default"
# is the same kind of company-wide standing answer.
DEFAULT_FIELD = "default_cash_account"


class CashAccount(Document):
    def after_insert(self):
        adopt_as_default(self)


def adopt_as_default(account):
    """Make this the default account if the company has no default yet."""
    if default_account():
        return
    frappe.db.set_single_value("AuraOS Settings", DEFAULT_FIELD, account.name)


def default_account():
    """Where collected money lands unless the caller says otherwise.

    The stored name is checked against the accounts that exist: an
    account deleted after being made the default would otherwise send
    every posting at a link that resolves to nothing, and a save that
    records a payment must not fail over the company's bookkeeping.
    """
    name = setting(DEFAULT_FIELD, None)
    if not name:
        return None
    return name if frappe.db.exists("Cash Account", name) else None

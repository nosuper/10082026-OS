"""One transaction as the bank recorded it (#150).

No behaviour of its own: a line is a fact from somebody else's document,
and everything that may be decided about it - whether it matches a
ledger entry, and which - is decided on the parent, where the rest of
the statement is in view.
"""

from frappe.model.document import Document


class BankStatementLine(Document):
    pass

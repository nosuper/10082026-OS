"""Post the money that moved before there was a ledger to record it (#100).

Every posting path reconciles on save, which means a record written
before the ledger existed gets its entry the next time somebody happens
to open it. That is uneven rather than wrong: two studios with identical
histories end up with different ledgers depending on who edited what,
and a balance nobody can reproduce is not a balance. This sweeps the
history once so the ledger starts complete.

All four flows, not only the three #100 adds: a milestone collected
before #99 shipped has exactly the same problem as an advance
transferred before it, and a patch that fixed three quarters of a ledger
would be worse than none.

Everything lands in the company's default account, which is the only
honest answer available - nobody recorded where money went on a day
before there was anywhere to record it. Where that is wrong the founder
knows it and the entry is a fact about the past that the app should not
be guessing at a second time, so nothing here ever restates an entry
already on file (auraos...cash_ledger_entry.backfill).

A company that has not named an account yet gets nothing, by the same
rule the save paths follow. That is the one case this leaves open: the
history posts when the patch is re-run after the first account exists,
which is safe to do at any time - it re-reads the same records and skips
everything already posted.
"""

import frappe

from auraos.auraos.doctype.cash_account.cash_account import default_account
from auraos.auraos.doctype.cash_ledger_entry import cash_ledger_entry
from auraos.lib import ledger
from auraos.lib.milestones import PAID
from auraos.lib.settlement import FROM_COMPANY


def execute():
    account = default_account()
    if not account:
        return
    post(_client_payments(account))
    post(_job_expenses(account))
    post(_crew_advances(account))
    post(_float_settlements(account))


def post(wanted):
    """Write the entries none of these movements has yet.

    The rows are read as movements first and filtered second: a query
    can say "paid" but only auraos.lib.ledger decides whether that is
    money, so a milestone billing 0% of the quote drops out here rather
    than being kept out by a filter that has to be got right twice.
    """
    for entry in wanted:
        cash_ledger_entry.backfill(entry)


def _client_payments(account):
    """Milestones the client has paid - #99's known gap, closed."""
    rows = frappe.get_all(
        "Job Payment Milestone",
        filters={"parenttype": "Job", "status": PAID, "paid_on": ["is", "set"]},
        fields=["name", "parent", "title", "status", "amount", "paid_on"],
    )
    return [ledger.client_payment(row, account, job=row.parent) for row in rows]


def _job_expenses(account):
    """Only the vendors the company paid itself.

    An expense paid out of a float moved no money of the company's on the
    day it was spent - the advance is where that cash left - so the
    backfill draws the same line the save path does.
    """
    rows = frappe.get_all(
        "Job Expense",
        filters={"paid_from": FROM_COMPANY, "spent_on": ["is", "set"]},
        fields=[
            "name",
            "job",
            "amount",
            "spent_on",
            "paid_from",
            "category",
            "description",
        ],
    )
    return [ledger.job_expense(row, account) for row in rows]


def _crew_advances(account):
    rows = frappe.get_all(
        "Job Advance",
        filters={"transferred_on": ["is", "set"]},
        fields=["name", "job", "amount", "transferred_on", "recipient"],
    )
    return [ledger.crew_advance(row, account) for row in rows]


def _float_settlements(account):
    rows = frappe.get_all(
        "Job Settlement",
        filters={"settled_on": ["is", "set"]},
        fields=["name", "job", "amount", "settled_on", "recipient"],
    )
    return [ledger.float_settlement(row, account) for row in rows]

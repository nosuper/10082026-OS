"""covers_cost_line becomes cost_line, because it now means something else (#123).

#11 gave a Job Expense a link meaning "this expense is the replacement
invoice for that Không hoá đơn cost line". #123 replaces that with a
broader one: "this expense is spending against that quoted line",
whatever its tax type. The pair of records is the same; the claim about
them is not.

Renamed rather than reused under a rewritten description. `covers_`
means "answers for" and the new meaning is "spends against", so keeping
the name would leave the next reader believing a word that had stopped
being true - which is the shape of the defect that produced the ticket
this patch belongs to.

The values carry across unchanged: a row that pointed at a line still
points at it, and under the new meaning it still spends against it.
What it stops asserting is that the expense was the paperwork rather
than the payment.

Copied column to column rather than through frappe's rename_field. The
copy is one statement anybody can read and predict; rename_field's
behaviour when the target column already exists - and it does exist,
because reload_doc has just created it - is a detail of the framework
rather than of this migration. The old column is left in place rather
than dropped: it holds no meaning any more, it costs a few bytes a row,
and dropping a column carrying the only copy of somebody's data is not
a thing to do on the strength of a patch nobody has run twice.

Frappe runs a patch once, so the guard below only matters to a re-run
somebody performs deliberately. In that case it refills `cost_line`
from the stale column for any row where it has since been cleared by
hand. Theoretical, and stated here rather than defended against: the
machinery to tell "never set" from "deliberately cleared" costs more
than the case is worth.

**A hazard this patch deliberately does not fix, named here because the
next person to meet it will be reading this file.**

A #11-era covering expense is a `Job Expense` with an amount and
`paid_from = Company`. Under #11 it meant "this is the replacement
invoice for that line" - paperwork. Under #123 there is no such thing:
an expense is money that moved. So those rows now read as ordinary
spending, counted in `spent_total` and indistinguishable from a real
payment.

That is worse than untidy on a site that has not yet run
`backfill_cash_ledger`. The backfill sweeps every Job Expense and posts
through `ledger.job_expense`, which posts anything the company paid - so
it will write **a real ledger entry for money that was never paid**. The
founder does not pay the vendor twice; the ledger would say they did.

Nothing is done about it here on purpose. Converting such a row means
folding its invoice number onto the expense it was covering, and **#11
never required that expense to exist** - the covering row *was* the
record. So a conversion has to guess which payment it answers for, and
on a small dataset a wrong guess looks like it worked. Deleting rows
from a company's money records on a guess is the owner's decision, not
a migration's.

dev.localhost had zero such rows out of eight expenses when #123 was
written, which is why nobody met this earlier. A site that ran #11 and
has not yet backfilled is carrying it.
"""

import frappe


def execute():
    if not frappe.db.has_column("Job Expense", "covers_cost_line"):
        return
    # Brings in cost_line, so there is somewhere to copy to.
    frappe.reload_doc("auraos", "doctype", "job_expense")
    if not frappe.db.has_column("Job Expense", "cost_line"):
        return
    frappe.db.sql(
        """
        UPDATE `tabJob Expense`
           SET cost_line = covers_cost_line
         WHERE IFNULL(covers_cost_line, '') != ''
           AND IFNULL(cost_line, '') = ''
        """
    )

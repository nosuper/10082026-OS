"""Give every invoice already issued the rate it was written at (#98).

A milestone invoiced before the app recorded a basis holds 0 in a column
that cannot be null - and 0% is a rate an export invoice is genuinely
written at, so left alone those rows would read as VAT-free rather than
as unknown.

The rate they were written at is their job's. It is frozen on a won job,
so it is the same number that produced the invoice request the accountant
worked from - this fills in what was already true rather than restating
anything. It is a patch and not a rule inside the save path on purpose:
back-filling an issued invoice is a deliberate, once, auditable act.
"""

import frappe


def execute():
    rows = frappe.get_all(
        "Job Payment Milestone",
        filters={
            "parenttype": "Job",
            "invoiced_on": ["is", "set"],
            "invoice_vat_pct": 0,
        },
        fields=["name", "parent"],
    )
    if not rows:
        return
    rates = {
        job.name: job.vat_pct
        for job in frappe.get_all(
            "Job",
            filters={"name": ["in", list({row.parent for row in rows})]},
            fields=["name", "vat_pct"],
        )
    }
    for row in rows:
        rate = rates.get(row.parent)
        if not rate:
            continue
        # update_modified=False: filling in the record of an invoice is
        # not somebody touching the money on that milestone today.
        frappe.db.set_value(
            "Job Payment Milestone",
            row.name,
            "invoice_vat_pct",
            rate,
            update_modified=False,
        )

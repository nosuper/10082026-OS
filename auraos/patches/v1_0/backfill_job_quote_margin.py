"""Give pre-T12 jobs the margin already implied by their frozen snapshot."""

import frappe

from auraos.lib.money import round_vnd


def execute():
    # Patches run before migrate's general DocType sync. Create the new
    # column first so an upgrade from pre-T12 can write the backfill.
    frappe.reload_doc("auraos", "doctype", "job")
    for job in frappe.get_all(
        "Job", fields=["name", "quote_subtotal", "quote_mf_amount"]
    ):
        cost_basis = frappe.db.get_value(
            "Deal Cost Line",
            {"parent": job.name, "parenttype": "Job"},
            "sum(cost_basis)",
        ) or 0
        margin = (job.quote_subtotal or 0) + (job.quote_mf_amount or 0) - cost_basis
        frappe.db.set_value(
            "Job", job.name, "quote_margin", round_vnd(margin), update_modified=False
        )

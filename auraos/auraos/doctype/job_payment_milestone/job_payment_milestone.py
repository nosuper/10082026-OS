"""Payment milestones on a job - the Frappe side (T10, issue #12).

The rules live in auraos.lib.milestones; this module is the adapter that
applies them to a Job document, reads the company's payment terms, and
answers the two questions the screens ask: what is overdue, and what do
I paste into Zalo for the accountant.

Money-in is deliberately *not* founder-only. A producer already sees the
job's quoted total (T7), runs the stages that make a payment due, and is
the one who knows a client has paid. Overhead, commission and CM remain
the founder's boundary; the client's own invoice is not.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from auraos.lib.milestones import (
    INVOICE_FIELDS,
    NOT_REQUESTED,
    STATUS_FLOW,
    allocated_pct,
    days_overdue,
    due_stamp,
    format_pct,
    invoice_request_text,
    is_overdue,
    milestone_amounts,
    stage_reached,
    stamps_for,
    vat_basis,
)
from auraos.settings import setting

# Days after a milestone falls due before it starts nudging. Overridable
# in AuraOS Settings; 0 turns the nudge off, the same switch the margin
# floor and the quote silence nudge use.
DEFAULT_PAYMENT_TERMS_DAYS = 7

# What a screen may edit on a milestone. Amounts and every timestamp are
# derived - the collection status moves through its own endpoint.
EDITABLE_FIELDS = ("title", "pct", "trigger_stage")


class JobPaymentMilestone(Document):
    pass


def payment_terms_days():
    """Days a due milestone may stay uncollected before it nudges."""
    return int(setting("payment_terms_days", DEFAULT_PAYMENT_TERMS_DAYS))


def replanned(current, planned):
    """One row of a saved plan: the stored row, re-planned.

    Carrying the whole stored row keeps its identity, its collection
    status and the stamps it has already earned; only the editable
    planning fields are taken from the caller. `idx` is dropped on
    purpose - the caller's order is the new order, and an idx carried
    from before a deletion would collide with a surviving row's.

    A row the caller invented has nothing stored to carry, so it starts
    from the planning fields alone.
    """
    values = current.as_dict() if current else {}
    values.pop("idx", None)
    values.update({field: planned.get(field) for field in EDITABLE_FIELDS})
    return values


def apply_to(job, stages):
    """Derive every milestone number on a job about to be saved.

    Amounts follow the quoted total, due dates follow the stage, and the
    collection timestamps follow the status - so a hand-typed amount, a
    stale due date or an invented "paid on" is overwritten rather than
    trusted. `stages` is passed in because the production flow belongs to
    the Job, not to its milestones.
    """
    rows = job.get("payment_milestones") or []
    if not rows:
        return

    validate_plan(rows, stages)
    now = frappe.utils.now_datetime()
    amounts = milestone_amounts(job.quote_total, [row.pct for row in rows])
    for row, amount in zip(rows, amounts):
        row.amount = amount
        row.due_on = due_stamp(
            reached=stage_reached(job.stage, row.trigger_stage, stages),
            due_on=row.due_on,
            status=row.status,
            now=now,
        )
        # job.vat_pct is only ever taken by a milestone being invoiced
        # for the first time; stamps_for keeps a rate already recorded.
        stamps = stamps_for(
            row.status or NOT_REQUESTED, row.as_dict(), now, vat_pct=job.vat_pct
        )
        for field, value in stamps.items():
            row.set(field, value)


def validate_plan(rows, stages):
    for row in rows:
        if row.status and row.status not in STATUS_FLOW:
            frappe.throw(
                _("{0} is not a collection status").format(row.status),
                frappe.ValidationError,
            )
        # A blank trigger stage never reaches here: Frappe fills an empty
        # Select with its first option. Which is why the API checks the
        # caller's own payload - see auraos.api.save_job_milestones.
        if row.trigger_stage not in stages:
            frappe.throw(
                _("{0} is not a production stage").format(row.trigger_stage),
                frappe.ValidationError,
            )
    # Billing the client more than they were quoted is an error, not a
    # judgement call. Billing less is a half-finished plan, which is
    # allowed: milestones get filled in over the life of a job.
    allocated = allocated_pct([row.pct for row in rows])
    if allocated > 100:
        frappe.throw(
            _(
                "Payment milestones bill {0} of the quote - more than the "
                "client agreed to"
            ).format(format_pct(allocated)),
            frappe.ValidationError,
        )


# What a milestone row carries onto a screen. The lateness verdict is
# added by milestone_view, never stored.
VIEW_FIELDS = (
    "name",
    "idx",
    "title",
    "pct",
    "trigger_stage",
    "amount",
    "status",
    "due_on",
    "requested_on",
    "invoiced_on",
    "paid_on",
    # The invoice, on the row it bills: its number and the rate it was
    # written on, so the screen reads the basis instead of assuming one.
    *INVOICE_FIELDS,
)


def milestone_view(row, terms_days=None, now=None):
    """One milestone as every screen reads it, lateness already decided.

    One builder for the job page and the board: the two surfaces showed
    different fields when they each built their own row, and the job page
    rendered a blank number where the days late should be.
    """
    if terms_days is None:
        terms_days = payment_terms_days()
    now = now or frappe.utils.now_datetime()
    due_on = frappe.utils.get_datetime(row.due_on) if row.due_on else None
    return {
        **{field: row.get(field) for field in VIEW_FIELDS},
        # There is an invoice exactly when there is an issue date. A
        # stored rate of 0 on a milestone nobody invoiced would read as
        # a VAT-free invoice, and an empty Data column would make the
        # screen test for two kinds of nothing.
        "invoice_no": (row.get("invoice_no") or None) if row.get("invoiced_on") else None,
        "invoice_vat_pct": row.get("invoice_vat_pct") if row.get("invoiced_on") else None,
        "overdue": is_overdue(
            status=row.status, due_on=due_on, now=now, terms_days=terms_days
        ),
        "days_overdue": days_overdue(due_on=due_on, now=now, terms_days=terms_days),
    }


def overdue():
    """Every milestone chasing the founder, oldest debt first.

    Reads child rows directly (get_all skips row-level permissions), so
    the query is scoped to the jobs this session may actually list - the
    same shape as the deal board's tag map.
    """
    permitted = frappe.get_list("Job", pluck="name", limit_page_length=0)
    if not permitted:
        return []
    terms = payment_terms_days()
    now = frappe.utils.now_datetime()
    rows = frappe.get_all(
        "Job Payment Milestone",
        filters={
            "parenttype": "Job",
            "parent": ["in", permitted],
            "status": ["!=", "Paid"],
            "due_on": ["is", "set"],
        },
        fields=[*VIEW_FIELDS, "parent"],
        order_by="due_on asc",
    )
    overdue_rows = [
        row
        for row in rows
        if is_overdue(
            status=row.status,
            due_on=frappe.utils.get_datetime(row.due_on),
            now=now,
            terms_days=terms,
        )
    ]
    if not overdue_rows:
        return []
    jobs = {
        job.name: job
        for job in frappe.get_all(
            "Job",
            filters={"name": ["in", list({row.parent for row in overdue_rows})]},
            fields=["name", "title", "company"],
        )
    }
    return [
        {
            **milestone_view(row, terms, now),
            "job": row.parent,
            "job_title": jobs.get(row.parent, {}).get("title"),
            "company": jobs.get(row.parent, {}).get("company"),
        }
        for row in overdue_rows
    ]


def find(job, milestone):
    """One milestone row of a job, or a loud 404."""
    for row in job.payment_milestones:
        if row.name == milestone:
            return row
    frappe.throw(
        _("Milestone {0} is not on job {1}").format(milestone, job.name),
        frappe.DoesNotExistError,
    )


def request_text(job, row):
    """The Zalo message asking the accountant for this milestone's invoice.

    The client's tax details are read off the Party Company the job
    carries - the record that exists precisely so tax codes stop living
    in chat threads (spec #2, story 1).
    """
    client = (
        frappe.db.get_value(
            "Party Company",
            job.company,
            ["company_name", "tax_code", "address"],
            as_dict=True,
        )
        or {}
    )
    return invoice_request_text(
        client=client,
        milestone={"title": row.title, "pct": row.pct, "amount": row.amount},
        job_title=job.title,
        vat_pct=invoice_vat_pct(job, row),
    )


def invoice_vat_pct(job, row):
    """The rate this milestone's invoice is read at.

    Its own, once it has one. Asking for the text again a quarter after
    the company moved to 10% must reproduce the 8% invoice the client
    holds, not a second version of it.
    """
    return vat_basis(row.get("invoiced_on"), row.get("invoice_vat_pct"), job.vat_pct)

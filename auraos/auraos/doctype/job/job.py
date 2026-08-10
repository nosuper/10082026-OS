"""The Job — a won deal in production (T7, issue #9).

The job reuses the deal's child tables wherever the shape is genuinely
the same (Deal Cost Line, Deal Package, Deal Link, Deal Stage Log): a
job's carried breakdown *is* the deal's breakdown, and a stage log is a
stage log. Job-shaped tables under new names would buy nothing but
migrations.

The carried numbers are a snapshot of what was won: nothing on the job
recomputes them, and the deal stays the one place pricing is edited.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from auraos.auraos.doctype.deal.deal import (
    append_stage_change,
    holds_operating_role,
)

# The agreed production flow (spec #2, story 27), in board order.
STAGES = [
    "Pre-production",
    "Shoot",
    "Post",
    "Feedback",
    "Delivery",
    "Nghiệm thu",
    "Chờ thanh toán",
    "Done",
]

# Revision rounds the client gets included; the next one is a chargeable
# change order (spec #2, story 28).
INCLUDED_REVISION_ROUNDS = 2

# Where a revision request puts the job: the client has asked for
# changes, so the work reopens where changes are made (issue #9, raised
# at the T6 walkthrough).
REDO_STAGE = "Post"


def redo_stage_for(stage):
    """The stage a job lands in when a revision is logged against it.

    A revision is only a *redo* once the client has been shown a cut —
    at Feedback and beyond. Before that the job is already where the
    work happens, so its stage is left alone rather than shoved
    sideways by a note.
    """
    if stage not in STAGES:
        return stage
    if STAGES.index(stage) > STAGES.index(REDO_STAGE):
        return REDO_STAGE
    return stage


# Fields carried from the deal that the job stores verbatim.
CARRIED_FIELDS = (
    "title",
    "company",
    "contact",
    "quote_mf_pct",
    "vat_pct",
    "quote_subtotal",
    "quote_mf_amount",
    "quote_vat_amount",
    "quote_total",
)


def carried_rows(rows):
    """Child rows as plain dicts, ready to append to another parent.

    Copies every data field the row's own doctype declares, so a field
    added to the breakdown later travels to the job without anyone
    remembering to update a list here.
    """
    return [
        {
            field.fieldname: row.get(field.fieldname)
            for field in row.meta.fields
            if field.fieldtype not in frappe.model.no_value_fields
        }
        for row in rows
    ]


def create_from_deal(deal_name):
    """Convert a won deal into a job, carrying everything it holds.

    Callers are responsible for the permission check on the deal; the
    insert itself enforces create permission on Job.
    """
    deal = frappe.get_doc("Deal", deal_name)
    if deal.stage != "Won":
        frappe.throw(
            _("Only a won deal becomes a job — {0} is at {1}").format(
                deal.name, deal.stage
            ),
            frappe.ValidationError,
        )
    # The friendly refusal; the unique index on Job.deal is what actually
    # stops two conversions racing each other into two jobs.
    existing = frappe.db.exists("Job", {"deal": deal.name})
    if existing:
        frappe.throw(
            _("{0} already became job {1}").format(deal.name, existing),
            frappe.ValidationError,
        )

    job = frappe.get_doc(
        {
            "doctype": "Job",
            "deal": deal.name,
            "job_owner": deal.deal_owner,
            "cost_lines": carried_rows(deal.cost_lines),
            "packages": carried_rows(deal.packages),
            "job_links": carried_rows(deal.deal_links),
            **{field: deal.get(field) for field in CARRIED_FIELDS},
        }
    )
    job.insert()
    job.carry_commission(deal)
    return job


class Job(Document):
    def before_validate(self):
        # A job created by an operating user belongs to them; conversion
        # overrides this with the deal's owner.
        if not self.job_owner and holds_operating_role(frappe.session.user):
            self.job_owner = frappe.session.user

    def validate(self):
        self.validate_owner()
        self.number_revisions()

    def validate_owner(self):
        if self.job_owner and not holds_operating_role(self.job_owner):
            frappe.throw(
                _("Job owner must hold the Founder or Producer role"),
                frappe.ValidationError,
            )

    def number_revisions(self):
        """Round numbers and the chargeable flag are derived, never input.

        Row order is the round order, so deleting a mistaken row
        renumbers the rest instead of leaving a hole — and no client can
        be charged because of a hand-edited counter.
        """
        for index, row in enumerate(self.revisions, start=1):
            row.round = index
            row.chargeable = 1 if index > INCLUDED_REVISION_ROUNDS else 0
        self.revision_rounds = len(self.revisions)
        self.change_order_due = (
            1 if self.revision_rounds > INCLUDED_REVISION_ROUNDS else 0
        )

    def before_save(self):
        # After validation, so a rejected transition is never logged.
        append_stage_change(self)

    def log_revision(self, note):
        """Record a revision round and reopen the work it asks for.

        One call, because the two halves are one event: a client asking
        for changes both counts against the included rounds *and* sends
        the job back to the edit. The move is an ordinary stage change —
        logged in the history, and free to be overridden by dragging the
        card somewhere else.
        """
        self.append(
            "revisions",
            {
                "note": note,
                "requested_on": frappe.utils.now_datetime(),
                "logged_by": frappe.session.user,
            },
        )
        self.stage = redo_stage_for(self.stage)
        self.save()
        return self.revisions[-1]

    def carry_commission(self, deal):
        """Copy the deal's commission rate onto the job after the insert.

        Frappe strips permlevel-1 fields from anything a producer session
        writes, so a producer's conversion would otherwise reset the rate
        to the field default. db_set writes regardless of field-level
        permissions; reads stay founder-only via permlevel 1 — the same
        move Deal.store_founder_chain makes, for the same reason.
        """
        self.db_set("commission_pct", deal.commission_pct, update_modified=False)

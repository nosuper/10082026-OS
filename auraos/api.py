"""Whitelisted HTTP endpoints for the frappe-ui SPA."""

import frappe
from frappe import _

from auraos.auraos.doctype.deal.deal import (
    OPERATING_ROLES,
    floor_breached,
    margin_floor_pct,
    quote_margin_fraction,
    rate,
    to_engine_lines,
)
from auraos.auraos.doctype.job.job import create_from_deal
from auraos.lib import pricing
from auraos.lib.money import round_vnd

# The company's standing commission practice (spec #2, story 14); the
# Deal field carries the same default.
DEFAULT_COMMISSION_PCT = 5


@frappe.whitelist()
def operating_users():
    """Users who may own a deal — the founder ↔ producer handover list.

    The SPA's owner dropdown needs this because Producer sessions
    cannot list the User doctype directly.
    """
    frappe.has_permission("Deal", "read", throw=True)
    holders = frappe.get_all(
        "Has Role",
        filters={
            "role": ["in", list(OPERATING_ROLES)],
            "parenttype": "User",
        },
        pluck="parent",
    )
    return frappe.get_all(
        "User",
        filters={"name": ["in", holders], "enabled": 1},
        fields=["name", "full_name"],
        order_by="full_name asc",
    )


def _check_deal_permission(deal, ptype):
    """Gate a collaboration endpoint on the underlying Deal.

    Comment and File rows are read with frappe.get_all (which skips
    row-level permissions), so this explicit doc-level check is the
    entire authorization for those reads.
    """
    if not frappe.db.exists("Deal", deal):
        frappe.throw(_("Deal {0} not found").format(deal), frappe.DoesNotExistError)
    frappe.has_permission("Deal", ptype, doc=deal, throw=True)


def _check_job_permission(job, ptype):
    """Gate a job endpoint on the job itself — missing means missing.

    Without the existence check a bad name reads as a permission
    failure, which tells the caller the wrong thing.
    """
    if not frappe.db.exists("Job", job):
        frappe.throw(_("Job {0} not found").format(job), frappe.DoesNotExistError)
    frappe.has_permission("Job", ptype, doc=job, throw=True)


COMMENT_FIELDS = ["name", "content", "comment_email", "comment_by", "creation"]


@frappe.whitelist()
def deal_comments(deal):
    """Comment thread of a deal, oldest first."""
    _check_deal_permission(deal, "read")
    return frappe.get_all(
        "Comment",
        filters={
            "comment_type": "Comment",
            "reference_doctype": "Deal",
            "reference_name": deal,
        },
        fields=COMMENT_FIELDS,
        order_by="creation asc",
    )


@frappe.whitelist()
def add_deal_comment(deal, content):
    """Append a comment to a deal's thread; returns the stored row."""
    _check_deal_permission(deal, "write")
    if not (content or "").strip():
        frappe.throw(_("Comment cannot be empty"), frappe.ValidationError)
    comment = frappe.get_doc("Deal", deal).add_comment("Comment", text=content)
    return {field: comment.get(field) for field in COMMENT_FIELDS}


@frappe.whitelist()
def deal_attachments(deal):
    """Files attached to a deal, newest first."""
    _check_deal_permission(deal, "read")
    return frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Deal", "attached_to_name": deal},
        fields=["name", "file_name", "file_url", "file_size", "owner", "creation"],
        order_by="creation desc",
    )


@frappe.whitelist()
def deal_tags_map():
    """Tags per deal, for the table view — {deal_name: [tag, ...]}.

    Child rows can't be fetched through the list API alongside their
    parents, so the table view asks for the whole (small) mapping.
    """
    frappe.has_permission("Deal", "read", throw=True)
    # get_all skips row-level permissions, so scope the child rows to
    # the deals this user may actually list.
    permitted = frappe.get_list("Deal", pluck="name", limit_page_length=0)
    tags = frappe.get_all(
        "Deal Tag Item",
        filters={"parenttype": "Deal", "parent": ["in", permitted]},
        fields=["parent", "deal_tag"],
        order_by="parent asc, idx asc",
    )
    tag_map = {}
    for row in tags:
        tag_map.setdefault(row.parent, []).append(row.deal_tag)
    return tag_map


def _is_founder():
    return "Founder" in frappe.get_roles()


def _founder_block(result, commission_pct):
    """The profit chain, assembled only for Founder sessions.

    The same numbers are persisted on the deal as permlevel-1 fields
    (Deal.store_founder_chain) for dashboards; this block exists for
    live editing, where nothing is saved yet.
    """
    return {
        "commission_pct": float(commission_pct),
        "total_commission": round_vnd(result.total_commission),
        "cm": round_vnd(
            result.revenue_ex_vat
            - result.total_profit_cost_basis
            - result.total_commission
        ),
        "profit_before_tax": round_vnd(result.profit_before_tax),
        "tndn": round_vnd(result.tndn),
        "net_profit": round_vnd(result.net_profit),
        "total_input_vat": round_vnd(result.total_input_vat),
        "vat_payable": round_vnd(result.vat_payable),
        "margin_floor_pct": float(margin_floor_pct()),
    }


@frappe.whitelist()
def compute_breakdown(lines, quote_mf_pct=10, vat_pct=8, commission_pct=None, packages=None):
    """Live engine results for the breakdown editor, before anything is saved.

    Producer sessions get costs, quote prices, margin and the floor
    warning; the commission/profit block is appended only for Founder
    sessions, and a producer-supplied commission_pct is ignored.
    """
    frappe.has_permission("Deal", "read", throw=True)
    line_rows = frappe.parse_json(lines) or []
    package_rows = frappe.parse_json(packages) if packages else []

    if not _is_founder() or commission_pct is None:
        commission_pct = DEFAULT_COMMISSION_PCT

    params = pricing.DealParams(
        quote_mf_rate=rate(quote_mf_pct),
        vat_rate=rate(vat_pct),
        commission_rate=rate(commission_pct),
    )
    result = pricing.compute_quote(to_engine_lines(line_rows), params)

    budgets = {}
    for row, line in zip(line_rows, result.lines):
        if row.get("package"):
            budgets.setdefault(row["package"], []).append(line.budget)

    pct = quote_margin_fraction(result)
    out = {
        "lines": [
            {
                "subtotal": round_vnd(line.subtotal_int_net),
                "cost_basis": round_vnd(line.profit_cost_basis),
                "input_vat": round_vnd(line.input_vat),
                "quote_price": round_vnd(line.budget),
                "margin": round_vnd(line.margin),
            }
            for line in result.lines
        ],
        "packages": [
            {
                "title": row.get("title"),
                **_package_dict(
                    budgets.get(row.get("title"), []),
                    row.get("price_override") or None,
                ),
            }
            for row in package_rows
        ],
        "subtotal": round_vnd(result.subtotal),
        "management_fee": round_vnd(result.management_fee),
        "vat": round_vnd(result.vat),
        "total": round_vnd(result.total),
        "margin": round_vnd(result.revenue_ex_vat - result.total_profit_cost_basis),
        "margin_pct": float(pct * 100) if pct is not None else None,
        "floor_breached": bool(result.lines) and floor_breached(result),
    }
    if _is_founder():
        out["founder"] = _founder_block(result, commission_pct)
    return out


def _package_dict(member_budgets, override):
    priced = pricing.package_price(member_budgets, override)
    return {
        "default_price": round_vnd(priced.default),
        "price": round_vnd(priced.price),
        "variance": round_vnd(priced.variance),
        "overridden": priced.overridden,
    }


@frappe.whitelist()
def deal_profit(deal):
    """The founder-only profit chain for a saved deal, computed on demand.

    A producer can hold the Deal document in full and still see nothing
    of commission, CM, or the profit block — the stored copies sit at
    permlevel 1 and this endpoint refuses non-founders outright.
    """
    if not _is_founder():
        frappe.throw(_("Only the Founder may see the profit chain"), frappe.PermissionError)
    doc = frappe.get_doc("Deal", deal)
    doc.check_permission("read")

    params = pricing.DealParams(
        quote_mf_rate=rate(doc.quote_mf_pct),
        vat_rate=rate(doc.vat_pct),
        commission_rate=rate(doc.commission_pct),
    )
    result = pricing.compute_quote(to_engine_lines(doc.cost_lines), params)
    return _founder_block(result, doc.commission_pct or 0)


@frappe.whitelist()
def create_job_from_deal(deal):
    """Turn a won deal into a job, carrying breakdown, packages and links."""
    _check_deal_permission(deal, "read")
    job = create_from_deal(deal)
    return {"name": job.name, "title": job.title, "stage": job.stage}


@frappe.whitelist()
def jobs_by_deal():
    """{deal_name: job_name} for the jobs this user may list.

    The board uses it to tell a won deal that still needs converting
    from one that already has a job.
    """
    frappe.has_permission("Job", "read", throw=True)
    rows = frappe.get_list(
        "Job",
        filters={"deal": ["is", "set"]},
        fields=["name", "deal"],
        limit_page_length=0,
    )
    return {row.deal: row.name for row in rows}


@frappe.whitelist()
def log_job_revision(job, note):
    """Record a client revision round on a job.

    The round number and the chargeable flag come back computed — the
    job derives both from row order (Job.number_revisions).
    """
    _check_job_permission(job, "write")
    if not (note or "").strip():
        frappe.throw(_("A revision needs a note"), frappe.ValidationError)
    doc = frappe.get_doc("Job", job)
    doc.append(
        "revisions",
        {
            "note": note,
            "requested_on": frappe.utils.now_datetime(),
            "logged_by": frappe.session.user,
        },
    )
    doc.save()
    latest = doc.revisions[-1]
    return {
        "name": doc.name,
        "revision_rounds": doc.revision_rounds,
        "change_order_due": bool(doc.change_order_due),
        "round": latest.round,
        "chargeable": bool(latest.chargeable),
    }


@frappe.whitelist()
def get_margin_floor():
    frappe.has_permission("AuraOS Settings", "read", throw=True)
    return float(margin_floor_pct())


@frappe.whitelist()
def set_margin_floor(pct):
    frappe.has_permission("AuraOS Settings", "write", throw=True)
    settings = frappe.get_doc("AuraOS Settings")
    settings.margin_floor_pct = float(pct or 0)
    settings.save()
    return float(settings.margin_floor_pct)

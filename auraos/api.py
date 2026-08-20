"""Whitelisted HTTP endpoints for the frappe-ui SPA."""

import frappe
from frappe import _
from frappe.utils.pdf import get_pdf

from auraos.auraos.doctype.deal.deal import (
    OPERATING_ROLES,
    margin_floor_pct,
)
from auraos.auraos.doctype.deal_quote import deal_quote
from auraos.auraos.doctype.job.job import STAGES as JOB_STAGES
from auraos.auraos.doctype.job.job import CLOSED_STAGE as JOB_CLOSED_STAGE
from auraos.auraos.doctype.job.job import create_from_deal
from auraos.auraos.doctype.job_payment_milestone import job_payment_milestone
from auraos.auraos.doctype.paperwork_template import paperwork_template
from auraos.lib import breakdown, contracts, exposure, finance, library, paper_status, paperwork, settlement
from auraos.lib import reporting
# Imported by name: `milestones` is a parameter of save_job_milestones.
from auraos.lib.milestones import INVOICED as MILESTONE_INVOICED
from auraos.lib.milestones import PAID as MILESTONE_PAID
from auraos.lib.milestones import invoice_split
from auraos.lib.money import round_vnd, to_decimal
# Imported by name: `quote` is a parameter throughout this module.
from auraos.lib.quote import COMPANY_FIELDS

# The company's standing commission practice (spec #2, story 14); the
# Deal field carries the same default.
DEFAULT_COMMISSION_PCT = 5

# Pricing ignores line metadata, but the live endpoint returns these
# approved fields alongside the computed values so editing never drops them.
LINE_METADATA_FIELDS = (
    "item_category",
    "cost_phase",
    "source_type",
    "source_contact",
)

# The table is deliberately a narrow editing surface. Quote delivery,
# breakdown values and audit fields still belong to their dedicated flows.
DEAL_TABLE_EDITABLE_FIELDS = {
    "title",
    "company",
    "stage",
    "deal_owner",
    "estimated_budget",
    "source",
    "project_type",
    "deal_tags",
}
DEAL_TABLE_FIELDS = [
    "name",
    "title",
    "company",
    "stage",
    "deal_owner",
    "estimated_budget",
    "source",
    "project_type",
    "quote_status",
    "quote_sent_on",
    "modified",
]


def _terms(terms):
    """The generation dialog's typed values, as a plain mapping.

    Frappe hands a whitelisted method its arguments as strings when the
    call arrives as form data, so a dict may land here as JSON text.
    Parsed in one place rather than trusted, and an unreadable value
    becomes no terms at all rather than a crash on a contract nobody
    can print.
    """
    if not terms:
        return {}
    if isinstance(terms, str):
        try:
            terms = frappe.parse_json(terms)
        except Exception:
            return {}
    return terms if isinstance(terms, dict) else {}


def _parent_contract_number(job):
    """The number of this job's contract, for a paper written about it.

    The most recent HDDV generated for the job. "Most recent" rather
    than "the one", because a contract can be regenerated - a typo
    fixed, a clause corrected - and the number the later paper should
    quote is the one on the copy that was actually signed.
    """
    rows = frappe.get_all(
        "Generated Paper",
        filters={"job": job, "contract_number": ["is", "set"]},
        fields=["contract_number", "creation"],
        order_by="creation desc",
    )
    for row in rows:
        if row.contract_number:
            return row.contract_number
    return None


@frappe.whitelist()
def propose_contract_number(job, template, signed_on):
    """What this paper would be numbered, before anyone commits to it.

    Offered to the generation dialog so the founder sees the number and
    can correct it before it is printed. Nothing is written here - the
    number is only fixed when the paper is generated.

    Two absences are reported rather than papered over, because both
    have a person as the fix and neither has a sensible default:
    a client with no short code, and a child paper whose contract has
    not been generated yet.
    """
    _check_job_permission(job, "read")
    frappe.has_permission("Paperwork Template", "read", throw=True)

    kind = frappe.db.get_value("Paperwork Template", template, "kind") or ""
    if not kind:
        return {"kind": "", "number": None, "needs": None}

    company = frappe.db.get_value("Job", job, "company")
    short_code = frappe.db.get_value("Party Company", company, "short_code") or ""

    if kind in contracts.CHILD_KINDS:
        parent = _parent_contract_number(job)
        return {
            "kind": kind,
            "number": parent,
            "needs": None if parent else "contract",
        }

    if not short_code:
        return {"kind": kind, "number": None, "needs": "short_code"}

    return {
        "kind": kind,
        "number": contracts.number_for(
            kind,
            frappe.utils.getdate(signed_on),
            short_code,
            taken=_numbers_taken(kind, frappe.utils.getdate(signed_on), short_code),
        ),
        "needs": None,
    }


def _numbers_taken(kind, signed_on, short_code):
    """Numbers already issued that this one could collide with.

    Read across every job rather than this one: two contracts with the
    same partner on the same day collide whatever job they belong to,
    and the number is the company's, not the job's.
    """
    stem = f"{kind.upper()}{signed_on.strftime('%d%m%y')}/AURA-"
    rows = frappe.get_all(
        "Generated Paper",
        filters={"contract_number": ["like", f"{stem}%"]},
        pluck="contract_number",
    )
    return [row for row in rows if row]


@frappe.whitelist()
def suggest_short_code(company_name):
    """The partner abbreviation proposed for a company name (#139).

    Asked of the server rather than worked out in the browser, so the
    rule that builds a contract number has one home. A second copy in
    TypeScript would agree with this one until somebody changed one of
    them, which is the defect the date rule and the fixture-name mirror
    both exist to avoid.

    A suggestion only. The field it fills is editable and may be left
    blank; generation asks for a code when it is missing rather than
    inventing one.
    """
    frappe.has_permission("Party Company", "read", throw=True)
    return contracts.suggest_short_code(company_name or "")


@frappe.whitelist()
def operating_users():
    """Users who may own a deal - the founder ↔ producer handover list.

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


def _deal_table_values(values):
    values = frappe.parse_json(values) or {}
    if not isinstance(values, dict):
        frappe.throw(_("Deal table values must be an object"), frappe.ValidationError)
    values = dict(values)
    unknown = set(values) - DEAL_TABLE_EDITABLE_FIELDS
    if unknown:
        frappe.throw(
            _("Fields cannot be edited in the deals table: {0}").format(
                ", ".join(sorted(unknown))
            ),
            frappe.ValidationError,
        )
    return values


def _apply_deal_table_values(doc, values):
    values = _deal_table_values(values)
    tags = values.pop("deal_tags", None)
    doc.update(values)
    if tags is not None:
        doc.set(
            "deal_tags",
            [
                {"deal_tag": tag if isinstance(tag, str) else tag.get("deal_tag")}
                for tag in tags
            ],
        )


def _deal_table_row(doc):
    row = {field: doc.get(field) for field in DEAL_TABLE_FIELDS}
    row["tags"] = [tag.deal_tag for tag in doc.deal_tags]
    return row


@frappe.whitelist()
def update_deal_table_row(deal, values):
    """Save editable table cells through the full Deal validation path."""
    doc = frappe.get_doc("Deal", deal)
    doc.check_permission("write")
    _apply_deal_table_values(doc, values)
    doc.save()
    return _deal_table_row(doc)


@frappe.whitelist()
def create_deal_table_row(values):
    """Create a Deal from the blank table row through normal defaults."""
    frappe.has_permission("Deal", "create", throw=True)
    doc = frappe.new_doc("Deal")
    _apply_deal_table_values(doc, values)
    doc.insert()
    return _deal_table_row(doc)


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
    """Gate a job endpoint on the job itself - missing means missing.

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
    """Tags per deal, for the table view - {deal_name: [tag, ...]}.

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


@frappe.whitelist()
def deal_stage_entries():
    """When each deal entered its current stage - {deal_name: datetime}.

    Serves the board's staleness badge: the founder's weekly ritual is
    "which deal has sat still in a stage for over a week?", and the
    board should answer it at a glance. Insertion logs a stage_history
    row too, so every deal has at least one; the last row per deal is
    the move into its current stage.
    """
    frappe.has_permission("Deal", "read", throw=True)
    # get_all skips row-level permissions, so scope the child rows to
    # the deals this user may actually list.
    permitted = frappe.get_list("Deal", pluck="name", limit_page_length=0)
    rows = frappe.get_all(
        "Deal Stage Log",
        filters={"parenttype": "Deal", "parent": ["in", permitted]},
        fields=["parent", "changed_on"],
        order_by="parent asc, idx asc",
    )
    entered = {}
    for row in rows:
        entered[row.parent] = row.changed_on
    return entered


def _is_founder():
    return "Founder" in frappe.get_roles()


def _founder_view(view, commission_pct):
    """The founder block as the SPA reads it: the lib's pure numbers
    plus the two dials only an adapter can know."""
    return {
        "commission_pct": float(commission_pct),
        **view["founder"],
        "margin_floor_pct": float(margin_floor_pct()),
    }


def _breakdown_view(line_rows, package_rows, quote_mf_pct, vat_pct, commission_pct):
    """lib/breakdown with this module's error channel and stored floor."""
    try:
        return breakdown.breakdown_view(
            line_rows,
            package_rows,
            quote_mf_pct=quote_mf_pct,
            vat_pct=vat_pct,
            commission_pct=commission_pct,
            margin_floor_pct=margin_floor_pct(),
        )
    except ValueError as err:
        frappe.throw(_(str(err)), frappe.ValidationError)


@frappe.whitelist()
def compute_breakdown(lines, quote_mf_pct=10, vat_pct=8, commission_pct=None, packages=None):
    """Live engine results for the breakdown editor, before anything is saved.

    Producer sessions get costs, quote prices, margin and the floor
    warning; the commission/profit block is appended only for Founder
    sessions, and a producer-supplied commission_pct is ignored. One
    assembly - lib/breakdown - shared with the persisted Deal fields,
    so the live editor and a saved deal cannot drift apart.
    """
    frappe.has_permission("Deal", "read", throw=True)
    line_rows = frappe.parse_json(lines) or []
    package_rows = frappe.parse_json(packages) if packages else []

    if not _is_founder() or commission_pct is None:
        commission_pct = DEFAULT_COMMISSION_PCT

    view = _breakdown_view(
        line_rows, package_rows, quote_mf_pct, vat_pct, commission_pct
    )
    out = {
        **view,
        # Pricing ignores line metadata; return it alongside the
        # computed values so editing never drops it.
        "lines": [
            {
                **{field: row.get(field) for field in LINE_METADATA_FIELDS},
                **line_view,
            }
            for row, line_view in zip(line_rows, view["lines"])
        ],
    }
    del out["founder"]
    if _is_founder():
        out["founder"] = _founder_view(view, commission_pct)
    return out


@frappe.whitelist()
def deal_profit(deal):
    """The founder-only profit chain for a saved deal, computed on demand.

    A producer can hold the Deal document in full and still see nothing
    of commission, CM, or the profit block - the stored copies sit at
    permlevel 1 and this endpoint refuses non-founders outright.
    """
    if not _is_founder():
        frappe.throw(_("Only the Founder may see the profit chain"), frappe.PermissionError)
    doc = frappe.get_doc("Deal", deal)
    doc.check_permission("read")
    return _founder_view(doc.breakdown_view(), doc.commission_pct or 0)


# -- quote delivery (T6, issue #8) --


def _quote_dict(quote, tracking=None):
    """A quote version as the producer's screen needs it.

    The client's view is a different, narrower projection - see
    auraos.lib.quote.client_view.
    """
    tracking = tracking or {}
    return {
        "name": quote.name,
        "version": quote.version,
        "status": quote.status,
        "total": quote.total,
        "published_on": quote.published_on,
        "sent_on": quote.sent_on,
        "confirmed_on": quote.confirmed_on,
        "url": deal_quote.page_url(quote.token),
        "pdf_url": deal_quote.pdf_url(quote.token),
        # Page opens and PDF downloads are counted apart: the page's own
        # download button would otherwise score one visit as two opens.
        "opens": tracking.get("Page", 0),
        "downloads": tracking.get("PDF", 0),
        "last_open": tracking.get("last_open"),
    }


@frappe.whitelist()
def publish_quote(deal, notes=None):
    """Freeze the deal's packages and totals as the next quote version."""
    quote = deal_quote.publish(deal, notes)
    return _quote_dict(quote)


@frappe.whitelist()
def deal_quotes(deal):
    """Every published version of a deal, newest first, with open counts."""
    _check_deal_permission(deal, "read")
    quotes = frappe.get_all(
        "Deal Quote",
        filters={"deal": deal},
        fields=[
            "name", "version", "status", "total", "token",
            "published_on", "sent_on", "confirmed_on",
        ],
        order_by="version desc",
    )
    tracking = _quote_tracking([row.name for row in quotes])
    return [_quote_dict(quote, tracking.get(quote.name)) for quote in quotes]


def _quote_tracking(names):
    """Opens and downloads per quote, counted in the database.

    Grouped rather than fetched row by row: the open log is the one
    table that grows without bound, and the cross-deal list asks about
    every version at once. The fold itself is lib/reporting's, so the
    two lists cannot count the same events differently.
    """
    if not names:
        return {}
    return reporting.open_tracking(
        frappe.get_all(
            "Deal Quote Open",
            filters={"quote": ["in", list(names)]},
            fields=[
                "quote",
                "via",
                "count(name) as events",
                "max(opened_on) as last_open",
            ],
            group_by="quote, via",
        )
    )


@frappe.whitelist()
def deal_quote_links():
    """Current quote link per deal, for the board - {deal: {...}}.

    The board asks for the whole (small) mapping in one call, the way it
    already does for tags: a card wants the link to hand out, and the
    list API cannot build a URL from a token it never fetches.
    """
    frappe.has_permission("Deal", "read", throw=True)
    permitted = frappe.get_list("Deal", pluck="name", limit_page_length=0)
    links = {}
    for row in frappe.get_all(
        "Deal Quote",
        filters={"deal": ["in", permitted]},
        fields=["deal", "name", "version", "status", "token"],
        order_by="version asc",
    ):
        # Ascending order, so the last write per deal is the newest.
        links[row.deal] = {
            "version": row.version,
            "status": row.status,
            "url": deal_quote.page_url(row.token),
        }
    return links


QUOTATION_LIST_FIELDS = [
    "name",
    "deal",
    "version",
    "status",
    "total",
    "token",
    "published_on",
    "sent_on",
    "confirmed_on",
]


def _company_names(companies):
    """Display names for a set of Party Company links.

    Screens list clients by name; the records link by code. One query
    for the whole page rather than one per row.
    """
    companies = {company for company in companies if company}
    if not companies:
        return {}
    return {
        row.name: row.company_name
        for row in frappe.get_all(
            "Party Company",
            filters={"name": ["in", list(companies)]},
            fields=["name", "company_name"],
        )
    }


@frappe.whitelist()
def quotation_list(status=None, search=None):
    """Every quote version across every deal, newest first.

    A deal has always been able to list its own versions
    (`deal_quotes`); this is the same rows without a deal in front of
    them, because "what is out with clients right now" cannot be
    assembled one deal at a time.

    Scoped to the deals this session may list, the way the board's
    mappings are: Deal Quote rows are read with get_all, which skips
    row-level permissions, so the scope is the entire authorization.

    Open tracking comes back as counts and a timestamp, never as prose -
    the screen decides whether that reads "3 opens, last 17 Aug" or
    "not opened yet".
    """
    frappe.has_permission("Deal", "read", throw=True)
    deals = {
        row.name: row
        for row in frappe.get_list(
            "Deal", fields=["name", "title", "company"], limit_page_length=0
        )
    }
    if not deals:
        return []

    filters = {"deal": ["in", list(deals)]}
    if status:
        filters["status"] = status
    quotes = frappe.get_all(
        "Deal Quote",
        filters=filters,
        fields=QUOTATION_LIST_FIELDS,
        # Newest first is publish order, not version order: two deals'
        # v1s are not the same age.
        order_by="published_on desc, version desc",
    )
    tracking = _quote_tracking([row.name for row in quotes])
    clients = _company_names(deal.company for deal in deals.values())
    rows = [
        reporting.quotation_row(
            quote,
            deal_title=deals[quote.deal].title,
            company=deals[quote.deal].company,
            client=clients.get(deals[quote.deal].company),
            url=deal_quote.page_url(quote.token),
            tracking=tracking.get(quote.name),
        )
        for quote in quotes
    ]
    # Searched after the rows are built, not in SQL: the client's name
    # lives on a third document, and the founder types whichever of the
    # two they remember.
    return [row for row in rows if reporting.matches_search(row, search)]


@frappe.whitelist()
def quote_opens(quote):
    """Open events of one version, newest first (spec #2, story 22)."""
    deal = frappe.db.get_value("Deal Quote", quote, "deal")
    if not deal:
        frappe.throw(_("Quote {0} not found").format(quote), frappe.DoesNotExistError)
    _check_deal_permission(deal, "read")
    return frappe.get_all(
        "Deal Quote Open",
        filters={"quote": quote},
        fields=["opened_on", "via", "ip_address"],
        order_by="opened_on desc",
        # Follow-up timing is decided by the recent opens; the rest is
        # history nobody scrolls to.
        limit=50,
    )


def _quote_for_write(name):
    quote = frappe.get_doc("Deal Quote", name)
    _check_deal_permission(quote.deal, "write")
    return quote


@frappe.whitelist()
def mark_quote_sent(quote):
    doc = _quote_for_write(quote)
    doc.mark_sent()
    return _quote_dict(doc)


@frappe.whitelist()
def mark_quote_confirmed(quote):
    doc = _quote_for_write(quote)
    doc.mark_confirmed()
    return _quote_dict(doc)


@frappe.whitelist()
def silent_quote_deals():
    """Deals whose sent quote has gone unanswered past the nudge window."""
    frappe.has_permission("Deal", "read", throw=True)
    return {
        "silence_days": deal_quote.silence_days(),
        "deals": deal_quote.silent_deals(),
    }


@frappe.whitelist(allow_guest=True)
def quote_pdf(token):
    """The quote page as a PDF, for clients who want an attachment.

    Guest-callable for the same reason the page is: the token is the
    authorization. Rendered from the same template and context as the
    page, so the two cannot say different things.
    """
    quote = deal_quote.resolve_token(token)
    html = frappe.render_template(
        "auraos/templates/includes/quote_body.html",
        deal_quote.client_context(quote),
    )
    deal_quote.record_open(quote.name, via="PDF")

    frappe.local.response.filename = f"{quote.name}.pdf"
    frappe.local.response.filecontent = get_pdf(html)
    frappe.local.response.type = "pdf"


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

    The round number and the chargeable flag come back computed - the
    job derives both from row order (Job.number_revisions) - as does
    the stage, which the revision may have sent back to the edit.
    """
    _check_job_permission(job, "write")
    if not (note or "").strip():
        frappe.throw(_("A revision needs a note"), frappe.ValidationError)
    doc = frappe.get_doc("Job", job)
    stage_before = doc.stage
    latest = doc.log_revision(note)
    return {
        "name": doc.name,
        "revision_rounds": doc.revision_rounds,
        "change_order_due": bool(doc.change_order_due),
        "round": latest.round,
        "chargeable": bool(latest.chargeable),
        "stage": doc.stage,
        "redo": doc.stage != stage_before,
    }


# -- money out on a job (T8, issue #10) --

ADVANCE_FIELDS = ["name", "recipient", "amount", "transferred_on", "note"]
# cost_line and invoice_no travel because the money screen can now
# correct them (#125), and a field an editor cannot read is a field it
# cannot open with the value the record actually holds.
EXPENSE_FIELDS = [
    "name", "spent_on", "amount", "category", "description",
    "paid_by", "paid_from", "photo", "creation",
    "cost_line", "invoice_no",
]
SETTLEMENT_FIELDS = [
    "name", "recipient", "amount", "direction", "advanced", "spent",
    "settled_on", "settled_by", "note",
]


def _money_rows(job):
    """The job's whole money-out ledger, in reading order.

    Read with get_all, which skips row-level permissions - the caller's
    check on the Job itself is the entire authorization for these rows,
    exactly as it is for a deal's comments and files.
    """
    return (
        frappe.get_all(
            "Job Advance",
            filters={"job": job},
            fields=ADVANCE_FIELDS,
            order_by="transferred_on asc, creation asc",
        ),
        frappe.get_all(
            "Job Expense",
            filters={"job": job},
            fields=EXPENSE_FIELDS,
            order_by="spent_on desc, creation desc",
        ),
        frappe.get_all(
            "Job Settlement",
            filters={"job": job},
            fields=SETTLEMENT_FIELDS,
            order_by="settled_on asc",
        ),
    )


def _float_dict(held):
    return {
        "holder": held.holder,
        "advanced": round_vnd(held.advanced),
        "spent": round_vnd(held.spent),
        "settled": round_vnd(held.settled),
        "amount": round_vnd(held.amount),
        "direction": held.direction,
    }


@frappe.whitelist()
def job_money(job):
    """Every đồng out on a job: the ledger, the floats, actual-vs-quoted.

    One call because the job's money screen is one question - "where has
    the money gone, and who is holding what?" - and the three answers
    are computed from the same rows.
    """
    _check_job_permission(job, "read")
    doc = frappe.get_doc("Job", job)
    advances, expenses, settlements = _money_rows(job)

    categories = settlement.category_actuals(doc.packages, doc.cost_lines, expenses)
    sums = settlement.totals(advances, expenses, categories)
    return {
        "advances": advances,
        "expenses": expenses,
        "settlements": settlements,
        "floats": [
            _float_dict(held)
            for held in settlement.floats(advances, expenses, settlements)
        ],
        "categories": [
            {
                "title": row.title,
                "quoted": round_vnd(row.quoted),
                "actual": round_vnd(row.actual),
                "variance": round_vnd(row.variance),
            }
            for row in categories
        ],
        "advanced_total": round_vnd(sums.advanced),
        "spent_total": round_vnd(sums.spent),
        "quoted_total": round_vnd(sums.quoted),
        # What this session may do with money, asked of the permissions
        # themselves rather than of the role - the screen hides what the
        # server would refuse anyway.
        "may_advance": bool(frappe.has_permission("Job Advance", "create")),
        "may_settle": bool(frappe.has_permission("Job Settlement", "create")),
        # Whether this job's spending is still a draft or already a
        # record (#123). Carried here rather than fetched separately, so
        # the screen and the lock read the same source: the doctype
        # refuses a change after the closing stage, and a screen offering
        # a control the server would refuse is a lie about the record.
        "closed": doc.stage == CLOSED_JOB_STAGE,
    }


@frappe.whitelist()
def job_expense_categories(job):
    """The categories an expense on this job may carry, in quote order."""
    _check_job_permission(job, "read")
    return frappe.get_doc("Job", job).expense_categories()


@frappe.whitelist()
def job_cost_lines(job):
    """The quoted lines an expense on this job may be spent against.

    In quote order, carrying the tax type, because the screen has to be
    able to say which of them come with no invoice - that is the whole
    reason a payment against one of them is a tax exposure (#123). The
    line's own expected cost travels too, so the person entering the
    real figure can see what was quoted beside it.
    """
    _check_job_permission(job, "read")
    doc = frappe.get_doc("Job", job)
    return [
        {
            "name": row.name,
            "description": row.description,
            "package": row.package,
            "tax_type": row.tax_type,
            "quoted": round_vnd(settlement.handed_over(row.as_dict())),
        }
        for row in doc.cost_lines
    ]


@frappe.whitelist()
def record_job_advance(job, recipient, amount, transferred_on=None, note=None):
    """Record cash handed to someone for this job.

    Create permission on Job Advance is what keeps this the founder's
    move; the job check is what stops it landing on a job they cannot
    touch.
    """
    _check_job_permission(job, "write")
    advance = frappe.get_doc(
        {
            "doctype": "Job Advance",
            "job": job,
            "recipient": recipient,
            "amount": amount,
            "transferred_on": transferred_on or frappe.utils.today(),
            "note": note,
        }
    ).insert()
    return {"name": advance.name, "float": _holder_float(job, recipient)}


@frappe.whitelist()
def log_job_expense(
    job,
    amount,
    category=None,
    description=None,
    spent_on=None,
    paid_by=None,
    paid_from=None,
    photo=None,
    cost_line=None,
    invoice_no=None,
):
    """Log one payment out, the way it happens on a shoot: fast.

    Everything but the amount has a default that is right often enough
    not to be typed - today, whoever is logging it, out of their float.
    `paid_by` exists for the case that isn't: money Linh spent that the
    founder is entering from a Zalo message, which has to land on her
    float rather than his.

    `cost_line` is which quoted line this spend answers to, and it is
    the reason the founder's tax exposure can be a fact rather than an
    estimate: the tax treatment lives on the line, the money lives here,
    and this link carries one to the other (#123). Optional, because
    money gets spent on things nobody quoted and forcing a line would
    invent one.

    Returns the payer's float, so the phone can answer the only
    follow-up question there is - how much of the advance is left.
    """
    _check_job_permission(job, "write")
    expense = frappe.get_doc(
        {
            "doctype": "Job Expense",
            "job": job,
            "amount": amount,
            "category": category or None,
            "description": description,
            "spent_on": spent_on or frappe.utils.today(),
            "paid_by": paid_by or frappe.session.user,
            "paid_from": paid_from or settlement.FROM_ADVANCE,
            "cost_line": cost_line,
            "invoice_no": invoice_no,
        }
    )
    expense.insert()
    if photo:
        _attach_photo(expense, photo)
    return {
        "name": expense.name,
        "amount": round_vnd(expense.amount),
        "category": expense.category,
        "photo": expense.photo,
        "float": _holder_float(job, expense.paid_by),
    }


@frappe.whitelist()
def update_job_expense(
    name,
    amount,
    category=None,
    description=None,
    cost_line=None,
    invoice_no=None,
):
    """Correct one payment that has already been logged (#125).

    **The reason this endpoint exists is the invoice number**, not the
    typo. `auraos.lib.exposure` calls a payment covered when paper was
    obtained for it, and covered spending leaves the founder's tax
    figure - so recording the replacement invoice is the only way that
    number ever comes down. Until now nothing in the app could write it:
    `log_job_expense` accepts one and no screen ever passed one, so the
    tile could rise and could not fall. The other fields ride along
    because the founder asked for spending to be correctable while a job
    is open, and an invoice number is a correction like any other.

    **`cost_line` is the second lever on the same figure.** An expense
    against a line marked Không hoá đơn is exposed, one against a line
    that comes with paper is not, and one attributed to nothing counts
    as exposed until somebody says otherwise. So a mis-picked line
    overstates or understates the company's position exactly as a
    missing invoice number does, and a screen that could fix one and not
    the other would close half the hole.

    **This states the row; it does not patch it.** Every editable field
    is written from what the caller sent, so an omitted `category`
    clears the category rather than keeping it. The caller is a row
    editor that holds all five values and sends all five; a patch
    endpoint that quietly kept what it was not told about would make
    "clear this field" unexpressible, which is the worse of the two
    surprises.

    Not editable here: who paid and out of whose float. The reconciler
    would cope - `paid_by_company` is re-read on every save - but moving
    a payment between a float and the company changes who is owed what,
    and that conversation belongs on the settlement screen.

    **No posting call, deliberately.** `Job Expense.on_update` already
    hangs `post_payment` off the save, and `auraos.lib.ledger.posting`
    answers a changed amount with REPOST while `restated` carries the
    original account forward. Correcting an amount reconciles itself;
    adding a second posting call here would double it.

    A closed job refuses all of this, in the doctype rather than here:
    `reject_change_after_close` runs in `validate`, so this endpoint
    inherits the freeze that #123 put on the record rather than
    restating it and risking the two drifting apart.
    """
    expense = frappe.get_doc("Job Expense", name)
    _check_job_permission(expense.job, "write")
    expense.amount = amount
    expense.category = category or None
    expense.description = description or None
    expense.cost_line = cost_line or None
    expense.invoice_no = (invoice_no or "").strip() or None
    expense.save()
    return {
        "name": expense.name,
        "amount": round_vnd(expense.amount),
        "category": expense.category,
        "photo": expense.photo,
        "float": _holder_float(expense.job, expense.paid_by),
    }


@frappe.whitelist()
def delete_job_expense(name):
    """Remove a payment that was never made (#125).

    The mistaken entry, not the corrected one: an amount typed wrong is
    `update_job_expense`'s job, and this is for spending that did not
    happen at all. Deleting was reachable from the Desk and from nowhere
    a person using the app could get to, which left the money screen
    able to add a payment and unable to take one back.

    The ledger comes back with it. `Job Expense.on_trash` posts the
    movement again with `moved=False`, which `auraos.lib.ledger.posting`
    answers by taking the entry out - so a deleted expense leaves no
    trace of money that never left the company.

    Closed jobs refuse this too, and for a sharper reason than they
    refuse an edit: `on_trash` walks a ledger entry back, so a freeze
    with a hole here would be the one direction that moves money and
    leaves nothing saying it was adjusted. The gate is in the doctype.

    Returns the payer's float, because taking a payment out of a shoot's
    spending is exactly when somebody wants to know what is left.
    """
    expense = frappe.get_doc("Job Expense", name)
    _check_job_permission(expense.job, "write")
    job, payer = expense.job, expense.paid_by
    expense.delete()
    return {"name": name, "float": _holder_float(job, payer)}


def _attach_photo(expense, file_url):
    """Point a just-uploaded receipt at the expense it documents.

    The photo is taken before the expense exists - that is the whole
    point of the phone flow - so it arrives as a private file attached
    to nothing, readable only by whoever uploaded it. Re-parenting it
    onto the expense hands it the expense's own permissions, which is
    how the founder gets to see the producer's receipts.

    Only an unattached file the caller uploaded themselves qualifies:
    otherwise this endpoint would re-parent someone else's private file
    and read it back through the expense.
    """
    photo = frappe.db.get_value(
        "File",
        {"file_url": file_url, "attached_to_name": ["is", "not set"]},
        ["name", "owner"],
        as_dict=True,
    )
    if not photo or photo.owner != frappe.session.user:
        frappe.throw(
            _("The photo must be a file you just uploaded"), frappe.ValidationError
        )
    file_doc = frappe.get_doc("File", photo.name)
    file_doc.attached_to_doctype = "Job Expense"
    file_doc.attached_to_name = expense.name
    file_doc.attached_to_field = "photo"
    file_doc.save()
    expense.db_set("photo", file_url)


def _holder_float(job, holder):
    """One person's float on a job, as the screens want to read it."""
    return _float_dict(settlement.float_for(holder, *_money_rows(job)))


@frappe.whitelist()
def settle_job(job, holder, note=None):
    """Close one person's float: the one click of story 34.

    The settlement is the transfer, recorded - so the float goes to zero
    and a job that carries on paying for things opens a fresh one.
    """
    _check_job_permission(job, "write")
    held = _holder_float(job, holder)
    if not held["amount"]:
        frappe.throw(
            _("{0}'s float on {1} is already even").format(holder, job),
            frappe.ValidationError,
        )
    settled = frappe.get_doc(
        {
            "doctype": "Job Settlement",
            "job": job,
            "recipient": holder,
            "amount": held["amount"],
            "advanced": held["advanced"],
            "spent": held["spent"],
            "note": note,
        }
    ).insert()
    return {
        "name": settled.name,
        "recipient": settled.recipient,
        "amount": settled.amount,
        "direction": settled.direction,
        "settled_on": settled.settled_on,
        "float": _holder_float(job, holder),
    }


# -- payment milestones (T10, issue #12) --


@frappe.whitelist()
def job_milestones(job):
    """A job's payment milestones, with the overdue call already made."""
    _check_job_permission(job, "read")
    terms = job_payment_milestone.payment_terms_days()
    return {
        "payment_terms_days": terms,
        "milestones": [
            job_payment_milestone.milestone_view(row, terms)
            for row in frappe.get_doc("Job", job).payment_milestones
        ],
    }


@frappe.whitelist()
def save_job_milestones(job, milestones):
    """Replace a job's milestone plan - names, shares and trigger stages.

    Rows the caller sends back with their row name keep the collection
    status and timestamps they have already earned; rows it leaves out
    are dropped. Amounts are never accepted from the caller: the job
    derives them from the quoted total on save.
    """
    _check_job_permission(job, "write")
    rows = frappe.parse_json(milestones) or []
    if not isinstance(rows, list):
        frappe.throw(_("Milestones must be a list"), frappe.ValidationError)

    doc = frappe.get_doc("Job", job)
    existing = {row.name: row for row in doc.payment_milestones}
    replacement = []
    for row in rows:
        if not (row.get("title") or "").strip():
            frappe.throw(_("A milestone needs a name"), frappe.ValidationError)
        # Checked here rather than on the stored row: Frappe fills an
        # empty Select with its first option, so by the time the job
        # validates, a plan that never said when the money falls due is
        # indistinguishable from one that chose Pre-production. Guessing
        # when a client owes us is not the system's call to make.
        if not row.get("trigger_stage"):
            frappe.throw(
                _("Milestone {0} needs the stage that makes it due").format(
                    row.get("title")
                ),
                frappe.ValidationError,
            )
        replacement.append(
            job_payment_milestone.replanned(existing.get(row.get("name")), row)
        )
    doc.set("payment_milestones", replacement)
    doc.save()
    return job_milestones(job)


@frappe.whitelist()
def set_milestone_status(job, milestone, status, invoice_no=None, account=None):
    """Move one milestone along (or back along) the collection flow.

    Back along on purpose: a status set by mistake would otherwise be a
    one-way door, which is exactly what the T6 walkthrough asked us to
    stop building. The timestamps follow the status either way.

    Issuing an invoice is this call, not a second one. đã xuất HĐ already
    stamps the issue date here; the number the accountant sent back rides
    in beside it, so there is exactly one door onto "invoiced" and the
    same door leads back out. Passing it again while the milestone is
    still invoiced corrects a mistyped number without disturbing the day
    the invoice went out. The VAT rate is never accepted from a caller -
    like the amount, it is derived on save, from the job.

    Collecting is the same shape: `account` says which pot of money the
    payment landed in, and belongs to đã thanh toán the way the invoice
    number belongs to đã xuất HĐ. It is optional at every level - omitted
    it falls back to the company's default account, and a company that
    has named no account collects exactly as it did before the ledger
    existed. The posting itself happens on the save; see
    job_payment_milestone.post_collections.
    """
    _check_job_permission(job, "write")
    if invoice_no is not None and status != MILESTONE_INVOICED:
        frappe.throw(
            _("An invoice number belongs to a milestone marked {0}").format(
                MILESTONE_INVOICED
            ),
            frappe.ValidationError,
        )
    if account is not None and status != MILESTONE_PAID:
        frappe.throw(
            _("An account belongs to a milestone marked {0}").format(MILESTONE_PAID),
            frappe.ValidationError,
        )
    if account and not frappe.db.exists("Cash Account", account):
        frappe.throw(
            _("{0} is not a cash account").format(account), frappe.DoesNotExistError
        )
    doc = frappe.get_doc("Job", job)
    row = job_payment_milestone.find(doc, milestone)
    row.status = status
    if invoice_no is not None:
        row.invoice_no = (invoice_no or "").strip()
    # Where this collection landed, carried to the save that posts it.
    doc.flags.cash_account = account or None
    doc.save()
    # The save recomputed the row's stamps in place, so this is the
    # stored milestone, not the one the caller described.
    return job_payment_milestone.milestone_view(row)


@frappe.whitelist()
def milestone_invoice_request(job, milestone):
    """The Zalo text asking the accountant to issue this milestone's invoice.

    Read-only: pasting the message is a human act, and marking the
    milestone requested is a separate, undoable decision.

    The text is for the accountant; the numbers beside it are for the
    screen. The VAT basis is stated rather than implied - a milestone
    already invoiced is read at the rate it was issued under, and one
    still to be invoiced at the company's rate today - so nothing has to
    parse a Vietnamese sentence to find out which.
    """
    _check_job_permission(job, "read")
    doc = frappe.get_doc("Job", job)
    row = job_payment_milestone.find(doc, milestone)
    vat_pct = job_payment_milestone.invoice_vat_pct(doc, row)
    amount = round_vnd(row.amount or 0)
    split = invoice_split(amount, vat_pct)
    return {
        "text": job_payment_milestone.request_text(doc, row),
        "invoice_no": row.invoice_no,
        "invoiced_on": row.invoiced_on,
        "amount": amount,
        "vat_pct": vat_pct,
        "net": split.net,
        "vat": split.vat,
    }


@frappe.whitelist()
def overdue_milestones():
    """Money owed past the company's payment terms - the founder's nudge.

    Lives here rather than on a dashboard page because the dashboard is
    T12's ticket; the Jobs board carries it in the meantime, and the
    dashboard will read the same endpoint.
    """
    frappe.has_permission("Job", "read", throw=True)
    return {
        "payment_terms_days": job_payment_milestone.payment_terms_days(),
        "milestones": job_payment_milestone.overdue(),
    }


# -- finance aggregates across every job --
#
# Money in, money out and money owed, rolled up for the finance screens.
# The arithmetic is auraos.lib.finance; these three are the adapters that
# fetch the rows.
#
# All three are producer-visible on purpose and by construction. They are
# built from milestone amounts and job expenses, both of which a producer
# already reads one job at a time (job_milestones, job_money); the
# founder's numbers - commission, CM, profit before tax, TNDN, net profit
# and VAT payable - live on the Deal behind permlevel 1 and are not part
# of any of these answers.

MILESTONE_INCOME_FIELDS = ["name", "parent", "title", "amount", "paid_on"]
MILESTONE_RECEIVABLE_FIELDS = ["name", "parent", "title", "amount", "status", "due_on"]
FINANCE_EXPENSE_FIELDS = ["name", "job", "spent_on", "amount", "category", "paid_from"]


def _finance_range(date_from, date_to):
    """The reporting window, refused rather than guessed.

    frappe.utils.getdate turns a missing bound into today, which would
    quietly report a different period than the caller asked for. A range
    that ends before it starts is a different matter - it is empty, and
    an empty report is the honest answer to it.
    """
    if not date_from or not date_to:
        frappe.throw(
            _("A finance report needs a date range"), frappe.ValidationError
        )
    return frappe.utils.getdate(date_from), frappe.utils.getdate(date_to)


def _permitted_jobs():
    """The jobs this session may list - the scope of every finance read.

    The rows below are read with frappe.get_all, which skips row-level
    permissions, so this list is the entire authorization: the same shape
    job_payment_milestone.overdue() and the deal board's tag map use.
    """
    return frappe.get_list("Job", pluck="name", limit_page_length=0)


def _job_clients(names):
    """{job: {title, company, company_name}} for a set of jobs.

    Read with get_all behind the caller's job scoping, exactly as
    job_payment_milestone.overdue() reads the same three fields. The
    client's own name is on every quote a producer sends, so nothing here
    widens what they may see.
    """
    if not names:
        return {}
    jobs = frappe.get_all(
        "Job",
        filters={"name": ["in", list(names)]},
        fields=["name", "title", "company"],
    )
    companies = {job.company for job in jobs if job.company}
    labels = (
        {
            row.name: row.company_name
            for row in frappe.get_all(
                "Party Company",
                filters={"name": ["in", list(companies)]},
                fields=["name", "company_name"],
            )
        }
        if companies
        else {}
    )
    return {
        job.name: {
            "title": job.title,
            "company": job.company,
            "company_name": labels.get(job.company),
        }
        for job in jobs
    }


def _with_client(rows, clients):
    """Hang each row's job, client and client name off the row."""
    for row in rows:
        client = clients.get(row.parent) or {}
        row["job"] = row.parent
        row["job_title"] = client.get("title")
        row["company"] = client.get("company")
        row["company_name"] = client.get("company_name")
    return rows


@frappe.whitelist()
def finance_income(date_from, date_to):
    """Money actually collected in a range, by month and by client.

    Cash basis: a milestone counts on the day it was recorded paid, not
    the day it fell due and not the day the accountant issued the
    invoice. Money in the bank is the only number a studio can spend, and
    the finance screens say "cash basis" on their face.
    """
    frappe.has_permission("Job", "read", throw=True)
    start, end = _finance_range(date_from, date_to)
    permitted = _permitted_jobs()
    rows = []
    if permitted:
        rows = frappe.get_all(
            "Job Payment Milestone",
            filters={
                "parenttype": "Job",
                "parent": ["in", permitted],
                "status": MILESTONE_PAID,
                "paid_on": ["between", [start, end]],
            },
            fields=MILESTONE_INCOME_FIELDS,
            order_by="paid_on asc",
        )
        rows = _with_client(rows, _job_clients({row.parent for row in rows}))
    return finance.income_report(rows, start, end)


@frappe.whitelist()
def finance_expenses(date_from, date_to):
    """Money spent in a range, by month, by category and by whose money.

    Every expense on every job this session may list - overhead has no
    home in the model yet, so this is job spend and says so by carrying
    the job on nothing but the query.
    """
    frappe.has_permission("Job Expense", "read", throw=True)
    start, end = _finance_range(date_from, date_to)
    permitted = _permitted_jobs()
    rows = []
    if permitted:
        rows = frappe.get_all(
            "Job Expense",
            filters={
                "job": ["in", permitted],
                "spent_on": ["between", [start, end]],
            },
            fields=FINANCE_EXPENSE_FIELDS,
            order_by="spent_on asc, creation asc",
        )
    return finance.expense_report(rows, start, end)


@frappe.whitelist()
def finance_receivables():
    """What clients owe us right now, aged into buckets.

    Not a range: what is owed is owed today. Everything uncollected
    counts, not only what has run past the terms - overdue_milestones()
    answers the nudge, this answers the ledger - and the lateness verdict
    is the same one, read from auraos.lib.milestones through the same
    payment terms.
    """
    frappe.has_permission("Job", "read", throw=True)
    permitted = _permitted_jobs()
    rows = []
    if permitted:
        rows = frappe.get_all(
            "Job Payment Milestone",
            filters={
                "parenttype": "Job",
                "parent": ["in", permitted],
                "status": ["!=", MILESTONE_PAID],
            },
            fields=MILESTONE_RECEIVABLE_FIELDS,
            order_by="due_on asc",
        )
        rows = _with_client(rows, _job_clients({row.parent for row in rows}))
    return finance.receivables_report(
        rows,
        now=frappe.utils.now_datetime(),
        terms_days=job_payment_milestone.payment_terms_days(),
    )


@frappe.whitelist()
def finance_profit_and_loss(date_from, date_to):
    """Money in against money out for a range, month by month.

    Both sides through the two endpoints that already answer them, so
    the profit and loss cannot print an income the income screen does
    not, and the permission check on each side is the one that side
    already carries: a session that may not list job expenses gets no
    profit and loss, not a profit and loss with the cost side missing.

    The subtraction is auraos.lib.finance's, not the browser's. A screen
    holding two arrays of months and zipping them itself would be the
    second place in this app that decides what a margin is when nothing
    came in, and the two places would eventually disagree.
    """
    return finance.profit_and_loss(
        finance_income(date_from, date_to),
        finance_expenses(date_from, date_to),
    )


# -- what a job earned (the new UI's per-job profitability) --

# Everything before Complete is still running and still worth watching.
# The stage itself is named beside the list it ends, so this and the
# expense freeze cannot drift apart.
CLOSED_JOB_STAGE = JOB_CLOSED_STAGE


def _job_profit(doc, client=None):
    """One job's money, as far as it has gone.

    Quoted-versus-actual is lib/settlement's - the same comparison
    `job_money` renders per category, totalled here rather than computed
    a second way. Money in is the milestones already collected, which is
    producer-visible by the same decision that makes the milestone plan
    producer-visible.
    """
    advances, expenses, settlements = _money_rows(doc.name)
    categories = settlement.category_actuals(doc.packages, doc.cost_lines, expenses)
    sums = settlement.totals(advances, expenses, categories)
    return {
        "name": doc.name,
        "title": doc.title,
        "company": doc.company,
        "client": client,
        "stage": doc.stage,
        **reporting.profit_view(
            quoted_total=doc.quote_total,
            # Output VAT is the client's tax passing through us, so the
            # margin base is what the company actually keeps - the same
            # base lib/quote.quote_chain measures a deal's margin on.
            revenue_ex_vat=to_decimal(doc.quote_subtotal or 0)
            + to_decimal(doc.quote_mf_amount or 0),
            quoted_cost=sums.quoted,
            actual_cost=sums.spent,
            milestones=[row.as_dict() for row in doc.payment_milestones],
        ),
    }


@frappe.whitelist()
def job_profitability(job=None, include_closed=0):
    """What a job has earned so far - one job, or every open one.

    Margin, deliberately, and not the founder profit chain. A producer
    already sees the quoted total, the milestone plan and every đồng
    spent; the difference between what was quoted and what the shoot is
    costing is the number that tells them it is going wrong, and story
    32 exists so they can act on it. Commission, CM, profit before tax,
    TNDN and net profit stay behind `deal_profit`, and no code path here
    reads them.

    With no argument the answer is the whole board, scoped by get_list
    so a producer sees only the jobs they may list.

    `include_closed` widens that board to the jobs that have finished.
    Off by default because the caller that has always asked this question
    - the job list - is watching work in progress, and a delivered job is
    not news. A margin report is the other reading: the only jobs whose
    margin is final are the closed ones, and a ranking that showed none
    of them would rank the studio on its unfinished work. Each row
    carries its own `stage`, so the two are told apart on the answer
    rather than by asking twice.
    """
    if job:
        _check_job_permission(job, "read")
        names = [job]
    else:
        frappe.has_permission("Job", "read", throw=True)
        filters = {} if frappe.utils.cint(include_closed) else {
            "stage": ["!=", CLOSED_JOB_STAGE]
        }
        names = frappe.get_list(
            "Job",
            filters=filters,
            pluck="name",
            order_by="modified desc",
            limit_page_length=0,
        )
    docs = [frappe.get_doc("Job", name) for name in names]
    clients = _company_names(doc.company for doc in docs)
    return [_job_profit(doc, clients.get(doc.company)) for doc in docs]


# -- paperwork (T11, issue #13) --


PAPERWORK_TEMPLATE_FIELDS = [
    "name",
    "template_name",
    # Which numbered document this is, so the screen knows whether to
    # ask for a signing date and a number at all (#139).
    "kind",
    "template_file",
    "template_source",
    "notes",
    "disabled",
    "placeholders",
]


def _paperwork_rows(filters=None):
    """Template rows with their stored placeholder list read back out.

    `unknown_placeholders` is why this is more than a list query: a
    template asking for `{{clint.tax_code}}` is broken, and the founder
    should meet that on a screen - where the fix is to edit the docx -
    rather than on a contract already coming off the printer.
    """
    known = set(paperwork.document_values())
    rows = frappe.get_list(
        "Paperwork Template",
        fields=PAPERWORK_TEMPLATE_FIELDS,
        filters=filters or {},
        order_by="template_name asc",
        limit_page_length=0,
    )
    for row in rows:
        names = paperwork_template.stored_placeholders(row)
        row["placeholders"] = names
        row["unknown_placeholders"] = [n for n in names if n not in known]
        # Which extra record this paper is about, if any - the screen
        # asks for exactly the parties the template mentions.
        row["needs_vendor"] = any(n.startswith("vendor.") for n in names)
        row["needs_freelancer"] = any(n.startswith("freelancer.") for n in names)
    return rows


@frappe.whitelist()
def paperwork_templates():
    """The templates a job can be papered from - the retired ones hidden."""
    frappe.has_permission("Paperwork Template", "read", throw=True)
    return _paperwork_rows(filters={"disabled": 0})


@frappe.whitelist()
def paperwork_library():
    """The whole library, for the screen that maintains it.

    Distinct from `paperwork_templates`, which answers "what can I
    generate for this job" and so hides the retired ones. This answers
    "what is in the library and may I change it", which needs the
    retired ones and the cheat sheet of placeholders a template may use.
    """
    frappe.has_permission("Paperwork Template", "read", throw=True)
    return {
        # Producers generate paperwork; the founder owns the templates.
        # The server enforces it either way - this only decides whether
        # the screen offers controls that would be refused.
        "can_manage": bool(frappe.has_permission("Paperwork Template", "create")),
        "placeholders": paperwork.fillable_placeholders(),
        "templates": _paperwork_rows(),
    }


@frappe.whitelist()
def generate_job_paperwork(
    job, template, vendor=None, freelancer=None, contract_number=None, terms=None
):
    """Fill a template for this job and attach the result to it.

    `contract_number` is what the dialog showed and the founder
    accepted or corrected, passed back rather than re-derived here.
    Deriving it twice - once to show and once to store - is two
    derivations of one fact, and they would agree until the moment
    another paper took the suffix between the two calls.

    Write permission on the job, not read: generating leaves a document
    hanging off the job, and whoever may not change a job may not add
    paperwork to it either.

    What could not be filled comes back with the file rather than
    instead of it. The document exists - it is printable, and the gaps
    are marked on the page - but the caller is told about them, because
    the founder is the only one who can close them.
    """
    _check_job_permission(job, "write")
    frappe.has_permission("Paperwork Template", "read", throw=True)
    document, filled = paperwork_template.generate(
        template, job, vendor=vendor, freelancer=freelancer,
        contract_number=contract_number, terms=_terms(terms),
    )
    _register_paper(
        job, template, vendor, freelancer, document, contract_number=contract_number
    )
    return {
        "name": document.name,
        "file_name": document.file_name,
        "file_url": document.file_url,
        "contract_number": contract_number or None,
        "missing": list(filled.missing),
        "unknown": list(filled.unknown),
    }


# What the status of a paper is made of, wherever a screen reads one.
PAPER_STATUS_FIELDS = ["name", "status", "status_changed_by", "status_changed_on"]


def _user_names(users):
    """Full names for a set of user ids, in one query.

    "Who told me this was signed" is answered with a person's name, so
    the screen never has to turn a login into one.
    """
    users = {user for user in users if user}
    if not users:
        return {}
    return {
        row.name: row.full_name
        for row in frappe.get_all(
            "User", filters={"name": ["in", list(users)]}, fields=["name", "full_name"]
        )
    }


def _attach_paper_status(row, paper, names):
    """Write one file row's signing status onto it, structured.

    Three fields and never a sentence: the screen decides how "Signed by
    Trần Minh Anh on Tuesday" reads, and papers older than the field
    read as Draft rather than as a blank.
    """
    row["paper"] = paper.name if paper else None
    row["status"] = paper_status.status_or_draft(paper.status) if paper else None
    row["status_changed_by"] = paper.status_changed_by if paper else None
    row["status_changed_by_label"] = names.get(paper.status_changed_by) if paper else None
    row["status_changed_on"] = paper.status_changed_on if paper else None
    return row


@frappe.whitelist()
def job_paperwork(job):
    """Documents hanging off this job, newest first, each with the
    registry row that says whether it has been signed.

    The status lives on Generated Paper, not on the File, so the two are
    joined here rather than on the screen: the job's paperwork tab shows
    and changes a paper's status without a second round trip, and a file
    that reached the job some other way simply has no registry row and
    so no status.
    """
    _check_job_permission(job, "read")
    rows = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Job", "attached_to_name": job},
        fields=["name", "file_name", "file_url", "file_size", "owner", "creation"],
        order_by="creation desc",
    )
    registry = frappe.get_all(
        "Generated Paper",
        filters={"job": job},
        fields=PAPER_STATUS_FIELDS + ["file_name", "file_url"],
        order_by="creation desc",
    )
    # Matched on the file's own name first: generating the same paper twice
    # produces two registry rows, and Frappe hands identical bytes back the
    # same file_url, so the url alone would tie both rows to one status. The
    # url is the fallback for anything stored without a name.
    by_name = {}
    by_url = {}
    for paper in registry:
        if paper.file_name:
            by_name.setdefault(paper.file_name, paper)
        if paper.file_url:
            by_url.setdefault(paper.file_url, paper)
    names = _user_names({paper.status_changed_by for paper in registry})
    for row in rows:
        paper = by_name.get(row.file_name) or by_url.get(row.file_url)
        _attach_paper_status(row, paper, names)
    return rows


def _register_paper(job, template, vendor, freelancer, document, contract_number=None):
    """The registry row (A5 round 2): every paper ever generated, in
    one place, with who it was for - the file alone hangs off its job
    and is invisible from anywhere else.

    **The contract number is frozen here and never re-derived** (#139).
    What is written is what the caller confirmed in the dialog, not what
    the rule would produce now: a number is an identity, and the inputs
    behind it can all move afterwards. The client's short code can be
    corrected, the template's `kind` can be changed, another contract
    can take the next suffix. None of that may rename a paper that has
    already been printed and signed. The field is read-only on the
    doctype for the same reason.
    """
    frappe.get_doc(
        {
            "doctype": "Generated Paper",
            "job": job,
            "template": template,
            "template_name": frappe.db.get_value(
                "Paperwork Template", template, "template_name"
            ),
            "vendor": vendor or None,
            "freelancer": freelancer or None,
            "contract_number": contract_number or None,
            "file_name": document.file_name,
            "file_url": document.file_url,
        }
    ).insert()


@frappe.whitelist()
def save_job_paperwork_draft(job, template, html, vendor=None, freelancer=None):
    """The draft as edited on screen, kept as a .docx on the job (A5
    round 4) - what the founder approved, not the raw fill.

    vendor/freelancer ride along only for the registry: the html is
    already filled and edited; nothing is substituted here.
    """
    _check_job_permission(job, "write")
    frappe.has_permission("Paperwork Template", "read", throw=True)
    document = paperwork_template.attach_draft(template, job, html)
    _register_paper(job, template, vendor, freelancer, document)
    return {
        "name": document.name,
        "file_name": document.file_name,
        "file_url": document.file_url,
    }


@frappe.whitelist()
def preview_template(template):
    """A template read before anything else (A5 round 5): its own HTML
    for a web one, its text for an uploaded Word file - placeholders
    visible as written."""
    frappe.has_permission("Paperwork Template", "read", throw=True)
    doc = frappe.get_doc("Paperwork Template", template)
    return {
        "html": paperwork_template.template_html(doc),
        "web": bool((doc.get("template_source") or "").strip()),
        "file_url": doc.template_file,
    }


@frappe.whitelist()
def preview_paper(file_url):
    """A paper already on a job, read on screen before any download
    (A5 round 5). Only files hanging off a job the session may read."""
    row = frappe.db.get_value(
        "File",
        {"file_url": file_url},
        ["name", "attached_to_doctype", "attached_to_name"],
        as_dict=True,
    )
    if not row or row.attached_to_doctype != "Job" or not row.attached_to_name:
        frappe.throw(_("No such paper"), frappe.DoesNotExistError)
    _check_job_permission(row.attached_to_name, "read")
    content = frappe.get_doc("File", row.name).get_content()
    return {"html": paperwork_template.paper_html(content)}


@frappe.whitelist()
def preview_job_paperwork(job, template, vendor=None, freelancer=None):
    """The paper on screen before anything is generated (A5 round 3).

    Read on the job is enough - nothing is attached; the screen shows
    what generate would print, gap markers highlighted, and offers the
    browser's own print dialog.
    """
    _check_job_permission(job, "read")
    frappe.has_permission("Paperwork Template", "read", throw=True)
    return paperwork_template.preview(
        template, job, vendor=vendor, freelancer=freelancer
    )


@frappe.whitelist()
def generated_papers():
    """Every paper ever generated, newest first - the registry screen.

    get_list, not get_all: row permissions apply, so this shows exactly
    what the session may read.
    """
    frappe.has_permission("Generated Paper", "read", throw=True)
    rows = frappe.get_list(
        "Generated Paper",
        fields=[
            "name",
            "job",
            "template",
            "template_name",
            "vendor",
            "freelancer",
            "file_name",
            "file_url",
            "owner",
            "creation",
            "status",
            "status_changed_by",
            "status_changed_on",
        ],
        order_by="creation desc",
        limit_page_length=0,
    )
    # Names, not codes, for the "who was this for" column.
    vendors = {row.vendor for row in rows if row.vendor}
    freelancers = {row.freelancer for row in rows if row.freelancer}
    vendor_names = (
        {
            r.name: r.company_name
            for r in frappe.get_all(
                "Party Company",
                filters={"name": ["in", list(vendors)]},
                fields=["name", "company_name"],
            )
        }
        if vendors
        else {}
    )
    freelancer_names = (
        {
            r.name: r.full_name
            for r in frappe.get_all(
                "Party Contact",
                filters={"name": ["in", list(freelancers)]},
                fields=["name", "full_name"],
            )
        }
        if freelancers
        else {}
    )
    changers = _user_names({row.status_changed_by for row in rows})
    for row in rows:
        row["vendor_label"] = vendor_names.get(row.vendor)
        row["freelancer_label"] = freelancer_names.get(row.freelancer)
        # Papers generated before the status existed read as Draft, so
        # "what is still unsigned" is one filter rather than two.
        row["status"] = paper_status.status_or_draft(row.status)
        row["status_changed_by_label"] = changers.get(row.status_changed_by)
    return rows


@frappe.whitelist()
def set_paper_status(paper, status):
    """Move one generated paper between Draft, Awaiting signature and Signed.

    Read on the job, not write: marking a contract signed is operational
    bookkeeping rather than privileged information, so anyone who can see
    the job can record it (#106). The Generated Paper permission the save
    itself checks was widened to match - a producer posts contracts too.

    Nothing enforces an order. A paper can be moved back to Draft,
    because a real document sometimes has to be redone, and a status set
    by mistake must not be a one-way door.
    """
    doc = frappe.get_doc("Generated Paper", paper)
    _check_job_permission(doc.job, "read")
    try:
        doc.status = paper_status.validated(status)
    except ValueError:
        frappe.throw(
            _("{0} is not a status a paper can be in").format(status),
            frappe.ValidationError,
        )
    # Who and when are the controller's to write, not the caller's.
    doc.save()
    return _attach_paper_status(
        {"name": doc.name, "file_url": doc.file_url},
        doc,
        _user_names({doc.status_changed_by}),
    )


@frappe.whitelist()
def job_parties(job):
    """The people this job's own breakdown names, for the paperwork
    pickers: a freelancer contract is nearly always for someone already
    on the job's cost lines, so they come first."""
    _check_job_permission(job, "read")
    doc = frappe.get_doc("Job", job)
    contacts = []
    seen = set()
    for row in doc.cost_lines:
        if row.source_contact and row.source_contact not in seen:
            seen.add(row.source_contact)
            contacts.append(row.source_contact)
    if not contacts:
        return {"freelancers": []}
    rows = frappe.get_all(
        "Party Contact",
        filters={"name": ["in", contacts]},
        fields=["name", "full_name"],
    )
    by_name = {row.name: row for row in rows}
    return {"freelancers": [by_name[name] for name in contacts if name in by_name]}


# -- the Library: knowledge the company keeps --
#
# The Documents screen has two tabs and they share nothing but a roof.
# Everything above fills a template from a job's own records and leaves
# a document belonging to that job. A Library document is written by
# hand, belongs to nobody and generates nothing, so none of the
# placeholder machinery reaches down here and none of it should.


def _library_attachment_counts(names):
    """How many files hang off each document, in one query.

    Counted rather than listed: the card shows a number, and the list
    of every file in the library would be the larger half of the
    response for something nobody has asked to see yet.

    Counted in Python rather than with a `count(*)` and a `group_by`,
    which is the obvious way to write this and is what Frappe's own
    listview does. Two reasons not to. Frappe qualifies its group_by
    with a backticked table prefix and passes `count(*)` rather than
    `count(name)`, and whether the plain forms survive its field
    validation is a question this can simply not ask. And the library is
    SOPs - tens of rows, not thousands - so the aggregate buys nothing
    measurable and costs a behaviour nobody here can run yet. If this
    table ever grows, the group_by is the right change and this comment
    is the reason it was not the first one.
    """
    if not names:
        return {}
    rows = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "Library Document",
            "attached_to_name": ["in", names],
        },
        fields=["attached_to_name"],
        limit_page_length=0,
    )
    counts = {}
    for row in rows:
        counts[row.attached_to_name] = counts.get(row.attached_to_name, 0) + 1
    return counts


@frappe.whitelist()
def library_documents():
    """Every Library document, for the table and card views.

    **The body is deliberately not in this response.** A card shows one
    line of the document's prose, and `lib.library.snippet` cuts that
    line on this side, so listing the library does not ship every SOP in
    full and the browser is never handed markup it only meant to
    summarise. One document in full is `library_document_detail`.
    """
    frappe.has_permission("Library Document", "read", throw=True)
    rows = frappe.get_all(
        "Library Document",
        fields=["name", "title", "category", "body", "modified"],
        order_by="modified desc",
    )
    counts = _library_attachment_counts([row.name for row in rows])
    return {
        # Everyone reads, the founder writes. The server refuses either
        # way - this only decides whether the screen offers a control
        # that would be refused, the way paperwork_library does.
        "can_manage": bool(frappe.has_permission("Library Document", "create")),
        "categories": [row.name for row in frappe.get_all("Library Category", order_by="name")],
        "documents": [
            {
                "name": row.name,
                "title": row.title,
                "category": row.category,
                "snippet": library.snippet(row.body),
                # Spec #81: stamps cross the wire as ISO strings.
                "modified": reporting.iso(row.modified),
                "attachment_count": counts.get(row.name, 0),
            }
            for row in rows
        ],
    }


@frappe.whitelist()
def library_document_detail(name):
    """One document in full: its body, and the files hanging off it.

    Named apart from `library_documents` rather than differing from it
    by one trailing letter. The two return different shapes, so a typo
    between them hands a caller a list where it expected a record, and
    that fails somewhere other than where the mistake is.
    """
    frappe.has_permission("Library Document", "read", throw=True)
    doc = frappe.get_doc("Library Document", name)
    return {
        "name": doc.name,
        "title": doc.title,
        "category": doc.category,
        "body": doc.body or "",
        "modified": reporting.iso(doc.modified),
        "attachments": frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": "Library Document",
                "attached_to_name": doc.name,
            },
            fields=["name", "file_name", "file_url"],
            order_by="creation",
        ),
    }


@frappe.whitelist()
def save_library_document(title, body="", category=None, name=None):
    """Write a document, creating its category if that word is new.

    **The side effect is the feature.** Category is a Link to a small
    doctype so the filter list stays a fixed set of words rather than a
    field of near-duplicates, but #66 exists so that maintaining an SOP
    stops needing a deploy - and a category the founder had to file a
    ticket for would put the deploy back one level up. So a category
    typed here that does not exist yet is created here. A reader who
    finds a save endpoint inserting a second doctype should see this
    paragraph before they conclude it is a mistake.

    No `name` means a new document, which Frappe names.
    """
    if name:
        frappe.has_permission("Library Document", "write", doc=name, throw=True)
    else:
        frappe.has_permission("Library Document", "create", throw=True)

    heading = (title or "").strip()
    if not heading:
        # The doctype would refuse this anyway; saying so in words beats
        # a mandatory-field traceback arriving in a dialog.
        frappe.throw(_("A document needs a title."))

    label = (category or "").strip()
    if label and not frappe.db.exists("Library Category", label):
        frappe.get_doc({"doctype": "Library Category", "category_name": label}).insert()

    doc = frappe.get_doc("Library Document", name) if name else frappe.new_doc("Library Document")
    doc.title = heading
    doc.category = label or None
    doc.body = body or ""
    doc.save()
    return {"name": doc.name}


@frappe.whitelist()
def get_margin_floor():
    frappe.has_permission("AuraOS Settings", "read", throw=True)
    return float(margin_floor_pct())


def _save_setting(fieldname, value):
    """Write one AuraOS Settings field and read back what was stored.

    The three settings endpoints differ only in their field and its type,
    so the permission check and the save live here rather than three
    times over. Each caller still owns its own casting: a 0 typed into
    either nudge is a deliberate 0, and only the caller knows whether the
    field is a percentage or a count of days.
    """
    frappe.has_permission("AuraOS Settings", "write", throw=True)
    settings = frappe.get_doc("AuraOS Settings")
    settings.set(fieldname, value)
    settings.save()
    return settings.get(fieldname)


@frappe.whitelist()
def set_margin_floor(pct):
    return float(_save_setting("margin_floor_pct", float(pct or 0)))


@frappe.whitelist()
def get_tier_thresholds():
    """The two tier boundaries, defaults applied (playbook §2.2)."""
    frappe.has_permission("AuraOS Settings", "read", throw=True)
    from auraos.auraos.doctype.deal.deal import tier2_threshold, tier3_threshold

    return {"tier2": float(tier2_threshold()), "tier3": float(tier3_threshold())}


@frappe.whitelist()
def set_tier_thresholds(tier2=None, tier3=None):
    """Store the founder's own tier boundaries; 0 falls back to the
    playbook defaults."""
    frappe.has_permission("AuraOS Settings", "write", throw=True)
    settings = frappe.get_doc("AuraOS Settings")
    settings.tier2_threshold = float(tier2 or 0)
    settings.tier3_threshold = float(tier3 or 0)
    settings.save()
    return get_tier_thresholds()


# Playbook §6.1's opening allocation, until the founder stores their
# own numbers. Read via auraos.settings.setting so an unset field falls
# back here instead of reading as a deliberate 0% target.
DEFAULT_POSITIONING_MIX = {"cash": 70, "bridge": 20, "brand": 10}


def positioning_mix():
    from auraos.settings import setting

    return {
        key: int(setting(f"positioning_{key}_pct", None) or default)
        for key, default in DEFAULT_POSITIONING_MIX.items()
    }


@frappe.whitelist()
def get_positioning_rules():
    """The founder's classification dials: mix targets + which job
    types count as the positioning segment (auto Tier 3)."""
    frappe.has_permission("AuraOS Settings", "read", throw=True)
    return {
        "mix": positioning_mix(),
        "project_types": frappe.get_all(
            "Project Type",
            fields=["name", "is_positioning"],
            order_by="name",
        ),
    }


@frappe.whitelist()
def set_positioning_rules(cash=None, bridge=None, brand=None, positioning_types=None):
    """Store the mix targets and flag the positioning-segment job
    types; 0/unset targets fall back to the playbook's 70/20/10."""
    frappe.has_permission("AuraOS Settings", "write", throw=True)
    settings = frappe.get_doc("AuraOS Settings")
    settings.positioning_cash_pct = int(cash or 0)
    settings.positioning_bridge_pct = int(bridge or 0)
    settings.positioning_brand_pct = int(brand or 0)
    settings.save()
    flagged = set(frappe.parse_json(positioning_types or "[]"))
    for row in frappe.get_all("Project Type", fields=["name", "is_positioning"]):
        should = 1 if row.name in flagged else 0
        if row.is_positioning != should:
            # Through the document, not db.set_value: the flag decides
            # tiers, so the change should validate and leave a trail
            # like every other write in this file.
            doc = frappe.get_doc("Project Type", row.name)
            doc.is_positioning = should
            doc.save()
    return get_positioning_rules()


@frappe.whitelist()
def classification_hints():
    """The mix targets alone - for the deal form's positioning labels
    and the SOP page. Readable by anyone who can read deals; the
    founder-only dials stay behind get_positioning_rules."""
    frappe.has_permission("Deal", "read", throw=True)
    return positioning_mix()


@frappe.whitelist()
def preview_tier(estimated_budget=0, project_type=None, positioning=None):
    """The tier the rules would assign - the deal form's live chip.

    Computed here, not in the browser, so a producer session (which has
    no read permission on Settings) sees the outcome without ever
    learning the thresholds themselves.
    """
    frappe.has_permission("Deal", "read", throw=True)
    from auraos.auraos.doctype.deal.deal import derive_tier

    return (
        derive_tier(
            float(estimated_budget or 0), project_type or None, positioning or None
        )
        or ""
    )


@frappe.whitelist()
def get_quote_silence_days():
    frappe.has_permission("AuraOS Settings", "read", throw=True)
    return deal_quote.silence_days()


@frappe.whitelist()
def set_quote_silence_days(days):
    return int(_save_setting("quote_silence_days", int(days or 0)))


@frappe.whitelist()
def get_payment_terms_days():
    frappe.has_permission("AuraOS Settings", "read", throw=True)
    return job_payment_milestone.payment_terms_days()


@frappe.whitelist()
def set_payment_terms_days(days):
    return int(_save_setting("payment_terms_days", int(days or 0)))


# -- company identity on the quote (T6.1a, issue #42) --


@frappe.whitelist()
def get_company_identity():
    """The company block as stored, for the screen that edits it.

    Not `company_view`: that is the client-facing projection, where an
    empty field is None so a line can be dropped. An editor needs the
    values themselves.
    """
    frappe.has_permission("AuraOS Settings", "read", throw=True)
    return {
        field: frappe.db.get_single_value("AuraOS Settings", field)
        for field in COMPANY_FIELDS
    }


@frappe.whitelist()
def set_company_identity(values):
    """Save the company block - and only the company block.

    The same narrow-surface rule as the deals table: a settings screen
    that can write any field on this Single is one bug away from setting
    the margin floor. Anything outside the whitelist is refused by name
    rather than ignored quietly.
    """
    frappe.has_permission("AuraOS Settings", "write", throw=True)
    values = frappe.parse_json(values) or {}
    if not isinstance(values, dict):
        frappe.throw(_("Company identity must be an object"), frappe.ValidationError)
    unknown = set(values) - set(COMPANY_FIELDS)
    if unknown:
        frappe.throw(
            _("Not part of the company identity: {0}").format(
                ", ".join(sorted(unknown))
            ),
            frappe.ValidationError,
        )
    settings = frappe.get_doc("AuraOS Settings")
    settings.update(values)
    settings.save()
    return get_company_identity()


# -- cash accounts: what the company actually holds (#101) --
#
# The first time the cash ledger is visible. Two reads, both derived:
# a balance is `sum(amount)` over an account's entries and nothing else,
# computed by auraos.lib.ledger and never stored, never defaulted and
# never accepted from a caller. There is no setter down here on purpose
# - a figure somebody can type over is an opinion, and the point of this
# pair of endpoints is that the number is a fact.
#
# Founder-only, decided by the server: the permission asked for is read
# on Cash Ledger Entry, which #99 granted to Founder and System Manager
# and to no operating role beyond them. A producer reads a job's own
# money through job_money(); what the company holds across every job is
# not their question, and the refusal is the doctype's, not this
# module's opinion of it.
#
# The imports are local to keep this section additive - see
# get_tier_thresholds() for the same shape.


@frappe.whitelist()
def cash_accounts():
    """Every cash account with what the ledger says it holds.

    The total comes down computed, like every balance under it. Nothing
    here is a list for a screen to add up: the frontend formats money
    and never works it out.

    A company that has named no account gets an empty list and a total
    of 0 - the same silence #99 chose when a collection has nowhere to
    post to, rather than an error about a company that simply has not
    said where it keeps its money yet.
    """
    from auraos.auraos.doctype.cash_account.cash_account import default_account
    from auraos.lib import ledger

    frappe.has_permission("Cash Ledger Entry", "read", throw=True)
    accounts = frappe.get_all(
        "Cash Account",
        fields=["name", "account_name", "note"],
        order_by="account_name asc",
    )
    entries = frappe.get_all("Cash Ledger Entry", fields=["account", "amount"])
    held = ledger.holdings([account.name for account in accounts], entries)
    by_account = {holding.account: holding for holding in held}
    default = default_account()
    return {
        "accounts": [
            {
                "name": account.name,
                "account_name": account.account_name,
                "note": account.note or None,
                "balance": by_account[account.name].balance,
                "count": by_account[account.name].count,
                # Where a collection lands when nobody says otherwise.
                "is_default": account.name == default,
            }
            for account in accounts
        ],
        "total": ledger.total_held(held),
        "count": sum(holding.count for holding in held),
    }


@frappe.whitelist()
def cash_account_entries(account):
    """One account's movements, newest first, each with its source.

    The source is what the origin calls itself, not the pair it is
    stored as: auraos.lib.ledger.source_of turns a doctype and a name
    into the milestone, expense or float a founder recognises, and the
    job it happened on is resolved to its title here because that is the
    one part of it a fetch can answer and arithmetic cannot.

    An account nothing has ever been posted against answers with an
    empty list and a balance of 0.
    """
    from auraos.auraos.doctype.cash_ledger_entry import cash_ledger_entry
    from auraos.lib import ledger

    frappe.has_permission("Cash Ledger Entry", "read", throw=True)
    if not frappe.db.exists("Cash Account", account):
        frappe.throw(
            _("{0} is not a cash account").format(account), frappe.DoesNotExistError
        )
    rows = cash_ledger_entry.entries_for(account)
    titles = _cash_job_titles({row.job for row in rows if row.job})
    (held,) = ledger.holdings([account], rows)
    return {
        "account": account,
        "account_name": frappe.db.get_value("Cash Account", account, "account_name"),
        "balance": held.balance,
        "count": held.count,
        "entries": [ledger.entry_view(row, titles.get(row.job)) for row in rows],
    }


def _cash_job_titles(names):
    """{job: title} for the jobs a set of entries came from.

    Read with get_all rather than get_list: this endpoint has already
    refused anybody who may not read the ledger, and a founder filtering
    their own cash by which jobs they happen to own would report a
    balance that is not the account's.
    """
    if not names:
        return {}
    return dict(
        frappe.get_all(
            "Job",
            filters={"name": ["in", list(names)]},
            fields=["name", "title"],
            as_list=True,
        )
    )


# -- no-invoice exposure (T9, issue #11) --


@frappe.whitelist()
def no_invoice_exposure():
    """Money paid out with no invoice, and the TNDN it exposes us to.

    Founder-only, and refused outright rather than blanked: this is the
    company's tax position, which sits behind the same boundary as the
    profit chain.

    **Read off the expenses, not off the quote.** An earlier version of
    this endpoint totalled `Không hoá đơn` cost lines, which taxed money
    that had been priced and never spent and missed money that had been
    spent and never priced (#123). A liability arises when the company
    pays out something it cannot deduct, so the source is the payment.

    The tax treatment still lives on the quoted line - it is the only
    record that carries it - and reaches the money through the line the
    expense says it spends against. Spending that names no line counts
    as exposed until somebody says otherwise: the founder chose the safe
    direction, because understating is the error that costs money at an
    audit. The payload keeps the two apart so the screen can show what
    is established beside what is assumed.

    Not a range. An uncovered payment is carried from the day it was
    made until an invoice is obtained, so the question is what the
    company is carrying now.

    Every job, not only the open ones. A finished shoot's missing
    invoice is still missing.
    """
    if not _is_founder():
        frappe.throw(
            _("Only the Founder may see the no-invoice tax exposure"),
            frappe.PermissionError,
        )

    jobs = dict(
        frappe.get_all("Job", fields=["name", "title"], as_list=True, limit_page_length=0)
    )
    if not jobs:
        return exposure.exposure_report([])

    expenses = frappe.get_all(
        "Job Expense",
        filters={"job": ["in", list(jobs)]},
        fields=["name", "job", "amount", "spent_on", "category", "description",
                "cost_line", "invoice_no"],
        order_by="spent_on desc",
        limit_page_length=0,
    )
    named = {row.cost_line for row in expenses if row.cost_line}
    lines = {}
    if named:
        lines = {
            row.name: row
            for row in frappe.get_all(
                "Deal Cost Line",
                filters={"name": ["in", list(named)]},
                fields=["name", "description", "tax_type"],
                limit_page_length=0,
            )
        }
    return exposure.exposure_report(exposure.exposure_rows(expenses, lines, jobs=jobs))


# -- what the pipeline is worth in the months ahead (#102) --
#
# A projection, and named like one at every level of the payload. The
# weighted figure travels as `weighted_projection`, the unweighted
# contrast as `open_pipeline`, and there is deliberately no key in here
# called total, balance, amount or income - auraos.lib.forecast.CASH_WORDS
# says which names are forbidden and `cash_shaped_keys` is what fails the
# test when one appears. #101 put a cash balance and a receivables total
# on the same dashboard; those are facts, provable against `sum(amount)`
# in the database. This is an estimate multiplied by a guess, and the
# next consumer of this endpoint must not be able to render it as money
# the company has without renaming a field to do it.
#
# Nothing is stored and nothing is cached. The dials are read from the
# settings rows on every call - not through frappe.get_cached_doc - so a
# probability changed in Settings changes the forecast on the very next
# read, with nothing in between that could hold a stale figure. There is
# no forecast table, no month totals column, and no setter anywhere that
# could write a weighted number.
#
# Founder-only, decided by the server: the permission asked for is read
# on AuraOS Settings, which grants read to Founder and System Manager and
# to no operating role. That is not squeamishness about the pipeline - a
# producer already reads deal values on the deals board. It is that this
# figure is the founder's own probability dials multiplied by values a
# producer knows, and division would hand the dials straight back.
#
# The imports are local to keep this section additive - see
# get_tier_thresholds() for the same shape.

# Where the per-stage dials live: a child table on the settings Single.
STAGE_FORECAST_TABLE = "Deal Stage Forecast"
STAGE_FORECAST_FIELD = "stage_forecast"


def _stored_stage_rules():
    """The dials as stored, read from the rows rather than from a cache.

    Read straight out of the child table on every call. A cached settings
    document would be one more thing between a founder moving a slider
    and the forecast moving with it, and "changing a probability changes
    the forecast" is an acceptance criterion rather than a nicety.

    An empty list is a real answer and not a failure: every stage falls
    back to the house default in auraos.lib.forecast, which is the only
    reading that does not turn an unconfigured site into an empty screen.
    """
    return frappe.get_all(
        STAGE_FORECAST_TABLE,
        filters={"parenttype": "AuraOS Settings", "parentfield": STAGE_FORECAST_FIELD},
        fields=["stage", "win_probability_pct", "lead_days"],
        order_by="idx asc",
        limit_page_length=0,
    )


@frappe.whitelist()
def stage_forecast_rules():
    """The win probability and lead time in force for every deal stage.

    Every stage of the Deal Select comes back, configured or not, so the
    settings screen renders the whole vocabulary. `configured` says
    whether a row exists: it is the only thing that can distinguish a
    founder who means 0% (Lost) from a stage nobody has been asked about,
    because on a Single an unwritten Int reads back as 0 as well.
    """
    from auraos.lib import forecast

    frappe.has_permission("AuraOS Settings", "read", throw=True)
    return {
        "stages": [
            {
                "stage": rule.stage,
                "win_probability_pct": rule.win_probability_pct,
                "lead_days": rule.lead_days,
                "configured": rule.configured,
                "contributes": rule.stage not in forecast.RESOLVED,
            }
            for rule in forecast.stage_rules(_stored_stage_rules())
        ]
    }


@frappe.whitelist()
def set_stage_forecast_rules(rules):
    """Store the founder's own dials, the whole table in one call.

    The table is rewritten rather than patched row by row: the founder
    edits every stage on one card, and a half-applied pair would forecast
    with one stage's old probability and another's new one.

    A probability of 0 is written and kept. That is the point of storing
    rows at all - a 0 that somebody typed is a decision, and it is only
    distinguishable from silence because the row exists to hold it.
    """
    from auraos.lib import forecast

    frappe.has_permission("AuraOS Settings", "write", throw=True)
    wanted = frappe.parse_json(rules) or []

    settings = frappe.get_doc("AuraOS Settings")
    settings.set(STAGE_FORECAST_FIELD, [])
    for row in wanted:
        stage = (row.get("stage") or "").strip()
        if stage not in forecast.STAGES:
            frappe.throw(
                _("{0} is not a deal stage").format(stage or "?"),
                frappe.ValidationError,
            )
        probability = int(row.get("win_probability_pct") or 0)
        if not 0 <= probability <= 100:
            frappe.throw(
                _("A win probability is a percentage between 0 and 100, not {0}").format(
                    probability
                ),
                frappe.ValidationError,
            )
        settings.append(
            STAGE_FORECAST_FIELD,
            {
                "stage": stage,
                "win_probability_pct": probability,
                "lead_days": max(int(row.get("lead_days") or 0), 0),
            },
        )
    settings.save()
    return stage_forecast_rules()


# What a deal needs for its value and its identity on the forecast. The
# three value fields are the ladder auraos.lib.forecast.deal_value walks:
# the quote the client holds, the deal's own pricing, the client's budget.
FORECAST_DEAL_FIELDS = [
    "name",
    "title",
    "stage",
    "estimated_budget",
    "quote_total",
    "latest_quote",
]


@frappe.whitelist()
def weighted_pipeline_forecast(months=6):
    """The open pipeline weighted by stage probability, month by month.

    Every figure is derived on this call out of the deals and the dials,
    and stored nowhere. A studio with no open deals gets the horizon with
    every month at zero and every stage at zero rather than an error -
    the same silence #101 chose for a company that has named no account.

    The value weighted is the best number written down for the deal: the
    total on the quote the client is holding, then the deal's own priced
    breakdown, then the client's stated budget. A published quote is a
    better number than a budget, and weighting the worse one when the
    better one exists would be wrong on purpose. Which one answered
    travels with the row as `value_basis`.
    """
    from auraos.lib import forecast

    frappe.has_permission("AuraOS Settings", "read", throw=True)
    deals = frappe.get_all(
        "Deal",
        filters={"stage": ["not in", list(forecast.RESOLVED)]},
        fields=FORECAST_DEAL_FIELDS,
        order_by="modified desc",
        limit_page_length=0,
    )
    quoted = _quoted_totals(deals)
    for deal in deals:
        # The frozen total off the quote the client was actually sent,
        # which does not move when somebody edits a cost line afterwards.
        deal["quoted_total"] = quoted.get(deal.get("latest_quote"))
    return forecast.projection(
        deals,
        forecast.stage_rules(_stored_stage_rules()),
        today=frappe.utils.today(),
        months=_forecast_months(months),
    )


def _quoted_totals(deals):
    """{quote: total} for the latest quote of each deal, frozen as sent."""
    names = {deal.get("latest_quote") for deal in deals if deal.get("latest_quote")}
    if not names:
        return {}
    return dict(
        frappe.get_all(
            "Deal Quote",
            filters={"name": ["in", list(names)]},
            fields=["name", "total"],
            as_list=True,
        )
    )


# How far ahead a forecast may be asked to look. A floor of one month
# because a horizon of none is not a screen, and a ceiling because the
# months come down as rows and a caller asking for a century would be
# asking this endpoint to render one.
MIN_FORECAST_MONTHS = 1
MAX_FORECAST_MONTHS = 24


def _forecast_months(months):
    """The horizon a caller asked for, clamped to something renderable."""
    try:
        wanted = int(months or 6)
    except (TypeError, ValueError):
        wanted = 6
    return max(MIN_FORECAST_MONTHS, min(wanted, MAX_FORECAST_MONTHS))

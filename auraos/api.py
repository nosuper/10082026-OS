"""Whitelisted HTTP endpoints for the frappe-ui SPA."""

import frappe
from frappe import _
from frappe.utils.pdf import get_pdf

from auraos.auraos.doctype.deal.deal import (
    OPERATING_ROLES,
    floor_breached,
    margin_floor_pct,
    quote_margin_fraction,
    rate,
    to_engine_lines,
)
from auraos.auraos.doctype.deal_quote import deal_quote
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


# -- quote delivery (T6, issue #8) --


def _quote_dict(quote, tracking=None):
    """A quote version as the producer's screen needs it.

    The client's view is a different, narrower projection — see
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
    tracking = {}
    if quotes:
        for row in frappe.get_all(
            "Deal Quote Open",
            filters={"quote": ["in", [q.name for q in quotes]]},
            fields=["quote", "via", "count(name) as events", "max(opened_on) as last_open"],
            group_by="quote, via",
        ):
            counts = tracking.setdefault(row.quote, {})
            counts[row.via] = row.events
            counts["last_open"] = max(
                filter(None, [counts.get("last_open"), row.last_open]), default=None
            )
    return [_quote_dict(quote, tracking.get(quote.name)) for quote in quotes]


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


@frappe.whitelist()
def get_quote_silence_days():
    frappe.has_permission("AuraOS Settings", "read", throw=True)
    return deal_quote.silence_days()


@frappe.whitelist()
def set_quote_silence_days(days):
    frappe.has_permission("AuraOS Settings", "write", throw=True)
    settings = frappe.get_doc("AuraOS Settings")
    settings.quote_silence_days = int(days or 0)
    settings.save()
    return int(settings.quote_silence_days)

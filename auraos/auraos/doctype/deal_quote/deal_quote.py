"""A published quote version: the client-facing snapshot of a deal.

Publishing freezes the deal's packages and totals into a new row with
its own random token. Rows are immutable afterwards — "wrong version
sent" (spec #2, story 21) is exactly the failure a mutable quote page
causes, so the controller refuses every content change and leaves only
the delivery status (sent / confirmed) writable.
"""

import frappe
from frappe import _
from frappe.model import default_fields, optional_fields
from frappe.model.document import Document

from auraos.lib.money import format_vnd, round_vnd, to_decimal
from auraos.lib.quote import (
    COMPANY_FIELDS,
    DEFAULT_DETAIL_LEVEL,
    client_view,
    company_view,
    delivery_state,
    lump_sum_entry,
    needs_nudge,
    quote_number,
    quote_totals,
)
from auraos.lib.quote import client_entries as quote_client_entries
from auraos.settings import setting

# Delivery status is the only thing that moves after publishing;
# everything else is the frozen snapshot the client may already have
# opened. Frappe's own bookkeeping columns are exempt.
MUTABLE_FIELDS = frozenset({"status", "sent_on", "confirmed_on"})

# Frappe's own columns (name, owner, creation, modified, docstatus…) are
# not quote content, and comparing them raises false alarms: a freshly
# inserted doc holds `creation` as a string where its database copy
# holds a datetime.
FRAPPE_BOOKKEEPING = frozenset(default_fields) | frozenset(optional_fields)

DEFAULT_SILENCE_DAYS = 5

# Stages a deal may be sitting in when its quote goes out; anything
# later (Negotiation, Won, Lost) is a human judgment we don't overrule.
PRE_SEND_STAGES = ("Brief Received", "De-brief", "Breakdown")


class DealQuote(Document):
    def before_insert(self):
        self.version = next_version(self.deal)
        # Guessing a 32-char hash is the whole access control on the
        # public page, so it is always server-generated.
        self.token = frappe.generate_hash(length=32)
        self.status = "Published"
        self.published_on = frappe.utils.now_datetime()
        self.sent_on = None
        self.confirmed_on = None

    def validate(self):
        if not self.is_new():
            self.reject_content_changes()

    def reject_content_changes(self):
        """A published version is a historical record, not a draft."""
        before = self.get_doc_before_save()
        if not before:
            return
        for field in self.meta.get_valid_columns():
            if field in MUTABLE_FIELDS or field in FRAPPE_BOOKKEEPING:
                continue
            if self.get(field) != before.get(field):
                frappe.throw(
                    _("Quote {0} is published — {1} cannot change. Publish a new version instead.").format(
                        self.name, field
                    ),
                    frappe.ValidationError,
                )
        if packages_snapshot(self) != packages_snapshot(before):
            frappe.throw(
                _("Quote {0} is published — its packages cannot change. Publish a new version instead.").format(
                    self.name
                ),
                frappe.ValidationError,
            )
        if lines_snapshot(self) != lines_snapshot(before):
            frappe.throw(
                _("Quote {0} is published — its lines cannot change. Publish a new version instead.").format(
                    self.name
                ),
                frappe.ValidationError,
            )

    def on_update(self):
        sync_deal_quote_state(self.deal)

    def mark_sent(self):
        """Mark the version sent — and undo an accidental confirm.

        Confirming used to be a one-way door (T6 walkthrough: "if I
        marked confirmed by accident, no turning back"). Marking sent
        again is the way back: the confirmation is withdrawn, the send
        it was based on is kept.
        """
        self.status = "Sent"
        self.confirmed_on = None
        self.sent_on = self.sent_on or frappe.utils.now_datetime()
        self.save()
        advance_deal_stage(self.deal)

    def mark_confirmed(self):
        self.status = "Confirmed"
        self.confirmed_on = frappe.utils.now_datetime()
        # sent_on is deliberately left alone: a quote confirmed without
        # ever being marked sent has no known send time, and inventing
        # one would put a fiction in the record.
        self.save()


def packages_snapshot(doc):
    return [
        (row.title, row.description, round_vnd(row.price or 0))
        for row in (doc.get("packages") or [])
    ]


def lines_snapshot(doc):
    return [
        (
            row.package,
            row.description,
            row.qty1,
            row.qty1_unit,
            row.qty2,
            row.qty2_unit,
            round_vnd(row.quote_price or 0),
        )
        for row in (doc.get("lines") or [])
    ]


def next_version(deal):
    """One past the deal's highest version.

    Two simultaneous publishes on the same deal would compute the same
    number and collide on the row name — a loud unique-key failure
    rather than two quotes sharing a version.
    """
    latest = frappe.get_all(
        "Deal Quote",
        filters={"deal": deal},
        fields=["version"],
        order_by="version desc",
        limit=1,
    )
    return (latest[0].version or 0) + 1 if latest else 1


def publish(deal_name, notes=None):
    """Freeze a deal's current packages and totals as the next version.

    Packages are the client-facing surface (spec #2, story 24), so a
    breakdown without them has nothing to publish. The deal's detail
    level decides what else the version carries: lump sum collapses the
    entries into one, line by line freezes the client-safe half of every
    cost line alongside them (A3, playbook §3.3).
    """
    deal = frappe.get_doc("Deal", deal_name)
    deal.check_permission("write")
    entries = client_entries(deal)
    if not entries:
        frappe.throw(
            _("Nothing to publish — add a cost line or a package first"),
            frappe.ValidationError,
        )

    detail_level = deal.quote_detail_level or DEFAULT_DETAIL_LEVEL
    lines = []
    if detail_level == "Lump sum":
        entries = [lump_sum_entry(deal.title, entries)]
    elif detail_level == "Line by line":
        lines = frozen_lines(deal)

    totals = quote_totals(
        [entry["price"] for entry in entries],
        mf_rate=to_decimal(deal.quote_mf_pct or 0) / 100,
        vat_rate=to_decimal(deal.vat_pct or 0) / 100,
    )
    quote = frappe.get_doc(
        {
            "doctype": "Deal Quote",
            "deal": deal.name,
            "title": deal.title,
            "client_name": client_name(deal),
            "detail_level": detail_level,
            "notes": notes,
            "quote_mf_pct": deal.quote_mf_pct,
            "vat_pct": deal.vat_pct,
            "subtotal": round_vnd(totals.subtotal),
            "mf_amount": round_vnd(totals.mf_amount),
            "vat_amount": round_vnd(totals.vat_amount),
            "total": round_vnd(totals.total),
            "packages": entries,
            "lines": lines,
        }
    )
    quote.insert()
    return quote


def frozen_lines(deal):
    """The client-safe half of every cost line, for a line-by-line quote.

    quote_price is the marked-up sell price; cost, markup and tax
    routing stay on the deal and are never frozen into a version.
    """
    return [
        {
            "package": row.package or None,
            "description": row.description,
            "qty1": row.qty1,
            "qty1_unit": row.qty1_unit,
            "qty2": row.qty2,
            "qty2_unit": row.qty2_unit,
            "quote_price": round_vnd(row.quote_price or 0),
        }
        for row in deal.cost_lines
    ]


def client_entries(deal):
    """What the client is offered — the shared rule, applied to a Deal.

    auraos.lib.quote owns the rule so the published quote and the
    breakdown's own totals cannot disagree about what the client sees.
    """
    entries = quote_client_entries(
        [package.as_dict() for package in deal.packages],
        [row.as_dict() for row in deal.cost_lines],
    )
    for entry in entries:
        entry["price"] = round_vnd(entry["price"])
    return entries


def client_name(deal):
    """The client's own name for the page header — never our deal title."""
    if not deal.company:
        return None
    return frappe.db.get_value("Party Company", deal.company, "company_name")


def deal_versions(deal_name):
    """Every version of a deal, newest first."""
    return frappe.get_all(
        "Deal Quote",
        filters={"deal": deal_name},
        fields=["name", "version", "status", "sent_on"],
        order_by="version desc",
    )


def sync_deal_quote_state(deal_name):
    """Mirror the quote delivery state onto the deal.

    The board and the nudge query read deals, not quotes; a stored
    mirror keeps both a single list query. Written with db.set_value so
    a producer's publish never trips Deal validation on fields they
    cannot edit.
    """
    versions = deal_versions(deal_name)
    newest = versions[0] if versions else None
    delivered = delivery_state(versions)
    frappe.db.set_value(
        "Deal",
        deal_name,
        {
            # The link is always the current version — that's the URL to
            # hand out; the status is the delivered one.
            "latest_quote": newest.name if newest else None,
            "quote_status": delivered.status if delivered else "Not Sent",
            "quote_sent_on": delivered.sent_on if delivered else None,
        },
        update_modified=False,
    )


def advance_deal_stage(deal_name):
    """Marking a quote sent moves the deal to Quote Sent (spec #2, story 25)."""
    stage = frappe.db.get_value("Deal", deal_name, "stage")
    if stage in PRE_SEND_STAGES:
        deal = frappe.get_doc("Deal", deal_name)
        deal.stage = "Quote Sent"
        deal.save()


def silence_days():
    """Days of client silence after a send before a quote is nudged."""
    return int(setting("quote_silence_days", DEFAULT_SILENCE_DAYS))


def silent_deals():
    """Deals whose delivered quote has gone quiet (spec #2, story 6).

    Deals already resolved (Won / Lost) are past nudging.
    """
    days = silence_days()
    now = frappe.utils.now_datetime()
    rows = frappe.get_list(
        "Deal",
        filters={
            "quote_status": "Sent",
            "stage": ["not in", ("Won", "Lost")],
        },
        fields=["name", "title", "quote_status", "quote_sent_on", "latest_quote"],
        limit_page_length=0,
    )
    return [
        row
        for row in rows
        if needs_nudge(
            status=row.quote_status,
            sent_on=frappe.utils.get_datetime(row.quote_sent_on)
            if row.quote_sent_on
            else None,
            now=now,
            silence_days=days,
        )
    ]


def find_by_token(token):
    """The quote a public token addresses, or None.

    Read past the permission layer on purpose (db.get_value and get_doc
    both skip it): the caller is Guest, and the token *is* the
    authorization. What Guest may then see is decided by client_context,
    not by row permissions — Deal Quote grants Guest nothing, so
    /api/resource stays closed even to someone holding a valid token.
    """
    name = frappe.db.get_value("Deal Quote", {"token": token or ""}, "name")
    return frappe.get_doc("Deal Quote", name) if name else None


def resolve_token(token):
    """find_by_token for callers with no page to render — the PDF
    endpoint, where a dead token is a 404 response, not a page."""
    quote = find_by_token(token)
    if not quote:
        frappe.throw(_("Quote not found"), frappe.DoesNotExistError)
    return quote


def page_url(token):
    """The public page's absolute URL, on the company domain."""
    return f"{frappe.utils.get_url()}/quote/{token}"


def pdf_url(token):
    """The PDF export of the same page — one definition, two callers."""
    return f"/api/method/auraos.api.quote_pdf?token={token}"


def client_context(quote):
    """The render context shared by the web page and the PDF export.

    One builder, one whitelist (auraos.lib.quote.client_view) — the page
    and the PDF cannot drift apart, and neither can leak a field the
    whitelist doesn't name.
    """
    context = client_view(quote.as_dict())
    # Who is making the offer — read live, through its own whitelist,
    # off a different document (issue #42, ADR 0002). Never merged into
    # the quote's own keys: two documents, two boundaries.
    context["company"] = company_identity()
    context["quote_number"] = quote_number(quote.name, quote.version)
    # Presentation helpers on top of the whitelist, never new data.
    context["money"] = format_vnd
    context["published_display"] = (
        frappe.utils.formatdate(context["published_on"], "d MMMM yyyy")
        if context.get("published_on")
        else None
    )
    return context


def stored_company_identity():
    """The company block as stored, field by field.

    Fetched per named field rather than as a document: `get_single_value`
    over the whitelist cannot pick up a setting nobody meant to publish,
    which matters more here than the round trips — the same Single holds
    the margin floor.
    """
    return {
        field: frappe.db.get_single_value("AuraOS Settings", field)
        for field in COMPANY_FIELDS
    }


def company_identity():
    """The company block a client sees, read at render time not at publish."""
    return company_view(stored_company_identity())


def request_header(name):
    """A request header, or None when there is no request (tests, jobs)."""
    if not getattr(frappe.local, "request", None):
        return None
    return frappe.get_request_header(name)


def record_open(quote_name, via="Page"):
    """Log a client opening the quote page or downloading its PDF.

    Inserted with ignore_permissions because the caller is Guest. Frappe
    rolls back GET requests unless asked not to, and the open *is* the
    point of this request — flags.commit makes the request's own commit
    run, rather than committing mid-render behind Frappe's back.
    """
    frappe.get_doc(
        {
            "doctype": "Deal Quote Open",
            "quote": quote_name,
            "opened_on": frappe.utils.now_datetime(),
            "via": via,
            "ip_address": getattr(frappe.local, "request_ip", None),
            "user_agent": request_header("User-Agent"),
        }
    ).insert(ignore_permissions=True)
    frappe.local.flags.commit = True

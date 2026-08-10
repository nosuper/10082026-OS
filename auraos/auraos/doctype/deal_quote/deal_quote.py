"""A published quote version: the client-facing snapshot of a deal.

Publishing freezes the deal's packages and totals into a new row with
its own random token. Rows are immutable afterwards — "wrong version
sent" (spec #2, story 21) is exactly the failure a mutable quote page
causes, so the controller refuses every content change and leaves only
the delivery status (sent / confirmed) writable.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from auraos.lib.money import format_vnd, round_vnd
from auraos.lib.quote import client_view, needs_nudge

# Delivery status is the only thing that moves after publishing;
# everything else is the frozen snapshot the client may already have
# opened. Frappe's own bookkeeping columns are exempt.
MUTABLE_FIELDS = frozenset({"status", "sent_on", "confirmed_on"})

FRAPPE_BOOKKEEPING = frozenset(
    {"modified", "modified_by", "docstatus", "idx", "_user_tags", "_comments",
     "_assign", "_liked_by", "_seen"}
)

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

    def on_update(self):
        sync_deal_quote_state(self.deal)

    def mark_sent(self):
        if self.status == "Confirmed":
            frappe.throw(
                _("Quote {0} is already confirmed").format(self.name),
                frappe.ValidationError,
            )
        self.status = "Sent"
        self.sent_on = frappe.utils.now_datetime()
        self.save()
        advance_deal_stage(self.deal)

    def mark_confirmed(self):
        self.status = "Confirmed"
        self.confirmed_on = frappe.utils.now_datetime()
        if not self.sent_on:
            # Confirmed without ever being marked sent (it went out over
            # Zalo before anyone touched the button); the send time is
            # unknown, so record it as now to keep the nudge honest.
            self.sent_on = self.confirmed_on
        self.save()


def packages_snapshot(doc):
    return [
        (row.title, row.description, round_vnd(row.price or 0))
        for row in (doc.get("packages") or [])
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
    breakdown without them has nothing to publish.
    """
    deal = frappe.get_doc("Deal", deal_name)
    deal.check_permission("write")
    if not deal.packages:
        frappe.throw(
            _("Add at least one client-facing package before publishing a quote"),
            frappe.ValidationError,
        )

    quote = frappe.get_doc(
        {
            "doctype": "Deal Quote",
            "deal": deal.name,
            "title": deal.title,
            "client_name": client_name(deal),
            "notes": notes,
            "quote_mf_pct": deal.quote_mf_pct,
            "vat_pct": deal.vat_pct,
            "subtotal": deal.quote_subtotal,
            "mf_amount": deal.quote_mf_amount,
            "vat_amount": deal.quote_vat_amount,
            "total": deal.quote_total,
            "packages": [
                {
                    "title": package.title,
                    "description": package.description,
                    "price": package.price,
                }
                for package in deal.packages
            ],
        }
    )
    quote.insert()
    return quote


def client_name(deal):
    """The client's own name for the page header — never our deal title."""
    if not deal.company:
        return None
    return frappe.db.get_value("Party Company", deal.company, "company_name")


def latest_quote(deal_name):
    rows = frappe.get_all(
        "Deal Quote",
        filters={"deal": deal_name},
        fields=["name", "version", "status", "sent_on"],
        order_by="version desc",
        limit=1,
    )
    return rows[0] if rows else None


def sync_deal_quote_state(deal_name):
    """Mirror the newest version's delivery state onto the deal.

    The board and the nudge query read deals, not quotes; a stored
    mirror keeps both a single list query. Written with db.set_value so
    a producer's publish never trips Deal validation on fields they
    cannot edit.
    """
    latest = latest_quote(deal_name)
    frappe.db.set_value(
        "Deal",
        deal_name,
        {
            "latest_quote": latest.name if latest else None,
            "quote_status": latest.status if latest else "Not Sent",
            "quote_sent_on": latest.sent_on if latest else None,
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
    value = frappe.db.get_single_value("AuraOS Settings", "quote_silence_days")
    return DEFAULT_SILENCE_DAYS if value is None else int(value)


def silent_deals():
    """Deals whose newest quote was sent and has gone quiet (story 6).

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


def resolve_token(token):
    """The quote a public token addresses; 404 for anything else.

    Read with ignore_permissions on purpose: the caller is Guest, and
    the token *is* the authorization. What Guest may then see is decided
    by client_context, not by row permissions — Deal Quote grants Guest
    nothing, so /api/resource stays closed.
    """
    name = frappe.db.get_value("Deal Quote", {"token": token or ""}, "name")
    if not name:
        frappe.throw(_("Quote not found"), frappe.DoesNotExistError)
    return frappe.get_doc("Deal Quote", name)


def client_context(quote):
    """The render context shared by the web page and the PDF export.

    One builder, one whitelist (auraos.lib.quote.client_view) — the page
    and the PDF cannot drift apart, and neither can leak a field the
    whitelist doesn't name.
    """
    context = client_view(quote.as_dict())
    # Presentation helpers on top of the whitelist, never new data.
    context["money"] = format_vnd
    context["published_display"] = (
        frappe.utils.formatdate(context["published_on"], "d MMMM yyyy")
        if context.get("published_on")
        else None
    )
    return context


def request_header(name):
    """A request header, or None when there is no request (tests, jobs)."""
    try:
        return frappe.get_request_header(name)
    except Exception:
        return None


def record_open(quote_name, via="Page"):
    """Log a client opening the quote page or downloading its PDF.

    Inserted with ignore_permissions because the caller is Guest, and
    committed explicitly: the open is the point of the request, and a
    later render error must not roll it back.
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
    frappe.db.commit()

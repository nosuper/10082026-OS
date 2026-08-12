"""Quote delivery decisions, framework-free (T6 / spec #2, stories 20–25).

Two rules that are worth pinning independently of Frappe:

**The guest boundary.** A published quote row carries the whole internal
chain — margin, commission, the profit block. What a client may read is
a whitelist, not a blocklist: `client_view` copies the named fields and
nothing else, so a new column on Deal Quote is invisible to guests until
someone deliberately adds it here.

**The silence nudge.** A quote counts as ignored when it was actually
sent, the configured window has elapsed, and the client has not
confirmed. Publishing alone never nudges: the page can exist for days
before the producer hands over the link.

No Frappe imports by contract; the DocType controller, the public web
page and the API are thin adapters over this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping

from auraos.lib.money import round_vnd, to_decimal
from auraos.lib.pricing import TNDN_RATE

# The playbook's three levels of quote detail (§3.3): how much of the
# build a client gets to read. Internal is always the full build; what
# goes out is gathered to the level the client needs.
DETAIL_LEVELS = ("Package totals", "Line by line", "Lump sum")
DEFAULT_DETAIL_LEVEL = "Package totals"

# Everything a client may read off a quote. Ordered as the page reads.
CLIENT_QUOTE_FIELDS = (
    "title",
    "client_name",
    "client_address",
    "client_tax_code",
    "client_contact",
    "version",
    "detail_level",
    "published_on",
    "quote_mf_pct",
    "vat_pct",
    "subtotal",
    "mf_amount",
    "vat_amount",
    "total",
    "notes",
)

# ...and off each of its packages. Cost, variance and the override are
# ours; the client sees an offer, not how we arrived at it.
CLIENT_PACKAGE_FIELDS = ("title", "description", "price")

# ...and off each frozen line on a line-by-line quote. quote_price is
# the marked-up sell price; cost, markup and tax routing are never
# frozen into a quote at all, so they cannot leak from here.
CLIENT_LINE_FIELDS = (
    "package",
    "description",
    "qty1",
    "qty1_unit",
    "qty2",
    "qty2_unit",
    "quote_price",
)

# Who is making the offer (T6.1a, issue #42). A second whitelist rather
# than a wider first one, because these fields come off a different
# document: AuraOS Settings, which also holds the margin floor. Handing
# that Single to a guest render context would put an internal number one
# typo away from a client's page.
#
# Unlike the quote, this is read live at render time and never frozen
# into a version — docs/adr/0002-quote-branding-renders-live.md says why.
COMPANY_FIELDS = (
    "logo",
    "company_name",
    "tax_code",
    "address",
    "phone",
    "email",
    "website",
    "bank_name",
    "bank_account_number",
    "bank_account_name",
    "signatory_name",
    "signatory_title",
)

# Which of those, present, make a block worth printing at all.
_BANK_FIELDS = ("bank_name", "bank_account_number", "bank_account_name")
_CONTACT_FIELDS = ("address", "phone", "email", "website")
# The letterhead's own half: who we are, as opposed to how to reach us
# or where to pay. The signatory names are not here — they belong to the
# PDF's signature block, and a site that filled in only those has no
# letterhead to print.
_MASTHEAD_FIELDS = ("logo", "company_name", "tax_code")


def company_view(settings: Mapping[str, Any]) -> dict:
    """The client-facing projection of the company's own identity.

    Every field comes back present, unfilled ones as None, so the
    template can address each key unconditionally and drop the lines
    that have nothing behind them. An empty string is an absence: a
    label with a blank beside it reads as a mistake on a printed
    contract, and a heading over three empty lines reads worse — hence
    `has_bank` and `has_contact`, which say whether a block has anything
    in it at all.
    """
    view = {field: _filled(settings.get(field)) for field in COMPANY_FIELDS}
    view["has_bank"] = any(view[field] for field in _BANK_FIELDS)
    view["has_contact"] = any(view[field] for field in _CONTACT_FIELDS)
    # Per field, not all-or-nothing: a site that filled in an address
    # and a tax code but never a company name still has a letterhead,
    # and hiding it would drop filled fields off the page.
    view["has_letterhead"] = (
        any(view[field] for field in _MASTHEAD_FIELDS) or view["has_contact"]
    )
    return view


def _filled(value):
    """A value, or None where there is nothing to print."""
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


def quote_number(name: str | None, version: int | None) -> str | None:
    """What the printed document calls itself — `DQ-0007-v2`.

    The record's identifier alone stops being an answer the moment a
    second version exists, and a page detached from its PDF has to be
    matchable to the offer it belongs to. v1 is written out for the same
    reason: a bare `DQ-0007` on a desk is ambiguous once v2 is sent.
    """
    if not name:
        return None
    return f"{name}-v{version}" if version else name


def client_view(quote: Mapping[str, Any]) -> dict:
    """The client-facing projection of a quote row and its packages.

    Missing fields come back as None rather than absent, so the template
    can address every key unconditionally.
    """
    view = {field: quote.get(field) for field in CLIENT_QUOTE_FIELDS}
    view["packages"] = [
        {field: package.get(field) for field in CLIENT_PACKAGE_FIELDS}
        for package in (quote.get("packages") or [])
    ]
    view["sections"] = line_sections(
        view["packages"], quote.get("lines") or []
    )
    return view


def quantity_display(qty1, unit1, qty2, unit2) -> str:
    """How a line's quantities read on a bid — "2 người × 3 ngày".

    Each half prints only when it says something: a bare quantity of 1
    with no unit is packaging noise, not information. Both halves silent
    → empty string, and the template leaves the cell blank.
    """

    def half(qty, unit):
        qty = to_decimal(qty or 0)
        unit = (unit or "").strip()
        if not unit and qty in (Decimal(0), Decimal(1)):
            return None
        number = f"{qty.normalize():f}"
        return f"{number} {unit}".strip() if unit else number

    parts = [part for part in (half(qty1, unit1), half(qty2, unit2)) if part]
    return " × ".join(parts)


def _number_display(value) -> str:
    value = to_decimal(value or 0)
    return f"{value.normalize():f}" if value else ""


def _client_line(line: Mapping[str, Any]) -> dict:
    view = {field: line.get(field) for field in CLIENT_LINE_FIELDS}
    view["quantity"] = quantity_display(
        line.get("qty1"),
        line.get("qty1_unit"),
        line.get("qty2"),
        line.get("qty2_unit"),
    )
    # Spreadsheet-style columns (founder, A3 walkthrough): quantities as
    # their own cells, plus the marked-up unit rate. The rate is derived
    # from the final amount, so a rescaled line keeps rate × qty ≈ amount.
    view["qty1_display"] = _number_display(line.get("qty1"))
    view["qty2_display"] = _number_display(line.get("qty2"))
    view["unit_rate"] = _unit_rate(view["quote_price"], line)
    return view


def _unit_rate(amount, line):
    factor = to_decimal(line.get("qty1") or 0) * to_decimal(line.get("qty2") or 0)
    if not factor:
        return round_vnd(amount or 0)
    return round_vnd(to_decimal(amount or 0) / factor)


def line_sections(packages, lines):
    """The line-by-line rendering: every offer entry with its member
    lines beneath it, in the same order `client_entries` prints.

    A package priced away from its lines' sum (T5's override — a
    round-up or a free-of-charge) would hand the client a table that
    doesn't add up; the difference is printed as its own Adjustment
    line, so the section total is always the sum of what's above it.
    """
    by_package = {}
    standalone = []
    for line in lines:
        if line.get("package"):
            by_package.setdefault(line["package"], []).append(line)
        else:
            standalone.append(line)

    def standalone_title(line):
        return line.get("description") or f"Item {line.get('idx')}"

    sections = []
    consumed = set()
    for package in packages:
        title = package.get("title")
        raw_members = by_package.get(title, [])
        # A standalone line published as its own entry (client_entries)
        # arrives here twice: once as this package entry, once in the
        # frozen lines. The entry *is* the line — consume it, or the
        # page would print it again below.
        if not raw_members:
            for index, line in enumerate(standalone):
                if index not in consumed and standalone_title(line) == title:
                    consumed.add(index)
                    break
        price = package.get("price") or 0
        members = [
            _client_line(line) for line in _rescaled_lines(raw_members, price)
        ]
        sections.append(
            {
                "title": title,
                "description": package.get("description"),
                "price": price,
                "lines": members,
            }
        )
    for index, line in enumerate(standalone):
        if index not in consumed:
            sections.append(
                {
                    "title": standalone_title(line),
                    "description": None,
                    "price": line.get("quote_price") or 0,
                    "lines": [],
                }
            )
    return sections


def _rescaled_lines(lines, price):
    """Line amounts that sum exactly to the price as offered.

    An overridden package must read as if it was simply quoted that way
    — no Adjustment row (the founder's A3 verdict): the difference is
    folded back into every line in proportion, whole đồng, remainder on
    the last line so the client's own arithmetic always closes. Lines
    that sum to zero cannot carry a proportion and are left alone.
    """
    rows = [dict(line) for line in lines]
    if not rows:
        return rows
    total = sum(to_decimal(row.get("quote_price") or 0) for row in rows)
    target = to_decimal(price or 0)
    if not total or total == target:
        return rows
    running = Decimal(0)
    for row in rows[:-1]:
        scaled = Decimal(
            round_vnd(to_decimal(row.get("quote_price") or 0) * target / total)
        )
        row["quote_price"] = scaled
        running += scaled
    rows[-1]["quote_price"] = target - running
    return rows


def lump_sum_entry(title, entries):
    """The whole offer as one line — the playbook's lump-sum level for
    small jobs and clients who don't read production budgets.

    The scope still reads: the single entry's description lists what
    the figure covers, so "one number" never becomes "no idea what
    for".
    """
    scope = ", ".join(
        entry["title"] for entry in entries if entry.get("title")
    )
    return {
        "title": title or "Production services",
        "description": scope or None,
        "price": sum(entry.get("price") or 0 for entry in entries),
    }


@dataclass(frozen=True)
class QuoteTotals:
    """Exact totals; rounding to whole đồng is the caller's concern."""

    subtotal: Decimal
    mf_amount: Decimal
    vat_amount: Decimal
    total: Decimal


def quote_totals(package_prices, mf_rate, vat_rate) -> QuoteTotals:
    """The client-facing totals, built from the prices the client can see.

    Deliberately *not* the engine's quote total. A producer who rounds a
    package price up (T5's override) changes what the client is offered,
    so the subtotal has to be the sum of the package prices as printed —
    otherwise the page shows an offer that doesn't add up to its own
    Total. Management fee and VAT then apply exactly as the engine does:
    MF on the subtotal, VAT on both.
    """
    subtotal = sum((to_decimal(price) for price in package_prices), Decimal(0))
    mf_amount = subtotal * to_decimal(mf_rate)
    vat_amount = (subtotal + mf_amount) * to_decimal(vat_rate)
    return QuoteTotals(
        subtotal=subtotal,
        mf_amount=mf_amount,
        vat_amount=vat_amount,
        total=subtotal + mf_amount + vat_amount,
    )


def client_entries(packages, lines):
    """What the client is offered, in reading order.

    Packages first, then any cost line belonging to none: the founder
    prices some items as standalone packages and quotes them straight
    (T6 walkthrough), so an unassigned line is its own one-line entry at
    its marked-up quote price — never money we silently absorb.
    """
    entries = [
        {
            "title": package.get("title"),
            "description": package.get("description"),
            "price": package.get("price") or 0,
        }
        for package in packages
    ]
    entries += [
        {
            "title": line.get("description") or f"Item {line.get('idx')}",
            "description": None,
            "price": line.get("quote_price") or 0,
        }
        for line in lines
        if not line.get("package")
    ]
    return entries


@dataclass(frozen=True)
class QuoteChain:
    """The client's price and everything it implies, exactly."""

    subtotal: Decimal
    mf_amount: Decimal
    vat_amount: Decimal
    total: Decimal
    revenue_ex_vat: Decimal
    margin: Decimal
    margin_fraction: Decimal | None
    total_commission: Decimal
    cm: Decimal
    profit_before_tax: Decimal
    tndn: Decimal
    net_profit: Decimal
    vat_payable: Decimal


def quote_chain(
    package_prices,
    cost_basis,
    input_vat,
    mf_rate,
    vat_rate,
    commission_rate,
) -> QuoteChain:
    """The profit chain measured against the price the client actually pays.

    The engine (auraos.lib.pricing) owns the cost side and stays the
    xlsx's arithmetic; what it cannot know is that a producer rounded a
    package up. Revenue therefore comes from the packages as printed,
    and margin, commission, tax and net profit all follow from it —
    otherwise rounding a package up would flatter the client's invoice
    without ever showing up in what the deal earns (issue #32).
    """
    totals = quote_totals(package_prices, mf_rate, vat_rate)
    cost_basis = to_decimal(cost_basis)
    revenue_ex_vat = totals.subtotal + totals.mf_amount
    margin = revenue_ex_vat - cost_basis
    total_commission = revenue_ex_vat * to_decimal(commission_rate)
    profit_before_tax = revenue_ex_vat - cost_basis - total_commission
    tndn = profit_before_tax * TNDN_RATE
    return QuoteChain(
        subtotal=totals.subtotal,
        mf_amount=totals.mf_amount,
        vat_amount=totals.vat_amount,
        total=totals.total,
        revenue_ex_vat=revenue_ex_vat,
        margin=margin,
        margin_fraction=(margin / revenue_ex_vat if revenue_ex_vat else None),
        total_commission=total_commission,
        cm=margin - total_commission,
        profit_before_tax=profit_before_tax,
        tndn=tndn,
        net_profit=profit_before_tax - tndn,
        vat_payable=totals.vat_amount - to_decimal(input_vat),
    )


DELIVERED_STATUSES = ("Sent", "Confirmed")


def delivery_state(versions):
    """Which version says where a deal actually stands with its client.

    Not simply the newest one. Publishing v2 does not un-send v1: the
    client still holds a quote they haven't answered, so the newest
    *delivered* version (sent or confirmed) is what the board and the
    silence nudge must read. Only when nothing has gone out yet does the
    newest published version speak.

    `versions` is newest-first; None when there are none.
    """
    for version in versions:
        if version.get("status") in DELIVERED_STATUSES:
            return version
    return versions[0] if versions else None


def needs_nudge(
    status: str | None,
    sent_on: datetime | None,
    now: datetime,
    silence_days: int | None,
) -> bool:
    """Whether a sent quote has gone unanswered long enough to nudge.

    A silence window of 0 (or unset) turns nudging off entirely, the same
    way a margin floor of 0 turns the floor warning off.
    """
    if not silence_days or silence_days <= 0:
        return False
    if status != "Sent" or sent_on is None:
        return False
    return (now - sent_on).total_seconds() >= silence_days * 86400

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

from auraos.lib.money import to_decimal

# Everything a client may read off a quote. Ordered as the page reads.
CLIENT_QUOTE_FIELDS = (
    "title",
    "client_name",
    "version",
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
    return view


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

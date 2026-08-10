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

from datetime import datetime
from typing import Any, Mapping

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

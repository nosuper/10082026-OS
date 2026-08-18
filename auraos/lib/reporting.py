"""Two cross-record views: every quote, and what a job has earned.

Framework-free by contract like the rest of auraos/lib; the whitelisted
endpoints in auraos.api are thin adapters that fetch the rows, apply the
permission scope and hand plain mappings here.

**Structured fields, never prose.** A quote row carries counts and
timestamps - `open_count`, `last_opened_at`, `download_count` - and the
screen decides whether that reads "3 opens, last 17 Aug" or "not opened
yet". A never-opened quote is zeros and None, not a missing key: the
list has a column either way.

**Margin, never the profit chain.** A job's profitability here is the
producer-visible half of the money: what the client was quoted, what has
been collected, what the job has actually paid out, and the difference.
Commission, CM, profit before tax, TNDN, net profit and VAT payable are
the founder's boundary (auraos.api.deal_profit) and are computed nowhere
in this module - a payload that cannot hold them cannot leak them.

**Margin is measured before VAT.** Output VAT is the client's tax
passing through the company, so the margin base is revenue excluding it,
exactly as auraos.lib.quote.quote_chain measures a deal's margin. The
cost side is the cash the job has actually handed over, which is what an
expense records and what auraos.lib.settlement already compares the
quote against.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, Mapping

from auraos.lib.milestones import PAID
from auraos.lib.money import round_vnd, to_decimal

Row = Mapping[str, Any]

# How a client reached a quote. Page views and PDF downloads are counted
# apart for the same reason auraos.api._quote_dict counts them apart: the
# page's own download button would otherwise score one visit as two.
PAGE = "Page"
PDF = "PDF"

# Where the folded tracking keeps the newest event of either kind.
LAST_OPEN = "last_open"

# What a free-text search on the quote list looks through: the deal and
# the client, the two things a founder remembers a quote by.
SEARCH_FIELDS = ("deal_title", "client")


def open_tracking(rows: Iterable[Row]) -> dict[str, dict]:
    """Grouped (quote, via) counts folded into one entry per quote.

    The caller groups in the database because the open log is the one
    table that grows without bound; this is the fold, kept here so the
    single-deal list and the cross-deal one count opens the same way.
    """
    tracking: dict[str, dict] = {}
    for row in rows:
        counts = tracking.setdefault(row.get("quote"), {})
        counts[row.get("via")] = row.get("events") or 0
        counts[LAST_OPEN] = max(
            filter(None, [counts.get(LAST_OPEN), row.get(LAST_OPEN)]), default=None
        )
    return tracking


def quotation_row(
    quote: Row,
    *,
    deal_title=None,
    company=None,
    client=None,
    url=None,
    tracking: Row | None = None,
) -> dict:
    """One published version as the cross-deal quote list reads it.

    The deal's own list (auraos.api.deal_quotes) answers "what have we
    sent this client"; this row answers "what is out with everyone right
    now", so it carries the deal and the client it belongs to.
    """
    tracking = tracking or {}
    return {
        "name": quote.get("name"),
        "deal": quote.get("deal"),
        "deal_title": deal_title,
        "company": company,
        "client": client,
        "version": quote.get("version"),
        "status": quote.get("status"),
        "total": round_vnd(quote.get("total") or 0),
        "published_on": quote.get("published_on"),
        "sent_on": quote.get("sent_on"),
        "confirmed_on": quote.get("confirmed_on"),
        "url": url,
        "open_count": int(tracking.get(PAGE) or 0),
        "download_count": int(tracking.get(PDF) or 0),
        "last_opened_at": tracking.get(LAST_OPEN),
    }


def matches_search(row: Row, search: str | None) -> bool:
    """Whether a quote row answers a free-text search.

    Case-insensitive substring over the deal title and the client name.
    An empty search matches everything, so the caller can pass whatever
    the box holds without asking whether it holds anything.
    """
    term = (search or "").strip().lower()
    if not term:
        return True
    return any(term in str(row.get(field) or "").lower() for field in SEARCH_FIELDS)


def collected(milestones: Iterable[Row]) -> Decimal:
    """What the client has actually paid: the milestones marked Paid.

    Requested and Invoiced are money asked for, not money in - the
    difference is the whole point of the collection flow, and a job with
    no milestones at all has simply collected nothing.
    """
    return sum(
        (
            to_decimal(row.get("amount") or 0)
            for row in milestones
            if row.get("status") == PAID
        ),
        Decimal(0),
    )


def margin_pct(margin, revenue_ex_vat):
    """Margin as a percentage of the revenue it was earned on.

    None when there is no revenue: a job quoted at nothing has no margin
    percentage, and 0 would read as a job breaking even.
    """
    if not revenue_ex_vat:
        return None
    return float(to_decimal(margin) / to_decimal(revenue_ex_vat) * 100)


def profit_view(
    *,
    quoted_total,
    revenue_ex_vat,
    quoted_cost,
    actual_cost,
    milestones: Iterable[Row] = (),
) -> dict:
    """What one job has earned so far, in whole đồng.

    `quoted_cost` and `actual_cost` are auraos.lib.settlement's totals -
    the same quoted-versus-actual comparison the job's money screen
    renders per category, totalled. Margin is the revenue the company
    keeps less what the job has actually paid out, so an overspent job
    reads negative rather than reading as if nothing had happened.

    Everything is rounded per part before the parts are compared, so the
    printed margin is exactly the printed revenue less the printed cost.
    """
    quoted = round_vnd(quoted_total or 0)
    revenue = round_vnd(revenue_ex_vat or 0)
    paid = round_vnd(collected(milestones))
    spent = round_vnd(actual_cost or 0)
    margin = revenue - spent
    return {
        "quoted_total": quoted,
        "collected": paid,
        # Measured against the quoted total, not against the milestone
        # plan: a job whose milestones bill less than 100% is a plan
        # half written, and the client still owes the rest.
        "uncollected": quoted - paid,
        "revenue_ex_vat": revenue,
        "quoted_cost": round_vnd(quoted_cost or 0),
        "actual_cost": spent,
        "margin": margin,
        "margin_pct": margin_pct(margin, revenue),
    }

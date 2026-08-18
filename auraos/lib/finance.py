"""Finance aggregates across jobs: money in, money out, money owed.

Framework-free by contract like the rest of auraos/lib; the whitelisted
endpoints in auraos.api are thin adapters that fetch rows and hand them
here. Three questions the finance screens ask, three shapes:

**Money in is cash, not invoices.** A milestone counts in the month the
payment was recorded, never the month it fell due or the month the
accountant issued the invoice. A company that bills in milestones and
gets paid in its own time cannot read an accrual number as its bank
balance, and the finance screens declare themselves cash basis.

**Money out is what was actually spent.** Job expenses, bucketed by the
month they were spent and by the quoted entry they belong to, split by
whether the company paid the vendor itself or somebody spent their
float. An expense naming no category lands in one Uncategorised bucket
rather than being dropped - the same rule actual-vs-quoted already uses,
and the same constant.

**Money owed ages from the terms, not from the due date.** The overdue
verdict and the days-late count come straight from auraos.lib.milestones,
so an ageing bucket and the nudge on the jobs board cannot disagree.
Terms of 0 turn the nudge off, and with it every overdue bucket - the
same switch the margin floor and the quote silence nudge use.

Nothing here touches commission, CM, profit before tax, TNDN, net profit
or VAT payable. Money in and money out are producer-visible by decision
(see the job_payment_milestone module docstring); the founder's profit
chain is a different question asked through a different door.

Rounding to whole đồng happens per part before the parts are added, so a
month's total is exactly the sum of its printed rows and the range total
is exactly the sum of its printed months. Nothing here emits a float.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, Mapping

from auraos.lib.milestones import PAID, days_overdue, is_overdue
from auraos.lib.money import round_vnd
from auraos.lib.money import to_decimal as _d
from auraos.lib.settlement import FROM_ADVANCE, FROM_COMPANY, UNCATEGORISED

Row = Mapping[str, Any]

# What money in is measured on. Stated in the payload because the screen
# that reads it says "cash basis" out loud and the two must be the same
# claim.
CASH_BASIS = "cash"

# The ageing ladder, in reading order. Keys, not labels: "1-30" is a
# bucket the UI names in whatever language it is written in, and this
# module has no business writing "Quá hạn 12 ngày" for it.
NOT_DUE = "not_due"
DAYS_1_30 = "1-30"
DAYS_31_60 = "31-60"
DAYS_61_90 = "61-90"
DAYS_90_PLUS = "90+"

AGEING_BUCKETS = (NOT_DUE, DAYS_1_30, DAYS_31_60, DAYS_61_90, DAYS_90_PLUS)


# -- dates in, dates out --


def as_date(value: Any) -> date | None:
    """Coerce a date, a datetime or an ISO string to a plain date."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def as_datetime(value: Any) -> datetime | None:
    """Coerce a datetime, a date or an ISO string to a datetime.

    Stored stamps arrive as `2026-08-10 09:30:00` from one driver and as
    a datetime from another; the lateness maths needs one of them.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    return datetime.fromisoformat(str(value).strip().replace(" ", "T"))


def month_key(day: date) -> str:
    """The calendar month a day falls in: `2026-08`."""
    return f"{day.year:04d}-{day.month:02d}"


def month_keys(date_from: Any, date_to: Any) -> list[str]:
    """Every calendar month the range touches, in order.

    Months with nothing in them are still months: a chart of income
    against expense with January quietly missing reads as a shorter year
    rather than an empty month. A range that ends before it starts - or
    one missing a bound - touches no months at all.
    """
    start, end = as_date(date_from), as_date(date_to)
    if start is None or end is None or end < start:
        return []
    keys = []
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        keys.append(month_key(cursor))
        cursor = date(
            cursor.year + cursor.month // 12, cursor.month % 12 + 1, 1
        )
    return keys


def _in_range(day: date | None, date_from: Any, date_to: Any) -> bool:
    start, end = as_date(date_from), as_date(date_to)
    if day is None or start is None or end is None:
        return False
    return start <= day <= end


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


# -- money in: what the client actually paid --


def income_report(rows: Iterable[Row], date_from: Any, date_to: Any) -> dict:
    """Collected money by calendar month, broken down by client.

    `rows` are paid milestones carrying `paid_on`, `amount`, `company`
    and `company_name`. Anything unpaid, unstamped or outside the range
    is ignored here as well as in the query, so the month boundary is a
    rule this module owns rather than a filter it hopes for.
    """
    keys = month_keys(date_from, date_to)
    clients: dict[str, dict[str, dict]] = {key: {} for key in keys}

    for row in rows:
        day = as_date(row.get("paid_on"))
        if not _in_range(day, date_from, date_to):
            continue
        _collect(clients[month_key(day)], row)

    months = [_income_month(key, clients[key]) for key in keys]
    return {
        "date_from": _iso(as_date(date_from)),
        "date_to": _iso(as_date(date_to)),
        "basis": CASH_BASIS,
        "months": months,
        "total": sum(month["total"] for month in months),
        "count": sum(month["count"] for month in months),
    }


def _collect(clients: dict[str, dict], row: Row) -> None:
    """Add one payment to its client's running total for the month."""
    company = row.get("company") or ""
    entry = clients.setdefault(
        company,
        {
            "company": row.get("company"),
            "company_name": row.get("company_name"),
            "total": Decimal(0),
            "count": 0,
        },
    )
    entry["company_name"] = entry["company_name"] or row.get("company_name")
    entry["total"] += _d(row.get("amount") or 0)
    entry["count"] += 1


def _income_month(key: str, clients: dict[str, dict]) -> dict:
    rows = sorted(
        (
            {
                "company": entry["company"],
                "company_name": entry["company_name"],
                "total": round_vnd(entry["total"]),
                "count": entry["count"],
            }
            for entry in clients.values()
        ),
        key=_by_total,
    )
    return {
        "month": key,
        "month_start": f"{key}-01",
        "total": sum(row["total"] for row in rows),
        "count": sum(row["count"] for row in rows),
        "clients": rows,
    }


def _by_total(row: Mapping[str, Any]):
    """Biggest first, then by name so equal totals hold a stable order."""
    return (-row["total"], row.get("company_name") or row.get("company") or "")


# -- money out: what the job actually cost --


def expense_report(rows: Iterable[Row], date_from: Any, date_to: Any) -> dict:
    """Spend by calendar month and category, plus a category rollup.

    `rows` are job expenses carrying `spent_on`, `amount`, `category` and
    `paid_from`. The paid-from split is the distinction the expense
    already records: money the company paid the vendor itself against
    money somebody spent out of the float they are holding.
    """
    keys = month_keys(date_from, date_to)
    by_month: dict[str, dict] = {key: _empty_spend() for key in keys}
    overall = _empty_spend()

    for row in rows:
        day = as_date(row.get("spent_on"))
        if not _in_range(day, date_from, date_to):
            continue
        _spend(by_month[month_key(day)], row)
        _spend(overall, row)

    months = [_expense_month(key, by_month[key]) for key in keys]
    return {
        "date_from": _iso(as_date(date_from)),
        "date_to": _iso(as_date(date_to)),
        "months": months,
        "categories": _category_rows(overall["categories"]),
        "paid_from": _paid_from_rows(overall["paid_from"]),
        "total": sum(month["total"] for month in months),
        "count": sum(month["count"] for month in months),
    }


def _empty_spend() -> dict:
    return {
        "categories": {},
        "paid_from": {FROM_ADVANCE: Decimal(0), FROM_COMPANY: Decimal(0)},
        "count": 0,
    }


def _spend(bucket: dict, row: Row) -> None:
    """Add one expense to a bucket's categories and paid-from split."""
    amount = _d(row.get("amount") or 0)
    category = row.get("category") or UNCATEGORISED
    bucket["categories"][category] = (
        bucket["categories"].get(category, Decimal(0)) + amount
    )
    bucket["paid_from"][paid_from_of(row.get("paid_from"))] += amount
    bucket["count"] += 1


def paid_from_of(value: Any) -> str:
    """Where an expense's money came from, defaulted the way floats are.

    A blank reads as the float rather than the company - the same
    assumption auraos.lib.settlement.floats makes, so the two views of
    the same expense cannot disagree about whose money it was.
    """
    return FROM_COMPANY if value == FROM_COMPANY else FROM_ADVANCE


def _expense_month(key: str, bucket: dict) -> dict:
    categories = _category_rows(bucket["categories"])
    return {
        "month": key,
        "month_start": f"{key}-01",
        "total": sum(row["total"] for row in categories),
        "count": bucket["count"],
        "categories": categories,
        "paid_from": _paid_from_rows(bucket["paid_from"]),
    }


def _category_rows(totals: Mapping[str, Decimal]) -> list[dict]:
    """Categories, biggest spend first, with Uncategorised trailing.

    Trailing on purpose: it is the one row that is not a thing the client
    was quoted, and actual-vs-quoted already prints it last.
    """
    rows = [
        {"category": title, "total": round_vnd(amount)}
        for title, amount in totals.items()
    ]
    rows.sort(
        key=lambda row: (
            row["category"] == UNCATEGORISED,
            -row["total"],
            row["category"],
        )
    )
    return rows


def _paid_from_rows(totals: Mapping[str, Decimal]) -> dict:
    """Both sources every time, so a month with one of them still prints."""
    return {source: round_vnd(totals[source]) for source in (FROM_ADVANCE, FROM_COMPANY)}


# -- money owed: what the client has not paid yet --


def ageing_bucket(days: int, overdue: bool) -> str:
    """Which rung of the ladder a receivable sits on.

    Everything not yet past the terms is one bucket - a milestone nobody
    has invoiced yet and one invoiced this morning are the same news.
    Past that the edges are inclusive at the top: day 30 is still 1-30,
    day 31 starts the next bucket.
    """
    if not overdue:
        return NOT_DUE
    if days <= 30:
        return DAYS_1_30
    if days <= 60:
        return DAYS_31_60
    if days <= 90:
        return DAYS_61_90
    return DAYS_90_PLUS


def receivables_report(rows: Iterable[Row], now: Any, terms_days: Any) -> dict:
    """Uncollected milestones, aged into buckets, oldest debt first.

    `rows` are milestones carrying `status`, `due_on`, `amount` and the
    job they hang off. A milestone whose job has not reached its trigger
    stage carries no due date and is still owed on a signed job, so it
    sits in "not yet due" rather than disappearing.
    """
    now = as_datetime(now)
    buckets: dict[str, list[dict]] = {key: [] for key in AGEING_BUCKETS}

    for row in rows:
        status = row.get("status")
        if status == PAID:
            continue
        view = _receivable(row, now, terms_days)
        buckets[ageing_bucket(view["days_overdue"], view["overdue"])].append(view)

    rungs = [_bucket(key, buckets[key]) for key in AGEING_BUCKETS]
    overdue_rungs = [rung for rung in rungs if rung["bucket"] != NOT_DUE]
    return {
        "as_of": _iso(now.date()) if now else None,
        "payment_terms_days": int(terms_days or 0),
        "buckets": rungs,
        "total": sum(rung["total"] for rung in rungs),
        "count": sum(rung["count"] for rung in rungs),
        "overdue_total": sum(rung["total"] for rung in overdue_rungs),
        "overdue_count": sum(rung["count"] for rung in overdue_rungs),
    }


def _receivable(row: Row, now: datetime | None, terms_days: Any) -> dict:
    due_on = as_datetime(row.get("due_on"))
    overdue = is_overdue(
        status=row.get("status"), due_on=due_on, now=now, terms_days=terms_days
    )
    # days_overdue counts past the terms whether or not the nudge is on,
    # so a terms setting of 0 would otherwise print a lateness the same
    # payload calls not overdue.
    late = days_overdue(due_on=due_on, now=now, terms_days=terms_days)
    return {
        "milestone": row.get("name"),
        "title": row.get("title"),
        "job": row.get("job"),
        "job_title": row.get("job_title"),
        "company": row.get("company"),
        "company_name": row.get("company_name"),
        "amount": round_vnd(row.get("amount") or 0),
        "status": row.get("status"),
        "due_on": _iso(due_on),
        "overdue": overdue,
        "days_overdue": late if overdue else 0,
    }


def _bucket(key: str, rows: list[dict]) -> dict:
    rows.sort(key=lambda row: (row["due_on"] is None, row["due_on"] or "", -row["amount"]))
    return {
        "bucket": key,
        "total": sum(row["amount"] for row in rows),
        "count": len(rows),
        "rows": rows,
    }

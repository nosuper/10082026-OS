"""Standing costs the company pays every month, and which of them are due.

Framework-free by contract like the rest of auraos/lib; the whitelisted
endpoints in auraos.api are thin adapters that fetch the rows and hand
plain mappings here.

**A template is not a payment, and this module never turns one into a
payment on its own.** #14's ask is that the founder must not type rent
twelve times a year. The tempting answer is a scheduler that writes a
`Company Expense` on the first of every month - and it is the wrong one,
because a Company Expense posts to the cash ledger. An invented posting
makes the cash screens disagree with the bank statement, which is the one
thing they exist to match, and the founder would find it while
reconciling rather than while reading. So what this module computes is a
**list of what is due**: the founder confirms, and confirming is one
click for the month rather than one form per line.

The stakes are asymmetric, which is what settles it. A due payment the
founder has not confirmed shows up on the screen, coloured, until they
do. A payment the system invented is a number in the books that nobody
decided, and it looks exactly like a real one.

**Due, never overdue.** This module says a month has arrived and nothing
has been recorded against it. Whether the landlord has been paid is a
fact about a bank account, not about this table, and a row here saying
"overdue" would be asserting something the app cannot know.

**Recorded is decided by the payment, never by a stamp on the template.**
A `Company Expense` carries the template it came from and the month it
covers, so "already recorded" is a question asked of the payments - the
things that actually exist. A `last_generated_on` field on the template
would be a second copy of that fact, and the copy is what goes stale when
somebody deletes a payment.

**Nothing here is ever due for a month that has not started.** Rent can
genuinely be paid in advance, and the founder can record that by hand -
what must not happen is a screen offering next quarter's salaries as
though the money had moved. A month becomes offerable on its first day.

**A recurring cost is a running cost, and so this has no depreciation
flag.** `Company Expense.for_depreciation` marks a purchase the
accountant may spread over years - a camera. A thing bought every month
is not that, by definition, and a template that could produce one would
be a contradiction the founder had to notice rather than a shape the
model refuses.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import Any, Iterable, Mapping

from auraos.lib.finance import as_date, month_key, month_keys
from auraos.lib.money import round_vnd

Row = Mapping[str, Any]

# What a due row is a claim about, said in the payload rather than left
# to a screen that would have to word an absence. The distinction between
# this and "unpaid" is the whole of the module's honesty.
DUE_BASIS = (
    "a month that has started, with no payment yet recorded against this "
    "standing cost for it - not a claim that the money is late"
)


def month_bounds(month: str) -> tuple[date, date]:
    """The first and last day of a `2026-08` month key."""
    year, number = (int(part) for part in month.split("-"))
    return date(year, number, 1), date(year, number, monthrange(year, number)[1])


def due_day(month: str, day_of_month: Any) -> date:
    """The day in a month a standing cost falls, clamped to that month.

    A template that says the 31st is a template about the end of the
    month, and February has to be able to answer it. Clamping down to the
    last day is the only reading that keeps a payment inside the month it
    belongs to - rolling forward to 1 March would file February's rent in
    March and quietly shorten February on the break-even screen.

    A missing or nonsensical day means the first, which is where rent and
    salaries land anyway and is a date the founder can correct on the
    payment rather than a blank they must fill on a template.
    """
    start, end = month_bounds(month)
    try:
        wanted = int(day_of_month or 1)
    except (TypeError, ValueError):
        wanted = 1
    if wanted < 1:
        wanted = 1
    return date(start.year, start.month, min(wanted, end.day))


def runs_in(template: Row, month: str) -> bool:
    """Whether a standing cost was running in a given month.

    Whole months on both ends. A template that starts on 20 August is
    running in August: rent agreed mid-month is still that month's rent,
    and the founder correcting the first payment's amount is a smaller
    ask than the founder wondering why August is missing.

    A template with no start date runs in no month at all rather than in
    every month since the epoch - `starts_on` is required on the record,
    and a row that has somehow lost it must fail closed.
    """
    if template.get("disabled"):
        return False
    start = as_date(template.get("starts_on"))
    if start is None:
        return False
    if month < month_key(start):
        return False
    end = as_date(template.get("ends_on"))
    return end is None or month <= month_key(end)


def offerable_months(date_from: Any, date_to: Any, today: Any) -> list[str]:
    """The months in a window that have begun, in order.

    A month is offerable from its first day. Anything later is a payment
    the company has not made, and offering it would invite a posting for
    money still in the bank.
    """
    now = as_date(today)
    if now is None:
        return []
    reached = month_key(now)
    return [key for key in month_keys(date_from, date_to) if key <= reached]


def recorded_months(payments: Iterable[Row]) -> set[tuple[Any, str]]:
    """Which (template, month) pairs already have a payment written.

    Asked of the payments rather than of the templates, so deleting a
    mistaken payment makes its month due again with nothing to reset.
    """
    pairs = set()
    for row in payments:
        template = row.get("recurring")
        month = row.get("recurring_month")
        if template and month:
            pairs.add((template, str(month)))
    return pairs


def due(
    templates: Iterable[Row],
    payments: Iterable[Row],
    date_from: Any,
    date_to: Any,
    today: Any,
) -> dict:
    """Every standing cost with a month that has come round unrecorded.

    One row per (template, month) - a template three months behind is
    three rows, because each is its own payment and the founder may
    record one without the others.

    Oldest first, so the founder works the backlog from the end that has
    been waiting longest rather than from the end that is easiest.
    """
    already = recorded_months(payments)
    months = offerable_months(date_from, date_to, today)
    rows = []
    for template in templates:
        name = template.get("name")
        for month in months:
            if not runs_in(template, month):
                continue
            if (name, month) in already:
                continue
            rows.append(line(template, month))
    rows.sort(key=lambda one: (one["month"], one["due_on"], str(one["template"] or "")))
    return {
        "basis": DUE_BASIS,
        "rows": rows,
        "count": len(rows),
        # What a click would post, so the button can say it. A total the
        # screen added itself would be the browser owning arithmetic it
        # has no business owning - the rule every finance screen here
        # already follows.
        "amount_total": sum(row["amount"] for row in rows),
    }


def line(template: Row, month: str) -> dict:
    """One standing cost owed for one month, as the payment it would become.

    Named after the fields of `Company Expense` rather than after the
    template's, because the founder is about to confirm a payment and the
    screen should show them the thing they are confirming.
    """
    return {
        "template": template.get("name"),
        "label": template.get("label"),
        "month": month,
        "due_on": due_day(month, template.get("day_of_month")),
        "amount": round_vnd(template.get("amount") or 0),
        "category": template.get("category") or None,
        "paid_from": template.get("paid_from") or None,
        "supplier": template.get("supplier") or None,
        "description": template.get("description") or None,
    }


def schedule(templates: Iterable[Row], date_from: Any, date_to: Any) -> dict:
    """What the standing costs commit the company to, month by month.

    Distinct from `due`: this is the shape of the obligation whether or
    not it has been recorded, and it includes months that have not
    started. It answers "what does this company cost to run" - the
    question the break-even screen puts the other side of the line
    against - where `due` answers "what have I not written down yet".

    Kept apart for exactly that reason. One number is a commitment and
    the other is a backlog, and a screen that showed one where the reader
    expected the other would be wrong in whichever direction the month
    happened to fall.
    """
    rows = list(templates)
    months = []
    for month in month_keys(date_from, date_to):
        running = [one for one in rows if runs_in(one, month)]
        months.append(
            {
                "month": month,
                "committed": sum(round_vnd(one.get("amount") or 0) for one in running),
                "count": len(running),
            }
        )
    return {
        "months": months,
        "committed_total": sum(month["committed"] for month in months),
        # The monthly run rate as it stands today, which is the figure a
        # founder holds against a quote. Taken from the last month in the
        # range rather than averaged: an average over a range in which
        # somebody was hired describes a company that never existed.
        "monthly_committed": months[-1]["committed"] if months else 0,
    }

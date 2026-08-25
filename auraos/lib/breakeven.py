"""Whether the work booked in a month covers what the company costs to run.

Framework-free by contract like the rest of auraos/lib; the whitelisted
endpoint in auraos.api is a thin adapter that fetches the rows and hands
plain mappings here.

**Show, don't suggest.** #14 says it in as many words: this informs the
founder's pricing judgement and the global margin floor, and it never
computes either. There is no recommended floor in this payload, no
suggested price, and nothing here writes a setting. A number that
proposed a floor would be read as one, and the floor is the founder's
call made against things this app cannot see - the quarter ahead, who is
about to leave, what a client is worth keeping.

**Contribution, not profit.** A job's margin is what it leaves behind
after its own direct costs, and that is what is available to pay for rent
and salaries. Calling it profit here would be wrong twice over: the
company's upkeep has not been taken out of it yet, and profit before tax
is a founder figure with commission in it that `reporting.profit_view`
deliberately does not compute. This module composes that view's `margin`
and reaches for nothing else.

**One derivation, N renderings.** Overheads arrive as the block
`auraos.lib.tax.overheads` already produces - the same block Finance's
Reports screen prints - and are never re-summed from the expense table
here. Job margin arrives as the rows `reporting.profit_view` already
produces, the same rows margin-by-job prints. Two functions over one set
of rows is how two screens come to disagree, and the disagreement always
surfaces in front of whoever is reconciling.

**The two sides are dated by different things and the payload says so,
loudly.** An overhead falls in the month the money left the account. A
job's margin is its *whole life's* margin, counted in the month the job
was booked - because that is the month the work was taken on, and the
decision the founder is checking (should we have said yes at that price)
was made then. A job that runs three months does not have three months of
margin to spread; it has one number, known properly only at the end.

That asymmetry is a real limit, not a rounding error, and it is why
`caveats` travels in the payload rather than being left for a screen to
word. A founder reading a surplus needs to know it may be made of a job
that has not finished spending.

**Provisional and final are separated, never added quietly.** A closed
job's margin is final; an open job is still spending, so its margin can
only fall. A month showing a surplus built entirely out of open jobs has
not broken even - it has an opinion about breaking even. Both totals are
here, and so is the split, so a screen can show the confident half.

**Flagged purchases are outside the break-even line, and visible beside
it.** `for_depreciation` marks a purchase the accountant may spread over
years - a camera, not a running cost - and a month that bought one would
otherwise read as a catastrophe against work that was priced fine. The
money did leave the bank, so it is carried as its own figure rather than
dropped: an invisible subtraction cannot be checked against anything.

Every figure is whole đồng, rounded by the modules upstream before it
arrives. The one figure that is not money - the coverage percentage - is
None rather than 0 when there was no overhead to cover, because a month
that spent nothing on itself was not covered 0%; it had nothing to cover.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from auraos.lib.finance import as_date, month_key, month_keys
from auraos.lib.reporting import margin_pct

Row = Mapping[str, Any]

# What each side of the line is measured on. Stated in the payload for
# the same reason auraos.lib.tax states its three: a reader holding this
# beside Income or beside the accountant's return needs to know why it
# will not match *before* they start reconciling, not after.
CONTRIBUTION_BASIS = (
    "each job's whole-life margin - revenue before VAT less what the job "
    "has actually spent - counted in the month the job was booked"
)

# The last stage in auraos.auraos.doctype.job.job.STAGES. Named here
# rather than imported because this module is framework-free by
# contract, and asserted against the doctype by the contract test in
# auraos/auraos/doctype/job/test_break_even.py - which is what stops the
# two from drifting apart.
CLOSED_STAGE = "Complete"

CAVEATS = [
    {
        "figure": "contribution",
        "why": (
            "a job's margin is one number for its whole life, counted in "
            "the month it was booked - a job that runs three months does "
            "not spread across them, so a month reads as the work it took "
            "on rather than the work it did"
        ),
    },
    {
        "figure": "open jobs' margin",
        "why": (
            "an open job is still spending, so its margin can only fall - "
            "a surplus made of open jobs is a forecast wearing a total's "
            "clothes, which is why the final half is totalled apart"
        ),
    },
    {
        "figure": "the margin floor",
        "why": (
            "nothing here proposes one. What a job must earn is the "
            "founder's judgement against the quarter ahead and who is on "
            "the payroll, and this screen is the evidence for that "
            "judgement rather than a substitute for it"
        ),
    },
]


def booked_month(job: Row) -> str | None:
    """The month a job's margin is counted in: the month it was booked.

    `booked_on` is the day the won deal became a job, which is the day
    the work was taken on at the price being judged. A job with no such
    day has no month, and is reported as unbooked rather than dropped
    into whichever month happens to be first - a job the founder cannot
    see is worse than a job in a bucket labelled "no date".
    """
    day = as_date(job.get("booked_on"))
    return month_key(day) if day else None


def _empty_month(key: str) -> dict:
    return {
        "month": key,
        "margin": 0,
        "final_margin": 0,
        "provisional_margin": 0,
        "job_count": 0,
        "final_count": 0,
        "revenue_ex_vat": 0,
        "actual_cost": 0,
    }


def _job_row(job: Row, day) -> dict:
    """One job as the break-even screen reads it.

    A projection of the profit view, never a recomputation of it: margin,
    revenue and cost are copied across as the upstream module rounded
    them, so this row and the margin-by-job row are the same figures.
    """
    return {
        "job": job.get("name"),
        "title": job.get("title"),
        "client": job.get("client") or job.get("company"),
        "stage": job.get("stage"),
        # Whether the number can still move. The screen is handed the
        # verdict rather than the stage name, because the rule about
        # which stage ends a job is not the browser's to know.
        "is_final": job.get("stage") == CLOSED_STAGE,
        "booked_on": day,
        "month": month_key(day) if day else None,
        "revenue_ex_vat": int(job.get("revenue_ex_vat") or 0),
        "actual_cost": int(job.get("actual_cost") or 0),
        "margin": int(job.get("margin") or 0),
        "margin_pct": job.get("margin_pct"),
    }


def contribution(jobs: Iterable[Row], date_from: Any, date_to: Any) -> dict:
    """What the jobs booked in a window left behind, by month.

    `jobs` are `reporting.profit_view` rows widened with `booked_on` and
    `stage` - the same rows margin-by-job renders, so a job's margin here
    and its margin there are one number computed once.

    The window is applied here rather than trusted from the caller, for
    the reason `finance.income_report` gives about its month boundary: a
    rule this module owns cannot disagree with a filter somebody wrote
    once in SQL.
    """
    start, end = as_date(date_from), as_date(date_to)
    months = {key: _empty_month(key) for key in month_keys(date_from, date_to)}
    rows = []
    unbooked = []
    for job in jobs:
        day = as_date(job.get("booked_on"))
        if day is None:
            unbooked.append(_job_row(job, None))
            continue
        if start is None or end is None or day < start or day > end:
            continue
        row = _job_row(job, day)
        rows.append(row)
        # A row inside the window falls in one of the window's months by
        # definition; the setdefault is here so a caller who hands over a
        # range these months were not built from gets an answer rather
        # than a KeyError.
        bucket = months.setdefault(row["month"], _empty_month(row["month"]))
        bucket["margin"] += row["margin"]
        bucket["job_count"] += 1
        bucket["revenue_ex_vat"] += row["revenue_ex_vat"]
        bucket["actual_cost"] += row["actual_cost"]
        if row["is_final"]:
            bucket["final_margin"] += row["margin"]
            bucket["final_count"] += 1
        else:
            bucket["provisional_margin"] += row["margin"]

    rows.sort(key=lambda one: (one["booked_on"], one["job"] or ""))
    unbooked.sort(key=lambda one: str(one["job"] or ""))
    return {
        "basis": CONTRIBUTION_BASIS,
        # In reading order, because months are a sequence: sorting them
        # by size would turn a run of the company's work into a league
        # table.
        "by_month": [months[key] for key in sorted(months)],
        "margin_total": sum(row["margin"] for row in rows),
        "final_total": sum(row["margin"] for row in rows if row["is_final"]),
        "provisional_total": sum(row["margin"] for row in rows if not row["is_final"]),
        "job_count": len(rows),
        "final_count": sum(1 for row in rows if row["is_final"]),
        "jobs": rows,
        # Jobs the window cannot place. Counted, never folded in: a job
        # with no booking date belongs to no month, and putting it in one
        # would be inventing the fact the record is missing.
        "unbooked": {
            "count": len(unbooked),
            "margin": sum(row["margin"] for row in unbooked),
            "jobs": unbooked,
        },
    }


def coverage_pct(margin, overhead):
    """How much of a month's upkeep its booked work covered, as a percent.

    None when there was no upkeep to cover. A month the company spent
    nothing on itself was not covered 0% - it had nothing to cover, and 0
    would read as the opposite of what happened. The same rule
    `reporting.margin_pct` uses for a job quoted at nothing.
    """
    if not overhead:
        return None
    return margin_pct(margin, overhead)


def _month(key: str, earned: Row, spent: Row) -> dict:
    margin = int(earned.get("margin") or 0)
    final = int(earned.get("final_margin") or 0)
    upkeep = int(spent.get("total") or 0)
    return {
        "month": key,
        "overhead": upkeep,
        # Carried through so the month a camera was bought reads as the
        # month a camera was bought rather than as a month that fell
        # apart. Outside the line above, beside it rather than inside it.
        "flagged_overhead": int(spent.get("flagged_total") or 0),
        "overhead_count": int(spent.get("count") or 0),
        "contribution": margin,
        "final_contribution": final,
        "provisional_contribution": int(earned.get("provisional_margin") or 0),
        "job_count": int(earned.get("job_count") or 0),
        "final_count": int(earned.get("final_count") or 0),
        # The whole point of the screen, signed: below zero the month's
        # work did not pay for the month.
        "surplus": margin - upkeep,
        # The same question asked of the half that cannot move. A month
        # can be in surplus on everything it booked and in shortfall on
        # everything it has finished, and those are different facts.
        "final_surplus": final - upkeep,
        "coverage_pct": coverage_pct(margin, upkeep),
        "covered": margin >= upkeep,
    }


def _total(contributions: Mapping[str, Any], overhead: Mapping[str, Any]) -> dict:
    """The range as one row.

    Summed from the two blocks' own totals rather than from the months
    above, so the range figure is the upstream module's figure and not a
    second addition of it. The months add to the same number - both sides
    fold one pass over one set of rows - and the test suite pins that they
    do rather than trusting that they will.
    """
    margin = int(contributions.get("margin_total") or 0)
    final = int(contributions.get("final_total") or 0)
    upkeep = int(overhead.get("paid_total") or 0)
    flagged = int((overhead.get("flagged") or {}).get("total") or 0)
    return {
        "overhead": upkeep,
        "flagged_overhead": flagged,
        "overhead_count": int(overhead.get("count") or 0),
        "contribution": margin,
        "final_contribution": final,
        "provisional_contribution": int(contributions.get("provisional_total") or 0),
        "job_count": int(contributions.get("job_count") or 0),
        "final_count": int(contributions.get("final_count") or 0),
        "surplus": margin - upkeep,
        "final_surplus": final - upkeep,
        "coverage_pct": coverage_pct(margin, upkeep),
        "covered": margin >= upkeep,
    }


def break_even(contributions: Mapping[str, Any], overhead: Mapping[str, Any]) -> dict:
    """The two sides against each other, month by month and over the range.

    Composed from the two blocks above rather than from the rows
    underneath them, so this screen's August overhead is the tax card's
    August overhead and this screen's job margin is the reports screen's
    job margin. A figure computed twice is a figure that will eventually
    be two figures.

    **Shortfall and surplus are one signed number, not two fields.**
    Contribution less overhead: negative is the shortfall, positive the
    surplus. Two fields would let a caller print both, and a screen
    showing a shortfall of 0 beside a surplus of 0 says nothing twice.

    The months are the union of the two sides' months, which - both being
    built from the same range - is the range's months. Kept as a union
    rather than as either side's list, so a month present on one side
    only still appears with the other side at zero.
    """
    overhead_months = {row["month"]: row for row in overhead.get("by_month", [])}
    margin_months = {row["month"]: row for row in contributions.get("by_month", [])}

    months = [
        _month(key, margin_months.get(key) or {}, overhead_months.get(key) or {})
        for key in sorted(set(overhead_months) | set(margin_months))
    ]

    return {
        "contribution_basis": contributions.get("basis"),
        "overhead_basis": overhead.get("basis"),
        "months": months,
        "total": _total(contributions, overhead),
        # The work behind the line, carried through rather than left for
        # a second call. A founder looking at a shortfall asks which jobs
        # made it immediately, and a screen that had to ask again could
        # get a different answer than the months above were built from.
        "jobs": list(contributions.get("jobs") or []),
        # And the ones no month could place, so a job with no booking
        # date is visible rather than merely absent from a total.
        "unbooked": dict(contributions.get("unbooked") or {}),
        # What the company spent on itself that is not a running cost,
        # over the range. Beside the line, never inside it, and never
        # invisible - an invisible subtraction cannot be checked against
        # anything.
        "flagged": dict(overhead.get("flagged") or {}),
        "by_category": list(overhead.get("by_category") or []),
        "caveats": CAVEATS,
    }

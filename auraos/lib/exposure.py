"""No-invoice exposure: the tax the company owes because it has no paper.

Framework-free by contract like the rest of auraos/lib. A cost line of
type Không hoá đơn is money handed over with nothing to deduct it
against, so the company's taxable profit is higher by that amount and it
owes TNDN on it. That cost is real the day the money leaves and it stays
real until a replacement invoice arrives; until then it is carried in
somebody's head. This module is the number.

**The exposure is derived, never stored.** Nothing here writes anything,
and there is deliberately no field on any doctype holding a total. A
stored exposure is a figure that can be edited into an opinion, and the
first time it disagrees with the lines underneath it, the lines are
right and the tile is a liability.

**The rate is auraos.lib.pricing's, not this module's.** TNDN_RATE is
already what the founder profit chain computes with. Two copies of a tax
rate is a defect waiting for the rate to change, so this imports the one
that exists rather than declaring a second 20%.

**Uncovered is the safe default.** A line whose replacement status
nobody has recorded reads as still exposed, never as covered. The
unrecorded direction has to be the one that keeps the number honest -
the opposite default would quietly shrink the founder's tax bill on a
screen and not on a filing.

**Rounding is per part, before the parts are added**, as everywhere else
in this app, so a printed total is exactly the sum of its printed rows
and the tax is computed on the rounded base rather than the other way
round.

The caller decides what a row's `amount` is and whether it is covered -
this module does not know where a replacement status is kept, and is
deliberately written so that it does not have to.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, Mapping

from auraos.lib.finance import as_date, month_key
from auraos.lib.money import round_vnd
from auraos.lib.money import to_decimal as _d
from auraos.lib.pricing import TNDN_RATE, TaxType
# The cash a cost line is expected to hand over, borrowed rather than
# rewritten. auraos.lib.settlement already owns that formula and the
# job's money screen already prints it; a second copy here would be a
# second opinion about the same đồng the first time one of them changed.
from auraos.lib.settlement import handed_over

Row = Mapping[str, Any]

# What the tile is measured on, carried in the payload for the same
# reason auraos.lib.finance carries its basis: the screen says it out
# loud and the two have to be the same claim.
TNDN_BASIS = "no-invoice cost with no replacement invoice on file"


def is_no_invoice(line: Row) -> bool:
    """Whether a cost line is the kind that carries exposure at all.

    Read off the line's own tax type, matched the way the pricing engine
    matches it, so this and the price cannot disagree about which lines
    have no invoice behind them.
    """
    try:
        return TaxType.parse(line.get("tax_type") or "") is TaxType.KHONG_HOA_DON
    except (ValueError, KeyError):
        return False


def coverage(expenses: Iterable[Row]) -> dict[str, dict]:
    """Which cost lines have a replacement invoice, keyed by line.

    An expense names the line it covers; this folds the expenses into
    one entry per line. **Many expenses may cover one line** - a
    replacement invoice can arrive split across two receipts, and
    refusing the second one would send somebody to edit the first.

    The covering total is carried alongside the count because a 10 triệu
    line covered by a 2 triệu invoice is not the same news as one
    covered in full, and a binary status alone cannot say so.
    """
    covered: dict[str, dict] = {}
    for row in expenses:
        line = row.get("covers_cost_line")
        if not line:
            continue
        entry = covered.setdefault(line, {"count": 0, "total": Decimal(0), "expenses": []})
        entry["count"] += 1
        entry["total"] += _d(row.get("amount") or 0)
        entry["expenses"].append(row.get("name"))
    return covered


def exposure_rows(
    cost_lines: Iterable[Row],
    expenses: Iterable[Row],
    *,
    job: Any = None,
    job_title: Any = None,
) -> list[dict]:
    """One job's no-invoice lines, each with its coverage resolved.

    The status is derived here and stored nowhere. A line is covered
    when an expense says it covers it, and the only way to change that
    is to record or unrecord the expense - so the status cannot drift
    from the paperwork, because it *is* the paperwork.

    Lines that were never Không hoá đơn are not in the answer at all:
    they had an invoice from the start and there is nothing to replace.
    """
    covered = coverage(expenses)
    rows = []
    for line in cost_lines:
        if not is_no_invoice(line):
            continue
        cover = covered.get(line.get("name")) or {}
        rows.append(
            {
                "job": job,
                "job_title": job_title,
                "line": line.get("name"),
                "description": line.get("description"),
                "amount": round_vnd(handed_over(line)),
                "covered": bool(cover),
                # Every covering expense, not the first of them. A line
                # covered by two receipts named after one of them is a
                # partial truth, and the screen has to be able to show
                # the reader all the paper that answers for it.
                "covering_expenses": list(cover.get("expenses") or []),
                "covering_count": cover.get("count") or 0,
                "covering_total": round_vnd(cover.get("total") or 0),
            }
        )
    return rows


def tndn_on(amount: Any, rate: Any = TNDN_RATE) -> int:
    """The tax owed on an undeductible amount, in whole đồng.

    Computed on the rounded base, so the tax printed beside a total is
    the tax on the total as printed rather than on a hidden fraction of
    a đồng nobody can see.
    """
    return round_vnd(_d(round_vnd(amount)) * _d(rate))


def is_covered(row: Row) -> bool:
    """Whether a replacement invoice is on file for this line.

    True only when the row says so. A row that says nothing is exposed:
    see the module docstring on why the unrecorded direction has to fall
    this way.
    """
    return bool(row.get("covered"))


def exposure_report(
    rows: Iterable[Row],
    *,
    rate: Any = TNDN_RATE,
    by_month: bool = False,
) -> dict:
    """Uncovered no-invoice cost and the TNDN it exposes the company to.

    `rows` are no-invoice cost lines the caller has already priced and
    already decided the covered state of. Each carries an `amount`, a
    `covered` flag, and whatever identifying fields the screen wants to
    print back - `job`, `job_title`, `description` are passed through
    untouched.

    Covered lines are counted separately rather than dropped. "Nothing
    is uncovered" and "there was never any no-invoice spend" are very
    different pieces of news, and a tile that cannot tell them apart
    reads as the good one on a studio that simply has not started.

    `by_month` groups the uncovered rows by the month of their
    `spent_on`. Off by default: a cost line has no date of its own, and
    an exposure is carried until the paper arrives rather than falling
    in a month - the same reading auraos.lib.finance.receivables_report
    takes when it says what is owed is owed today. The caller turns it
    on only when it has a real date to group by, and a row with no date
    lands in `undated` rather than being dropped or being guessed into
    the current month.
    """
    lines = [_line(row) for row in rows]
    uncovered = [line for line in lines if not line["covered"]]
    covered = [line for line in lines if line["covered"]]

    total = sum(line["amount"] for line in uncovered)
    report = {
        "basis": TNDN_BASIS,
        "rate_pct": float(_d(rate) * 100),
        "uncovered_total": total,
        "tndn_exposure": tndn_on(total, rate),
        "uncovered_count": len(uncovered),
        "covered_total": sum(line["amount"] for line in covered),
        "covered_count": len(covered),
        "lines": uncovered,
    }
    if by_month:
        report["months"] = _months(uncovered, rate)
    return report


def _line(row: Row) -> dict:
    """One no-invoice line as the tile reads it, money rounded once."""
    return {
        "job": row.get("job"),
        "job_title": row.get("job_title"),
        "description": row.get("description"),
        "amount": round_vnd(row.get("amount") or 0),
        "covered": is_covered(row),
        "covering_expenses": list(row.get("covering_expenses") or []),
        "covering_count": row.get("covering_count") or 0,
        "covering_total": round_vnd(row.get("covering_total") or 0),
        "line": row.get("line"),
        "spent_on": _iso(row.get("spent_on")),
    }


def _months(lines: Iterable[dict], rate: Any) -> list[dict]:
    """Uncovered exposure grouped by the month the money went out.

    Only the months that have something in them: unlike a profit and
    loss, this is not a run along a range the caller chose, so an empty
    month here would be a month nobody asked about.
    """
    buckets: dict[str, list[dict]] = {}
    for line in lines:
        day = as_date(line["spent_on"])
        buckets.setdefault(month_key(day) if day else UNDATED, []).append(line)

    rows = [_month(key, buckets[key], rate) for key in sorted(buckets)]
    # Lines nobody has dated sort last rather than first, where a "u"
    # would otherwise put them among the years.
    rows.sort(key=lambda row: (row["month"] == UNDATED, row["month"]))
    return rows


# Where a line whose money has no recorded date goes. Named, not
# dropped: an exposure with no date is still an exposure, and a tile
# that hid it would understate the bill.
UNDATED = "undated"


def _month(key: str, lines: list[dict], rate: Any) -> dict:
    total = sum(line["amount"] for line in lines)
    return {
        "month": key,
        "uncovered_total": total,
        "tndn_exposure": tndn_on(total, rate),
        "count": len(lines),
    }


def _iso(value: Any) -> str | None:
    day = as_date(value)
    return day.isoformat() if day is not None else None

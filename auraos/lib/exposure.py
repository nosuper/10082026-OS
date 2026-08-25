"""No-invoice exposure: the tax the company owes because it has no paper.

Framework-free by contract like the rest of auraos/lib.

**Exposure is money that moved, never money that was planned.** A
`Không hoá đơn` cost line is a plan to spend without an invoice, and a
plan creates no liability - the company owes TNDN when it has actually
paid out something it cannot deduct. An earlier version of this module
read the cost lines and taxed the quote, which reported a liability on
meals that were priced and never bought, and missed the parking and
coffee that were actually paid for. It was a plausible number on a
dashboard beside figures that are facts, which is the worst kind.

**The tax treatment lives on the plan, the money lives on the expense,
and the link carries one to the other.** An expense names the quoted
line it spends against; if that line is `Không hoá đơn`, the money that
expense records is exposed. Nothing is duplicated onto the expense, and
the person logging spending on a phone picks a line rather than
answering a question about invoices.

**An expense that names no line counts as exposed until somebody says
otherwise.** The founder chose this over leaving it out, and their
reason decides it: **understating is the error that costs money at an
audit.** A tile that omits unattributed cash tells the company it is
clean when nobody has looked.

It is still reported apart from spending whose treatment is on record,
because "we know this had no invoice" and "nobody has said yet" are
different degrees of knowledge, and a founder deciding what to chase
needs to tell them apart. **Attributing an expense moves it out of the
assumed half**, so the figure falls as the work gets done - which makes
the tile a prompt rather than a verdict.

**Covered means an invoice was obtained, and it is recorded, not
derived.** A replacement invoice is paper, not money: it answers for
spending that already happened. Recording it as a second expense - which
is what #11 did - adds its amount to the job's cost and posts a ledger
entry for money that never moved.

**The rate is auraos.lib.pricing's**, the same TNDN_RATE the founder
profit chain computes with. Two copies of a tax rate is a defect waiting
for the rate to change.

Rounding is per part before the parts are added, so a printed total is
exactly the sum of its printed rows.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from auraos.lib.finance import as_date, month_key
from auraos.lib.money import round_vnd
from auraos.lib.money import to_decimal as _d
from auraos.lib.pricing import TNDN_RATE, TaxType

Row = Mapping[str, Any]

# What the tile is measured on, carried in the payload for the same
# reason auraos.lib.finance carries its basis: the screen says it out
# loud and the two have to be the same claim.
#
# It names **both** halves on purpose. An earlier draft of this string
# read "money paid out against a no-invoice line", which was true of the
# stated half and silent about the assumed one - so the screen would
# have declared a basis narrower than the number beside it. That is the
# defect this whole module was rewritten for, in one line of prose: the
# figure was not wrong, the sentence over it was.
TNDN_BASIS = (
    "money paid out with no invoice on file: against a no-invoice line, "
    "or not yet attributed to any line"
)

# How a payment came to be counted. On every row, because the founder's
# breakdown separates what is established from what is merely assumed,
# and a caller should not have to re-derive that from a null.
STATED = "stated"
UNATTRIBUTED = "unattributed"


def is_no_invoice(line: Row | None) -> bool:
    """Whether a quoted line is the kind that carries exposure.

    Read off the line's own tax type, matched the way the pricing engine
    matches it, so this and the price cannot disagree about which lines
    have no invoice behind them. No line at all is not a no-invoice
    line - it is an unstated treatment, which is a different thing.
    """
    if not line:
        return False
    try:
        return TaxType.parse(line.get("tax_type") or "") is TaxType.KHONG_HOA_DON
    except (ValueError, KeyError):
        return False


def has_invoice(expense: Row) -> bool:
    """Whether paper was obtained for this spend."""
    return bool(str(expense.get("invoice_no") or "").strip())


def exposure_rows(
    expenses: Iterable[Row],
    lines: Mapping[str, Row],
    *,
    jobs: Mapping[str, Any] | None = None,
) -> list[dict]:
    """Spending that carries tax exposure, one row per payment.

    `expenses` are Job Expenses carrying `amount`, `spent_on`,
    `cost_line`, `invoice_no` and the job they are on. `lines` maps a
    cost line name to that line, so this can read its tax type without
    knowing how the caller fetched it.

    Two ways in, and every row says which:

    - **stated** - it spends against a quoted line marked Không hoá đơn,
      so the treatment is on record.
    - **unattributed** - it names no quoted line at all, so nobody has
      said what it is. Counted as exposed, because the founder chose the
      safe direction and the unsafe one is the expensive one.

    A payment against a line that *does* carry an invoice is not here at
    all. That is the one case where naming a line takes money out of the
    figure, and it is why attributing spending makes the number fall.
    """
    jobs = jobs or {}
    rows = []
    for expense in expenses:
        named = expense.get("cost_line")
        line = lines.get(named) if named else None
        if named and line is not None and not is_no_invoice(line):
            # Attributed to a line that came with its paper.
            continue
        if named and line is None:
            # The link points at a line nobody can find, so it states
            # nothing. Under the founder's rule that is spending nobody
            # has accounted for, not spending proved safe.
            named = None
        job = expense.get("job")
        rows.append(
            {
                "expense": expense.get("name"),
                "job": job,
                "job_title": jobs.get(job),
                "line": named or None,
                "treatment": STATED if named else UNATTRIBUTED,
                "description": (
                    expense.get("description")
                    or (line or {}).get("description")
                    or expense.get("category")
                ),
                "amount": round_vnd(expense.get("amount") or 0),
                "spent_on": _iso(expense.get("spent_on")),
                "covered": has_invoice(expense),
                "invoice_no": (expense.get("invoice_no") or "") or None,
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


def exposure_report(
    rows: Iterable[Row],
    *,
    rate: Any = TNDN_RATE,
    by_month: bool = False,
) -> dict:
    """What the company is carrying, and the TNDN it exposes it to.

    The headline counts both halves. The breakdown keeps them apart, so
    the founder can see how much of their own number is established and
    how much is an assumption waiting to be resolved.
    """
    lines = list(rows)
    uncovered = [row for row in lines if not row.get("covered")]
    covered = [row for row in lines if row.get("covered")]
    stated = [row for row in uncovered if row.get("treatment") == STATED]
    assumed = [row for row in uncovered if row.get("treatment") == UNATTRIBUTED]

    total = sum(row["amount"] for row in uncovered)
    report = {
        "basis": TNDN_BASIS,
        "rate_pct": float(_d(rate) * 100),
        "uncovered_total": total,
        "tndn_exposure": tndn_on(total, rate),
        "uncovered_count": len(uncovered),
        # The two halves of that headline: spending whose treatment is
        # on record, and spending nobody has pointed at a line yet.
        "stated_total": sum(row["amount"] for row in stated),
        "stated_count": len(stated),
        "unattributed_total": sum(row["amount"] for row in assumed),
        "unattributed_count": len(assumed),
        "covered_total": sum(row["amount"] for row in covered),
        "covered_count": len(covered),
        "lines": uncovered,
    }
    if by_month:
        report["months"] = _months(uncovered, rate)
    return report


def _months(lines: Iterable[dict], rate: Any) -> list[dict]:
    """Uncovered exposure grouped by the month the money went out.

    Every expense carries a date, so unlike the quoted lines this
    replaces, a month is always a real answer rather than a guess.
    """
    buckets: dict[str, list[dict]] = {}
    for line in lines:
        day = as_date(line.get("spent_on"))
        buckets.setdefault(month_key(day) if day else UNDATED, []).append(line)

    rows = [_month(key, buckets[key], rate) for key in sorted(buckets)]
    rows.sort(key=lambda row: (row["month"] == UNDATED, row["month"]))
    return rows


# An expense with no spent_on should not exist - the field is how money
# gets into a month - but a row that lost its date is still money out,
# and hiding it would understate the bill.
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

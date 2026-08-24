"""What the company owes for a period, and what it cannot work out yet.

Framework-free by contract like the rest of auraos/lib.

**This module deliberately computes half of a tax position.** #109 asked
for TNDN and VAT on a period. VAT is here. TNDN is not, and the reason is
a fact about the data rather than a shortage of effort:

**TNDN is not a tax on revenue.** It is a tax on profit - revenue less
deductible costs - and `Job Expense.job` is `reqd`, with no other expense
doctype in the app. Every cost AuraOS can see belongs to a job. Rent,
salaries, software and the accountant's own fee cannot be recorded at
all, so a TNDN figure computed from these tables is
`rate x (revenue - job costs)`: it omits every overhead and therefore
**overstates the tax, in one direction, plausibly.** The founder's
guidebook already refuses that number in as many words - better an empty
tile than one showing a figure that looks right and nobody can reproduce
- and a figure that would be *filed* is the worst version of it.

So what is here is what can be stated as fact, and the gap is part of the
payload rather than a silence for a screen to fill.

**Output VAT is dated by the invoice, and that is statute rather than a
preference.** Every other figure in Finance is cash basis and says so on
its face; this one cannot be. Output VAT falls due when the invoice is
issued, so the period a milestone belongs to is the period its
`invoiced_on` falls in, whatever month the money arrives in. A tile that
did not say this beside the number would be inviting the reader to
reconcile it against an income figure it will not match.

**The rate is the one the invoice was written at**, never today's.
`invoice_vat_pct` is captured once, when `invoiced_on` is first written,
precisely so an issued invoice keeps its own rate - see
`auraos.lib.milestones.vat_basis`. Reading a past period at the current
rate would restate invoices the client is already holding.

**Broken out by rate, because that is how it is filed.** A period can
carry 10%, 8% and 0% invoices at once - an export invoice is genuinely
written at zero - and one summed figure cannot be checked against a
return. Rounding is per invoice before the parts are added, so a printed
total is exactly the sum of its printed rows.

**Nothing here is stored.** A tax figure is derived on every read, from
the invoice dates and rates the milestones already carry. The one value
that is stored is `invoice_vat_pct`, and it is stored because it is a
historical fact about a document rather than a cached derivation.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from auraos.lib.finance import as_date, month_key, month_keys
from auraos.lib.milestones import invoice_split
from auraos.lib.money import round_vnd

Row = Mapping[str, Any]

OVERHEAD_BASIS = (
    "what the company paid for its own upkeep, dated by the day the money "
    "left the account"
)

INPUT_VAT_BASIS = (
    "VAT on invoices the company was given, dated by the day each invoice "
    "was issued - the same rule as output VAT, and not all the input VAT "
    "there is"
)

VAT_BASIS = (
    "output VAT on invoices issued in the period, dated by the day the "
    "invoice was issued rather than the day the money arrived"
)

# Said in the payload rather than left to the screen, because the screen
# that has to explain an absence is the one most likely to explain it
# wrongly - and because this list shrinks as tickets land, which makes it
# a fact about the data that belongs beside the data.
NOT_COMPUTED = [
    {
        "figure": "input VAT on job spending",
        "why": (
            "an overhead records the VAT on its invoice, but a job expense "
            "has no VAT fields at all - so the input VAT here is the "
            "company's own upkeep and not everything the company could "
            "deduct"
        ),
    },
    {
        "figure": "VAT payable",
        "why": (
            "output VAT less all input VAT, and half the input VAT - the "
            "job side - is still unrecorded"
        ),
    },
    {
        "figure": "TNDN for the period",
        "why": (
            "whether a purchase is expensed now or depreciated over years "
            "is the accountant's judgement, and they may reclassify what is "
            "flagged here - so the deductible total below is what this app "
            "can see, not a taxable base"
        ),
    },
]


def invoiced_rows(milestones: Iterable[Row], date_from: Any, date_to: Any) -> list[dict]:
    """The invoices issued in a window, one row each.

    The window is applied here rather than trusted from the caller, for
    the reason `finance.income_report` gives about its month boundary: a
    rule this module owns cannot disagree with a filter somebody wrote
    once in SQL.

    A milestone carries `invoiced_on` exactly while it is at đã xuất HĐ
    or past it - `milestones.stamps_for` clears the date, the number and
    the rate together when a status walks back before that step - so
    "has an issue date" is the same question as "has an invoice", and
    this needs no status filter of its own.
    """
    start, end = as_date(date_from), as_date(date_to)
    rows = []
    for row in milestones:
        issued = as_date(row.get("invoiced_on"))
        if not issued or start is None or end is None:
            continue
        if issued < start or issued > end:
            continue
        amount = round_vnd(row.get("amount") or 0)
        rate = row.get("invoice_vat_pct")
        split = invoice_split(amount, rate)
        rows.append(
            {
                "milestone": row.get("name"),
                "job": row.get("parent"),
                "job_title": row.get("job_title"),
                "title": row.get("title"),
                "invoice_no": row.get("invoice_no") or None,
                "invoiced_on": issued,
                "month": month_key(issued),
                # Nought is a rate, not a blank. An export invoice is
                # written at 0% and a milestone nobody invoiced has no
                # row here at all, so there is no second kind of nothing
                # for this field to mean.
                "vat_pct": float(rate or 0),
                "gross": amount,
                "net": split.net,
                "vat": split.vat,
            }
        )
    rows.sort(key=lambda one: (one["invoiced_on"], one["milestone"] or ""))
    return rows


def output_vat(rows: Iterable[Row]) -> dict:
    """Output VAT for a period, and the rates it is made of.

    The by-rate breakdown is not a nicety: a VAT return is filed per
    rate, and a single total cannot be checked against one.
    """
    lines = list(rows)
    by_rate: dict[float, dict] = {}
    for line in lines:
        bucket = by_rate.setdefault(
            line["vat_pct"],
            {"vat_pct": line["vat_pct"], "gross": 0, "net": 0, "vat": 0, "count": 0},
        )
        bucket["gross"] += line["gross"]
        bucket["net"] += line["net"]
        bucket["vat"] += line["vat"]
        bucket["count"] += 1

    return {
        "basis": VAT_BASIS,
        "gross_total": sum(line["gross"] for line in lines),
        "net_total": sum(line["net"] for line in lines),
        "vat_total": sum(line["vat"] for line in lines),
        "count": len(lines),
        "by_rate": [by_rate[key] for key in sorted(by_rate)],
        "lines": lines,
    }


def overheads(expenses: Iterable[Row], date_from: Any, date_to: Any) -> dict:
    """What the company paid for its own upkeep in a window.

    **One derivation, N renderings.** This is the single place overheads
    are totalled and grouped. #14's break-even screen shows the same
    numbers against booked margin, and when it is built it must render
    *this block* rather than recompute it from the same table - two
    functions summing one set of rows is how two screens come to
    disagree, and the disagreement always surfaces in front of whoever
    is reconciling.

    **Payment-dated, and that is a different basis from the VAT blocks
    beside it.** AuraOS records the day money left the account; an
    accountant recognises a cost on their own basis. One basis per
    figure and every basis written on its face is the rule - uniformity
    was never the requirement, silence about it was the danger.

    **Grouped by category because a return is**, and an uncategorised
    payment gets its own bucket rather than being dropped: `category` is
    optional on the record for the same reason it is optional on a job
    expense - money gets spent on things nobody has classified yet, and
    a row called Uncategorised is far better than pretending it was not
    spent.

    **Flagged purchases are listed, not merely subtracted.** The founder
    wants to hold the accountant's return beside this and check it line
    by line; an invisible subtraction cannot be checked against
    anything.

    **Broken out by month as well as by category, because break-even is
    a monthly question.** A tax return reads a period whole; #14 asks
    whether *this month's* work covered *this month's* upkeep, and a
    range total cannot answer that. The two views are folds of one pass
    over one set of rows, which is what keeps them from disagreeing -
    `sum(month["total"] for month in by_month)` is `paid_total` by
    construction rather than by luck, and the same holds for the flagged
    side.

    **A month the range touches is a month here, even if nothing was
    paid in it.** The caller cannot know which months are missing
    without the range, and a break-even chart with an empty August
    quietly absent reads as a shorter year rather than a month that took
    nothing - the rule `finance.month_keys` already owns for income
    against expense.
    """
    start, end = as_date(date_from), as_date(date_to)
    deductible: dict[Any, dict] = {}
    flagged = []
    paid_total = 0
    months = {
        key: {"month": key, "total": 0, "count": 0, "flagged_total": 0}
        for key in month_keys(date_from, date_to)
    }
    for row in expenses:
        paid = as_date(row.get("spent_on"))
        if not paid or start is None or end is None:
            continue
        if paid < start or paid > end:
            continue
        amount = round_vnd(row.get("amount") or 0)
        line = {
            "expense": row.get("name"),
            "spent_on": paid,
            "month": month_key(paid),
            "category": row.get("category") or None,
            "description": row.get("description") or None,
            "amount": amount,
        }
        # A row inside the window is inside one of the window's months by
        # definition; the setdefault is here so a caller passing a
        # half-open range cannot make this raise instead of answering.
        month = months.setdefault(
            line["month"],
            {"month": line["month"], "total": 0, "count": 0, "flagged_total": 0},
        )
        if row.get("for_depreciation"):
            flagged.append(line)
            month["flagged_total"] += amount
            continue
        paid_total += amount
        month["total"] += amount
        month["count"] += 1
        bucket = deductible.setdefault(
            line["category"], {"category": line["category"], "total": 0, "count": 0}
        )
        bucket["total"] += amount
        bucket["count"] += 1

    flagged.sort(key=lambda one: (one["spent_on"], one["expense"] or ""))
    return {
        "basis": OVERHEAD_BASIS,
        "paid_total": paid_total,
        "count": sum(bucket["count"] for bucket in deductible.values()),
        # In reading order, unlike by_category: months are a sequence and
        # sorting them by size would turn a run of the company's upkeep
        # into a league table.
        "by_month": [months[key] for key in sorted(months)],
        # Biggest first: a founder checking a return reads down from the
        # line most likely to be wrong about real money.
        "by_category": sorted(
            deductible.values(), key=lambda one: (-one["total"], str(one["category"] or ""))
        ),
        "flagged": {
            "total": sum(line["amount"] for line in flagged),
            "count": len(flagged),
            "lines": flagged,
        },
    }


def input_vat(expenses: Iterable[Row], date_from: Any, date_to: Any) -> dict:
    """The VAT on invoices the company was given in a window.

    **Dated by the invoice, like output VAT**, because that is the rule
    for both and dating one by payment would put two bases inside one
    figure.

    **Flagged purchases count here.** How a cost is treated for TNDN and
    whether its VAT is deductible are different questions with different
    answers, and excluding a depreciated purchase's VAT because it is
    excluded from the cost block would be tidiness overriding the tax.

    **The amount is the supplier's, never derived.** They wrote the
    invoice; reconstructing their VAT line by division can land a đồng
    from the paper the accountant is holding, and this figure exists to
    be checked against exactly that paper.
    """
    start, end = as_date(date_from), as_date(date_to)
    lines = []
    for row in expenses:
        vat = round_vnd(row.get("invoice_vat_amount") or 0)
        issued = as_date(row.get("invoice_date"))
        if not vat or not issued or start is None or end is None:
            continue
        if issued < start or issued > end:
            continue
        lines.append(
            {
                "expense": row.get("name"),
                "invoice_no": row.get("invoice_no") or None,
                "invoice_date": issued,
                "supplier": row.get("supplier") or None,
                "vat": vat,
            }
        )
    lines.sort(key=lambda one: (one["invoice_date"], one["expense"] or ""))
    return {
        "basis": INPUT_VAT_BASIS,
        "vat_total": sum(line["vat"] for line in lines),
        "count": len(lines),
        "lines": lines,
    }


def position(
    vat: Mapping[str, Any],
    exposure: Mapping[str, Any] | None = None,
    overhead: Mapping[str, Any] | None = None,
    inputs: Mapping[str, Any] | None = None,
) -> dict:
    """The period's tax position, as much of it as exists.

    **The two halves are not measured over the same thing and the payload
    says so.** The VAT figure is what was invoiced inside the window. The
    exposure figure is what the company is carrying *now* - an uncovered
    payment is carried from the day it was made until an invoice turns
    up, so it has no period at all (`api.no_invoice_exposure` takes no
    range for the same reason). Adding them, or drawing them as two bars
    on one axis, would be a category error that a reader cannot see.

    The exposure half is a **component** of a TNDN position and never a
    position: it is the tax on spending that cannot be deducted, which is
    one input to a number this module deliberately does not compute.
    """
    return {
        "vat": dict(vat),
        # Kept in named branches rather than flattened, so nothing can
        # total two figures that were measured over different things.
        "input_vat": dict(inputs) if inputs is not None else None,
        "overheads": dict(overhead) if overhead is not None else None,
        # A component, labelled, or omitted entirely rather than sent as
        # a zero - "no exposure" and "not asked for" are different, and a
        # zero would read as the first.
        "tndn_component": (
            {
                "standing": True,
                "of": "spending with no invoice, which cannot be deducted",
                **dict(exposure),
            }
            if exposure is not None
            else None
        ),
        "not_computed": NOT_COMPUTED,
    }

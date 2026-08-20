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

from auraos.lib.finance import as_date, month_key
from auraos.lib.milestones import invoice_split
from auraos.lib.money import round_vnd

Row = Mapping[str, Any]

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
        "figure": "input VAT",
        "why": (
            "an expense records an amount and, at most, an invoice number - "
            "no VAT amount and no rate - so there is nothing to deduct from "
            "output VAT"
        ),
    },
    {
        "figure": "VAT payable",
        "why": "output VAT less input VAT, and input VAT is not recorded",
    },
    {
        "figure": "TNDN for the period",
        "why": (
            "TNDN is charged on profit, and every expense in AuraOS belongs "
            "to a job - overheads are not recordable, so any figure here "
            "would omit them and overstate the tax"
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


def position(vat: Mapping[str, Any], exposure: Mapping[str, Any] | None = None) -> dict:
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

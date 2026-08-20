"""What a client still owes when a job is settled (#153).

The acceptance document's summary table, as arithmetic. Five columns per
band - contracted, settled, difference, collected, remaining - and three
bands: pre-VAT, VAT, and the total.

**This is revenue, not cost.** "Settled" is the revised value we are
billing the client, not what the job cost us to produce. The two are
different quantities with different owners, and putting a cost where a
settled value belongs would both demand the wrong amount and print our
margin on a page the client signs. The document's own columns say which
it means: "Thành tiền (HĐ gốc)" against "Giá trị thanh lý (thực tế)".

**Every figure refuses rather than guesses.** A remaining balance that
prints 0 is a document saying nothing is owed, and it gets signed. One
that prints a visible gap does not. So `None` propagates: a band whose
settled value is unknown has no difference and no remaining, and says so
instead of treating the unknown as zero.

The one place zero is a real answer is collections. A client who has
paid nothing has collected zero and owes the whole settled value, and
that is a fact rather than an absence - which is why `collected` is
distinguished from `None` here rather than being defaulted.

Framework-free: this is money on a signed page, and it should be
readable and testable without a site.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

#: The three rows the summary table states, in the document's order.
BANDS = ("pre_vat", "vat", "total")


def _amount(value: Any) -> Decimal | None:
    """A figure, or None for anything that is not one.

    Blank, missing and unparseable all become None rather than zero,
    because the whole point of this module is that those are different.
    """
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def band(contracted: Any, settled: Any, collected: Any) -> dict[str, Decimal | None]:
    """One row of the table: what was agreed, what it became, what is left.

    `difference` is settled minus contracted, so an overrun is positive
    and an underrun negative. The sign is the document's meaning, not a
    display choice: "chênh lệch" of +2.000.000 and -2.000.000 are
    opposite sentences about who owes whom more than they expected.

    `remaining` is settled minus collected - what the client still owes
    against the settled value, not against the original. Billing the
    contracted figure after a scope reduction would demand money the
    settlement just agreed to drop.
    """
    contracted_amount = _amount(contracted)
    settled_amount = _amount(settled)
    collected_amount = _amount(collected)

    difference = (
        settled_amount - contracted_amount
        if settled_amount is not None and contracted_amount is not None
        else None
    )
    remaining = (
        settled_amount - collected_amount
        if settled_amount is not None and collected_amount is not None
        else None
    )
    return {
        "contracted": contracted_amount,
        "settled": settled_amount,
        "difference": difference,
        "collected": collected_amount,
        "remaining": remaining,
    }


def summary(
    contracted: Mapping[str, Any] | None = None,
    settled: Mapping[str, Any] | None = None,
    collected: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Decimal | None]]:
    """The whole table, one band at a time.

    The bands are computed independently rather than derived from each
    other. It is tempting to make `total` the sum of `pre_vat` and
    `vat`, and it would be wrong the moment one of them is unknown: the
    sum of a number and an absence would either raise or quietly become
    the number, and the second is how a total ends up understating a
    bill by exactly its VAT.
    """
    contracted = contracted or {}
    settled = settled or {}
    collected = collected or {}
    return {
        name: band(contracted.get(name), settled.get(name), collected.get(name))
        for name in BANDS
    }


def refusals(table: Mapping[str, Mapping[str, Any]]) -> tuple[str, ...]:
    """Which figures the table cannot state, named for a person to fix.

    Reported rather than inferred from blanks on the page, because a
    person about to send an acceptance document should be told what is
    missing before they print it, not after the client asks.
    """
    missing = []
    for name in BANDS:
        row = table.get(name) or {}
        if row.get("settled") is None:
            missing.append(f"{name}: no settled value")
        if row.get("contracted") is None:
            missing.append(f"{name}: no contracted value")
        if row.get("collected") is None:
            missing.append(f"{name}: no collection total")
    return tuple(missing)


# -- per line, which is where a settlement actually happens (#153) -----------

def settled_lines(lines, adjustments=None):
    """The contract's lines with their settled values, one row each.

    The founder's rule: "giá trị thanh lý thông thường sẽ là giá trị
    hợp đồng" - normally the settled value IS the contract value, and
    the exceptions are *phát sinh* (work added during the job) and
    *trừ bớt* (items reduced or not performed).

    So settled defaults to contracted per line, and only the rows that
    actually moved are stated. An added row has no contracted value and
    is all difference; a dropped row settles at zero, which is a
    statement rather than an absence and must be given as one.

    **The default is a claim, not an absence, and that is the one
    dangerous thing here.** Everywhere else in this module an unstated
    figure refuses. Here an unstated line asserts "this was delivered as
    agreed" - which is usually true and is what makes the normal case
    free, but it means a reduction nobody recorded prints as a full
    charge rather than as a gap. The protection is not in this function:
    it is that a person sees every line before the document is made.
    """
    rows = []
    moved = {str(k): v for k, v in (adjustments or {}).items()}
    for line in lines or []:
        key = str(line.get("name") or line.get("description") or "")
        contracted = _amount(line.get("amount"))
        settled = _amount(moved[key]) if key in moved else contracted
        rows.append(
            {
                "description": line.get("description"),
                "contracted": contracted,
                "settled": settled,
                "difference": (
                    settled - contracted
                    if settled is not None and contracted is not None
                    else None
                ),
                "added": False,
            }
        )
    return rows


def added_lines(extras):
    """Phát sinh - work that was not in the contract at all.

    Contracted is None rather than zero, deliberately: a zero would say
    "this was agreed at no charge", and the difference column would read
    the same for both. None says nobody agreed it in advance, which is
    what phát sinh means and what the client is being asked to accept.
    """
    rows = []
    for extra in extras or []:
        settled = _amount(extra.get("amount"))
        rows.append(
            {
                "description": extra.get("description"),
                "contracted": None,
                "settled": settled,
                "difference": settled,
                "added": True,
            }
        )
    return rows


def band_from_lines(rows, collected=None):
    """One band totalled from its lines - and only if every line speaks.

    A band whose lines are partly unknown is not the sum of the ones
    that are. Summing what is available and printing it as a total is
    the same defect as deriving the total row from pre-VAT and VAT: a
    figure short by exactly what is missing, indistinguishable from a
    complete one.
    """
    rows = list(rows or [])
    if not rows:
        return band(None, None, collected)
    settled = [r["settled"] for r in rows]
    contracted = [r["contracted"] for r in rows if not r["added"]]
    return band(
        sum(contracted) if all(v is not None for v in contracted) else None,
        sum(settled) if all(v is not None for v in settled) else None,
        collected,
    )

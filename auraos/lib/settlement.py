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

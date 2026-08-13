"""Money out on a job: floats, settlement, and actual against quoted.

Framework-free by contract (T8 / spec #2, stories 30–34); the DocType
controllers and the API are thin adapters over this module. All
arithmetic is exact Decimal - rounding to whole đồng is the caller's
concern (auraos.lib.money.round_vnd).

**The float.** The founder advances cash to whoever is doing the
spending; every expense that person pays out of it hands part of it
back as receipts. What remains is the float - positive while they are
still holding company money, negative once they have covered a
shortfall themselves. Settling records the transfer that puts it back
to zero, so the same job can be advanced, spent and settled again
without the history being rewritten.

Money the company paid directly belongs to no float: it lands in
actual-vs-quoted and moves nobody's float.

**Categories mirror the quote.** An expense's category is one of the
entries the client was quoted - a package, or a cost line quoted on its
own - which is what makes actual-vs-quoted per package fall out with no
extra work. The quoted side is measured in what somebody on the job
actually hands over, never the client-facing price.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable, Mapping

from auraos.lib.money import to_decimal as _d

# Where an expense's money came from.
FROM_ADVANCE = "Advance"  # spent out of a float someone is holding
FROM_COMPANY = "Company"  # the company paid the vendor itself

# Which way a float has to move to close.
RETURN = "Return"  # the holder gives the remainder back
TOP_UP = "Top-up"  # the company reimburses the holder
EVEN = "Even"  # nothing to move

# Where an expense lands when it names no category the quote knows.
UNCATEGORISED = "Uncategorised"

Row = Mapping[str, Any]


@dataclass(frozen=True)
class Float:
    """What one person is holding of the company's money on one job.

    `amount` is the float itself - what they were advanced, less what
    they have spent out of it, less what has already been settled.
    """

    holder: str
    advanced: Decimal
    spent: Decimal
    settled: Decimal
    amount: Decimal
    direction: str


def floats(
    advances: Iterable[Row],
    expenses: Iterable[Row],
    settlements: Iterable[Row] = (),
) -> list[Float]:
    """Every float on a job, one per person, sorted by holder.

    Only expenses paid from an advance touch a float; the rest is the
    company's own spending. Settlements are signed the way the money
    moves: positive when the holder returns cash, negative when the
    company tops them up.
    """
    advanced: dict[str, Decimal] = {}
    spent: dict[str, Decimal] = {}
    settled: dict[str, Decimal] = {}

    for row in advances:
        _add(advanced, row.get("recipient"), row.get("amount"))
    for row in expenses:
        if (row.get("paid_from") or FROM_ADVANCE) == FROM_ADVANCE:
            _add(spent, row.get("paid_by"), row.get("amount"))
    for row in settlements:
        _add(settled, row.get("recipient"), row.get("amount"))

    holders = set(advanced) | set(spent) | set(settled)
    return [_held_by(holder, advanced, spent, settled) for holder in sorted(holders)]


def _add(totals: dict[str, Decimal], key: str, amount: Any) -> None:
    totals[key] = totals.get(key, Decimal(0)) + _d(amount or 0)


def _held_by(holder, advanced, spent, settled) -> Float:
    zero = Decimal(0)
    amount = (
        advanced.get(holder, zero)
        - spent.get(holder, zero)
        - settled.get(holder, zero)
    )
    return Float(
        holder=holder,
        advanced=advanced.get(holder, zero),
        spent=spent.get(holder, zero),
        settled=settled.get(holder, zero),
        amount=amount,
        direction=direction_of(amount),
    )


def float_for(
    holder: str,
    advances: Iterable[Row],
    expenses: Iterable[Row],
    settlements: Iterable[Row] = (),
) -> Float:
    """One person's float, whether or not they are holding anything.

    An empty float is a real answer - "you have nothing of ours" - and
    the screen that asks after every logged expense needs it as often as
    it needs a full one.
    """
    for held in floats(advances, expenses, settlements):
        if held.holder == holder:
            return held
    zero = Decimal(0)
    return Float(
        holder=holder,
        advanced=zero,
        spent=zero,
        settled=zero,
        amount=zero,
        direction=EVEN,
    )


def direction_of(amount: Any) -> str:
    """Which way a float has to move to close."""
    amount = _d(amount)
    if amount > 0:
        return RETURN
    if amount < 0:
        return TOP_UP
    return EVEN


@dataclass(frozen=True)
class CategoryActual:
    """What one quoted entry was expected to cost, and what it has cost."""

    title: str
    quoted: Decimal
    actual: Decimal
    variance: Decimal  # actual − quoted; positive is over the quoted cost


def categories(packages: Iterable[Row], cost_lines: Iterable[Row]) -> list[str]:
    """The categories an expense on this job may carry, in quote order.

    Exactly what the client was offered: the packages, then any cost
    line standing in none of them - the same rule the quote page reads
    (auraos.lib.quote.client_entries). Anything else and actual-vs-quoted
    would have holes in it.
    """
    return list(_quoted_costs(packages, cost_lines))


def category_actuals(
    packages: Iterable[Row],
    cost_lines: Iterable[Row],
    expenses: Iterable[Row],
) -> list[CategoryActual]:
    """Quoted cash-out against money actually spent, per category.

    Every category appears whether or not anything has been spent on it
    - an untouched package is the interesting one during a shoot. An
    expense naming no known category is gathered into one trailing row
    rather than quietly dropped.
    """
    quoted = _quoted_costs(packages, cost_lines)

    actual: dict[str, Decimal] = {}
    for row in expenses:
        title = row.get("category") or UNCATEGORISED
        _add(actual, title if title in quoted else UNCATEGORISED, row.get("amount"))

    rows = [
        _actual_row(title, amount, actual.get(title, Decimal(0)))
        for title, amount in quoted.items()
    ]
    if UNCATEGORISED in actual:
        rows.append(_actual_row(UNCATEGORISED, Decimal(0), actual[UNCATEGORISED]))
    return rows


def _actual_row(title, quoted, actual) -> CategoryActual:
    return CategoryActual(
        title=title, quoted=quoted, actual=actual, variance=actual - quoted
    )


def _quoted_costs(packages, cost_lines) -> dict[str, Decimal]:
    """Cash out expected per category, keyed in quote order.

    A package's quoted cost is its member lines'; a line in no package
    carries its own.

    Per line that is the cost after the vendor management fee, plus the
    VAT on an invoice-bearing one - money somebody on the job hands
    over, which is the same kind of money an expense records. It is
    deliberately *not* the line's profit cost basis: for a freelancer
    that basis is grossed up by the PIT the company remits later
    through its accountant, which nobody logs against a shoot. Comparing
    against it would leave every crew-heavy package reading ~10% under
    for good.
    """
    costs: dict[str, Decimal] = {
        (package.get("title") or ""): Decimal(0) for package in packages
    }
    for line in cost_lines:
        title = line.get("package") or line.get("description") or ""
        costs.setdefault(title, Decimal(0))
        costs[title] += _handed_over(line)
    return costs


def _handed_over(line: Row) -> Decimal:
    """What one cost line is expected to cost in cash paid out."""
    vendor_mf_rate = _d(line.get("vendor_mf_pct") or 0) / 100
    after_vendor_mf = _d(line.get("subtotal") or 0) * (1 + vendor_mf_rate)
    return after_vendor_mf + _d(line.get("input_vat") or 0)


@dataclass(frozen=True)
class Totals:
    """A job's money out at a glance."""

    advanced: Decimal
    spent: Decimal
    quoted: Decimal


def totals(
    advances: Iterable[Row],
    expenses: Iterable[Row],
    categories: Iterable[CategoryActual],
) -> Totals:
    """What the job has handed out, paid out, and expected to pay out."""
    return Totals(
        advanced=_total(row.get("amount") for row in advances),
        spent=_total(row.get("amount") for row in expenses),
        quoted=sum((row.quoted for row in categories), Decimal(0)),
    )


def _total(amounts) -> Decimal:
    return sum((_d(amount or 0) for amount in amounts), Decimal(0))

"""A bank statement, read and lined up against what we already knew (#150).

Framework-free by contract like the rest of auraos/lib: everything here
takes rows that somebody else pulled out of a spreadsheet, so the
arithmetic and the matching can be tested without a site, a file, or a
spreadsheet library.

**A statement is somebody else's document.** It is recorded as it
arrived and never derived, the same rule the supplier VAT follows: the
company's ledger says what AuraOS knows, the statement says what the
bank saw, and the whole point of putting them side by side is that the
two can disagree. So nothing here rewrites a line, and nothing here
posts a ledger entry - matching *suggests*, and a person confirms.

**Most of a real statement cannot match, and that is the product.** In
the July 2026 sample: 24 transactions, of which advances, vendor
payments, client money in and a company purchase can each meet a ledger
entry - and tax paid to the treasury, bank interest, and cash moved from
the bank into the company's own cash box cannot, because the app has no
record of those kinds at all. The unmatched list is not a backlog of
failures; it is the honest answer to "what did the bank see that we have
no record of", and a reconciliation screen that hid it would be worse
than no screen.

**Two representations of money in one sheet**, which is the trap this
parser exists to absorb: the transaction table carries floats in
scientific notation - `1.0E7` is ten million - while the summary block
above it carries comma-grouped strings - `59,621,339.00`. A reader that
handles one and meets the other gets a plausible number rather than an
error, so both go through `to_amount`.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping, Sequence

Row = Mapping[str, Any]

# What a line says about the money's direction, named from the company's
# side of the account rather than the bank's.
OUT = "Out"
IN = "In"

# How sure the matcher is. Nothing here confirms anything - these are
# what a person is being shown before they decide.
STRONG = "strong"
WEAK = "weak"

# How far apart a statement line and a ledger entry may be and still be
# the same movement. Money leaves the company on the day the job records
# it and reaches the bank's books on the day the bank posts it; the
# sample carries a payment transacted on 01/07 with an effective date of
# 02/07, which is the whole reason this is not zero.
WINDOW_DAYS = 3


def to_amount(value: Any) -> int:
    """One money cell, in whole đồng, however the sheet chose to write it.

    Blank is zero: the out and in columns are mutually exclusive on every
    row, so the empty one means "no money went that way" rather than
    "unknown".
    """
    if value is None:
        return 0
    if isinstance(value, (int, float, Decimal)):
        return int(round(Decimal(str(value))))
    text = str(value).strip().replace(",", "")
    if not text:
        return 0
    try:
        return int(round(Decimal(text)))
    except InvalidOperation:
        raise ValueError(f"not an amount: {value!r}")


def to_day(value: Any) -> date:
    """`01/07/2026`, or a datetime the reader already resolved."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    return datetime.strptime(text[:10], "%d/%m/%Y").date()


def to_moment(value: Any) -> datetime | None:
    """`01/07/2026 01:23:20`. None when the cell holds only a day.

    Kept apart from the effective date because they differ - by hours
    normally and by a day at a month boundary - and which one a match
    should use is a decision, not an accident of parsing.
    """
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if len(text) <= 10:
        return None
    return datetime.strptime(text, "%d/%m/%Y %H:%M:%S")


# -- what the statement says --


def read_summary(cells: Row) -> dict:
    """The four figures the bank prints above the table."""
    return {
        "opening": to_amount(cells.get("opening")),
        "withdrawn": to_amount(cells.get("withdrawn")),
        "deposited": to_amount(cells.get("deposited")),
        "closing": to_amount(cells.get("closing")),
    }


def read_lines(rows: Iterable[Row]) -> list[dict]:
    """The transaction table, one dict per row, in the order it arrived.

    `sequence` is the bank's own transaction number and is what makes a
    line identifiable: two coffees for the same amount on the same day
    are two lines and must stay two.
    """
    read = []
    for row in rows:
        withdrawn = to_amount(row.get("withdrawn"))
        deposited = to_amount(row.get("deposited"))
        read.append(
            {
                "effective_on": to_day(row.get("effective_on")),
                "transacted_at": to_moment(row.get("transacted_at")),
                "sequence": str(row.get("sequence") or "").strip(),
                "description": str(row.get("description") or "").strip(),
                "withdrawn": withdrawn,
                "deposited": deposited,
                "amount": deposited - withdrawn,
                "direction": IN if deposited else OUT,
                "running_balance": to_amount(row.get("running_balance")),
            }
        )
    return read


def complaints(summary: Mapping[str, int], lines: Sequence[Mapping]) -> list[str]:
    """Everywhere the statement disagrees with itself. Empty means sound.

    **A statement that fails its own arithmetic is refused rather than
    imported**, because every later question - what is unmatched, what
    the account really holds - is asked of these numbers. A parser that
    silently drops a row it could not read would produce exactly this
    disagreement, so this is also the parser's own alarm.

    Three separate claims, reported separately so a failure says which:
    the totals, the opening-to-closing walk, and the running balance,
    which is the only one that says *where* the trouble is.
    """
    said = []
    withdrawn = sum(line["withdrawn"] for line in lines)
    deposited = sum(line["deposited"] for line in lines)
    if withdrawn != summary["withdrawn"]:
        said.append(
            f"the withdrawals add up to {withdrawn}, and the statement's own "
            f"total says {summary['withdrawn']}"
        )
    if deposited != summary["deposited"]:
        said.append(
            f"the deposits add up to {deposited}, and the statement's own "
            f"total says {summary['deposited']}"
        )
    walked = summary["opening"] + deposited - withdrawn
    if walked != summary["closing"]:
        said.append(
            f"opening plus deposits less withdrawals is {walked}, and the "
            f"closing balance says {summary['closing']}"
        )
    running = summary["opening"]
    for line in lines:
        running += line["amount"]
        if running != line["running_balance"]:
            said.append(
                f"line {line['sequence'] or '?'} should leave {running} in the "
                f"account and the statement says {line['running_balance']}"
            )
            break
    return said


# -- what a line says about itself --

# The references a description can carry, and they are the only text on a
# bank line a machine can key on. Written four ways in one month:
#
#   HDDV 0107-2026            HOP DONG SO 1806-2026/HDDV
#   19052026HDDV              HOA DON SO 13
#
# so the first three are normalised to one shape - `1905-2026` - and an
# eight-digit run is read as ddmmyyyy. That is what lets a payment
# labelled `19052026HDDV` meet a job whose contract is `1905-2026`.
CONTRACT_HINT = re.compile(r"HDDV|HOP\s*DONG")
CONTRACT_DASHED = re.compile(r"(?<!\d)(\d{4})-(\d{4})(?!\d)")
# Lookarounds rather than \b, learned by running this against the real
# sample: the reference in `SO 19052026HDDV` is followed immediately by
# letters, and a word boundary needs a word/non-word transition - digit
# to letter is not one. `\b` matched every other form and silently
# missed the one the normalisation exists for.
CONTRACT_RUN = re.compile(r"(?<!\d)(\d{2})(\d{2})(\d{4})(?!\d)")
INVOICE = re.compile(r"HO[AÁ]\s*DON\s*S[OỐ]\s*(\d+)")


def references(description: str) -> set[str]:
    """Every contract or invoice reference in a line's description.

    Contract references are only read out of a description that mentions
    a contract at all: an eight-digit run is also what a date, a phone
    number and half a transaction id look like, and a reference matched
    out of a bank's own trace code would attach a payment to a job it has
    nothing to do with. **The hint is what makes the pattern safe.**
    """
    text = " ".join(str(description or "").upper().split())
    found = set()
    for number in INVOICE.findall(text):
        found.add(f"HD:{int(number)}")
    if CONTRACT_HINT.search(text):
        for head, tail in CONTRACT_DASHED.findall(text):
            found.add(f"HDDV:{head}-{tail}")
        for day, month, year in CONTRACT_RUN.findall(text):
            # Only if it reads as a date. An eight-digit run is also what
            # a trace code looks like, and `2884JN12` becoming contract
            # `2884-JN12` would attach money to a job at random.
            if 1 <= int(day) <= 31 and 1 <= int(month) <= 12 and 2000 <= int(year) <= 2099:
                found.add(f"HDDV:{day}{month}-{year}")
    return found


# The kinds of movement this app has no record for, and the sentence to
# say so. Read off the description because that is all a bank line is:
# these are not failures to match, they are movements AuraOS does not
# model, and a screen that said "unmatched" without saying which would
# invite somebody to go looking for a record that was never made.
TREASURY = re.compile(r"^NTDT\+KB:")
INTEREST = re.compile(r"LAI\s*NHAP\s*VON")
WITHDRAWAL = re.compile(r"RUT\s*QUY")

UNMODELLED = (
    (TREASURY, "tax paid to the treasury - AuraOS keeps no record of remittances"),
    (INTEREST, "bank interest - AuraOS has no income record of this kind"),
    (
        WITHDRAWAL,
        "cash moved into the company's own box - the ledger has no transfer "
        "between two of its accounts (#151)",
    ),
)


def unmodelled(description: str) -> str | None:
    """Why this line can never match, if it never can. None if it could."""
    text = " ".join(str(description or "").upper().split())
    for pattern, reason in UNMODELLED:
        if pattern.search(text):
            return reason
    return None


# -- lining the two up --


def candidates(
    line: Mapping,
    entries: Iterable[Mapping],
    *,
    window_days: int = WINDOW_DAYS,
) -> list[dict]:
    """Ledger entries that could be this statement line, best first.

    An entry is a candidate only on **exact amount and agreeing
    direction** - money the bank says left the account against money the
    ledger says left the company. Near-amounts are deliberately not
    candidates: a bank line and a ledger entry that differ by a thousand
    đồng are two different facts, and offering them as one invites
    somebody to confirm away a real discrepancy.

    `entries` carry `amount` (signed, the ledger's own convention),
    `entry_date`, and a `references` set the caller assembled - which
    contract, which invoice. Assembling that set is Frappe's job and not
    this module's.

    Strong means a shared reference as well as the amount and the day.
    Weak means the money and the day agree and nothing names the same
    thing twice.
    """
    day = line["effective_on"]
    wanted = abs(line["amount"])
    direction = line["direction"]
    refs = references(line["description"])
    found = []
    for entry in entries:
        amount = int(entry.get("amount") or 0)
        if abs(amount) != wanted or not amount:
            continue
        if (IN if amount > 0 else OUT) != direction:
            continue
        entry_day = entry.get("entry_date")
        if entry_day is None:
            continue
        gap = abs((entry_day - day).days)
        if gap > window_days:
            continue
        shared = refs & set(entry.get("references") or ())
        found.append(
            {
                "entry": entry.get("name"),
                "confidence": STRONG if shared else WEAK,
                "shared_references": sorted(shared),
                "days_apart": gap,
            }
        )
    found.sort(key=lambda one: (one["confidence"] != STRONG, one["days_apart"]))
    return found


def suggestion(found: Sequence[Mapping]) -> dict | None:
    """The one candidate worth showing as *the* answer, or none.

    **Ambiguity is reported as ambiguity rather than resolved by
    ranking.** Two entries of the same amount on the same day with no
    reference between them are genuinely indistinguishable from here, and
    picking the closer one would dress a coin toss as an answer. A person
    with the job in front of them can tell; this cannot.
    """
    if not found:
        return None
    best = found[0]
    if best["confidence"] == STRONG:
        rivals = [one for one in found if one["confidence"] == STRONG]
        return best if len(rivals) == 1 else None
    return best if len(found) == 1 else None

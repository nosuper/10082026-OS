"""The cash ledger: what moved, which way, and where it landed (#99).

Framework-free by contract like the rest of auraos/lib; the Cash Ledger
Entry controller and the doctype adapters are thin over this module.
Four decisions live here rather than in a controller.

**An entry is one movement of money, and its origin is a pair.** What an
entry came from is a doctype *and* a name, never a link to one doctype:
#100 posts expenses, advances and settlements through this same door, and
a client payment's origin is not even a top-level record - it is a
milestone row inside a job. A pair carries all four without a fifth
field, and every flow it can carry is named in `FLOWS` up front so the
vocabulary is a decision rather than an accident of what shipped first.

**The sign is the direction.** Money in is a positive amount, money out
a negative one, so a balance is `sum(amount)` - one number, no case
analysis, whatever mix of flows an account holds. The `In`/`Out` word a
human reads is derived from the sign by `direction_of` and never typed,
so the word and the arithmetic cannot disagree. Zero is not a movement
and has no direction: an entry for it is refused rather than stored as a
row that means nothing.

**Posting is reconciliation, not an event.** `posting` is handed what the
ledger should say and what it already says, and answers with one of four
actions. Called twice about the same money it answers "nothing" the
second time, so a second caller - or a second save, or a third - cannot
double-post. It is also what makes a mis-click recoverable: a milestone
walked back out of đã thanh toán unposts the entry it earned, the same
way `stamps_for` clears the stamp it earned. An entry describing money
that never landed is worse than no entry, because a ledger reads as
authoritative.

**Where the money landed is decided once.** An entry already on file
keeps its account, and only its amount and date are ever restated. Which
account the money hit is a fact of the day it hit; a save a month later
naming a different account is not new information about that day, it is
today's default leaking backwards.

No Frappe imports by contract. The doctype names in `SOURCES` are
strings, not links - naming the origin's vocabulary is a rule, and this
is where the rules are.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Any, Iterable, Mapping

from auraos.lib.milestones import PAID
from auraos.lib.money import round_vnd
from auraos.lib.settlement import FROM_COMPANY

# Which way the money went, as a human reads it. Derived from the sign
# of the amount, never stored independently of it.
IN = "In"
OUT = "Out"

DIRECTIONS = (IN, OUT)

# The movements that reach the ledger. All four were named in #99,
# before three of them posted: a Select the next ticket has to widen is a
# migration, and the vocabulary is the part of this design that had to
# survive #100 unchanged. It did.
CLIENT_PAYMENT = "Client payment"  # a milestone the client paid
JOB_EXPENSE = "Job expense"  # the company paid a vendor itself
CREW_ADVANCE = "Crew advance"  # cash handed to whoever is spending it
FLOAT_SETTLEMENT = "Float settlement"  # a float closed, either way

FLOWS = (CLIENT_PAYMENT, JOB_EXPENSE, CREW_ADVANCE, FLOAT_SETTLEMENT)

# Where each flow comes from. One doctype per flow today; the pair on the
# entry is what keeps that from being an assumption anything relies on.
SOURCES = {
    CLIENT_PAYMENT: "Job Payment Milestone",
    JOB_EXPENSE: "Job Expense",
    CREW_ADVANCE: "Job Advance",
    FLOAT_SETTLEMENT: "Job Settlement",
}

# The prefix that opens an entry's name. The name of an entry is its
# origin, spelled - see `entry_name`.
FLOW_CODES = {
    CLIENT_PAYMENT: "PAY",
    JOB_EXPENSE: "EXP",
    CREW_ADVANCE: "ADV",
    FLOAT_SETTLEMENT: "STL",
}

# What reconciling one movement asks the caller to do.
NOTHING = "nothing"
POST = "post"
UNPOST = "unpost"
REPOST = "repost"


def as_date(value: Any) -> date | None:
    """Coerce a date, a datetime or an ISO string to a plain date.

    The same coercion auraos.lib.finance does, for the same reason -
    stored stamps arrive in all three shapes depending on the driver.
    Repeated rather than imported so that the posting rules stay a leaf
    every other module may import without risking a cycle.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def direction_of(amount: Any) -> str:
    """Which way an amount moved money.

    Zero is not a direction. A row that moves nothing has no business
    claiming it moved money in, and callers are expected to have decided
    already that there is a movement to post.
    """
    amount = round_vnd(amount or 0)
    if not amount:
        raise ValueError("An amount of 0 moves no money and has no direction")
    return IN if amount > 0 else OUT


@dataclass(frozen=True)
class Entry:
    """One movement of money, as the ledger holds it.

    `amount` is signed đồng - the direction is not a second opinion about
    it. `entry_date` is the day the money moved, which is the day the
    origin records, never the day somebody typed it in.
    """

    account: str
    amount: int
    entry_date: date
    flow: str
    source_doctype: str
    source_name: str
    job: str | None = None
    description: str | None = None

    def __post_init__(self):
        # Normalised on the way in so that an entry read back from a
        # database compares equal to the one that was posted - a stored
        # Currency comes back a float and a stored Date as one of three
        # types.
        object.__setattr__(self, "amount", round_vnd(self.amount or 0))
        object.__setattr__(self, "entry_date", as_date(self.entry_date))
        object.__setattr__(self, "job", self.job or None)
        object.__setattr__(self, "description", self.description or None)

    @property
    def direction(self) -> str:
        return direction_of(self.amount)


def entry_name(flow: str, source_name: str) -> str:
    """The name an entry for this movement must have.

    The name *is* the origin, so posting the same movement twice is a
    duplicate primary key rather than a second row. Reconciliation
    already refuses to double-post; this is the guarantee underneath it,
    the one that holds when two saves race each other and neither can see
    the other's uncommitted insert.
    """
    return f"{FLOW_CODES[flow]}-{source_name}"


def restates(existing: Entry, wanted: Entry) -> bool:
    """Whether the entry on file says something different about the money.

    Only the amount and the day: the account an entry already carries is
    where the money went, and no later save is evidence about that.
    """
    return (existing.amount, existing.entry_date) != (wanted.amount, wanted.entry_date)


def restated(existing: Entry, wanted: Entry) -> Entry:
    """`wanted`, landing where the money already landed."""
    return replace(wanted, account=existing.account)


def posting(wanted: Entry | None, existing: Entry | None, moved: bool) -> str:
    """What to do about one movement, given what the ledger already says.

    `moved` is whether money changed hands at all, judged without any
    reference to an account - that separation is the whole of the fourth
    acceptance criterion. Money that moved somewhere we cannot name is
    not the same as money that never moved:

    - nothing moved, so any entry on file is a lie and comes back out;
    - it moved, but no account is known - nothing is posted and nothing
      already posted is disturbed. The collection is still recorded on
      the milestone; a company that has not said where it keeps money
      simply has no ledger yet, and gets one on the next save after it
      says so. Refusing the save was never an option;
    - it moved, nothing is on file - post it;
    - it moved and the entry on file already says so - do nothing, which
      is what makes a second caller harmless.
    """
    if not moved:
        return UNPOST if existing else NOTHING
    if wanted is None:
        return NOTHING
    if existing is None:
        return POST
    return REPOST if restates(existing, wanted) else NOTHING


# -- money in: what the client paid --


def collected(milestone: Mapping[str, Any]) -> bool:
    """Whether this milestone's money has actually landed.

    đã thanh toán and a day it was marked on and an amount worth
    recording. A milestone billing 0% of the quote is a placeholder in a
    plan, not a payment, however it is marked.
    """
    return bool(
        milestone.get("status") == PAID
        and as_date(milestone.get("paid_on"))
        and round_vnd(milestone.get("amount") or 0)
    )


def client_payment(
    milestone: Mapping[str, Any],
    account: str | None,
    job: str | None = None,
) -> Entry | None:
    """The ledger entry a collected milestone earns, or None.

    None covers both nothings: a milestone nobody has collected, and one
    collected into a company that has not named an account yet. Which of
    the two it is stays readable, because `posting` is told separately
    whether the money moved.

    Positive, because this is the one flow where money comes in.
    """
    if not collected(milestone) or not account:
        return None
    return Entry(
        account=account,
        amount=round_vnd(milestone.get("amount") or 0),
        entry_date=as_date(milestone.get("paid_on")),
        flow=CLIENT_PAYMENT,
        source_doctype=SOURCES[CLIENT_PAYMENT],
        source_name=milestone.get("name"),
        job=job,
        description=milestone.get("title"),
    )


# -- money out: what the company paid --


def paid_by_company(expense: Mapping[str, Any]) -> bool:
    """Whether this expense moved money out of an account of ours.

    Only the ones the company paid the vendor itself. An expense paid
    out of a float spends đồng that already left the company the day the
    advance was transferred; posting it again would have the same money
    leaving twice, and a double-counted ledger is worse than a thin one.
    A float's own arithmetic is closed by its settlement, which is the
    entry that records the rest of that money moving.

    Blank is a float expense, the same reading auraos.lib.settlement
    gives it - the column has a default and pre-existing rows may not.
    """
    return bool(
        expense.get("paid_from") == FROM_COMPANY
        and as_date(expense.get("spent_on"))
        and round_vnd(expense.get("amount") or 0)
    )


def job_expense(expense: Mapping[str, Any], account: str | None) -> Entry | None:
    """The ledger entry a vendor payment earns, or None.

    Negative: this is money leaving. The job comes off the record rather
    than from the caller - unlike a milestone, an expense is a record of
    its own and knows which job it is on, so there is no second opinion
    to keep in step.
    """
    if not paid_by_company(expense) or not account:
        return None
    return Entry(
        account=account,
        amount=-round_vnd(expense.get("amount") or 0),
        entry_date=as_date(expense.get("spent_on")),
        flow=JOB_EXPENSE,
        source_doctype=SOURCES[JOB_EXPENSE],
        source_name=expense.get("name"),
        job=expense.get("job"),
        description=expense.get("description") or expense.get("category"),
    )


def transferred(advance: Mapping[str, Any]) -> bool:
    """Whether the cash in this advance has actually changed hands.

    The day it was transferred is what says so, and nothing else can: an
    amount column is never null, so 0 would have to mean both "no money"
    and "nobody has recorded this yet". An advance planned and not yet
    handed over is money still in the company's account.
    """
    return bool(
        as_date(advance.get("transferred_on"))
        and round_vnd(advance.get("amount") or 0)
    )


def crew_advance(advance: Mapping[str, Any], account: str | None) -> Entry | None:
    """The ledger entry an advance earns, or None.

    Negative: cash handed to whoever is spending it has left the company,
    whatever they go on to spend it on. Described by its recipient,
    because "who is holding it" is the only thing anybody asks of a row
    like this without opening it.
    """
    if not transferred(advance) or not account:
        return None
    return Entry(
        account=account,
        amount=-round_vnd(advance.get("amount") or 0),
        entry_date=as_date(advance.get("transferred_on")),
        flow=CREW_ADVANCE,
        source_doctype=SOURCES[CREW_ADVANCE],
        source_name=advance.get("name"),
        job=advance.get("job"),
        description=advance.get("recipient"),
    )


def settled(row: Mapping[str, Any]) -> bool:
    """Whether this settlement's transfer has been made.

    A settlement is a transfer recorded after the fact - the doctype
    freezes its numbers precisely because it describes money already
    moved - so the day it was settled on is the whole test. A float that
    turns out to be wrong is corrected by settling again, never by
    rewriting this row; a settlement that never happened is deleted, and
    then nothing moved and the entry comes back out.
    """
    return bool(
        as_date(row.get("settled_on")) and round_vnd(row.get("amount") or 0)
    )


def float_settlement(row: Mapping[str, Any], account: str | None) -> Entry | None:
    """The ledger entry closing a float earns, or None.

    The amount is taken exactly as stored, sign and all. A settlement is
    already signed the way this ledger signs money - positive when the
    holder hands the remainder back, negative when the company tops them
    up - because auraos.lib.settlement reads that same sign to close the
    float. Re-deriving it here would be a second opinion about which way
    the cash went, and two opinions is one too many.
    """
    if not settled(row) or not account:
        return None
    return Entry(
        account=account,
        amount=round_vnd(row.get("amount") or 0),
        entry_date=as_date(row.get("settled_on")),
        flow=FLOAT_SETTLEMENT,
        source_doctype=SOURCES[FLOAT_SETTLEMENT],
        source_name=row.get("name"),
        job=row.get("job"),
        description=row.get("recipient"),
    )


# -- what an account is worth --


def balance(entries: Iterable[Entry | Mapping[str, Any]]) -> int:
    """What an account holds: the sum of its entries, in whole đồng.

    A sum and nothing else - no direction to branch on, no opening figure
    to trust, and an account with no entries is worth 0 rather than an
    error. #101 renders this; it is here so that the claim "a balance is
    derived" is testable without a database.
    """
    return sum(round_vnd(_amount_of(entry) or 0) for entry in entries)


def _amount_of(entry: Entry | Mapping[str, Any]) -> Any:
    """One entry's signed amount, whether it is an Entry or a stored row."""
    return entry["amount"] if isinstance(entry, dict) else entry.amount


# -- reading the ledger back (#101) --


def _field(entry: Entry | Mapping[str, Any], name: str) -> Any:
    """One field off an entry, whether it is an Entry or a stored row."""
    if isinstance(entry, dict):
        return entry.get(name)
    return getattr(entry, name, None)


@dataclass(frozen=True)
class Holding:
    """One account and what the ledger says it holds.

    Not a stored figure and not a storable one: it is made here, out of
    the rows, every time somebody asks. There is deliberately no way to
    put a number into this that the entries did not put there.
    """

    account: str
    balance: int
    count: int


def holdings(
    accounts: Iterable[str],
    entries: Iterable[Entry | Mapping[str, Any]],
) -> list[Holding]:
    """What each account holds, in the order the accounts were given.

    Every account named comes back, whether or not anything was ever
    posted against it. An account with no entries holds 0 - that is a
    fact about the account, not a gap in the data, and a studio that has
    never posted anything opens this screen to zeros rather than to an
    error.

    Each balance is `balance()` over that account's rows and nothing
    else, so widening the ledger with a fifth flow tomorrow widens these
    figures without a line changing here.
    """
    held = {account: [] for account in accounts}
    for entry in entries:
        rows = held.get(_field(entry, "account"))
        if rows is not None:
            rows.append(entry)
    return [
        Holding(account, balance(rows), len(rows)) for account, rows in held.items()
    ]


def total_held(held: Iterable[Holding]) -> int:
    """What the company has: the accounts on the screen, added up.

    Taken from the same holdings the screen lists rather than from the
    entries again, so the total and the rows under it cannot disagree.
    """
    return sum(holding.balance for holding in held)


def source_of(
    entry: Entry | Mapping[str, Any],
    job_title: str | None = None,
) -> str:
    """The origin as a human recognises it - never a doctype and a name.

    An entry's origin is a pair, which is the right thing to store and
    the wrong thing to read: "Job Payment Milestone / 8f3c1a2b" tells a
    founder nothing about their own money. What the origin calls itself
    is already on the entry - a milestone's title, an expense's
    description, the person holding a float - so that is the first
    answer. The job it happened on is the second, because money out of a
    record with no title of its own is still recognisably that job's.
    The flow is the last resort, and it is always true.
    """
    for candidate in (
        _field(entry, "description"),
        job_title,
        _field(entry, "flow"),
    ):
        named = str(candidate or "").strip()
        if named:
            return named
    return ""


def entry_view(
    entry: Entry | Mapping[str, Any],
    job_title: str | None = None,
) -> dict[str, Any]:
    """One movement as a screen reads it (#101).

    The direction is read off the sign here as well, rather than trusted
    from the stored column: the amount is what a balance is made of, so
    the word printed beside it has to come from the same place.

    The origin pair travels too. The screen prints `source`, but a
    founder querying a figure needs to be able to reach the record it
    came from, and the pair is what identifies it.
    """
    amount = round_vnd(_amount_of(entry) or 0)
    entry_date = as_date(_field(entry, "entry_date"))
    return {
        "name": _field(entry, "name"),
        "entry_date": entry_date.isoformat() if entry_date else None,
        "amount": amount,
        "direction": direction_of(amount),
        "flow": _field(entry, "flow"),
        "source": source_of(entry, job_title),
        "source_doctype": _field(entry, "source_doctype"),
        "source_name": _field(entry, "source_name"),
        "job": _field(entry, "job") or None,
        "job_title": job_title or None,
    }

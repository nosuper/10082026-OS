"""What the open pipeline is worth in the months ahead (#102).

Framework-free by contract like the rest of auraos/lib; the whitelisted
endpoints in auraos.api are thin adapters that fetch deals and hand them
here. Five decisions live in this module rather than in a screen.

**This number is an estimate multiplied by a guess, and the payload has
to say so in its own field names.** As of #101 it lands on a dashboard
beside a cash balance and a receivables total that are facts - provable
against `sum(amount)` in the database. A founder who cannot tell those
apart at a glance has been made worse informed, not better. So the
weighted figure travels as `weighted_projection` and never as a total, a
balance, an amount or an income, and the unweighted contrast travels as
`open_pipeline`. That is not a convention anybody has to remember:
`projection` runs its own answer through `guarded` before returning it,
so a later edit that adds a `total` to this report raises on the first
read instead of shipping a mislabelled figure. A screen may style it
however it likes - what it cannot do is receive a key called `total`
from here and print it as money the company has. See `CASH_WORDS`.

**Nothing here is stored and nothing here is storable.** No forecast
table, no cached month totals, no field on any doctype holding a
weighted figure. Every number is made out of the deals and the stage
rules on the read that asked for it, which is the property that lets a
probability changed in settings change the forecast on the very next
read, and the same property that made #99's ledger and #101's balances
worth trusting.

**A deal is worth the best number anybody has actually written down.**
Three rungs, best first: the total on the quote the client has been
given, the deal's own priced breakdown, and only then the client's
stated budget. A deal with a published quote has a better number than
its estimated budget, and weighting the worse one when the better one
exists is a forecast that is wrong on purpose. Which rung answered
travels with the row as `value_basis`, because a founder reading a
figure is entitled to know whether it came from a quote or a guess.

**Won and Lost are not pipeline.** A won deal has become a job, and that
job's milestones are already counted as receivables; adding it here
would have the same money arriving twice. Lost is gone. They still carry
rules, at 100 and 0, because the stage vocabulary here has to be the
Deal Select's or the two drift - not because either ever contributes.

**An unset rule falls back to the house default, never to zero.** A
stage nobody has configured weights at its default and says so
(`configured=False`). Reading an absent rule as 0% would render a real
pipeline as an empty screen that looks like "no deals" rather than "not
configured", and 0 is a legitimate stored probability (Lost), so the two
can never be told apart by value. Only the presence of a rule can say
which is which, which is why `stage_rules` keys on the stage rather than
on the number.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable, Mapping

from auraos.lib.finance import as_date, month_key
from auraos.lib.money import round_vnd
from auraos.lib.money import to_decimal as _d

Row = Mapping[str, Any]

# The deal stages, exactly as the Deal doctype's Select spells them.
# Copied as constants rather than read from a doctype because this module
# has no Frappe to read one with; the contract test beside the settings
# doctype is what pins the two together.
BRIEF_RECEIVED = "Brief Received"
DE_BRIEF = "De-brief"
BREAKDOWN = "Breakdown"
QUOTE_SENT = "Quote Sent"
NEGOTIATION = "Negotiation"
WON = "Won"
LOST = "Lost"

STAGES = (
    BRIEF_RECEIVED,
    DE_BRIEF,
    BREAKDOWN,
    QUOTE_SENT,
    NEGOTIATION,
    WON,
    LOST,
)

# The stages that have stopped being pipeline. A won deal is a job and is
# counted as receivables; a lost one is not coming back.
RESOLVED = (WON, LOST)

# The house opening dials: win probability in whole percent, and the lead
# time in days between today and the month that money is expected to be
# billed. Whole percent because a win probability finer than one point is
# false precision on a guess.
#
# The probabilities are the ones #102 names. The lead times ladder down
# with the stage: a brief just received is a quarter away from an
# invoice, a deal in negotiation is a month away. Won and Lost lead
# nowhere because neither contributes.
DEFAULT_RULES: dict[str, tuple[int, int]] = {
    BRIEF_RECEIVED: (10, 90),
    DE_BRIEF: (20, 75),
    BREAKDOWN: (30, 60),
    QUOTE_SENT: (50, 45),
    NEGOTIATION: (70, 30),
    WON: (100, 0),
    LOST: (0, 0),
}

# Which rung of the ladder a deal's value came off.
QUOTED = "quoted"  # the total on the quote the client has been given
PRICED = "priced"  # the deal's own breakdown, not yet quoted out
ESTIMATED = "estimated"  # nobody has priced it; the client's stated budget
UNVALUED = "unvalued"  # no number of any kind on the deal yet

VALUE_BASES = (QUOTED, PRICED, ESTIMATED, UNVALUED)

# What this projection is measured on, carried in the payload for the
# same reason auraos.lib.exposure carries its basis: the screen says it
# out loud and the two have to be the same claim.
PROJECTION_BASIS = (
    "open deal value weighted by the win probability of its stage, "
    "billed in the month that stage's lead time reaches - a projection, "
    "not money held"
)

# The names a figure in this payload may never be called.
#
# This is the mechanical half of "the weighted figure is labelled
# distinctly". A caption can be edited away and a colour is one refactor
# from vanishing, but a key called `total` here fails a test that names
# the reason, in both suites, before it can reach a screen. The next
# consumer of this payload cannot receive a projection under a name that
# reads as money in the bank, because no such name is allowed to exist.
CASH_WORDS = frozenset(
    {
        "total",
        "balance",
        "cash",
        "amount",
        "income",
        "revenue",
        "held",
        "collected",
        "paid",
        "received",
    }
)


def guarded(payload: dict) -> dict:
    """The payload, refused outright if it names a figure like cash.

    Not a test helper - `projection` runs this before it returns, so the
    rule is enforced by the code that produces the number rather than
    only by a suite somebody has to remember to run. A future edit that
    adds a `total` to this report does not ship a mislabelled figure to a
    screen; it raises here, on the first read, with the reason attached.

    This is the half of "labelled distinctly" that survives a refactor. A
    caption can be deleted and a colour can be restyled, and neither
    failure is visible to the next consumer of the payload. A name cannot
    be introduced at all.
    """
    offenders = cash_shaped_keys(payload)
    if offenders:
        raise ValueError(
            "A projection may not be named like money the company has: "
            + ", ".join(sorted(offenders))
            + ". This report is an estimate multiplied by a probability and "
            "sits beside a real cash balance; name the figure so a screen "
            "cannot render it as cash (see auraos.lib.forecast.CASH_WORDS)."
        )
    return payload


def cash_shaped_keys(payload: Any) -> set[str]:
    """Every key in a payload that reads as money the company has.

    Walks dicts and lists to any depth, because a month row and a deal
    row are as capable of misnaming a projection as the report is. The
    match is on the whole key: `weighted_projection` and `open_pipeline`
    pass, `total` and `weighted_total` do not - a name that ends in a
    cash word is exactly the quiet rename this guards against.
    """
    found: set[str] = set()
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            for word in CASH_WORDS:
                if key == word or key.endswith(f"_{word}"):
                    found.add(key)
            found |= cash_shaped_keys(value)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            found |= cash_shaped_keys(item)
    return found


# -- the dials --


@dataclass(frozen=True)
class StageRule:
    """One stage's two dials, and where they came from.

    `configured` is the whole answer to the trap this feature sits on. An
    AuraOS Settings row that nobody has written reads back as 0 rather
    than as nothing, and 0 is what Lost is legitimately set to, so no
    figure can distinguish "the founder means zero" from "nobody has said
    yet". Only whether a rule exists can, so that fact travels rather
    than being inferred downstream from a number that cannot carry it.
    """

    stage: str
    win_probability_pct: int
    lead_days: int
    configured: bool


def default_rule(stage: str) -> StageRule:
    """The house dials for a stage, marked as nobody's decision yet."""
    probability, lead_days = DEFAULT_RULES[stage]
    return StageRule(stage, probability, lead_days, configured=False)


def stage_rules(stored: Iterable[Row] = ()) -> list[StageRule]:
    """The dials in force, stored rows laid over the house defaults.

    Every stage of the Deal Select comes back whether or not anybody has
    configured it, in the order the pipeline runs, so a settings screen
    renders the whole vocabulary and a stage with no deals is a row of
    zeros rather than a gap.

    A stored row wins outright, including a stored 0 - that is the
    difference this table exists to record. A row naming a stage the Deal
    Select no longer has is kept and marked configured, because dropping
    somebody's stored dial silently is how a rename becomes data loss;
    the settings screen shows it and the founder deletes it.
    """
    rows = {}
    for row in stored:
        stage = (row.get("stage") or "").strip()
        if not stage:
            continue
        rows[stage] = StageRule(
            stage=stage,
            win_probability_pct=int(row.get("win_probability_pct") or 0),
            lead_days=int(row.get("lead_days") or 0),
            configured=True,
        )
    rules = [rows.get(stage) or default_rule(stage) for stage in STAGES]
    rules += [rule for stage, rule in rows.items() if stage not in STAGES]
    return rules


def rule_for(rules: Iterable[StageRule], stage: str) -> StageRule | None:
    """The rule governing a stage, or None if no rule reaches it.

    None rather than a zero rule on purpose. A deal at a stage nothing
    governs is not a deal worth nothing; it is a deal this projection
    cannot speak for, and `projection` carries it out as `unruled` rather
    than weighting it at 0% and quietly shrinking the forecast.
    """
    for rule in rules:
        if rule.stage == stage:
            return rule
    return None


# -- what a deal is worth --


def deal_value(deal: Row) -> tuple[int, str]:
    """The best number written down for this deal, and which one it is.

    Three rungs, best first:

    1. `quoted_total` - the total on the quote the client has actually
       been given. This is the strongest claim available: it is frozen on
       the quote document, it is the figure the client is holding, and it
       does not move when somebody edits a cost line afterwards.
    2. `quote_total` - the deal's own breakdown, priced but never sent.
       Weaker than a quote because the client has not seen it, stronger
       than a budget because it is built out of real cost lines.
    3. `estimated_budget` - what the client said they had. A guess, and
       the only thing available on a deal nobody has priced.

    Zero at a rung is not an answer and falls through: a Currency column
    is never null, so 0 there means "nothing recorded" rather than "this
    deal is worth nothing". A deal genuinely worth nothing weights to
    nothing either way, so nothing is lost by reading a 0 as silence.
    """
    for field, basis in (
        ("quoted_total", QUOTED),
        ("quote_total", PRICED),
        ("estimated_budget", ESTIMATED),
    ):
        value = round_vnd(deal.get(field) or 0)
        if value:
            return value, basis
    return 0, UNVALUED


def weighted(value: Any, win_probability_pct: Any) -> int:
    """One deal's contribution: its value times the stage's probability.

    Rounded to whole đồng here, before anything is added, as everywhere
    else in this app - so a month's printed figure is exactly the sum of
    the printed rows under it.
    """
    return round_vnd(_d(round_vnd(value)) * _d(win_probability_pct) / 100)


# -- which month it lands in --


def expected_month(today: Any, lead_days: Any) -> str:
    """The month a deal at this stage is expected to bill in.

    Counted from today, not from the day the deal entered its stage. A
    forecast answers "starting now, when does this money arrive", and a
    deal that has been sitting in Breakdown since spring does not bill
    sooner for having waited. Counting from stage entry would also drop
    contributions into months that have already been and gone, which is
    not a forecast of anything.

    A negative lead time lands in the current month rather than in the
    past, for the same reason.
    """
    day = as_date(today)
    return month_key(day + timedelta(days=max(int(lead_days or 0), 0)))


def horizon(today: Any, months: int = 6) -> list[str]:
    """The months a forecast covers, starting with the current one.

    Always at least one month, and always contiguous. A month with
    nothing in it is still a month: a forecast with October quietly
    missing reads as a shorter year rather than as an empty October, and
    an empty October is the news a founder opened this screen for.
    """
    day = as_date(today)
    year, month = day.year, day.month
    keys = []
    for _ in range(max(int(months or 0), 1)):
        keys.append(f"{year:04d}-{month:02d}")
        year, month = year + month // 12, month % 12 + 1
    return keys


# -- the projection --


def contribution(deal: Row, rule: StageRule, today: Any) -> dict:
    """One open deal's line in the forecast.

    Both figures travel: what the deal is worth if it lands, and what it
    is worth weighted. A screen showing only the second cannot explain
    it, and a screen showing only the first is not a forecast.
    """
    value, basis = deal_value(deal)
    return {
        "deal": deal.get("name"),
        "title": deal.get("title"),
        "stage": rule.stage,
        "deal_value": value,
        "value_basis": basis,
        "win_probability_pct": rule.win_probability_pct,
        "lead_days": rule.lead_days,
        "weighted_projection": weighted(value, rule.win_probability_pct),
        "month": expected_month(today, rule.lead_days),
    }


def is_open(deal: Row) -> bool:
    """Whether this deal is still pipeline. Won and Lost are not."""
    return (deal.get("stage") or "") not in RESOLVED


def projection(
    deals: Iterable[Row],
    rules: Iterable[StageRule] | None = None,
    *,
    today: Any = None,
    months: int = 6,
) -> dict:
    """What the open pipeline is expected to be worth, month by month.

    `deals` are open deals the caller has already fetched, each carrying
    whatever value fields it has. Resolved deals are dropped here rather
    than being kept out by a query filter alone, so the rule lives in one
    place and is testable without a database.

    The report is arranged three ways over the same contributions, and
    the three agree by construction: `weighted_projection` at the top is
    the sum of the months, which is the sum of the stages, which is the
    sum of the deal rows. Nothing is computed twice from different
    inputs, so no two figures on the screen can disagree.

    The months are the requested horizon plus any month a contribution
    actually lands in. A lead time longer than the horizon must not lose
    the money it carries: a dropped contribution would make the headline
    disagree with the rows, and a founder cannot audit a figure whose
    parts are not on the screen.

    A studio with no open deals gets the horizon, every month at zero,
    every stage at zero, and no error - the same silence #101 chose for a
    company that has named no account.
    """
    rules = list(rules if rules is not None else stage_rules())
    today = as_date(today) or date.today()

    lines: list[dict] = []
    unruled: list[dict] = []
    for deal in deals:
        if not is_open(deal):
            continue
        rule = rule_for(rules, deal.get("stage") or "")
        if rule is None:
            value, basis = deal_value(deal)
            unruled.append(
                {
                    "deal": deal.get("name"),
                    "title": deal.get("title"),
                    "stage": deal.get("stage"),
                    "deal_value": value,
                    "value_basis": basis,
                }
            )
            continue
        lines.append(contribution(deal, rule, today))

    keys = horizon(today, months)
    keys += sorted({line["month"] for line in lines} - set(keys))

    return guarded(
        {
            "basis": PROJECTION_BASIS,
            "as_of": today.isoformat(),
            "weighted_projection": sum(line["weighted_projection"] for line in lines),
            "open_pipeline": sum(line["deal_value"] for line in lines),
            "deal_count": len(lines),
            "months": [_month(key, lines) for key in sorted(keys)],
            "stages": [_stage(rule, lines) for rule in rules],
            # Deals no rule reaches. Named rather than dropped: money this
            # projection cannot speak for is still money, and a founder is
            # owed the fact that it is missing from the figure above.
            "unruled": unruled,
            "unruled_pipeline": sum(row["deal_value"] for row in unruled),
        }
    )


def _month(key: str, lines: Iterable[dict]) -> dict:
    """One month of the forecast, with the deals that make it up."""
    rows = [line for line in lines if line["month"] == key]
    return {
        "month": key,
        "weighted_projection": sum(row["weighted_projection"] for row in rows),
        "open_pipeline": sum(row["deal_value"] for row in rows),
        "deal_count": len(rows),
        "deals": rows,
    }


def _stage(rule: StageRule, lines: Iterable[dict]) -> dict:
    """One stage's dials and what the deals sitting at it are worth.

    Present for every stage, including the ones nothing sits at and the
    two that never contribute. A stage row of zeros is the answer to
    "what is in Negotiation", and an absent row is not.
    """
    rows = [line for line in lines if line["stage"] == rule.stage]
    return {
        "stage": rule.stage,
        "win_probability_pct": rule.win_probability_pct,
        "lead_days": rule.lead_days,
        "configured": rule.configured,
        "contributes": rule.stage not in RESOLVED,
        "deal_count": len(rows),
        "open_pipeline": sum(row["deal_value"] for row in rows),
        "weighted_projection": sum(row["weighted_projection"] for row in rows),
        "month": rows[0]["month"] if rows else None,
    }

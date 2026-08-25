"""Pure-python tests for auraos.lib.breakeven - no Frappe required.

Subtracting one number from another is not what these tests are for.
What they pin is **which side each figure comes from, which date puts a
job in a month, and which half of a surplus can still move** - the four
ways a break-even screen misleads while looking entirely reasonable:

- **The two sides are aggregated across different things.** #14 asks for
  aggregation across months and jobs, and the trap is that overheads
  aggregate by the day money left while a job's margin aggregates by the
  day it was booked. A suite whose fixtures booked and paid everything in
  one month would pass whichever date the module read.
- **A surplus can be entirely provisional.** An open job is still
  spending, so its margin can only fall. The final half is totalled
  apart, and one of these tests exists to fail if the two are ever added
  into one confident number.
- **Nothing here proposes a floor.** "Show, don't suggest" is the
  ticket's own wording, and it is asserted by content: no key in this
  payload proposes a price, a floor or a target, and `caveats` says in
  words that the floor stays the founder's. Deleting the honesty is a
  test failure, which is the only way it stays.
- **A capital purchase is not a running cost.** A flagged purchase sits
  beside the break-even line, never inside it and never invisible.
"""

from datetime import date

from auraos.lib.breakeven import (
    CAVEATS,
    CLOSED_STAGE,
    booked_month,
    break_even,
    contribution,
    coverage_pct,
)
from auraos.lib.tax import overheads

JULY = (date(2026, 7, 1), date(2026, 7, 31))
Q3 = (date(2026, 7, 1), date(2026, 9, 30))


def job(**overrides):
    """One `reporting.profit_view` row widened with its booking day.

    Revenue less actual cost is the margin, exactly as the upstream
    module computed it - these fixtures never invent a margin that does
    not follow from the two figures beside it, because a fixture that did
    would hide the day this module starts recomputing instead of copying.
    """
    row = {
        "name": "JOB-0001",
        "title": "TVC Tết",
        "client": "SUMO",
        "stage": "Post-production",
        "booked_on": date(2026, 7, 8),
        "revenue_ex_vat": 100_000_000,
        "actual_cost": 60_000_000,
        "margin": 40_000_000,
        "margin_pct": 40.0,
    }
    row.update(overrides)
    return row


def overhead(**overrides):
    """One Company Expense row, as the tax module reads them."""
    row = {
        "name": "CE-2026-00001",
        "spent_on": date(2026, 7, 1),
        "amount": 30_000_000,
        "category": "Thuê văn phòng",
        "description": "Tiền thuê tháng 7",
        "for_depreciation": 0,
    }
    row.update(overrides)
    return row


def report(jobs, expenses, window=JULY):
    """The whole payload, built the way the endpoint builds it."""
    return break_even(contribution(jobs, *window), overheads(expenses, *window))


# -- which month a job belongs to --


def test_a_job_is_counted_in_the_month_it_was_booked_not_the_month_it_ships():
    """The date under test is the booking date and nothing else.

    A job booked in July and still in post in September is July's
    decision: July is when somebody said yes at that price, which is the
    judgement the founder is checking.
    """
    booked_in_july = job(booked_on=date(2026, 7, 8), stage="Post-production")

    assert booked_month(booked_in_july) == "2026-07"
    assert contribution([booked_in_july], *JULY)["margin_total"] == 40_000_000
    assert contribution([booked_in_july], date(2026, 9, 1), date(2026, 9, 30))[
        "margin_total"
    ] == 0


def test_a_job_with_no_booking_date_is_reported_apart_rather_than_dropped():
    """No date is a fact about the record, and it stays visible.

    Folding it into the first month would invent the thing the record is
    missing; dropping it silently would make the range total disagree
    with the job list beside it for a reason nobody could see.
    """
    undated = job(name="JOB-0009", booked_on=None, margin=7_000_000)

    earned = contribution([job(), undated], *JULY)

    assert earned["job_count"] == 1
    assert earned["margin_total"] == 40_000_000
    assert earned["unbooked"]["count"] == 1
    assert earned["unbooked"]["margin"] == 7_000_000
    assert [row["job"] for row in earned["unbooked"]["jobs"]] == ["JOB-0009"]


def test_a_job_booked_outside_the_window_is_not_counted():
    outside = job(name="JOB-0002", booked_on=date(2026, 6, 30))

    assert contribution([outside], *JULY)["job_count"] == 0


# -- aggregation across months and jobs --


def test_months_the_range_touches_are_present_even_when_nothing_happened():
    """An empty August is an empty August, not a missing one.

    A chart that quietly omits a month reads as a shorter quarter rather
    than as a month that took nothing on - the rule `finance.month_keys`
    already owns for income against expense.
    """
    quarter = report([job(booked_on=date(2026, 7, 8))], [overhead()], window=Q3)

    assert [month["month"] for month in quarter["months"]] == [
        "2026-07",
        "2026-08",
        "2026-09",
    ]
    assert quarter["months"][1]["contribution"] == 0
    assert quarter["months"][1]["overhead"] == 0


def test_many_jobs_and_many_overheads_fold_into_their_own_months():
    """The aggregation #14 asks for, across both axes at once."""
    jobs = [
        job(name="JOB-1", booked_on=date(2026, 7, 8), margin=40_000_000),
        job(name="JOB-2", booked_on=date(2026, 7, 20), margin=10_000_000),
        job(name="JOB-3", booked_on=date(2026, 8, 3), margin=25_000_000),
    ]
    spending = [
        overhead(name="CE-1", spent_on=date(2026, 7, 1), amount=30_000_000),
        overhead(name="CE-2", spent_on=date(2026, 7, 5), amount=12_000_000),
        overhead(name="CE-3", spent_on=date(2026, 8, 1), amount=30_000_000),
    ]

    quarter = report(jobs, spending, window=Q3)
    july, august, september = quarter["months"]

    assert (july["contribution"], july["overhead"]) == (50_000_000, 42_000_000)
    assert (august["contribution"], august["overhead"]) == (25_000_000, 30_000_000)
    assert (september["contribution"], september["overhead"]) == (0, 0)
    assert july["job_count"] == 2
    assert july["overhead_count"] == 2


def test_the_months_add_up_to_the_range_total_on_both_sides():
    """The range row is the upstream total, and the months agree with it.

    Two additions of one set of rows is how a footer comes to disagree
    with the column above it. Both are computed, and they are asserted
    equal rather than assumed equal.
    """
    jobs = [
        job(name="JOB-1", booked_on=date(2026, 7, 8), margin=40_000_000),
        job(name="JOB-2", booked_on=date(2026, 8, 3), margin=25_000_000),
        job(name="JOB-3", booked_on=date(2026, 9, 30), margin=-5_000_000),
    ]
    spending = [
        overhead(name="CE-1", spent_on=date(2026, 7, 1), amount=30_000_000),
        overhead(name="CE-2", spent_on=date(2026, 9, 2), amount=30_000_000),
    ]

    quarter = report(jobs, spending, window=Q3)
    total = quarter["total"]

    assert sum(month["contribution"] for month in quarter["months"]) == total[
        "contribution"
    ]
    assert sum(month["overhead"] for month in quarter["months"]) == total["overhead"]
    assert sum(month["surplus"] for month in quarter["months"]) == total["surplus"]
    assert total["job_count"] == 3
    assert total["overhead_count"] == 2


# -- the line itself --


def test_a_shortfall_and_a_surplus_are_one_signed_number():
    """Below zero the month did not pay for itself, and says so once."""
    short = report([job(margin=10_000_000)], [overhead(amount=30_000_000)])
    over = report([job(margin=50_000_000)], [overhead(amount=30_000_000)])

    assert short["total"]["surplus"] == -20_000_000
    assert short["total"]["covered"] is False
    assert over["total"]["surplus"] == 20_000_000
    assert over["total"]["covered"] is True
    # One field, so a screen cannot print a shortfall of 0 beside a
    # surplus of 0 and say nothing twice.
    assert "shortfall" not in short["total"]


def test_covering_the_upkeep_exactly_counts_as_covered():
    """Break-even is the line, and the line is on the covered side."""
    exact = report([job(margin=30_000_000)], [overhead(amount=30_000_000)])

    assert exact["total"]["surplus"] == 0
    assert exact["total"]["covered"] is True
    assert exact["total"]["coverage_pct"] == 100.0


def test_a_month_with_no_upkeep_has_no_coverage_percentage():
    """Nothing to cover is not the same as covering nothing.

    0% would read as work that failed to pay for a month it was never
    asked to pay for. The same rule `reporting.margin_pct` uses for a job
    quoted at nothing.
    """
    assert coverage_pct(40_000_000, 0) is None
    assert report([job()], [])["total"]["coverage_pct"] is None
    # And a month with upkeep but no work is 0%, which is a real answer.
    assert report([], [overhead()])["total"]["coverage_pct"] == 0.0


# -- what can still move --


def test_an_open_job_and_a_closed_one_are_totalled_apart():
    """A surplus made of open jobs is an opinion about breaking even.

    An open job is still spending, so its margin can only fall. The final
    total is the half that cannot move, and this is here to fail the day
    the two are added into one confident number.
    """
    jobs = [
        job(name="JOB-1", stage=CLOSED_STAGE, margin=20_000_000),
        job(name="JOB-2", stage="Post-production", margin=25_000_000),
    ]

    month = report(jobs, [overhead(amount=30_000_000)])["total"]

    assert month["contribution"] == 45_000_000
    assert month["final_contribution"] == 20_000_000
    assert month["provisional_contribution"] == 25_000_000
    assert month["final_count"] == 1
    # Booked, the month is in surplus. Finished, it is not - and both are
    # true at once, which is exactly why both are printed.
    assert month["surplus"] == 15_000_000
    assert month["final_surplus"] == -10_000_000


# -- what is outside the line --


def test_a_flagged_purchase_sits_beside_the_line_and_not_inside_it():
    """A camera is not a running cost, and is not invisible either.

    Inside the line, the month a company buys one reads as a catastrophe
    against work that was priced fine. Dropped, the founder holding a
    bank statement cannot find where the money went.
    """
    spending = [
        overhead(name="CE-1", amount=30_000_000),
        overhead(name="CE-2", amount=90_000_000, for_depreciation=1),
    ]

    month = report([job(margin=40_000_000)], spending)["total"]

    assert month["overhead"] == 30_000_000
    assert month["flagged_overhead"] == 90_000_000
    assert month["surplus"] == 10_000_000
    assert month["covered"] is True


# -- the sentence over the number --


def test_both_bases_travel_in_the_payload_because_they_are_different_bases():
    """One basis per figure, every basis written on its face.

    The reader who tries to reconcile the contribution side against
    Income should be told why it will not match before they try.
    """
    payload = report([job()], [overhead()])

    assert "the month the job was booked" in payload["contribution_basis"]
    assert "the day the money left the account" in payload["overhead_basis"]


def test_nothing_in_the_payload_proposes_a_floor_or_a_price():
    """Show, don't suggest - asserted mechanically, not just believed.

    #14's own wording: this informs the founder's pricing judgement and
    the global floor, and never computes either. A key called
    `recommended_floor` would be read as a recommendation the moment it
    existed.
    """
    payload = report([job()], [overhead()])
    keys = set(payload) | set(payload["total"]) | set(payload["months"][0])
    forbidden = ("floor", "recommend", "suggest", "target", "should", "advice")

    assert not [key for key in keys if any(word in key for word in forbidden)]
    assert any(caveat["figure"] == "the margin floor" for caveat in CAVEATS)
    assert payload["caveats"] == CAVEATS


def test_the_caveats_say_why_a_surplus_may_not_be_one():
    """Asserted by content, because deleting the honesty must fail.

    #123 was a correct figure under a description that had drifted wider
    than it. These two sentences are the ones a founder needs before
    acting on a surplus, and a `not-empty` assertion would not keep them.
    """
    figures = {caveat["figure"]: caveat["why"] for caveat in CAVEATS}

    assert "whole life" in figures["contribution"]
    assert "still spending" in figures["open jobs' margin"]

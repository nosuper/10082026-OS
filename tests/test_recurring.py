"""Pure-python tests for auraos.lib.recurring - no Frappe required.

Working out that August comes after July is not what these tests are
for. What they pin is **when a standing cost is allowed to become a
payment**, which is the whole risk in the feature:

- **A template is never a payment.** This module computes what is due
  and stops there, because a `Company Expense` posts to the cash ledger
  and an invented posting makes the cash screens disagree with the bank.
  One of these tests exists to fail if a function that writes payments
  ever appears here.
- **Nothing is due for a month that has not started.** Rent can be paid
  in advance by hand; a screen offering next quarter's salaries is a
  standing invitation to post money that is still in the bank.
- **Recorded is a fact about the payments, not a stamp on the
  template.** Delete the payment and the month comes due again, with
  nothing to reset.
- **The 31st has to survive February.** A clamped day keeps a payment
  inside the month it belongs to; a rolled-forward one files February's
  rent in March and quietly shortens February on the break-even screen.
"""

from datetime import date

import auraos.lib.recurring as recurring
from auraos.lib.recurring import (
    DUE_BASIS,
    due,
    due_day,
    month_bounds,
    offerable_months,
    recorded_months,
    runs_in,
    schedule,
)

Q3 = (date(2026, 7, 1), date(2026, 9, 30))
IN_SEPTEMBER = date(2026, 9, 10)


def template(**overrides):
    """One standing cost, as the doctype stores it."""
    row = {
        "name": "RO-00001",
        "label": "Tiền thuê văn phòng",
        "amount": 30_000_000,
        "category": "Thuê văn phòng",
        "paid_from": "Tài khoản ngân hàng",
        "supplier": "Chị Hà",
        "description": "Thuê văn phòng tầng 3",
        "day_of_month": 5,
        "starts_on": date(2026, 1, 1),
        "ends_on": None,
        "disabled": 0,
    }
    row.update(overrides)
    return row


def payment(**overrides):
    """One Company Expense written from a template."""
    row = {
        "name": "CE-2026-00001",
        "recurring": "RO-00001",
        "recurring_month": "2026-07",
    }
    row.update(overrides)
    return row


# -- the day a standing cost falls --


def test_the_thirty_first_survives_a_short_month():
    """A template that says the 31st is a template about month end.

    Clamping down keeps the payment inside the month it belongs to.
    Rolling forward would file February's rent in March, which shortens
    February on the break-even screen for a reason nobody could see.
    """
    assert due_day("2026-02", 31) == date(2026, 2, 28)
    assert due_day("2028-02", 31) == date(2028, 2, 29)
    assert due_day("2026-04", 31) == date(2026, 4, 30)
    assert due_day("2026-07", 31) == date(2026, 7, 31)


def test_a_missing_or_nonsensical_day_means_the_first():
    """Where rent and salaries land anyway, and correctable on the
    payment rather than a blank to fill on the template."""
    assert due_day("2026-07", None) == date(2026, 7, 1)
    assert due_day("2026-07", 0) == date(2026, 7, 1)
    assert due_day("2026-07", "") == date(2026, 7, 1)
    assert due_day("2026-07", "rằm") == date(2026, 7, 1)


def test_month_bounds_are_the_calendar_month():
    assert month_bounds("2026-02") == (date(2026, 2, 1), date(2026, 2, 28))


# -- which months a standing cost runs in --


def test_a_cost_agreed_mid_month_runs_that_whole_month():
    """Rent agreed on the 20th is still that month's rent.

    The founder correcting a first payment's amount is a smaller ask than
    the founder wondering why August is missing entirely.
    """
    started_late = template(starts_on=date(2026, 8, 20))

    assert runs_in(started_late, "2026-07") is False
    assert runs_in(started_late, "2026-08") is True


def test_a_cost_stops_at_the_end_of_the_month_it_ended_in():
    ended = template(ends_on=date(2026, 8, 3))

    assert runs_in(ended, "2026-08") is True
    assert runs_in(ended, "2026-09") is False


def test_a_disabled_template_runs_nowhere():
    """A pause the founder can take without deleting the history of what
    the company used to pay for."""
    assert runs_in(template(disabled=1), "2026-08") is False


def test_a_template_with_no_start_date_fails_closed():
    """`starts_on` is required on the record; a row that has lost it must
    run in no month rather than in every month since the epoch."""
    assert runs_in(template(starts_on=None), "2026-08") is False


# -- nothing is due before its month has begun --


def test_a_month_becomes_offerable_on_its_first_day_and_not_before():
    """Offering a month still ahead invites a posting for money that is
    still in the bank."""
    assert offerable_months(*Q3, date(2026, 6, 30)) == []
    assert offerable_months(*Q3, date(2026, 7, 1)) == ["2026-07"]
    assert offerable_months(*Q3, date(2026, 8, 31)) == ["2026-07", "2026-08"]
    assert offerable_months(*Q3, date(2026, 12, 1)) == [
        "2026-07",
        "2026-08",
        "2026-09",
    ]


def test_nothing_is_due_for_a_month_that_has_not_started():
    ahead = due([template()], [], date(2026, 10, 1), date(2026, 12, 31), IN_SEPTEMBER)

    assert ahead["rows"] == []
    assert ahead["amount_total"] == 0


# -- what has already been written down --


def test_a_month_with_a_payment_against_it_is_not_due_again():
    """The guard against the founder paying the rent twice on paper."""
    backlog = due([template()], [payment(recurring_month="2026-07")], *Q3, IN_SEPTEMBER)

    assert [row["month"] for row in backlog["rows"]] == ["2026-08", "2026-09"]


def test_deleting_the_payment_makes_the_month_due_again():
    """Recorded is asked of the payments, never of a stamp on the
    template - so there is nothing to reset when one is deleted."""
    with_it = due([template()], [payment(recurring_month="2026-08")], *Q3, IN_SEPTEMBER)
    without_it = due([template()], [], *Q3, IN_SEPTEMBER)

    assert "2026-08" not in [row["month"] for row in with_it["rows"]]
    assert "2026-08" in [row["month"] for row in without_it["rows"]]


def test_a_payment_naming_no_month_pins_nothing():
    """A hand-entered overhead is not a template's month.

    An expense with a template but no month - or a month but no template
    - is somebody's manual row, and must not silently mark a month
    covered.
    """
    assert recorded_months([payment(recurring_month=None)]) == set()
    assert recorded_months([payment(recurring="")]) == set()
    assert recorded_months([payment()]) == {("RO-00001", "2026-07")}


# -- the backlog itself --


def test_three_months_behind_is_three_rows():
    """Each month is its own payment, and the founder may record one
    without the others."""
    backlog = due([template()], [], *Q3, IN_SEPTEMBER)

    assert backlog["count"] == 3
    assert [row["month"] for row in backlog["rows"]] == [
        "2026-07",
        "2026-08",
        "2026-09",
    ]
    assert [row["due_on"] for row in backlog["rows"]] == [
        date(2026, 7, 5),
        date(2026, 8, 5),
        date(2026, 9, 5),
    ]
    assert backlog["amount_total"] == 90_000_000


def test_the_oldest_month_comes_first():
    """The backlog is worked from the end that has been waiting longest,
    not from the end that is easiest."""
    backlog = due(
        [template(name="RO-2", day_of_month=1), template(name="RO-1", day_of_month=20)],
        [],
        date(2026, 7, 1),
        date(2026, 8, 31),
        IN_SEPTEMBER,
    )

    assert [(row["month"], row["template"]) for row in backlog["rows"]] == [
        ("2026-07", "RO-2"),
        ("2026-07", "RO-1"),
        ("2026-08", "RO-2"),
        ("2026-08", "RO-1"),
    ]


def test_a_due_row_is_shaped_like_the_payment_it_would_become():
    """The founder is about to confirm a payment, so the screen shows
    them the payment rather than the template behind it."""
    row = due([template()], [], date(2026, 7, 1), date(2026, 7, 31), IN_SEPTEMBER)[
        "rows"
    ][0]

    assert row["amount"] == 30_000_000
    assert row["category"] == "Thuê văn phòng"
    assert row["paid_from"] == "Tài khoản ngân hàng"
    assert row["supplier"] == "Chị Hà"
    assert row["description"] == "Thuê văn phòng tầng 3"
    assert row["due_on"] == date(2026, 7, 5)


def test_due_says_it_is_due_and_not_that_it_is_late():
    """Whether the landlord has been paid is a fact about a bank account.

    A row here claiming "overdue" would be asserting something this app
    cannot know, from a table that only records what has been typed.
    """
    assert DUE_BASIS == due([], [], *Q3, IN_SEPTEMBER)["basis"]
    assert "not a claim that the money is late" in DUE_BASIS


def test_this_module_writes_nothing():
    """A template is never a payment, and the seam is asserted.

    A `Company Expense` posts to the cash ledger, so a function here that
    created one would be inventing money movements. Nothing in this
    module may name a doctype or reach a database, and the import list is
    where that starts to go wrong.
    """
    assert not hasattr(recurring, "frappe")
    source = open(recurring.__file__, encoding="utf-8").read()
    assert "import frappe" not in source


# -- what the company costs to run --


def test_the_schedule_is_the_commitment_and_not_the_backlog():
    """One number is what the company owes every month whether or not it
    has been written down; the other is what has not been written down.

    A screen showing one where the reader expected the other would be
    wrong in whichever direction the month happened to fall, which is why
    they are two functions.
    """
    hired_in_august = template(name="RO-2", amount=60_000_000, starts_on=date(2026, 8, 1))

    plan = schedule([template(), hired_in_august], *Q3)

    assert [month["committed"] for month in plan["months"]] == [
        30_000_000,
        90_000_000,
        90_000_000,
    ]
    assert plan["committed_total"] == 210_000_000
    # As it stands today, not averaged: an average over a range in which
    # somebody was hired describes a company that never existed.
    assert plan["monthly_committed"] == 90_000_000


def test_a_schedule_over_no_months_commits_to_nothing():
    plan = schedule([template()], date(2026, 9, 30), date(2026, 7, 1))

    assert plan["months"] == []
    assert plan["monthly_committed"] == 0

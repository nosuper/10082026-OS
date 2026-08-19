"""Pure-python tests for auraos.lib.ledger - no Frappe required.

Issue #99. The ledger is the one record in this app that reads as
authoritative about money, so the four decisions it rests on are pinned
here rather than only in the Frappe-side test:

- **The sign is the direction**, so a balance is a sum. `direction_of`
  reads the word off the number, and zero is refused rather than given
  one.
- **The origin is a pair**, doctype and name, because #100 posts three
  more flows through this door and a client payment's origin is a
  milestone row rather than a record of its own.
- **Posting twice does nothing the second time.** `posting` is asked what
  the ledger should say against what it already says, and a movement
  already on file returns "nothing" however many callers ask.
- **No account is not a refusal.** Money that moved somewhere nobody has
  named posts nothing and disturbs nothing; money that never moved takes
  its entry back out. The two are told apart by `moved`, which is judged
  without an account at all.

The Frappe-side test (auraos/auraos/doctype/cash_ledger_entry/
test_cash_ledger.py) proves the doctype and the save path go through
this module.
"""

from datetime import date, datetime

import pytest

from auraos.lib.ledger import (
    CLIENT_PAYMENT,
    FLOWS,
    IN,
    JOB_EXPENSE,
    NOTHING,
    OUT,
    POST,
    REPOST,
    SOURCES,
    UNPOST,
    Entry,
    balance,
    client_payment,
    collected,
    direction_of,
    entry_name,
    posting,
    restated,
    restates,
)
from auraos.lib.milestones import INVOICED, PAID, REQUESTED

PAID_MILESTONE = {
    "name": "abc123",
    "title": "Đặt cọc (không hoàn lại)",
    "status": PAID,
    "amount": 55_000_000,
    "paid_on": datetime(2026, 8, 19, 9, 30),
}

ACCOUNT = "Vietcombank - main"


def milestone(**changes):
    return {**PAID_MILESTONE, **changes}


# -- the sign is the direction --


@pytest.mark.parametrize("amount", [1, 55_000_000, 0.6])
def test_a_positive_amount_came_in(amount):
    assert direction_of(amount) == IN


@pytest.mark.parametrize("amount", [-1, -55_000_000, -0.6])
def test_a_negative_amount_went_out(amount):
    assert direction_of(amount) == OUT


@pytest.mark.parametrize("amount", [0, None, 0.4, -0.4])
def test_zero_moves_no_money_and_has_no_direction(amount):
    """Including amounts that round to nothing - VND has no smaller unit."""
    with pytest.raises(ValueError):
        direction_of(amount)


def test_a_balance_is_a_sum_not_a_case_analysis():
    """The whole reason the direction is a sign: #101 adds a column up."""
    entries = [
        Entry(ACCOUNT, 55_000_000, date(2026, 8, 1), *_origin("a")),
        Entry(ACCOUNT, -20_000_000, date(2026, 8, 2), *_origin("b")),
        Entry(ACCOUNT, 27_500_000, date(2026, 8, 3), *_origin("c")),
    ]

    assert balance(entries) == 62_500_000


def test_an_account_with_no_entries_is_worth_nothing_not_an_error():
    assert balance([]) == 0


def test_a_balance_adds_up_stored_rows_too():
    """#101 sums rows out of a query, not dataclasses."""
    assert balance([{"amount": 55_000_000.0}, {"amount": -5_000_000.0}]) == 50_000_000


def _origin(source_name):
    return (CLIENT_PAYMENT, SOURCES[CLIENT_PAYMENT], source_name)


# -- the origin is a pair, and it names the entry --


def test_every_flow_the_ledger_will_ever_carry_is_named_now():
    """#100 posts the other three; widening a Select later is a migration."""
    assert FLOWS == (
        "Client payment",
        "Job expense",
        "Crew advance",
        "Float settlement",
    )
    assert set(SOURCES) == set(FLOWS)


def test_a_client_payment_comes_from_a_milestone_row_not_a_record():
    assert SOURCES[CLIENT_PAYMENT] == "Job Payment Milestone"


def test_an_entry_is_named_after_the_movement_it_records():
    assert entry_name(CLIENT_PAYMENT, "abc123") == "PAY-abc123"


def test_two_flows_that_share_a_source_name_are_two_entries():
    """The pair, not the name: doctypes number their own rows."""
    assert entry_name(CLIENT_PAYMENT, "0001") != entry_name(JOB_EXPENSE, "0001")


# -- what a collected milestone is worth --


def test_a_paid_milestone_moved_money():
    assert collected(PAID_MILESTONE)


@pytest.mark.parametrize("status", [None, REQUESTED, INVOICED])
def test_a_milestone_short_of_paid_moved_nothing(status):
    assert not collected(milestone(status=status))


def test_a_milestone_marked_paid_with_no_day_moved_nothing_yet():
    assert not collected(milestone(paid_on=None))


def test_a_milestone_billing_nothing_is_a_placeholder_not_a_payment():
    """0% of the quote is a real row in a plan; it is not money."""
    assert not collected(milestone(amount=0))


def test_a_collected_milestone_records_amount_date_account_and_origin():
    entry = client_payment(PAID_MILESTONE, ACCOUNT, job="JOB-0001")

    assert entry.amount == 55_000_000
    assert entry.direction == IN
    assert entry.entry_date == date(2026, 8, 19)
    assert entry.account == ACCOUNT
    assert entry.flow == CLIENT_PAYMENT
    assert entry.source_doctype == "Job Payment Milestone"
    assert entry.source_name == "abc123"
    assert entry.job == "JOB-0001"
    assert entry.description == "Đặt cọc (không hoàn lại)"


def test_the_day_the_money_landed_is_the_day_it_was_marked():
    """Not the day of the save that happens to reconcile it."""
    entry = client_payment(milestone(paid_on="2026-07-04 23:15:00"), ACCOUNT)

    assert entry.entry_date == date(2026, 7, 4)


def test_a_milestone_nobody_collected_earns_no_entry():
    assert client_payment(milestone(status=INVOICED), ACCOUNT) is None


def test_a_collection_with_no_account_earns_no_entry_either():
    """But it still moved money - see the posting rules below."""
    assert client_payment(PAID_MILESTONE, None) is None
    assert collected(PAID_MILESTONE)


# -- posting the same money twice --


def posted(**changes):
    return client_payment(milestone(**changes), ACCOUNT, job="JOB-0001")


def test_the_first_caller_posts():
    assert posting(wanted=posted(), existing=None, moved=True) == POST


def test_the_second_caller_posts_nothing():
    """A ledger that can double-post reads as authoritative and is wrong."""
    entry = posted()

    assert posting(wanted=entry, existing=entry, moved=True) == NOTHING


def test_a_third_and_a_fourth_do_nothing_either():
    entry = posted()
    for _ in range(3):
        assert posting(wanted=entry, existing=entry, moved=True) == NOTHING


def test_walking_a_milestone_back_out_of_paid_takes_its_entry_with_it():
    """The same rule stamps_for follows: stepping back clears what it undid."""
    assert posting(wanted=None, existing=posted(), moved=False) == UNPOST


def test_a_milestone_that_was_never_paid_has_nothing_to_take_back():
    assert posting(wanted=None, existing=None, moved=False) == NOTHING


def test_money_that_moved_somewhere_nobody_named_posts_nothing():
    """The fourth acceptance criterion, and it is not a refusal."""
    assert posting(wanted=None, existing=None, moved=True) == NOTHING


def test_a_later_save_with_no_account_leaves_a_posted_entry_alone():
    """Not naming an account today is not evidence about yesterday."""
    assert posting(wanted=None, existing=posted(), moved=True) == NOTHING


def test_a_restated_amount_is_reposted():
    assert posting(wanted=posted(amount=60_000_000), existing=posted(), moved=True) == (
        REPOST
    )


def test_a_restated_day_is_reposted():
    assert posting(
        wanted=posted(paid_on=datetime(2026, 9, 1)), existing=posted(), moved=True
    ) == REPOST


def test_where_the_money_landed_is_decided_once():
    """A default that changed months later is not news about that day."""
    on_file = posted()
    today = client_payment(PAID_MILESTONE, "Cash box", job="JOB-0001")

    assert not restates(on_file, today)
    assert posting(wanted=today, existing=on_file, moved=True) == NOTHING


def test_a_repost_lands_back_in_the_account_it_came_from():
    on_file = posted()
    today = client_payment(
        milestone(amount=60_000_000), "Cash box", job="JOB-0001"
    )

    assert restated(on_file, today).account == ACCOUNT
    assert restated(on_file, today).amount == 60_000_000


# -- what a stored row reads back as --


def test_an_entry_read_back_out_of_a_database_compares_equal():
    """Currency comes back a float and a Date as a date; neither is a change."""
    stored = Entry(
        account=ACCOUNT,
        amount=55_000_000.0,
        entry_date="2026-08-19",
        flow=CLIENT_PAYMENT,
        source_doctype=SOURCES[CLIENT_PAYMENT],
        source_name="abc123",
        job="JOB-0001",
        description="Đặt cọc (không hoàn lại)",
    )

    assert stored == client_payment(PAID_MILESTONE, ACCOUNT, job="JOB-0001")
    assert not restates(stored, client_payment(PAID_MILESTONE, ACCOUNT))

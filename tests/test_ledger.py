"""Pure-python tests for auraos.lib.ledger - no Frappe required.

Issues #99 and #100. The ledger is the one record in this app that reads
as authoritative about money, so the four decisions it rests on are
pinned here rather than only in the Frappe-side test:

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

#100 adds the other three flows and with them the question each one has
to answer for itself: what "moved" means here. An expense logged against
a float moved nobody's money out of an account, an advance nobody has
transferred yet is still in the company's hands, and a settlement is a
transfer recorded after the fact. Each is pinned below.

The Frappe-side test (auraos/auraos/doctype/cash_ledger_entry/
test_cash_ledger.py) proves the doctype and the save path go through
this module.
"""

from dataclasses import asdict
from datetime import date, datetime

import pytest

from auraos.lib.ledger import (
    CLIENT_PAYMENT,
    CREW_ADVANCE,
    FLOAT_SETTLEMENT,
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
    Holding,
    balance,
    client_payment,
    collected,
    company_expense,
    crew_advance,
    direction_of,
    entry_name,
    entry_view,
    float_settlement,
    holdings,
    job_expense,
    paid_by_company,
    posting,
    restated,
    restates,
    settled,
    source_of,
    total_held,
    transferred,
)
from auraos.lib.milestones import INVOICED, PAID, REQUESTED
from auraos.lib.settlement import FROM_ADVANCE, FROM_COMPANY

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


def test_the_flows_the_ledger_carries_are_named_here():
    """The vocabulary, pinned - and it has been widened once.

    #99 named four before three of them posted, on the reasoning that
    widening a Select afterwards is a migration. That reasoning held for
    #100 and it was right; it did not hold forever. #14/#109 needed a
    fifth, because the company pays for things that belong to no job and
    the ledger had no way to say so.

    This test is not here to freeze the list. It is here so that
    widening it is a deliberate act with a failing test in front of it,
    rather than something a later ticket does in passing - which is
    exactly what happened here, and what should happen next time.
    """
    assert FLOWS == (
        "Client payment",
        "Job expense",
        "Crew advance",
        "Float settlement",
        "Company expense",
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


# -- money out: the vendors the company paid itself --

COMPANY_EXPENSE = {
    "name": "EXP-00007",
    "job": "JOB-0001",
    "amount": 3_000_000,
    "spent_on": date(2026, 8, 10),
    "paid_from": FROM_COMPANY,
    "category": "Thiết bị",
    "description": "Thuê ống kính Sigma",
}


def expense(**changes):
    return {**COMPANY_EXPENSE, **changes}


def paid(**changes):
    return job_expense(expense(**changes), ACCOUNT)


def test_an_expense_the_company_paid_moved_the_companys_money():
    assert paid_by_company(COMPANY_EXPENSE)


def test_an_expense_paid_out_of_a_float_moved_none_of_it():
    """The đồng left the company the day the advance was transferred.

    Posting it again here would have the same money leaving twice, and
    the float's own arithmetic is closed by its settlement.
    """
    assert not paid_by_company(expense(paid_from=FROM_ADVANCE))
    assert job_expense(expense(paid_from=FROM_ADVANCE), ACCOUNT) is None


def test_an_expense_naming_no_source_of_funds_is_a_float_expense():
    """What the column defaults to, and what a row older than it means."""
    assert not paid_by_company(expense(paid_from=None))


def test_an_expense_nobody_dated_has_not_been_paid_yet():
    assert not paid_by_company(expense(spent_on=None))


def test_an_expense_of_nothing_is_not_a_payment():
    assert not paid_by_company(expense(amount=0))


def test_paying_a_vendor_records_amount_date_account_and_origin():
    entry = paid()

    assert entry.amount == -3_000_000
    assert entry.direction == OUT
    assert entry.entry_date == date(2026, 8, 10)
    assert entry.account == ACCOUNT
    assert entry.flow == JOB_EXPENSE
    assert entry.source_doctype == "Job Expense"
    assert entry.source_name == "EXP-00007"
    assert entry.job == "JOB-0001"
    assert entry.description == "Thuê ống kính Sigma"


def test_an_expense_nobody_described_reads_as_its_category():
    assert paid(description=None).description == "Thiết bị"


def test_an_expense_with_no_account_earns_no_entry_either():
    assert job_expense(COMPANY_EXPENSE, None) is None
    assert paid_by_company(COMPANY_EXPENSE)


def test_an_expense_entry_is_named_after_the_expense():
    assert entry_name(JOB_EXPENSE, "EXP-00007") == "EXP-EXP-00007"


def test_paying_the_same_vendor_payment_twice_posts_once():
    assert posting(wanted=paid(), existing=paid(), moved=True) == NOTHING


def test_correcting_an_expense_onto_a_float_takes_its_entry_back():
    """It was never the company account's money that moved; the advance was."""
    corrected = expense(paid_from=FROM_ADVANCE)

    assert posting(
        wanted=job_expense(corrected, ACCOUNT),
        existing=paid(),
        moved=paid_by_company(corrected),
    ) == UNPOST


def test_a_restated_expense_amount_is_reposted():
    assert posting(wanted=paid(amount=3_500_000), existing=paid(), moved=True) == REPOST


# -- money out: cash handed to whoever is spending it --

ADVANCE = {
    "name": "ADV-00003",
    "job": "JOB-0001",
    "amount": 10_000_000,
    "transferred_on": date(2026, 8, 1),
    "recipient": "linh@auraos.test",
}


def advance(**changes):
    return {**ADVANCE, **changes}


def handed_over(**changes):
    return crew_advance(advance(**changes), ACCOUNT)


def test_an_advance_that_was_transferred_moved_money():
    assert transferred(ADVANCE)


def test_an_advance_nobody_transferred_is_still_the_companys_cash():
    """A day is what says the cash changed hands; an amount cannot.

    A Currency column is never null, so 0 would have to mean both "no
    money" and "nobody has recorded this yet".
    """
    assert not transferred(advance(transferred_on=None))
    assert crew_advance(advance(transferred_on=None), ACCOUNT) is None


def test_issuing_an_advance_records_amount_date_account_and_origin():
    entry = handed_over()

    assert entry.amount == -10_000_000
    assert entry.direction == OUT
    assert entry.entry_date == date(2026, 8, 1)
    assert entry.account == ACCOUNT
    assert entry.flow == CREW_ADVANCE
    assert entry.source_doctype == "Job Advance"
    assert entry.source_name == "ADV-00003"
    assert entry.job == "JOB-0001"
    assert entry.description == "linh@auraos.test"


def test_an_advance_with_no_account_earns_no_entry_either():
    assert crew_advance(ADVANCE, None) is None
    assert transferred(ADVANCE)


def test_an_advance_entry_is_named_after_the_advance():
    assert entry_name(CREW_ADVANCE, "ADV-00003") == "ADV-ADV-00003"


def test_issuing_the_same_advance_twice_posts_once():
    assert posting(wanted=handed_over(), existing=handed_over(), moved=True) == NOTHING


def test_an_advance_deleted_was_an_advance_never_handed_over():
    assert posting(wanted=None, existing=handed_over(), moved=False) == UNPOST


# -- either way: closing a float --

RETURNED = {
    "name": "STL-00002",
    "job": "JOB-0001",
    "amount": 2_000_000,
    "settled_on": datetime(2026, 8, 20, 17, 5),
    "recipient": "linh@auraos.test",
}


def closing(**changes):
    return {**RETURNED, **changes}


def closed(**changes):
    return float_settlement(closing(**changes), ACCOUNT)


def test_a_holder_handing_the_remainder_back_is_money_in():
    entry = closed()

    assert entry.amount == 2_000_000
    assert entry.direction == IN


def test_the_company_topping_a_holder_up_is_money_out():
    """One entry either way: the settlement is already signed the way the
    ledger signs money, so nothing here decides the direction twice."""
    entry = closed(amount=-1_500_000)

    assert entry.amount == -1_500_000
    assert entry.direction == OUT


def test_settling_records_the_day_the_transfer_was_made():
    assert closed().entry_date == date(2026, 8, 20)


def test_settling_records_account_and_origin():
    entry = closed()

    assert entry.account == ACCOUNT
    assert entry.flow == FLOAT_SETTLEMENT
    assert entry.source_doctype == "Job Settlement"
    assert entry.source_name == "STL-00002"
    assert entry.job == "JOB-0001"
    assert entry.description == "linh@auraos.test"


def test_a_settlement_nobody_made_moved_nothing():
    assert not settled(closing(settled_on=None))
    assert float_settlement(closing(settled_on=None), ACCOUNT) is None


def test_an_even_float_has_nothing_to_settle():
    assert not settled(closing(amount=0))


def test_a_settlement_with_no_account_earns_no_entry_either():
    assert float_settlement(RETURNED, None) is None
    assert settled(RETURNED)


def test_a_settlement_entry_is_named_after_the_settlement():
    assert entry_name(FLOAT_SETTLEMENT, "STL-00002") == "STL-STL-00002"


def test_settling_the_same_float_twice_posts_once():
    assert posting(wanted=closed(), existing=closed(), moved=True) == NOTHING


def test_a_settlement_reversed_takes_its_entry_back():
    """Its numbers are frozen, so deleting it is the only way back."""
    assert posting(wanted=None, existing=closed(), moved=False) == UNPOST


# -- the flows in one account --


def test_every_flow_writes_its_own_entry_for_the_same_record_name():
    """Doctypes number their own rows; the pair is what keeps them apart."""
    assert len({entry_name(flow, "0001") for flow in FLOWS}) == len(FLOWS)


def test_a_float_advanced_spent_and_settled_leaves_the_company_out_what_was_spent():
    """The whole reason a float expense posts nothing of its own.

    10M handed over, 12M spent out of it, the shortfall topped up: the
    company is out 12M, counted once.
    """
    entries = [
        handed_over(),
        job_expense(expense(amount=12_000_000, paid_from=FROM_ADVANCE), ACCOUNT),
        closed(amount=-2_000_000),
    ]

    assert balance([entry for entry in entries if entry]) == -12_000_000


def test_the_four_flows_add_up_in_one_column():
    entries = [
        client_payment(PAID_MILESTONE, ACCOUNT),
        paid(),
        handed_over(),
        closed(),
    ]

    assert balance(entries) == 55_000_000 - 3_000_000 - 10_000_000 + 2_000_000


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


# -- what the founder sees: an account, its balance, its movements (#101) --
#
# The screen's arithmetic, pinned without a database. Every figure #101
# prints is made here out of the entries: there is no function below
# that accepts a balance, and none that stores one.

CASH_BOX = "Két tiền mặt"


def test_every_account_gets_a_balance_made_of_its_own_entries():
    entries = [
        Entry(ACCOUNT, 55_000_000, date(2026, 8, 1), *_origin("a")),
        Entry(CASH_BOX, -3_000_000, date(2026, 8, 2), *_origin("b")),
        Entry(ACCOUNT, -10_000_000, date(2026, 8, 3), *_origin("c")),
    ]

    assert holdings([ACCOUNT, CASH_BOX], entries) == [
        Holding(ACCOUNT, 45_000_000, 2),
        Holding(CASH_BOX, -3_000_000, 1),
    ]


def test_an_account_with_no_entries_holds_zero_rather_than_erroring():
    """The studio that has never posted anything opens Finance to a 0."""
    assert holdings([ACCOUNT], []) == [Holding(ACCOUNT, 0, 0)]


def test_a_company_with_no_accounts_at_all_holds_nothing():
    assert holdings([], []) == []
    assert total_held(holdings([], [])) == 0


def test_the_accounts_come_back_in_the_order_they_were_given():
    """The caller orders them; adding up is all this does."""
    assert [held.account for held in holdings([CASH_BOX, ACCOUNT], [])] == [
        CASH_BOX,
        ACCOUNT,
    ]


def test_the_total_is_the_accounts_added_up():
    entries = [
        Entry(ACCOUNT, 55_000_000, date(2026, 8, 1), *_origin("a")),
        Entry(CASH_BOX, -3_000_000, date(2026, 8, 2), *_origin("b")),
    ]

    assert total_held(holdings([ACCOUNT, CASH_BOX], entries)) == 52_000_000


def test_the_total_of_the_four_flows_is_the_same_sum_the_ledger_makes():
    """One account holding a mix of everything - no case analysis anywhere."""
    entries = [entry for entry in (client_payment(PAID_MILESTONE, ACCOUNT), paid(), handed_over(), closed()) if entry]

    assert total_held(holdings([ACCOUNT], entries)) == balance(entries)


def test_a_balance_adds_up_stored_rows_out_of_a_query_too():
    rows = [
        {"account": ACCOUNT, "amount": 55_000_000.0},
        {"account": ACCOUNT, "amount": -5_000_000.0},
    ]

    assert holdings([ACCOUNT], rows) == [Holding(ACCOUNT, 50_000_000, 2)]


# -- an origin is a doctype and a name; a source is something recognisable --


def test_a_source_is_what_the_origin_calls_itself():
    entry = client_payment(PAID_MILESTONE, ACCOUNT, job="JOB-0001")

    assert source_of(entry, "TVC Tết Vinamilk") == "Đặt cọc (không hoàn lại)"


def test_an_origin_with_no_title_of_its_own_reads_as_its_job():
    entry = job_expense(expense(description=None, category=None), ACCOUNT)

    assert source_of(entry, "TVC Tết Vinamilk") == "TVC Tết Vinamilk"


def test_an_origin_with_no_title_and_no_job_still_says_something_true():
    entry = job_expense(expense(description=None, category=None, job=None), ACCOUNT)

    assert source_of(entry, None) == JOB_EXPENSE


def test_a_source_is_never_a_doctype_and_a_hash():
    entry = client_payment(PAID_MILESTONE, ACCOUNT, job="JOB-0001")

    for shown in (source_of(entry, "TVC Tết Vinamilk"), source_of(entry, None)):
        assert entry.source_doctype not in shown
        assert entry.source_name not in shown


# -- the shape a screen reads one movement in --


def test_a_movement_reads_as_a_day_a_signed_amount_and_a_source():
    view = entry_view(
        {
            "name": "PAY-abc123",
            "account": ACCOUNT,
            "amount": 55_000_000.0,
            "entry_date": datetime(2026, 8, 19, 9, 30),
            "flow": CLIENT_PAYMENT,
            "source_doctype": SOURCES[CLIENT_PAYMENT],
            "source_name": "abc123",
            "job": "JOB-0001",
            "description": "Đặt cọc (không hoàn lại)",
        },
        job_title="TVC Tết Vinamilk",
    )

    assert view == {
        "name": "PAY-abc123",
        "entry_date": "2026-08-19",
        "amount": 55_000_000,
        "direction": IN,
        "flow": CLIENT_PAYMENT,
        "source": "Đặt cọc (không hoàn lại)",
        "source_doctype": SOURCES[CLIENT_PAYMENT],
        "source_name": "abc123",
        "job": "JOB-0001",
        "job_title": "TVC Tết Vinamilk",
    }
    assert type(view["amount"]) is int


def test_the_direction_a_movement_reads_as_comes_off_its_own_sign():
    """Never off the stored column, which is where the two could differ."""
    view = entry_view({**asdict(paid()), "name": "EXP-e1", "direction": IN})

    assert view["direction"] == OUT


# -- the flow that has no job (#14/#109) --


def test_an_overhead_posts_without_a_job():
    """Rent belongs to the company, not to any shoot.

    `Entry.job` was optional from the day it was written and nothing
    used that until now. A company expense is the case it was left open
    for - and a screen reading this entry must be able to show a
    movement with no job rather than inventing one.
    """
    entry = company_expense(
        {
            "name": "CE-2026-00001",
            "amount": 2_200_000,
            "spent_on": date(2026, 8, 10),
            "description": "Cơm khách",
        },
        "Bank",
    )
    assert entry.job is None
    assert entry.flow == "Company expense"
    assert entry.source_doctype == "Company Expense"


def test_an_overhead_is_money_leaving():
    """Signed, like every other payment out - the direction is not a
    second opinion about the amount."""
    entry = company_expense(
        {"name": "CE-1", "amount": 2_200_000, "spent_on": date(2026, 8, 10)}, "Bank"
    )
    assert entry.amount == -2_200_000


def test_an_overhead_always_posts_where_a_job_expense_sometimes_does_not():
    """A job expense asks `paid_by_company` first, because a producer
    spending their float moves no company money that day. An overhead has
    no float to come out of, so there is no case here that posts nothing
    - only the case where nobody has named an account."""
    paid = {"name": "CE-1", "amount": 500_000, "spent_on": date(2026, 8, 10)}
    assert company_expense(paid, "Bank") is not None
    assert company_expense(paid, None) is None


def test_an_overhead_and_a_job_expense_with_one_name_do_not_collide():
    """Two doctypes number their own rows, so the flow code is what keeps
    their entries apart on a primary key."""
    assert entry_name("Company expense", "0001") != entry_name("Job expense", "0001")

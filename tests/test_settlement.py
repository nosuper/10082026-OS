"""Pure-python tests for auraos.lib.settlement - no Frappe required.

Two decisions live here (T8 / spec #2, stories 30–34), both worth
pinning independently of the framework:

- **Whose money is it.** An advance puts company cash in someone's
  hands; an expense paid from that float hands it back as receipts.
  What is left over is what one of them owes the other, and the
  direction has to be named - "2.500.000" alone never says who pays.
  Money the company paid directly is job spend that settles nothing.
- **Categories mirror the quote.** Actual-vs-quoted per package is
  supposed to fall out with no extra work (story 32), which only holds
  if the categories an expense may carry are exactly the entries the
  client was quoted - packages, plus any line quoted on its own.

The Frappe-side tests (auraos/auraos/doctype/job/test_job_money.py)
prove the doctypes and the API actually go through these functions.
"""

from decimal import Decimal as D

from auraos.lib.settlement import (
    EVEN,
    FROM_ADVANCE,
    FROM_COMPANY,
    RETURN,
    TOP_UP,
    UNCATEGORISED,
    categories,
    category_actuals,
    float_for,
    floats,
    totals,
)

LINH = "linh@aura.local"
CHUNG = "chung@aura.local"


def advance(amount, recipient=LINH):
    return {"recipient": recipient, "amount": amount}


def expense(amount, paid_by=LINH, paid_from=FROM_ADVANCE, category=None):
    return {
        "paid_by": paid_by,
        "amount": amount,
        "paid_from": paid_from,
        "category": category,
    }


def settlement(amount, recipient=LINH):
    return {"recipient": recipient, "amount": amount}


# -- the float: advances out, receipts back --


def test_a_job_nobody_has_been_advanced_for_has_no_floats():
    assert floats([], []) == []


def test_an_advance_alone_is_cash_the_holder_still_owes_back():
    (held,) = floats([advance(20_000_000)], [])

    assert held.holder == LINH
    assert held.advanced == D(20_000_000)
    assert held.spent == D(0)
    assert held.amount == D(20_000_000)
    assert held.direction == RETURN


def test_expenses_paid_from_the_float_eat_into_it():
    (held,) = floats(
        [advance(20_000_000)],
        [expense(12_000_000), expense(5_500_000)],
    )

    assert held.spent == D(17_500_000)
    assert held.amount == D(2_500_000)
    assert held.direction == RETURN


def test_spending_the_float_exactly_settles_to_even():
    (held,) = floats([advance(20_000_000)], [expense(20_000_000)])

    assert held.amount == D(0)
    assert held.direction == EVEN


def test_overspending_the_float_turns_the_debt_around():
    """Linh covered the difference herself - the company owes her."""
    (held,) = floats([advance(20_000_000)], [expense(23_000_000)])

    assert held.amount == D(-3_000_000)
    assert held.direction == TOP_UP


def test_someone_who_paid_without_an_advance_is_owed_it_back():
    (held,) = floats([], [expense(800_000)])

    assert held.advanced == D(0)
    assert held.spent == D(800_000)
    assert held.direction == TOP_UP


def test_money_the_company_paid_directly_settles_nothing():
    """The founder's own vendor payment is job spend, not Linh's float."""
    assert floats([], [expense(50_000_000, paid_by=CHUNG, paid_from=FROM_COMPANY)]) == []

    (held,) = floats(
        [advance(20_000_000)],
        [
            expense(5_000_000),
            expense(50_000_000, paid_by=CHUNG, paid_from=FROM_COMPANY),
        ],
    )
    assert held.spent == D(5_000_000)
    assert held.amount == D(15_000_000)


def test_each_holder_settles_their_own_float():
    held = floats(
        [advance(20_000_000), advance(6_000_000, recipient=CHUNG)],
        [expense(17_500_000), expense(9_000_000, paid_by=CHUNG)],
    )

    assert [(row.holder, row.amount, row.direction) for row in held] == [
        (CHUNG, D(-3_000_000), TOP_UP),
        (LINH, D(2_500_000), RETURN),
    ]


def test_settling_closes_the_float():
    args = ([advance(20_000_000)], [expense(17_500_000)])
    assert floats(*args)[0].amount == D(2_500_000)

    (held,) = floats(*args, [settlement(2_500_000)])
    assert held.settled == D(2_500_000)
    assert held.amount == D(0)
    assert held.direction == EVEN


def test_a_top_up_is_settled_by_paying_the_holder():
    (held,) = floats([], [expense(800_000)], [settlement(-800_000)])

    assert held.amount == D(0)
    assert held.direction == EVEN


def test_an_advance_after_a_settlement_opens_a_fresh_float():
    held = floats(
        [advance(20_000_000), advance(4_000_000)],
        [expense(17_500_000)],
        [settlement(2_500_000)],
    )

    assert held[0].amount == D(4_000_000)
    assert held[0].direction == RETURN


def test_amounts_written_as_text_still_add_up():
    """Frappe hands currency over as strings often enough to pin it."""
    (held,) = floats([advance("20000000")], [expense("17500000.00")])

    assert held.amount == D("2500000.00")


# -- categories mirror what the client was quoted --

PACKAGES = [
    {"title": "Human resources"},
    {"title": "Equipment"},
]

# As the engine leaves them on a saved breakdown. Đạo diễn is a
# freelancer (Cá nhân): the company hands over the 15.000.000 he quoted
# and remits his PIT separately, so his cost basis - 16.666.667, net
# ÷ 0.9 - is deliberately *not* what a shoot pays out.
COST_LINES = [
    {"description": "Đạo diễn", "package": "Human resources",
     "subtotal": 15_000_000, "cost_basis": 16_666_667, "input_vat": 0},
    {"description": "Thuê thiết bị", "package": "Equipment",
     "subtotal": 24_000_000, "vendor_mf_pct": 5,
     "cost_basis": 25_200_000, "input_vat": 2_016_000},
    {"description": "Flycam", "package": None,
     "subtotal": 6_000_000, "cost_basis": 6_000_000, "input_vat": 480_000},
]


def test_the_categories_are_the_packages_plus_anything_quoted_alone():
    assert categories(PACKAGES, COST_LINES) == [
        "Human resources",
        "Equipment",
        "Flycam",
    ]


def test_a_line_inside_a_package_is_not_a_category_of_its_own():
    assert "Đạo diễn" not in categories(PACKAGES, COST_LINES)


def test_two_lines_quoted_alone_under_one_name_are_one_category():
    lines = [
        {"description": "Đi lại", "cost_basis": 1_000_000, "input_vat": 0},
        {"description": "Đi lại", "cost_basis": 2_000_000, "input_vat": 0},
    ]
    assert categories([], lines) == ["Đi lại"]


def test_quoted_cost_is_the_cash_the_package_was_expected_to_need():
    """What somebody hands over - cost after the vendor management fee,
    plus VAT on an invoice - not the price the client pays for it."""
    rows = {row.title: row for row in category_actuals(PACKAGES, COST_LINES, [])}

    assert rows["Human resources"].quoted == D(15_000_000)
    assert rows["Equipment"].quoted == D(24_000_000) * D("1.05") + D(2_016_000)
    assert rows["Flycam"].quoted == D(6_480_000)


def test_a_freelancers_pit_is_not_money_the_shoot_pays_out():
    """The company remits it later through its accountant, and nobody
    logs it against the job - counting it would leave every crew-heavy
    package reading under budget for good."""
    (row,) = category_actuals([], COST_LINES[:1], [])

    assert row.quoted == D(15_000_000)
    assert row.quoted < D(COST_LINES[0]["cost_basis"])


def test_with_nothing_spent_yet_every_package_is_under_by_its_quoted_cost():
    rows = category_actuals(PACKAGES, COST_LINES, [])

    assert all(row.actual == D(0) for row in rows)
    assert rows[0].variance == -rows[0].quoted


def test_expenses_land_on_their_category_whoever_paid_them():
    rows = {
        row.title: row
        for row in category_actuals(
            PACKAGES,
            COST_LINES,
            [
                expense(10_000_000, category="Equipment"),
                expense(20_000_000, category="Equipment",
                        paid_by=CHUNG, paid_from=FROM_COMPANY),
            ],
        )
    }

    assert rows["Equipment"].actual == D(30_000_000)
    assert rows["Human resources"].actual == D(0)


def test_spending_over_the_quoted_cost_shows_as_a_positive_variance():
    rows = {
        row.title: row
        for row in category_actuals(
            PACKAGES, COST_LINES, [expense(30_000_000, category="Equipment")]
        )
    }

    assert rows["Equipment"].variance == D(30_000_000) - rows["Equipment"].quoted
    assert rows["Equipment"].variance > 0


def test_an_expense_outside_every_category_is_shown_rather_than_lost():
    rows = category_actuals(
        PACKAGES, COST_LINES, [expense(500_000), expense(200_000, category="Phạt")]
    )

    assert rows[-1].title == UNCATEGORISED
    assert rows[-1].actual == D(700_000)
    assert rows[-1].quoted == D(0)


def test_there_is_no_uncategorised_row_when_everything_is_categorised():
    rows = category_actuals(
        PACKAGES, COST_LINES, [expense(500_000, category="Equipment")]
    )

    assert [row.title for row in rows] == ["Human resources", "Equipment", "Flycam"]


# -- the helpers the API is an adapter over --


def test_a_float_is_readable_for_one_person_by_name():
    held = float_for(LINH, [advance(20_000_000)], [expense(17_500_000)])

    assert held.holder == LINH
    assert held.amount == D(2_500_000)


def test_someone_holding_nothing_still_gets_an_answer():
    """The phone asks after every expense; "nothing of ours" is a
    perfectly good reply."""
    held = float_for(CHUNG, [advance(20_000_000)], [expense(1_000_000)])

    assert held.holder == CHUNG
    assert held.advanced == D(0)
    assert held.amount == D(0)
    assert held.direction == EVEN


def test_the_job_totals_are_handed_out_paid_out_and_expected():
    rows = category_actuals(PACKAGES, COST_LINES, [expense(5_000_000, category="Equipment")])
    summary = totals(
        [advance(20_000_000), advance(6_000_000, recipient=CHUNG)],
        [expense(5_000_000, category="Equipment"),
         expense(1_000_000, paid_from=FROM_COMPANY)],
        rows,
    )

    assert summary.advanced == D(26_000_000)
    # Both, whoever paid: the job's money out is the job's money out.
    assert summary.spent == D(6_000_000)
    assert summary.quoted == sum((row.quoted for row in rows), D(0))

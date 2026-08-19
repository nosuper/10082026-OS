"""Pure-python tests for auraos.lib.exposure - no Frappe required.

This module was rebuilt in #123 after the founder found it taxing money
that was never spent. The tests carry that history on purpose, because
the arithmetic was never the problem - the source was, and a test suite
that only checks arithmetic will pass just as confidently next time.

- **Exposure is money that moved.** A `Không hoá đơn` cost line is a
  plan; a plan owes no tax. The first two tests here are the two
  directions the old version was wrong in: it reported a liability on a
  quoted line nobody spent against, and missed a payment that carried
  one.
- **The link carries the treatment.** The tax type lives on the quoted
  line, the money on the expense, and an expense is exposed when the
  line it spends against has no invoice behind it.
- **An expense naming no line is not exposure.** It is unstated, which
  is different from untaxed, and it is counted separately because that
  number is the reason to go and state it.
- **Covered is recorded, not derived.** An invoice number on the
  expense means paper was obtained. A replacement invoice is not a
  second expense - #11 modelled it that way and it double-counted the
  money.
"""

from decimal import Decimal

from auraos.lib.exposure import (
    STATED,
    TNDN_BASIS,
    UNATTRIBUTED,
    UNDATED,
    exposure_report,
    exposure_rows,
    has_invoice,
    is_no_invoice,
    tndn_on,
)
from auraos.lib.pricing import TNDN_RATE

NO_INVOICE = {"name": "l1", "description": "Ăn uống đoàn", "tax_type": "Không hoá đơn"}
INVOICED = {"name": "l2", "description": "Thuê thiết bị", "tax_type": "Công ty"}
LINES = {"l1": NO_INVOICE, "l2": INVOICED}


def spend(amount, cost_line=None, invoice_no=None, spent_on="2026-08-10", name="EXP-1"):
    return {
        "name": name,
        "job": "JOB-0009",
        "amount": amount,
        "spent_on": spent_on,
        "description": "Gửi xe + cà phê đoàn",
        "cost_line": cost_line,
        "invoice_no": invoice_no,
    }


def report(expenses, **kw):
    return exposure_report(exposure_rows(expenses, LINES), **kw)


# -- the two directions #123 was wrong in --


def test_a_quoted_no_invoice_line_nobody_spent_against_is_not_exposure():
    """The reported bug. 4.5tr of meals were priced and never bought;
    the founder was shown a 900k liability they did not have."""
    assert report([])["tndn_exposure"] == 0
    assert report([])["uncovered_total"] == 0
    # And a quoted line with no payment against it contributes nothing
    # even though the line exists and says Không hoá đơn.
    assert report([spend(5_000_000, cost_line="l2")])["uncovered_total"] == 0


def test_money_actually_paid_out_with_no_invoice_is_exposure():
    """The other half: the parking and coffee that were really paid for
    never reached the old tile at all."""
    out = report([spend(850_000, cost_line="l1")])

    assert out["uncovered_total"] == 850_000
    assert out["tndn_exposure"] == 170_000


# -- the link carries the treatment --


def test_an_expense_against_an_invoiced_line_is_not_exposed():
    assert report([spend(5_000_000, cost_line="l2")])["uncovered_total"] == 0


def test_is_no_invoice_reads_the_line_not_the_expense():
    assert is_no_invoice(NO_INVOICE) is True
    assert is_no_invoice(INVOICED) is False


def test_no_line_at_all_is_not_a_no_invoice_line():
    """Unstated is not untaxed. Guessing either way invents a fact."""
    assert is_no_invoice(None) is False
    assert is_no_invoice({}) is False
    assert is_no_invoice({"tax_type": "nonsense"}) is False


def test_an_expense_pointing_at_a_line_that_is_not_there_is_not_dropped():
    """A dangling link states nothing - so under the founder's rule it
    is spending nobody has accounted for, not spending proved safe."""
    (row,) = exposure_rows([spend(1_000_000, cost_line="gone")], LINES)

    assert row["treatment"] == UNATTRIBUTED


# -- spending nobody attributed --


def test_an_expense_naming_no_line_counts_as_exposed():
    """The founder's call, and their reason: understating is the error
    that costs money at an audit."""
    out = report([spend(850_000)])

    assert out["uncovered_total"] == 850_000
    assert out["tndn_exposure"] == 170_000
    assert out["unattributed_total"] == 850_000


def test_the_headline_counts_both_halves_and_the_breakdown_keeps_them_apart():
    out = report([spend(850_000), spend(4_500_000, cost_line="l1", name="EXP-2")])

    assert out["uncovered_total"] == 5_350_000
    assert out["stated_total"] == 4_500_000
    assert out["unattributed_total"] == 850_000
    assert out["stated_count"] == 1
    assert out["unattributed_count"] == 1


def test_the_two_halves_add_up_to_the_headline():
    """A breakdown that does not sum to its own headline is the defect
    this whole ticket is about."""
    out = report([spend(850_000), spend(4_500_000, cost_line="l1", name="EXP-2")])

    assert out["stated_total"] + out["unattributed_total"] == out["uncovered_total"]


def test_attributing_an_expense_to_an_invoiced_line_makes_the_number_fall():
    """The tile is a prompt, not a verdict: the figure goes down as the
    work of pointing each payment at its line gets done."""
    before = report([spend(5_000_000)])
    after = report([spend(5_000_000, cost_line="l2")])

    assert before["uncovered_total"] == 5_000_000
    assert after["uncovered_total"] == 0


def test_a_row_says_whether_its_treatment_is_stated_or_assumed():
    (assumed,) = exposure_rows([spend(850_000)], LINES)
    (stated,) = exposure_rows([spend(850_000, cost_line="l1")], LINES)

    assert assumed["treatment"] == UNATTRIBUTED
    assert stated["treatment"] == STATED


# -- covered means paper was obtained --


def test_an_invoice_number_takes_the_exposure_off():
    out = report([spend(850_000, cost_line="l1", invoice_no="0001234")])

    assert out["uncovered_total"] == 0
    assert out["covered_total"] == 850_000
    assert out["covered_count"] == 1


def test_blank_and_whitespace_are_not_an_invoice():
    assert has_invoice({"invoice_no": None}) is False
    assert has_invoice({"invoice_no": ""}) is False
    assert has_invoice({"invoice_no": "   "}) is False
    assert has_invoice({"invoice_no": "0001234"}) is True


def test_nothing_uncovered_is_told_apart_from_nothing_at_all():
    nothing = report([])
    all_covered = report([spend(850_000, cost_line="l1", invoice_no="0001")])

    assert nothing["tndn_exposure"] == all_covered["tndn_exposure"] == 0
    assert nothing["covered_count"] == 0
    assert all_covered["covered_count"] == 1


def test_only_the_uncovered_rows_come_back_to_chase():
    out = report([
        spend(850_000, cost_line="l1"),
        spend(1_000_000, cost_line="l1", invoice_no="0001", name="EXP-2"),
    ])

    assert [row["amount"] for row in out["lines"]] == [850_000]


# -- the tax on it --


def test_the_rate_is_the_one_the_profit_chain_already_uses():
    assert TNDN_RATE == Decimal("0.2")
    assert report([])["rate_pct"] == 20.0


def test_a_caller_may_supply_a_different_rate():
    out = report([spend(10_000_000, cost_line="l1")], rate=Decimal("0.25"))

    assert out["tndn_exposure"] == 2_500_000


def test_the_tax_is_computed_on_the_total_as_printed():
    out = report([spend(850_000.4, cost_line="l1")])

    assert out["uncovered_total"] == 850_000
    assert out["tndn_exposure"] == tndn_on(850_000)


def test_every_figure_is_whole_dong_never_a_float():
    out = report([spend(850_000.6, cost_line="l1"), spend(1_000_000.4, name="EXP-2")])

    for key in ("uncovered_total", "tndn_exposure", "covered_total",
                "unattributed_total", "stated_total"):
        assert isinstance(out[key], int), key


def test_the_report_declares_what_it_measured():
    """The basis names the payment, not the plan - the screen prints it
    and the two have to be the same claim."""
    assert exposure_report([])["basis"] == TNDN_BASIS
    assert "paid out" in TNDN_BASIS


def test_the_basis_names_both_halves_of_the_number_it_describes():
    """The headline counts stated and unattributed spending, so a basis
    that mentioned only the stated half would declare something narrower
    than the figure beside it - which is this ticket's own defect,
    committed in prose instead of arithmetic."""
    assert "no-invoice line" in TNDN_BASIS
    assert "not yet attributed" in TNDN_BASIS


# -- months, which are now always real --


def test_months_are_absent_unless_asked_for():
    assert "months" not in report([spend(850_000, cost_line="l1")])


def test_expenses_group_into_the_month_the_money_went_out():
    out = report(
        [
            spend(850_000, cost_line="l1", spent_on="2026-08-03"),
            spend(150_000, cost_line="l1", spent_on="2026-08-30", name="EXP-2"),
            spend(1_000_000, cost_line="l1", spent_on="2026-07-31", name="EXP-3"),
        ],
        by_month=True,
    )

    assert [row["month"] for row in out["months"]] == ["2026-07", "2026-08"]
    assert next(r for r in out["months"] if r["month"] == "2026-08")["uncovered_total"] == 1_000_000


def test_the_total_is_exactly_the_sum_of_the_printed_months():
    out = report(
        [
            spend(850_000, cost_line="l1", spent_on="2026-08-03"),
            spend(1_000_000, cost_line="l1", spent_on="2026-07-31", name="EXP-2"),
        ],
        by_month=True,
    )

    assert out["uncovered_total"] == sum(r["uncovered_total"] for r in out["months"])


def test_an_expense_that_lost_its_date_is_named_rather_than_dropped():
    out = report([spend(850_000, cost_line="l1", spent_on=None)], by_month=True)

    assert [row["month"] for row in out["months"]] == [UNDATED]


def test_a_stamped_date_comes_back_as_a_plain_iso_day():
    from datetime import datetime

    rows = exposure_rows(
        [spend(850_000, cost_line="l1", spent_on=datetime(2026, 8, 3, 9, 30))], LINES
    )
    assert rows[0]["spent_on"] == "2026-08-03"


# -- what a row carries --


def test_a_row_names_the_expense_and_the_line_it_spends_against():
    rows = exposure_rows([spend(850_000, cost_line="l1")], LINES, jobs={"JOB-0009": "MV"})

    (row,) = rows
    assert row["expense"] == "EXP-1"
    assert row["line"] == "l1"
    assert row["job_title"] == "MV"


def test_a_row_falls_back_to_the_quoted_lines_description():
    """So a wordless expense still says what it was spent on."""
    expense = spend(850_000, cost_line="l1")
    expense["description"] = None
    rows = exposure_rows([expense], LINES)

    assert rows[0]["description"] == "Ăn uống đoàn"


def test_the_treatments_are_named_not_bare_strings():
    assert STATED == "stated"
    assert UNATTRIBUTED == "unattributed"

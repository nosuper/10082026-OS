"""Pure-python tests for auraos.lib.exposure - no Frappe required.

The tile this feeds turns a tax cost the founder currently carries in
their head into a number on a screen, so the arithmetic under it is
worth pinning apart from any doctype:

- **Uncovered is the safe default.** A line whose replacement status
  nobody recorded counts as still exposed. A wrong default here shrinks
  the tax bill on the screen and nowhere else.
- **Covered lines are counted, not dropped.** "Nothing is uncovered" and
  "there was never any no-invoice spend" are different news, and a tile
  that cannot tell them apart reads as the good one on a studio that has
  not started yet.
- **The rate is pricing.TNDN_RATE.** Not a second 20% living here, which
  would be a defect waiting for the rate to change.
- **Whole đồng, and the tax is computed on the rounded base**, so the
  figure printed beside a total is the tax on the total as printed.

The month grouping is off by default and tested as an option, because a
cost line has no date of its own - see the module docstring on why an
exposure is carried rather than falling in a month.

The Frappe-side surface is a thin adapter over these functions and
gates them to the founder; that boundary is tested at the seam.
"""

from decimal import Decimal

from auraos.lib.exposure import (
    TNDN_BASIS,
    UNDATED,
    coverage,
    exposure_report,
    exposure_rows,
    is_covered,
    is_no_invoice,
    tndn_on,
)
from auraos.lib.pricing import TNDN_RATE


def line(amount, covered=None, spent_on=None, job="JOB-0009", description="Xe"):
    row = {"job": job, "description": description, "amount": amount}
    if covered is not None:
        row["covered"] = covered
    if spent_on is not None:
        row["spent_on"] = spent_on
    return row


def month_of(report, key):
    return next(row for row in report["months"] if row["month"] == key)


# -- nothing to report is a report --


def test_no_lines_at_all_reads_as_zero_rather_than_raising():
    report = exposure_report([])

    assert report["uncovered_total"] == 0
    assert report["tndn_exposure"] == 0
    assert report["uncovered_count"] == 0
    assert report["lines"] == []


def test_nothing_uncovered_is_told_apart_from_nothing_at_all():
    """Both show a zero exposure. Only one of them means the founder
    has been chasing invoices and winning."""
    nothing = exposure_report([])
    all_covered = exposure_report([line(10_000_000, covered=True)])

    assert nothing["tndn_exposure"] == all_covered["tndn_exposure"] == 0
    assert nothing["covered_count"] == 0
    assert all_covered["covered_count"] == 1
    assert all_covered["covered_total"] == 10_000_000


# -- what counts as exposed --


def test_a_line_nobody_has_recorded_a_status_for_is_exposed():
    """The unrecorded direction has to keep the number honest."""
    report = exposure_report([line(10_000_000)])

    assert report["uncovered_total"] == 10_000_000
    assert report["uncovered_count"] == 1


def test_a_covered_line_carries_no_exposure():
    report = exposure_report([line(10_000_000, covered=True)])

    assert report["uncovered_total"] == 0
    assert report["tndn_exposure"] == 0


def test_covered_and_uncovered_are_added_up_separately():
    report = exposure_report(
        [line(10_000_000), line(3_000_000, covered=True), line(2_500_000)]
    )

    assert report["uncovered_total"] == 12_500_000
    assert report["uncovered_count"] == 2
    assert report["covered_total"] == 3_000_000
    assert report["covered_count"] == 1


def test_only_the_uncovered_lines_come_back_on_the_payload():
    """The tile is a list of what still needs an invoice chasing."""
    report = exposure_report([line(10_000_000), line(3_000_000, covered=True)])

    assert [row["amount"] for row in report["lines"]] == [10_000_000]


def test_is_covered_reads_a_missing_flag_as_not_covered():
    assert is_covered({}) is False
    assert is_covered({"covered": False}) is False
    assert is_covered({"covered": True}) is True


# -- the tax on it --


def test_the_exposure_is_the_rate_applied_to_the_uncovered_total():
    report = exposure_report([line(10_000_000)])

    assert report["tndn_exposure"] == 2_000_000


def test_the_rate_is_the_one_the_profit_chain_already_uses():
    """Not a second 20% living in this module."""
    assert TNDN_RATE == Decimal("0.2")
    assert exposure_report([line(10_000_000)])["rate_pct"] == 20.0


def test_a_caller_may_supply_a_different_rate():
    report = exposure_report([line(10_000_000)], rate=Decimal("0.25"))

    assert report["tndn_exposure"] == 2_500_000
    assert report["rate_pct"] == 25.0


def test_the_tax_is_computed_on_the_total_as_printed():
    """Not on a hidden fraction of a đồng nobody can see."""
    report = exposure_report([line(10_000_000.4)])

    assert report["uncovered_total"] == 10_000_000
    assert report["tndn_exposure"] == tndn_on(10_000_000)


def test_every_figure_is_whole_dong_never_a_float():
    report = exposure_report([line(10_000_000.4), line(2_500_000.6)])

    for key in ("uncovered_total", "tndn_exposure", "covered_total"):
        assert isinstance(report[key], int), key
    assert all(isinstance(row["amount"], int) for row in report["lines"])


def test_the_report_declares_what_it_measured():
    report = exposure_report([])

    assert report["basis"] == TNDN_BASIS


# -- grouping by month, when the caller has a date to group by --


def test_months_are_absent_unless_asked_for():
    """A cost line has no date of its own; an exposure is carried until
    the paper arrives rather than falling in a month."""
    assert "months" not in exposure_report([line(10_000_000)])


def test_uncovered_lines_group_into_the_month_the_money_went_out():
    report = exposure_report(
        [
            line(10_000_000, spent_on="2026-08-03"),
            line(4_000_000, spent_on="2026-08-30"),
            line(1_000_000, spent_on="2026-07-31"),
        ],
        by_month=True,
    )

    assert [row["month"] for row in report["months"]] == ["2026-07", "2026-08"]
    assert month_of(report, "2026-08")["uncovered_total"] == 14_000_000
    assert month_of(report, "2026-08")["count"] == 2


def test_each_month_carries_the_tax_on_its_own_total():
    report = exposure_report([line(10_000_000, spent_on="2026-08-03")], by_month=True)

    assert month_of(report, "2026-08")["tndn_exposure"] == 2_000_000


def test_the_total_is_exactly_the_sum_of_the_printed_months():
    report = exposure_report(
        [
            line(10_000_000, spent_on="2026-08-03"),
            line(1_000_000, spent_on="2026-07-31"),
            line(2_500_000),
        ],
        by_month=True,
    )

    assert report["uncovered_total"] == sum(
        row["uncovered_total"] for row in report["months"]
    )


def test_a_line_nobody_dated_is_named_rather_than_dropped():
    """An exposure with no date is still an exposure. Dropping it would
    understate the bill; guessing it into this month would invent one."""
    report = exposure_report([line(2_500_000)], by_month=True)

    assert [row["month"] for row in report["months"]] == [UNDATED]
    assert month_of(report, UNDATED)["uncovered_total"] == 2_500_000


def test_undated_lines_sort_after_the_real_months():
    report = exposure_report(
        [line(2_500_000), line(10_000_000, spent_on="2026-08-03")], by_month=True
    )

    assert [row["month"] for row in report["months"]] == ["2026-08", UNDATED]


def test_a_covered_line_is_in_no_month():
    report = exposure_report(
        [line(3_000_000, covered=True, spent_on="2026-08-03")], by_month=True
    )

    assert report["months"] == []


# -- what a row carries back --


def test_a_line_carries_what_the_screen_needs_to_name_it():
    report = exposure_report(
        [
            {
                "job": "JOB-0009",
                "job_title": "TVC Tết",
                "description": "Xe 16 chỗ",
                "amount": 10_000_000,
                "spent_on": "2026-08-03",
            }
        ]
    )

    (row,) = report["lines"]
    assert row["job"] == "JOB-0009"
    assert row["job_title"] == "TVC Tết"
    assert row["description"] == "Xe 16 chỗ"
    assert row["spent_on"] == "2026-08-03"


def test_a_stamped_date_comes_back_as_a_plain_iso_day():
    """Frappe hands back datetimes; a screen should never have to parse
    "2026-08-03 09:30:00"."""
    from datetime import datetime

    report = exposure_report([line(10_000_000, spent_on=datetime(2026, 8, 3, 9, 30))])

    assert report["lines"][0]["spent_on"] == "2026-08-03"


# -- the linkage: which lines a replacement invoice covers --
#
# The status is derived from the expenses and stored nowhere, so these
# are the tests that stop it becoming an opinion. An expense says which
# line it covers; nothing else can say a line is covered.


def cost_line(name, tax_type="Không hoá đơn", subtotal=10_000_000, vendor_mf_pct=0):
    return {
        "name": name,
        "description": f"line {name}",
        "tax_type": tax_type,
        "subtotal": subtotal,
        "vendor_mf_pct": vendor_mf_pct,
        "input_vat": 0,
    }


def expense(name, amount, covers=None):
    return {"name": name, "amount": amount, "covers_cost_line": covers}


def test_only_no_invoice_lines_are_ever_exposed():
    """A line that came with an invoice has nothing to replace."""
    assert is_no_invoice(cost_line("l1")) is True
    assert is_no_invoice(cost_line("l2", tax_type="Công ty")) is False
    assert is_no_invoice(cost_line("l3", tax_type="Cá nhân")) is False


def test_a_line_with_no_tax_type_at_all_is_not_exposed():
    """Unparseable is not the same as no-invoice, and guessing that it
    were would invent a tax bill."""
    assert is_no_invoice({"name": "l1"}) is False
    assert is_no_invoice({"name": "l1", "tax_type": "nonsense"}) is False


def test_invoice_bearing_lines_are_left_out_of_the_answer_entirely():
    rows = exposure_rows(
        [cost_line("l1"), cost_line("l2", tax_type="Công ty")], []
    )

    assert [row["line"] for row in rows] == ["l1"]


def test_a_line_is_covered_only_when_an_expense_says_so():
    rows = exposure_rows([cost_line("l1")], [expense("EXP-1", 10_000_000, "l1")])

    assert rows[0]["covered"] is True
    assert rows[0]["covering_expenses"] == ["EXP-1"]


def test_a_line_no_expense_names_stays_uncovered():
    rows = exposure_rows([cost_line("l1")], [expense("EXP-1", 10_000_000)])

    assert rows[0]["covered"] is False
    assert rows[0]["covering_count"] == 0


def test_two_expenses_may_cover_one_line():
    """A replacement invoice can arrive split across two receipts, and
    refusing the second would send somebody to edit the first."""
    rows = exposure_rows(
        [cost_line("l1")],
        [expense("EXP-1", 4_000_000, "l1"), expense("EXP-2", 6_000_000, "l1")],
    )

    assert rows[0]["covered"] is True
    assert rows[0]["covering_count"] == 2
    assert rows[0]["covering_total"] == 10_000_000
    # Both of them named, not just the first: a line answered for by two
    # receipts and shown as one is a partial truth.
    assert rows[0]["covering_expenses"] == ["EXP-1", "EXP-2"]


def test_a_part_covered_line_says_how_much_was_covered():
    """Binary status, but the amount is carried: 10 triệu covered by a
    2 triệu invoice is not the same news as covered in full."""
    rows = exposure_rows([cost_line("l1")], [expense("EXP-1", 2_000_000, "l1")])

    assert rows[0]["covered"] is True
    assert rows[0]["amount"] == 10_000_000
    assert rows[0]["covering_total"] == 2_000_000


def test_the_amount_is_the_cash_the_line_hands_over():
    """The vendor management fee is money that leaves too, so it is
    exposed as well - the same figure the job's money screen compares
    against, not a second reading of the line."""
    rows = exposure_rows([cost_line("l1", subtotal=3_000_000, vendor_mf_pct=10)], [])

    assert rows[0]["amount"] == 3_300_000


def test_coverage_ignores_expenses_that_cover_nothing():
    """Most expenses on a shoot are not replacement invoices."""
    folded = coverage([expense("EXP-1", 500_000), expense("EXP-2", 1_000_000, "l1")])

    assert sorted(folded) == ["l1"]


def test_the_job_is_carried_onto_every_row():
    rows = exposure_rows(
        [cost_line("l1")], [], job="JOB-0009", job_title="TVC Tết"
    )

    assert rows[0]["job"] == "JOB-0009"
    assert rows[0]["job_title"] == "TVC Tết"


def test_rows_feed_the_report_without_translation():
    """exposure_rows is what exposure_report expects, so a caller never
    reshapes anything between them."""
    rows = exposure_rows(
        [cost_line("l1"), cost_line("l2", subtotal=3_000_000)],
        [expense("EXP-1", 3_000_000, "l2")],
        job="JOB-0009",
    )
    report = exposure_report(rows)

    assert report["uncovered_total"] == 10_000_000
    assert report["tndn_exposure"] == 2_000_000
    assert report["covered_total"] == 3_000_000

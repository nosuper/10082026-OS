"""Pure-python tests for auraos.lib.tax - no Frappe required.

The arithmetic here is a two-line division and it is not what these
tests are for. What they pin is **which rows count, which date decides,
and which rate is used** - the three ways a VAT figure goes wrong while
looking entirely reasonable:

- **The invoice date decides the period, not the payment date.** Every
  other figure in Finance is cash basis; output VAT falls due when the
  invoice is issued. A test suite that seeded one milestone paid and
  invoiced in the same month would pass whichever date the module read.
- **The rate is the one the invoice was written at.** `invoice_vat_pct`
  is captured once, at issue, so a past period cannot be restated by
  today's rate. The module never looks at a current rate at all, and one
  of these tests is here to fail if it ever starts.
- **The sentence over the number has to be true too.** #123 was a
  correct figure under a description that had drifted wider than it -
  so `not_computed` is asserted by content, not merely present. Deleting
  the honesty is a test failure, which is the only way it stays.
"""

from datetime import date

from auraos.lib.tax import (
    NOT_COMPUTED,
    VAT_BASIS,
    input_vat,
    invoiced_rows,
    output_vat,
    overheads,
    position,
)

JULY = (date(2026, 7, 1), date(2026, 7, 31))


def milestone(**overrides):
    """One invoiced milestone, VAT-inclusive the way a quote is."""
    row = {
        "name": "m1",
        "parent": "JOB-0001",
        "job_title": "A shoot",
        "title": "Đặt cọc",
        "amount": 110_000_000,
        "invoice_vat_pct": 10,
        "invoiced_on": date(2026, 7, 10),
        "invoice_no": "INV-1",
    }
    row.update(overrides)
    return row


def test_a_milestone_nobody_invoiced_is_not_in_the_period():
    """No issue date is no invoice, so there is nothing to declare.

    `milestones.stamps_for` clears the date, the number and the rate
    together when a status walks back before đã xuất HĐ, so this is the
    same question as "has an invoice" and needs no status filter.
    """
    rows = invoiced_rows([milestone(invoiced_on=None, invoice_vat_pct=None)], *JULY)
    assert rows == []


def test_the_invoice_date_decides_the_period_not_the_payment():
    """The whole ticket, in one assertion.

    A milestone invoiced in June and collected in July belongs to June's
    VAT return. Reading `paid_on` here would put it in July and the
    figure would still look plausible - it would simply be a different
    month's tax.
    """
    collected_in_july = milestone(
        invoiced_on=date(2026, 6, 28), paid_on=date(2026, 7, 3)
    )
    assert invoiced_rows([collected_in_july], *JULY) == []

    invoiced_in_july = milestone(
        invoiced_on=date(2026, 7, 28), paid_on=date(2026, 9, 3)
    )
    assert len(invoiced_rows([invoiced_in_july], *JULY)) == 1


def test_the_window_includes_both_of_its_ends():
    """A return covers the month, not the month minus its edges."""
    first = milestone(name="a", invoiced_on=date(2026, 7, 1))
    last = milestone(name="b", invoiced_on=date(2026, 7, 31))
    assert len(invoiced_rows([first, last], *JULY)) == 2


def test_the_rate_is_the_one_the_invoice_carries():
    """An invoice issued at 8% stays at 8%.

    The module is handed no "current rate" anywhere, and that is the
    point: an invoice the client is already holding cannot be restated
    because the company's rate changed afterwards. If a current rate is
    ever threaded through here, this test is what should stop it.
    """
    row = invoiced_rows([milestone(amount=108_000_000, invoice_vat_pct=8)], *JULY)[0]
    assert row["vat_pct"] == 8
    assert row["net"] == 100_000_000
    assert row["vat"] == 8_000_000


def test_zero_is_a_rate_and_not_a_blank():
    """An export invoice is genuinely written at 0%.

    It is a row in the return with no VAT on it, not a row missing from
    the return - and a module that treated 0 as "no rate recorded" would
    drop the revenue as well as the tax.
    """
    rows = invoiced_rows([milestone(amount=50_000_000, invoice_vat_pct=0)], *JULY)
    assert len(rows) == 1
    assert rows[0]["vat"] == 0
    assert rows[0]["net"] == 50_000_000


def test_the_parts_add_back_to_the_amount_the_client_was_asked_for():
    """Per row and in the total, because both get printed."""
    rows = invoiced_rows(
        [
            milestone(name="a", amount=110_000_000, invoice_vat_pct=10),
            milestone(name="b", amount=108_000_000, invoice_vat_pct=8),
            milestone(name="c", amount=33_333_333, invoice_vat_pct=10),
        ],
        *JULY,
    )
    for row in rows:
        assert row["net"] + row["vat"] == row["gross"]

    report = output_vat(rows)
    assert report["net_total"] + report["vat_total"] == report["gross_total"]
    assert report["vat_total"] == sum(row["vat"] for row in rows)


def test_the_period_is_broken_out_by_rate_because_a_return_is():
    """Three invoices, two rates, and the split is checkable against a
    filing. One summed figure is not."""
    rows = invoiced_rows(
        [
            milestone(name="a", amount=110_000_000, invoice_vat_pct=10),
            milestone(name="b", amount=220_000_000, invoice_vat_pct=10),
            milestone(name="c", amount=50_000_000, invoice_vat_pct=0),
        ],
        *JULY,
    )
    by_rate = {bucket["vat_pct"]: bucket for bucket in output_vat(rows)["by_rate"]}
    assert set(by_rate) == {0.0, 10.0}
    assert by_rate[10.0]["count"] == 2
    assert by_rate[10.0]["vat"] == 30_000_000
    assert by_rate[0.0]["vat"] == 0


def test_an_empty_period_is_zero_rather_than_missing():
    """A month with no invoices is a month that owes no output VAT, and
    the card still has rows to draw."""
    report = output_vat(invoiced_rows([], *JULY))
    assert report["count"] == 0
    assert report["vat_total"] == 0
    assert report["by_rate"] == []
    assert report["basis"] == VAT_BASIS


def test_the_exposure_component_is_labelled_standing_and_kept_apart():
    """It is not measured over the period and must not read as if it is.

    An uncovered payment is carried from the day it was made until an
    invoice turns up - `api.no_invoice_exposure` takes no range for the
    same reason - so a payload that let it sit unlabelled beside a
    period figure would invite a screen to add them.
    """
    report = output_vat(invoiced_rows([milestone()], *JULY))
    whole = position(report, {"tndn_exposure": 4_000_000, "uncovered_total": 20_000_000})
    assert whole["tndn_component"]["standing"] is True
    assert whole["tndn_component"]["tndn_exposure"] == 4_000_000
    # Kept in its own branch of the payload rather than merged into the
    # VAT figures, so no consumer can total them by accident.
    assert "tndn_exposure" not in whole["vat"]


def test_no_exposure_asked_for_is_none_rather_than_zero():
    """"Nothing exposed" and "not asked" are different answers, and a
    zero would render as the first."""
    assert position(output_vat([]))["tndn_component"] is None


# -- the company's own upkeep (#14/#109 step 2) --


def overhead(**overrides):
    """One company expense, paid and invoiced on the same day - which is
    what an ordinary receipt looks like and what the record defaults to."""
    row = {
        "name": "CE-2026-00001",
        "spent_on": date(2026, 7, 10),
        "amount": 2_200_000,
        "category": "Chi phí tiếp khách",
        "description": "Cơm khách",
        "for_depreciation": 0,
        "invoice_no": "INV-A",
        "invoice_date": date(2026, 7, 10),
        "invoice_vat_amount": 200_000,
        "supplier": "Nhà hàng",
    }
    row.update(overrides)
    return row


def test_overheads_are_dated_by_the_day_the_money_left():
    """A different basis from the VAT blocks, on purpose and on its face.

    A cost paid in July belongs to July's spending whatever month its
    invoice bears - the app records when money left, and the accountant
    recognises the cost on their own basis.
    """
    paid_in_august = overhead(spent_on=date(2026, 8, 2), invoice_date=date(2026, 7, 30))
    assert overheads([paid_in_august], *JULY)["paid_total"] == 0

    paid_in_july = overhead(spent_on=date(2026, 7, 30), invoice_date=date(2026, 8, 2))
    assert overheads([paid_in_july], *JULY)["paid_total"] == 2_200_000


def test_input_vat_is_dated_by_the_invoice_like_output_vat():
    """The inconsistency this exists to prevent.

    Rent invoiced in June and paid in July is the ordinary case: its VAT
    belongs to June's return even though the money moved in July. Dating
    it by payment would put two bases inside one figure - the thing the
    output side already refuses.
    """
    invoiced_in_june = overhead(invoice_date=date(2026, 6, 28), spent_on=date(2026, 7, 3))
    assert input_vat([invoiced_in_june], *JULY)["vat_total"] == 0
    # And it is that month's spending all the same, on the other basis.
    assert overheads([invoiced_in_june], *JULY)["paid_total"] == 2_200_000


def test_a_flagged_purchase_is_listed_and_left_out_of_the_total():
    """The founder's reconciliation criterion, in one assertion.

    Excluded from the deductible total *and* visible as its own line -
    an invisible subtraction cannot be checked against a return.
    """
    report = overheads(
        [
            overhead(name="a", amount=2_000_000),
            overhead(name="b", amount=30_000_000, for_depreciation=1, description="Máy in"),
        ],
        *JULY,
    )
    assert report["paid_total"] == 2_000_000
    assert report["flagged"]["total"] == 30_000_000
    assert [line["description"] for line in report["flagged"]["lines"]] == ["Máy in"]


def test_a_flagged_purchase_still_carries_its_input_vat():
    """Two different questions with two different answers.

    How a cost is treated for TNDN and whether its VAT is deductible are
    unrelated, and excluding a depreciated purchase's VAT because it is
    excluded from the cost block would be tidiness overriding the tax.
    """
    report = input_vat([overhead(for_depreciation=1)], *JULY)
    assert report["vat_total"] == 200_000


def test_an_uncategorised_payment_gets_its_own_bucket():
    """Dropped, it would make the tile disagree with the bank by exactly
    the money nobody has classified yet."""
    report = overheads([overhead(category=None, amount=500_000)], *JULY)
    assert report["paid_total"] == 500_000
    assert [bucket["category"] for bucket in report["by_category"]] == [None]


def test_categories_are_biggest_first():
    """A founder checking a return reads down from the line most likely
    to be wrong about real money."""
    report = overheads(
        [
            overhead(name="a", category="Nhỏ", amount=1_000_000),
            overhead(name="b", category="Lớn", amount=9_000_000),
        ],
        *JULY,
    )
    assert [bucket["category"] for bucket in report["by_category"]] == ["Lớn", "Nhỏ"]


def test_the_blocks_stay_in_their_own_branches():
    """Nothing can total two figures measured over different things."""
    whole = position(
        output_vat([]),
        {"tndn_exposure": 1},
        overhead=overheads([overhead()], *JULY),
        inputs=input_vat([overhead()], *JULY),
    )
    assert whole["overheads"]["paid_total"] == 2_200_000
    assert whole["input_vat"]["vat_total"] == 200_000
    assert "paid_total" not in whole["vat"]
    assert "vat_total" not in whole["overheads"]


def test_the_payload_says_what_it_does_not_compute():
    """#123's lesson, pinned.

    That ticket was a correct number under a sentence that had drifted
    wider than it. Here the risk runs the other way: the figures are
    narrow and honest only while the payload keeps saying so. Asserting
    the content rather than the presence means deleting the explanation
    breaks a test instead of quietly shipping a tax card that looks
    complete.
    """
    figures = {row["figure"] for row in position(output_vat([]))["not_computed"]}
    assert "TNDN for the period" in figures
    assert "input VAT on job spending" in figures
    assert "VAT payable" in figures

    reasons = {row["figure"]: row["why"].lower() for row in NOT_COMPUTED}
    # TNDN's reason changed when overheads became recordable, and the new
    # one is better: it is a judgement that is not ours rather than data
    # we were missing. If it ever reverts to "overheads are not
    # recordable", something has been un-built.
    assert "accountant" in reasons["TNDN for the period"]
    assert "depreciated" in reasons["TNDN for the period"]
    # And the input-VAT gap is now about the job side specifically, not
    # about input VAT existing at all.
    assert "job expense" in reasons["input VAT on job spending"]

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

from auraos.lib.tax import NOT_COMPUTED, VAT_BASIS, invoiced_rows, output_vat, position

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
    assert "input VAT" in figures
    assert "VAT payable" in figures

    reasons = " ".join(row["why"] for row in NOT_COMPUTED).lower()
    # The reason TNDN is absent is the one a reader will ask about, and
    # it is a fact about the data rather than a disclaimer.
    assert "job" in reasons and "overhead" in reasons
    assert "input vat is not recorded" in reasons

"""Pure-python tests for auraos.lib.milestones — no Frappe required.

T10 / spec #2, stories 37–40. Four decisions live in the pure module
because each is a rule rather than plumbing:

- **What the client owes when**: a milestone's amount is a share of the
  job's quoted total, and the shares must add up to the total the client
  was quoted — no đồng invented or lost to rounding.
- **The collection flow**: chưa yêu cầu → đã yêu cầu KT → đã xuất HĐ →
  đã thanh toán, and what moving along (or back along) it stamps.
- **When a milestone is overdue**: the nudge condition.
- **What the accountant is sent**: the invoice-request text, to the
  character.

The Frappe-side tests (auraos/auraos/doctype/job/test_job_milestones.py)
prove the job and the API actually go through these functions.
"""

from datetime import datetime, timedelta
from decimal import Decimal as D

import pytest

from auraos.lib.milestones import (
    NOT_REQUESTED,
    PAID,
    REQUESTED,
    STAMP_FIELDS,
    STATUS_FLOW,
    due_stamp,
    invoice_request_text,
    invoice_split,
    is_overdue,
    milestone_amounts,
    stage_reached,
    stamps_for,
    status_index,
)

NOW = datetime(2026, 8, 10, 9, 30)

STAGES = [
    "Pre-production",
    "Production",
    "Post-production",
    "Client review",
    "Delivery",
    "Client sign-off",
    "Awaiting payment",
    "Complete",
]


# -- amounts derived from the quoted total --


def test_a_milestone_is_its_percentage_of_the_quoted_total():
    assert milestone_amounts(100_000_000, [50]) == [50_000_000]


def test_the_shares_add_up_to_the_total_the_client_was_quoted():
    """The whole point of deriving them: what we chase must equal what we
    quoted, or the last invoice is off by a đồng nobody can explain."""
    total = 118_800_000
    amounts = milestone_amounts(total, [D("33.33"), D("33.33"), D("33.34")])
    assert sum(amounts) == total


def test_rounding_never_invents_or_loses_a_dong():
    # Each share is the running total rounded, minus what came before, so
    # a rounding gain on one share is paid back by the next.
    amounts = milestone_amounts(100, [D("33.33"), D("33.33"), D("33.34")])
    assert amounts == [33, 34, 33]
    assert sum(amounts) == 100


def test_percentages_short_of_a_hundred_bill_only_what_they_name():
    assert milestone_amounts(100_000_000, [30]) == [30_000_000]


def test_no_milestones_is_no_money():
    assert milestone_amounts(100_000_000, []) == []


def test_a_job_with_no_quoted_total_owes_nothing_yet():
    assert milestone_amounts(0, [50, 50]) == [0, 0]
    assert milestone_amounts(None, [50, 50]) == [0, 0]


def test_a_blank_percentage_is_zero_not_a_crash():
    assert milestone_amounts(100_000_000, [50, None]) == [50_000_000, 0]


def test_amounts_are_whole_dong():
    for amount in milestone_amounts(118_800_001, [D("33.3"), D("33.3"), D("33.4")]):
        assert isinstance(amount, int)


# -- the collection flow --


def test_the_flow_is_the_four_agreed_states_in_order():
    assert STATUS_FLOW == (
        "Not requested",   # chưa yêu cầu
        "Requested",       # đã yêu cầu KT
        "Invoiced",        # đã xuất HĐ
        "Paid",            # đã thanh toán
    )


def test_status_index_orders_the_flow():
    assert status_index(NOT_REQUESTED) < status_index(REQUESTED)
    assert status_index(REQUESTED) < status_index(PAID)


def test_an_unknown_status_is_rejected():
    with pytest.raises(ValueError):
        status_index("đã quên")


def test_moving_forward_stamps_the_step_it_passes():
    stamps = stamps_for("Invoiced", current={}, now=NOW)
    assert stamps["requested_on"] == NOW
    assert stamps["invoiced_on"] == NOW
    assert stamps["paid_on"] is None


def test_a_step_already_stamped_keeps_its_original_time():
    """Marking paid must not rewrite when the accountant was asked."""
    asked = NOW - timedelta(days=3)
    stamps = stamps_for("Paid", current={"requested_on": asked}, now=NOW)
    assert stamps["requested_on"] == asked
    assert stamps["paid_on"] == NOW


def test_stepping_back_clears_the_steps_it_undoes():
    """The T6 lesson: no one-way doors. A status set by accident is
    walked back, and the stamps behind it go with it."""
    stamps = stamps_for(
        "Requested",
        current={
            "requested_on": NOW - timedelta(days=2),
            "invoiced_on": NOW - timedelta(days=1),
            "paid_on": NOW,
        },
        now=NOW,
    )
    assert stamps["requested_on"] == NOW - timedelta(days=2)
    assert stamps["invoiced_on"] is None
    assert stamps["paid_on"] is None


def test_the_first_state_stamps_nothing():
    stamps = stamps_for(NOT_REQUESTED, current={"requested_on": NOW}, now=NOW)
    assert set(stamps.values()) == {None}


def test_every_state_past_the_first_has_a_stamp_of_its_own():
    assert set(STAMP_FIELDS) == set(STATUS_FLOW[1:])


# -- when a milestone becomes due, and when it is overdue --


def test_a_milestone_falls_due_when_the_job_reaches_its_trigger_stage():
    assert stage_reached("Client review", "Client review", STAGES)


def test_a_milestone_is_not_due_before_its_trigger_stage():
    assert not stage_reached("Production", "Client sign-off", STAGES)


def test_a_job_past_the_trigger_stage_owes_the_milestone_too():
    """Stages are dragged around; passing straight through Client sign-off
    to Complete must not skip the final invoice."""
    assert stage_reached("Complete", "Client sign-off", STAGES)


def test_an_unknown_stage_never_falls_due():
    assert not stage_reached("Đi nhậu", "Delivery", STAGES)
    assert not stage_reached("Delivery", "Đi nhậu", STAGES)


def test_reaching_the_trigger_stage_stamps_when_the_money_fell_due():
    assert due_stamp(reached=True, due_on=None, status=NOT_REQUESTED, now=NOW) == NOW


def test_the_due_date_is_stamped_once_and_then_left_alone():
    """Bouncing between stages must not restart the payment clock."""
    first = NOW - timedelta(days=10)
    assert due_stamp(reached=True, due_on=first, status=REQUESTED, now=NOW) == first


def test_a_milestone_before_its_trigger_stage_has_not_fallen_due():
    assert due_stamp(reached=False, due_on=None, status=NOT_REQUESTED, now=NOW) is None


def test_dragging_a_job_back_un_dues_a_milestone_nobody_has_acted_on():
    """A mis-drag to Complete and back should leave no clock running."""
    assert (
        due_stamp(reached=False, due_on=NOW, status=NOT_REQUESTED, now=NOW) is None
    )


def test_money_already_asked_for_stays_due_wherever_the_board_sits():
    """Once the accountant has been asked, a revision that reopens the
    job does not un-owe the payment."""
    fell_due = NOW - timedelta(days=3)
    for status in (REQUESTED, "Invoiced", PAID):
        assert (
            due_stamp(reached=False, due_on=fell_due, status=status, now=NOW)
            == fell_due
        )


def test_an_unpaid_milestone_is_overdue_once_the_terms_run_out():
    due = NOW - timedelta(days=8)
    assert is_overdue(status=REQUESTED, due_on=due, now=NOW, terms_days=7)


def test_a_milestone_inside_its_payment_terms_is_not_overdue():
    due = NOW - timedelta(days=2)
    assert not is_overdue(status=REQUESTED, due_on=due, now=NOW, terms_days=7)


def test_a_paid_milestone_is_never_overdue():
    due = NOW - timedelta(days=90)
    assert not is_overdue(status=PAID, due_on=due, now=NOW, terms_days=7)


def test_a_milestone_that_has_not_fallen_due_is_not_overdue():
    assert not is_overdue(status=NOT_REQUESTED, due_on=None, now=NOW, terms_days=7)


def test_zero_payment_terms_turns_the_nudge_off():
    """Same switch as the margin floor and the silence nudge."""
    due = NOW - timedelta(days=365)
    assert not is_overdue(status=REQUESTED, due_on=due, now=NOW, terms_days=0)
    assert not is_overdue(status=REQUESTED, due_on=due, now=NOW, terms_days=None)


def test_an_unrequested_milestone_past_its_terms_is_overdue_too():
    """Nobody has even asked the accountant — that is the worst case, not
    an exempt one."""
    due = NOW - timedelta(days=30)
    assert is_overdue(status=NOT_REQUESTED, due_on=due, now=NOW, terms_days=7)


# -- what the accountant is sent --


def test_the_invoice_amount_splits_back_out_of_its_vat():
    """The quoted total carries VAT, so the share of it does too; the
    accountant needs the number before VAT."""
    split = invoice_split(108_000_000, vat_pct=8)
    assert split.net == 100_000_000
    assert split.vat == 8_000_000
    assert split.net + split.vat == 108_000_000


def test_a_vat_free_amount_splits_into_itself():
    split = invoice_split(50_000_000, vat_pct=0)
    assert (split.net, split.vat) == (50_000_000, 0)


CLIENT = {
    "company_name": "Chungify Media",
    "tax_code": "0312345678",
    "address": "12 Nguyễn Huệ, Quận 1, TP.HCM",
}
MILESTONE = {"title": "Đặt cọc", "pct": 50, "amount": 64_152_000}


def test_the_invoice_request_carries_the_client_tax_info_and_the_amount():
    text = invoice_request_text(
        client=CLIENT, milestone=MILESTONE, job_title="MV — Hà Anh Tuấn", vat_pct=8
    )
    assert text == (
        "Nhờ chị xuất hoá đơn giúp em:\n"
        "\n"
        "Khách hàng: Chungify Media\n"
        "Mã số thuế: 0312345678\n"
        "Địa chỉ: 12 Nguyễn Huệ, Quận 1, TP.HCM\n"
        "\n"
        "Nội dung: MV — Hà Anh Tuấn — Đặt cọc (50%)\n"
        "Số tiền: 64.152.000 ₫ (đã gồm VAT 8%)\n"
        "Chưa VAT: 59.400.000 ₫\n"
        "VAT 8%: 4.752.000 ₫\n"
        "\n"
        "Em cảm ơn chị!"
    )


def test_a_missing_tax_code_is_said_out_loud_not_left_blank():
    """A silently missing tax code is a message the accountant bounces;
    the founder should see the gap before pasting it into Zalo."""
    text = invoice_request_text(
        client={**CLIENT, "tax_code": None},
        milestone=MILESTONE,
        job_title="MV",
        vat_pct=8,
    )
    assert "Mã số thuế: (chưa có trong hệ thống)" in text


def test_a_missing_address_is_left_out_rather_than_shown_empty():
    text = invoice_request_text(
        client={**CLIENT, "address": None},
        milestone=MILESTONE,
        job_title="MV",
        vat_pct=8,
    )
    assert "Địa chỉ" not in text


def test_a_whole_percentage_is_written_without_decimals():
    text = invoice_request_text(
        client=CLIENT, milestone=MILESTONE, job_title="MV", vat_pct=8
    )
    assert "(50%)" in text


def test_a_fractional_percentage_keeps_its_decimals_vietnamese_style():
    text = invoice_request_text(
        client=CLIENT,
        milestone={**MILESTONE, "pct": D("33.50")},
        job_title="MV",
        vat_pct=8,
    )
    assert "(33,5%)" in text


def test_a_vat_free_request_says_no_vat_line():
    text = invoice_request_text(
        client=CLIENT,
        milestone={**MILESTONE, "amount": 50_000_000},
        job_title="MV",
        vat_pct=0,
    )
    assert "Số tiền: 50.000.000 ₫" in text
    assert "VAT" not in text

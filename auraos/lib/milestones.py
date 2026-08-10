"""Payment milestones, framework-free (T10 / spec #2, stories 37–40).

Money-in is four rules, none of which needs Frappe to be true:

**Shares of the quoted total.** A milestone bills a percentage of what
the client was quoted, never a number typed in. The shares are rounded
cumulatively so that whatever we chase adds up to the total on the quote
the client agreed to — the last invoice can't be a đồng off.

**The collection flow.** ``chưa yêu cầu → đã yêu cầu KT → đã xuất HĐ →
đã thanh toán``, in English on the enum and Vietnamese wherever a human
reads it. Each step past the first stamps its own time, and stepping
back clears what it undoes: the T6 walkthrough's "if I marked confirmed
by accident, no turning back" is a mistake this repo doesn't repeat.

**The nudge.** A milestone falls due when the job reaches its trigger
stage, and goes overdue when the payment terms run out with the money
uncollected. Terms of 0 turn the nudge off, the same switch the margin
floor and the silence nudge use.

**The invoice request.** The text the founder pastes into Zalo for the
external accountant. Vietnamese, because its reader is: the English-UI
decision (spec #2, story 50) is about the app's chrome, not about
messages written to Vietnamese people.

No Frappe imports by contract; the Job controller and the API are thin
adapters over this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping, Sequence

from auraos.lib.money import format_vnd, round_vnd, to_decimal

# The agreed collection flow, in order. The Vietnamese beside each name
# is what the founder and the accountant call it; the stored value is
# English so the enum reads like every other status in the app.
NOT_REQUESTED = "Not requested"  # chưa yêu cầu
REQUESTED = "Requested"  # đã yêu cầu KT
INVOICED = "Invoiced"  # đã xuất HĐ
PAID = "Paid"  # đã thanh toán

STATUS_FLOW = (NOT_REQUESTED, REQUESTED, INVOICED, PAID)

# Where each step past the first records when it happened. "Not
# requested" is the absence of all of them, so it has no field.
STAMP_FIELDS = {
    REQUESTED: "requested_on",
    INVOICED: "invoiced_on",
    PAID: "paid_on",
}


def status_index(status: str) -> int:
    """Position in the flow; unknown statuses are a programming error."""
    try:
        return STATUS_FLOW.index(status)
    except ValueError:
        raise ValueError(
            f"{status!r} is not a collection status: {', '.join(STATUS_FLOW)}"
        ) from None


# -- what each milestone bills --


def milestone_amounts(total, percents: Sequence) -> list[int]:
    """Each milestone's share of the quoted total, in whole đồng.

    Rounded against the running total rather than one share at a time, so
    the shares of a fully-allocated job add up to the job's quoted total
    exactly. Rounding each share on its own would leave the sum a đồng or
    two adrift from the quote the client signed, and the last invoice is
    where that shows up.
    """
    total = to_decimal(total or 0)
    amounts = []
    cumulative_pct = Decimal(0)
    billed = 0
    for pct in percents:
        cumulative_pct += to_decimal(pct or 0)
        so_far = round_vnd(total * cumulative_pct / 100)
        amounts.append(so_far - billed)
        billed = so_far
    return amounts


def allocated_pct(percents: Sequence) -> Decimal:
    """How much of the quoted total the milestones between them bill."""
    return sum((to_decimal(pct or 0) for pct in percents), Decimal(0))


@dataclass(frozen=True)
class InvoiceSplit:
    """A VAT-inclusive amount, as the accountant needs it written."""

    net: int
    vat: int


def invoice_split(amount, vat_pct) -> InvoiceSplit:
    """Split a milestone amount back out of the VAT it carries.

    The quoted total is VAT-inclusive, so a share of it is too. The
    accountant issues the invoice from the number before VAT; the VAT
    line is the remainder, so the two always add back to the amount the
    client is asked for.
    """
    amount = round_vnd(amount or 0)
    net = round_vnd(to_decimal(amount) / (1 + to_decimal(vat_pct or 0) / 100))
    return InvoiceSplit(net=net, vat=amount - net)


# -- when a milestone falls due, and when it is overdue --


def stage_reached(stage: str | None, trigger: str | None, stages: Sequence[str]) -> bool:
    """Whether a job at `stage` has reached a milestone's trigger stage.

    Reached, not equalled: jobs are dragged around the board and a job
    that jumped from Delivery to Complete still owes the final payment.
    A stage outside the known flow never triggers anything.
    """
    if stage not in stages or trigger not in stages:
        return False
    return stages.index(stage) >= stages.index(trigger)


def due_stamp(
    reached: bool,
    due_on: datetime | None,
    status: str | None,
    now: datetime,
) -> datetime | None:
    """When a milestone fell due, given where the job stands now.

    Stamped the first time the trigger stage is reached and left alone
    afterwards — bouncing a job between stages must not restart the
    payment clock. A job dragged back *before* the trigger un-dues the
    milestone only while nobody has acted on it: once the accountant has
    been asked, the money is owed wherever the board happens to sit.
    """
    if reached:
        return due_on or now
    return None if status == NOT_REQUESTED else due_on


def is_overdue(
    status: str | None,
    due_on: datetime | None,
    now: datetime,
    terms_days: int | None,
) -> bool:
    """Whether a milestone has gone uncollected past the payment terms.

    Anything short of Paid counts, including a milestone nobody has even
    asked the accountant about: that is the worst case, not an exempt
    one.
    """
    if not terms_days or terms_days <= 0:
        return False
    if due_on is None or status == PAID:
        return False
    return (now - due_on).total_seconds() >= terms_days * 86400


def days_overdue(due_on: datetime | None, now: datetime, terms_days: int | None) -> int:
    """How late the money is — days past the terms, not days since due.

    "Eight days late" is what the founder chases on; "fifteen days old"
    counts a week they were never owed anything for.
    """
    if due_on is None:
        return 0
    return max(0, (now - due_on).days - (terms_days or 0))


def stamps_for(status: str, current: Mapping[str, Any], now: datetime) -> dict:
    """The collection timestamps a milestone should hold at `status`.

    Steps already behind the current status keep the time they were first
    recorded; steps ahead of it are cleared, so walking a mis-click back
    leaves no fiction in the record.
    """
    reached = status_index(status)
    return {
        field: (current.get(field) or now) if reached >= status_index(step) else None
        for step, field in STAMP_FIELDS.items()
    }


# -- what the accountant is sent --


def format_pct(pct) -> str:
    """A percentage as Vietnamese writes it: 50%, 33,5%."""
    value = to_decimal(pct or 0).normalize()
    # Decimal.normalize() renders small whole numbers in exponent form
    # (50 -> 5E+1), which is not a percentage anyone wants to read.
    text = f"{value:f}" if value == value.to_integral_value() else str(value)
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",") + "%"


def money(amount) -> str:
    return f"{format_vnd(amount)} ₫"


def invoice_request_text(
    client: Mapping[str, Any],
    milestone: Mapping[str, Any],
    job_title: str | None,
    vat_pct,
) -> str:
    """The message the founder pastes into Zalo for the accountant.

    Everything the accountant asks for on the phone otherwise: who the
    invoice is for, their tax code, what it covers and how much — split
    out of its VAT. A missing tax code is written out as missing rather
    than left blank, because a request without one comes straight back.
    """
    amount = milestone.get("amount")
    split = invoice_split(amount, vat_pct)

    lines = [
        "Nhờ chị xuất hoá đơn giúp em:",
        "",
        f"Khách hàng: {client.get('company_name') or '(chưa có trong hệ thống)'}",
        f"Mã số thuế: {client.get('tax_code') or '(chưa có trong hệ thống)'}",
    ]
    if client.get("address"):
        lines.append(f"Địa chỉ: {client['address']}")
    lines += [
        "",
        f"Nội dung: {job_title} — {milestone.get('title')} "
        f"({format_pct(milestone.get('pct'))})",
    ]
    if split.vat:
        lines += [
            f"Số tiền: {money(amount)} (đã gồm VAT {format_pct(vat_pct)})",
            f"Chưa VAT: {money(split.net)}",
            f"VAT {format_pct(vat_pct)}: {money(split.vat)}",
        ]
    else:
        lines.append(f"Số tiền: {money(amount)}")
    lines += ["", "Em cảm ơn chị!"]
    return "\n".join(lines)

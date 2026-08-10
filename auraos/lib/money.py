"""Framework-free money helpers for Vietnamese đồng amounts.

VND is a whole-number currency. Rounding is half away from zero to match
the company's normative cost-breakdown xlsx (Excel ROUND), not Python's
banker's rounding.
"""

from decimal import ROUND_HALF_UP, Decimal
from numbers import Number


def round_vnd(amount: Number | Decimal) -> int:
    """Round an amount to whole đồng, half away from zero."""
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def format_vnd(amount: Number | Decimal) -> str:
    """Format an amount as whole đồng with dot thousands separators."""
    return f"{round_vnd(amount):,}".replace(",", ".")

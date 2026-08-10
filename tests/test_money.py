"""Pure-python tests for auraos.lib.money — no Frappe required.

House style (per spec Testing Decisions): assert external behavior at a
seam. This seam is the framework-free library that the pricing engine
(T4) will build on. Amounts are Vietnamese đồng: whole-number currency,
half-up rounding to match the normative xlsx.
"""

from decimal import Decimal

import pytest

from auraos.lib.money import format_vnd, round_vnd


class TestRoundVnd:
    def test_whole_amount_passes_through(self):
        assert round_vnd(1_500_000) == 1_500_000

    def test_rounds_half_up_not_bankers(self):
        # Python's built-in round() would give 0 and 2 here; xlsx gives 1 and 3.
        assert round_vnd(0.5) == 1
        assert round_vnd(2.5) == 3

    def test_rounds_down_below_half(self):
        assert round_vnd(1234.4999) == 1234

    def test_negative_amounts_round_half_away_from_zero(self):
        assert round_vnd(-0.5) == -1
        assert round_vnd(-1234.4) == -1234

    def test_accepts_decimal_input(self):
        assert round_vnd(Decimal("999999.5")) == 1_000_000

    def test_returns_int(self):
        assert isinstance(round_vnd(10.2), int)


class TestFormatVnd:
    def test_groups_thousands_with_dots(self):
        assert format_vnd(1_500_000) == "1.500.000"

    def test_rounds_before_formatting(self):
        assert format_vnd(1234.6) == "1.235"

    def test_zero(self):
        assert format_vnd(0) == "0"

    def test_negative(self):
        assert format_vnd(-2_000_000) == "-2.000.000"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))

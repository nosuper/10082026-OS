"""Pure-python tests for auraos.lib.pricing - no Frappe required.

The engine's normative definition is the repo's cost-breakdown xlsx
(docs/samples/cost-breakdown-template.xlsx). These tests pin each rule
individually; test_pricing_parity.py pins the filled example end to end.

Rules under test (per T4 / spec #2):
- Tax types: Công ty (8% VAT), Cty 10%, Cá nhân (PIT gross-up net÷0.9),
  Không hoá đơn (no VAT, zero input VAT, still costs).
- Vendor management fee on cost lines; per-line markup; quote-level MF + VAT.
- Package sum, manual override, and variance.
- Profit chain: margin → CMF → CM → lợi nhuận trước thuế → TNDN 20% →
  net profit → VAT phải nộp (output − input).
- Floor breach as a pure function.
"""

import sys
from decimal import Decimal

import pytest

from auraos.lib.money import round_vnd
from auraos.lib.pricing import (
    CostLine,
    DealParams,
    TaxType,
    compute_line,
    compute_quote,
    is_floor_breached,
    package_price,
)

D = Decimal


def line(**kwargs):
    """A minimal valid cost line; override per test."""
    defaults = dict(
        qty1=1,
        qty2=1,
        unit_price=1_000_000,
        tax_type=TaxType.CONG_TY,
        vendor_mf_rate=0,
        markup_rate=0,
    )
    defaults.update(kwargs)
    return CostLine(**defaults)


class TestTaxTypeParsing:
    def test_parses_canonical_labels(self):
        assert TaxType.parse("Công ty") is TaxType.CONG_TY
        assert TaxType.parse("Cty 10%") is TaxType.CTY_10
        assert TaxType.parse("Cá nhân") is TaxType.CA_NHAN
        assert TaxType.parse("Không hoá đơn") is TaxType.KHONG_HOA_DON

    def test_parse_is_case_insensitive_like_excel_switch(self):
        # The filled xlsx itself writes "Công Ty" on one row.
        assert TaxType.parse("Công Ty") is TaxType.CONG_TY
        assert TaxType.parse("cá nhân") is TaxType.CA_NHAN

    def test_parse_accepts_hoa_spelling_variant(self):
        assert TaxType.parse("Không hóa đơn") is TaxType.KHONG_HOA_DON

    def test_parse_rejects_unknown_label(self):
        with pytest.raises(ValueError):
            TaxType.parse("VAT 5%")


class TestCongTy8:
    def test_vat_is_8_percent_of_cost_after_mf(self):
        c = compute_line(line(unit_price=2_000_000), DealParams())
        assert c.vat_pit == D("160000")

    def test_input_vat_equals_vat(self):
        c = compute_line(line(unit_price=2_000_000), DealParams())
        assert c.input_vat == D("160000")

    def test_profit_cost_basis_is_net(self):
        c = compute_line(line(unit_price=2_000_000), DealParams())
        assert c.profit_cost_basis == D("2000000")

    def test_internal_gross_is_net_plus_vat(self):
        c = compute_line(line(unit_price=2_000_000), DealParams())
        assert c.internal_gross == D("2160000")


class TestCty10:
    def test_vat_is_10_percent(self):
        c = compute_line(line(tax_type=TaxType.CTY_10), DealParams())
        assert c.vat_pit == D("100000")

    def test_input_vat_equals_vat(self):
        c = compute_line(line(tax_type=TaxType.CTY_10), DealParams())
        assert c.input_vat == D("100000")

    def test_profit_cost_basis_is_net(self):
        c = compute_line(line(tax_type=TaxType.CTY_10), DealParams())
        assert c.profit_cost_basis == D("1000000")


class TestCaNhanGrossUp:
    """PIT gross-up: freelancer net ÷ 0.9 is the true cost; tax = net/9."""

    def test_pit_is_net_over_nine(self):
        c = compute_line(line(tax_type=TaxType.CA_NHAN, unit_price=900_000), DealParams())
        assert c.vat_pit == D("100000")

    def test_profit_cost_basis_is_net_over_0_9(self):
        c = compute_line(line(tax_type=TaxType.CA_NHAN, unit_price=900_000), DealParams())
        assert c.profit_cost_basis == D("1000000")

    def test_no_input_vat(self):
        c = compute_line(line(tax_type=TaxType.CA_NHAN), DealParams())
        assert c.input_vat == 0

    def test_gross_up_survives_rounding_to_the_dong(self):
        c = compute_line(line(tax_type=TaxType.CA_NHAN, unit_price=1_000_000), DealParams())
        assert round_vnd(c.vat_pit) == 111_111
        assert round_vnd(c.profit_cost_basis) == 1_111_111

    def test_markup_applies_to_grossed_up_unit_price(self):
        # xlsx: U = (I/0.9) * (1+MU) for Cá nhân
        c = compute_line(
            line(tax_type=TaxType.CA_NHAN, unit_price=500_000, markup_rate="0.8", qty1=2),
            DealParams(),
        )
        assert c.markup_unit_price == D("1000000")
        assert c.line_total == D("2000000")


class TestKhongHoaDon:
    def test_no_vat(self):
        c = compute_line(line(tax_type=TaxType.KHONG_HOA_DON), DealParams())
        assert c.vat_pit == 0

    def test_zero_input_vat(self):
        c = compute_line(line(tax_type=TaxType.KHONG_HOA_DON), DealParams())
        assert c.input_vat == 0

    def test_still_costs_at_face_value(self):
        c = compute_line(line(tax_type=TaxType.KHONG_HOA_DON), DealParams())
        assert c.profit_cost_basis == D("1000000")
        assert c.internal_gross == D("1000000")


class TestVendorMf:
    def test_vendor_mf_inflates_cost(self):
        c = compute_line(line(vendor_mf_rate="0.1"), DealParams())
        assert c.subtotal_int_net == D("1000000")
        assert c.cost_after_vendor_mf == D("1100000")

    def test_tax_computed_on_cost_after_mf(self):
        c = compute_line(line(vendor_mf_rate="0.1"), DealParams())
        assert c.vat_pit == D("88000")  # 8% of 1.1m

    def test_markup_price_ignores_vendor_mf(self):
        # xlsx markup column starts from the raw unit price, not cost-after-MF;
        # the markup has to cover the vendor MF.
        c = compute_line(line(vendor_mf_rate="0.1", markup_rate="0.5"), DealParams())
        assert c.markup_unit_price == D("1500000")


class TestQuantitiesAndMarkup:
    def test_two_unit_quantities_multiply(self):
        c = compute_line(line(qty1=2, qty2=3, unit_price=500_000), DealParams())
        assert c.subtotal_int_net == D("3000000")

    def test_markup_scales_unit_price(self):
        c = compute_line(line(markup_rate="0.5"), DealParams())
        assert c.markup_unit_price == D("1500000")

    def test_line_total_is_markup_price_times_quantities(self):
        c = compute_line(line(qty1=2, qty2=3, unit_price=500_000, markup_rate="0.5"), DealParams())
        assert c.line_total == D("4500000")


class TestQuoteMfAndVatChain:
    """Per line: budget → +quote MF → +VAT, and the margin columns."""

    def test_budget_is_line_total(self):
        c = compute_line(line(markup_rate="0.5"), DealParams())
        assert c.budget == c.line_total == D("1500000")

    def test_quote_mf_default_10_percent(self):
        c = compute_line(line(), DealParams())
        assert c.quote_mf == D("100000")
        assert c.after_quote_mf == D("1100000")

    def test_vat_default_8_percent_on_after_mf(self):
        c = compute_line(line(), DealParams())
        assert c.vat == D("88000")
        assert c.subtotal_with_vat == D("1188000")

    def test_margin_is_after_mf_minus_cost_basis(self):
        c = compute_line(line(markup_rate="0.5"), DealParams())
        # Z = 1.5m * 1.1 = 1.65m; O = 1m
        assert c.margin == D("650000")
        assert c.margin_pct == D("650000") / D("1650000")

    def test_cmf_and_cm(self):
        c = compute_line(line(markup_rate="0.5"), DealParams())
        assert c.cmf == D("82500")  # 5% of 1.65m
        assert c.cm == D("567500")
        assert c.cm_pct == D("567500") / D("1650000")

    def test_custom_rates(self):
        p = DealParams(quote_mf_rate="0.2", vat_rate="0.1", commission_rate=0)
        c = compute_line(line(), p)
        assert c.after_quote_mf == D("1200000")
        assert c.vat == D("120000")
        assert c.cmf == 0

    def test_zero_budget_line_has_no_percentages(self):
        c = compute_line(line(unit_price=0), DealParams())
        assert c.margin_pct is None
        assert c.cm_pct is None


class TestQuoteTotals:
    """The two-line filled example, computed from first principles."""

    def lines(self):
        return [
            line(qty1=2, unit_price=500_000, tax_type=TaxType.CA_NHAN, markup_rate="0.8"),
            line(unit_price=2_000_000, tax_type=TaxType.CONG_TY, markup_rate="0.5"),
        ]

    def test_external_price_block(self):
        q = compute_quote(self.lines(), DealParams())
        assert q.subtotal == D("5000000")
        assert q.management_fee == D("500000")
        assert q.vat == D("440000")
        assert q.total == D("5940000")

    def test_profit_chain(self):
        q = compute_quote(self.lines(), DealParams())
        assert q.revenue_ex_vat == D("5500000")
        assert round_vnd(q.total_profit_cost_basis) == 3_111_111
        assert q.total_commission == D("275000")
        assert round_vnd(q.profit_before_tax) == 2_113_889
        assert round_vnd(q.tndn) == 422_778
        assert round_vnd(q.net_profit) == 1_691_111

    def test_tndn_is_20_percent_of_profit_before_tax(self):
        q = compute_quote(self.lines(), DealParams())
        assert q.tndn == q.profit_before_tax * D("0.2")
        assert q.net_profit == q.profit_before_tax - q.tndn

    def test_vat_payable_is_output_minus_input(self):
        q = compute_quote(self.lines(), DealParams())
        # output 440k − input 160k (only the Công ty line carries input VAT)
        assert q.vat_payable == D("280000")

    def test_khong_hoa_don_contributes_zero_input_vat_to_payable(self):
        q = compute_quote(
            [line(tax_type=TaxType.KHONG_HOA_DON), line(tax_type=TaxType.CONG_TY)],
            DealParams(),
        )
        assert q.vat_payable == q.vat - D("80000")

    def test_computed_lines_are_exposed(self):
        q = compute_quote(self.lines(), DealParams())
        assert [c.budget for c in q.lines] == [D("2000000"), D("3000000")]

    def test_empty_quote_is_all_zero(self):
        q = compute_quote([], DealParams())
        assert q.total == 0
        assert q.profit_before_tax == 0
        assert q.vat_payable == 0


class TestPackagePrice:
    def test_defaults_to_sum_of_member_line_totals(self):
        p = package_price([2_000_000, 3_000_000])
        assert p.default == D("5000000")
        assert p.price == D("5000000")
        assert p.variance == 0
        assert p.overridden is False

    def test_override_records_variance(self):
        p = package_price([2_000_000, 3_000_000], override=5_500_000)
        assert p.price == D("5500000")
        assert p.variance == D("500000")
        assert p.overridden is True

    def test_rounding_down_shows_negative_variance(self):
        p = package_price([2_000_000, 3_000_000], override=4_900_000)
        assert p.variance == D("-100000")

    def test_override_equal_to_default_still_counts_as_override(self):
        p = package_price([1_000_000], override=1_000_000)
        assert p.variance == 0
        assert p.overridden is True

    def test_empty_package(self):
        p = package_price([])
        assert p.default == 0
        assert p.price == 0


class TestFloorBreach:
    def test_below_floor_breaches(self):
        assert is_floor_breached(D("0.25"), D("0.30")) is True

    def test_at_floor_does_not_breach(self):
        assert is_floor_breached(D("0.30"), D("0.30")) is False

    def test_above_floor_does_not_breach(self):
        assert is_floor_breached(D("0.35"), D("0.30")) is False

    def test_unknown_margin_counts_as_breach(self):
        # A quote whose margin can't be computed (zero revenue) must warn.
        assert is_floor_breached(None, D("0.30")) is True


class TestContingency:
    """§3.1.4: contingency is inside cost and before markup.

    The playbook's sentence is "chi phí dự phòng thật, không phải lợi
    nhuận" - a real reserve, not profit - and each test here pins one
    half of what that has to mean arithmetically. The one that matters
    most is test_margin_percentage_is_untouched: it is the difference
    between a reserve and a hidden price rise, and it is the assertion
    that fails if someone later "simplifies" this into an uplift on the
    price alone.
    """

    def test_default_is_an_identity(self):
        # Every deal quoted before contingency existed recomputes on every
        # save. An unset rate has to leave those figures exactly alone.
        priced = line(unit_price=1_000_000, markup_rate=D("0.2"))
        assert compute_line(priced, DealParams()) == compute_line(
            priced, DealParams(contingency_rate=0)
        )

    def test_it_is_inside_the_cost_basis(self):
        priced = line(unit_price=1_000_000, tax_type=TaxType.KHONG_HOA_DON)
        plain = compute_line(priced, DealParams())
        with_reserve = compute_line(priced, DealParams(contingency_rate=D("0.1")))
        assert with_reserve.profit_cost_basis == plain.profit_cost_basis * D("1.1")

    def test_markup_applies_after_it(self):
        # Not a second markup line: the reserve enters the base the markup
        # is taken on, so the price moves by the reserve times the markup.
        priced = line(
            unit_price=1_000_000, markup_rate=D("0.2"), tax_type=TaxType.KHONG_HOA_DON
        )
        plain = compute_line(priced, DealParams())
        with_reserve = compute_line(priced, DealParams(contingency_rate=D("0.1")))
        assert with_reserve.budget == plain.budget * D("1.1")

    def test_margin_percentage_is_untouched(self):
        # The whole claim. Cost and price scale together, so the reserve
        # cannot show up as profit - which is what the playbook forbids.
        priced = line(
            unit_price=1_000_000, markup_rate=D("0.25"), tax_type=TaxType.CONG_TY
        )
        plain = compute_line(priced, DealParams())
        with_reserve = compute_line(priced, DealParams(contingency_rate=D("0.1")))
        assert with_reserve.margin_pct == plain.margin_pct
        assert with_reserve.margin > plain.margin

    def test_no_input_vat_on_money_not_yet_spent(self):
        # There is no supplier invoice behind a reserve, so there is
        # nothing to reclaim against. Scaling input VAT with it would
        # understate VAT phải nộp, which is the direction that costs money
        # at an audit.
        priced = line(unit_price=1_000_000, tax_type=TaxType.CONG_TY)
        plain = compute_line(priced, DealParams())
        with_reserve = compute_line(priced, DealParams(contingency_rate=D("0.1")))
        assert with_reserve.input_vat == plain.input_vat

    def test_a_freelancer_reserve_is_taken_on_the_grossed_cost(self):
        # Cá nhân costs the company net ÷ 0.9, and that grossed figure is
        # what it actually bears - so the reserve is 10% of it, not of the
        # net the freelancer quoted. PIT itself stays off the reserve for
        # the same reason input VAT does: nobody has been paid it.
        priced = line(unit_price=900_000, tax_type=TaxType.CA_NHAN)
        plain = compute_line(priced, DealParams())
        with_reserve = compute_line(priced, DealParams(contingency_rate=D("0.1")))
        assert with_reserve.profit_cost_basis == plain.profit_cost_basis * D("1.1")
        assert with_reserve.vat_pit == plain.vat_pit


class TestPurity:
    def test_module_never_imports_frappe(self):
        assert "auraos.lib.pricing" in sys.modules
        assert "frappe" not in sys.modules


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))

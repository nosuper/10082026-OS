"""lib/breakdown - the one assembly of the money view.

These pin the seam the live editor endpoint and the persisted Deal both
sit on. The site tests keep proving the two adapters wire it up with
the right permissions; the arithmetic and the dict shape live here,
bench-free.
"""

import pytest

from auraos.lib import breakdown, pricing, quote
from auraos.lib.breakdown import breakdown_view, rate
from auraos.lib.money import round_vnd

LINES = [
    {
        "description": "Đạo diễn",
        "package": "Crew",
        "qty1": 1,
        "qty2": 2,
        "unit_price": 4_000_000,
        "tax_type": "Cá nhân",
        "vendor_mf_pct": 0,
        "markup_pct": 20,
    },
    {
        "description": "Thuê máy",
        "package": "Crew",
        "qty1": 1,
        "qty2": 2,
        "unit_price": 2_000_000,
        "tax_type": "Công ty",
        "vendor_mf_pct": 5,
        "markup_pct": 25,
    },
    {
        # No package: quoted standalone at its marked-up price.
        "description": "Data/DIT",
        "package": "",
        "qty1": 1,
        "qty2": 1,
        "unit_price": 1_500_000,
        "tax_type": "Không hoá đơn",
        "vendor_mf_pct": 0,
        "markup_pct": 30,
    },
]

PACKAGES = [{"title": "Crew", "has_price_override": 0, "price_override": None}]

PARAMS = {"quote_mf_pct": 10, "vat_pct": 8, "commission_pct": 5}


def engine_result():
    return pricing.compute_quote(
        breakdown.engine_lines(LINES),
        pricing.DealParams(
            quote_mf_rate=rate(10), vat_rate=rate(8), commission_rate=rate(5)
        ),
    )


def test_line_values_agree_with_the_engine():
    view = breakdown_view(LINES, PACKAGES, **PARAMS)
    for line_view, line in zip(view["lines"], engine_result().lines):
        assert line_view["subtotal"] == round_vnd(line.subtotal_int_net)
        assert line_view["cost_basis"] == round_vnd(line.profit_cost_basis)
        assert line_view["input_vat"] == round_vnd(line.input_vat)
        assert line_view["quote_price"] == round_vnd(line.budget)
        assert line_view["margin"] == round_vnd(line.margin)


def test_package_price_is_the_member_sum():
    view = breakdown_view(LINES, PACKAGES, **PARAMS)
    crew = view["packages"][0]
    members = [
        round_vnd(line.budget)
        for row, line in zip(LINES, engine_result().lines)
        if row["package"] == "Crew"
    ]
    assert crew["price"] == crew["default_price"]
    assert crew["default_price"] == round_vnd(sum(members))
    assert crew["variance"] == 0
    assert not crew["overridden"]


def test_a_zero_dong_override_is_a_real_price():
    packages = [{"title": "Crew", "has_price_override": 1, "price_override": 0}]
    view = breakdown_view(LINES, packages, **PARAMS)
    crew = view["packages"][0]
    assert crew["overridden"]
    assert crew["price"] == 0
    assert crew["variance"] == -crew["default_price"]


def test_an_override_without_its_flag_is_ignored():
    packages = [
        {"title": "Crew", "has_price_override": 0, "price_override": 9_999_999}
    ]
    view = breakdown_view(LINES, packages, **PARAMS)
    assert not view["packages"][0]["overridden"]
    assert view["packages"][0]["price"] == view["packages"][0]["default_price"]


def test_totals_are_measured_against_what_the_client_reads():
    """Package prices plus standalone lines - never the raw line sum."""
    view = breakdown_view(LINES, PACKAGES, **PARAMS)
    standalone = view["lines"][2]["quote_price"]
    client_subtotal = view["packages"][0]["price"] + standalone
    chain = quote.quote_chain(
        [view["packages"][0]["price"], standalone],
        cost_basis=engine_result().total_profit_cost_basis,
        input_vat=engine_result().total_input_vat,
        mf_rate=rate(10),
        vat_rate=rate(8),
        commission_rate=rate(5),
    )
    assert view["subtotal"] == round_vnd(chain.subtotal) == client_subtotal
    assert view["management_fee"] == round_vnd(chain.mf_amount)
    assert view["vat"] == round_vnd(chain.vat_amount)
    assert view["total"] == round_vnd(chain.total)
    assert view["margin"] == round_vnd(chain.margin)
    assert view["margin_pct"] == pytest.approx(float(chain.margin_fraction * 100))


def test_founder_block_agrees_with_the_chain():
    view = breakdown_view(LINES, PACKAGES, **PARAMS)
    result = engine_result()
    chain = quote.quote_chain(
        [view["packages"][0]["price"], view["lines"][2]["quote_price"]],
        cost_basis=result.total_profit_cost_basis,
        input_vat=result.total_input_vat,
        mf_rate=rate(10),
        vat_rate=rate(8),
        commission_rate=rate(5),
    )
    assert view["founder"] == {
        "total_commission": round_vnd(chain.total_commission),
        "cm": round_vnd(chain.cm),
        "profit_before_tax": round_vnd(chain.profit_before_tax),
        "tndn": round_vnd(chain.tndn),
        "net_profit": round_vnd(chain.net_profit),
        "total_input_vat": round_vnd(result.total_input_vat),
        "vat_payable": round_vnd(chain.vat_payable),
    }


def test_floor_breach_flags_a_thin_margin():
    view = breakdown_view(LINES, PACKAGES, **PARAMS, margin_floor_pct=99)
    assert view["floor_breached"]


def test_floor_of_zero_never_warns():
    view = breakdown_view(LINES, PACKAGES, **PARAMS, margin_floor_pct=0)
    assert not view["floor_breached"]


def test_an_empty_breakdown_has_nothing_to_breach():
    view = breakdown_view([], [], **PARAMS, margin_floor_pct=20)
    assert view["lines"] == []
    assert view["subtotal"] == 0
    assert not view["floor_breached"]


def test_an_unknown_tax_type_is_a_value_error():
    bad = [{**LINES[0], "tax_type": "Chịu"}]
    with pytest.raises(ValueError):
        breakdown_view(bad, [], **PARAMS)

"""xlsx parity: the engine's acceptance test.

Feeds the filled example in docs/samples/cost-breakdown-template.xlsx
through the pricing engine and asserts every computed column and every
quote-level total matches the spreadsheet's cached values to the đồng.
The workbook is the normative definition of the math; this test is what
makes that sentence enforceable.

Requires openpyxl (test dependency only - the engine itself needs nothing).
"""

from decimal import Decimal
from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")

from auraos.lib.money import round_vnd
from auraos.lib.pricing import (
    CostLine,
    DealParams,
    TaxType,
    compute_line,
    compute_quote,
)

WORKBOOK = Path(__file__).parent.parent / "docs" / "samples" / "cost-breakdown-template.xlsx"

# Line-item table geometry (see the sheet's row 9 headers).
FIRST_DATA_ROW, LAST_DATA_ROW = 10, 26

# Engine field → xlsx column, for every computed money column.
MONEY_COLUMNS = {
    "subtotal_int_net": "J",
    "cost_after_vendor_mf": "L",
    "vat_pit": "N",
    "profit_cost_basis": "O",
    "input_vat": "P",
    "internal_gross": "Q",
    "markup_unit_price": "U",
    "line_total": "V",
    "budget": "X",
    "quote_mf": "Y",
    "after_quote_mf": "Z",
    "vat": "AA",
    "subtotal_with_vat": "AB",
    "margin": "AC",
    "cmf": "AE",
    "cm": "AF",
}
PCT_COLUMNS = {"margin_pct": "AD", "cm_pct": "AG"}

QUOTE_CELLS = {
    "subtotal": "C17",
    "management_fee": "C18",
    "vat": "C19",
    "total": "C20",
    "revenue_ex_vat": "G17",
    "profit_before_tax": "G20",
    "tndn": "G21",
    "net_profit": "G22",
    "vat_payable": "G23",
}
# G18/G19 are displayed negated (costs subtracted from revenue).
NEGATED_QUOTE_CELLS = {
    "total_profit_cost_basis": "G18",
    "total_commission": "G19",
}


def sheet():
    return openpyxl.load_workbook(WORKBOOK, data_only=True)["Sheet1"]


def load_fixture():
    ws = sheet()
    params = DealParams(
        quote_mf_rate=Decimal(str(ws["Y8"].value)),
        vat_rate=Decimal("0.08"),  # hardcoded as 8% in the sheet's formulas
        commission_rate=Decimal(str(ws["AE8"].value)),
    )
    rows = []
    for r in range(FIRST_DATA_ROW, LAST_DATA_ROW + 1):
        if ws[f"J{r}"].value is None:
            continue
        rows.append(
            (
                r,
                CostLine(
                    qty1=Decimal(str(ws[f"E{r}"].value)),
                    qty2=Decimal(str(ws[f"G{r}"].value)),
                    unit_price=Decimal(str(ws[f"I{r}"].value)),
                    tax_type=TaxType.parse(ws[f"M{r}"].value),
                    vendor_mf_rate=Decimal(str(ws[f"K{r}"].value or 0)),
                    markup_rate=Decimal(str(ws[f"S{r}"].value or 0)),
                ),
            )
        )
    return ws, params, rows


WS, PARAMS, ROWS = load_fixture()


def test_fixture_has_filled_rows():
    assert ROWS, "the sample workbook must contain at least one filled cost line"


@pytest.mark.parametrize("row,line", ROWS, ids=[f"row{r}" for r, _ in ROWS])
@pytest.mark.parametrize("field,col", MONEY_COLUMNS.items(), ids=MONEY_COLUMNS.keys())
def test_line_money_columns_match_to_the_dong(row, line, field, col):
    computed = compute_line(line, PARAMS)
    expected = WS[f"{col}{row}"].value or 0
    assert round_vnd(getattr(computed, field)) == round_vnd(expected), (
        f"{field} ({col}{row}) diverges from the workbook"
    )


@pytest.mark.parametrize("row,line", ROWS, ids=[f"row{r}" for r, _ in ROWS])
@pytest.mark.parametrize("field,col", PCT_COLUMNS.items(), ids=PCT_COLUMNS.keys())
def test_line_percentage_columns_match(row, line, field, col):
    computed = compute_line(line, PARAMS)
    expected = Decimal(str(WS[f"{col}{row}"].value))
    assert abs(getattr(computed, field) - expected) < Decimal("1e-9")


@pytest.mark.parametrize("field,cell", QUOTE_CELLS.items(), ids=QUOTE_CELLS.keys())
def test_quote_totals_match_to_the_dong(field, cell):
    quote = compute_quote([line for _, line in ROWS], PARAMS)
    assert round_vnd(getattr(quote, field)) == round_vnd(WS[cell].value), (
        f"{field} ({cell}) diverges from the workbook"
    )


@pytest.mark.parametrize("field,cell", NEGATED_QUOTE_CELLS.items(), ids=NEGATED_QUOTE_CELLS.keys())
def test_negated_quote_totals_match_to_the_dong(field, cell):
    quote = compute_quote([line for _, line in ROWS], PARAMS)
    assert round_vnd(getattr(quote, field)) == -round_vnd(WS[cell].value)


def test_average_cm_pct_matches_h20():
    quote = compute_quote([line for _, line in ROWS], PARAMS)
    pcts = [c.cm_pct for c in quote.lines if c.cm_pct is not None]
    avg = sum(pcts) / len(pcts)
    assert abs(avg - Decimal(str(WS["H20"].value))) < Decimal("1e-9")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))

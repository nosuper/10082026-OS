"""The pricing engine: cost lines + deal parameters in, the full computed
chain out.

Framework-free by contract (T4 / spec #2): no Frappe imports; DocType
controllers are thin adapters over this module. The normative definition
of the math is the repo's cost-breakdown xlsx
(docs/samples/cost-breakdown-template.xlsx); column letters in comments
refer to it. All arithmetic is exact Decimal — rounding to whole đồng is
the caller's concern (auraos.lib.money.round_vnd).

Per line:
    subtotal (J) = qty1 × qty2 × unit price
    cost after vendor MF (L) = J × (1 + vendor MF)
    VAT/PIT (N), profit cost basis (O), input VAT (P) — by tax type
    internal gross (Q) = L + N
    markup unit price (U) = (unit price, grossed up for Cá nhân) × (1 + markup)
    line total / budget (V, X) = U × qty1 × qty2
    quote MF (Y) = X × quote MF rate; after MF (Z) = X + Y
    VAT (AA) = Z × VAT rate; subtotal with VAT (AB) = Z + AA
    margin (AC) = Z − O;  CMF (AE) = Z × commission;  CM (AF) = AC − AE

Quote level:
    subtotal = Σ budget; MF; VAT on (subtotal + MF); total
    lợi nhuận trước thuế = revenue ex VAT − Σ cost basis − Σ CMF
    TNDN = 20% of that; net profit = remainder
    VAT phải nộp = output VAT − Σ input VAT
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from numbers import Number
from typing import Iterable, Sequence

from auraos.lib.money import to_decimal as _d

Amount = Number | Decimal | str

TNDN_RATE = Decimal("0.2")


class TaxType(Enum):
    """Per-line tax treatment, named as in the xlsx dropdown."""

    CONG_TY = "Công ty"  # invoice with 8% VAT
    CTY_10 = "Cty 10%"  # invoice with 10% VAT
    CA_NHAN = "Cá nhân"  # freelancer: PIT gross-up, net ÷ 0.9
    KHONG_HOA_DON = "Không hoá đơn"  # no invoice: no VAT either way

    @classmethod
    def parse(cls, label: str) -> "TaxType":
        """Match a label the way Excel's SWITCH does: case-insensitively.

        Also tolerates the hóa/hoá spelling variants (same word, both occur
        in real data).
        """
        key = unicodedata.normalize("NFC", label).strip().lower().replace("hóa", "hoá")
        for member in cls:
            if member.value.lower() == key:
                return member
        raise ValueError(f"Unknown tax type: {label!r}")


VAT_RATE_BY_TAX_TYPE = {
    TaxType.CONG_TY: Decimal("0.08"),
    TaxType.CTY_10: Decimal("0.10"),
}


@dataclass(frozen=True)
class CostLine:
    """One row of the internal cost breakdown."""

    qty1: Amount
    qty2: Amount
    unit_price: Amount
    tax_type: TaxType
    vendor_mf_rate: Amount = 0
    markup_rate: Amount = 0


@dataclass(frozen=True)
class DealParams:
    """Quote-level rates. Defaults are the company's standing practice."""

    quote_mf_rate: Amount = Decimal("0.10")
    vat_rate: Amount = Decimal("0.08")
    commission_rate: Amount = Decimal("0.05")


@dataclass(frozen=True)
class ComputedLine:
    """Every computed column for one cost line (xlsx letters in comments)."""

    subtotal_int_net: Decimal  # J
    cost_after_vendor_mf: Decimal  # L
    vat_pit: Decimal  # N
    profit_cost_basis: Decimal  # O — chi phí tính lãi
    input_vat: Decimal  # P — VAT đầu vào
    internal_gross: Decimal  # Q
    markup_unit_price: Decimal  # U
    line_total: Decimal  # V
    budget: Decimal  # X
    quote_mf: Decimal  # Y
    after_quote_mf: Decimal  # Z
    vat: Decimal  # AA
    subtotal_with_vat: Decimal  # AB
    margin: Decimal  # AC
    margin_pct: Decimal | None  # AD — None when the line has no revenue
    cmf: Decimal  # AE
    cm: Decimal  # AF
    cm_pct: Decimal | None  # AG


@dataclass(frozen=True)
class QuoteResult:
    """Quote-level totals plus the computed lines they were built from."""

    lines: tuple[ComputedLine, ...]
    subtotal: Decimal  # Σ budget
    management_fee: Decimal
    vat: Decimal  # output VAT
    total: Decimal  # client-facing total
    revenue_ex_vat: Decimal  # doanh thu chưa VAT
    total_profit_cost_basis: Decimal  # Σ chi phí tính lãi
    total_commission: Decimal  # Σ CMF
    profit_before_tax: Decimal  # lợi nhuận trước thuế
    tndn: Decimal
    net_profit: Decimal
    total_input_vat: Decimal
    vat_payable: Decimal  # VAT phải nộp


def compute_line(line: CostLine, params: DealParams) -> ComputedLine:
    qty1, qty2 = _d(line.qty1), _d(line.qty2)
    unit_price = _d(line.unit_price)
    vendor_mf_rate = _d(line.vendor_mf_rate)
    markup_rate = _d(line.markup_rate)
    quote_mf_rate = _d(params.quote_mf_rate)
    vat_rate = _d(params.vat_rate)
    commission_rate = _d(params.commission_rate)
    tax = line.tax_type

    subtotal = qty1 * qty2 * unit_price
    cost_after_mf = subtotal * (1 + vendor_mf_rate)

    input_vat = cost_after_mf * VAT_RATE_BY_TAX_TYPE.get(tax, Decimal(0))
    if tax is TaxType.CA_NHAN:
        # Freelancer quotes a net figure; the company bears 10% PIT on the
        # gross, so true cost = net ÷ 0.9 and the tax itself = net ÷ 9.
        vat_pit = cost_after_mf / 9
        profit_cost_basis = cost_after_mf / Decimal("0.9")
        grossed_unit_price = unit_price / Decimal("0.9")
    else:
        vat_pit = input_vat
        profit_cost_basis = cost_after_mf
        grossed_unit_price = unit_price

    # Markup starts from the (grossed-up) unit price, not cost-after-MF:
    # the markup is expected to cover any vendor MF.
    markup_unit_price = grossed_unit_price * (1 + markup_rate)
    line_total = markup_unit_price * qty1 * qty2

    budget = line_total
    quote_mf = budget * quote_mf_rate
    after_quote_mf = budget + quote_mf
    vat = after_quote_mf * vat_rate

    margin = after_quote_mf - profit_cost_basis
    cmf = after_quote_mf * commission_rate
    cm = margin - cmf

    has_revenue = after_quote_mf != 0
    return ComputedLine(
        subtotal_int_net=subtotal,
        cost_after_vendor_mf=cost_after_mf,
        vat_pit=vat_pit,
        profit_cost_basis=profit_cost_basis,
        input_vat=input_vat,
        internal_gross=cost_after_mf + vat_pit,
        markup_unit_price=markup_unit_price,
        line_total=line_total,
        budget=budget,
        quote_mf=quote_mf,
        after_quote_mf=after_quote_mf,
        vat=vat,
        subtotal_with_vat=after_quote_mf + vat,
        margin=margin,
        margin_pct=margin / after_quote_mf if has_revenue else None,
        cmf=cmf,
        cm=cm,
        cm_pct=cm / after_quote_mf if has_revenue else None,
    )


def compute_quote(lines: Iterable[CostLine], params: DealParams) -> QuoteResult:
    computed = tuple(compute_line(line, params) for line in lines)

    subtotal = sum((c.budget for c in computed), Decimal(0))
    management_fee = subtotal * _d(params.quote_mf_rate)
    revenue_ex_vat = subtotal + management_fee
    vat = revenue_ex_vat * _d(params.vat_rate)

    total_profit_cost_basis = sum((c.profit_cost_basis for c in computed), Decimal(0))
    total_commission = sum((c.cmf for c in computed), Decimal(0))
    profit_before_tax = revenue_ex_vat - total_profit_cost_basis - total_commission
    tndn = profit_before_tax * TNDN_RATE

    total_input_vat = sum((c.input_vat for c in computed), Decimal(0))

    return QuoteResult(
        lines=computed,
        subtotal=subtotal,
        management_fee=management_fee,
        vat=vat,
        total=revenue_ex_vat + vat,
        revenue_ex_vat=revenue_ex_vat,
        total_profit_cost_basis=total_profit_cost_basis,
        total_commission=total_commission,
        profit_before_tax=profit_before_tax,
        tndn=tndn,
        net_profit=profit_before_tax - tndn,
        total_input_vat=total_input_vat,
        vat_payable=vat - total_input_vat,
    )


@dataclass(frozen=True)
class PackagePrice:
    """A client-facing package price and its link back to member-line cost."""

    default: Decimal  # Σ member line totals
    price: Decimal  # override if given, else default
    variance: Decimal  # price − default
    overridden: bool


def package_price(
    member_line_totals: Sequence[Amount], override: Amount | None = None
) -> PackagePrice:
    default = sum((_d(t) for t in member_line_totals), Decimal(0))
    price = _d(override) if override is not None else default
    return PackagePrice(
        default=default,
        price=price,
        variance=price - default,
        overridden=override is not None,
    )


def is_floor_breached(margin_pct: Amount | None, floor_pct: Amount) -> bool:
    """True when a quote's margin falls below the global floor.

    A margin that cannot be computed (None — no revenue) always breaches:
    the warning must fail safe.
    """
    if margin_pct is None:
        return True
    return _d(margin_pct) < _d(floor_pct)

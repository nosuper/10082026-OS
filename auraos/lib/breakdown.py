"""One assembly of the money view of a breakdown.

The live editor endpoint (auraos.api.compute_breakdown), the persisted
Deal fields (Deal.compute_breakdown), and the founder profit views all
render the same thing: engine results per line, package prices as the
client will read them, the client-facing chain, and the founder-only
profit numbers. Before this module existed those assemblies lived
apart - api.py and deal.py each built the whole thing, with a site test
policing their agreement. Now there is one builder and the callers are
adapters.

Framework-free like the rest of lib/: rows come in as plain mappings,
errors are ValueError, and the caller owns permissions, persistence and
HTTP shapes.
"""

from .money import round_vnd, to_decimal
from . import pricing, quote


def rate(pct):
    """A Percent field value (10 = 10%) as the engine's fractional rate."""
    return to_decimal(pct or 0) / 100


def engine_lines(rows):
    """Cost-line mappings as engine CostLines.

    Raises ValueError (from TaxType.parse) for an unknown tax type -
    adapters translate that into their own error channel.
    """
    return [
        pricing.CostLine(
            qty1=row.get("qty1") or 0,
            qty2=row.get("qty2") or 0,
            unit_price=row.get("unit_price") or 0,
            tax_type=pricing.TaxType.parse(row.get("tax_type") or ""),
            vendor_mf_rate=rate(row.get("vendor_mf_pct")),
            markup_rate=rate(row.get("markup_pct")),
        )
        for row in rows
    ]


def breakdown_view(
    line_rows,
    package_rows,
    *,
    quote_mf_pct,
    vat_pct,
    commission_pct,
    margin_floor_pct=0,
):
    """The complete money view of a breakdown, as one dict.

    line_rows: mappings with the engine fields (qty1, qty2, unit_price,
    tax_type, vendor_mf_pct, markup_pct) plus "package" / "description"
    for client grouping. package_rows: mappings with "title" and the
    override pair (price_override + has_price_override - the flag
    carries "is this set", so an override of literally 0 đồng is a real
    free-of-charge price).

    Returns rounded whole-đồng numbers throughout:
      lines:     [{subtotal, cost_basis, input_vat, quote_price, margin}]
      packages:  [{title, default_price, price, variance, overridden}]
      subtotal, management_fee, vat, total, margin, margin_pct,
      floor_breached, and the founder block (total_commission, cm,
      profit_before_tax, tndn, net_profit, total_input_vat,
      vat_payable). Exposing or withholding the founder block is the
      caller's business - the numbers are pure arithmetic either way.
    """
    params = pricing.DealParams(
        quote_mf_rate=rate(quote_mf_pct),
        vat_rate=rate(vat_pct),
        commission_rate=rate(commission_pct),
    )
    result = pricing.compute_quote(engine_lines(line_rows), params)

    # Packages first: the chain is measured against the prices the
    # client actually reads, so those have to exist before the totals.
    budgets = {}
    for row, line in zip(line_rows, result.lines):
        if row.get("package"):
            budgets.setdefault(row["package"], []).append(line.budget)
    packages = []
    for row in package_rows:
        priced = pricing.package_price(
            budgets.get(row.get("title"), []),
            row.get("price_override") if row.get("has_price_override") else None,
        )
        packages.append(
            {
                "title": row.get("title"),
                "description": row.get("description"),
                "default_price": round_vnd(priced.default),
                "price": round_vnd(priced.price),
                "variance": round_vnd(priced.variance),
                "overridden": priced.overridden,
            }
        )

    priced_lines = [
        {**dict(row), "quote_price": round_vnd(line.budget)}
        for row, line in zip(line_rows, result.lines)
    ]
    client_prices = [
        entry["price"] for entry in quote.client_entries(packages, priced_lines)
    ]
    chain = quote.quote_chain(
        client_prices,
        cost_basis=result.total_profit_cost_basis,
        input_vat=result.total_input_vat,
        mf_rate=params.quote_mf_rate,
        vat_rate=params.vat_rate,
        commission_rate=params.commission_rate,
    )

    pct = chain.margin_fraction
    floor = rate(margin_floor_pct)
    return {
        "lines": [
            {
                "subtotal": round_vnd(line.subtotal_int_net),
                "cost_basis": round_vnd(line.profit_cost_basis),
                "input_vat": round_vnd(line.input_vat),
                "quote_price": round_vnd(line.budget),
                "margin": round_vnd(line.margin),
            }
            for line in result.lines
        ],
        "packages": packages,
        "subtotal": round_vnd(chain.subtotal),
        "management_fee": round_vnd(chain.mf_amount),
        "vat": round_vnd(chain.vat_amount),
        "total": round_vnd(chain.total),
        "margin": round_vnd(chain.margin),
        "margin_pct": float(pct * 100) if pct is not None else None,
        # A floor of 0 means "not set yet" and never warns; an empty
        # breakdown has no margin to fall anywhere.
        "floor_breached": bool(result.lines)
        and bool(floor)
        and pricing.is_floor_breached(pct, floor),
        "founder": {
            "total_commission": round_vnd(chain.total_commission),
            "cm": round_vnd(chain.cm),
            "profit_before_tax": round_vnd(chain.profit_before_tax),
            "tndn": round_vnd(chain.tndn),
            "net_profit": round_vnd(chain.net_profit),
            "total_input_vat": round_vnd(result.total_input_vat),
            "vat_payable": round_vnd(chain.vat_payable),
        },
    }

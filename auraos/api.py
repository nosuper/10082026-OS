"""Whitelisted HTTP endpoints for the frappe-ui SPA."""

import frappe
from frappe import _

from auraos.auraos.doctype.deal.deal import (
    OPERATING_ROLES,
    floor_breached,
    margin_floor_pct,
    quote_margin_pct,
    rate,
    to_engine_lines,
)
from auraos.lib import pricing
from auraos.lib.money import round_vnd


@frappe.whitelist()
def operating_users():
    """Users who may own a deal — the founder ↔ producer handover list.

    The SPA's owner dropdown needs this because Producer sessions
    cannot list the User doctype directly.
    """
    frappe.has_permission("Deal", "read", throw=True)
    holders = frappe.get_all(
        "Has Role",
        filters={
            "role": ["in", list(OPERATING_ROLES)],
            "parenttype": "User",
        },
        pluck="parent",
    )
    return frappe.get_all(
        "User",
        filters={"name": ["in", holders], "enabled": 1},
        fields=["name", "full_name"],
        order_by="full_name asc",
    )


def _is_founder():
    return "Founder" in frappe.get_roles()


def _founder_block(result, commission_pct):
    """The profit chain — assembled only for Founder sessions, never stored."""
    return {
        "commission_pct": float(commission_pct),
        "total_commission": round_vnd(result.total_commission),
        "cm": round_vnd(
            result.revenue_ex_vat
            - result.total_profit_cost_basis
            - result.total_commission
        ),
        "profit_before_tax": round_vnd(result.profit_before_tax),
        "tndn": round_vnd(result.tndn),
        "net_profit": round_vnd(result.net_profit),
        "total_input_vat": round_vnd(result.total_input_vat),
        "vat_payable": round_vnd(result.vat_payable),
        "margin_floor_pct": float(margin_floor_pct()),
    }


@frappe.whitelist()
def compute_breakdown(lines, quote_mf_pct=10, vat_pct=8, commission_pct=None, packages=None):
    """Live engine results for the breakdown editor, before anything is saved.

    Producer sessions get costs, quote prices, margin and the floor
    warning; the commission/profit block is appended only for Founder
    sessions, and a producer-supplied commission_pct is ignored.
    """
    frappe.has_permission("Deal", "read", throw=True)
    line_rows = frappe.parse_json(lines) or []
    package_rows = frappe.parse_json(packages) if packages else []

    if not _is_founder() or commission_pct is None:
        commission_pct = 5

    params = pricing.DealParams(
        quote_mf_rate=rate(quote_mf_pct),
        vat_rate=rate(vat_pct),
        commission_rate=rate(commission_pct),
    )
    result = pricing.compute_quote(to_engine_lines(line_rows), params)

    budgets = {}
    for row, line in zip(line_rows, result.lines):
        if row.get("package"):
            budgets.setdefault(row["package"], []).append(line.budget)

    pct = quote_margin_pct(result)
    out = {
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
        "packages": [
            {
                "title": row.get("title"),
                **_package_dict(
                    budgets.get(row.get("title"), []),
                    row.get("price_override") or None,
                ),
            }
            for row in package_rows
        ],
        "subtotal": round_vnd(result.subtotal),
        "management_fee": round_vnd(result.management_fee),
        "vat": round_vnd(result.vat),
        "total": round_vnd(result.total),
        "margin": round_vnd(result.revenue_ex_vat - result.total_profit_cost_basis),
        "margin_pct": float(pct * 100) if pct is not None else None,
        "floor_breached": bool(result.lines) and floor_breached(result),
    }
    if _is_founder():
        out["founder"] = _founder_block(result, commission_pct)
    return out


def _package_dict(member_budgets, override):
    priced = pricing.package_price(member_budgets, override)
    return {
        "default_price": round_vnd(priced.default),
        "price": round_vnd(priced.price),
        "variance": round_vnd(priced.variance),
        "overridden": priced.overridden,
    }


@frappe.whitelist()
def deal_profit(deal):
    """The founder-only profit chain for a saved deal, computed on demand.

    Never persisted: a producer can hold the Deal document in full and
    still see nothing of commission, CM, or the profit block.
    """
    if not _is_founder():
        frappe.throw(_("Only the Founder may see the profit chain"), frappe.PermissionError)
    doc = frappe.get_doc("Deal", deal)
    doc.check_permission("read")

    params = pricing.DealParams(
        quote_mf_rate=rate(doc.quote_mf_pct),
        vat_rate=rate(doc.vat_pct),
        commission_rate=rate(doc.commission_pct),
    )
    result = pricing.compute_quote(to_engine_lines(doc.cost_lines), params)
    return _founder_block(result, doc.commission_pct or 0)


@frappe.whitelist()
def get_margin_floor():
    frappe.has_permission("AuraOS Settings", "read", throw=True)
    return float(margin_floor_pct())


@frappe.whitelist()
def set_margin_floor(pct):
    frappe.has_permission("AuraOS Settings", "write", throw=True)
    settings = frappe.get_doc("AuraOS Settings")
    settings.margin_floor_pct = float(pct or 0)
    settings.save()
    return float(settings.margin_floor_pct)

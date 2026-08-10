import frappe
from frappe import _
from frappe.model.document import Document

from auraos.lib import pricing
from auraos.lib.money import round_vnd, to_decimal

# Only the two operating roles may own a deal; ownership is the
# explicit handover instrument between the founder and the producer.
OPERATING_ROLES = {"Founder", "Producer"}


def rate(pct):
    """A Percent field value (10 = 10%) as the engine's fractional rate."""
    return to_decimal(pct or 0) / 100


def to_engine_lines(rows):
    """Cost-line rows (child docs or plain dicts) as engine CostLines."""
    lines = []
    for row in rows:
        try:
            tax_type = pricing.TaxType.parse(row.get("tax_type") or "")
        except ValueError:
            frappe.throw(
                _("Unknown tax type: {0}").format(row.get("tax_type")),
                frappe.ValidationError,
            )
        lines.append(
            pricing.CostLine(
                qty1=row.get("qty1") or 0,
                qty2=row.get("qty2") or 0,
                unit_price=row.get("unit_price") or 0,
                tax_type=tax_type,
                vendor_mf_rate=rate(row.get("vendor_mf_pct")),
                markup_rate=rate(row.get("markup_pct")),
            )
        )
    return lines


def quote_margin_fraction(result):
    """Quote margin as a fraction of revenue; None when there is none."""
    margin = result.revenue_ex_vat - result.total_profit_cost_basis
    if not result.revenue_ex_vat:
        return None
    return margin / result.revenue_ex_vat


def margin_floor_pct():
    return frappe.db.get_single_value("AuraOS Settings", "margin_floor_pct") or 0


def floor_breached(result):
    """Whether the quote's margin falls below the global floor.

    A floor of 0 means "not set yet" and never warns; read via the db
    layer so the check works inside a Producer session that has no read
    permission on the settings doctype.
    """
    floor = margin_floor_pct()
    if not floor:
        return False
    return pricing.is_floor_breached(quote_margin_fraction(result), rate(floor))


def holds_operating_role(user):
    # Explicit role assignments only — frappe.get_roles reports every
    # role for Administrator, which would let it slip through.
    return bool(
        frappe.db.exists(
            "Has Role",
            {"parent": user, "role": ["in", list(OPERATING_ROLES)]},
        )
    )


class Deal(Document):
    def before_validate(self):
        # A deal created by an operating user belongs to them unless
        # they hand it over explicitly.
        if not self.deal_owner and holds_operating_role(frappe.session.user):
            self.deal_owner = frappe.session.user

    def validate(self):
        self.validate_owner()
        self.validate_lost_reason()
        self.validate_packages()
        self.compute_breakdown()

    def validate_owner(self):
        if self.deal_owner and not holds_operating_role(self.deal_owner):
            frappe.throw(
                _("Deal owner must hold the Founder or Producer role"),
                frappe.ValidationError,
            )

    def validate_lost_reason(self):
        if self.stage == "Lost":
            if not self.lost_reason:
                frappe.throw(
                    _("Marking a deal Lost requires a lost reason"),
                    frappe.ValidationError,
                )
        else:
            # A revived deal is no longer lost; a stale reason would
            # poison the lost-reason statistics.
            self.lost_reason = None
            self.lost_note = None

    def validate_packages(self):
        titles = [p.title for p in self.packages]
        duplicates = {t for t in titles if titles.count(t) > 1}
        if duplicates:
            frappe.throw(
                _("Duplicate package title: {0}").format(", ".join(sorted(duplicates))),
                frappe.ValidationError,
            )
        known = set(titles)
        for row in self.cost_lines:
            if row.package and row.package not in known:
                frappe.throw(
                    _("Cost line #{0} references unknown package {1}").format(
                        row.idx, row.package
                    ),
                    frappe.ValidationError,
                )

    def compute_breakdown(self):
        """Store the engine's outputs alongside the inputs (the T5 seam).

        Only producer-visible numbers are ever persisted; the founder-only
        chain (commission, CM, profit block) is computed on demand by
        auraos.api.deal_profit so it cannot leak through the list API or
        global search.
        """
        if not self.cost_lines:
            self.quote_subtotal = 0
            self.quote_mf_amount = 0
            self.quote_vat_amount = 0
            self.quote_total = 0
            self.quote_margin = 0
            self.quote_margin_pct = 0
            self.floor_breached = 0
            for package in self.packages:
                package.default_price = 0
                package.price = round_vnd(package.price_override or 0)
                package.variance = package.price
            return

        params = pricing.DealParams(
            quote_mf_rate=rate(self.quote_mf_pct),
            vat_rate=rate(self.vat_pct),
            # Commission only feeds founder-only numbers, none of which
            # are stored here; pass it anyway for completeness.
            commission_rate=rate(self.commission_pct),
        )
        result = pricing.compute_quote(to_engine_lines(self.cost_lines), params)

        for row, line in zip(self.cost_lines, result.lines):
            row.subtotal = round_vnd(line.subtotal_int_net)
            row.cost_basis = round_vnd(line.profit_cost_basis)
            row.input_vat = round_vnd(line.input_vat)
            row.quote_price = round_vnd(line.budget)
            row.margin = round_vnd(line.margin)

        self.quote_subtotal = round_vnd(result.subtotal)
        self.quote_mf_amount = round_vnd(result.management_fee)
        self.quote_vat_amount = round_vnd(result.vat)
        self.quote_total = round_vnd(result.total)
        self.quote_margin = round_vnd(
            result.revenue_ex_vat - result.total_profit_cost_basis
        )
        fraction = quote_margin_fraction(result)
        self.quote_margin_pct = float(fraction * 100) if fraction is not None else 0
        self.floor_breached = 1 if floor_breached(result) else 0

        budgets = {}
        for row, line in zip(self.cost_lines, result.lines):
            if row.package:
                budgets.setdefault(row.package, []).append(line.budget)
        for package in self.packages:
            priced = pricing.package_price(
                budgets.get(package.title, []), package.price_override or None
            )
            package.default_price = round_vnd(priced.default)
            package.price = round_vnd(priced.price)
            package.variance = round_vnd(priced.variance)

    def before_save(self):
        # After validation, so a rejected transition is never logged.
        previous = self.get_doc_before_save()
        from_stage = previous.stage if previous else None
        if self.is_new() or from_stage != self.stage:
            self.append(
                "stage_history",
                {
                    "from_stage": from_stage,
                    "to_stage": self.stage,
                    "changed_on": frappe.utils.now_datetime(),
                    "changed_by": frappe.session.user,
                },
            )

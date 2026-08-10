import frappe
from frappe import _
from frappe.model.document import Document

from auraos.lib import pricing, quote
from auraos.lib.money import round_vnd, to_decimal

# Only the two operating roles may own a deal; ownership is the
# explicit handover instrument between the founder and the producer.
OPERATING_ROLES = {"Founder", "Producer"}


def check_attachment_permission(doc, method=None):
    """doc_events hook on File: attaching to a Deal requires write
    permission on that deal.

    Core File permissions let any System User create files, so without
    this gate a role-less user could hang attachments on deals they
    cannot even read.
    """
    if doc.flags.ignore_permissions:
        return
    if doc.attached_to_doctype == "Deal":
        frappe.has_permission(
            "Deal", "write", doc=doc.attached_to_name, throw=True
        )


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


def client_prices(packages, lines):
    """The prices the client is shown, as plain numbers.

    Revenue is measured against these — not the engine's line total —
    because a rounded-up package is what the client actually pays
    (issue #32). Rows may be child docs or plain dicts.
    """
    return [
        entry["price"]
        for entry in quote.client_entries(
            [as_dict(package) for package in packages],
            [as_dict(line) for line in lines],
        )
    ]


def as_dict(row):
    return row if isinstance(row, dict) else row.as_dict()


def deal_chain(doc, result):
    """The client-facing chain for a deal, given its engine result."""
    return quote.quote_chain(
        client_prices(doc.packages, doc.cost_lines),
        cost_basis=result.total_profit_cost_basis,
        input_vat=result.total_input_vat,
        mf_rate=rate(doc.quote_mf_pct),
        vat_rate=rate(doc.vat_pct),
        commission_rate=rate(doc.commission_pct),
    )


def margin_floor_pct():
    return frappe.db.get_single_value("AuraOS Settings", "margin_floor_pct") or 0


def floor_breached(margin_fraction):
    """Whether the quote's margin falls below the global floor.

    A floor of 0 means "not set yet" and never warns; read via the db
    layer so the check works inside a Producer session that has no read
    permission on the settings doctype.
    """
    floor = margin_floor_pct()
    if not floor:
        return False
    return pricing.is_floor_breached(margin_fraction, rate(floor))


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
        """Store the engine's producer-visible outputs (the T5 seam).

        The founder-only chain is persisted separately by
        store_founder_chain (permlevel-1 fields, written post-save) —
        see that method for why it cannot happen here.
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

        # Packages first: the quote totals are measured against their
        # prices, so they have to exist before the totals are computed.
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

        chain = deal_chain(self, result)
        self.quote_subtotal = round_vnd(chain.subtotal)
        self.quote_mf_amount = round_vnd(chain.mf_amount)
        self.quote_vat_amount = round_vnd(chain.vat_amount)
        self.quote_total = round_vnd(chain.total)
        self.quote_margin = round_vnd(chain.margin)
        self.quote_margin_pct = (
            float(chain.margin_fraction * 100)
            if chain.margin_fraction is not None
            else 0
        )
        self.floor_breached = 1 if floor_breached(chain.margin_fraction) else 0

    def on_update(self):
        self.store_founder_chain()

    def store_founder_chain(self):
        """Persist the founder-only profit chain (for future dashboards).

        Written with db_set after the save, not in validate: a producer's
        save must refresh these numbers too, but Frappe resets any
        permlevel-1 value a producer session touches back to its stale
        database copy during validation (validate_higher_perm_levels), so
        controller-computed values set there would be thrown away. By
        on_update the reset has already run — self.commission_pct holds
        the database truth — and db_set writes regardless of the session's
        field-level permissions. Reads stay founder-only via permlevel 1.
        """
        if not self.cost_lines:
            values = {
                "total_commission": 0,
                "cm": 0,
                "profit_before_tax": 0,
                "tndn": 0,
                "net_profit": 0,
                "vat_payable": 0,
            }
        else:
            params = pricing.DealParams(
                quote_mf_rate=rate(self.quote_mf_pct),
                vat_rate=rate(self.vat_pct),
                commission_rate=rate(self.commission_pct),
            )
            result = pricing.compute_quote(to_engine_lines(self.cost_lines), params)
            # Same client-facing revenue the producer sees on the quote,
            # so commission and tax are taken on what we actually charge.
            chain = deal_chain(self, result)
            values = {
                "total_commission": round_vnd(chain.total_commission),
                "cm": round_vnd(chain.cm),
                "profit_before_tax": round_vnd(chain.profit_before_tax),
                "tndn": round_vnd(chain.tndn),
                "net_profit": round_vnd(chain.net_profit),
                "vat_payable": round_vnd(chain.vat_payable),
            }
        self.db_set(values, update_modified=False)

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

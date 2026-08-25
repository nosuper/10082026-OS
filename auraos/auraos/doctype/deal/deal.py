import frappe
from frappe import _
from frappe.model.document import Document

from auraos.lib import breakdown, pricing
from auraos.lib.breakdown import rate
from auraos.lib.money import round_vnd

# Only the two operating roles may own a deal; ownership is the
# explicit handover instrument between the founder and the producer.
OPERATING_ROLES = {"Founder", "Producer"}


def as_dict(row):
    return row if isinstance(row, dict) else row.as_dict()


def margin_floor_pct():
    return frappe.db.get_single_value("AuraOS Settings", "margin_floor_pct") or 0


# The playbook's opening suggestion (§2.2), until the founder stores
# their own numbers in Settings. Read through auraos.settings.setting so
# an unset field falls back here rather than reading as a 0 threshold
# that would make every deal Tier 3.
DEFAULT_TIER2_THRESHOLD = 50_000_000
DEFAULT_TIER3_THRESHOLD = 200_000_000


def tier2_threshold():
    from auraos.settings import setting

    return setting("tier2_threshold", None) or DEFAULT_TIER2_THRESHOLD


def tier3_threshold():
    from auraos.settings import setting

    return setting("tier3_threshold", None) or DEFAULT_TIER3_THRESHOLD


def derive_tier(estimated_budget=0, project_type=None, positioning=None):
    """The tier the playbook's rules (§2.2) assign to a deal.

    Positioning is the input, tier is the output: Brand work - or a job
    type flagged as the positioning segment - is Tier 3 whatever it
    pays; everything else follows the two budget thresholds. No budget
    and no positioning signal means no tier yet.
    """
    if positioning == "Brand":
        return "Tier 3"
    if project_type and frappe.db.get_value(
        "Project Type", project_type, "is_positioning"
    ):
        return "Tier 3"
    budget = estimated_budget or 0
    if not budget:
        return None
    if budget >= tier3_threshold():
        return "Tier 3"
    if budget >= tier2_threshold():
        return "Tier 2"
    return "Tier 1"


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


def append_stage_change(doc):
    """Log a stage move on a doc carrying a `stage_history` table.

    Shared by Deal and Job - both move through a fixed stage list and
    both answer "who moved this, and when" from the same child table.
    Call from before_save, after validation, so a rejected transition is
    never logged.
    """
    previous = doc.get_doc_before_save()
    from_stage = previous.stage if previous else None
    if doc.is_new() or from_stage != doc.stage:
        doc.append(
            "stage_history",
            {
                "from_stage": from_stage,
                "to_stage": doc.stage,
                "changed_on": frappe.utils.now_datetime(),
                "changed_by": frappe.session.user,
            },
        )


def holds_operating_role(user):
    # Explicit role assignments only - frappe.get_roles reports every
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
        self.apply_tier()
        self.compute_breakdown()

    def apply_tier(self):
        """Keep the tier derived unless someone pinned it by hand.

        One strategic question - positioning - plus the budget decides
        the tier (derive_tier), so it tracks the deal as those change.
        Writing the tier directly pins it (tier_is_manual) and the rules
        leave it alone; clearing it hands it back to the rules.
        """
        previous = self.get_doc_before_save()
        stored_tier = previous.tier if previous else None
        if (self.tier or None) != (stored_tier or None):
            self.tier_is_manual = 1 if self.tier else 0
        if self.tier_is_manual:
            return
        self.tier = derive_tier(
            self.estimated_budget, self.project_type, self.positioning
        )

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

    def breakdown_view(self):
        """The one money view of this deal's breakdown (lib/breakdown).

        Adapter duties only: child rows become plain mappings, the
        stored floor joins the params, and the lib's ValueError comes
        back out as a validation error.
        """
        try:
            return breakdown.breakdown_view(
                [as_dict(row) for row in self.cost_lines],
                [as_dict(package) for package in self.packages],
                quote_mf_pct=self.quote_mf_pct,
                vat_pct=self.vat_pct,
                # Unset on every deal quoted before #69, and Frappe does
                # not backfill a new field's default onto existing rows -
                # so those recompute to the figures they were sold at
                # rather than jumping 10% the next time anyone saves them.
                contingency_pct=self.contingency_pct,
                # Commission only feeds the founder block; whether that
                # block is exposed is each caller's business.
                commission_pct=self.commission_pct,
                margin_floor_pct=margin_floor_pct(),
            )
        except ValueError as err:
            frappe.throw(_(str(err)), frappe.ValidationError)

    def compute_breakdown(self):
        """Store the engine's producer-visible outputs (the T5 seam).

        The founder-only chain is persisted separately by
        store_founder_chain (permlevel-1 fields, written post-save) -
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
                package.price = round_vnd(
                    package.price_override if package.has_price_override else 0
                )
                package.variance = package.price
            return

        view = self.breakdown_view()
        for row, line in zip(self.cost_lines, view["lines"]):
            row.subtotal = line["subtotal"]
            row.cost_basis = line["cost_basis"]
            row.input_vat = line["input_vat"]
            row.quote_price = line["quote_price"]
            row.margin = line["margin"]
        for package, priced in zip(self.packages, view["packages"]):
            package.default_price = priced["default_price"]
            package.price = priced["price"]
            package.variance = priced["variance"]
        self.quote_subtotal = view["subtotal"]
        self.quote_mf_amount = view["management_fee"]
        self.quote_vat_amount = view["vat"]
        self.quote_total = view["total"]
        self.quote_margin = view["margin"]
        self.quote_margin_pct = view["margin_pct"] or 0
        self.floor_breached = 1 if view["floor_breached"] else 0

    def on_update(self):
        self.store_founder_chain()

    def store_founder_chain(self):
        """Persist the founder-only profit chain (for future dashboards).

        Written with db_set after the save, not in validate: a producer's
        save must refresh these numbers too, but Frappe resets any
        permlevel-1 value a producer session touches back to its stale
        database copy during validation (validate_higher_perm_levels), so
        controller-computed values set there would be thrown away. By
        on_update the reset has already run - self.commission_pct holds
        the database truth - and db_set writes regardless of the session's
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
            # Same client-facing revenue the producer sees on the quote,
            # so commission and tax are taken on what we actually charge.
            founder = self.breakdown_view()["founder"]
            values = {
                field: founder[field]
                for field in (
                    "total_commission",
                    "cm",
                    "profit_before_tax",
                    "tndn",
                    "net_profit",
                    "vat_payable",
                )
            }
        self.db_set(values, update_modified=False)

    def before_save(self):
        # After validation, so a rejected transition is never logged.
        append_stage_change(self)

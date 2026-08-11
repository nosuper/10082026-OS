"""Seam and permission tests for T5 (issue #7): breakdown & quote editor.

Seam: a persisted breakdown's stored computed values must agree with the
pricing engine's outputs for the same inputs — the engine itself is the
oracle, so no number here is hand-computed.

Permissions: commission (CMF), CM and the profit chain are founder-only
through every access path, and the global margin floor is founder-editable
only, while its warning stays visible to the producer.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import (
    compute_breakdown,
    deal_profit,
    get_margin_floor,
    set_margin_floor,
)
from auraos.auraos.doctype.deal.test_deal import make_company
from auraos.lib import pricing
from auraos.lib.money import round_vnd
from auraos.tests.utils import make_test_user

FOUNDER = "founder@test.auraos.local"
PRODUCER = "producer@test.auraos.local"

# One line per offered tax type (Cty 10% exists in the engine for xlsx
# parity but is not offered on deals — T5 walkthrough decision), with
# vendor MF and markup in play.
LINES = [
    {
        "description": "Đạo diễn",
        "qty1": 1,
        "qty1_unit": "người",
        "qty2": 3,
        "qty2_unit": "ngày",
        "unit_price": 5_000_000,
        "tax_type": "Cá nhân",
        "markup_pct": 20,
    },
    {
        "description": "Thuê thiết bị",
        "qty1": 2,
        "qty2": 3,
        "unit_price": 8_000_000,
        "tax_type": "Công ty",
        "vendor_mf_pct": 5,
        "markup_pct": 10,
    },
    {
        "description": "Studio",
        "qty1": 1,
        "qty2": 1,
        "unit_price": 12_000_000,
        "tax_type": "Công ty",
        "markup_pct": 15,
    },
    {
        "description": "Ăn uống đoàn",
        "qty1": 10,
        "qty2": 3,
        "unit_price": 150_000,
        "tax_type": "Không hoá đơn",
    },
]


def engine_result(deal):
    """Run the deal's persisted inputs through the engine directly."""
    params = pricing.DealParams(
        quote_mf_rate=frappe.utils.flt(deal.quote_mf_pct) / 100,
        vat_rate=frappe.utils.flt(deal.vat_pct) / 100,
        commission_rate=frappe.utils.flt(deal.commission_pct) / 100,
    )
    lines = [
        pricing.CostLine(
            qty1=row.qty1,
            qty2=row.qty2,
            unit_price=row.unit_price,
            tax_type=pricing.TaxType.parse(row.tax_type),
            vendor_mf_rate=frappe.utils.flt(row.vendor_mf_pct) / 100,
            markup_rate=frappe.utils.flt(row.markup_pct) / 100,
        )
        for row in deal.cost_lines
    ]
    return pricing.compute_quote(lines, params)


def make_breakdown_deal(**overrides):
    doc = frappe.get_doc(
        {
            "doctype": "Deal",
            "title": "TVC với breakdown",
            "deal_owner": FOUNDER,
            "company": make_company().name,
            "cost_lines": overrides.pop("cost_lines", [dict(row) for row in LINES]),
            **overrides,
        }
    )
    doc.insert()
    return doc


class TestDealBreakdown(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")

    def setUp(self):
        frappe.set_user("Administrator")
        frappe.db.set_single_value("AuraOS Settings", "margin_floor_pct", 0)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.set_single_value("AuraOS Settings", "margin_floor_pct", 0)
        super().tearDown()

    def assertAgreesWithEngine(self, actual, expected):
        """Quote-level money, compared to the engine within rounding dust.

        Since T6 (issue #32) revenue is measured against the prices the
        client is shown — each entry rounded to the đồng, then summed —
        while the engine sums unrounded line budgets. With no package
        override the two say the same thing, but they can differ by up
        to a đồng per line. Per-line values below stay exact.
        """
        self.assertAlmostEqual(actual, expected, delta=len(LINES))

    # -- the seam: stored computed values agree with the engine --

    def test_stored_line_values_agree_with_engine(self):
        deal = frappe.get_doc("Deal", make_breakdown_deal().name)
        result = engine_result(deal)
        for row, line in zip(deal.cost_lines, result.lines):
            self.assertEqual(row.subtotal, round_vnd(line.subtotal_int_net))
            self.assertEqual(row.cost_basis, round_vnd(line.profit_cost_basis))
            self.assertEqual(row.input_vat, round_vnd(line.input_vat))
            self.assertEqual(row.quote_price, round_vnd(line.budget))
            self.assertEqual(row.margin, round_vnd(line.margin))

    def test_stored_quote_totals_agree_with_engine(self):
        deal = frappe.get_doc("Deal", make_breakdown_deal().name)
        result = engine_result(deal)
        self.assertAgreesWithEngine(deal.quote_subtotal, round_vnd(result.subtotal))
        self.assertAgreesWithEngine(
            deal.quote_mf_amount, round_vnd(result.management_fee)
        )
        self.assertAgreesWithEngine(deal.quote_vat_amount, round_vnd(result.vat))
        self.assertAgreesWithEngine(deal.quote_total, round_vnd(result.total))
        margin = result.revenue_ex_vat - result.total_profit_cost_basis
        self.assertAgreesWithEngine(deal.quote_margin, round_vnd(margin))
        self.assertAlmostEqual(
            deal.quote_margin_pct,
            float(margin / result.revenue_ex_vat * 100),
            places=3,
        )

    def test_editing_a_line_recomputes_stored_values(self):
        deal = make_breakdown_deal()
        deal.cost_lines[1].unit_price = 9_500_000
        deal.cost_lines[1].markup_pct = 25
        deal.save()
        reloaded = frappe.get_doc("Deal", deal.name)
        result = engine_result(reloaded)
        self.assertEqual(
            reloaded.cost_lines[1].quote_price, round_vnd(result.lines[1].budget)
        )
        self.assertAgreesWithEngine(reloaded.quote_total, round_vnd(result.total))

    def test_cost_line_metadata_is_persisted_untouched(self):
        category = frappe.get_doc(
            {"doctype": "Cost Item Category", "category_name": "Crew"}
        ).insert()
        contact = frappe.get_doc(
            {
                "doctype": "Party Contact",
                "full_name": "Nguyễn Quay Phim",
                "phone": "0907654321",
            }
        ).insert()
        lines = [dict(row) for row in LINES]
        lines[0].update(
            {
                "item_category": category.name,
                "cost_phase": "Pre-production",
                "source_type": "Freelancer",
                "source_contact": contact.name,
            }
        )

        stored = make_breakdown_deal(cost_lines=lines).cost_lines[0]

        self.assertEqual(stored.item_category, "Crew")
        self.assertEqual(stored.cost_phase, "Pre-production")
        self.assertEqual(stored.source_type, "Freelancer")
        self.assertEqual(stored.source_contact, contact.name)

    def test_producer_can_extend_the_item_category_vocabulary(self):
        frappe.set_user(PRODUCER)

        category = frappe.get_doc(
            {"doctype": "Cost Item Category", "category_name": "Location"}
        ).insert()

        self.assertEqual(category.name, "Location")

    def test_new_internal_line_defaults_to_no_invoice_tax(self):
        deal = make_breakdown_deal(
            cost_lines=[
                {
                    "description": "In-house producer",
                    "qty1": 1,
                    "qty2": 1,
                    "unit_price": 1_000_000,
                }
            ]
        )

        self.assertEqual(deal.cost_lines[0].source_type, "Internal")
        self.assertEqual(deal.cost_lines[0].tax_type, "Không hoá đơn")

    def test_line_order_is_persisted(self):
        deal = make_breakdown_deal()
        reordered = [deal.cost_lines[2], deal.cost_lines[0], deal.cost_lines[1], deal.cost_lines[3]]
        deal.cost_lines = []
        for row in reordered:
            deal.append("cost_lines", row.as_dict(no_default_fields=True))
        deal.save()
        stored = [row.description for row in frappe.get_doc("Deal", deal.name).cost_lines]
        self.assertEqual(stored, ["Studio", "Đạo diễn", "Thuê thiết bị", "Ăn uống đoàn"])

    def test_empty_breakdown_stores_zero_totals(self):
        deal = make_breakdown_deal(cost_lines=[])
        self.assertEqual(deal.quote_total, 0)
        self.assertEqual(deal.quote_margin, 0)
        self.assertFalse(deal.floor_breached)

    def test_unknown_tax_type_is_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            make_breakdown_deal(
                cost_lines=[
                    {
                        "description": "Sai thuế",
                        "qty1": 1,
                        "qty2": 1,
                        "unit_price": 1_000_000,
                        "tax_type": "Tiền mặt",
                    }
                ]
            )

    # -- packages --

    def package_lines(self):
        lines = [dict(row) for row in LINES]
        lines[0]["package"] = "Human resources"
        lines[1]["package"] = "Equipment"
        lines[2]["package"] = "Equipment"
        return lines

    def test_package_price_defaults_to_member_sum(self):
        deal = make_breakdown_deal(
            cost_lines=self.package_lines(),
            packages=[
                {"title": "Human resources", "description": "Crew & talent"},
                {"title": "Equipment", "description": "Gear & studio"},
            ],
        )
        result = engine_result(deal)
        by_title = {p.title: p for p in deal.packages}
        hr_sum = round_vnd(result.lines[0].budget)
        eq_sum = round_vnd(result.lines[1].budget + result.lines[2].budget)
        self.assertEqual(by_title["Human resources"].default_price, hr_sum)
        self.assertEqual(by_title["Human resources"].price, hr_sum)
        self.assertEqual(by_title["Human resources"].variance, 0)
        self.assertEqual(by_title["Equipment"].price, eq_sum)

    def test_package_override_stores_variance(self):
        deal = make_breakdown_deal(
            cost_lines=self.package_lines(),
            packages=[
                {"title": "Human resources"},
                {"title": "Equipment", "price_override": 70_000_000},
            ],
        )
        equipment = {p.title: p for p in deal.packages}["Equipment"]
        self.assertEqual(equipment.price, 70_000_000)
        self.assertEqual(
            equipment.variance, 70_000_000 - equipment.default_price
        )
        self.assertNotEqual(equipment.variance, 0)

    def test_duplicate_package_titles_are_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            make_breakdown_deal(
                packages=[{"title": "Equipment"}, {"title": "Equipment"}]
            )

    def test_line_referencing_unknown_package_is_rejected(self):
        lines = [dict(row) for row in LINES]
        lines[0]["package"] = "Ghost package"
        with self.assertRaises(frappe.ValidationError):
            make_breakdown_deal(cost_lines=lines)

    # -- margin floor --

    def test_floor_breach_is_stored_and_visible_to_producer(self):
        frappe.set_user(FOUNDER)
        set_margin_floor(95)  # far above any sane margin
        frappe.set_user("Administrator")
        deal = make_breakdown_deal()
        self.assertTrue(deal.floor_breached)

        from frappe.client import get

        frappe.set_user(PRODUCER)
        fetched = get("Deal", name=deal.name)
        self.assertTrue(fetched.floor_breached)
        self.assertTrue(fetched.quote_margin)

    def test_floor_not_breached_when_margin_clears_it(self):
        frappe.set_user(FOUNDER)
        set_margin_floor(1)
        frappe.set_user("Administrator")
        deal = make_breakdown_deal()
        self.assertFalse(deal.floor_breached)

    def test_floor_of_zero_never_warns(self):
        deal = make_breakdown_deal()
        self.assertFalse(deal.floor_breached)

    def test_founder_can_set_and_read_floor(self):
        frappe.set_user(FOUNDER)
        self.assertEqual(set_margin_floor(32.5), 32.5)
        self.assertEqual(get_margin_floor(), 32.5)

    def test_producer_cannot_set_floor(self):
        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            set_margin_floor(1)

    def test_producer_cannot_read_floor(self):
        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            get_margin_floor()
        with self.assertRaises(frappe.PermissionError):
            from frappe.client import get

            get("AuraOS Settings")

    # -- founder-only: commission, CM, profit chain --

    def test_deal_profit_agrees_with_engine_for_founder(self):
        deal = make_breakdown_deal(commission_pct=5)
        result = engine_result(deal)
        frappe.set_user(FOUNDER)
        block = deal_profit(deal.name)
        self.assertAgreesWithEngine(
            block["total_commission"], round_vnd(result.total_commission)
        )
        self.assertAgreesWithEngine(
            block["profit_before_tax"], round_vnd(result.profit_before_tax)
        )
        self.assertAgreesWithEngine(block["tndn"], round_vnd(result.tndn))
        self.assertAgreesWithEngine(block["net_profit"], round_vnd(result.net_profit))
        self.assertAgreesWithEngine(block["vat_payable"], round_vnd(result.vat_payable))
        self.assertAgreesWithEngine(
            block["cm"],
            round_vnd(
                result.revenue_ex_vat
                - result.total_profit_cost_basis
                - result.total_commission
            ),
        )

    def test_founder_chain_is_stored_and_agrees_with_engine(self):
        deal = frappe.get_doc(
            "Deal", make_breakdown_deal(commission_pct=5).name
        )
        result = engine_result(deal)
        self.assertAgreesWithEngine(
            deal.total_commission, round_vnd(result.total_commission)
        )
        self.assertAgreesWithEngine(
            deal.profit_before_tax, round_vnd(result.profit_before_tax)
        )
        self.assertAgreesWithEngine(deal.tndn, round_vnd(result.tndn))
        self.assertAgreesWithEngine(deal.net_profit, round_vnd(result.net_profit))
        self.assertAgreesWithEngine(deal.vat_payable, round_vnd(result.vat_payable))
        self.assertAgreesWithEngine(
            deal.cm,
            round_vnd(
                result.revenue_ex_vat
                - result.total_profit_cost_basis
                - result.total_commission
            ),
        )

    def test_producer_save_refreshes_stored_founder_chain(self):
        # The dashboard numbers must track every edit, including edits a
        # producer makes — while the commission itself stays theirs to
        # neither see nor change.
        deal = make_breakdown_deal(commission_pct=7)
        frappe.set_user(PRODUCER)
        copy = frappe.get_doc("Deal", deal.name)
        copy.cost_lines[0].markup_pct = 40
        copy.save()
        frappe.set_user("Administrator")
        reloaded = frappe.get_doc("Deal", deal.name)
        self.assertEqual(reloaded.commission_pct, 7)
        result = engine_result(reloaded)
        self.assertAgreesWithEngine(
            reloaded.total_commission, round_vnd(result.total_commission)
        )
        self.assertAgreesWithEngine(reloaded.net_profit, round_vnd(result.net_profit))

    def test_producer_cannot_read_stored_profit_fields(self):
        deal = make_breakdown_deal(commission_pct=7)
        from frappe.client import get

        frappe.set_user(PRODUCER)
        fetched = get("Deal", name=deal.name)
        for field in (
            "total_commission",
            "cm",
            "profit_before_tax",
            "tndn",
            "net_profit",
            "vat_payable",
        ):
            self.assertFalse(
                fetched.get(field),
                f"PERMISSION LEAK: producer read {field} via the document API",
            )

    def test_deal_profit_denied_to_producer(self):
        deal = make_breakdown_deal()
        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            deal_profit(deal.name)

    def test_producer_cannot_read_commission_via_document_api(self):
        deal = make_breakdown_deal(commission_pct=7)
        from frappe.client import get

        frappe.set_user(PRODUCER)
        fetched = get("Deal", name=deal.name)
        # Frappe masks unreadable permlevel fields to None/0 rather than
        # dropping the key; the property that matters is that the stored
        # value never comes through.
        self.assertFalse(fetched.get("commission_pct"))

    def test_producer_cannot_read_commission_via_list_api(self):
        make_breakdown_deal(commission_pct=7)
        from frappe.client import get_list

        frappe.set_user(PRODUCER)
        try:
            rows = get_list("Deal", fields=["name", "commission_pct"])
        except frappe.PermissionError:
            return  # refusing outright is fine too
        self.assertTrue(rows)
        self.assertTrue(
            all(row.get("commission_pct") is None for row in rows),
            "PERMISSION LEAK: producer read commission_pct via the list API",
        )

    def test_no_sensitive_deal_field_is_in_global_search(self):
        # Global search indexes whole fields; the founder-only ones must
        # never be indexed at all.
        meta = frappe.get_meta("Deal")
        leaked = [
            df.fieldname
            for df in meta.fields
            if df.permlevel and df.get("in_global_search")
        ]
        self.assertEqual(leaked, [])

    def test_commission_never_reaches_the_search_index(self):
        # Behavioral counterpart to the meta assertion, in the spike-note
        # pattern: index a deal with a distinctive title and an unusual
        # commission, then check what the search content actually holds.
        from frappe.desk.doctype.global_search_settings.global_search_settings import (
            update_global_search_doctypes,
        )
        from frappe.utils import global_search

        # Register hook-declared doctypes in Global Search Settings —
        # normally done by migrate, which CI's fresh site never runs.
        update_global_search_doctypes()

        marker = "hoahongbimat8823"
        make_breakdown_deal(title=f"Deal {marker}", commission_pct=41.77)
        global_search.sync_global_search()

        frappe.set_user(PRODUCER)
        results = [
            r for r in global_search.search(marker) if r.get("doctype") == "Deal"
        ]
        self.assertTrue(
            results,
            "positive control failed: the deal should be findable by title",
        )
        for row in results:
            self.assertNotIn(
                "41.77",
                row.get("content") or "",
                "PERMISSION LEAK: commission value found in global search content",
            )

    def test_producer_save_cannot_change_commission(self):
        deal = make_breakdown_deal(commission_pct=7)
        frappe.set_user(PRODUCER)
        producer_copy = frappe.get_doc("Deal", deal.name)
        producer_copy.commission_pct = 0
        producer_copy.cost_lines[0].markup_pct = 30
        producer_copy.save()
        frappe.set_user("Administrator")
        reloaded = frappe.get_doc("Deal", deal.name)
        self.assertEqual(reloaded.commission_pct, 7)
        self.assertEqual(reloaded.cost_lines[0].markup_pct, 30)

    # -- the live compute endpoint --

    def test_compute_breakdown_matches_saved_deal_for_producer(self):
        deal = make_breakdown_deal()
        frappe.set_user(PRODUCER)
        out = compute_breakdown(lines=[dict(row) for row in LINES])
        self.assertEqual(out["subtotal"], deal.quote_subtotal)
        self.assertEqual(out["total"], deal.quote_total)
        self.assertEqual(out["margin"], deal.quote_margin)
        self.assertEqual(
            [line["quote_price"] for line in out["lines"]],
            [row.quote_price for row in deal.cost_lines],
        )

    def test_compute_breakdown_returns_line_metadata_untouched(self):
        lines = [dict(row) for row in LINES]
        metadata = {
            "item_category": "Crew",
            "cost_phase": "Appendix",
            "source_type": "Internal",
            "source_contact": "internal@example.com",
        }
        lines[0].update(metadata)

        out = compute_breakdown(lines=lines)

        self.assertEqual(
            {key: out["lines"][0][key] for key in metadata},
            metadata,
        )

    def test_compute_breakdown_hides_founder_block_from_producer(self):
        frappe.set_user(PRODUCER)
        out = compute_breakdown(
            lines=[dict(row) for row in LINES], commission_pct=50
        )
        self.assertNotIn("founder", out)

    def test_compute_breakdown_gives_founder_the_profit_chain(self):
        frappe.set_user(FOUNDER)
        out = compute_breakdown(lines=[dict(row) for row in LINES])
        self.assertIn("founder", out)
        founder = out["founder"]
        for key in (
            "total_commission",
            "cm",
            "profit_before_tax",
            "tndn",
            "net_profit",
            "vat_payable",
        ):
            self.assertIn(key, founder)

    def test_compute_breakdown_reports_package_variance(self):
        frappe.set_user(PRODUCER)
        lines = self.package_lines()
        out = compute_breakdown(
            lines=lines,
            packages=[
                {"title": "Human resources"},
                {"title": "Equipment", "price_override": 70_000_000},
            ],
        )
        by_title = {p["title"]: p for p in out["packages"]}
        hr = by_title["Human resources"]
        self.assertEqual(hr["price"], hr["default_price"])
        self.assertFalse(hr["overridden"])
        equipment = by_title["Equipment"]
        self.assertEqual(equipment["price"], 70_000_000)
        self.assertTrue(equipment["overridden"])
        self.assertEqual(
            equipment["variance"], 70_000_000 - equipment["default_price"]
        )

    def test_compute_breakdown_reports_floor_breach(self):
        frappe.set_user(FOUNDER)
        set_margin_floor(95)
        frappe.set_user(PRODUCER)
        out = compute_breakdown(lines=[dict(row) for row in LINES])
        self.assertTrue(out["floor_breached"])

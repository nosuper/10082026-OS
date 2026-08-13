"""Seam tests for T3 (issue #5): deal pipeline - stage transitions,
lost-reason enforcement, ownership, and stage history.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.tests.utils import make_test_user

FOUNDER = "founder@test.auraos.local"
PRODUCER = "producer@test.auraos.local"
# A System User with neither app role - the negative control.
OUTSIDER = "outsider@test.auraos.local"

STAGES = [
    "Brief Received",
    "De-brief",
    "Breakdown",
    "Quote Sent",
    "Negotiation",
    "Won",
    "Lost",
]

LOST_REASONS = ["Price", "Timing", "Silence", "Competitor", "Scope"]


def make_company(company_name="Chungify Media"):
    existing = frappe.db.exists("Party Company", {"company_name": company_name})
    if existing:
        return frappe.get_doc("Party Company", existing)
    return frappe.get_doc(
        {"doctype": "Party Company", "company_name": company_name}
    ).insert()


def make_deal(**overrides):
    overrides.setdefault("company", make_company().name)
    doc = frappe.get_doc(
        {
            "doctype": "Deal",
            "title": "TVC cho Chungify",
            "deal_owner": FOUNDER,
            **overrides,
        }
    )
    doc.insert()
    return doc


class TestDeal(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    # -- required fields & defaults --

    def test_deal_requires_title(self):
        with self.assertRaises(frappe.MandatoryError):
            frappe.get_doc(
                {"doctype": "Deal", "deal_owner": FOUNDER}
            ).insert()

    def test_deal_requires_company(self):
        # T3 walkthrough decision: every deal names its client company.
        with self.assertRaises(frappe.MandatoryError):
            frappe.get_doc(
                {
                    "doctype": "Deal",
                    "title": "No client",
                    "deal_owner": FOUNDER,
                }
            ).insert()

    def test_new_deal_starts_at_brief_received(self):
        deal = make_deal()
        self.assertEqual(deal.stage, "Brief Received")

    def test_deal_links_company_contact_and_brief(self):
        company = make_company()
        contact = frappe.get_doc(
            {
                "doctype": "Party Contact",
                "full_name": "Nguyễn Văn A",
                "phone": "0901234567",
                "company": company.name,
            }
        ).insert()
        deal = make_deal(
            company=company.name,
            contact=contact.name,
            brief="30s TVC, quay 2 ngày, deadline cuối tháng",
        )
        reloaded = frappe.get_doc("Deal", deal.name)
        self.assertEqual(reloaded.company, company.name)
        self.assertEqual(reloaded.contact, contact.name)
        self.assertIn("TVC", reloaded.brief)

    # -- stage transitions & history --

    def test_stage_moves_forward_through_pipeline(self):
        deal = make_deal()
        for stage in STAGES[1:-2]:  # up to Negotiation
            deal.stage = stage
            deal.save()
        self.assertEqual(
            frappe.get_doc("Deal", deal.name).stage, "Negotiation"
        )

    def test_invalid_stage_is_rejected(self):
        deal = make_deal()
        deal.stage = "Daydreaming"
        with self.assertRaises(frappe.ValidationError):
            deal.save()

    def test_insert_logs_initial_stage(self):
        deal = frappe.get_doc("Deal", make_deal().name)
        self.assertEqual(len(deal.stage_history), 1)
        entry = deal.stage_history[0]
        self.assertFalse(entry.from_stage)
        self.assertEqual(entry.to_stage, "Brief Received")
        self.assertTrue(entry.changed_on)
        self.assertEqual(entry.changed_by, "Administrator")

    def test_stage_change_appends_history_with_timestamp(self):
        deal = make_deal()
        deal.stage = "De-brief"
        deal.save()
        deal.stage = "Breakdown"
        deal.save()
        history = frappe.get_doc("Deal", deal.name).stage_history
        self.assertEqual(
            [(h.from_stage or "", h.to_stage) for h in history],
            [
                ("", "Brief Received"),
                ("Brief Received", "De-brief"),
                ("De-brief", "Breakdown"),
            ],
        )
        self.assertTrue(all(h.changed_on for h in history))

    def test_saving_without_stage_change_adds_no_history(self):
        deal = make_deal()
        deal.brief = "updated brief"
        deal.save()
        self.assertEqual(
            len(frappe.get_doc("Deal", deal.name).stage_history), 1
        )

    # -- lost-reason enforcement --

    def test_lost_without_reason_is_rejected(self):
        deal = make_deal()
        deal.stage = "Lost"
        with self.assertRaises(frappe.ValidationError):
            deal.save()

    def test_lost_with_reason_and_note_is_stored(self):
        deal = make_deal()
        deal.stage = "Lost"
        deal.lost_reason = "Silence"
        deal.lost_note = "Quote sent, đọc không rep"
        deal.save()
        reloaded = frappe.get_doc("Deal", deal.name)
        self.assertEqual(reloaded.stage, "Lost")
        self.assertEqual(reloaded.lost_reason, "Silence")
        self.assertEqual(reloaded.lost_note, "Quote sent, đọc không rep")

    def test_every_agreed_lost_reason_is_accepted(self):
        for reason in LOST_REASONS:
            deal = make_deal(title=f"Lost to {reason}")
            deal.stage = "Lost"
            deal.lost_reason = reason
            deal.save()

    def test_unknown_lost_reason_is_rejected(self):
        deal = make_deal()
        deal.stage = "Lost"
        deal.lost_reason = "Bad luck"
        with self.assertRaises(frappe.ValidationError):
            deal.save()

    def test_reviving_a_lost_deal_clears_reason_and_note(self):
        deal = make_deal()
        deal.stage = "Lost"
        deal.lost_reason = "Price"
        deal.lost_note = "quá chát"
        deal.save()
        deal.stage = "Negotiation"
        deal.save()
        reloaded = frappe.get_doc("Deal", deal.name)
        self.assertFalse(reloaded.lost_reason)
        self.assertFalse(reloaded.lost_note)

    # -- ownership --

    def test_owner_is_required(self):
        # As a user with no operating role: before_validate auto-fills
        # the owner for Founder/Producer sessions, and on a lived-in
        # site Administrator holds Founder - which made this test pass
        # only on a pristine CI site.
        frappe.set_user(OUTSIDER)
        with self.assertRaises(
            (frappe.MandatoryError, frappe.ValidationError)
        ):
            frappe.get_doc(
                {
                    "doctype": "Deal",
                    "title": "Ownerless",
                    "company": make_company().name,
                }
            ).insert(ignore_permissions=True)

    def test_owner_defaults_to_creating_operating_user(self):
        company = make_company()
        frappe.set_user(PRODUCER)
        deal = frappe.get_doc(
            {
                "doctype": "Deal",
                "title": "Producer's deal",
                "company": company.name,
            }
        )
        deal.insert()
        self.assertEqual(deal.deal_owner, PRODUCER)

    def test_owner_reassigns_between_founder_and_producer(self):
        deal = make_deal(deal_owner=FOUNDER)
        deal.deal_owner = PRODUCER
        deal.save()
        self.assertEqual(
            frappe.get_doc("Deal", deal.name).deal_owner, PRODUCER
        )

    def test_owner_without_operating_role_is_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            make_deal(deal_owner=OUTSIDER)

    # -- role access --

    def assert_role_can_read_write(self, user):
        frappe.set_user(user)
        for ptype in ("read", "write", "create"):
            self.assertTrue(
                frappe.has_permission("Deal", ptype),
                f"{user} should have {ptype} on Deal",
            )
        deal = make_deal(title=f"Access probe {user}", deal_owner=user)
        deal.stage = "De-brief"
        deal.save()
        from frappe.client import get_list

        # Filtered by name: the unfiltered list is capped at a page
        # (20 rows), so on a site with real data the probe deal may
        # legitimately fall off it.
        self.assertIn(
            deal.name,
            [
                row["name"]
                for row in get_list(
                    "Deal", fields=["name"], filters={"name": deal.name}
                )
            ],
        )

    def test_founder_can_read_write_deals(self):
        self.assert_role_can_read_write(FOUNDER)

    def test_producer_can_read_write_deals(self):
        self.assert_role_can_read_write(PRODUCER)

    def test_user_without_app_role_is_denied(self):
        from frappe.client import get_list

        frappe.set_user(OUTSIDER)
        self.assertFalse(frappe.has_permission("Deal", "read"))
        with self.assertRaises(frappe.PermissionError):
            get_list("Deal")

    # -- operating_users endpoint (owner dropdown on the board) --

    def test_operating_users_lists_both_operating_roles(self):
        from auraos.api import operating_users

        frappe.set_user(PRODUCER)
        names = [u["name"] for u in operating_users()]
        self.assertIn(FOUNDER, names)
        self.assertIn(PRODUCER, names)
        self.assertNotIn(OUTSIDER, names)

    def test_operating_users_denied_without_app_role(self):
        from auraos.api import operating_users

        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            operating_users()


class TestDealDetailsFields(FrappeTestCase):
    """T3.2 (issue #21): budget, source, tags, project type."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)
        # The seeds normally arrive via migrate; run them here so the
        # tests do not depend on the site's migration history.
        from auraos.setup.install import create_deal_vocabularies

        create_deal_vocabularies()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def make_tag(self, tag_name):
        if not frappe.db.exists("Deal Tag", tag_name):
            frappe.get_doc(
                {"doctype": "Deal Tag", "tag_name": tag_name}
            ).insert(ignore_permissions=True)
        return tag_name

    # -- seeded vocabularies (founder answers on issue #21) --

    def test_founder_confirmed_sources_are_seeded(self):
        for source in ("Website", "Referral", "Zalo", "Expo"):
            self.assertTrue(frappe.db.exists("Deal Source", source))

    def test_project_types_are_seeded(self):
        for project_type in ("TVC", "Social Video", "Event", "Documentary"):
            self.assertTrue(frappe.db.exists("Project Type", project_type))

    # -- persistence --

    def test_details_fields_persist(self):
        deal = make_deal(
            estimated_budget=250_000_000,
            source="Zalo",
            project_type="TVC",
            deal_tags=[
                {"deal_tag": self.make_tag("Tết")},
                {"deal_tag": self.make_tag("gấp")},
            ],
        )
        reloaded = frappe.get_doc("Deal", deal.name)
        self.assertEqual(reloaded.estimated_budget, 250_000_000)
        self.assertEqual(reloaded.source, "Zalo")
        self.assertEqual(reloaded.project_type, "TVC")
        self.assertEqual(
            [row.deal_tag for row in reloaded.deal_tags], ["Tết", "gấp"]
        )

    def test_details_fields_are_optional(self):
        deal = make_deal(title="Bare deal")
        self.assertFalse(deal.source)
        self.assertFalse(deal.project_type)
        self.assertFalse(deal.deal_tags)

    # -- vocabulary enforcement --

    def test_unknown_source_is_rejected(self):
        with self.assertRaises(frappe.LinkValidationError):
            make_deal(source="Carrier pigeon")

    def test_unknown_project_type_is_rejected(self):
        with self.assertRaises(frappe.LinkValidationError):
            make_deal(project_type="Feature film")

    def test_unknown_tag_is_rejected(self):
        with self.assertRaises(frappe.LinkValidationError):
            make_deal(deal_tags=[{"deal_tag": "never created"}])

    def test_negative_budget_is_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            make_deal(estimated_budget=-1)

    # -- who may grow which vocabulary --

    def test_founder_can_expand_sources(self):
        # Founder decision on issue #21: the source list must stay
        # expandable - a new expo or channel is a Desk entry, not code.
        frappe.set_user(FOUNDER)
        source = frappe.get_doc(
            {"doctype": "Deal Source", "source_name": "TikTok"}
        ).insert()
        self.assertTrue(frappe.db.exists("Deal Source", source.name))

    def test_producer_cannot_expand_sources(self):
        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc(
                {"doctype": "Deal Source", "source_name": "Cold call"}
            ).insert()

    def test_both_operating_roles_can_create_tags(self):
        for user, tag in ((FOUNDER, "phim ngắn"), (PRODUCER, "khách quen")):
            frappe.set_user(user)
            frappe.get_doc(
                {"doctype": "Deal Tag", "tag_name": tag}
            ).insert()
            self.assertTrue(frappe.db.exists("Deal Tag", tag))

    # -- visibility (founder: budget is fine for the producer) --

    def test_producer_sees_budget_source_tags_project_type(self):
        deal = make_deal(
            title="Producer visibility probe",
            estimated_budget=80_000_000,
            source="Referral",
            project_type="Event",
            deal_tags=[{"deal_tag": self.make_tag("visibility")}],
        )
        frappe.set_user(PRODUCER)
        seen = frappe.get_doc("Deal", deal.name)
        self.assertEqual(seen.estimated_budget, 80_000_000)
        self.assertEqual(seen.source, "Referral")
        self.assertEqual(seen.project_type, "Event")
        self.assertEqual([row.deal_tag for row in seen.deal_tags], ["visibility"])

    def test_deal_tags_map_covers_tagged_deals(self):
        from auraos.api import deal_tags_map

        deal = make_deal(
            title="Tag map probe",
            deal_tags=[
                {"deal_tag": self.make_tag("bản đồ")},
                {"deal_tag": self.make_tag("Tết")},
            ],
        )
        frappe.set_user(PRODUCER)
        tag_map = deal_tags_map()
        self.assertEqual(tag_map.get(deal.name), ["bản đồ", "Tết"])

    def test_deal_tags_map_denied_without_app_role(self):
        from auraos.api import deal_tags_map

        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            deal_tags_map()

    def test_deal_stage_entries_tracks_the_latest_move(self):
        from auraos.api import deal_stage_entries

        deal = make_deal(title="Stage age probe")
        frappe.set_user(PRODUCER)
        entered = deal_stage_entries()
        # Insertion logs the first stage_history row.
        first = entered.get(deal.name)
        self.assertIsNotNone(first)

        deal.reload()
        deal.stage = "De-brief"
        deal.save()
        moved = deal_stage_entries().get(deal.name)
        # The map follows the move into the current stage.
        self.assertEqual(moved, deal.stage_history[-1].changed_on)
        self.assertGreaterEqual(moved, first)

    def test_deal_stage_entries_denied_without_app_role(self):
        from auraos.api import deal_stage_entries

        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            deal_stage_entries()


class TestDealTableEditing(FrappeTestCase):
    """T3.3 (#27): the table saves through the Deal validation seam."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def test_inline_edit_persists(self):
        from auraos.api import update_deal_table_row

        deal = make_deal(title="Before inline edit")
        frappe.set_user(PRODUCER)
        row = update_deal_table_row(
            deal.name,
            {"title": "After inline edit", "estimated_budget": 125_000_000},
        )

        saved = frappe.get_doc("Deal", deal.name)
        self.assertEqual(saved.title, "After inline edit")
        self.assertEqual(saved.estimated_budget, 125_000_000)
        self.assertEqual(row["title"], "After inline edit")

    def test_inline_edit_uses_deal_validation_and_preserves_saved_value(self):
        from auraos.api import update_deal_table_row

        deal = make_deal(estimated_budget=10_000_000)
        frappe.set_user(PRODUCER)

        with self.assertRaises(frappe.ValidationError):
            update_deal_table_row(deal.name, {"estimated_budget": -1})

        self.assertEqual(
            frappe.db.get_value("Deal", deal.name, "estimated_budget"), 10_000_000
        )

    def test_blank_table_row_creates_deal_with_user_as_owner(self):
        from auraos.api import create_deal_table_row

        company = make_company("Blank row client")
        frappe.set_user(PRODUCER)
        row = create_deal_table_row(
            {"title": "Created in table", "company": company.name}
        )

        saved = frappe.get_doc("Deal", row["name"])
        self.assertEqual(saved.title, "Created in table")
        self.assertEqual(saved.company, company.name)
        self.assertEqual(saved.deal_owner, PRODUCER)
        self.assertEqual(saved.stage, "Brief Received")

    def test_table_endpoint_rejects_fields_that_are_not_editable(self):
        from auraos.api import update_deal_table_row

        deal = make_deal()
        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.ValidationError):
            update_deal_table_row(deal.name, {"quote_status": "Confirmed"})

    def test_table_endpoints_deny_user_without_deal_access(self):
        from auraos.api import create_deal_table_row, update_deal_table_row

        deal = make_deal()
        company = make_company()
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            update_deal_table_row(deal.name, {"title": "Forbidden"})
        with self.assertRaises(frappe.PermissionError):
            create_deal_table_row(
                {"title": "Forbidden", "company": company.name}
            )


class TestTierSuggestion(FrappeTestCase):
    """Phase B (playbook §2.2): positioning is the input, tier is the
    output - derived by the rules unless someone pins it by hand."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def test_budget_bands_suggest_the_tier(self):
        self.assertEqual(
            make_deal(title="B nhỏ", estimated_budget=30_000_000).tier, "Tier 1"
        )
        # Boundaries are inclusive: "từ 50 triệu" means 50 triệu counts.
        self.assertEqual(
            make_deal(title="B vừa", estimated_budget=50_000_000).tier, "Tier 2"
        )
        self.assertEqual(
            make_deal(title="B lớn", estimated_budget=200_000_000).tier, "Tier 3"
        )

    def test_the_founders_explicit_tier_survives(self):
        deal = make_deal(
            title="Chốt tay", estimated_budget=300_000_000, tier="Tier 1"
        )
        self.assertEqual(deal.tier, "Tier 1")
        deal.estimated_budget = 400_000_000
        deal.save()
        self.assertEqual(deal.tier, "Tier 1")

    def test_an_auto_tier_follows_the_budget_as_it_changes(self):
        deal = make_deal(title="Budget đổi", estimated_budget=30_000_000)
        self.assertEqual(deal.tier, "Tier 1")
        deal.estimated_budget = 250_000_000
        deal.save()
        self.assertEqual(deal.tier, "Tier 3")

    def test_brand_positioning_is_tier_3_whatever_it_pays(self):
        deal = make_deal(
            title="Passion nhỏ", estimated_budget=10_000_000, positioning="Brand"
        )
        self.assertEqual(deal.tier, "Tier 3")

    def test_clearing_a_pinned_tier_hands_it_back_to_the_rules(self):
        deal = make_deal(
            title="Bỏ pin", estimated_budget=300_000_000, tier="Tier 1"
        )
        deal.tier = ""
        deal.save()
        self.assertEqual(deal.tier, "Tier 3")
        # ...and it keeps tracking afterwards.
        deal.estimated_budget = 60_000_000
        deal.save()
        self.assertEqual(deal.tier, "Tier 2")

    def test_a_positioning_job_type_is_tier_3_whatever_it_pays(self):
        frappe.db.set_value("Project Type", "TVC", "is_positioning", 1)
        try:
            deal = make_deal(
                title="TVC bé", estimated_budget=10_000_000, project_type="TVC"
            )
            self.assertEqual(deal.tier, "Tier 3")
        finally:
            frappe.db.set_value("Project Type", "TVC", "is_positioning", 0)

    def test_custom_thresholds_from_settings_are_honored(self):
        frappe.db.set_single_value("AuraOS Settings", "tier2_threshold", 100_000_000)
        try:
            frappe.get_cached_doc("AuraOS Settings")  # refresh cache
            frappe.clear_document_cache("AuraOS Settings", "AuraOS Settings")
            deal = make_deal(title="Ngưỡng riêng", estimated_budget=90_000_000)
            self.assertEqual(deal.tier, "Tier 1")
        finally:
            frappe.db.set_single_value("AuraOS Settings", "tier2_threshold", 0)
            frappe.clear_document_cache("AuraOS Settings", "AuraOS Settings")

    def test_no_budget_and_no_type_suggests_nothing(self):
        self.assertFalse(make_deal(title="Trống trơn").tier)

    def test_positioning_field_is_stored_as_given(self):
        deal = make_deal(title="Định vị", positioning="Bridge")
        self.assertEqual(deal.positioning, "Bridge")

    def test_founder_edits_positioning_rules_and_they_bite(self):
        from auraos import api

        frappe.set_user(FOUNDER)
        try:
            stored = api.set_positioning_rules(
                cash=60, bridge=25, brand=15, positioning_types=["TVC"]
            )
            self.assertEqual(
                stored["mix"], {"cash": 60, "bridge": 25, "brand": 15}
            )
            flagged = {
                row["name"]
                for row in stored["project_types"]
                if row["is_positioning"]
            }
            self.assertEqual(flagged, {"TVC"})
            # The flag bites: a cheap TVC deal derives Tier 3.
            deal = make_deal(
                title="TVC rẻ", estimated_budget=10_000_000, project_type="TVC"
            )
            self.assertEqual(deal.tier, "Tier 3")
        finally:
            frappe.set_user(FOUNDER)
            api.set_positioning_rules(positioning_types=[])

    def test_producer_cannot_edit_positioning_rules(self):
        from auraos import api

        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            api.set_positioning_rules(cash=50)

    def test_classification_hints_are_readable_by_a_producer(self):
        from auraos import api

        frappe.set_user(PRODUCER)
        hints = api.classification_hints()
        self.assertEqual(set(hints), {"cash", "bridge", "brand"})

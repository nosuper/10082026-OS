"""Seam tests for T6 (issue #8): hosted quote page.

The four seams the ticket names:

- **Token access** — a valid token renders the page for a guest; an
  invalid one 404s; the token is random per version.
- **Version immutability** — a published version's content cannot change;
  publishing again makes a new version and leaves the old one alone.
- **Guest serialization boundary** — the page and the PDF carry packages,
  descriptions and totals, and nothing of cost, margin or commission;
  Guest cannot reach Deal Quote through the document or list API either.
- **Nudge condition** — a sent quote that stays quiet past the configured
  window shows up in the nudge query; a confirmed one never does.

Runs via: bench --site <site> run-tests --app auraos
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, set_request
from frappe.website.serve import get_response

from auraos.api import (
    deal_quotes,
    mark_quote_confirmed,
    mark_quote_sent,
    publish_quote,
    quote_opens,
    quote_pdf,
    silent_quote_deals,
)
from auraos.auraos.doctype.deal.test_deal import make_company
from auraos.auraos.doctype.deal_quote.deal_quote import (
    client_context,
    publish,
    record_open,
    silent_deals,
)
from auraos.lib.money import format_vnd
from auraos.tests.utils import make_test_user

FOUNDER = "founder@test.auraos.local"
PRODUCER = "producer@test.auraos.local"
# A System User with neither app role — the negative control.
OUTSIDER = "outsider@test.auraos.local"

LINES = [
    {
        "description": "Đạo diễn",
        "package": "Human resources",
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
        "package": "Equipment",
        "qty1": 2,
        "qty1_unit": "bộ",
        "qty2": 3,
        "qty2_unit": "ngày",
        "unit_price": 8_000_000,
        "tax_type": "Công ty",
        "vendor_mf_pct": 5,
        "markup_pct": 10,
    },
]

PACKAGES = [
    {"title": "Human resources", "description": "Director & crew, 3 shoot days"},
    {"title": "Equipment", "description": "Camera, lighting and grip package"},
]


def make_quotable_deal(**overrides):
    doc = frappe.get_doc(
        {
            "doctype": "Deal",
            "title": "Brand film for Chungify",
            "deal_owner": FOUNDER,
            "company": make_company().name,
            "cost_lines": overrides.pop("cost_lines", [dict(row) for row in LINES]),
            "packages": overrides.pop("packages", [dict(row) for row in PACKAGES]),
            **overrides,
        }
    )
    doc.insert()
    return doc


def render_page(token):
    set_request(method="GET", path=f"/quote/{token}")
    return get_response()


def squash(html):
    """Collapse whitespace so template indentation can't fail a compare."""
    return re.sub(r"\s+", " ", html)


class TestDealQuote(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")
        frappe.db.set_single_value("AuraOS Settings", "quote_silence_days", 5)

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    # -- publishing & versions --

    def test_publishing_freezes_the_deals_packages_and_totals(self):
        deal = make_quotable_deal()
        quote = publish(deal.name)
        self.assertEqual(quote.version, 1)
        self.assertEqual(quote.status, "Published")
        self.assertEqual(quote.total, deal.quote_total)
        self.assertEqual(
            [(p.title, p.price) for p in quote.packages],
            [(p.title, p.price) for p in deal.packages],
        )

    def test_each_version_gets_its_own_random_token(self):
        deal = make_quotable_deal()
        first = publish(deal.name)
        second = publish(deal.name)
        self.assertEqual(second.version, 2)
        self.assertNotEqual(first.token, second.token)
        self.assertEqual(len(first.token), 32)

    def test_republishing_leaves_the_earlier_version_untouched(self):
        deal = make_quotable_deal()
        first = publish(deal.name)
        frozen_total = first.total

        deal.packages[0].price_override = 999_000_000
        deal.packages[0].has_price_override = 1
        deal.save()
        second = publish(deal.name)

        reloaded = frappe.get_doc("Deal Quote", first.name)
        self.assertEqual(reloaded.total, frozen_total)
        self.assertNotEqual(second.total, frozen_total)

    def test_the_published_total_is_what_the_client_can_add_up(self):
        deal = make_quotable_deal()
        quote = publish(deal.name)
        packages = sum(package.price for package in quote.packages)
        self.assertEqual(quote.subtotal, packages)
        self.assertEqual(
            quote.total, quote.subtotal + quote.mf_amount + quote.vat_amount
        )

    def test_an_overridden_package_price_moves_the_published_total(self):
        # The producer rounds a package up; the client's Total has to
        # follow the price they're shown, not the internal line sum.
        deal = make_quotable_deal()
        before = publish(deal.name)
        deal.packages[0].price_override = deal.packages[0].price + 1_500_000
        deal.packages[0].has_price_override = 1
        deal.save()
        after = publish(deal.name)
        self.assertEqual(after.subtotal - before.subtotal, 1_500_000)
        self.assertGreater(after.total, before.total)

    def test_a_line_in_no_package_is_quoted_as_its_own_entry(self):
        # The founder prices some items as standalone packages and
        # quotes them straight (T6 walkthrough) — an unassigned line is
        # its own one-line entry, not an error.
        lines = [dict(row) for row in LINES]
        lines[1]["package"] = None
        deal = make_quotable_deal(cost_lines=lines)
        quote = publish(deal.name)
        titles = [package.title for package in quote.packages]
        self.assertIn(lines[1]["description"], titles)
        self.assertEqual(
            quote.subtotal, sum(package.price for package in quote.packages)
        )

    def test_a_standalone_line_is_priced_at_its_quote_price(self):
        lines = [dict(row) for row in LINES]
        lines[1]["package"] = None
        deal = make_quotable_deal(cost_lines=lines)
        quote = publish(deal.name)
        standalone = next(
            p for p in quote.packages if p.title == lines[1]["description"]
        )
        self.assertEqual(standalone.price, deal.cost_lines[1].quote_price)

    def test_rounding_a_package_up_raises_the_stored_margin(self):
        # Issue #32: the client pays the overridden price, so the
        # margin, the margin % and the floor warning must move with it —
        # they used to be measured against the line-based total.
        deal = make_quotable_deal()
        before = frappe.get_doc("Deal", deal.name)
        deal.packages[0].price_override = deal.packages[0].price + 2_000_000
        deal.packages[0].has_price_override = 1
        deal.save()
        after = frappe.get_doc("Deal", deal.name)

        self.assertGreater(after.quote_margin, before.quote_margin)
        self.assertGreater(after.quote_margin_pct, before.quote_margin_pct)
        self.assertGreater(after.quote_total, before.quote_total)

    def test_rounding_a_package_up_raises_the_founder_chain(self):
        deal = make_quotable_deal()
        before = frappe.get_doc("Deal", deal.name)
        deal.packages[0].price_override = deal.packages[0].price + 2_000_000
        deal.packages[0].has_price_override = 1
        deal.save()
        after = frappe.get_doc("Deal", deal.name)

        self.assertGreater(after.net_profit, before.net_profit)
        self.assertGreater(after.total_commission, before.total_commission)

    def test_the_published_total_matches_the_deals_own_total(self):
        # One price, computed one way: what the breakdown says the deal
        # is worth is what the client is asked to pay.
        deal = make_quotable_deal()
        deal.packages[0].price_override = deal.packages[0].price + 2_000_000
        deal.packages[0].has_price_override = 1
        deal.save()
        quote = publish(deal.name)
        reloaded = frappe.get_doc("Deal", deal.name)
        self.assertEqual(quote.total, reloaded.quote_total)
        self.assertEqual(quote.subtotal, reloaded.quote_subtotal)

    def test_publishing_an_empty_deal_is_refused(self):
        deal = make_quotable_deal(packages=[], cost_lines=[])
        with self.assertRaises(frappe.ValidationError):
            publish(deal.name)

    # -- immutability --

    def test_published_totals_cannot_be_edited(self):
        quote = publish(make_quotable_deal().name)
        quote.total = 1
        with self.assertRaises(frappe.ValidationError):
            quote.save()

    def test_published_packages_cannot_be_edited(self):
        quote = publish(make_quotable_deal().name)
        quote.packages[0].price = 1
        with self.assertRaises(frappe.ValidationError):
            quote.save()

    def test_published_token_cannot_be_swapped(self):
        quote = publish(make_quotable_deal().name)
        quote.token = "x" * 32
        with self.assertRaises(frappe.ValidationError):
            quote.save()

    def test_delivery_status_stays_writable(self):
        quote = publish(make_quotable_deal().name)
        quote.mark_sent()
        self.assertEqual(frappe.db.get_value("Deal Quote", quote.name, "status"), "Sent")

    # -- the public page --

    def test_valid_token_renders_the_packages_for_a_guest(self):
        deal = make_quotable_deal()
        quote = publish(deal.name)

        frappe.set_user("Guest")
        response = render_page(quote.token)
        html = response.get_data().decode()

        self.assertEqual(response.status_code, 200)
        for package in quote.packages:
            self.assertIn(package.title, html)
            self.assertIn(package.description, html)
        self.assertIn(format_vnd(quote.total), html)

    def test_invalid_token_404s_with_a_readable_page(self):
        frappe.set_user("Guest")
        response = render_page("not-a-real-token")
        html = response.get_data().decode()
        self.assertEqual(response.status_code, 404)
        # A client following a dead link gets a sentence, not a trace.
        self.assertIn("Quote not found", html)
        self.assertNotIn("Traceback", html)
        self.assertNotIn("DoesNotExistError", html)

    def test_page_never_serializes_internals_to_a_guest(self):
        deal = make_quotable_deal()
        quote = publish(deal.name)

        frappe.set_user("Guest")
        html = render_page(quote.token).get_data().decode()

        # The numbers the producer and the founder see on the breakdown.
        # (A package price legitimately equals its single member line's
        # quote price, so cost basis and margin are the honest probes.)
        for internal in (
            deal.quote_margin,
            deal.cost_lines[0].cost_basis,
            deal.cost_lines[1].cost_basis,
        ):
            self.assertNotIn(
                format_vnd(internal), html, f"{internal} leaked to the client"
            )
        # ...and the line-level story behind the packages.
        for row in deal.cost_lines:
            self.assertNotIn(row.description, html)
        self.assertNotIn("commission", html.lower())

    def test_guest_cannot_reach_deal_quote_through_the_document_api(self):
        quote = publish(make_quotable_deal().name)
        frappe.set_user("Guest")
        self.assertFalse(frappe.has_permission("Deal Quote", "read", doc=quote.name))
        with self.assertRaises(frappe.PermissionError):
            frappe.get_list("Deal Quote")

    # -- open events --

    def test_opening_the_page_records_an_open_event(self):
        deal = make_quotable_deal()
        quote = publish(deal.name)

        frappe.set_user("Guest")
        render_page(quote.token)
        render_page(quote.token)

        frappe.set_user(FOUNDER)
        self.assertEqual(deal_quotes(deal.name)[0]["opens"], 2)
        self.assertEqual(len(quote_opens(quote.name)), 2)

    def test_open_events_are_not_readable_by_guests(self):
        quote = publish(make_quotable_deal().name)
        frappe.set_user("Guest")
        render_page(quote.token)
        with self.assertRaises(frappe.PermissionError):
            frappe.get_list("Deal Quote Open")

    # -- PDF export --

    def test_pdf_export_is_downloadable_by_a_guest(self):
        quote = publish(make_quotable_deal().name)
        frappe.set_user("Guest")
        try:
            quote_pdf(quote.token)
        except Exception as error:  # wkhtmltopdf is not installed everywhere
            if "wkhtmltopdf" not in str(error).lower():
                raise
            self.skipTest("wkhtmltopdf unavailable on this machine")
        self.assertEqual(frappe.local.response.type, "pdf")
        self.assertTrue(frappe.local.response.filecontent.startswith(b"%PDF"))
        frappe.set_user("Administrator")
        self.assertEqual(
            frappe.db.count("Deal Quote Open", {"quote": quote.name, "via": "PDF"}), 1
        )

    def test_pdf_export_refuses_an_invalid_token(self):
        frappe.set_user("Guest")
        with self.assertRaises(frappe.DoesNotExistError):
            quote_pdf("not-a-real-token")

    def test_pdf_downloads_are_counted_apart_from_page_opens(self):
        deal = make_quotable_deal()
        quote = publish(deal.name)
        frappe.set_user("Guest")
        render_page(quote.token)
        record_open(quote.name, via="PDF")

        frappe.set_user(FOUNDER)
        row = deal_quotes(deal.name)[0]
        self.assertEqual(row["opens"], 1)
        self.assertEqual(row["downloads"], 1)
        self.assertTrue(row["last_open"])

    def test_pdf_renders_the_same_body_as_the_page(self):
        quote = publish(make_quotable_deal().name)
        frappe.set_user("Guest")
        html = render_page(quote.token).get_data().decode()
        # The PDF endpoint renders exactly this, from the same builder.
        body = frappe.render_template(
            "auraos/templates/includes/quote_body.html", client_context(quote)
        )
        self.assertIn(squash(body), squash(html))

    # -- delivery status on the deal --

    def test_publishing_mirrors_the_status_onto_the_deal(self):
        deal = make_quotable_deal()
        quote = publish(deal.name)
        reloaded = frappe.get_doc("Deal", deal.name)
        self.assertEqual(reloaded.quote_status, "Published")
        self.assertEqual(reloaded.latest_quote, quote.name)

    def test_marking_sent_moves_the_deal_to_quote_sent(self):
        deal = make_quotable_deal(stage="Breakdown")
        quote = publish(deal.name)
        quote.mark_sent()
        reloaded = frappe.get_doc("Deal", deal.name)
        self.assertEqual(reloaded.stage, "Quote Sent")
        self.assertEqual(reloaded.quote_status, "Sent")
        self.assertTrue(reloaded.quote_sent_on)

    def test_marking_sent_does_not_drag_a_negotiating_deal_backwards(self):
        deal = make_quotable_deal(stage="Negotiation")
        publish(deal.name).mark_sent()
        self.assertEqual(frappe.db.get_value("Deal", deal.name, "stage"), "Negotiation")

    def test_confirming_records_the_status_on_the_deal(self):
        deal = make_quotable_deal()
        quote = publish(deal.name)
        quote.mark_sent()
        quote.mark_confirmed()
        self.assertEqual(
            frappe.db.get_value("Deal", deal.name, "quote_status"), "Confirmed"
        )

    def test_confirming_an_older_version_still_reaches_the_deal(self):
        # The producer re-published a tweak, then the client confirmed
        # the version they were actually holding.
        deal = make_quotable_deal()
        first = publish(deal.name)
        publish(deal.name)
        first.mark_confirmed()
        self.assertEqual(
            frappe.db.get_value("Deal", deal.name, "quote_status"), "Confirmed"
        )

    def test_a_user_without_deal_access_cannot_read_or_mark_quotes(self):
        deal = make_quotable_deal()
        quote = publish(deal.name)
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            deal_quotes(deal.name)
        with self.assertRaises(frappe.PermissionError):
            quote_opens(quote.name)
        with self.assertRaises(frappe.PermissionError):
            mark_quote_sent(quote.name)

    def test_an_accidental_confirm_can_be_undone(self):
        # "If I marked confirmed by accident, no turning back" — marking
        # it sent again is the way back, keeping the original send time.
        deal = make_quotable_deal()
        quote = publish(deal.name)
        quote.mark_sent()
        sent_on = quote.sent_on
        quote.mark_confirmed()
        quote.mark_sent()
        self.assertEqual(quote.status, "Sent")
        self.assertIsNone(quote.confirmed_on)
        self.assertEqual(quote.sent_on, sent_on)
        self.assertEqual(
            frappe.db.get_value("Deal", deal.name, "quote_status"), "Sent"
        )

    def test_a_producer_can_publish_and_mark_a_quote(self):
        deal = make_quotable_deal()
        frappe.set_user(PRODUCER)
        published = publish_quote(deal.name)
        sent = mark_quote_sent(published["name"])
        self.assertEqual(sent["status"], "Sent")
        confirmed = mark_quote_confirmed(published["name"])
        self.assertEqual(confirmed["status"], "Confirmed")

    # -- the silence nudge --

    def sent_quote_deal(self, days_ago, silence_days=5):
        deal = make_quotable_deal()
        quote = publish(deal.name)
        quote.mark_sent()
        sent_on = add_to_date(frappe.utils.now_datetime(), days=-days_ago)
        frappe.db.set_value("Deal Quote", quote.name, "sent_on", sent_on)
        frappe.db.set_value("Deal", deal.name, "quote_sent_on", sent_on)
        frappe.db.set_single_value("AuraOS Settings", "quote_silence_days", silence_days)
        return deal

    def test_a_quiet_sent_quote_is_nudged_after_the_window(self):
        deal = self.sent_quote_deal(days_ago=6)
        self.assertIn(deal.name, [row.name for row in silent_deals()])

    def test_republishing_does_not_cancel_the_nudge(self):
        # Re-pricing a quote the client is sitting on must not make the
        # deal look untouched — that is the silence death T6 exists to
        # stop (spec #2, story 6).
        deal = self.sent_quote_deal(days_ago=10)
        publish(deal.name)
        self.assertIn(deal.name, [row.name for row in silent_deals()])

    def test_a_fresh_sent_quote_is_not_nudged(self):
        deal = self.sent_quote_deal(days_ago=1)
        self.assertNotIn(deal.name, [row.name for row in silent_deals()])

    def test_a_confirmed_quote_is_never_nudged(self):
        deal = self.sent_quote_deal(days_ago=30)
        frappe.get_doc("Deal Quote", frappe.db.get_value("Deal", deal.name, "latest_quote")).mark_confirmed()
        self.assertNotIn(deal.name, [row.name for row in silent_deals()])

    def test_zero_silence_days_turns_the_nudge_off(self):
        deal = self.sent_quote_deal(days_ago=30, silence_days=0)
        self.assertNotIn(deal.name, [row.name for row in silent_deals()])

    def test_the_nudge_endpoint_reports_the_configured_window(self):
        deal = self.sent_quote_deal(days_ago=6, silence_days=3)
        frappe.set_user(PRODUCER)
        payload = silent_quote_deals()
        self.assertEqual(payload["silence_days"], 3)
        self.assertIn(deal.name, [row.name for row in payload["deals"]])


class TestQuoteDetailLevels(FrappeTestCase):
    """A3 (playbook §3.3): how much of the build the client's page shows."""

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

    def test_default_publish_stays_package_totals(self):
        deal = make_quotable_deal()
        quote = publish(deal.name)
        self.assertEqual(quote.detail_level, "Package totals")
        self.assertEqual(len(quote.lines), 0)

    def test_line_by_line_freezes_the_client_safe_half_of_every_line(self):
        deal = make_quotable_deal(quote_detail_level="Line by line")
        quote = publish(deal.name)
        self.assertEqual(quote.detail_level, "Line by line")
        self.assertEqual(len(quote.lines), len(deal.cost_lines))
        frozen = quote.lines[0]
        source = deal.cost_lines[0]
        self.assertEqual(frozen.description, source.description)
        self.assertEqual(frozen.package, source.package)
        self.assertEqual(frozen.qty1, source.qty1)
        self.assertEqual(frozen.quote_price, source.quote_price)
        # The totals are the same offer whichever way it is printed.
        self.assertEqual(quote.total, deal.quote_total)

    def test_line_by_line_page_prints_quantities_and_amounts(self):
        deal = make_quotable_deal(quote_detail_level="Line by line")
        quote = publish(deal.name)
        html = squash(render_page(quote.token).get_data(as_text=True))
        self.assertIn("1 người × 3 ngày", html)
        self.assertIn("Đạo diễn", html)
        self.assertIn(format_vnd(deal.cost_lines[0].quote_price), html)

    def test_the_page_never_prints_the_cost_side_at_any_level(self):
        deal = make_quotable_deal(quote_detail_level="Line by line")
        quote = publish(deal.name)
        html = squash(render_page(quote.token).get_data(as_text=True))
        # The internal unit cost and markup are not in the frozen rows at
        # all, so they cannot render — pin it anyway. (Checked as field
        # names and figures, not bare words: a template comment may
        # legitimately say "markup".)
        self.assertNotIn(format_vnd(deal.cost_lines[0].unit_price), html)
        self.assertNotIn("markup_pct", html)
        self.assertNotIn("vendor_mf_pct", html)

    def test_lump_sum_collapses_to_one_entry_with_the_scope(self):
        deal = make_quotable_deal(quote_detail_level="Lump sum")
        quote = publish(deal.name)
        self.assertEqual(quote.detail_level, "Lump sum")
        self.assertEqual(len(quote.packages), 1)
        entry = quote.packages[0]
        self.assertEqual(entry.title, deal.title)
        self.assertIn("Human resources", entry.description)
        self.assertIn("Equipment", entry.description)
        # One line or many, the client is offered the same money.
        self.assertEqual(quote.total, deal.quote_total)

    def test_frozen_lines_are_immutable(self):
        deal = make_quotable_deal(quote_detail_level="Line by line")
        quote = publish(deal.name)
        quote.lines[0].quote_price = 1
        with self.assertRaises(frappe.ValidationError):
            quote.save()

"""Seam tests for T6.1a (issue #42): company identity on the quote.

`tests/test_quote_identity.py` proves the whitelist and the empty-field
rules without Frappe. What only a site can prove is the wiring:

1. **The second guest boundary holds against the real Single.** AuraOS
   Settings carries the margin floor beside the company block. The
   render context a guest is handed must contain the block and not the
   floor — through the whitelist, not through anyone remembering.
2. **Branding renders live.** Editing the company name changes what an
   already-sent version displays, and creates no new version. This is a
   deliberate exception to quote-version immutability
   (docs/adr/0002-quote-branding-renders-live.md), so it is pinned by a
   test rather than left as a property of how the code happens to read.
3. **One template, two surfaces.** The letterhead is on the page and in
   the PDF; the signature block and the running header/footer are in the
   PDF only, and reach it through Frappe's own extraction rather than a
   second template.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import get_company_identity, quote_pdf, set_company_identity
from auraos.auraos.doctype.deal_quote.deal_quote import client_context, publish
from auraos.auraos.doctype.deal_quote.test_deal_quote import (
    FOUNDER,
    PRODUCER,
    make_quotable_deal,
    render_page,
    squash,
)
from auraos.lib.quote import COMPANY_FIELDS
from auraos.tests.utils import make_test_user

IDENTITY = {
    "company_name": "Aura Productions",
    "tax_code": "0312345678",
    "address": "12 Nguyễn Huệ, Quận 1, TP.HCM",
    "phone": "028 3822 1234",
    "email": "hello@aura.example",
    "website": "aura.example",
    "bank_name": "Vietcombank",
    "bank_account_number": "0071000123456",
    "bank_account_name": "CONG TY TNHH AURA",
    "signatory_name": "Nguyễn Anh Chung",
    "signatory_title": "Giám đốc",
}

MARGIN_FLOOR = 37.77


def set_identity(**overrides):
    """Write the company block onto the Single, floor and all."""
    values = {**{field: None for field in COMPANY_FIELDS}, **IDENTITY, **overrides}
    for field, value in values.items():
        frappe.db.set_single_value("AuraOS Settings", field, value)
    frappe.db.set_single_value("AuraOS Settings", "margin_floor_pct", MARGIN_FLOOR)


def clear_identity():
    for field in COMPANY_FIELDS:
        frappe.db.set_single_value("AuraOS Settings", field, None)


def rendered(token):
    return squash(render_page(token).get_data().decode())


class TestQuoteIdentity(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")

    def setUp(self):
        frappe.set_user("Administrator")
        set_identity()

    def tearDown(self):
        frappe.set_user("Administrator")
        clear_identity()
        frappe.db.set_single_value("AuraOS Settings", "margin_floor_pct", 0)
        super().tearDown()

    # -- the second guest boundary --

    def test_the_guest_context_carries_no_setting_outside_the_whitelist(self):
        """The regression this whitelist exists for.

        A setting added to the Single later must not reach a client page
        until someone names it in COMPANY_FIELDS on purpose.
        """
        quote = publish(make_quotable_deal().name)

        company = client_context(quote)["company"]

        self.assertEqual(
            set(company),
            set(COMPANY_FIELDS) | {"has_bank", "has_contact", "has_letterhead"},
        )
        self.assertNotIn("margin_floor_pct", company)
        self.assertNotIn("quote_silence_days", company)

    def test_the_margin_floor_never_reaches_the_body_a_guest_is_served(self):
        """Asserted against the quote body, not the whole page.

        Frappe's own chrome inlines SVG path data, and a short decimal
        turns up inside it by coincidence — a search over the finished
        page fails on noise while proving nothing about this template.
        """
        quote = publish(make_quotable_deal().name)

        body = frappe.render_template(
            "auraos/templates/includes/quote_body.html", client_context(quote)
        )

        self.assertNotIn(str(MARGIN_FLOOR), body)
        self.assertNotIn("margin_floor", body)

    # -- what a client actually sees --

    def test_the_page_shows_the_company_identity(self):
        quote = publish(make_quotable_deal().name)

        frappe.set_user("Guest")
        html = rendered(quote.token)

        self.assertIn("Aura Productions", html)
        self.assertIn("0312345678", html)
        self.assertIn("12 Nguyễn Huệ", html)
        self.assertIn("hello@aura.example", html)

    def test_the_page_shows_the_bank_details_a_client_pays_into(self):
        quote = publish(make_quotable_deal().name)

        frappe.set_user("Guest")
        html = rendered(quote.token)

        self.assertIn("Vietcombank", html)
        self.assertIn("0071000123456", html)

    def test_an_unfilled_bank_block_prints_no_heading(self):
        """A heading over three blank lines reads worse than no block."""
        set_identity(bank_name=None, bank_account_number=None, bank_account_name=None)
        quote = publish(make_quotable_deal().name)

        frappe.set_user("Guest")
        html = rendered(quote.token)

        self.assertNotIn('<div class="aura-bank-heading">', html)

    def test_a_site_that_filled_nothing_in_still_serves_a_quote(self):
        """Identity is optional; a quote without it is still an offer."""
        clear_identity()
        quote = publish(make_quotable_deal().name)

        frappe.set_user("Guest")
        html = rendered(quote.token)

        self.assertNotIn('<div class="aura-letterhead">', html)
        self.assertIn("Brand film for Chungify", html)

    def test_an_unfilled_field_prints_nothing_rather_than_its_label(self):
        set_identity(tax_code=None)
        quote = publish(make_quotable_deal().name)

        frappe.set_user("Guest")
        html = rendered(quote.token)

        self.assertIn("Aura Productions", html)
        self.assertNotIn("Tax code", html)

    # -- the document's own name --

    def test_the_document_carries_a_quote_number_with_its_version(self):
        deal = make_quotable_deal()
        publish(deal.name)
        second = publish(deal.name)

        frappe.set_user("Guest")
        html = rendered(second.token)

        self.assertEqual(second.version, 2)
        self.assertIn(f"{second.name}-v2", html)

    def test_the_standalone_version_line_folded_into_the_number(self):
        quote = publish(make_quotable_deal().name)

        frappe.set_user("Guest")
        html = rendered(quote.token)

        self.assertNotIn("Version 1", html)
        self.assertIn(f"{quote.name}-v1", html)

    # -- live, not frozen (ADR 0002) --

    def test_renaming_the_company_changes_what_a_sent_version_shows(self):
        quote = publish(make_quotable_deal().name)
        frappe.set_user(FOUNDER)
        quote.mark_sent()

        frappe.set_user("Administrator")
        frappe.db.set_single_value("AuraOS Settings", "company_name", "Aura Studio")

        frappe.set_user("Guest")
        html = rendered(quote.token)

        self.assertIn("Aura Studio", html)
        self.assertNotIn("Aura Productions", html)

    def test_renaming_the_company_creates_no_new_version(self):
        """Branding is not part of the offer, so it does not re-issue it."""
        deal = make_quotable_deal()
        quote = publish(deal.name)

        frappe.db.set_single_value("AuraOS Settings", "company_name", "Aura Studio")

        self.assertEqual(frappe.db.count("Deal Quote", {"deal": deal.name}), 1)
        reloaded = frappe.get_doc("Deal Quote", quote.name)
        self.assertEqual(reloaded.version, 1)
        self.assertEqual(reloaded.total, quote.total)

    def test_emptying_a_field_blanks_it_on_an_existing_quote(self):
        """No per-version fallback to the old value — ADR 0002 says so."""
        quote = publish(make_quotable_deal().name)
        frappe.db.set_single_value("AuraOS Settings", "phone", None)

        frappe.set_user("Guest")
        html = rendered(quote.token)

        self.assertNotIn("028 3822 1234", html)
        self.assertIn("Aura Productions", html)

    # -- one template, two surfaces --

    def test_the_page_and_the_pdf_are_built_from_one_template_and_context(self):
        quote = publish(make_quotable_deal().name)
        frappe.set_user("Guest")
        html = rendered(quote.token)

        body = squash(
            frappe.render_template(
                "auraos/templates/includes/quote_body.html", client_context(quote)
            )
        )

        self.assertIn(body, html)

    def test_the_signature_block_is_written_for_the_pdf_and_hidden_on_the_page(self):
        """Both parties sign, on the PDF only.

        The block is in the one template, marked `visible-pdf` — the
        class Frappe's PDF pipeline strips to unhide it. On the page the
        stylesheet in the same file keeps it hidden, which is why the
        markup being present is not the same as it being shown.
        """
        quote = publish(make_quotable_deal().name)

        frappe.set_user("Guest")
        html = rendered(quote.token)

        self.assertIn("aura-signatures visible-pdf", html)
        self.assertIn(".visible-pdf { display: none; }", html)
        self.assertIn("Nguyễn Anh Chung", html)
        self.assertIn("Giám đốc", html)

    def test_the_running_header_and_footer_are_pdf_chrome_only(self):
        """Frappe extracts these by id; on the page they must not show."""
        quote = publish(make_quotable_deal().name)

        frappe.set_user("Guest")
        html = rendered(quote.token)

        self.assertIn('id="header-html"', html)
        self.assertIn('id="footer-html"', html)
        # Their contents carry the same hiding class as the signatures,
        # because Frappe only strips the elements on the PDF path.
        self.assertIn("aura-running-header visible-pdf", html)
        self.assertIn("aura-running-footer visible-pdf", html)

    def test_the_footer_asks_wkhtmltopdf_for_the_page_count(self):
        quote = publish(make_quotable_deal().name)

        body = frappe.render_template(
            "auraos/templates/includes/quote_body.html", client_context(quote)
        )

        self.assertIn('<span class="page"></span>', body)
        self.assertIn('<span class="topage"></span>', body)

    def test_the_running_header_names_the_company_and_the_quote(self):
        """A page detached from the rest is still traceable."""
        quote = publish(make_quotable_deal().name)

        body = squash(
            frappe.render_template(
                "auraos/templates/includes/quote_body.html", client_context(quote)
            )
        )
        header = body.split('id="header-html"')[1].split("</div>")[0]

        self.assertIn("Aura Productions", header)

    def pdf_pages(self, quote):
        """The delivered PDF, page by page, as text.

        Through `auraos.api.quote_pdf` rather than a hand-rolled
        `get_pdf` call: the endpoint is what a client downloads, and a
        test that renders its own HTML would keep passing if the
        endpoint were pointed at another template tomorrow.
        """
        from io import BytesIO

        from pypdf import PdfReader

        frappe.set_user("Guest")
        try:
            quote_pdf(quote.token)
        except Exception as error:  # wkhtmltopdf is not installed everywhere
            if "wkhtmltopdf" not in str(error).lower():
                raise
            self.skipTest("wkhtmltopdf unavailable on this machine")
        content = frappe.local.response.filecontent
        self.assertTrue(content.startswith(b"%PDF"))
        return [
            squash(page.extract_text())
            for page in PdfReader(BytesIO(content)).pages
        ]

    def test_the_delivered_pdf_carries_the_company_identity(self):
        """The AC's drift guard, on the endpoint a client actually calls."""
        quote = publish(make_quotable_deal().name)

        text = " ".join(self.pdf_pages(quote))

        self.assertIn("Aura Productions", text)
        self.assertIn(f"Tax code {IDENTITY['tax_code']}", text)
        self.assertIn(f"{quote.name}-v1", text)
        self.assertIn(IDENTITY["bank_account_number"], text)
        # Uppercased by the stylesheet, and extracted that way.
        self.assertIn("FOR THE CLIENT", text)
        self.assertIn(IDENTITY["signatory_name"], text)

    def test_the_pdf_carries_its_chrome_on_the_pages_it_should(self):
        """The one thing only a rendered PDF can answer.

        Every other surface here is HTML we can read. Whether the
        continuation header stays off page 1 depends on wkhtmltopdf
        handing its header document a `page` query parameter, and on the
        script in the template parsing it in a WebKit old enough to lack
        URLSearchParams — a mechanism that would break silently.

        Slow (it runs wkhtmltopdf over five pages) and worth it.
        """
        deal = make_quotable_deal()
        for index in range(40):
            deal.append(
                "packages",
                {"title": f"Extra package {index}", "description": "x" * 200},
            )
        deal.save()
        quote = publish(deal.name)

        pages = self.pdf_pages(quote)
        running = f"{IDENTITY['company_name']} {quote.name}-v1"

        self.assertGreater(len(pages), 1)
        # Page 1 has the letterhead; repeating the slim header above it
        # is the redundancy this suppression exists for.
        self.assertNotIn(running, pages[0])
        self.assertIn(running, pages[1])
        # And the footer counts pages on every one of them.
        for number, page in enumerate(pages, start=1):
            self.assertIn(f"Page {number} of {len(pages)}", page)
            self.assertIn(f"Tax code {IDENTITY['tax_code']}", page)

    def test_the_logo_url_survives_the_pdf_pipeline(self):
        """Extracted text cannot see an image, so test the mechanism.

        The stored value is site-relative (`/files/...`). wkhtmltopdf
        fetches it over HTTP, which only works because `get_pdf` runs
        `scrub_urls` over the body first — that rewrite is the half of
        this AC the page render does not exercise.
        """
        from frappe.utils.pdf import scrub_urls

        logo = self.public_logo()
        set_identity(logo=logo.file_url)
        quote = publish(make_quotable_deal().name)

        body = frappe.render_template(
            "auraos/templates/includes/quote_body.html", client_context(quote)
        )

        self.assertIn(f'src="{logo.file_url}"', body)
        self.assertIn(f'src="http', scrub_urls(body))
        self.assertNotIn(f'src="{logo.file_url}"', scrub_urls(body))

    def public_logo(self):
        """A logo a guest can load — private would 403 on the page."""
        return frappe.get_doc(
            {
                "doctype": "File",
                "file_name": "aura-logo.png",
                "is_private": 0,
                "content": b"\x89PNG\r\n\x1a\n",
            }
        ).insert(ignore_permissions=True)

    # -- the settings screen writes the block, and only the block --

    def test_the_founder_can_read_and_write_the_company_block(self):
        frappe.set_user(FOUNDER)

        saved = set_company_identity(values={"company_name": "Aura Studio"})

        self.assertEqual(saved["company_name"], "Aura Studio")
        self.assertEqual(get_company_identity()["company_name"], "Aura Studio")

    def test_the_settings_screen_cannot_write_the_margin_floor(self):
        """The security-shaped half of the endpoint.

        A screen that can write any field on this Single is one bug away
        from setting the floor, so anything outside the whitelist is
        refused by name rather than ignored quietly.
        """
        frappe.set_user(FOUNDER)

        with self.assertRaises(frappe.ValidationError) as refusal:
            set_company_identity(
                values={"company_name": "Aura Studio", "margin_floor_pct": 0}
            )

        self.assertIn("margin_floor_pct", str(refusal.exception))
        self.assertEqual(
            frappe.db.get_single_value("AuraOS Settings", "margin_floor_pct"),
            MARGIN_FLOOR,
        )

    def test_a_producer_cannot_change_the_company_identity(self):
        frappe.set_user(PRODUCER)

        with self.assertRaises(frappe.PermissionError):
            set_company_identity(values={"company_name": "Producer Productions"})

    # -- the other half of the guest boundary --

    def test_a_guest_cannot_reach_the_settings_document_at_all(self):
        """Rule one of the guest boundary, for the second document.

        The whitelist decides what the page *shows*; this is the reason
        it is not the only thing standing between a client and the
        margin floor. The same proof `test_deal_quote` makes for Deal
        Quote, made here for AuraOS Settings.
        """
        publish(make_quotable_deal().name)

        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc("AuraOS Settings").check_permission("read")
        with self.assertRaises(frappe.PermissionError):
            get_company_identity()

    def test_a_producer_cannot_read_the_company_block_through_the_endpoint(self):
        """AuraOS Settings is founder-only; this endpoint does not widen it."""
        frappe.set_user(PRODUCER)

        with self.assertRaises(frappe.PermissionError):
            get_company_identity()

    def test_the_logo_reaches_both_surfaces_as_one_url(self):
        """One context, so the page and the PDF cannot point elsewhere."""
        logo = self.public_logo()
        set_identity(logo=logo.file_url)
        quote = publish(make_quotable_deal().name)

        context = client_context(quote)
        frappe.set_user("Guest")
        html = rendered(quote.token)

        self.assertEqual(context["company"]["logo"], logo.file_url)
        self.assertIn(logo.file_url, html)

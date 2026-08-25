"""Seam tests for package detail and quote validity (#44).

The rules - what a quantity reads as, what counts as expired, where a
deliverables line breaks - are pinned framework-free in
tests/test_quote.py. What only a site can prove is the freezing, and one
thing the pure tests cannot say at all:

1. **Publishing copies both onto the version**, so a client holding a
   quote keeps the detail and the date it was handed.
2. **Re-pricing the deal does not restate a published version.** The
   client is holding a PDF that says "valid until 20 August"; changing
   the deal must not change it.
3. **A quantity is descriptive and nothing multiplies it.** The price on
   the version is the price the engine computed, whatever quantity sits
   beside it - which is the whole of the decision and the thing a future
   change is most likely to break.
4. **An expired quote still opens and still reads in full.** The page
   says so; it does not close.

Runs via: bench --site <site> run-tests --app auraos
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, set_request, today
from frappe.website.serve import get_response

from auraos.auraos.doctype.deal.test_deal import FOUNDER, make_company
from auraos.auraos.doctype.deal_quote.deal_quote import publish
from auraos.tests.utils import make_test_user

LINES = [
    {
        "description": "Quay chính",
        "qty1": 2,
        "qty2": 1,
        "unit_price": 20_000_000,
        "tax_type": "Không hoá đơn",
        "package": "Ngày quay",
    },
]

DELIVERABLES = "Bản dựng 60s\nBản 30s\nFile gốc"


class QuoteDetailTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")

    def setUp(self):
        frappe.set_user(FOUNDER)

    def tearDown(self):
        frappe.set_user("Administrator")

    def a_deal(self, valid_until=None, **package):
        doc = frappe.get_doc(
            {
                "doctype": "Deal",
                "title": "TVC Tết",
                "deal_owner": FOUNDER,
                "company": make_company().name,
                "cost_lines": [dict(row) for row in LINES],
                "packages": [
                    {
                        "title": "Ngày quay",
                        "qty": 2,
                        "unit": "ngày quay",
                        "deliverables": DELIVERABLES,
                        **package,
                    }
                ],
                "quote_valid_until": valid_until,
            }
        )
        doc.insert()
        return doc

    def rendered(self, quote):
        frappe.set_user("Guest")
        set_request(method="GET", path=f"/quote/{quote.token}")
        html = get_response().get_data(as_text=True)
        frappe.set_user(FOUNDER)
        return re.sub(r"\s+", " ", html)

    # -- freezing --

    def test_publishing_freezes_the_detail_and_the_date(self):
        deal = self.a_deal(valid_until="2026-08-20")

        quote = publish(deal.name)

        self.assertEqual(str(quote.valid_until), "2026-08-20")
        package = quote.packages[0]
        self.assertEqual(package.qty, 2)
        self.assertEqual(package.unit, "ngày quay")
        self.assertEqual(package.deliverables, DELIVERABLES)

    def test_re_pricing_the_deal_does_not_restate_a_published_version(self):
        """The client is holding a PDF that says 20 August."""
        deal = self.a_deal(valid_until="2026-08-20")
        quote = publish(deal.name)

        deal.reload()
        deal.quote_valid_until = "2027-01-01"
        deal.packages[0].qty = 9
        deal.packages[0].unit = "buổi"
        deal.packages[0].deliverables = "Chỉ một file"
        deal.save()

        quote.reload()
        self.assertEqual(str(quote.valid_until), "2026-08-20")
        self.assertEqual(quote.packages[0].qty, 2)
        self.assertEqual(quote.packages[0].unit, "ngày quay")
        self.assertEqual(quote.packages[0].deliverables, DELIVERABLES)

    def test_a_deal_with_no_expiry_publishes_without_one(self):
        """Blank is the default and the common case."""
        quote = publish(self.a_deal().name)

        self.assertFalse(quote.valid_until)

    # -- the decision most likely to be broken later --

    def test_a_quantity_multiplies_nothing(self):
        """Descriptive, never arithmetic.

        The price is the sum of the lines or the override the producer
        typed. Two versions of the same deal, one with a quantity of 2
        and one with 9, must carry the same money - and this is the test
        that fails on the day somebody makes the quantity a multiplier.
        """
        two = publish(self.a_deal(qty=2).name)
        nine = publish(self.a_deal(qty=9).name)

        self.assertEqual(two.packages[0].price, nine.packages[0].price)
        self.assertEqual(two.total, nine.total)
        self.assertEqual(two.packages[0].qty, 2)
        self.assertEqual(nine.packages[0].qty, 9)

    # -- what the client reads --

    def test_the_page_prints_the_detail(self):
        quote = publish(self.a_deal().name)

        page = self.rendered(quote)

        self.assertIn("2 ngày quay", page)
        for line in DELIVERABLES.split("\n"):
            self.assertIn(line, page)

    def test_an_expired_quote_still_opens_and_says_it_has_passed(self):
        """Said, never enforced. The version is a record of what was
        offered, and the founder may still honour it - a page that locked
        itself would make that decision for them."""
        quote = publish(self.a_deal(valid_until=add_days(today(), -1)).name)

        page = self.rendered(quote)

        self.assertIn("đã qua", page)
        # And the offer below it is still all there.
        self.assertIn("Ngày quay", page)
        self.assertIn("2 ngày quay", page)

    def test_a_quote_valid_today_is_not_expired(self):
        """The last day is inclusive: valid until the 20th is valid on
        the 20th, which is what anyone reading the words expects."""
        quote = publish(self.a_deal(valid_until=today()).name)

        page = self.rendered(quote)

        self.assertNotIn("đã qua", page)
        self.assertIn("Hiệu lực đến", page)

    def test_a_quote_with_no_expiry_prints_no_validity_line(self):
        page = self.rendered(publish(self.a_deal().name))

        self.assertNotIn("Hiệu lực đến", page)

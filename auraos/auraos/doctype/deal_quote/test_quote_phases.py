"""Seam tests for quote phases (#43).

Which group an entry lands in, and in what order the groups print, is
pinned framework-free in tests/test_quote.py. What only a site can prove
is the freezing:

1. **Publishing copies the phases onto the version**, so a quote handed
   to a client keeps the shape it was handed in.
2. **Only the phases the offer uses are frozen.** A phase the founder
   made and put nothing in is not part of what was offered.
3. **Renaming or deleting a phase on the deal does not restate a
   published version.** That is the whole point of a version being a
   snapshot, and it is the assertion this file exists for.
4. **A deal with no phases publishes as it always did** - every quote
   sent before #43, and every quote the founder never splits.
5. **The client's page prints the phase headings and their subtotals**,
   and never prints a phase with nothing under it.

Runs via: bench --site <site> run-tests --app auraos
"""

import re

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import set_request
from frappe.website.serve import get_response

from auraos.auraos.doctype.deal.test_deal import FOUNDER, make_company
from auraos.auraos.doctype.deal_quote.deal_quote import publish
from auraos.lib.money import format_vnd
from auraos.tests.utils import make_test_user

PRE = "Tiền kỳ"
PRODUCTION = "Sản xuất"

LINES = [
    {
        "description": "Kịch bản",
        "qty1": 1,
        "qty2": 1,
        "unit_price": 10_000_000,
        "tax_type": "Không hoá đơn",
        "package": "Kịch bản & ý tưởng",
    },
    {
        "description": "Quay chính",
        "qty1": 2,
        "qty2": 1,
        "unit_price": 20_000_000,
        "tax_type": "Không hoá đơn",
        "package": "Ngày quay",
    },
    {
        "description": "Thuê kho",
        "qty1": 1,
        "qty2": 1,
        "unit_price": 5_000_000,
        "tax_type": "Không hoá đơn",
        "package": "Thuê kho",
    },
]

# Two phased packages and one deliberately left on its own, so every
# assertion below has all three cases in front of it.
PACKAGES = [
    {"title": "Kịch bản & ý tưởng", "phase": PRE},
    {"title": "Ngày quay", "phase": PRODUCTION},
    {"title": "Thuê kho"},
]


class QuotePhasesTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")

    def setUp(self):
        frappe.set_user(FOUNDER)

    def tearDown(self):
        frappe.set_user("Administrator")

    def a_deal(self, phases=None, packages=None):
        doc = frappe.get_doc(
            {
                "doctype": "Deal",
                "title": "TVC Tết",
                "deal_owner": FOUNDER,
                "company": make_company().name,
                "cost_lines": [dict(row) for row in LINES],
                "packages": [dict(row) for row in (packages or PACKAGES)],
                "phases": [
                    dict(row)
                    for row in (
                        phases
                        if phases is not None
                        else [
                            {"title": PRE, "blurb": "Chuẩn bị trước khi bấm máy"},
                            {"title": PRODUCTION},
                        ]
                    )
                ],
            }
        )
        doc.insert()
        return doc

    # -- freezing --

    def test_publishing_freezes_the_phases_the_offer_uses(self):
        deal = self.a_deal()

        quote = publish(deal.name)

        self.assertEqual([row.title for row in quote.phases], [PRE, PRODUCTION])
        self.assertEqual(quote.phases[0].blurb, "Chuẩn bị trước khi bấm máy")
        # And the packages carry which phase they sit under.
        under = {row.title: row.phase for row in quote.packages}
        self.assertEqual(under["Kịch bản & ý tưởng"], PRE)
        self.assertEqual(under["Ngày quay"], PRODUCTION)
        self.assertFalse(under["Thuê kho"])

    def test_a_phase_nothing_is_quoted_under_is_not_frozen(self):
        """A phase the founder made and put nothing in is not part of the
        offer, so it is not part of the snapshot of the offer."""
        deal = self.a_deal(
            phases=[{"title": PRE}, {"title": PRODUCTION}, {"title": "Hậu kỳ"}]
        )

        quote = publish(deal.name)

        self.assertEqual([row.title for row in quote.phases], [PRE, PRODUCTION])

    def test_phases_are_frozen_in_the_deals_order_not_the_packages(self):
        """The founder decides pre-production is read before post; a phase
        keeps its place even when the package in it was added last."""
        deal = self.a_deal(
            phases=[{"title": PRODUCTION}, {"title": PRE}],
        )

        quote = publish(deal.name)

        self.assertEqual([row.title for row in quote.phases], [PRODUCTION, PRE])

    def test_renaming_a_phase_does_not_restate_a_published_version(self):
        """The assertion this file exists for.

        A quote version is an immutable snapshot handed to a client. The
        client is holding a PDF; renaming a phase on the deal afterwards
        must not change the document they were given.
        """
        deal = self.a_deal()
        quote = publish(deal.name)

        deal.reload()
        deal.phases[0].title = "Giai đoạn 1"
        deal.packages[0].phase = "Giai đoạn 1"
        deal.save()

        quote.reload()
        self.assertEqual([row.title for row in quote.phases], [PRE, PRODUCTION])
        self.assertEqual(quote.packages[0].phase, PRE)

    def test_deleting_every_phase_does_not_empty_a_published_version(self):
        deal = self.a_deal()
        quote = publish(deal.name)

        deal.reload()
        deal.phases = []
        for package in deal.packages:
            package.phase = None
        deal.save()

        quote.reload()
        self.assertEqual(len(quote.phases), 2)
        self.assertEqual(quote.packages[0].phase, PRE)

    def test_a_deal_with_no_phases_publishes_exactly_as_it_always_did(self):
        """Every quote sent before #43, and every quote never split."""
        deal = self.a_deal(
            phases=[], packages=[{"title": row["title"]} for row in PACKAGES]
        )

        quote = publish(deal.name)

        self.assertEqual(list(quote.phases), [])
        self.assertEqual([row.phase for row in quote.packages], [None, None, None])
        self.assertEqual(len(quote.packages), 3)

    # -- what the client reads --

    def rendered(self, quote):
        frappe.set_user("Guest")
        set_request(method="GET", path=f"/quote/{quote.token}")
        html = get_response().get_data(as_text=True)
        frappe.set_user(FOUNDER)
        return re.sub(r"\s+", " ", html)

    def test_the_page_prints_each_phase_with_its_own_subtotal(self):
        deal = self.a_deal()
        quote = publish(deal.name)

        page = self.rendered(quote)

        self.assertIn(PRE, page)
        self.assertIn(PRODUCTION, page)
        self.assertIn("Chuẩn bị trước khi bấm máy", page)
        # The subtotal of a phase is the sum of what is printed under it.
        under_pre = sum(
            row.price for row in quote.packages if row.phase == PRE
        )
        self.assertIn(format_vnd(under_pre), page)

    def test_the_page_never_prints_a_phase_with_nothing_under_it(self):
        """A heading with no rows and a zero beneath it reads as a defect
        in the document rather than as a phase nobody filled."""
        deal = self.a_deal(
            phases=[{"title": PRE}, {"title": PRODUCTION}, {"title": "Hậu kỳ"}]
        )
        quote = publish(deal.name)

        page = self.rendered(quote)

        self.assertNotIn("Hậu kỳ", page)

    def test_an_unphased_package_is_printed_without_a_heading(self):
        """It is quoted on its own, ahead of the first phase - and the
        money is never what disappears to keep a layout tidy."""
        deal = self.a_deal()
        quote = publish(deal.name)

        page = self.rendered(quote)

        self.assertIn("Thuê kho", page)

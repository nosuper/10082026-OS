"""Seam tests for the cross-deal quote list (auraos.api.quotation_list).

The row shaping is pinned framework-free in tests/test_reporting.py.
What only a site can prove is the wiring:

1. **Every version, across every deal.** Publishing again makes a new
   version, and both show up in one call - the answer a deal-by-deal
   list cannot give.
2. **The scope is the entire authorization.** Deal Quote rows are read
   with get_all, which skips row-level permissions, so the list is
   scoped to the deals the session may list and an outsider reads
   nothing at all.
3. **Tracking arrives as fields.** Opens and downloads are counted
   apart against the real open log, and a never-opened version comes
   back as zeros rather than as a missing key.
4. **Nothing founder-only rides along.** A producer session gets the
   same rows, and none of them carries commission, CM or the profit
   chain.
5. **The row is a contract** (issue #83). Now that a separate React
   frontend reads these rows over HTTP, the key set, the integer đồng
   and the date types are asserted as an interface rather than left to
   whatever the endpoint happens to return.

Runs via: bench --site <site> run-tests --app auraos
"""

from datetime import datetime

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import mark_quote_confirmed, mark_quote_sent, publish_quote, quotation_list
from auraos.auraos.doctype.deal.test_deal import make_company
from auraos.auraos.doctype.deal_quote.deal_quote import record_open
from auraos.auraos.doctype.deal_quote.test_deal_quote import (
    FOUNDER,
    OUTSIDER,
    PRODUCER,
    make_quotable_deal,
)
from auraos.tests.contract import (
    FOUNDER_ONLY,
    assert_counts,
    assert_keys,
    assert_money,
    assert_no_founder_chain,
)
from auraos.tests.utils import make_test_user

# Every key a row carries. Listed once: the boundary test proves a
# producer gets exactly this and no founder field, and the contract test
# proves the frontend gets exactly this and no renamed one.
ROW_KEYS = [
    "client",
    "company",
    "confirmed_on",
    "deal",
    "deal_title",
    "download_count",
    "last_opened_at",
    "name",
    "open_count",
    "published_on",
    "sent_on",
    "status",
    "total",
    "url",
    "version",
]


def rows_for(deal, **kwargs):
    """The list, narrowed to one deal - other tests publish quotes too."""
    return [row for row in quotation_list(**kwargs) if row["deal"] == deal]


class QuotationListTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")
        self.deal = make_quotable_deal()

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()


class TestQuotationList(QuotationListTestCase):
    def test_every_version_of_a_deal_is_listed_newest_first(self):
        """Three rounds of negotiation, three rows - the history the
        deal page shows, without having to open the deal."""
        for _ in range(3):
            publish_quote(self.deal.name)

        rows = rows_for(self.deal.name)
        self.assertEqual([row["version"] for row in rows], [3, 2, 1])

    def test_a_row_names_the_deal_and_the_client_it_belongs_to(self):
        quote = publish_quote(self.deal.name)

        (row,) = rows_for(self.deal.name)
        self.assertEqual(row["name"], quote["name"])
        self.assertEqual(row["deal_title"], self.deal.title)
        self.assertEqual(row["company"], self.deal.company)
        self.assertEqual(
            row["client"],
            frappe.db.get_value("Party Company", self.deal.company, "company_name"),
        )

    def test_a_row_carries_the_total_the_url_and_the_delivery_dates(self):
        quote = publish_quote(self.deal.name)
        mark_quote_sent(quote["name"])

        (row,) = rows_for(self.deal.name)
        self.assertEqual(row["total"], quote["total"])
        self.assertEqual(row["url"], quote["url"])
        self.assertEqual(row["status"], "Sent")
        self.assertIsNotNone(row["published_on"])
        self.assertIsNotNone(row["sent_on"])
        self.assertIsNone(row["confirmed_on"])

    def test_a_confirmed_quote_carries_the_date_it_was_signed(self):
        quote = publish_quote(self.deal.name)
        mark_quote_confirmed(quote["name"])

        (row,) = rows_for(self.deal.name)
        self.assertEqual(row["status"], "Confirmed")
        self.assertIsNotNone(row["confirmed_on"])

    def test_a_quote_nobody_opened_reads_as_zeros(self):
        publish_quote(self.deal.name)

        (row,) = rows_for(self.deal.name)
        self.assertEqual(row["open_count"], 0)
        self.assertEqual(row["download_count"], 0)
        self.assertIsNone(row["last_opened_at"])

    def test_opens_and_downloads_are_counted_apart(self):
        quote = publish_quote(self.deal.name)
        record_open(quote["name"], via="Page")
        record_open(quote["name"], via="Page")
        record_open(quote["name"], via="PDF")

        (row,) = rows_for(self.deal.name)
        self.assertEqual(row["open_count"], 2)
        self.assertEqual(row["download_count"], 1)
        self.assertIsNotNone(row["last_opened_at"])

    def test_each_version_keeps_its_own_opens(self):
        first = publish_quote(self.deal.name)
        second = publish_quote(self.deal.name)
        record_open(first["name"], via="Page")

        rows = {row["name"]: row for row in rows_for(self.deal.name)}
        self.assertEqual(rows[first["name"]]["open_count"], 1)
        self.assertEqual(rows[second["name"]]["open_count"], 0)


class TestQuotationListFilters(QuotationListTestCase):
    def test_the_status_filter_narrows_to_one_delivery_state(self):
        publish_quote(self.deal.name)
        sent = publish_quote(self.deal.name)
        mark_quote_sent(sent["name"])

        rows = rows_for(self.deal.name, status="Sent")
        self.assertEqual([row["name"] for row in rows], [sent["name"]])

    def test_a_search_finds_a_quote_by_its_deal_title(self):
        publish_quote(self.deal.name)

        self.assertTrue(rows_for(self.deal.name, search="brand film"))
        self.assertFalse(rows_for(self.deal.name, search="no such deal"))

    def test_a_search_finds_a_quote_by_its_client(self):
        other = make_quotable_deal(
            title="TVC Tết 2027",
            company=make_company("Nhất Minh Beverage").name,
        )
        publish_quote(self.deal.name)
        publish_quote(other.name)

        found = [row["deal"] for row in quotation_list(search="nhất minh")]
        self.assertIn(other.name, found)
        self.assertNotIn(self.deal.name, found)


class TestQuotationListBoundary(QuotationListTestCase):
    def test_the_producer_reads_the_list_and_none_of_the_profit_chain(self):
        """Quote delivery is the producer's job; the profit chain is not
        on the row for anybody."""
        publish_quote(self.deal.name)

        frappe.set_user(PRODUCER)
        (row,) = rows_for(self.deal.name)
        self.assertTrue(FOUNDER_ONLY.isdisjoint(row))
        assert_no_founder_chain(self, row, "producer quote row")
        assert_keys(self, row, ROW_KEYS, "producer quote row")

    def test_an_outsider_reads_no_quotes_at_all(self):
        publish_quote(self.deal.name)

        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            quotation_list()


class TestQuotationListContract(QuotationListTestCase):
    """The row as the React frontend receives it (issue #83, spec #81).

    Shape only. What a total *is* belongs to lib/quote and is pinned in
    tests/; what this file pins is that the total is still called
    `total` and still arrives as a number the frontend can print.
    """

    def test_the_row_carries_every_documented_key_and_no_other(self):
        publish_quote(self.deal.name)

        (row,) = rows_for(self.deal.name)
        assert_keys(self, row, ROW_KEYS, "quote row")

    def test_the_total_is_whole_dong_and_the_tallies_are_plain_counts(self):
        quote = publish_quote(self.deal.name)
        record_open(quote["name"], via="Page")

        (row,) = rows_for(self.deal.name)
        assert_money(self, row, "total", where="quote row")
        assert_counts(self, row, "version", "open_count", "download_count", where="quote row")

    def test_an_empty_result_is_an_empty_list_not_an_error(self):
        """A search that matches nothing is a normal afternoon, and a
        new company has published no quotes at all."""
        publish_quote(self.deal.name)

        rows = quotation_list(search="no client by this name exists")
        self.assertEqual(rows, [])

    def test_the_quote_stamps_cross_the_wire_as_iso_strings(self):
        """Spec #81 requires ISO strings on the wire.

        This test was written the other way round, pinning the bug it
        found: the endpoint passed the stored stamp straight out of
        get_all, so it left Python as a datetime and left Frappe's JSON
        encoder as `2026-08-13 16:45:26.952510` - a space where the T
        belongs, which not every browser's Date parser accepts. The
        finance reports already normalised. lib/reporting.iso now does
        the same here, and this test asserts the fix rather than the
        defect.
        """
        quote = publish_quote(self.deal.name)
        mark_quote_sent(quote["name"])
        record_open(quote["name"], via="Page")

        (row,) = rows_for(self.deal.name)
        for field in ("published_on", "sent_on", "last_opened_at"):
            self.assertIsInstance(row[field], str, f"{field} is not a string")
            datetime.fromisoformat(row[field])
        self.assertIsNone(row["confirmed_on"], "an unsigned quote has no signing date")

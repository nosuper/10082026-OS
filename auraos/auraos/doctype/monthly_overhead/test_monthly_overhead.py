"""Founder overhead entry and break-even dashboard seams (issue #14)."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import global_search

from auraos.api import break_even_dashboard, get_overhead_month, save_overhead_month
from auraos.tests.utils import make_test_user


FOUNDER = "overhead-founder@test.auraos.local"
PRODUCER = "overhead-producer@test.auraos.local"


def make_overhead(month, items):
    return frappe.get_doc(
        {
            "doctype": "Monthly Overhead",
            "month": month,
            "items": items,
        }
    ).insert(ignore_permissions=True)


def make_booked_job(title, margin, booked_at):
    company = frappe.get_doc(
        {
            "doctype": "Party Company",
            "company_name": f"{title} Client",
        }
    ).insert(ignore_permissions=True)
    job = frappe.get_doc(
        {
            "doctype": "Job",
            "title": title,
            "stage": "Pre-production",
            "job_owner": FOUNDER,
            "company": company.name,
            "quote_margin": margin,
        }
    ).insert(ignore_permissions=True)
    # Booking is the conversion that creates a Job. Backdate the framework
    # timestamp to exercise month boundaries without freezing the clock.
    frappe.db.set_value(
        "Job", job.name, "creation", booked_at, update_modified=False
    )
    return job


class TestMonthlyOverhead(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from frappe.desk.doctype.global_search_settings.global_search_settings import (
            update_global_search_doctypes,
        )

        update_global_search_doctypes()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def test_founder_records_recurring_and_one_off_items(self):
        frappe.set_user(FOUNDER)
        overhead = frappe.get_doc(
            {
                "doctype": "Monthly Overhead",
                "month": "2026-08-01",
                "items": [
                    {
                        "kind": "Recurring",
                        "category": "Rent",
                        "amount": 12_000_000,
                    },
                    {
                        "kind": "One-off",
                        "category": "Other",
                        "description": "Replace office air conditioner",
                        "amount": 3_500_000,
                    },
                ],
            }
        ).insert()

        saved = frappe.get_doc("Monthly Overhead", overhead.name)
        self.assertEqual(saved.total, 15_500_000)
        self.assertEqual([row.kind for row in saved.items], ["Recurring", "One-off"])

    def test_founder_saves_and_reopens_a_month_through_the_page_api(self):
        frappe.set_user(FOUNDER)
        saved = save_overhead_month(
            "2026-12-19",
            [
                {"kind": "Recurring", "category": "Rent", "amount": 2_000_000},
                {
                    "kind": "One-off",
                    "category": "Other",
                    "description": "Year-end repairs",
                    "amount": 750_000,
                },
            ],
        )
        reopened = get_overhead_month("2026-12-01")

        self.assertEqual(saved["month"], "2026-12-01")
        self.assertEqual(reopened["total"], 2_750_000)
        self.assertEqual(reopened["items"][1]["description"], "Year-end repairs")

    def test_producer_is_denied_document_and_rest_apis(self):
        from frappe.client import get, get_list

        overhead = make_overhead(
            "2026-09-01",
            [{"kind": "Recurring", "category": "Rent", "amount": 123_456}],
        )
        frappe.set_user(PRODUCER)

        self.assertFalse(frappe.has_permission("Monthly Overhead", "read"))
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc("Monthly Overhead", overhead.name).check_permission("read")
        with self.assertRaises(frappe.PermissionError):
            get("Monthly Overhead", name=overhead.name)
        with self.assertRaises(frappe.PermissionError):
            get_list("Monthly Overhead")
        with self.assertRaises(frappe.PermissionError):
            break_even_dashboard("2026-09-01")
        with self.assertRaises(frappe.PermissionError):
            get_overhead_month("2026-09-01")
        with self.assertRaises(frappe.PermissionError):
            save_overhead_month("2026-09-01", [])

    def test_producer_cannot_find_overhead_in_global_search(self):
        overhead = make_overhead(
            "2026-10-01",
            [
                {
                    "kind": "One-off",
                    "category": "Other",
                    "description": "Private office repair",
                    "amount": 654_321,
                }
            ],
        )
        global_search.sync_global_search()

        frappe.set_user(FOUNDER)
        found = [
            row
            for row in global_search.search(overhead.title)
            if row.get("doctype") == "Monthly Overhead"
        ]
        self.assertTrue(
            any(row.get("name") == overhead.name for row in found),
            "positive control failed: founder should find the overhead month",
        )

        frappe.set_user(PRODUCER)
        leaked = [
            row
            for row in global_search.search(overhead.title)
            if row.get("doctype") == "Monthly Overhead"
        ]
        self.assertEqual(leaked, [])


class TestBreakEvenDashboard(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def test_aggregates_only_the_selected_months_overhead_and_booked_jobs(self):
        make_overhead(
            "2026-07-01",
            [{"kind": "Recurring", "category": "Salaries", "amount": 9_000_000}],
        )
        make_overhead(
            "2026-08-01",
            [
                {"kind": "Recurring", "category": "Rent", "amount": 1_000_000},
                {"kind": "One-off", "category": "Other", "amount": 500_000},
            ],
        )
        make_booked_job("July job", 20_000_000, "2026-07-20 12:00:00")
        make_booked_job("August job one", 2_000_000, "2026-08-02 12:00:00")
        make_booked_job("August job two", 1_000_000, "2026-08-31 23:59:59")

        frappe.set_user(FOUNDER)
        july = break_even_dashboard("2026-07-01")
        august = break_even_dashboard("2026-08-19")

        self.assertEqual(july["overhead"], 9_000_000)
        self.assertEqual(july["booked_margin"], 20_000_000)
        self.assertEqual(july["surplus"], 11_000_000)
        self.assertEqual(july["shortfall"], 0)
        self.assertEqual(august["month"], "2026-08-01")
        self.assertEqual(august["overhead"], 1_500_000)
        self.assertEqual(august["booked_margin"], 3_000_000)
        self.assertEqual(august["contribution"], 1_500_000)
        self.assertEqual(august["job_count"], 2)

    def test_shortfall_is_shown_as_a_positive_amount(self):
        make_overhead(
            "2026-11-01",
            [{"kind": "Recurring", "category": "Utilities", "amount": 4_000_000}],
        )
        make_booked_job("November job", 1_500_000, "2026-11-10 12:00:00")

        frappe.set_user(FOUNDER)
        result = break_even_dashboard("2026-11-01")

        self.assertEqual(result["contribution"], -2_500_000)
        self.assertEqual(result["shortfall"], 2_500_000)
        self.assertEqual(result["surplus"], 0)

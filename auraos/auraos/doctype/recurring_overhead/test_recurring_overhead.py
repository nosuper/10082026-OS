"""Seam tests for standing costs and the payments they become (#14).

The arithmetic - which months are due, where the 31st lands in February,
what a range commits the company to - is pinned framework-free in
tests/test_recurring.py. What only a site can prove is here:

1. **Confirming a month writes a real payment that posts to the cash
   ledger.** A standing cost is a template; the founder's confirmation
   is what turns it into money that moved, and the movement has to reach
   the account the same way a hand-entered overhead's does.
2. **A month already recorded is skipped, not written twice.** Two
   clicks on a slow connection must not become two rents, and the guard
   has to hold at the database rather than in the browser.
3. **Deleting the payment makes the month due again**, because recorded
   is a fact about the payments and there is no stamp on the template to
   go stale.
4. **The amount is re-derived from the record, never trusted from the
   caller** - this writes to the cash ledger, so a browser that could
   post its own figure could post any figure.
5. **A producer cannot see or reach any of it** - not through the ORM,
   not through the REST layer, not through the endpoints - because #14
   asks for invisible via UI, API and search, and that is a permission
   matrix rather than an endpoint check. There is deliberately no
   Producer row on the doctype.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos import api
from auraos.auraos.doctype.deal.test_deal import FOUNDER, PRODUCER
from auraos.lib import ledger
from auraos.tests.utils import make_test_user

CATEGORY = "Thuê văn phòng"
ACCOUNT = "Tài khoản ngân hàng"

# Far enough back that every month of it has started, so `due` offers
# them all and the tests never depend on what today happens to be.
STARTED_ON = "2020-01-01"


def months_back(count):
    """The first days of the `count` whole months before this one.

    Relative rather than written out, because a suite that named 2026
    would pass today and start failing on a clock that had not moved -
    the failure that reads as a bug in the feature. Whole months only:
    the current one is left out so a run on the 1st and a run on the 31st
    see the same window.
    """
    this_month = frappe.utils.get_first_day(frappe.utils.today())
    return [
        frappe.utils.getdate(frappe.utils.add_months(this_month, -back))
        for back in range(count, 0, -1)
    ]


class RecurringOverheadTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        if not frappe.db.exists("Company Expense Category", CATEGORY):
            frappe.get_doc(
                {"doctype": "Company Expense Category", "category_name": CATEGORY}
            ).insert(ignore_permissions=True)
        if not frappe.db.exists("Cash Account", ACCOUNT):
            frappe.get_doc(
                {"doctype": "Cash Account", "account_name": ACCOUNT}
            ).insert(ignore_permissions=True)

    def setUp(self):
        frappe.set_user(FOUNDER)
        # Three whole months, the newest of which has certainly started.
        # `months` are their first days, `keys` the 2026-08 form the
        # payload speaks in, and the middle one is the month these tests
        # record - so there is a month either side of it to prove the
        # backlog shrinks by exactly one.
        self.months = months_back(3)
        self.keys = [day.strftime("%Y-%m") for day in self.months]

    def tearDown(self):
        frappe.set_user("Administrator")

    # -- fixtures --

    def template(self, **values):
        doc = frappe.get_doc(
            {
                "doctype": "Recurring Overhead",
                "label": "Tiền thuê văn phòng",
                "amount": 30_000_000,
                "category": CATEGORY,
                "paid_from": ACCOUNT,
                "day_of_month": 5,
                "starts_on": STARTED_ON,
                **values,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc

    def entry_for(self, expense_name):
        return frappe.db.get_value(
            "Cash Ledger Entry",
            ledger.entry_name(ledger.COMPANY_EXPENSE, expense_name),
            ["amount", "flow", "account"],
            as_dict=True,
        )

    def due_months(self, template_name):
        """The months waiting for this template, over the fixed window."""
        return [
            row["month"]
            for row in api.overheads_due(self.months[0], self.months[-1])["rows"]
            if row["template"] == template_name
        ]

    # -- confirming a month writes a payment, and the payment posts --

    def test_confirming_a_month_writes_a_payment_that_posts_to_the_ledger(self):
        """The whole point of the flow: twelve forms a year become twelve
        clicks, and each click is a real payment rather than a note."""
        doc = self.template()

        result = api.record_recurring_overheads(
            [{"template": doc.name, "month": self.keys[1]}]
        )

        self.assertEqual(len(result["written"]), 1)
        written = result["written"][0]
        expense = frappe.get_doc("Company Expense", written["name"])
        self.assertEqual(expense.amount, 30_000_000)
        self.assertEqual(
            expense.spent_on, frappe.utils.add_days(self.months[1], 4)
        )
        self.assertEqual(expense.category, CATEGORY)
        self.assertEqual(expense.recurring, doc.name)
        self.assertEqual(expense.recurring_month, self.keys[1])
        # The description reads the way the founder named the cost, not
        # "RO-00001".
        self.assertEqual(expense.description, "Tiền thuê văn phòng")

        entry = self.entry_for(expense.name)
        self.assertIsNotNone(entry, "a confirmed standing cost posted nothing")
        self.assertEqual(entry.amount, -30_000_000)
        self.assertEqual(entry.flow, ledger.COMPANY_EXPENSE)
        self.assertEqual(entry.account, ACCOUNT)

    def test_the_thirty_first_lands_inside_february(self):
        """A payment stays inside the month it covers.

        Rolled forward, February's rent would be filed in March and
        February would read short on the break-even screen for a reason
        nobody could see.
        """
        doc = self.template(day_of_month=31)

        api.record_recurring_overheads([{"template": doc.name, "month": self.keys[1]}])

        expense = frappe.get_doc(
            "Company Expense", {"recurring": doc.name, "recurring_month": self.keys[1]}
        )
        # The last day of that month, whichever month the clock makes it -
        # which is the whole of the rule, and a hard-coded 28 would only
        # test it in February.
        self.assertEqual(
            expense.spent_on, frappe.utils.getdate(frappe.utils.get_last_day(self.months[1]))
        )

    # -- recorded once, and only once --

    def test_a_month_already_recorded_is_skipped_rather_than_doubled(self):
        """Two clicks on a slow connection must not become two rents.

        Skipped rather than refused, so one already-written line cannot
        stop the founder recording the other eleven - and reported, so
        the screen can say what happened rather than quietly showing
        fewer rows than were ticked.
        """
        doc = self.template()
        rows = [{"template": doc.name, "month": self.keys[1]}]

        first = api.record_recurring_overheads(rows)
        second = api.record_recurring_overheads(rows)

        self.assertEqual(len(first["written"]), 1)
        self.assertEqual(second["written"], [])
        self.assertEqual(second["skipped"], [{"template": doc.name, "month": self.keys[1]}])
        self.assertEqual(
            frappe.db.count(
                "Company Expense", {"recurring": doc.name, "recurring_month": self.keys[1]}
            ),
            1,
        )

    def test_a_recorded_month_stops_coming_due_and_a_deleted_one_starts_again(self):
        """Recorded is a fact about the payments, so there is nothing to
        reset when one is deleted - and the month has genuinely not been
        paid for after all."""
        doc = self.template()
        self.assertEqual(self.due_months(doc.name), self.keys)

        api.record_recurring_overheads([{"template": doc.name, "month": self.keys[1]}])
        self.assertEqual(self.due_months(doc.name), [self.keys[0], self.keys[2]])

        expense = frappe.db.get_value(
            "Company Expense", {"recurring": doc.name, "recurring_month": self.keys[1]}
        )
        api.delete_company_expense(expense)
        self.assertEqual(self.due_months(doc.name), self.keys)
        # And the movement came back out with it, so the account balance
        # and the bank statement stay in step.
        self.assertIsNone(self.entry_for(expense))

    def test_the_amount_comes_off_the_record_and_not_off_the_request(self):
        """This writes to the cash ledger.

        A caller who could post their own figure could post any figure,
        so the endpoint re-reads the template at the moment of writing
        and ignores anything else the browser sent.
        """
        doc = self.template(amount=30_000_000)

        api.record_recurring_overheads(
            [{"template": doc.name, "month": self.keys[1], "amount": 1}]
        )

        expense = frappe.get_doc(
            "Company Expense", {"recurring": doc.name, "recurring_month": self.keys[1]}
        )
        self.assertEqual(expense.amount, 30_000_000)

    def test_a_pair_missing_its_month_is_refused(self):
        doc = self.template()
        with self.assertRaises(frappe.ValidationError):
            api.record_recurring_overheads([{"template": doc.name}])

    # -- the record's own rules --

    def test_a_last_month_before_the_first_is_refused(self):
        """Reversed, the template runs in no month at all - a template
        that silently does nothing, which is the failure that looks like
        a feature working quietly."""
        with self.assertRaises(frappe.ValidationError):
            self.template(starts_on="2026-06-01", ends_on="2026-01-01")

    def test_a_standing_cost_needs_an_amount(self):
        with self.assertRaises(frappe.ValidationError):
            self.template(amount=0)

    def test_changing_the_amount_does_not_restate_a_payment_already_made(self):
        """The figure on the template is what the company is committed to
        from now on. A month that came out different is corrected on that
        month's payment, beside the money it changed."""
        doc = self.template()
        api.record_recurring_overheads([{"template": doc.name, "month": self.keys[1]}])

        doc.amount = 45_000_000
        doc.save(ignore_permissions=True)

        expense = frappe.get_doc(
            "Company Expense", {"recurring": doc.name, "recurring_month": self.keys[1]}
        )
        self.assertEqual(expense.amount, 30_000_000)

    def test_a_paused_template_stops_coming_due_without_losing_its_history(self):
        doc = self.template()
        api.record_recurring_overheads([{"template": doc.name, "month": self.keys[1]}])

        doc.disabled = 1
        doc.save(ignore_permissions=True)

        self.assertEqual(self.due_months(doc.name), [])
        self.assertTrue(
            frappe.db.exists(
                "Company Expense", {"recurring": doc.name, "recurring_month": self.keys[1]}
            )
        )

    # -- the write door is a whitelist --

    def test_a_field_outside_the_whitelist_is_refused_by_name(self):
        """A whitelisted method's arguments are whatever the caller sends.

        Refused rather than ignored, so a caller learns that their field
        did nothing instead of believing it worked.
        """
        with self.assertRaises(frappe.ValidationError):
            api.save_recurring_overhead(
                {"label": "Lương", "amount": 1_000_000, "starts_on": STARTED_ON,
                 "for_depreciation": 1}
            )

    def test_a_template_with_payments_against_it_cannot_be_deleted(self):
        """The guard, not an obstacle to work around.

        `Company Expense.recurring` is a Link, so Frappe refuses to
        orphan one - and it should: a rent whose origin had been deleted
        is a payment nobody can trace back to the agreement it came from.
        A cost that genuinely stopped gets a last month instead, which is
        why `ends_on` exists beside `disabled`.
        """
        doc = self.template()
        api.record_recurring_overheads([{"template": doc.name, "month": self.keys[1]}])

        with self.assertRaises(frappe.LinkExistsError):
            api.delete_recurring_overhead(doc.name)

        # And ending it does what deleting was reached for, without
        # throwing the history away.
        doc.ends_on = frappe.utils.get_last_day(self.months[1])
        doc.save(ignore_permissions=True)
        self.assertEqual(self.due_months(doc.name), [self.keys[0]])

    def test_the_founder_can_write_one_through_the_endpoint(self):
        saved = api.save_recurring_overhead(
            {"label": "Adobe", "amount": 1_200_000, "starts_on": STARTED_ON}
        )
        self.assertEqual(saved["label"], "Adobe")
        self.assertEqual(saved["amount"], 1_200_000)

        amended = api.save_recurring_overhead({"amount": 1_500_000}, name=saved["name"])
        self.assertEqual(amended["amount"], 1_500_000)

        api.delete_recurring_overhead(saved["name"])
        self.assertFalse(frappe.db.exists("Recurring Overhead", saved["name"]))

    # -- invisible to the producer, via UI, API and search --

    def test_a_producer_cannot_read_a_standing_cost(self):
        """#14's third criterion, at the layer that decides it.

        There is no Producer row in the doctype's permissions, so this is
        refused by the framework rather than by any endpoint of ours -
        which is what makes it true of the REST API and the awesome bar
        as well as of a screen we wrote. This table is the payroll and
        the rent.
        """
        doc = self.template()
        frappe.set_user(PRODUCER)

        self.assertFalse(frappe.has_permission("Recurring Overhead", "read"))
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc("Recurring Overhead", doc.name).check_permission("read")
        # get_list is what the awesome bar and every list view go
        # through, and it **refuses** rather than answering an empty
        # list. The stronger of the two, and worth asserting as the
        # stronger: an empty list is what a producer would also get from
        # a table that happened to have no rows in it that day, so a
        # suite that accepted one would go green on a site where the
        # permission had been deleted and the rent not yet entered.
        with self.assertRaises(frappe.PermissionError):
            frappe.get_list("Recurring Overhead", ignore_permissions=False)

    def test_a_producer_is_refused_by_every_endpoint_in_the_flow(self):
        """The second lock, for the reads that skip permissions.

        `frappe.get_all` bypasses the matrix by design and break-even
        reads every job in the site, so a check that lived only in the
        doctype would not cover these doors.
        """
        doc = self.template()
        frappe.set_user(PRODUCER)

        refused = [
            lambda: api.recurring_overheads(),
            lambda: api.overheads_due(),
            lambda: api.save_recurring_overhead({"label": "x", "amount": 1}),
            lambda: api.delete_recurring_overhead(doc.name),
            lambda: api.record_recurring_overheads(
                [{"template": doc.name, "month": self.keys[1]}]
            ),
            lambda: api.overhead_log("2026-01-01", "2026-12-31"),
            lambda: api.log_company_expense(1_000_000),
            lambda: api.update_company_expense("CE-2026-00001", 1_000_000),
            lambda: api.delete_company_expense("CE-2026-00001"),
            lambda: api.company_expense_categories(),
            lambda: api.break_even("2026-01-01", "2026-12-31"),
        ]
        for call in refused:
            with self.assertRaises(frappe.PermissionError):
                call()

    def test_the_founder_can_reach_them_all(self):
        """The other half of the same assertion: a gate that refused
        everybody would pass the test above and be useless."""
        doc = self.template()
        frappe.set_user(FOUNDER)

        self.assertIn(doc.name, [row["name"] for row in api.recurring_overheads()["rows"]])
        self.assertIn(doc.name, [row["template"] for row in api.overheads_due()["rows"]])
        self.assertIn("months", api.break_even("2026-01-01", "2026-12-31"))
        self.assertIn("rows", api.overhead_log("2026-01-01", "2026-12-31"))

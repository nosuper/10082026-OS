"""Contract tests for what the company holds (#101, spec #81).

The arithmetic is pinned framework-free in tests/test_ledger.py. This
file is the other seam: the payload the React screen reads, and the four
things only a database can show.

1. **A balance is derived, every time it is asked for.** Checked against
   the database's own sum of the amount column, not against a figure
   this app wrote down - because there is no figure this app wrote down.
   Nothing on Cash Account stores one, neither endpoint takes an
   argument that could set one, and the doctype that holds the rows
   grants write to no operating role.
2. **Zero is an answer, not an error.** An account nothing has been
   posted against holds 0, and a studio that has never named an account
   reads as an empty list and a total of 0 - the same silence #99 chose
   when a collection has nowhere to post to.
3. **An origin becomes a source a human recognises.** The stored pair is
   a doctype and a name; what comes down the wire is the milestone,
   expense or float it names, with the job resolved to its title.
4. **The ledger is the founder's.** A producer is refused by the server,
   and refused because the Cash Ledger Entry doctype refuses them -
   never because a screen decided not to ask.

Runs via: bench --site <site> run-tests --app auraos
"""

import inspect

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import (
    cash_account_entries,
    cash_accounts,
    create_job_from_deal,
    log_job_expense,
    record_job_advance,
    set_milestone_status,
    settle_job,
)
from auraos.auraos.doctype.cash_account.cash_account import DEFAULT_FIELD
from auraos.auraos.doctype.cash_ledger_entry import cash_ledger_entry
from auraos.auraos.doctype.deal.test_deal import FOUNDER, PRODUCER, make_company
from auraos.auraos.doctype.job.test_job import won_deal
from auraos.lib import ledger
from auraos.lib.milestones import INVOICED, PAID
from auraos.lib.settlement import FROM_ADVANCE, FROM_COMPANY
from auraos.tests.contract import (
    assert_counts,
    assert_iso_date,
    assert_keys,
    assert_money,
)
from auraos.tests.utils import make_test_user

BANK = "Vietcombank - main"
CASH_BOX = "Két tiền mặt"

# One of the categories won_deal() quotes, so an expense may name it.
CATEGORY = "Thiết bị"

REPORT_KEYS = ["accounts", "total", "count"]
ACCOUNT_KEYS = ["name", "account_name", "note", "balance", "count", "is_default"]
ENTRIES_KEYS = ["account", "account_name", "balance", "count", "entries"]
ENTRY_KEYS = [
    "name",
    "entry_date",
    "amount",
    "direction",
    "flow",
    "source",
    "source_doctype",
    "source_name",
    "job",
    "job_title",
]


class CashAccountsTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")

    def setUp(self):
        frappe.set_user("Administrator")
        self.clear_accounts()
        make_company()
        self.job = frappe.get_doc("Job", create_job_from_deal(won_deal().name)["name"])
        self.deposit = self.job.payment_milestones[0]

    def tearDown(self):
        frappe.set_user("Administrator")
        self.clear_accounts()
        super().tearDown()

    def clear_accounts(self):
        """A studio that has never named an account - the starting state."""
        for entry in frappe.get_all("Cash Ledger Entry", pluck="name"):
            frappe.delete_doc("Cash Ledger Entry", entry, force=True)
        frappe.db.set_single_value("AuraOS Settings", DEFAULT_FIELD, None)
        for account in frappe.get_all("Cash Account", pluck="name"):
            frappe.delete_doc("Cash Account", account, force=True)

    def make_account(self, name=BANK):
        return frappe.get_doc(
            {"doctype": "Cash Account", "account_name": name}
        ).insert()

    def collect(self, account=None):
        return set_milestone_status(
            self.job.name, self.deposit.name, PAID, account=account
        )

    def spend(self, amount=3_000_000, paid_from=FROM_COMPANY, **fields):
        return log_job_expense(
            self.job.name, amount, category=CATEGORY, paid_from=paid_from, **fields
        )

    def row_for(self, report, account=BANK):
        (row,) = [row for row in report["accounts"] if row["name"] == account]
        return row

    def summed_in_the_database(self, account=BANK):
        """The sum of the amount column, asked of the database itself.

        The independent check: if the endpoint's figure ever came from
        anywhere but the rows, this is what would disagree with it.
        """
        total = frappe.db.sql(
            "select sum(amount) from `tabCash Ledger Entry` where account = %s",
            account,
        )[0][0]
        return int(total or 0)


class TestTheShapeOfWhatWeHold(CashAccountsTestCase):
    def test_the_report_has_exactly_the_documented_keys(self):
        self.make_account()

        assert_keys(self, cash_accounts(), REPORT_KEYS)

    def test_an_account_row_has_exactly_the_documented_keys(self):
        self.make_account()

        assert_keys(self, self.row_for(cash_accounts()), ACCOUNT_KEYS, "account")

    def test_money_crosses_the_wire_as_whole_dong(self):
        self.make_account()
        self.collect()

        report = cash_accounts()

        assert_money(self, report, "total")
        assert_money(self, self.row_for(report), "balance", where="account")
        assert_counts(self, report, "count")
        assert_counts(self, self.row_for(report), "count", where="account")

    def test_the_default_account_is_named_on_the_row_not_guessed_by_the_screen(self):
        self.make_account()
        self.make_account(CASH_BOX)

        report = cash_accounts()

        self.assertTrue(self.row_for(report, BANK)["is_default"])
        self.assertFalse(self.row_for(report, CASH_BOX)["is_default"])


class TestABalanceIsDerived(CashAccountsTestCase):
    def test_a_balance_is_the_sum_of_the_accounts_entries(self):
        self.make_account()
        self.collect()
        self.spend()

        row = self.row_for(cash_accounts())

        self.assertEqual(row["balance"], self.summed_in_the_database())
        self.assertEqual(
            row["balance"], ledger.balance(cash_ledger_entry.entries_for(BANK))
        )
        self.assertEqual(row["balance"], self.deposit.amount - 3_000_000)
        self.assertEqual(row["count"], 2)

    def test_the_total_is_every_account_added_up(self):
        self.make_account()
        self.make_account(CASH_BOX)
        self.collect(account=CASH_BOX)
        self.spend()

        report = cash_accounts()

        self.assertEqual(
            report["total"],
            self.row_for(report, BANK)["balance"]
            + self.row_for(report, CASH_BOX)["balance"],
        )
        self.assertEqual(report["total"], self.deposit.amount - 3_000_000)
        self.assertEqual(report["count"], 2)

    def test_the_same_dong_is_counted_once(self):
        """An advance spent out of a float left the company when it was handed
        over; the balance is not 10M and 12M out, it is 12M out."""
        self.make_account()
        record_job_advance(self.job.name, PRODUCER, 10_000_000)
        self.spend(amount=12_000_000, paid_from=FROM_ADVANCE, paid_by=PRODUCER)
        settle_job(self.job.name, PRODUCER)

        self.assertEqual(self.row_for(cash_accounts())["balance"], -12_000_000)

    def test_a_movement_walked_back_takes_its_money_with_it(self):
        """The figure follows the ledger down as well as up - which is what
        derived means, and what a stored total would not do."""
        self.make_account()
        self.collect()
        self.assertEqual(self.row_for(cash_accounts())["balance"], self.deposit.amount)

        set_milestone_status(self.job.name, self.deposit.name, INVOICED)

        self.assertEqual(self.row_for(cash_accounts())["balance"], 0)
        self.assertEqual(self.summed_in_the_database(), 0)

    def test_nothing_on_a_cash_account_stores_a_balance(self):
        """An account is a name and a note. There is no column to type into."""
        fields = {field.fieldname for field in frappe.get_meta("Cash Account").fields}

        self.assertEqual(fields, {"account_name", "note"})

    def test_neither_endpoint_accepts_a_figure(self):
        """A balance cannot be passed in, so it cannot be argued with."""
        self.assertEqual(list(inspect.signature(cash_accounts).parameters), [])
        self.assertEqual(
            list(inspect.signature(cash_account_entries).parameters), ["account"]
        )

    def test_not_even_the_founder_may_write_a_ledger_entry(self):
        """The rows a balance is made of are out of everybody's hands."""
        frappe.set_user(FOUNDER)

        self.assertFalse(frappe.has_permission("Cash Ledger Entry", "create"))
        self.assertFalse(frappe.has_permission("Cash Ledger Entry", "write"))
        self.assertFalse(frappe.has_permission("Cash Ledger Entry", "delete"))


class TestNothingHasHappenedYet(CashAccountsTestCase):
    def test_an_account_with_no_entries_holds_zero(self):
        self.make_account()

        row = self.row_for(cash_accounts())

        self.assertEqual(row["balance"], 0)
        self.assertEqual(row["count"], 0)

    def test_its_movements_are_an_empty_list_not_a_failure(self):
        self.make_account()

        payload = cash_account_entries(BANK)

        self.assertEqual(payload["entries"], [])
        self.assertEqual(payload["balance"], 0)
        self.assertEqual(payload["count"], 0)

    def test_a_company_that_has_named_no_account_reads_as_zero(self):
        report = cash_accounts()

        self.assertEqual(report["accounts"], [])
        self.assertEqual(report["total"], 0)
        self.assertEqual(report["count"], 0)

    def test_an_account_nobody_ever_created_is_refused(self):
        """A typo is not a company that keeps no accounts."""
        with self.assertRaises(frappe.DoesNotExistError):
            cash_account_entries("Bank of Nowhere")


class TestOneAccountsMovements(CashAccountsTestCase):
    def setUp(self):
        super().setUp()
        self.make_account()

    def test_the_payload_has_exactly_the_documented_keys(self):
        assert_keys(self, cash_account_entries(BANK), ENTRIES_KEYS)

    def test_an_entry_has_exactly_the_documented_keys(self):
        self.collect()

        (entry,) = cash_account_entries(BANK)["entries"]

        assert_keys(self, entry, ENTRY_KEYS, "entry")
        assert_money(self, entry, "amount", where="entry")
        assert_iso_date(self, entry["entry_date"], "entry.entry_date")

    def test_an_entry_reads_as_the_record_it_came_from(self):
        """Not as a doctype and a hash, which is what it is stored as."""
        self.collect()

        (entry,) = cash_account_entries(BANK)["entries"]

        self.assertEqual(entry["source"], self.deposit.title)
        self.assertNotIn(entry["source_doctype"], entry["source"])
        self.assertNotIn(entry["source_name"], entry["source"])

    def test_an_entry_names_the_job_it_happened_on_by_title(self):
        self.collect()

        (entry,) = cash_account_entries(BANK)["entries"]

        self.assertEqual(entry["job"], self.job.name)
        self.assertEqual(entry["job_title"], self.job.title)

    def test_money_out_reads_as_out_and_carries_the_minus_sign(self):
        self.spend(description="Thuê ống kính Sigma")

        (entry,) = cash_account_entries(BANK)["entries"]

        self.assertEqual(entry["direction"], ledger.OUT)
        self.assertEqual(entry["amount"], -3_000_000)
        self.assertEqual(entry["flow"], ledger.JOB_EXPENSE)
        self.assertEqual(entry["source"], "Thuê ống kính Sigma")

    def test_the_movements_add_up_to_the_balance_beside_them(self):
        self.collect()
        self.spend()

        payload = cash_account_entries(BANK)

        self.assertEqual(
            payload["balance"], sum(entry["amount"] for entry in payload["entries"])
        )
        self.assertEqual(payload["balance"], self.summed_in_the_database())
        self.assertEqual(payload["count"], len(payload["entries"]))

    def test_the_newest_movement_is_first(self):
        self.spend(spent_on="2026-01-05")
        self.spend(amount=4_000_000, spent_on="2026-03-09")

        dates = [entry["entry_date"] for entry in cash_account_entries(BANK)["entries"]]

        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_another_accounts_money_is_not_in_this_ones_list(self):
        self.make_account(CASH_BOX)
        self.collect(account=CASH_BOX)
        self.spend()

        self.assertEqual(len(cash_account_entries(BANK)["entries"]), 1)
        self.assertEqual(len(cash_account_entries(CASH_BOX)["entries"]), 1)


class TestWhoMayLookAtIt(CashAccountsTestCase):
    def test_a_producer_is_refused_what_the_company_holds(self):
        self.make_account()

        frappe.set_user(PRODUCER)

        with self.assertRaises(frappe.PermissionError):
            cash_accounts()
        with self.assertRaises(frappe.PermissionError):
            cash_account_entries(BANK)

    def test_the_refusal_is_the_ledgers_and_not_this_endpoints(self):
        frappe.set_user(PRODUCER)

        self.assertFalse(frappe.has_permission("Cash Ledger Entry", "read"))

    def test_the_founder_reads_both(self):
        self.make_account()
        self.collect()

        frappe.set_user(FOUNDER)

        self.assertEqual(cash_accounts()["total"], self.deposit.amount)
        self.assertEqual(len(cash_account_entries(BANK)["entries"]), 1)

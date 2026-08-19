"""Collecting a payment records where the money landed (#99, spec #81).

The posting rules themselves are pinned framework-free in
tests/test_ledger.py. This file proves the three things only a database
can show:

1. **The save path posts, and posts once.** Marking a milestone collected
   writes exactly one entry carrying the amount, the direction, the day,
   the account and what it came from - and marking it again, or saving
   the job again, writes nothing more. A ledger that can double-post the
   same milestone is worse than no ledger.
2. **The expand step expands nothing away.** A company that has never
   created a cash account collects exactly as it did before this ticket:
   no error, no prompt, no blocked save, and no ledger.
3. **Nobody types an entry.** The doctype grants create and write to no
   operating role, which is what lets #101 call a balance derived rather
   than agreed.

Runs via: bench --site <site> run-tests --app auraos
"""

from dataclasses import asdict

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import create_job_from_deal, job_milestones, set_milestone_status
from auraos.auraos.doctype.cash_account.cash_account import (
    DEFAULT_FIELD,
    default_account,
)
from auraos.auraos.doctype.cash_ledger_entry import cash_ledger_entry
from auraos.auraos.doctype.deal.test_deal import FOUNDER, PRODUCER, make_company
from auraos.auraos.doctype.job.test_job import won_deal
from auraos.lib import ledger
from auraos.lib.milestones import INVOICED, PAID
from auraos.tests.utils import make_test_user

BANK = "Vietcombank - main"
CASH_BOX = "Két tiền mặt"


class CashLedgerTestCase(FrappeTestCase):
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

    def entries(self):
        return frappe.get_all(
            "Cash Ledger Entry",
            filters={"source_name": self.deposit.name},
            fields=[
                "name",
                "account",
                "amount",
                "direction",
                "entry_date",
                "flow",
                "source_doctype",
                "source_name",
                "job",
                "description",
            ],
        )


class TestPostingACollection(CashLedgerTestCase):
    def test_collecting_posts_one_entry_for_the_money_that_landed(self):
        self.make_account()

        self.collect()
        posted = self.entries()

        self.assertEqual(len(posted), 1)
        entry = posted[0]
        self.assertEqual(entry.amount, self.deposit.amount)
        self.assertEqual(entry.direction, ledger.IN)
        self.assertEqual(str(entry.entry_date), frappe.utils.nowdate())
        self.assertEqual(entry.account, BANK)
        self.assertEqual(entry.flow, ledger.CLIENT_PAYMENT)
        self.assertEqual(entry.source_doctype, "Job Payment Milestone")
        self.assertEqual(entry.source_name, self.deposit.name)
        self.assertEqual(entry.job, self.job.name)
        self.assertEqual(entry.description, self.deposit.title)

    def test_the_entry_is_named_after_the_milestone_it_came_from(self):
        """So the database itself refuses a second entry for it."""
        self.make_account()

        self.collect()

        self.assertEqual(
            self.entries()[0].name,
            ledger.entry_name(ledger.CLIENT_PAYMENT, self.deposit.name),
        )

    def test_money_in_is_positive_so_a_balance_is_a_sum(self):
        self.make_account()

        self.collect()

        self.assertEqual(
            ledger.balance(cash_ledger_entry.entries_for(BANK)), self.deposit.amount
        )

    def test_an_account_with_no_entries_is_worth_nothing(self):
        self.make_account()

        self.assertEqual(ledger.balance(cash_ledger_entry.entries_for(BANK)), 0)


class TestCollectingTwice(CashLedgerTestCase):
    def test_marking_it_collected_again_does_not_post_again(self):
        self.make_account()

        self.collect()
        self.collect()

        self.assertEqual(len(self.entries()), 1)

    def test_saving_the_job_afterwards_does_not_post_again(self):
        """Every save reconciles, which is exactly why none of them repeats."""
        self.make_account()
        self.collect()

        job = frappe.get_doc("Job", self.job.name)
        job.stage = "Complete"
        job.save()

        self.assertEqual(len(self.entries()), 1)

    def test_a_second_posting_attempt_reports_that_it_did_nothing(self):
        self.make_account()
        self.collect()
        row = frappe.get_doc("Job", self.job.name).payment_milestones[0]

        action = cash_ledger_entry.sync(
            flow=ledger.CLIENT_PAYMENT,
            source_name=row.name,
            wanted=ledger.client_payment(row.as_dict(), BANK, job=self.job.name),
            moved=True,
        )

        self.assertEqual(action, ledger.NOTHING)

    def test_the_database_itself_refuses_a_second_entry_for_the_same_money(self):
        """Not a convention that callers behave - a primary key.

        Reconciliation is what usually stops a repeat, but two saves
        racing each other both read an empty ledger and both believe
        they are first. The name of an entry is the movement it records,
        so the second insert is a duplicate key rather than a second row,
        whatever the caller thought.
        """
        self.make_account()
        self.collect()
        row = frappe.get_doc("Job", self.job.name).payment_milestones[0]
        wanted = ledger.client_payment(row.as_dict(), BANK, job=self.job.name)

        with self.assertRaises(frappe.DuplicateEntryError):
            frappe.get_doc(
                {"doctype": "Cash Ledger Entry", **asdict(wanted)}
            ).insert(ignore_permissions=True)

    def test_the_loser_of_that_race_has_nothing_left_to_do(self):
        """The entry it wanted exists; that is success, not a failure."""
        self.make_account()
        self.collect()
        row = frappe.get_doc("Job", self.job.name).payment_milestones[0]
        wanted = ledger.client_payment(row.as_dict(), BANK, job=self.job.name)

        self.assertIsNone(cash_ledger_entry._insert(wanted))
        self.assertEqual(len(self.entries()), 1)

    def test_walking_back_out_of_collected_takes_the_entry_with_it(self):
        """A mis-click must not leave money in the ledger that never landed."""
        self.make_account()
        self.collect()

        set_milestone_status(self.job.name, self.deposit.name, INVOICED)

        self.assertEqual(self.entries(), [])

    def test_collecting_it_again_afterwards_posts_once(self):
        self.make_account()
        self.collect()
        set_milestone_status(self.job.name, self.deposit.name, INVOICED)

        self.collect()

        self.assertEqual(len(self.entries()), 1)


class TestWithNoAccountAnywhere(CashLedgerTestCase):
    def test_collecting_still_works_exactly_as_it_did(self):
        row = self.collect()

        self.assertEqual(row["status"], PAID)
        self.assertTrue(row["paid_on"])

    def test_and_posts_nothing(self):
        self.collect()

        self.assertEqual(self.entries(), [])
        self.assertIsNone(default_account())

    def test_the_job_carries_on_being_saved(self):
        self.collect()

        job = frappe.get_doc("Job", self.job.name)
        job.stage = "Complete"
        job.save()

        self.assertEqual(frappe.db.get_value("Job", self.job.name, "stage"), "Complete")

    def test_the_money_still_reads_as_collected_on_the_milestone(self):
        self.collect()

        self.assertEqual(job_milestones(self.job.name)["milestones"][0]["status"], PAID)

    def test_naming_an_account_that_does_not_exist_is_refused(self):
        """A typo is not a company that keeps no accounts."""
        with self.assertRaises(frappe.DoesNotExistError):
            self.collect(account="Bank of Nowhere")

    def test_an_account_belongs_to_a_milestone_being_collected(self):
        with self.assertRaises(frappe.ValidationError):
            set_milestone_status(
                self.job.name, self.deposit.name, INVOICED, account=BANK
            )


class TestWhereTheMoneyLands(CashLedgerTestCase):
    def test_the_first_account_created_becomes_the_default(self):
        """Otherwise naming where the money is kept posts nothing."""
        self.make_account()

        self.assertEqual(default_account(), BANK)

    def test_a_second_account_does_not_move_the_default(self):
        self.make_account()

        self.make_account(CASH_BOX)

        self.assertEqual(default_account(), BANK)

    def test_a_named_account_beats_the_default(self):
        self.make_account()
        self.make_account(CASH_BOX)

        self.collect(account=CASH_BOX)

        self.assertEqual(self.entries()[0].account, CASH_BOX)

    def test_a_default_pointing_at_a_deleted_account_is_no_default(self):
        """The bookkeeping must not be able to fail a collection."""
        self.make_account()
        frappe.delete_doc("Cash Account", BANK, force=True)

        self.assertIsNone(default_account())
        self.assertEqual(self.collect()["status"], PAID)


class TestWhoTouchesTheLedger(CashLedgerTestCase):
    def test_a_producer_collects_and_the_entry_is_still_posted(self):
        """Money-in is not founder-only, and the posting is not the caller's."""
        self.make_account()

        frappe.set_user(PRODUCER)
        self.collect()

        frappe.set_user("Administrator")
        self.assertEqual(len(self.entries()), 1)

    def test_a_producer_may_name_the_account_the_money_landed_in(self):
        """An account is a name, not a balance - the boundary is #101's."""
        self.make_account()
        self.make_account(CASH_BOX)

        frappe.set_user(PRODUCER)
        self.collect(account=CASH_BOX)

        frappe.set_user("Administrator")
        self.assertEqual(self.entries()[0].account, CASH_BOX)

    def test_a_producer_may_not_read_the_ledger(self):
        frappe.set_user(PRODUCER)

        self.assertFalse(frappe.has_permission("Cash Ledger Entry", "read"))

    def test_nobody_types_an_entry_by_hand(self):
        """Not even the founder - #101 derives balances, it does not agree them."""
        frappe.set_user(FOUNDER)

        self.assertFalse(frappe.has_permission("Cash Ledger Entry", "create"))
        self.assertFalse(frappe.has_permission("Cash Ledger Entry", "write"))

    def test_an_entry_that_moves_no_money_is_refused(self):
        self.make_account()

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Cash Ledger Entry",
                    "account": BANK,
                    "amount": 0,
                    "entry_date": frappe.utils.nowdate(),
                    "flow": ledger.CLIENT_PAYMENT,
                    "source_doctype": "Job Payment Milestone",
                    "source_name": "nothing-at-all",
                }
            ).insert(ignore_permissions=True)

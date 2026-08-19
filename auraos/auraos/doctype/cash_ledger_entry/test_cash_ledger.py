"""Every movement of money, recorded as it moves (#99, #100, spec #81).

The posting rules themselves are pinned framework-free in
tests/test_ledger.py. This file proves the things only a database can
show. For the client payment #99 posts:

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

And for the three #100 adds - paying a vendor, issuing an advance and
settling a float - the same three, plus the two that only matter once
money goes out as well as in:

4. **The same đồng is counted once.** Cash leaves the company when an
   advance is transferred, so an expense paid out of that float posts
   nothing and the settlement posts only the difference. A job advanced
   10M and spent 12M out of leaves the account 12M down, not 22M.
5. **The backfill is even.** auraos.patches.backfill_cash_ledger posts
   the history of all four flows for records that predate the ledger,
   twice over without a second entry, and never restates one already on
   file.

Runs via: bench --site <site> run-tests --app auraos
"""

from dataclasses import asdict

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import (
    create_job_from_deal,
    job_milestones,
    log_job_expense,
    record_job_advance,
    set_milestone_status,
    settle_job,
)
from auraos.auraos.doctype.cash_account.cash_account import (
    DEFAULT_FIELD,
    default_account,
)
from auraos.auraos.doctype.cash_ledger_entry import cash_ledger_entry
from auraos.auraos.doctype.deal.test_deal import FOUNDER, PRODUCER, make_company
from auraos.auraos.doctype.job.test_job import won_deal
from auraos.lib import ledger
from auraos.lib.milestones import INVOICED, PAID
from auraos.lib.settlement import FROM_ADVANCE, FROM_COMPANY
from auraos.patches import backfill_cash_ledger
from auraos.tests.utils import make_test_user

BANK = "Vietcombank - main"
CASH_BOX = "Két tiền mặt"

# One of the categories won_deal() quotes, so an expense may name it.
CATEGORY = "Thiết bị"


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

    def entries(self, source_name=None):
        """Every entry one record earned - the deposit unless told otherwise."""
        return frappe.get_all(
            "Cash Ledger Entry",
            filters={"source_name": source_name or self.deposit.name},
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


class MoneyOutTestCase(CashLedgerTestCase):
    """The three flows #100 adds, all against a company that has an account."""

    def setUp(self):
        super().setUp()
        self.make_account()

    def spend(self, amount=3_000_000, paid_from=FROM_COMPANY, **fields):
        """Log one expense and hand back the record, not the payload."""
        row = log_job_expense(
            self.job.name, amount, category=CATEGORY, paid_from=paid_from, **fields
        )
        return frappe.get_doc("Job Expense", row["name"])

    def advance(self, amount=10_000_000, recipient=PRODUCER):
        row = record_job_advance(self.job.name, recipient, amount)
        return frappe.get_doc("Job Advance", row["name"])

    def settle(self, holder=PRODUCER):
        row = settle_job(self.job.name, holder)
        return frappe.get_doc("Job Settlement", row["name"])

    def all_entries(self):
        return frappe.get_all("Cash Ledger Entry", pluck="name")

    def balance(self):
        return ledger.balance(cash_ledger_entry.entries_for(BANK))


class TestPayingAJobExpense(MoneyOutTestCase):
    def test_paying_a_vendor_posts_one_entry_for_the_money_that_left(self):
        expense = self.spend()

        posted = self.entries(expense.name)

        self.assertEqual(len(posted), 1)
        entry = posted[0]
        self.assertEqual(entry.amount, -3_000_000)
        self.assertEqual(entry.direction, ledger.OUT)
        self.assertEqual(str(entry.entry_date), frappe.utils.nowdate())
        self.assertEqual(entry.account, BANK)
        self.assertEqual(entry.flow, ledger.JOB_EXPENSE)
        self.assertEqual(entry.source_doctype, "Job Expense")
        self.assertEqual(entry.source_name, expense.name)
        self.assertEqual(entry.job, self.job.name)
        self.assertEqual(entry.description, CATEGORY)

    def test_an_expense_paid_out_of_a_float_posts_nothing(self):
        """That cash left the company the day the advance was transferred."""
        expense = self.spend(paid_from=FROM_ADVANCE)

        self.assertEqual(self.entries(expense.name), [])

    def test_saving_the_expense_again_does_not_post_again(self):
        expense = self.spend()

        expense.save()

        self.assertEqual(len(self.entries(expense.name)), 1)

    def test_the_database_itself_refuses_a_second_entry_for_the_same_expense(self):
        """Not a convention that callers behave - a primary key."""
        expense = self.spend()
        wanted = ledger.job_expense(expense.as_dict(), BANK)

        with self.assertRaises(frappe.DuplicateEntryError):
            frappe.get_doc(
                {"doctype": "Cash Ledger Entry", **asdict(wanted)}
            ).insert(ignore_permissions=True)

    def test_moving_the_expense_onto_a_float_takes_its_entry_back(self):
        """It was the advance that left the account, not this."""
        expense = self.spend()

        expense.paid_from = FROM_ADVANCE
        expense.save()

        self.assertEqual(self.entries(expense.name), [])

    def test_correcting_the_amount_restates_the_entry(self):
        expense = self.spend()

        expense.amount = 4_000_000
        expense.save()

        posted = self.entries(expense.name)
        self.assertEqual(len(posted), 1)
        self.assertEqual(posted[0].amount, -4_000_000)

    def test_deleting_the_expense_takes_its_entry_back(self):
        expense = self.spend()

        frappe.delete_doc("Job Expense", expense.name)

        self.assertEqual(self.entries(expense.name), [])

    def test_a_producer_paying_a_vendor_posts_the_same_entry(self):
        """The posting is not the caller's, and money out is not founder-only."""
        frappe.set_user(PRODUCER)
        row = log_job_expense(
            self.job.name, 3_000_000, category=CATEGORY, paid_from=FROM_COMPANY
        )

        frappe.set_user("Administrator")
        self.assertEqual(len(self.entries(row["name"])), 1)


class TestIssuingAnAdvance(MoneyOutTestCase):
    def test_issuing_an_advance_posts_one_entry_for_the_cash_handed_over(self):
        advance = self.advance()

        posted = self.entries(advance.name)

        self.assertEqual(len(posted), 1)
        entry = posted[0]
        self.assertEqual(entry.amount, -10_000_000)
        self.assertEqual(entry.direction, ledger.OUT)
        self.assertEqual(str(entry.entry_date), frappe.utils.nowdate())
        self.assertEqual(entry.account, BANK)
        self.assertEqual(entry.flow, ledger.CREW_ADVANCE)
        self.assertEqual(entry.source_doctype, "Job Advance")
        self.assertEqual(entry.source_name, advance.name)
        self.assertEqual(entry.job, self.job.name)
        self.assertEqual(entry.description, PRODUCER)

    def test_the_account_is_down_what_was_handed_over(self):
        self.advance()

        self.assertEqual(self.balance(), -10_000_000)

    def test_saving_the_advance_again_does_not_post_again(self):
        advance = self.advance()

        advance.save()

        self.assertEqual(len(self.entries(advance.name)), 1)

    def test_the_database_itself_refuses_a_second_entry_for_the_same_advance(self):
        advance = self.advance()
        wanted = ledger.crew_advance(advance.as_dict(), BANK)

        with self.assertRaises(frappe.DuplicateEntryError):
            frappe.get_doc(
                {"doctype": "Cash Ledger Entry", **asdict(wanted)}
            ).insert(ignore_permissions=True)

    def test_deleting_the_advance_takes_its_entry_back(self):
        """An advance deleted was an advance never handed over."""
        advance = self.advance()

        frappe.delete_doc("Job Advance", advance.name)

        self.assertEqual(self.entries(advance.name), [])


class TestSettlingAFloat(MoneyOutTestCase):
    def test_a_holder_handing_the_remainder_back_posts_money_coming_in(self):
        self.advance()
        self.spend(amount=3_000_000, paid_from=FROM_ADVANCE, paid_by=PRODUCER)

        settled = self.settle()

        posted = self.entries(settled.name)
        self.assertEqual(len(posted), 1)
        entry = posted[0]
        self.assertEqual(entry.amount, 7_000_000)
        self.assertEqual(entry.direction, ledger.IN)
        self.assertEqual(str(entry.entry_date), frappe.utils.nowdate())
        self.assertEqual(entry.account, BANK)
        self.assertEqual(entry.flow, ledger.FLOAT_SETTLEMENT)
        self.assertEqual(entry.source_doctype, "Job Settlement")
        self.assertEqual(entry.source_name, settled.name)
        self.assertEqual(entry.job, self.job.name)
        self.assertEqual(entry.description, PRODUCER)

    def test_the_company_covering_a_shortfall_posts_money_going_out(self):
        self.advance()
        self.spend(amount=12_000_000, paid_from=FROM_ADVANCE, paid_by=PRODUCER)

        settled = self.settle()

        entry = self.entries(settled.name)[0]
        self.assertEqual(entry.amount, -2_000_000)
        self.assertEqual(entry.direction, ledger.OUT)

    def test_the_money_spent_out_of_a_float_is_counted_once(self):
        """10M handed over and 12M spent leaves the account 12M down."""
        self.advance()
        self.spend(amount=12_000_000, paid_from=FROM_ADVANCE, paid_by=PRODUCER)

        self.settle()

        self.assertEqual(self.balance(), -12_000_000)

    def test_a_float_settled_to_zero_leaves_the_account_out_what_was_spent(self):
        self.advance()
        self.spend(amount=3_000_000, paid_from=FROM_ADVANCE, paid_by=PRODUCER)

        self.settle()

        self.assertEqual(self.balance(), -3_000_000)

    def test_saving_the_settlement_again_does_not_post_again(self):
        self.advance()
        settled = self.settle()

        settled.save()

        self.assertEqual(len(self.entries(settled.name)), 1)

    def test_the_database_itself_refuses_a_second_entry_for_the_same_settlement(self):
        self.advance()
        settled = self.settle()
        wanted = ledger.float_settlement(settled.as_dict(), BANK)

        with self.assertRaises(frappe.DuplicateEntryError):
            frappe.get_doc(
                {"doctype": "Cash Ledger Entry", **asdict(wanted)}
            ).insert(ignore_permissions=True)

    def test_reversing_a_settlement_takes_its_entry_back(self):
        """Its numbers are frozen, so deleting it is the only way back."""
        self.advance()
        settled = self.settle()

        frappe.delete_doc("Job Settlement", settled.name)

        self.assertEqual(self.entries(settled.name), [])
        self.assertEqual(self.balance(), -10_000_000)


class TestMoneyOutWithNoAccountAnywhere(CashLedgerTestCase):
    def test_paying_a_vendor_still_works_exactly_as_it_did(self):
        row = log_job_expense(
            self.job.name, 3_000_000, category=CATEGORY, paid_from=FROM_COMPANY
        )

        self.assertEqual(row["amount"], 3_000_000)
        self.assertEqual(self.entries(row["name"]), [])

    def test_issuing_an_advance_still_works_exactly_as_it_did(self):
        row = record_job_advance(self.job.name, PRODUCER, 10_000_000)

        self.assertEqual(row["float"]["amount"], 10_000_000)
        self.assertEqual(self.entries(row["name"]), [])

    def test_settling_a_float_still_works_exactly_as_it_did(self):
        record_job_advance(self.job.name, PRODUCER, 10_000_000)

        row = settle_job(self.job.name, PRODUCER)

        self.assertEqual(row["amount"], 10_000_000)
        self.assertEqual(self.entries(row["name"]), [])


class TestBackfillingWhatMovedBeforeTheLedger(MoneyOutTestCase):
    """The records a studio already had when this shipped.

    Written with no account in existence, which is what a record older
    than the ledger looks like: it moved money and posted nothing.
    """

    def setUp(self):
        super().setUp()
        self.clear_accounts()
        self.collect()
        self.expense = self.spend()
        self.transfer = self.advance()
        self.settled = self.settle()

    def posted_history(self):
        """The entry each of this test's four records earned, by flow."""
        return {
            entry.flow: entry.name
            for source in (
                self.deposit.name,
                self.expense.name,
                self.transfer.name,
                self.settled.name,
            )
            for entry in self.entries(source)
        }

    def test_nothing_of_that_history_posted_at_the_time(self):
        self.assertEqual(self.posted_history(), {})

    def test_the_backfill_posts_all_four_flows(self):
        self.make_account()

        backfill_cash_ledger.execute()

        self.assertEqual(
            self.posted_history(),
            {
                ledger.CLIENT_PAYMENT: ledger.entry_name(
                    ledger.CLIENT_PAYMENT, self.deposit.name
                ),
                ledger.JOB_EXPENSE: ledger.entry_name(
                    ledger.JOB_EXPENSE, self.expense.name
                ),
                ledger.CREW_ADVANCE: ledger.entry_name(
                    ledger.CREW_ADVANCE, self.transfer.name
                ),
                ledger.FLOAT_SETTLEMENT: ledger.entry_name(
                    ledger.FLOAT_SETTLEMENT, self.settled.name
                ),
            },
        )

    def test_the_backfilled_entries_say_what_the_records_say(self):
        """Each at its own amount and its own day, not the day of the sweep."""
        self.make_account()

        backfill_cash_ledger.execute()

        self.assertEqual(self.entries(self.deposit.name)[0].amount, self.deposit.amount)
        self.assertEqual(self.entries(self.expense.name)[0].amount, -3_000_000)
        self.assertEqual(self.entries(self.transfer.name)[0].amount, -10_000_000)
        self.assertEqual(self.entries(self.settled.name)[0].amount, 10_000_000)
        self.assertEqual(
            str(self.entries(self.transfer.name)[0].entry_date),
            str(self.transfer.transferred_on),
        )

    def test_running_it_twice_posts_nothing_more(self):
        self.make_account()
        backfill_cash_ledger.execute()
        once = self.all_entries()

        backfill_cash_ledger.execute()

        self.assertEqual(sorted(self.all_entries()), sorted(once))

    def test_a_company_with_no_account_gets_no_ledger_and_no_error(self):
        backfill_cash_ledger.execute()

        self.assertEqual(self.posted_history(), {})

    def test_it_leaves_a_float_expense_out_of_the_ledger(self):
        """The same line the save path draws, drawn once."""
        out_of_float = self.spend(paid_from=FROM_ADVANCE)
        self.make_account()

        backfill_cash_ledger.execute()

        self.assertEqual(self.entries(out_of_float.name), [])

    def test_it_never_restates_an_entry_already_on_file(self):
        """What the save path posted is the more recent reading of the two."""
        self.make_account()
        posted = self.spend(amount=5_000_000)
        frappe.db.set_value("Job Expense", posted.name, "amount", 9_000_000)

        backfill_cash_ledger.execute()

        self.assertEqual(self.entries(posted.name)[0].amount, -5_000_000)

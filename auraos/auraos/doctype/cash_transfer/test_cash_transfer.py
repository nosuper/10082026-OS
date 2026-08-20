"""Seam tests for money moving between our own accounts (#151).

The pairing rule is pinned framework-free in tests/test_ledger.py. What
only a site can show is that both halves reach the ledger from one save,
survive a correction together, and leave together - and that the
company-wide total never moves while the two accounts do.

**The invariant is the first test and the last one.** A transfer that
posted one side would invent money or lose it in transit, and would look
sound on every screen that reads one account at a time - which is every
screen the app has. So it is asserted against the sum over all accounts,
not against either balance.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import cash_transfers, record_cash_transfer
from auraos.auraos.doctype.cash_account.cash_account import DEFAULT_FIELD
from auraos.auraos.doctype.cash_ledger_entry import cash_ledger_entry
from auraos.auraos.doctype.deal.test_deal import FOUNDER, OUTSIDER, PRODUCER
from auraos.lib import ledger
from auraos.tests.utils import make_test_user

BANK = "Vietcombank - transfers"
BOX = "Két tiền mặt - transfers"
AMOUNT = 15_000_000


class TransferTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")
        self.clear_money()
        for name in (BANK, BOX):
            frappe.get_doc({"doctype": "Cash Account", "account_name": name}).insert()
        frappe.set_user(FOUNDER)

    def tearDown(self):
        frappe.set_user("Administrator")
        self.clear_money()
        super().tearDown()

    def clear_money(self):
        for transfer in frappe.get_all("Cash Transfer", pluck="name"):
            frappe.delete_doc("Cash Transfer", transfer, force=True)
        for entry in frappe.get_all("Cash Ledger Entry", pluck="name"):
            frappe.delete_doc("Cash Ledger Entry", entry, force=True)
        frappe.db.set_single_value("AuraOS Settings", DEFAULT_FIELD, None)
        for account in frappe.get_all("Cash Account", pluck="name"):
            frappe.delete_doc("Cash Account", account, force=True)

    def move(self, **overrides):
        values = {
            "from_account": BANK,
            "to_account": BOX,
            "amount": AMOUNT,
            "moved_on": "2026-07-01",
        }
        values.update(overrides)
        return record_cash_transfer(**values)

    def balance(self, account):
        return ledger.balance(cash_ledger_entry.entries_for(account))

    def everything(self):
        """What the company holds, across every account it has."""
        return sum(
            int(row.amount or 0)
            for row in frappe.get_all("Cash Ledger Entry", fields=["amount"])
        )

    def entries_of(self, transfer):
        return sorted(
            frappe.get_all(
                "Cash Ledger Entry",
                filters={"source_name": transfer},
                fields=["name", "account", "amount", "flow", "job"],
            ),
            key=lambda row: row.amount,
        )


class TestTheCompanyHoldsWhatItHeld(TransferTestCase):
    def test_a_transfer_moves_two_balances_and_no_total(self):
        """The whole design in one assertion."""
        before = self.everything()

        self.move()

        self.assertEqual(self.balance(BANK), -AMOUNT)
        self.assertEqual(self.balance(BOX), AMOUNT)
        self.assertEqual(self.everything(), before)

    def test_one_record_writes_two_entries(self):
        out = self.move()

        left, arrived = self.entries_of(out["name"])
        self.assertEqual(left.account, BANK)
        self.assertEqual(left.amount, -AMOUNT)
        self.assertEqual(left.flow, ledger.TRANSFER_OUT)
        self.assertEqual(arrived.account, BOX)
        self.assertEqual(arrived.amount, AMOUNT)
        self.assertEqual(arrived.flow, ledger.TRANSFER_IN)

    def test_neither_entry_belongs_to_a_job(self):
        out = self.move()

        self.assertEqual([row.job for row in self.entries_of(out["name"])], [None, None])

    def test_the_endpoint_hands_back_both_balances(self):
        """The only reason to record a withdrawal is to make two figures
        right, so the caller is shown both rather than told it worked."""
        out = self.move()

        self.assertEqual(out["balances"][BANK], -AMOUNT)
        self.assertEqual(out["balances"][BOX], AMOUNT)


class TestCorrectingAndDeleting(TransferTestCase):
    def test_correcting_the_amount_restates_both_halves(self):
        out = self.move()
        doc = frappe.get_doc("Cash Transfer", out["name"])

        doc.amount = 4_000_000
        doc.save()

        self.assertEqual(self.balance(BANK), -4_000_000)
        self.assertEqual(self.balance(BOX), 4_000_000)
        self.assertEqual(len(self.entries_of(out["name"])), 2)

    def test_saving_again_changes_nothing(self):
        """The reconciler answers a movement already on file with
        nothing, and it has to do that for both halves or a second save
        doubles the transfer."""
        out = self.move()
        doc = frappe.get_doc("Cash Transfer", out["name"])

        doc.save()

        self.assertEqual(len(self.entries_of(out["name"])), 2)
        self.assertEqual(self.balance(BANK), -AMOUNT)

    def test_deleting_takes_both_halves_out(self):
        before = self.everything()
        out = self.move()

        frappe.delete_doc("Cash Transfer", out["name"])

        self.assertEqual(self.entries_of(out["name"]), [])
        self.assertEqual(self.balance(BANK), 0)
        self.assertEqual(self.balance(BOX), 0)
        self.assertEqual(self.everything(), before)

    def test_redirecting_a_transfer_moves_the_money_with_it(self):
        """The account is on the record rather than defaulted, so
        correcting it is a real correction - and the old account must not
        keep a half."""
        third = frappe.get_doc(
            {"doctype": "Cash Account", "account_name": "Ví MoMo - transfers"}
        ).insert()
        out = self.move()
        doc = frappe.get_doc("Cash Transfer", out["name"])

        doc.to_account = third.name
        doc.save()

        self.assertEqual(self.balance(BOX), 0)
        self.assertEqual(self.balance(third.name), AMOUNT)
        self.assertEqual(self.balance(BANK), -AMOUNT)


class TestWhatIsNotATransfer(TransferTestCase):
    def test_money_moved_to_the_account_it_came_from_is_refused(self):
        with self.assertRaises(frappe.ValidationError):
            self.move(to_account=BANK)

    def test_a_transfer_of_nothing_is_refused(self):
        with self.assertRaises(frappe.ValidationError):
            self.move(amount=0)

    def test_an_account_that_does_not_exist_is_refused(self):
        with self.assertRaises(frappe.LinkValidationError):
            self.move(to_account="Không có tài khoản này")


class TestWhoMayMoveTheCompanysMoney(TransferTestCase):
    def test_a_producer_may_not(self):
        """Decided on the Company Expense precedent rather than by a
        founder ruling - #143's every-producer answer was about job
        money, and this is not job money."""
        frappe.set_user(PRODUCER)

        with self.assertRaises(frappe.PermissionError):
            self.move()

    def test_an_outsider_may_not_even_read_them(self):
        self.move()
        frappe.set_user(OUTSIDER)

        with self.assertRaises(frappe.PermissionError):
            cash_transfers()

    def test_the_founder_reads_what_they_recorded(self):
        self.move(note="Rút quỹ đi Phan Thiết")

        (row,) = cash_transfers()

        self.assertEqual(row["from_account"], BANK)
        self.assertEqual(row["to_account"], BOX)
        self.assertEqual(row["note"], "Rút quỹ đi Phan Thiết")

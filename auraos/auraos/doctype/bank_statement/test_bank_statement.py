"""Seam tests for bank statements and reconciliation (#150).

The arithmetic, the references and the matcher are pinned framework-free
in tests/test_statement.py. What only a site can show is the wiring, and
the wiring is where this feature's promises live:

1. **A real file becomes a statement**, read out of a spreadsheet by
   labels rather than row numbers - the fixture is the shape of the
   founder's July statement with every detail of the company fabricated.
2. **A statement that fails its own arithmetic is refused**, so nothing
   downstream is ever asked of numbers that do not add up.
3. **The facts freeze and the reconciliation does not.** The bank's
   columns refuse to change after insert; the match is the one thing a
   person may set and take back.
4. **Matching is one-to-one and a person does it.** Nothing here writes
   a ledger entry from a statement line, and no entry is claimed twice.
5. **Both halves of the difference are reported** - what the bank saw
   that we have no record of, and what we recorded that no line claims.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import (
    bank_reconciliation,
    bank_statements,
    create_job_from_deal,
    import_bank_statement,
    log_job_expense,
    match_statement_line,
    unmatch_statement_line,
)
from auraos.auraos.doctype.cash_account.cash_account import DEFAULT_FIELD
from auraos.auraos.doctype.deal.test_deal import FOUNDER, OUTSIDER, PRODUCER
from auraos.auraos.doctype.job.test_job import won_deal
from auraos.lib import ledger
from auraos.lib.settlement import FROM_COMPANY
from auraos.tests.utils import make_test_user

BANK = "Vietcombank - statements"
FIXTURE = "sao_ke_vi_du.xlsx"

# What the fabricated statement says about itself.
OPENING = 10_000_000
WITHDRAWN = 11_600_000
DEPOSITED = 20_000_500
CLOSING = 18_400_500
LINES = 7

# Two of its lines, by the bank's own transaction number.
VENDOR_PAYMENT = "1003"  # -3.000.000 on 05/09, quoting HDDV 0109-2026
INTEREST = "1004"  # +500, a movement AuraOS keeps no record of


class StatementTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")
        self.clear_money()
        frappe.get_doc({"doctype": "Cash Account", "account_name": BANK}).insert()
        frappe.set_user(FOUNDER)

    def tearDown(self):
        frappe.set_user("Administrator")
        self.clear_money()
        super().tearDown()

    def clear_money(self):
        for statement in frappe.get_all("Bank Statement", pluck="name"):
            frappe.delete_doc("Bank Statement", statement, force=True)
        for entry in frappe.get_all("Cash Ledger Entry", pluck="name"):
            frappe.delete_doc("Cash Ledger Entry", entry, force=True)
        frappe.db.set_single_value("AuraOS Settings", DEFAULT_FIELD, None)
        for account in frappe.get_all("Cash Account", pluck="name"):
            frappe.delete_doc("Cash Account", account, force=True)

    def fixture_file(self):
        """The fabricated statement, attached the way an upload arrives."""
        path = frappe.get_app_path("auraos", "tests", "fixtures", FIXTURE)
        with open(path, "rb") as handle:
            content = handle.read()
        existing = frappe.db.get_value("File", {"file_name": FIXTURE}, "file_url")
        if existing:
            return existing
        return frappe.get_doc(
            {
                "doctype": "File",
                "file_name": FIXTURE,
                "is_private": 1,
                "content": content,
            }
        ).insert().file_url

    def imported(self):
        return import_bank_statement(self.fixture_file(), BANK)

    def statement_doc(self):
        frappe.set_user("Administrator")
        doc = frappe.get_doc("Bank Statement", self.imported()["name"])
        frappe.set_user(FOUNDER)
        return doc

    def line_named(self, doc, sequence):
        (row,) = [one for one in doc.lines if one.sequence == sequence]
        return row

    def spend(self, amount, spent_on, description="Chi thật"):
        """A company-paid expense, which posts a ledger entry."""
        frappe.set_user("Administrator")
        job = create_job_from_deal(won_deal().name)["name"]
        row = log_job_expense(
            job, amount, description=description, spent_on=spent_on,
            paid_from=FROM_COMPANY,
        )
        entry = ledger.entry_name(ledger.JOB_EXPENSE, row["name"])
        frappe.set_user(FOUNDER)
        return entry


class TestImportingAStatement(StatementTestCase):
    def test_a_real_file_becomes_a_statement(self):
        out = self.imported()

        doc = frappe.get_doc("Bank Statement", out["name"])
        self.assertEqual(len(doc.lines), LINES)
        self.assertEqual(int(doc.opening), OPENING)
        self.assertEqual(int(doc.withdrawn), WITHDRAWN)
        self.assertEqual(int(doc.deposited), DEPOSITED)
        self.assertEqual(int(doc.closing), CLOSING)

    def test_the_account_number_the_file_names_is_handed_back(self):
        """The account is the caller's - AuraOS keeps accounts by name
        and a bank prints a number - so the number travels back for a
        person to see the two agree rather than being guessed at."""
        self.assertEqual(self.imported()["account_number"], "9999999999")

    def test_the_bank_writes_money_two_ways_and_both_arrive(self):
        """The summary block is comma-grouped text and the table is
        floats in scientific notation. Both are money."""
        doc = self.statement_doc()

        self.assertEqual(int(doc.opening), OPENING)
        self.assertEqual(int(self.line_named(doc, VENDOR_PAYMENT).withdrawn), 3_000_000)

    def test_the_same_statement_cannot_be_imported_twice(self):
        self.imported()

        with self.assertRaises(frappe.DuplicateEntryError):
            self.imported()

    def test_a_statement_that_disagrees_with_itself_is_refused(self):
        """Every later question is asked of these numbers, so a sheet
        that does not add up never becomes a record."""
        frappe.set_user("Administrator")
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Bank Statement",
                    "account": BANK,
                    "period_from": "2026-09-01",
                    "period_to": "2026-09-30",
                    "opening": 0,
                    "withdrawn": 1_000_000,
                    "deposited": 0,
                    "closing": 0,
                    "lines": [
                        {
                            "effective_on": "2026-09-01",
                            "sequence": "1",
                            "description": "Chi",
                            "withdrawn": 999_000,
                            "running_balance": -999_000,
                        }
                    ],
                }
            ).insert()

    def test_a_producer_may_not_import(self):
        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            import_bank_statement("/files/nothing.xlsx", BANK)

    def test_an_outsider_may_not_read_the_statements(self):
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            bank_statements()


class TestTheFactsFreeze(StatementTestCase):
    def test_a_line_cannot_be_edited_after_import(self):
        doc = self.statement_doc()
        self.line_named(doc, VENDOR_PAYMENT).withdrawn = 1

        with self.assertRaises(frappe.ValidationError):
            doc.save()

    def test_the_period_cannot_be_edited_after_import(self):
        doc = self.statement_doc()
        doc.period_to = "2026-10-31"

        with self.assertRaises(frappe.ValidationError):
            doc.save()

    def test_a_line_cannot_be_added(self):
        doc = self.statement_doc()
        doc.append("lines", {"effective_on": "2026-09-30", "sequence": "9999",
                             "description": "Không có thật", "withdrawn": 1})

        with self.assertRaises(frappe.ValidationError):
            doc.save()

    def test_the_match_is_the_one_thing_that_may_change(self):
        """The other side of the freeze, asserted so that "immutable"
        cannot quietly become "read-only"."""
        entry = self.spend(3_000_000, "2026-09-05")
        doc = self.statement_doc()
        line = self.line_named(doc, VENDOR_PAYMENT)

        match_statement_line(doc.name, line.name, entry)

        stored = frappe.get_doc("Bank Statement", doc.name)
        self.assertEqual(self.line_named(stored, VENDOR_PAYMENT).matched_entry, entry)


class TestMatchingIsAJudgement(StatementTestCase):
    def test_confirming_records_who_and_when(self):
        entry = self.spend(3_000_000, "2026-09-05")
        doc = self.statement_doc()

        out = match_statement_line(doc.name, self.line_named(doc, VENDOR_PAYMENT).name, entry)

        self.assertEqual(out["matched_entry"], entry)
        self.assertEqual(out["matched_by"], FOUNDER)
        self.assertTrue(out["matched_on"])

    def test_an_entry_already_claimed_is_refused(self):
        """Two lines pointing at one entry would say the company paid
        once and the bank saw it twice."""
        entry = self.spend(3_000_000, "2026-09-05")
        doc = self.statement_doc()
        match_statement_line(doc.name, self.line_named(doc, VENDOR_PAYMENT).name, entry)

        with self.assertRaises(frappe.ValidationError):
            match_statement_line(doc.name, self.line_named(doc, "1007").name, entry)

    def test_unmatching_takes_the_judgement_back(self):
        entry = self.spend(3_000_000, "2026-09-05")
        doc = self.statement_doc()
        line = self.line_named(doc, VENDOR_PAYMENT).name
        match_statement_line(doc.name, line, entry)

        unmatch_statement_line(doc.name, line)

        stored = frappe.get_doc("Bank Statement", doc.name)
        self.assertIsNone(self.line_named(stored, VENDOR_PAYMENT).matched_entry)

    def test_a_producer_may_not_confirm_a_match(self):
        entry = self.spend(3_000_000, "2026-09-05")
        doc = self.statement_doc()
        line = self.line_named(doc, VENDOR_PAYMENT).name

        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            match_statement_line(doc.name, line, entry)


class TestTheDifferenceIsTheProduct(StatementTestCase):
    def read(self, doc):
        return bank_reconciliation(doc.name)

    def test_an_entry_of_the_same_money_on_the_same_day_is_suggested(self):
        entry = self.spend(3_000_000, "2026-09-05")
        doc = self.statement_doc()

        (line,) = [one for one in self.read(doc)["lines"] if one["sequence"] == VENDOR_PAYMENT]

        self.assertEqual(line["suggestion"]["entry"], entry)

    def test_a_line_the_app_keeps_no_record_of_says_why(self):
        """Not a failure to match - a movement AuraOS does not model.
        Saying so is what stops somebody hunting for a record nobody
        made."""
        doc = self.statement_doc()

        (line,) = [one for one in self.read(doc)["lines"] if one["sequence"] == INTEREST]

        self.assertIsNone(line["suggestion"])
        self.assertIn("interest", line["unmodelled"])

    def test_an_entry_no_line_claims_is_reported_as_well(self):
        """The other half of the difference. A screen that showed only
        the matches would be a screen that agreed with itself."""
        self.spend(4_242_000, "2026-09-08", description="Cái ngân hàng không thấy")
        doc = self.statement_doc()

        names = [one["name"] for one in self.read(doc)["unmatched_entries"]]

        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(
            any(
                frappe.db.get_value("Cash Ledger Entry", name, "amount") == -4_242_000
                for name in names
            )
        )

    def test_a_confirmed_line_leaves_the_unmatched_list(self):
        entry = self.spend(3_000_000, "2026-09-05")
        doc = self.statement_doc()
        match_statement_line(doc.name, self.line_named(doc, VENDOR_PAYMENT).name, entry)

        read = self.read(doc)

        self.assertNotIn(entry, [one["name"] for one in read["unmatched_entries"]])
        (line,) = [one for one in read["lines"] if one["sequence"] == VENDOR_PAYMENT]
        self.assertEqual(line["matched_entry"], entry)

    def test_a_producer_may_not_read_the_reconciliation(self):
        doc = self.statement_doc()

        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            bank_reconciliation(doc.name)

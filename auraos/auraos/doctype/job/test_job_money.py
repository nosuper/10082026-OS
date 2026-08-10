"""Seam tests for T8 (issue #10): advances, expenses and settlement.

Four seams:

1. **Advances** — company cash recorded against a job and a recipient,
   and only for people who can actually hold a float.
2. **Quick expense entry** — the phone case: an amount and a category
   is a complete expense, everything else defaults to what it almost
   always is.
3. **Categories mirror the quote** — an expense's category is one of
   the entries the job was quoted, which is what makes actual-vs-quoted
   per package appear without anyone maintaining it.
4. **Settlement** — advances minus what was spent out of them, named as
   a direction, recorded as a transfer that closes the float.

The arithmetic itself is pinned framework-free in tests/test_settlement.py;
what these tests prove is that the documents and the API go through it,
and that the permission boundary around money holds.

Runs via: bench --site <site> run-tests --app auraos
"""

import base64

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import (
    create_job_from_deal,
    job_expense_categories,
    job_money,
    log_job_expense,
    record_job_advance,
    settle_job,
)
from auraos.auraos.doctype.deal.test_deal import FOUNDER, OUTSIDER, PRODUCER
from auraos.auraos.doctype.job.test_job import won_deal
from auraos.lib.settlement import EVEN, RETURN, TOP_UP, UNCATEGORISED
from auraos.tests.utils import make_test_user

# The packages won_deal() carries, and the two lines it quotes on their
# own — together, every category an expense on that job may name.
PACKAGES = ["Nhân sự", "Thiết bị"]
STANDALONE = ["Studio", "Ăn uống đoàn"]


def money_job():
    """A job converted from a won, packaged, priced deal."""
    return frappe.get_doc("Job", create_job_from_deal(won_deal().name)["name"])


def float_of(job, holder):
    for held in job_money(job)["floats"]:
        if held["holder"] == holder:
            return held
    return None


def category(job, title):
    for row in job_money(job)["categories"]:
        if row["title"] == title:
            return row
    return None


class MoneyTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")
        self.job = money_job().name

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()


class TestJobAdvances(MoneyTestCase):
    def test_an_advance_records_its_amount_and_recipient(self):
        record_job_advance(self.job, PRODUCER, 20_000_000)

        (advance,) = job_money(self.job)["advances"]
        self.assertEqual(advance.recipient, PRODUCER)
        self.assertEqual(advance.amount, 20_000_000)
        self.assertEqual(advance.transferred_on, frappe.utils.getdate())

    def test_an_advance_puts_the_whole_amount_in_the_recipients_hands(self):
        record_job_advance(self.job, PRODUCER, 20_000_000)

        held = float_of(self.job, PRODUCER)
        self.assertEqual(held["advanced"], 20_000_000)
        self.assertEqual(held["amount"], 20_000_000)
        self.assertEqual(held["direction"], RETURN)

    def test_advances_to_the_same_person_add_up(self):
        record_job_advance(self.job, PRODUCER, 20_000_000)
        record_job_advance(self.job, PRODUCER, 5_000_000)

        self.assertEqual(float_of(self.job, PRODUCER)["advanced"], 25_000_000)

    def test_an_advance_needs_an_amount(self):
        with self.assertRaises(frappe.ValidationError):
            record_job_advance(self.job, PRODUCER, 0)

    def test_an_advance_only_goes_to_someone_who_works_here(self):
        """A float pointed at an outsider is one nobody ever settles."""
        with self.assertRaises(frappe.ValidationError):
            record_job_advance(self.job, OUTSIDER, 1_000_000)

    def test_an_advance_on_a_missing_job_fails(self):
        with self.assertRaises(frappe.DoesNotExistError):
            record_job_advance("JOB-does-not-exist", PRODUCER, 1_000_000)

    def test_recording_an_advance_is_the_founders_move(self):
        """Story 30 is the founder's: he transfers, she spends."""
        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            record_job_advance(self.job, PRODUCER, 20_000_000)

    def test_the_producer_can_see_the_float_she_is_holding(self):
        record_job_advance(self.job, PRODUCER, 20_000_000)

        frappe.set_user(PRODUCER)
        self.assertEqual(float_of(self.job, PRODUCER)["amount"], 20_000_000)

    def test_an_outsider_reads_no_money_at_all(self):
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            job_money(self.job)


class TestQuickExpenseEntry(MoneyTestCase):
    def test_an_amount_and_a_category_are_a_complete_expense(self):
        """The 15-second case (story 31): everything else defaults."""
        frappe.set_user(PRODUCER)
        logged = log_job_expense(self.job, 1_500_000, category="Thiết bị")

        expense = frappe.get_doc("Job Expense", logged["name"])
        self.assertEqual(expense.amount, 1_500_000)
        self.assertEqual(expense.category, "Thiết bị")
        self.assertEqual(expense.spent_on, frappe.utils.getdate())
        self.assertEqual(expense.paid_by, PRODUCER)
        self.assertEqual(expense.paid_from, "Advance")

    def test_logging_an_expense_answers_how_much_float_is_left(self):
        record_job_advance(self.job, PRODUCER, 20_000_000)

        frappe.set_user(PRODUCER)
        logged = log_job_expense(self.job, 12_000_000, category="Thiết bị")

        self.assertEqual(logged["float"]["amount"], 8_000_000)
        self.assertEqual(logged["float"]["direction"], RETURN)

    def test_an_expense_needs_an_amount(self):
        with self.assertRaises(frappe.ValidationError):
            log_job_expense(self.job, 0, category="Thiết bị")

    def test_an_expense_may_be_uncategorised(self):
        """Money gets spent on things nobody quoted; hiding it is worse."""
        logged = log_job_expense(self.job, 200_000, description="Gửi xe")

        self.assertIsNone(frappe.get_doc("Job Expense", logged["name"]).category)
        self.assertEqual(category(self.job, UNCATEGORISED)["actual"], 200_000)

    def test_an_expense_cannot_invent_a_category(self):
        with self.assertRaises(frappe.ValidationError):
            log_job_expense(self.job, 200_000, category="Phòng marketing")

    def test_the_founder_can_log_what_someone_else_paid(self):
        """A receipt that arrived by Zalo still belongs to her float."""
        record_job_advance(self.job, PRODUCER, 20_000_000)
        frappe.set_user(FOUNDER)
        log_job_expense(self.job, 3_000_000, category="Nhân sự", paid_by=PRODUCER)

        self.assertEqual(float_of(self.job, PRODUCER)["spent"], 3_000_000)
        self.assertIsNone(float_of(self.job, FOUNDER))

    def test_an_outsider_cannot_log_an_expense(self):
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            log_job_expense(self.job, 200_000, category="Thiết bị")

    def test_an_expense_on_a_missing_job_fails(self):
        with self.assertRaises(frappe.DoesNotExistError):
            log_job_expense("JOB-does-not-exist", 200_000)


class TestExpensePhotos(MoneyTestCase):
    # A 1×1 PNG: Frappe strips EXIF from anything it recognises as an
    # image, so the receipt has to actually be one.
    PIXEL = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )

    def upload(self, name="receipt.png"):
        """A private file with nothing attached to it yet — what the
        phone leaves behind when the receipt is photographed before the
        expense exists."""
        return frappe.get_doc(
            {
                "doctype": "File",
                "file_name": name,
                "content": self.PIXEL,
                "is_private": 1,
            }
        ).insert()

    def test_the_receipt_ends_up_attached_to_the_expense(self):
        frappe.set_user(PRODUCER)
        photo = self.upload()
        logged = log_job_expense(self.job, 500_000, category="Thiết bị",
                                 photo=photo.file_url)

        expense = frappe.get_doc("Job Expense", logged["name"])
        self.assertEqual(expense.photo, photo.file_url)
        attached = frappe.get_doc("File", photo.name)
        self.assertEqual(attached.attached_to_doctype, "Job Expense")
        self.assertEqual(attached.attached_to_name, expense.name)

    def test_an_attached_receipt_is_readable_by_the_other_role(self):
        """The point of attaching it: the founder checking her receipts
        against the spend is the whole reason photos are logged."""
        frappe.set_user(PRODUCER)
        photo = self.upload()
        log_job_expense(self.job, 500_000, category="Thiết bị", photo=photo.file_url)

        frappe.set_user(FOUNDER)
        frappe.get_doc("File", photo.name).check_permission("read")

    def test_a_file_somebody_else_uploaded_is_not_a_receipt(self):
        """Otherwise this endpoint would re-parent any private file and
        read it back through an expense."""
        frappe.set_user(FOUNDER)
        someone_elses = self.upload("founder-only.png")

        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.ValidationError):
            log_job_expense(self.job, 500_000, photo=someone_elses.file_url)

    def test_an_expense_without_a_photo_is_still_an_expense(self):
        logged = log_job_expense(self.job, 500_000, category="Thiết bị")
        self.assertFalse(frappe.get_doc("Job Expense", logged["name"]).photo)


class TestDirectPayments(MoneyTestCase):
    def test_a_direct_payment_is_money_out_that_settles_no_float(self):
        """Story 33: the founder's own vendor payments belong in the
        job's money out, but they are not Linh's to hand back."""
        record_job_advance(self.job, PRODUCER, 20_000_000)
        frappe.set_user(PRODUCER)
        log_job_expense(self.job, 5_000_000, category="Nhân sự")

        frappe.set_user(FOUNDER)
        log_job_expense(self.job, 48_000_000, category="Thiết bị",
                        paid_from="Company")

        self.assertEqual(job_money(self.job)["spent_total"], 53_000_000)
        self.assertEqual(float_of(self.job, PRODUCER)["amount"], 15_000_000)
        self.assertIsNone(float_of(self.job, FOUNDER))

    def test_a_direct_payment_still_counts_against_its_package(self):
        frappe.set_user(FOUNDER)
        log_job_expense(self.job, 48_000_000, category="Thiết bị",
                        paid_from="Company")

        self.assertEqual(category(self.job, "Thiết bị")["actual"], 48_000_000)


class TestCategoriesMirrorTheQuote(MoneyTestCase):
    def test_the_categories_are_the_packages_and_anything_quoted_alone(self):
        self.assertEqual(job_expense_categories(self.job), PACKAGES + STANDALONE)

    def test_a_line_inside_a_package_is_not_a_category(self):
        job = frappe.get_doc("Job", self.job)
        self.assertIn(job.cost_lines[0].description, [row.description for row in job.cost_lines])
        self.assertNotIn(job.cost_lines[0].description, job_expense_categories(self.job))

    def test_the_categories_cannot_drift_away_from_the_expenses_on_them(self):
        """Renaming a package would silently reclassify every expense
        already logged against it. T7 froze the carried snapshot, which
        is what stops that — pinned here because this ticket is what
        made it matter."""
        job = frappe.get_doc("Job", self.job)
        job.packages[0].title = "Crew"

        with self.assertRaises(frappe.ValidationError):
            job.save()

    def test_every_category_appears_before_anything_is_spent(self):
        """An untouched package is the interesting one during a shoot."""
        rows = job_money(self.job)["categories"]

        self.assertEqual([row["title"] for row in rows], PACKAGES + STANDALONE)
        self.assertTrue(all(row["actual"] == 0 for row in rows))
        self.assertTrue(all(row["quoted"] > 0 for row in rows))

    def test_a_packages_quoted_cost_is_what_its_lines_will_hand_over(self):
        """Cost after the vendor management fee plus VAT on an invoice —
        not the profit cost basis, which for the freelancer line is
        grossed up by PIT nobody pays on a shoot."""
        job = frappe.get_doc("Job", self.job)
        members = [row for row in job.cost_lines if row.package == "Nhân sự"]
        expected = sum(
            row.subtotal * (1 + (row.vendor_mf_pct or 0) / 100) + row.input_vat
            for row in members
        )

        quoted = category(self.job, "Nhân sự")["quoted"]
        self.assertEqual(quoted, round(expected))
        self.assertLess(quoted, sum(row.cost_basis for row in members))

    def test_spending_shows_up_against_the_package_it_was_quoted_in(self):
        log_job_expense(self.job, 4_000_000, category="Nhân sự")
        log_job_expense(self.job, 1_000_000, category="Nhân sự")

        row = category(self.job, "Nhân sự")
        self.assertEqual(row["actual"], 5_000_000)
        self.assertEqual(row["variance"], row["actual"] - row["quoted"])

    def test_the_quoted_total_is_what_the_job_expected_to_pay_out(self):
        money = job_money(self.job)
        self.assertEqual(
            money["quoted_total"],
            sum(row["quoted"] for row in money["categories"]),
        )


class TestSettlement(MoneyTestCase):
    def spend_from_float(self, advanced, spent):
        record_job_advance(self.job, PRODUCER, advanced)
        frappe.set_user(PRODUCER)
        log_job_expense(self.job, spent, category="Thiết bị")
        frappe.set_user(FOUNDER)

    def test_settling_returns_what_is_left_of_the_float(self):
        self.spend_from_float(20_000_000, 17_500_000)

        result = settle_job(self.job, PRODUCER)
        self.assertEqual(result["amount"], 2_500_000)
        self.assertEqual(result["direction"], RETURN)

    def test_settling_an_overspent_float_pays_the_holder_back(self):
        self.spend_from_float(20_000_000, 23_000_000)

        result = settle_job(self.job, PRODUCER)
        self.assertEqual(result["amount"], -3_000_000)
        self.assertEqual(result["direction"], TOP_UP)

    def test_a_settled_float_is_even(self):
        self.spend_from_float(20_000_000, 17_500_000)
        settle_job(self.job, PRODUCER)

        held = float_of(self.job, PRODUCER)
        self.assertEqual(held["amount"], 0)
        self.assertEqual(held["direction"], EVEN)
        self.assertEqual(held["settled"], 2_500_000)

    def test_a_settlement_records_what_it_closed(self):
        self.spend_from_float(20_000_000, 17_500_000)
        settled = frappe.get_doc("Job Settlement", settle_job(self.job, PRODUCER)["name"])

        self.assertEqual(settled.job, self.job)
        self.assertEqual(settled.recipient, PRODUCER)
        self.assertEqual(settled.advanced, 20_000_000)
        self.assertEqual(settled.spent, 17_500_000)
        self.assertEqual(settled.settled_by, FOUNDER)
        self.assertTrue(settled.settled_on)

    def test_an_even_float_has_nothing_to_settle(self):
        self.spend_from_float(20_000_000, 20_000_000)

        with self.assertRaises(frappe.ValidationError):
            settle_job(self.job, PRODUCER)

    def test_settling_twice_over_needs_new_money_to_have_moved(self):
        self.spend_from_float(20_000_000, 17_500_000)
        settle_job(self.job, PRODUCER)

        with self.assertRaises(frappe.ValidationError):
            settle_job(self.job, PRODUCER)

    def test_the_job_carries_on_after_a_settlement(self):
        """A settled float is closed, not final: the shoot goes on."""
        self.spend_from_float(20_000_000, 17_500_000)
        settle_job(self.job, PRODUCER)

        record_job_advance(self.job, PRODUCER, 6_000_000)
        frappe.set_user(PRODUCER)
        log_job_expense(self.job, 1_000_000, category="Thiết bị")

        held = float_of(self.job, PRODUCER)
        self.assertEqual(held["amount"], 5_000_000)
        self.assertEqual(held["direction"], RETURN)

    def test_settling_is_the_founders_move(self):
        self.spend_from_float(20_000_000, 17_500_000)

        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            settle_job(self.job, PRODUCER)

    def test_a_settlement_cannot_be_rewritten_afterwards(self):
        """It records a transfer that already happened."""
        self.spend_from_float(20_000_000, 17_500_000)
        settled = frappe.get_doc("Job Settlement", settle_job(self.job, PRODUCER)["name"])

        settled.amount = 1
        with self.assertRaises(frappe.ValidationError):
            settled.save()

    def test_a_settlement_note_can_still_be_written(self):
        self.spend_from_float(20_000_000, 17_500_000)
        settled = frappe.get_doc("Job Settlement", settle_job(self.job, PRODUCER)["name"])

        settled.note = "Chuyển khoản 12/08"
        settled.save()
        self.assertEqual(
            frappe.get_doc("Job Settlement", settled.name).note, "Chuyển khoản 12/08"
        )

    def test_each_holder_settles_separately(self):
        record_job_advance(self.job, PRODUCER, 20_000_000)
        record_job_advance(self.job, FOUNDER, 6_000_000)
        frappe.set_user(PRODUCER)
        log_job_expense(self.job, 17_500_000, category="Thiết bị")
        frappe.set_user(FOUNDER)
        log_job_expense(self.job, 9_000_000, category="Nhân sự")

        settle_job(self.job, PRODUCER)

        self.assertEqual(float_of(self.job, PRODUCER)["direction"], EVEN)
        self.assertEqual(float_of(self.job, FOUNDER)["amount"], -3_000_000)

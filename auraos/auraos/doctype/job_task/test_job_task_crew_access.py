"""The crew boundary (T7.1, issue #41) - the standing permission proof.

The founder's rule, first written down in test_founder_spike_note.py: a
number someone may not see has to be unreachable through the document
API, the list API *and* global search. T7.1 puts a third kind of user on
the system - a designer or editor who opens the job they are working on
- and the money surface they must not reach is most of a job.

The design that makes the proof simple is that crew hold no permission
on Job at all. So the money half of this file is not a field-by-field
audit: it is the same three paths as the spike note, plus every job
endpoint that carries money, all answering the same way.

The second half proves the reach they *do* have is exactly one job's
task plan, and that the only thing they may write is their own card.

Runs via: bench --site <site> run-tests --app auraos
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import global_search

from auraos import api
from auraos.api import (
    create_job_from_deal,
    save_job_task,
    set_job_task_note,
    set_job_task_status,
)
from auraos.auraos.doctype.deal.test_deal import FOUNDER, OUTSIDER, PRODUCER
from auraos.auraos.doctype.job.test_job import won_deal
from auraos.tests.utils import make_test_user

EDITOR = "crew.editor@test.auraos.local"
DESIGNER = "crew.designer@test.auraos.local"
# Crew on some other job entirely - the negative control for reach.
COLOURIST = "crew.colourist@test.auraos.local"

# The job is findable by this; the money on it is marked by the other.
# Two markers, because a crew session is *meant* to read the title.
TITLE_MARKER = "congviectuan9902"
MONEY_MARKER = "chiphibimat7741"
MONEY_AMOUNT = 8_823_000

# Every money-bearing key of a Job. If one of these ever appears in a
# crew-facing payload, the boundary has moved and this list is the
# reason the test says so by name.
MONEY_KEYS = (
    "cost_lines",
    "packages",
    "payment_milestones",
    "quote_subtotal",
    "quote_mf_amount",
    "quote_vat_amount",
    "quote_total",
    "quote_mf_pct",
    "vat_pct",
    "commission_pct",
    "deal",
)


def priced_job(title_marker):
    """A job whose title is findable and whose breakdown is marked."""
    deal = won_deal(
        title=f"TVC {title_marker}",
        commission_pct=7,
        cost_lines=[
            {
                "description": f"Đạo diễn {MONEY_MARKER}",
                "qty1": 1,
                "qty2": 3,
                "unit_price": MONEY_AMOUNT,
                "tax_type": "Cá nhân",
                "markup_pct": 20,
            },
            {
                "description": "Thuê thiết bị",
                "qty1": 2,
                "qty2": 3,
                "unit_price": 8_000_000,
                "tax_type": "Công ty",
                "markup_pct": 10,
            },
        ],
    )
    return create_job_from_deal(deal.name)["name"]


class CrewCase(FrappeTestCase):
    """Shared world: one job the crew are on, one they are not."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from frappe.desk.doctype.global_search_settings.global_search_settings import (
            update_global_search_doctypes,
        )

        # Register hook-declared doctypes in Global Search Settings -
        # normally done by migrate, which CI's fresh site never runs.
        update_global_search_doctypes()

        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)
        for crew in (EDITOR, DESIGNER, COLOURIST):
            make_test_user(crew, "Crew")

        cls.job = priced_job(TITLE_MARKER)
        cls.other_job = priced_job("congviackhac5510")

        cls.editor_task = save_job_task(
            cls.job,
            {
                "title": "Dựng bản 1",
                "craft": "Editing",
                "assigned_to": EDITOR,
                "start_date": "2026-09-01",
                "end_date": "2026-09-04",
            },
        )["name"]
        cls.designer_task = save_job_task(
            cls.job,
            {"title": "Key visual", "craft": "Design", "assigned_to": DESIGNER},
        )["name"]
        cls.other_task = save_job_task(
            cls.other_job,
            {"title": "Grade", "craft": "Colour", "assigned_to": COLOURIST},
        )["name"]

        # Global search is normally flushed on commit; tests roll back,
        # so flush the pending buffer into __global_search explicitly.
        global_search.sync_global_search()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def assertNoMoney(self, payload, path):
        """No money key, and no marked money value, anywhere in it."""
        blob = json.dumps(payload, default=str)
        self.assertNotIn(
            MONEY_MARKER,
            blob,
            f"PERMISSION LEAK: a marked cost line reached crew via {path}",
        )
        self.assertNotIn(
            str(MONEY_AMOUNT),
            blob,
            f"PERMISSION LEAK: a marked amount reached crew via {path}",
        )
        for key in MONEY_KEYS:
            self.assertNotIn(
                key,
                blob,
                f"PERMISSION LEAK: {key} reached crew via {path}",
            )


class TestCrewSeesNoMoney(CrewCase):
    # -- positive control: the producer reaches the job every way --

    def test_producer_reads_the_priced_job(self):
        from frappe.client import get

        frappe.set_user(PRODUCER)
        fetched = get("Job", name=self.job)
        self.assertIn(MONEY_MARKER, json.dumps(fetched, default=str))

    def test_producer_finds_the_job_in_search(self):
        frappe.set_user(PRODUCER)
        results = global_search.search(TITLE_MARKER)
        self.assertTrue(
            any(row.get("doctype") == "Job" for row in results),
            "positive control failed: the producer should find the job",
        )

    # -- the proof: a crew session is blind to the Job on every path --

    def test_crew_have_no_read_permission_on_job(self):
        frappe.set_user(EDITOR)
        self.assertFalse(frappe.has_permission("Job", "read"))
        self.assertFalse(frappe.has_permission("Job", "read", doc=self.job))

    def test_crew_cannot_read_the_job_via_document_api(self):
        frappe.set_user(EDITOR)
        doc = frappe.get_doc("Job", self.job)
        with self.assertRaises(frappe.PermissionError):
            doc.check_permission("read")

    def test_crew_cannot_read_the_job_via_rest_document_endpoint(self):
        # frappe.client.get backs GET /api/resource/<doctype>/<name>
        from frappe.client import get

        frappe.set_user(EDITOR)
        with self.assertRaises(frappe.PermissionError):
            get("Job", name=self.job)

    def test_crew_cannot_list_jobs(self):
        frappe.set_user(EDITOR)
        with self.assertRaises(frappe.PermissionError):
            frappe.get_list("Job")

    def test_crew_cannot_list_jobs_via_rest_list_endpoint(self):
        # frappe.client.get_list backs GET /api/resource/<doctype>
        from frappe.client import get_list

        frappe.set_user(EDITOR)
        with self.assertRaises(frappe.PermissionError):
            get_list("Job")

    def test_crew_cannot_global_search_a_job(self):
        frappe.set_user(EDITOR)
        results = global_search.search(TITLE_MARKER)
        leaked = [row for row in results if row.get("doctype") == "Job"]
        self.assertEqual(
            leaked, [], "PERMISSION LEAK: crew found a job via global search"
        )

    def test_crew_cannot_reach_the_deal_the_pricing_lives_on(self):
        frappe.set_user(EDITOR)
        self.assertFalse(frappe.has_permission("Deal", "read"))
        with self.assertRaises(frappe.PermissionError):
            frappe.get_list("Deal")

    def test_every_money_endpoint_of_a_job_refuses_crew(self):
        """The endpoints, not only the doctype.

        Each of these gates on Job read, which crew do not have - this
        is the test that would fail the day one of them stops asking.
        """
        frappe.set_user(EDITOR)
        for call in (
            lambda: api.job_money(self.job),
            lambda: api.job_milestones(self.job),
            lambda: api.job_expense_categories(self.job),
            lambda: api.jobs_by_deal(),
            lambda: api.overdue_milestones(),
            lambda: api.assignable_users(),
        ):
            with self.assertRaises(frappe.PermissionError):
                call()

    def test_crew_cannot_write_to_the_job(self):
        frappe.set_user(EDITOR)
        with self.assertRaises(frappe.PermissionError):
            api.log_job_revision(self.job, "Sửa giúp em")
        with self.assertRaises(frappe.PermissionError):
            save_job_task(self.job, {"title": "Việc em tự thêm"})

    # -- what crew are handed instead, checked for money --

    def test_the_crew_job_view_carries_no_money(self):
        frappe.set_user(EDITOR)
        self.assertNoMoney(api.crew_job(self.job), "crew_job")

    def test_the_crew_job_list_carries_no_money(self):
        frappe.set_user(EDITOR)
        self.assertNoMoney(api.my_jobs(), "my_jobs")

    def test_the_task_plan_carries_no_money(self):
        frappe.set_user(EDITOR)
        self.assertNoMoney(api.job_tasks(self.job), "job_tasks")

    def test_the_crew_job_view_still_says_what_the_job_is(self):
        """Blind to the money, not blind to the work."""
        frappe.set_user(EDITOR)
        view = api.crew_job(self.job)
        self.assertEqual(view["name"], self.job)
        self.assertIn(TITLE_MARKER, view["title"])
        self.assertTrue(view["stage"])
        self.assertEqual(len(api.job_tasks(self.job)["tasks"]), 2)

    def test_a_job_task_declares_no_money_field(self):
        """The standing guard on the doctype crew can read.

        Tasks are pure scheduling by decision, not by accident; the day
        someone adds a rate to a task, this is what says so.
        """
        money_types = {"Currency", "Float", "Percent"}
        money_words = ("amount", "price", "rate", "cost", "pct", "fee", "budget")
        for field in frappe.get_meta("Job Task").fields:
            self.assertNotIn(
                field.fieldtype,
                money_types,
                f"a task must carry no money: {field.fieldname} is {field.fieldtype}",
            )
            for word in money_words:
                self.assertNotIn(
                    word,
                    field.fieldname,
                    f"a task must carry no money: {field.fieldname}",
                )


class TestCrewReach(CrewCase):
    """One job's plan, and one card on it."""

    def test_crew_read_their_own_task(self):
        from frappe.client import get

        frappe.set_user(EDITOR)
        self.assertEqual(get("Job Task", name=self.editor_task)["assigned_to"], EDITOR)

    def test_crew_read_the_whole_plan_of_the_job_they_are_on(self):
        """A board showing one card is not a board."""
        from frappe.client import get

        frappe.set_user(EDITOR)
        self.assertEqual(get("Job Task", name=self.designer_task)["title"], "Key visual")
        titles = {row.title for row in api.job_tasks(self.job)["tasks"]}
        self.assertEqual(titles, {"Dựng bản 1", "Key visual"})

    def test_crew_cannot_read_a_task_on_a_job_they_are_not_on(self):
        from frappe.client import get

        frappe.set_user(EDITOR)
        with self.assertRaises(frappe.PermissionError):
            get("Job Task", name=self.other_task)

    def test_the_crew_task_list_holds_only_their_jobs(self):
        frappe.set_user(EDITOR)
        names = frappe.get_list("Job Task", pluck="name", limit_page_length=0)
        self.assertIn(self.editor_task, names)
        self.assertIn(self.designer_task, names)
        self.assertNotIn(
            self.other_task,
            names,
            "PERMISSION LEAK: crew listed a task on a job they are not on",
        )

    def test_crew_cannot_open_the_plan_of_a_job_they_are_not_on(self):
        frappe.set_user(EDITOR)
        with self.assertRaises(frappe.PermissionError):
            api.job_tasks(self.other_job)
        with self.assertRaises(frappe.PermissionError):
            api.crew_job(self.other_job)

    def test_my_jobs_is_the_jobs_they_hold_a_task_on(self):
        frappe.set_user(EDITOR)
        mine = [row["name"] for row in api.my_jobs()]
        self.assertIn(self.job, mine)
        self.assertNotIn(
            self.other_job,
            mine,
            "PERMISSION LEAK: a job with no task of theirs reached a crew list",
        )

    def test_my_jobs_counts_only_their_own_open_work(self):
        frappe.set_user(EDITOR)
        row = next(row for row in api.my_jobs() if row["name"] == self.job)
        # Two tasks on the job, one of them theirs and not yet done.
        self.assertEqual(row["task_count"], 2)
        self.assertEqual(row["open_tasks"], 1)

    def test_crew_with_no_task_reach_nothing(self):
        make_test_user("crew.idle@test.auraos.local", "Crew")
        frappe.set_user("crew.idle@test.auraos.local")
        self.assertEqual(api.my_jobs(), [])
        self.assertEqual(frappe.get_list("Job Task", limit_page_length=0), [])

    def test_an_outsider_reads_no_task_at_all(self):
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            frappe.get_list("Job Task")


class TestCrewWrites(CrewCase):
    """The one write: their own card, and only its status or note."""

    def test_crew_move_their_own_card(self):
        frappe.set_user(EDITOR)
        moved = set_job_task_status(self.editor_task, "In progress")
        self.assertEqual(moved["status"], "In progress")
        set_job_task_status(self.editor_task, "To do")

    def test_crew_cannot_move_someone_elses_card(self):
        frappe.set_user(EDITOR)
        with self.assertRaises(frappe.PermissionError):
            set_job_task_status(self.designer_task, "Done")

    def test_crew_cannot_move_a_card_on_another_job(self):
        frappe.set_user(EDITOR)
        with self.assertRaises(frappe.PermissionError):
            set_job_task_status(self.other_task, "Done")

    def test_crew_cannot_rewrite_the_plan_around_their_card(self):
        frappe.set_user(EDITOR)
        for field, value in (
            ("title", "Việc khác"),
            ("assigned_to", DESIGNER),
            ("start_date", "2026-10-01"),
            ("end_date", "2026-10-09"),
            ("craft", "Colour"),
            ("job", self.other_job),
        ):
            task = frappe.get_doc("Job Task", self.editor_task)
            task.set(field, value)
            with self.assertRaises(frappe.PermissionError):
                task.save()

    def test_crew_may_note_what_they_did(self):
        frappe.set_user(EDITOR)
        task = frappe.get_doc("Job Task", self.editor_task)
        task.notes = "Đã gửi bản nháp"
        task.save()
        self.assertEqual(
            frappe.db.get_value("Job Task", self.editor_task, "notes"),
            "Đã gửi bản nháp",
        )

    def test_the_note_endpoint_answers_the_same_way(self):
        frappe.set_user(EDITOR)
        set_job_task_note(self.editor_task, "Đang chờ logo của khách")
        self.assertEqual(
            frappe.db.get_value("Job Task", self.editor_task, "notes"),
            "Đang chờ logo của khách",
        )
        with self.assertRaises(frappe.PermissionError):
            set_job_task_note(self.designer_task, "Không phải việc của em")

    def test_crew_cannot_add_a_task(self):
        frappe.set_user(EDITOR)
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc(
                {"doctype": "Job Task", "job": self.job, "title": "Việc em tự thêm"}
            ).insert()

    def test_crew_cannot_delete_a_task(self):
        frappe.set_user(EDITOR)
        with self.assertRaises(frappe.PermissionError):
            frappe.delete_doc("Job Task", self.editor_task)

    def test_a_producer_who_is_also_crew_is_still_a_producer(self):
        """Holding the Crew role never takes an operating role away."""
        frappe.set_user("Administrator")
        both = "producer.editor@test.auraos.local"
        make_test_user(both, "Producer")
        make_test_user(both, "Crew")
        frappe.set_user(both)
        self.assertTrue(frappe.has_permission("Job", "read", doc=self.job))
        self.assertTrue(api.job_tasks(self.other_job)["can_plan"])

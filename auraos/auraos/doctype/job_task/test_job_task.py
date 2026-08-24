"""Seam tests for the scheduling half of T7.1 (issue #41).

The task itself: what it may hold, what order it reads in, and the
narrow endpoint the planner writes through. The crew half - who may see
any of it - is proven separately in test_job_task_crew_access.py.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import (
    create_job_from_deal,
    delete_job_task,
    job_tasks,
    save_job_task,
    set_job_task_status,
)
from auraos.auraos.doctype.deal.test_deal import FOUNDER, OUTSIDER, PRODUCER
from auraos.auraos.doctype.job.test_job import won_deal
from auraos.auraos.doctype.job_task.job_task import DEFAULT_STATUS, STATUSES
from auraos.tests.utils import make_test_user

EDITOR = "editor@test.auraos.local"


def make_job():
    return create_job_from_deal(won_deal().name)["name"]


class TestJobTaskShape(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(EDITOR, "Crew")

    def setUp(self):
        frappe.set_user("Administrator")
        self.job = make_job()

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def task(self, **values):
        values.setdefault("title", "Dựng bản 1")
        return frappe.get_doc({"doctype": "Job Task", "job": self.job, **values}).insert()

    def test_a_task_holds_the_plan_and_nothing_else(self):
        task = self.task(
            craft="Editing",
            assigned_to=EDITOR,
            start_date="2026-09-01",
            end_date="2026-09-04",
            notes="Theo brief v2",
        )
        stored = frappe.get_doc("Job Task", task.name)
        self.assertEqual(stored.job, self.job)
        self.assertEqual(stored.craft, "Editing")
        self.assertEqual(stored.assigned_to, EDITOR)
        self.assertEqual(str(stored.start_date), "2026-09-01")
        self.assertEqual(str(stored.end_date), "2026-09-04")
        self.assertEqual(stored.notes, "Theo brief v2")

    def test_a_new_task_starts_to_do(self):
        self.assertEqual(self.task().status, DEFAULT_STATUS)

    def test_the_status_set_is_the_board(self):
        self.assertEqual(
            list(STATUSES),
            ["To do", "In progress", "Blocked", "In review", "Done"],
        )
        self.assertEqual(
            frappe.get_meta("Job Task").get_field("status").options.split("\n"),
            list(STATUSES),
        )

    def test_an_unknown_status_is_rejected(self):
        task = self.task()
        task.status = "Almost"
        with self.assertRaises(frappe.ValidationError):
            task.save()

    def test_a_task_needs_a_title(self):
        with self.assertRaises(frappe.ValidationError):
            self.task(title="   ")

    def test_a_task_may_be_undated(self):
        """Work gets written down before it gets scheduled."""
        task = self.task(title="Grade")
        self.assertIsNone(task.start_date)
        self.assertIsNone(task.end_date)

    def test_a_task_cannot_be_due_before_it_starts(self):
        with self.assertRaises(frappe.ValidationError):
            self.task(start_date="2026-09-10", end_date="2026-09-02")

    def test_dated_work_reads_first_and_in_date_order(self):
        self.task(title="Undated")
        self.task(title="Later", start_date="2026-09-20", end_date="2026-09-21")
        self.task(title="Earlier", start_date="2026-09-02", end_date="2026-09-03")
        titles = [row.title for row in job_tasks(self.job)["tasks"]]
        self.assertEqual(titles, ["Earlier", "Later", "Undated"])

    def test_the_plan_of_one_job_is_not_the_plan_of_another(self):
        self.task(title="On this job")
        other = make_job()
        frappe.get_doc(
            {"doctype": "Job Task", "job": other, "title": "On the other job"}
        ).insert()
        self.assertEqual(
            [row.title for row in job_tasks(self.job)["tasks"]], ["On this job"]
        )


class TestJobTaskPlanning(FrappeTestCase):
    """The planner's endpoint: one narrow surface, both operating roles."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)
        make_test_user(EDITOR, "Crew")

    def setUp(self):
        frappe.set_user("Administrator")
        self.job = make_job()

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def test_save_creates_then_updates_the_same_task(self):
        created = save_job_task(
            self.job,
            {"title": "Dựng bản 1", "craft": "Editing", "assigned_to": EDITOR},
        )
        updated = save_job_task(
            self.job, {"name": created["name"], "title": "Dựng bản 2"}
        )
        self.assertEqual(updated["name"], created["name"])
        self.assertEqual(updated["title"], "Dựng bản 2")
        self.assertEqual(updated["assigned_to"], EDITOR)
        self.assertEqual(len(job_tasks(self.job)["tasks"]), 1)

    def test_a_field_outside_the_plan_is_refused_by_name(self):
        with self.assertRaises(frappe.ValidationError):
            save_job_task(self.job, {"title": "Dựng", "amount": 5_000_000})

    def test_a_task_cannot_be_moved_onto_another_job(self):
        created = save_job_task(self.job, {"title": "Dựng"})
        other = make_job()
        with self.assertRaises(frappe.ValidationError):
            save_job_task(other, {"name": created["name"], "title": "Dựng"})

    def test_deleting_a_task_drops_it_from_the_plan(self):
        created = save_job_task(self.job, {"title": "Dựng"})
        delete_job_task(created["name"])
        self.assertEqual(job_tasks(self.job)["tasks"], [])

    def test_both_operating_roles_plan(self):
        for user in (FOUNDER, PRODUCER):
            frappe.set_user(user)
            created = save_job_task(self.job, {"title": f"Task by {user}"})
            self.assertTrue(created["name"])
            self.assertTrue(job_tasks(self.job)["can_plan"])

    def test_an_outsider_reaches_no_plan_at_all(self):
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            job_tasks(self.job)
        with self.assertRaises(frappe.PermissionError):
            save_job_task(self.job, {"title": "Dựng"})

    def test_a_missing_job_reads_as_missing_not_forbidden(self):
        with self.assertRaises(frappe.DoesNotExistError):
            job_tasks("JOB-9999")

    def test_the_planner_moves_a_card_too(self):
        created = save_job_task(self.job, {"title": "Dựng", "assigned_to": EDITOR})
        frappe.set_user(PRODUCER)
        moved = set_job_task_status(created["name"], "In review")
        self.assertEqual(moved["status"], "In review")

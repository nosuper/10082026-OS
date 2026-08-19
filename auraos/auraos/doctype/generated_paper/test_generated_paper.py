"""Seam tests for #106: has the client actually signed it?

`tests/test_paper_status.py` proves the vocabulary and the no-order rule
without Frappe. What can only be proved here is the wiring:

1. **A paper starts as Draft** the moment it is generated, and every
   paper generated before the field existed reads as Draft too.
2. **A producer can move one.** Marking a contract signed is operational
   bookkeeping, not privileged information, so the Generated Paper
   permission was widened from create to create-and-write - and no
   further: a producer still cannot delete a registry row.
3. **Every move records who and when**, because "who told me this was
   signed" is the question asked when a contract turns out to be
   missing.
4. **Both read paths carry the status as a field**, never as a sentence.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime

from auraos.api import generated_papers, job_paperwork, set_paper_status
from auraos.auraos.doctype.deal.test_deal import FOUNDER, OUTSIDER, PRODUCER
from auraos.auraos.doctype.paperwork_template.test_paperwork_template import (
    make_job,
    make_template,
)
from auraos.lib.paper_status import AWAITING_SIGNATURE, DRAFT, SIGNED, STATUSES
from auraos.tests.utils import make_test_user


class TestGeneratedPaperStatus(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")
        self.template = make_template()
        self.job = make_job(tax_code="0312345678")

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def generate(self, as_user=PRODUCER):
        """One paper on this job, generated the way the screen does it."""
        from auraos.api import generate_job_paperwork

        frappe.set_user(as_user)
        generate_job_paperwork(job=self.job.name, template=self.template.name)
        frappe.set_user("Administrator")
        return frappe.get_last_doc("Generated Paper", filters={"job": self.job.name})

    def test_a_newly_generated_paper_is_a_draft(self):
        paper = self.generate()

        self.assertEqual(paper.status, DRAFT)
        self.assertEqual(paper.status_changed_by, PRODUCER)
        self.assertTrue(paper.status_changed_on)

    def test_a_producer_can_move_a_paper_all_the_way_to_signed(self):
        """Nothing about this is founder-only."""
        paper = self.generate()

        frappe.set_user(PRODUCER)
        sent = set_paper_status(paper=paper.name, status=AWAITING_SIGNATURE)
        signed = set_paper_status(paper=paper.name, status=SIGNED)

        self.assertEqual(sent["status"], AWAITING_SIGNATURE)
        self.assertEqual(signed["status"], SIGNED)
        self.assertEqual(
            frappe.db.get_value("Generated Paper", paper.name, "status"), SIGNED
        )

    def test_a_paper_can_be_moved_back_to_draft(self):
        """A real document sometimes has to be redone."""
        paper = self.generate()

        frappe.set_user(PRODUCER)
        set_paper_status(paper=paper.name, status=SIGNED)
        back = set_paper_status(paper=paper.name, status=DRAFT)

        self.assertEqual(back["status"], DRAFT)
        self.assertEqual(
            frappe.db.get_value("Generated Paper", paper.name, "status"), DRAFT
        )

    def test_the_move_records_who_made_it_and_when(self):
        paper = self.generate(as_user=PRODUCER)
        generated_at = get_datetime(paper.status_changed_on)

        frappe.set_user(FOUNDER)
        moved = set_paper_status(paper=paper.name, status=SIGNED)

        self.assertEqual(moved["status_changed_by"], FOUNDER)
        self.assertTrue(moved["status_changed_by_label"])
        self.assertGreaterEqual(get_datetime(moved["status_changed_on"]), generated_at)

    def test_a_move_that_changes_nothing_else_leaves_the_paper_alone(self):
        paper = self.generate()

        frappe.set_user(PRODUCER)
        set_paper_status(paper=paper.name, status=SIGNED)
        stored = frappe.get_doc("Generated Paper", paper.name)

        self.assertEqual(stored.file_url, paper.file_url)
        self.assertEqual(stored.job, paper.job)
        self.assertEqual(stored.template_name, paper.template_name)

    def test_a_status_outside_the_three_is_refused_in_words(self):
        paper = self.generate()

        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.ValidationError) as refusal:
            set_paper_status(paper=paper.name, status="Posted")

        self.assertIn("Posted", str(refusal.exception))
        self.assertEqual(
            frappe.db.get_value("Generated Paper", paper.name, "status"), DRAFT
        )

    def test_a_paper_written_before_the_field_existed_reads_as_draft(self):
        """What the backfill patch fixes, proved from the read paths."""
        paper = self.generate()
        frappe.db.set_value(
            "Generated Paper", paper.name, "status", "", update_modified=False
        )

        frappe.set_user(PRODUCER)
        listed = {row["name"]: row for row in generated_papers()}
        on_job = job_paperwork(self.job.name)

        self.assertEqual(listed[paper.name]["status"], DRAFT)
        self.assertEqual(on_job[0]["status"], DRAFT)

    def test_the_registry_carries_the_status_as_a_field(self):
        """Structured, never a sentence: the screen writes the words."""
        paper = self.generate()

        frappe.set_user(PRODUCER)
        set_paper_status(paper=paper.name, status=AWAITING_SIGNATURE)
        row = {row["name"]: row for row in generated_papers()}[paper.name]

        self.assertIn(row["status"], STATUSES)
        self.assertEqual(row["status"], AWAITING_SIGNATURE)
        self.assertEqual(row["status_changed_by"], PRODUCER)

    def test_the_job_tab_ties_each_file_to_its_registry_row(self):
        paper = self.generate()

        frappe.set_user(PRODUCER)
        set_paper_status(paper=paper.name, status=SIGNED)
        row = job_paperwork(self.job.name)[0]

        self.assertEqual(row["paper"], paper.name)
        self.assertEqual(row["status"], SIGNED)

    def test_a_producer_still_cannot_delete_a_registry_row(self):
        """Write was widened for the status; nothing else was."""
        paper = self.generate()

        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            frappe.delete_doc("Generated Paper", paper.name)

    def test_someone_who_cannot_see_the_job_cannot_touch_its_papers(self):
        paper = self.generate()

        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            set_paper_status(paper=paper.name, status=SIGNED)

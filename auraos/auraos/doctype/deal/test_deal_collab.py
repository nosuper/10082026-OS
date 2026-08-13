"""Seam tests for T3.1 (issue #20): collaboration on the deal card -
comments, file attachments, and labelled links.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import add_deal_comment, deal_attachments, deal_comments
from auraos.auraos.doctype.deal.test_deal import (
    FOUNDER,
    OUTSIDER,
    PRODUCER,
    make_deal,
)
from auraos.tests.utils import make_test_user


def attach_file(deal_name, file_name="brief.txt"):
    """Attach a file the way upload_file does: a File doc pointing at
    the deal, inserted as the session user."""
    return frappe.get_doc(
        {
            "doctype": "File",
            "file_name": file_name,
            "content": "nội dung brief",
            "attached_to_doctype": "Deal",
            "attached_to_name": deal_name,
        }
    ).insert()


class TestDealCollab(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")
        self.deal = make_deal(title="Collab probe")

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    # -- comments --

    def test_both_operating_roles_comment_and_read_the_thread(self):
        frappe.set_user(FOUNDER)
        add_deal_comment(self.deal.name, "Khách muốn quay trước Tết")
        frappe.set_user(PRODUCER)
        add_deal_comment(self.deal.name, "Đã book đạo diễn")

        thread = deal_comments(self.deal.name)
        self.assertEqual(len(thread), 2)
        self.assertIn("trước Tết", thread[0].content)
        self.assertEqual(thread[0].comment_email, FOUNDER)
        self.assertIn("đạo diễn", thread[1].content)
        self.assertEqual(thread[1].comment_email, PRODUCER)
        self.assertTrue(all(row.creation for row in thread))

    def test_empty_comment_is_rejected(self):
        frappe.set_user(FOUNDER)
        with self.assertRaises(frappe.ValidationError):
            add_deal_comment(self.deal.name, "   ")

    def test_comment_on_missing_deal_fails(self):
        frappe.set_user(FOUNDER)
        with self.assertRaises(frappe.DoesNotExistError):
            add_deal_comment("DEAL-does-not-exist", "hello")

    def test_outsider_cannot_comment_or_read_thread(self):
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            add_deal_comment(self.deal.name, "sneaky")
        with self.assertRaises(frappe.PermissionError):
            deal_comments(self.deal.name)

    # -- attachments --

    def test_both_operating_roles_attach_and_list_files(self):
        frappe.set_user(FOUNDER)
        attach_file(self.deal.name, "brief-v1.txt")
        frappe.set_user(PRODUCER)
        attach_file(self.deal.name, "moodboard.txt")

        rows = deal_attachments(self.deal.name)
        names = [row.file_name for row in rows]
        self.assertIn("brief-v1.txt", names)
        self.assertIn("moodboard.txt", names)
        self.assertTrue(all(row.file_url for row in rows))

    def test_outsider_cannot_attach_or_list_files(self):
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            attach_file(self.deal.name)
        with self.assertRaises(frappe.PermissionError):
            deal_attachments(self.deal.name)

    # -- links --

    def test_labelled_links_persist_across_roles(self):
        frappe.set_user(FOUNDER)
        deal = make_deal(
            title="Linked deal",
            deal_owner=FOUNDER,
            deal_links=[
                {
                    "label": "Drive folder",
                    "url": "https://drive.google.com/drive/folders/abc",
                },
                {"label": "Ref video", "url": "https://vimeo.com/123"},
            ],
        )
        frappe.set_user(PRODUCER)
        reloaded = frappe.get_doc("Deal", deal.name)
        self.assertEqual(
            [(row.label, row.url) for row in reloaded.deal_links],
            [
                ("Drive folder", "https://drive.google.com/drive/folders/abc"),
                ("Ref video", "https://vimeo.com/123"),
            ],
        )

    def test_producer_can_add_a_link(self):
        frappe.set_user(PRODUCER)
        deal = frappe.get_doc("Deal", self.deal.name)
        deal.append(
            "deal_links", {"label": "Moodboard", "url": "https://miro.com/m/1"}
        )
        deal.save()
        self.assertEqual(
            frappe.get_doc("Deal", deal.name).deal_links[0].label, "Moodboard"
        )

    def test_link_requires_label_and_url(self):
        with self.assertRaises(frappe.MandatoryError):
            make_deal(deal_links=[{"url": "https://example.com"}])
        with self.assertRaises(frappe.MandatoryError):
            make_deal(deal_links=[{"label": "no url"}])

    def test_invalid_url_is_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            make_deal(deal_links=[{"label": "bad", "url": "not a url"}])

    def test_outsider_cannot_read_or_add_links(self):
        deal = make_deal(
            title="Linked, outsider probe",
            deal_links=[{"label": "Drive", "url": "https://drive.google.com/x"}],
        )
        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc("Deal", deal.name).check_permission("read")
        loaded = frappe.get_doc("Deal", deal.name)
        loaded.append(
            "deal_links", {"label": "sneaky", "url": "https://evil.example"}
        )
        with self.assertRaises(frappe.PermissionError):
            loaded.save()

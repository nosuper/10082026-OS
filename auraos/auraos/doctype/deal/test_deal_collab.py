"""Seam tests for collaboration on the deal card.

T3.1 (issue #20) built the thread, the attachments and the labelled
links. T3.4 (issue #28) is the founder's answer to what was missing:
naming the other seat, rewriting or removing your own words, pasting a
screenshot into a comment, and one page that lists every file across
every deal.

Two rules are the point of the T3.4 half, and both are proved here
rather than assumed:

- **Your own words only.** Both seats have full write on every deal, so
  document permissions alone would let either rewrite the other's
  comment. The thread carries a second gate.
- **The deal is the boundary for files.** Core File lets any System
  User read a File row, so the file manager scopes by the deals the
  caller may list, and renames and deletions gate on writing the deal
  the file hangs on.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import (
    add_deal_comment,
    deal_attachments,
    deal_comments,
    deal_files,
    delete_deal_comment,
    delete_deal_file,
    edit_deal_comment,
    rename_deal_file,
)
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


# -- T3.4 (issue #28): mentions, own-comment edit/delete, inline images --

MENTION = (
    '<span class="mention" data-type="mention" '
    'data-id="{user}" data-label="{label}">@{label}</span>'
)


def mention(user, label="Linh"):
    """The markup the comment editor produces for a named seat."""
    return MENTION.format(user=user, label=label)


def mention_notifications(user, deal):
    return frappe.get_all(
        "Notification Log",
        filters={
            "for_user": user,
            "type": "Mention",
            "document_type": "Deal",
            "document_name": deal,
        },
        fields=["name", "subject"],
    )


class TestDealCommentUpgrades(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")
        self.deal = make_deal(title="Thread probe")

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def founder_says(self, content):
        frappe.set_user(FOUNDER)
        return add_deal_comment(self.deal.name, content)

    # -- mentions --

    def test_naming_the_other_seat_notifies_them(self):
        """Once, not twice. Core notifies a mention when the Comment is
        inserted, so this endpoint must not do it again."""
        self.founder_says(f"<p>{mention(PRODUCER)} xem giúp nhé</p>")

        rows = mention_notifications(PRODUCER, self.deal.name)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0].subject)

    def test_the_at_name_stays_readable_in_the_thread(self):
        self.founder_says(f"<p>{mention(PRODUCER, 'Linh')} xem giúp nhé</p>")

        frappe.set_user(PRODUCER)
        thread = deal_comments(self.deal.name)
        self.assertIn("@Linh", thread[0]["content"])

    def test_a_comment_naming_nobody_notifies_nobody(self):
        self.founder_says("<p>khách muốn quay trước Tết</p>")
        self.assertEqual(mention_notifications(PRODUCER, self.deal.name), [])

    def test_naming_yourself_notifies_nobody(self):
        self.founder_says(f"<p>{mention(FOUNDER, 'Chung')} ghi chú cho mình</p>")
        self.assertEqual(mention_notifications(FOUNDER, self.deal.name), [])

    def test_naming_someone_outside_the_operating_seats_notifies_nobody(self):
        """The ids arrive from a browser, so they are checked, not trusted."""
        self.founder_says(f"<p>{mention(OUTSIDER, 'Ai đó')} hi</p>")
        self.assertEqual(mention_notifications(OUTSIDER, self.deal.name), [])

    def test_a_mention_notifies_each_named_seat_once(self):
        self.founder_says(f"<p>{mention(PRODUCER)} và {mention(PRODUCER)} nhé</p>")
        self.assertEqual(len(mention_notifications(PRODUCER, self.deal.name)), 1)

    # -- inline images --

    def test_a_pasted_image_survives_into_the_thread(self):
        self.founder_says(
            '<p>tham khảo:</p><p><img src="/private/files/moodboard.png"></p>'
        )

        frappe.set_user(PRODUCER)
        thread = deal_comments(self.deal.name)
        self.assertIn("/private/files/moodboard.png", thread[0]["content"])
        self.assertIn("<img", thread[0]["content"])

    def test_a_comment_that_is_only_an_image_is_accepted(self):
        row = self.founder_says('<p><img src="/private/files/shot.png"></p>')
        self.assertTrue(row["name"])

    def test_an_empty_editor_is_still_rejected(self):
        frappe.set_user(FOUNDER)
        for empty in ("<p></p>", "<p><br></p>", "   "):
            with self.assertRaises(frappe.ValidationError):
                add_deal_comment(self.deal.name, empty)

    def test_a_script_pasted_into_a_comment_is_scrubbed(self):
        row = self.founder_says("<p>ok</p><script>alert(1)</script>")
        self.assertNotIn("<script", row["content"])

    # -- editing your own comment --

    def test_you_may_rewrite_your_own_comment(self):
        row = self.founder_says("<p>quay trước Tết</p>")
        edited = edit_deal_comment(row["name"], "<p>quay sau Tết</p>")

        self.assertIn("sau Tết", edited["content"])
        thread = deal_comments(self.deal.name)
        self.assertEqual(len(thread), 1)
        self.assertIn("sau Tết", thread[0]["content"])

    def test_a_fresh_comment_is_not_marked_edited(self):
        self.founder_says("<p>quay trước Tết</p>")
        self.assertFalse(deal_comments(self.deal.name)[0]["edited"])

    def test_a_rewritten_comment_is_marked_edited(self):
        row = self.founder_says("<p>quay trước Tết</p>")
        edit_deal_comment(row["name"], "<p>quay sau Tết</p>")
        self.assertTrue(deal_comments(self.deal.name)[0]["edited"])

    def test_the_other_seat_cannot_rewrite_your_comment(self):
        row = self.founder_says("<p>quay trước Tết</p>")

        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            edit_deal_comment(row["name"], "<p>đã đổi lời của sếp</p>")

        frappe.set_user(FOUNDER)
        self.assertIn("trước Tết", deal_comments(self.deal.name)[0]["content"])

    def test_an_edit_cannot_empty_a_comment(self):
        row = self.founder_says("<p>quay trước Tết</p>")
        with self.assertRaises(frappe.ValidationError):
            edit_deal_comment(row["name"], "<p></p>")
        self.assertIn("trước Tết", deal_comments(self.deal.name)[0]["content"])

    def test_an_edit_notifies_only_the_newly_named(self):
        row = self.founder_says(f"<p>{mention(PRODUCER)} xem giúp</p>")
        edit_deal_comment(
            row["name"], f"<p>{mention(PRODUCER)} xem giúp trước thứ 6</p>"
        )
        self.assertEqual(len(mention_notifications(PRODUCER, self.deal.name)), 1)

    def test_naming_someone_for_the_first_time_in_an_edit_notifies_them(self):
        row = self.founder_says("<p>xem giúp</p>")
        self.assertEqual(mention_notifications(PRODUCER, self.deal.name), [])
        edit_deal_comment(row["name"], f"<p>{mention(PRODUCER)} xem giúp</p>")
        self.assertEqual(len(mention_notifications(PRODUCER, self.deal.name)), 1)

    # -- deleting your own comment --

    def test_you_may_delete_your_own_comment(self):
        row = self.founder_says("<p>nhầm deal</p>")
        delete_deal_comment(row["name"])
        self.assertEqual(deal_comments(self.deal.name), [])

    def test_the_other_seat_cannot_delete_your_comment(self):
        row = self.founder_says("<p>quay trước Tết</p>")

        frappe.set_user(PRODUCER)
        with self.assertRaises(frappe.PermissionError):
            delete_deal_comment(row["name"])

        frappe.set_user(FOUNDER)
        self.assertEqual(len(deal_comments(self.deal.name)), 1)

    def test_an_outsider_cannot_edit_or_delete_anything_in_the_thread(self):
        row = self.founder_says("<p>quay trước Tết</p>")

        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            edit_deal_comment(row["name"], "<p>sneaky</p>")
        with self.assertRaises(frappe.PermissionError):
            delete_deal_comment(row["name"])

    def test_the_thread_says_which_rows_are_yours(self):
        self.founder_says("<p>của sếp</p>")
        frappe.set_user(PRODUCER)
        add_deal_comment(self.deal.name, "<p>của Linh</p>")

        thread = deal_comments(self.deal.name)
        self.assertEqual([row["mine"] for row in thread], [False, True])

        frappe.set_user(FOUNDER)
        thread = deal_comments(self.deal.name)
        self.assertEqual([row["mine"] for row in thread], [True, False])

    def test_a_comment_on_another_doctype_is_not_a_deal_comment(self):
        frappe.set_user("Administrator")
        note = frappe.get_doc(
            {"doctype": "Founder Spike Note", "title": "Không phải deal"}
        ).insert()
        elsewhere = note.add_comment("Comment", text="<p>không phải deal</p>")

        frappe.set_user(FOUNDER)
        with self.assertRaises(frappe.ValidationError):
            edit_deal_comment(elsewhere.name, "<p>sneaky</p>")
        with self.assertRaises(frappe.ValidationError):
            delete_deal_comment(elsewhere.name)


# -- T3.4 (issue #28): the file manager --


class TestDealFileManager(FrappeTestCase):
    """The listing spans every deal in the site, so nothing here may
    assume it is the only thing that ever attached a file. Each test
    names its files after the deal they hang on and reads the listing
    back through that deal's own filter."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")
        self.first = make_deal(title="Files probe one")
        self.second = make_deal(title="Files probe two")

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def attach(self, deal, label):
        """Attach a file named so it cannot collide with another test's."""
        return attach_file(deal.name, f"{deal.name}-{label}.txt")

    def named(self, deal, label):
        return f"{deal.name}-{label}.txt"

    def rows_for(self, **filters):
        listing = deal_files(**filters)
        return {row["file_name"]: row for row in listing["files"]}

    def test_files_from_every_deal_land_in_one_listing(self):
        frappe.set_user(FOUNDER)
        self.attach(self.first, "brief")
        frappe.set_user(PRODUCER)
        self.attach(self.second, "moodboard")

        rows = self.rows_for()
        self.assertIn(self.named(self.first, "brief"), rows)
        self.assertIn(self.named(self.second, "moodboard"), rows)

    def test_a_row_carries_the_deal_it_hangs_on(self):
        frappe.set_user(FOUNDER)
        self.attach(self.first, "brief")

        row = self.rows_for(deal=self.first.name)[self.named(self.first, "brief")]
        self.assertEqual(row["deal"], self.first.name)
        self.assertEqual(row["deal_title"], "Files probe one")

    def test_a_row_says_whether_the_file_is_private(self):
        """The flag travels rather than being assumed - client sharing
        later must not have to unpick a private-only listing."""
        frappe.set_user(FOUNDER)
        self.attach(self.first, "brief")

        row = self.rows_for(deal=self.first.name)[self.named(self.first, "brief")]
        self.assertIn("is_private", row)

    def test_the_deal_filter_narrows_without_emptying_the_dropdown(self):
        frappe.set_user(FOUNDER)
        self.attach(self.first, "brief")
        self.attach(self.second, "moodboard")

        listing = deal_files(deal=self.first.name)
        self.assertEqual(
            [row["file_name"] for row in listing["files"]],
            [self.named(self.first, "brief")],
        )
        # The choices come from the unfiltered set, so the filter that
        # got you here is still on offer.
        offered = [row["name"] for row in listing["deals"]]
        self.assertIn(self.first.name, offered)
        self.assertIn(self.second.name, offered)

    def test_the_uploader_filter_narrows_to_one_seat(self):
        frappe.set_user(FOUNDER)
        self.attach(self.first, "brief")
        frappe.set_user(PRODUCER)
        self.attach(self.first, "moodboard")

        rows = self.rows_for(deal=self.first.name, uploader=PRODUCER)
        self.assertEqual(list(rows), [self.named(self.first, "moodboard")])
        self.assertEqual(rows[self.named(self.first, "moodboard")]["owner"], PRODUCER)

    def test_the_type_filter_narrows_to_one_kind(self):
        frappe.set_user(FOUNDER)
        self.attach(self.first, "brief")
        listing = self.rows_for(deal=self.first.name)
        text_type = listing[self.named(self.first, "brief")]["file_type"]

        self.assertEqual(
            list(self.rows_for(deal=self.first.name, file_type=text_type)),
            [self.named(self.first, "brief")],
        )
        self.assertEqual(self.rows_for(deal=self.first.name, file_type="PDF"), {})

    def test_an_outsider_cannot_list_files(self):
        frappe.set_user(FOUNDER)
        self.attach(self.first, "brief")

        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            deal_files()

    def test_either_seat_may_rename_a_file(self):
        """A file is shared material, not authored speech: the rule is
        the one attaching runs on - you may manage what you may write."""
        frappe.set_user(FOUNDER)
        uploaded = self.attach(self.first, "IMG_2831")

        frappe.set_user(PRODUCER)
        renamed = f"{self.first.name}-brief khách gửi.txt"
        rename_deal_file(uploaded.name, renamed)

        self.assertIn(renamed, self.rows_for(deal=self.first.name))

    def test_a_file_cannot_be_renamed_to_nothing(self):
        frappe.set_user(FOUNDER)
        uploaded = self.attach(self.first, "brief")
        with self.assertRaises(frappe.ValidationError):
            rename_deal_file(uploaded.name, "   ")

    def test_either_seat_may_delete_a_file(self):
        frappe.set_user(FOUNDER)
        uploaded = self.attach(self.first, "nham")

        frappe.set_user(PRODUCER)
        delete_deal_file(uploaded.name)

        self.assertEqual(self.rows_for(deal=self.first.name), {})
        self.assertEqual(deal_attachments(self.first.name), [])

    def test_an_outsider_cannot_rename_or_delete_a_file(self):
        frappe.set_user(FOUNDER)
        uploaded = self.attach(self.first, "brief")

        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            rename_deal_file(uploaded.name, "stolen.txt")
        with self.assertRaises(frappe.PermissionError):
            delete_deal_file(uploaded.name)

    def test_a_file_that_hangs_on_no_deal_cannot_be_managed_here(self):
        frappe.set_user("Administrator")
        loose = frappe.get_doc(
            {"doctype": "File", "file_name": "loose.txt", "content": "x"}
        ).insert()

        frappe.set_user(FOUNDER)
        with self.assertRaises(frappe.ValidationError):
            rename_deal_file(loose.name, "renamed.txt")
        with self.assertRaises(frappe.ValidationError):
            delete_deal_file(loose.name)

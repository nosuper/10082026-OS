"""Seam tests for T11 (issue #13): docx paperwork from templates.

`tests/test_paperwork.py` proves the filling itself — split runs,
escaping, markers — without Frappe. What can only be proved here is the
wiring around it:

1. **The template library is the founder's.** A producer may read the
   templates so they can generate from them, and may not upload, edit,
   rename or delete one.
2. **A template is read from its own file.** Save it and the placeholders
   it asks for follow the docx; hand it something that is not a docx and
   it is refused with a sentence, not a stack trace.
3. **Generating reaches the real records.** The client's tax code comes
   off the Party Company, the amount off the job's carried quote, and a
   freelancer's details off whoever was picked.
4. **Missing data reaches the caller.** A client with no tax code
   produces a document and a complaint, not a silent blank.
5. **The result lands on the job**, where the next person looking for
   the contract will look — and only for people who may write that job.

Runs via: bench --site <site> run-tests --app auraos
"""

import zipfile
from io import BytesIO

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import (
    generate_job_paperwork,
    job_paperwork,
    paperwork_library,
    paperwork_templates,
)
from auraos.auraos.doctype.deal.test_deal import (
    FOUNDER,
    OUTSIDER,
    PRODUCER,
    make_company,
)
from auraos.auraos.doctype.job.job import create_from_deal
from auraos.auraos.doctype.job.test_job import won_deal
from auraos.lib.money import format_vnd
from auraos.lib.paperwork import build_docx
from auraos.tests.utils import make_test_user

CLIENT = "Công ty Chungify"

CONTRACT = [
    "HỢP ĐỒNG DỊCH VỤ",
    "Hôm nay, ngày {{today.day}} tháng {{today.month}} năm {{today.year}}",
    "Bên A: {{client.company_name}}",
    "Mã số thuế: {{client.tax_code}}",
    "Công việc: {{job.title}} ({{job.code}})",
    "Giá trị hợp đồng: {{quote.total}} đồng",
]

FREELANCER_PAPER = [
    "HỢP ĐỒNG CỘNG TÁC VIÊN",
    "Ông/Bà: {{freelancer.full_name}}",
    "CCCD: {{freelancer.id_number}}",
    "Công việc: {{job.title}}",
]


def upload(content, file_name="template.docx"):
    """A private File holding these bytes, unattached, as an upload is."""
    return frappe.get_doc(
        {
            "doctype": "File",
            "file_name": file_name,
            "is_private": 1,
            "content": content,
        }
    ).insert(ignore_permissions=True)


def make_template(paragraphs=None, template_name="Hợp đồng dịch vụ", **overrides):
    existing = frappe.db.exists("Paperwork Template", {"template_name": template_name})
    if existing:
        frappe.delete_doc("Paperwork Template", existing, force=True)
    uploaded = upload(build_docx(paragraphs or CONTRACT))
    return frappe.get_doc(
        {
            "doctype": "Paperwork Template",
            "template_name": template_name,
            "template_file": uploaded.file_url,
            **overrides,
        }
    ).insert(ignore_permissions=True)


def make_job(**company_fields):
    """A job for a client whose details are exactly what this test set.

    The client record is shared across the suite, so every field a paper
    reads is cleared and re-set here — otherwise "no tax code on file"
    would depend on which test ran first.
    """
    company = make_company(CLIENT)
    company.update({"tax_code": None, "address": None, **company_fields})
    company.save(ignore_permissions=True)
    return create_from_deal(won_deal(company=company.name).name)


def read_text(file_url):
    """Every word of a generated document, as a reader would see it."""
    import re

    content = frappe.get_doc("File", {"file_url": file_url}).get_content()
    xml = zipfile.ZipFile(BytesIO(content)).read("word/document.xml").decode()
    return "".join(re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", xml, re.DOTALL))


class TestPaperworkTemplateLibrary(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def test_a_template_lists_the_placeholders_its_own_file_asks_for(self):
        template = make_template()

        self.assertEqual(
            template.placeholders.split("\n"),
            [
                "today.day",
                "today.month",
                "today.year",
                "client.company_name",
                "client.tax_code",
                "job.title",
                "job.code",
                "quote.total",
            ],
        )

    def test_replacing_the_file_moves_the_placeholders_with_it(self):
        """The list follows the docx — there is no second step to forget."""
        template = make_template()

        template.template_file = upload(
            build_docx(["Chỉ có {{job.code}}"]), "v2.docx"
        ).file_url
        template.save(ignore_permissions=True)

        self.assertEqual(template.placeholders, "job.code")

    def test_a_file_that_is_not_a_docx_is_refused_in_words(self):
        """The real mistake: an old .doc, renamed rather than re-saved."""
        uploaded = upload(b"\xd0\xcf\x11\xe0 old Word format", "contract.docx")

        with self.assertRaises(frappe.ValidationError) as refusal:
            frappe.get_doc(
                {
                    "doctype": "Paperwork Template",
                    "template_name": "Bản PDF nhầm",
                    "template_file": uploaded.file_url,
                }
            ).insert(ignore_permissions=True)

        self.assertIn("docx", str(refusal.exception))

    def test_the_library_flags_a_placeholder_no_version_of_this_can_fill(self):
        """A typo in a template is found in the library, not on the printer."""
        make_template(
            ["Bên A: {{clint.company_name}} — {{job.title}}"],
            template_name="Hợp đồng có lỗi chính tả",
        )

        frappe.set_user(FOUNDER)
        listed = {row["template_name"]: row for row in paperwork_templates()}

        self.assertEqual(
            listed["Hợp đồng có lỗi chính tả"]["unknown_placeholders"],
            ["clint.company_name"],
        )
        self.assertEqual(listed["Hợp đồng dịch vụ"]["unknown_placeholders"], [])

    def test_the_library_says_which_paper_needs_which_extra_party(self):
        make_template(FREELANCER_PAPER, template_name="Hợp đồng cộng tác viên")

        frappe.set_user(FOUNDER)
        listed = {row["template_name"]: row for row in paperwork_templates()}

        self.assertTrue(listed["Hợp đồng cộng tác viên"]["needs_freelancer"])
        self.assertFalse(listed["Hợp đồng cộng tác viên"]["needs_vendor"])
        self.assertFalse(listed["Hợp đồng dịch vụ"]["needs_freelancer"])

    def test_a_disabled_template_is_retired_from_the_job_screen_not_deleted(self):
        make_template(template_name="Mẫu cũ", disabled=1)

        frappe.set_user(FOUNDER)
        self.assertNotIn(
            "Mẫu cũ", [row["template_name"] for row in paperwork_templates()]
        )
        self.assertIn(
            "Mẫu cũ",
            [row["template_name"] for row in paperwork_library()["templates"]],
        )

    def test_the_library_tells_the_screen_who_may_change_it(self):
        """Producers generate paperwork; the founder owns the templates."""
        frappe.set_user(FOUNDER)
        self.assertTrue(paperwork_library()["can_manage"])

        frappe.set_user(PRODUCER)
        self.assertFalse(paperwork_library()["can_manage"])

    def test_the_cheat_sheet_names_every_field_a_template_may_use(self):
        frappe.set_user(PRODUCER)
        names = paperwork_library()["placeholders"]

        for expected in (
            "client.tax_code",
            "contact.full_name",
            "freelancer.id_number",
            "vendor.bank_account_number",
            "job.code",
            "quote.total",
            "today.date",
        ):
            self.assertIn(expected, names)

    def test_only_the_founder_manages_the_library(self):
        """Producers generate from templates; the founder owns them."""
        template = make_template()
        uploaded = upload(build_docx(["{{job.code}}"]), "sneaky.docx")

        frappe.set_user(PRODUCER)
        # Read, so they can pick one to generate from.
        self.assertTrue(paperwork_templates())

        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc(
                {
                    "doctype": "Paperwork Template",
                    "template_name": "Mẫu của producer",
                    "template_file": uploaded.file_url,
                }
            ).insert()

        with self.assertRaises(frappe.PermissionError):
            renamed = frappe.get_doc("Paperwork Template", template.name)
            renamed.template_name = "Đổi tên"
            renamed.save()

        with self.assertRaises(frappe.PermissionError):
            frappe.delete_doc("Paperwork Template", template.name)

    def test_a_user_with_no_role_cannot_even_read_the_library(self):
        make_template()

        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            paperwork_templates()


class TestGeneratingPaperwork(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")
        make_test_user(OUTSIDER)

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def test_a_generated_contract_carries_the_records_it_names(self):
        template = make_template()
        job = make_job(tax_code="0312345678")

        frappe.set_user(FOUNDER)
        result = generate_job_paperwork(job=job.name, template=template.name)
        text = read_text(result["file_url"])

        self.assertIn(f"Bên A: {CLIENT}", text)
        self.assertIn("Mã số thuế: 0312345678", text)
        self.assertIn(f"({job.name})", text)
        self.assertIn(job.title, text)
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["unknown"], [])

    def test_the_amount_comes_off_the_quote_the_job_carries(self):
        template = make_template()
        job = make_job(tax_code="0312345678")

        frappe.set_user(FOUNDER)
        result = generate_job_paperwork(job=job.name, template=template.name)

        self.assertIn(
            f"Giá trị hợp đồng: {format_vnd(job.quote_total)} đồng",
            read_text(result["file_url"]),
        )

    def test_a_missing_tax_code_is_marked_on_the_page_and_reported(self):
        """The whole reason this ticket exists: no silent blanks."""
        template = make_template()
        job = make_job(tax_code=None)

        frappe.set_user(FOUNDER)
        result = generate_job_paperwork(job=job.name, template=template.name)

        self.assertEqual(result["missing"], ["client.tax_code"])
        self.assertIn("«thiếu: client.tax_code»", read_text(result["file_url"]))

    def test_a_freelancers_details_come_from_the_person_picked(self):
        template = make_template(
            FREELANCER_PAPER, template_name="Hợp đồng cộng tác viên"
        )
        job = make_job(tax_code="0312345678")
        editor = frappe.get_doc(
            {
                "doctype": "Party Contact",
                "full_name": "Nguyễn Văn A",
                "phone": "0909000111",
                "id_number": "079090001234",
            }
        ).insert(ignore_permissions=True)

        frappe.set_user(FOUNDER)
        result = generate_job_paperwork(
            job=job.name, template=template.name, freelancer=editor.name
        )
        text = read_text(result["file_url"])

        self.assertIn("Ông/Bà: Nguyễn Văn A", text)
        self.assertIn("CCCD: 079090001234", text)
        self.assertEqual(result["missing"], [])

    def test_a_freelancer_paper_with_nobody_picked_says_so(self):
        """Nobody selected is missing data, not a broken template."""
        template = make_template(
            FREELANCER_PAPER, template_name="Hợp đồng cộng tác viên"
        )
        job = make_job()

        frappe.set_user(FOUNDER)
        result = generate_job_paperwork(job=job.name, template=template.name)

        self.assertEqual(
            result["missing"], ["freelancer.full_name", "freelancer.id_number"]
        )
        self.assertEqual(result["unknown"], [])

    def test_the_document_attaches_to_the_job_it_was_made_for(self):
        template = make_template()
        job = make_job(tax_code="0312345678")

        frappe.set_user(FOUNDER)
        result = generate_job_paperwork(job=job.name, template=template.name)
        attached = job_paperwork(job.name)

        self.assertEqual([row.name for row in attached], [result["name"]])
        stored = frappe.get_doc("File", result["name"])
        self.assertEqual(stored.attached_to_doctype, "Job")
        self.assertEqual(stored.attached_to_name, job.name)
        self.assertTrue(stored.is_private)
        self.assertIn(job.name, stored.file_name)
        self.assertIn(template.template_name, stored.file_name)

    def test_generating_twice_keeps_both_documents(self):
        """A re-signed contract does not overwrite the one already sent."""
        template = make_template()
        job = make_job(tax_code="0312345678")

        frappe.set_user(FOUNDER)
        first = generate_job_paperwork(job=job.name, template=template.name)
        second = generate_job_paperwork(job=job.name, template=template.name)

        self.assertNotEqual(first["name"], second["name"])
        self.assertEqual(len(job_paperwork(job.name)), 2)

    def test_a_producer_may_generate_paperwork_for_a_job(self):
        template = make_template()
        job = make_job(tax_code="0312345678")

        frappe.set_user(PRODUCER)
        result = generate_job_paperwork(job=job.name, template=template.name)

        self.assertIn(CLIENT, read_text(result["file_url"]))

    def test_someone_who_cannot_write_the_job_cannot_paper_it(self):
        template = make_template()
        job = make_job(tax_code="0312345678")

        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            generate_job_paperwork(job=job.name, template=template.name)

    def test_nobody_can_hang_a_file_on_a_job_they_cannot_write(self):
        """The gate the generated document goes through, tested directly."""
        job = make_job()

        frappe.set_user(OUTSIDER)
        with self.assertRaises(frappe.PermissionError):
            frappe.get_doc(
                {
                    "doctype": "File",
                    "file_name": "smuggled.txt",
                    "attached_to_doctype": "Job",
                    "attached_to_name": job.name,
                    "is_private": 1,
                    "content": b"hello",
                }
            ).insert()

    def test_a_disabled_template_cannot_be_generated_from(self):
        template = make_template(template_name="Mẫu cũ", disabled=1)
        job = make_job()

        frappe.set_user(FOUNDER)
        with self.assertRaises(frappe.ValidationError) as refusal:
            generate_job_paperwork(job=job.name, template=template.name)

        self.assertIn("Mẫu cũ", str(refusal.exception))


class TestWebAuthoredTemplates(FrappeTestCase):
    """A5 round 2: templates written in the app, not uploaded from Word."""

    def setUp(self):
        frappe.set_user("Administrator")
        existing = frappe.db.exists(
            "Paperwork Template", {"template_name": "Web hợp đồng"}
        )
        if existing:
            frappe.delete_doc("Paperwork Template", existing, force=True)

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def make_web_template(self, source=None):
        return frappe.get_doc(
            {
                "doctype": "Paperwork Template",
                "template_name": "Web hợp đồng",
                "template_source": source
                or "\n".join(
                    [
                        "HỢP ĐỒNG",
                        "Bên B: {{freelancer.full_name}}",
                        "Việc: {{job.title}}",
                    ]
                ),
            }
        ).insert(ignore_permissions=True)

    def test_source_builds_the_docx_and_reads_its_placeholders(self):
        template = self.make_web_template()
        self.assertTrue(template.template_file)
        from auraos.auraos.doctype.paperwork_template.paperwork_template import (
            stored_placeholders,
        )

        self.assertIn("freelancer.full_name", stored_placeholders(template))
        self.assertIn("job.title", stored_placeholders(template))
        self.assertIn("Bên B:", read_text(template.template_file))

    def test_editing_the_source_rebuilds_the_file(self):
        template = self.make_web_template()
        first_file = template.template_file
        template.template_source = "CHỈ MỘT DÒNG: {{client.company_name}}"
        template.save(ignore_permissions=True)
        self.assertNotEqual(template.template_file, first_file)
        self.assertEqual(
            stored_names(template), ["client.company_name"]
        )

    def test_an_uploaded_template_keeps_working_with_no_source(self):
        template = make_template()
        self.assertFalse(template.get("template_source"))
        self.assertIn("client.tax_code", stored_names(template))


def stored_names(template):
    from auraos.auraos.doctype.paperwork_template.paperwork_template import (
        stored_placeholders,
    )

    return stored_placeholders(template)


class TestGeneratedPaperRegistry(FrappeTestCase):
    """A5 round 2: every generated paper lands in one findable registry."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def test_generating_writes_a_registry_row_with_who_it_was_for(self):
        from auraos.api import generate_job_paperwork, generated_papers

        template = make_template()
        job = make_job()
        person = frappe.get_doc(
            {
                "doctype": "Party Contact",
                "full_name": "Registry Freelancer",
                "phone": "0900000001",
            }
        ).insert(ignore_permissions=True)

        frappe.set_user(PRODUCER)
        result = generate_job_paperwork(
            job.name, template.name, freelancer=person.name
        )

        rows = generated_papers()
        mine = [row for row in rows if row.file_name == result["file_name"]]
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0].job, job.name)
        self.assertEqual(mine[0].freelancer, person.name)
        self.assertEqual(mine[0].freelancer_label, "Registry Freelancer")
        self.assertEqual(mine[0].template_name, template.template_name)

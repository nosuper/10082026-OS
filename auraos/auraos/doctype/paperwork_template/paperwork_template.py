"""Docx templates and the papers made from them (T11, issue #13).

The founder designs each paper once in Word - letterhead, clauses,
signature block, seal space - and types ``{{client.tax_code}}`` where a
value belongs. This module is the thin Frappe half of that: it reads the
uploaded file, assembles the records a paper is written about, and hands
both to `auraos.lib.paperwork`, which knows nothing about Frappe.

Generating attaches the result to the job, because a contract that lives
in someone's Downloads folder is a contract nobody else can find.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from auraos.lib import paperwork

# The generated file's name: the job it belongs to, the paper it is, and
# when it was made - so a regenerated contract sits beside the first one
# rather than quietly replacing it.
FILENAME = "{job} - {template} - {stamp}.docx"
STAMP_FORMAT = "%Y%m%d-%H%M"


class PaperworkTemplate(Document):
    def validate(self):
        # A template written in the app carries its paragraphs in
        # template_source; the .docx is built from them (A5 round 2 -
        # the founder wanted templates viewable and editable on the
        # website, not only uploaded from Word).
        if (self.template_source or "").strip():
            self.rebuild_from_source()
        # Reading the file on every save is what keeps `placeholders`
        # honest: replace the docx and the list follows, with no second
        # step for anyone to forget.
        self.placeholders = "\n".join(placeholders(self))

    def rebuild_from_source(self):
        before = self.get_doc_before_save()
        unchanged = (
            before
            and before.template_source == self.template_source
            and self.template_file
        )
        if unchanged:
            return
        # The web editor writes HTML; the first seeds wrote plain
        # paragraph lines. Both stay buildable.
        if paperwork.looks_like_html(self.template_source):
            content = paperwork.html_to_docx(self.template_source)
        else:
            content = paperwork.build_docx(self.template_source.splitlines())
        built = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": f"{self.template_name}.docx",
                "is_private": 1,
                "content": content,
            }
        ).insert()
        self.template_file = built.file_url


def placeholders(template):
    """The placeholders a template asks for, read from the file itself."""
    try:
        return paperwork.placeholders_in_docx(content(template))
    except ValueError as error:
        frappe.throw(str(error), frappe.ValidationError)


def stored_placeholders(template):
    """The list `validate` wrote, back as names.

    Lives beside the line that encodes it so the two cannot drift: a
    reader that split on the wrong character would be a bug nothing
    catches until a screen quietly shows no placeholders at all.
    """
    return [name for name in (template.get("placeholders") or "").split("\n") if name]


def content(template) -> bytes:
    """The uploaded .docx, as bytes.

    Templates are uploaded through the app, so the attachment is always
    a File row; a `template_file` pointing anywhere else is a template
    nobody can generate from, and saying so beats a stack trace.
    """
    name = frappe.db.get_value("File", {"file_url": template.template_file}, "name")
    if not name:
        frappe.throw(
            _("The template file for {0} is missing - upload it again.").format(
                template.template_name
            ),
            frappe.DoesNotExistError,
        )
    return frappe.get_doc("File", name).get_content()


def party(doctype, name):
    """One client, vendor or freelancer as a plain dict - or nothing.

    Permission-checked even though both operating roles read the party
    doctypes today: a template can pull a bank account and an ID number
    onto a page, and "whoever may write the job" is not the same
    sentence as "whoever may read this person".
    """
    if not name:
        return None
    frappe.has_permission(doctype, "read", doc=name, throw=True)
    # get_value skips permissions by design; the check above is the
    # entire authorization for this read.
    return frappe.db.get_value(doctype, name, "*", as_dict=True)


def values_for(job, vendor=None, freelancer=None):
    """Everything a paper about this job may say - one builder, shared
    by the generated .docx and the on-screen preview so the two can
    never disagree about a value."""
    return paperwork.document_values(
        job=job.as_dict(),
        client=party("Party Company", job.company),
        contact=party("Party Contact", job.contact),
        vendor=party("Party Company", vendor),
        freelancer=party("Party Contact", freelancer),
        today=frappe.utils.getdate(),
    )


def loaded_template(template_name):
    template = frappe.get_doc("Paperwork Template", template_name)
    if template.disabled:
        frappe.throw(
            _("{0} is disabled and cannot be used.").format(template.template_name),
            frappe.ValidationError,
        )
    return template


def preview(template_name, job_name, vendor=None, freelancer=None):
    """The paper as it would print, as HTML for the screen (A5 round 3).

    A web-authored template previews from its own HTML source. An
    uploaded Word template previews as its filled text, paragraph by
    paragraph - formatting stays in the .docx, but every word and every
    gap marker is on screen before anything is generated.
    """
    template = loaded_template(template_name)
    job = frappe.get_doc("Job", job_name)
    values = values_for(job, vendor=vendor, freelancer=freelancer)

    source = template.get("template_source") or ""
    if source.strip():
        if not paperwork.looks_like_html(source):
            source = "".join(
                f"<p>{frappe.utils.escape_html(line)}</p>"
                for line in source.splitlines()
            )
        filled = paperwork.fill_html(source, values)
        return {
            "html": filled.html,
            "missing": list(filled.missing),
            "unknown": list(filled.unknown),
        }

    docx = paperwork.fill_docx(content(template), values)
    return {
        "html": paperwork.highlight_gaps(paperwork.docx_to_html(docx.document)),
        "missing": list(docx.missing),
        "unknown": list(docx.unknown),
    }


def _mark_gaps(text):
    """Wrap the «…» markers so the preview can highlight them."""
    import re

    return re.sub(r"(«[^»]*»)", r'<mark data-gap="1">\1</mark>', text)


def paper_html(content: bytes):
    """A stored .docx as screen HTML - emphasis and alignment kept -
    or None for a file that isn't one (a receipt photo hangs off jobs
    too)."""
    try:
        return paperwork.highlight_gaps(paperwork.docx_to_html(content))
    except ValueError:
        return None


def template_html(template):
    """A template as the screen shows it, unfilled - its own HTML for a
    web-authored one, its text paragraphs for an uploaded Word file."""
    source = template.get("template_source") or ""
    if source.strip():
        if paperwork.looks_like_html(source):
            return source
        return "".join(
            f"<p>{frappe.utils.escape_html(line)}</p>"
            for line in source.splitlines()
        )
    return paper_html(content(template))


def attach_draft(template_name, job_name, html):
    """An on-screen draft, kept as a .docx on the job (A5 round 4).

    The PandaDoc-shaped flow: fill the template, let the founder edit
    the draft on screen, and what they approved - not the raw fill -
    becomes the job's paper. Built through the same HTML→Word
    translator the web editor uses.
    """
    template = loaded_template(template_name)
    job = frappe.get_doc("Job", job_name)
    return frappe.get_doc(
        {
            "doctype": "File",
            "file_name": FILENAME.format(
                job=job.name,
                template=template.template_name,
                stamp=frappe.utils.now_datetime().strftime(STAMP_FORMAT),
            ),
            "attached_to_doctype": "Job",
            "attached_to_name": job.name,
            "is_private": 1,
            "content": paperwork.html_to_docx(html),
        }
    ).insert()


def generate(template_name, job_name, vendor=None, freelancer=None):
    """Fill a template for a job and attach the result to that job.

    Returns the attached File alongside the report of what could not be
    filled. Both matter: the caller shows the document *and* what is
    wrong with it, because the founder is about to print it.
    """
    template = loaded_template(template_name)
    job = frappe.get_doc("Job", job_name)

    filled = paperwork.fill_docx(
        content(template),
        values_for(job, vendor=vendor, freelancer=freelancer),
    )

    document = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": FILENAME.format(
                job=job.name,
                template=template.template_name,
                stamp=frappe.utils.now_datetime().strftime(STAMP_FORMAT),
            ),
            "attached_to_doctype": "Job",
            "attached_to_name": job.name,
            "is_private": 1,
            "content": filled.document,
        }
    ).insert()

    return document, filled

"""Filling docx paperwork from templates, framework-free (T11, issue #13).

The company signs on paper: contracts, phụ lục, biên bản nghiệm thu,
thanh lý and freelancer papers are printed, signed by hand and sealed.
What the system owes that practice is the typing — the client's tax
code, the job's number, the amount agreed — not a rendering engine. So a
template here is the founder's own .docx, designed in Word, with
``{{client.tax_code}}`` typed where a value belongs; generating a
document returns *that file* with the placeholders replaced and
everything else untouched, down to the letterhead's bytes.

Two things make that harder than a string replace.

**Word does not store a typed word as a typed word.** A placeholder the
founder typed in one go is routinely three runs in the XML, split
wherever a spell-check pass or a formatting toggle happened to land.
Placeholders are therefore matched against a paragraph's *joined* text
and written back into the run each one starts in — so the surrounding
runs keep their own formatting, and only paragraphs that actually carry
a placeholder are rewritten at all.

**Missing data must not disappear.** A blank where a tax code belongs is
invisible on a printed page and expensive at the notary. Anything the
system cannot fill is written into the document as a marker a human eye
catches, and reported back to the caller besides — separated into fields
we know but have no data for (open the client record) and names we have
never heard of (fix the template).

No Frappe imports by contract; the API and the Job are thin adapters.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime
from io import BytesIO
from typing import Any, Iterable, Mapping, Sequence
from xml.sax.saxutils import escape, unescape

from auraos.lib.money import format_vnd

# What a placeholder looks like in the founder's template. Dotted names
# only — the vocabulary below is namespaced, and a pattern this narrow
# cannot mistake a stray brace in the prose for a field.
PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*)\s*\}\}")

# What lands on the page where a value could not be filled. Vietnamese,
# because the person proofreading the printout is: the English-UI
# decision is about the app's chrome, not about the paperwork.
BLANK_MARKER = "«thiếu: {name}»"
UNKNOWN_MARKER = "«không có trường: {name}»"

# The parts of a docx that hold text a template author can type into.
# Everything else — styles, fonts, images, numbering, the relationship
# graph — is copied through untouched.
_FILLABLE_PART = re.compile(
    r"^word/(document\d*|header\d+|footer\d+|footnotes|endnotes)\.xml$"
)

_PARAGRAPH = re.compile(r"<w:p(?:\s[^>]*)?>.*?</w:p>", re.DOTALL)
_TEXT = re.compile(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", re.DOTALL)


@dataclass(frozen=True)
class Filled:
    """A generated document and everything it could not fill.

    `blank` and `unknown` are kept apart because they ask the reader for
    different things: a blank is fixed by opening the client (or picking
    the freelancer) and filling the field in; an unknown is a name no
    version of this system will ever fill, so the template is what needs
    editing.
    """

    document: bytes
    blank: tuple[str, ...] = ()
    unknown: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return not self.blank and not self.unknown


@dataclass
class _Report:
    """Names that could not be filled, in the order they were met."""

    blank: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)

    def note(self, name: str, known: bool) -> None:
        target = self.blank if known else self.unknown
        if name not in target:
            target.append(name)


# -- reading a template --


def _archive(data: bytes) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError(
            "That file is not a docx — Word documents saved as .doc or "
            "exported as PDF cannot be used as templates."
        ) from None


def placeholders_in_docx(data: bytes) -> list[str]:
    """Every field a template asks for, in reading order, once each."""
    archive = _archive(data)
    names: list[str] = []
    for part in archive.namelist():
        if not _FILLABLE_PART.match(part):
            continue
        for name in placeholders_in_xml(archive.read(part).decode("utf-8")):
            if name not in names:
                names.append(name)
    return names


def placeholders_in_xml(xml: str) -> list[str]:
    """Placeholder names in one part, paragraph by paragraph.

    Scoped to paragraphs for the same reason filling is: an unclosed
    ``{{`` is a defect in the line that holds it, not a licence to
    swallow the four pages up to the next ``}}``.
    """
    names: list[str] = []
    for paragraph in _PARAGRAPH.finditer(xml):
        joined, _, _ = _segments(paragraph.group(0))
        for match in PLACEHOLDER.finditer(joined):
            if match.group(1) not in names:
                names.append(match.group(1))
    return names


# -- filling --


def fill_docx(data: bytes, values: Mapping[str, Any]) -> Filled:
    """A template with its placeholders replaced, as a docx.

    Rebuilt part by part in the original order so the result is the
    founder's own file with different words in it. Only the text-bearing
    parts are re-serialised; a logo, a style sheet and the content-type
    map come out byte-for-byte identical.
    """
    archive = _archive(data)
    report = _Report()

    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as written:
        for item in archive.infolist():
            content = archive.read(item.filename)
            if _FILLABLE_PART.match(item.filename):
                content = fill_xml(
                    content.decode("utf-8"), values, report
                ).encode("utf-8")
            written.writestr(item, content)

    return Filled(
        document=out.getvalue(),
        blank=tuple(report.blank),
        unknown=tuple(report.unknown),
    )


def fill_xml(xml: str, values: Mapping[str, Any], report: _Report | None = None) -> str:
    """One document part, filled. Paragraphs without fields are untouched."""
    report = report if report is not None else _Report()
    return _PARAGRAPH.sub(lambda m: _fill_paragraph(m.group(0), values, report), xml)


def _segments(paragraph: str) -> tuple[str, list[str], list[int]]:
    """A paragraph's text runs: the joined reading, the parts, the offsets.

    Text comes back decoded (``&amp;`` → ``&``) so a placeholder is
    matched against what the founder typed rather than against however
    Word chose to escape it.
    """
    parts = [unescape(match.group(1)) for match in _TEXT.finditer(paragraph)]
    starts: list[int] = []
    cursor = 0
    for part in parts:
        starts.append(cursor)
        cursor += len(part)
    return "".join(parts), parts, starts


def _fill_paragraph(
    paragraph: str, values: Mapping[str, Any], report: _Report
) -> str:
    joined, parts, starts = _segments(paragraph)
    matches = list(PLACEHOLDER.finditer(joined))
    if not matches:
        # Nothing to fill: hand back the paragraph exactly as it was, so
        # the generated file differs from the template only where a value
        # went in.
        return paragraph

    rebuilt: list[list[str]] = [[] for _ in parts]

    def copy(start: int, end: int) -> None:
        """Text that is not a placeholder, back into the runs it came from."""
        for index, part in enumerate(parts):
            low, high = starts[index], starts[index] + len(part)
            take_from, take_to = max(start, low), min(end, high)
            if take_from < take_to:
                rebuilt[index].append(joined[take_from:take_to])

    cursor = 0
    for match in matches:
        copy(cursor, match.start())
        # The replacement goes wholly into the run the placeholder opens
        # in — the one whose formatting the founder chose for it.
        rebuilt[_run_at(match.start(), parts, starts)].append(
            _replacement(match.group(1), values, report)
        )
        cursor = match.end()
    copy(cursor, len(joined))

    return _rewrite_runs(paragraph, ["".join(chunks) for chunks in rebuilt])


def _run_at(position: int, parts: Sequence[str], starts: Sequence[int]) -> int:
    """Which run a character belongs to; empty runs never own anything."""
    for index, part in enumerate(parts):
        if starts[index] <= position < starts[index] + len(part):
            return index
    return len(parts) - 1


def _replacement(name: str, values: Mapping[str, Any], report: _Report) -> str:
    """What one placeholder becomes — its value, or a visible absence."""
    known = name in values
    value = values.get(name)
    # `0` and `0.0` are answers; only None and the empty string are gaps.
    if value is None or value == "":
        report.note(name, known)
        marker = BLANK_MARKER if known else UNKNOWN_MARKER
        return marker.format(name=name)
    return str(value)


def _rewrite_runs(paragraph: str, texts: Sequence[str]) -> str:
    """Put the new text back into the paragraph's <w:t> elements.

    `xml:space="preserve"` on every rewritten run: filling can leave a
    run beginning or ending in a space (`"Bên A: "` before a name), and
    Word discards those unless it is told not to.
    """
    replacements = iter(texts)

    def one(_match: re.Match) -> str:
        return f'<w:t xml:space="preserve">{escape(next(replacements))}</w:t>'

    return _TEXT.sub(one, paragraph)


# -- the vocabulary a template may draw on --

# Fields carried by a company-shaped record (the client, a vendor) and a
# person-shaped one (the client's contact, a freelancer). The names are
# the DocType fieldnames on purpose: a founder reading the Contacts
# screen already knows what to type into a template.
COMPANY_FIELDS = (
    "company_name",
    "tax_code",
    "address",
    "phone",
    "email",
    "website",
    "bank_name",
    "bank_account_number",
    "bank_account_name",
)
PERSON_FIELDS = (
    "full_name",
    "company",
    "phone",
    "email",
    "id_number",
    "date_of_birth",
    "tax_code",
    "permanent_address",
    "contact_address",
    "bank_name",
    "bank_account_number",
    "bank_account_name",
)
JOB_FIELDS = {
    "code": "name",
    "title": "title",
    "stage": "stage",
    "files_location": "files_location",
    "deal": "deal",
}
MONEY_FIELDS = {
    "subtotal": "quote_subtotal",
    "mf_amount": "quote_mf_amount",
    "vat_amount": "quote_vat_amount",
    "total": "quote_total",
}
PCT_FIELDS = {"mf_pct": "quote_mf_pct", "vat_pct": "vat_pct"}


def document_values(
    job: Mapping[str, Any] | None = None,
    client: Mapping[str, Any] | None = None,
    contact: Mapping[str, Any] | None = None,
    vendor: Mapping[str, Any] | None = None,
    freelancer: Mapping[str, Any] | None = None,
    today: date | None = None,
) -> dict[str, str | None]:
    """Every placeholder a template may use, filled from plain records.

    Five namespaces, because a paper is written *about* somebody:
    `job` and `quote` are the work and its price, `client`/`contact` are
    who the job is for, and `vendor`/`freelancer` are whoever this
    particular paper is with. A record nobody selected still contributes
    its field names, with no value — so "no freelancer chosen" reports as
    missing data rather than as a broken template.

    Our own company's name, tax code and address are deliberately absent:
    they are the same on every document, so they are typed into the
    template once rather than filled in a thousand times.
    """
    values: dict[str, str | None] = {}
    job = job or {}

    for name, fieldname in JOB_FIELDS.items():
        values[f"job.{name}"] = _text(job.get(fieldname))
    for name, fieldname in MONEY_FIELDS.items():
        values[f"quote.{name}"] = _money(job.get(fieldname))
    for name, fieldname in PCT_FIELDS.items():
        values[f"quote.{name}"] = _pct(job.get(fieldname))

    values.update(_namespace("client", client, COMPANY_FIELDS))
    values.update(_namespace("vendor", vendor, COMPANY_FIELDS))
    values.update(_namespace("contact", contact, PERSON_FIELDS))
    values.update(_namespace("freelancer", freelancer, PERSON_FIELDS))

    # Contracts open with the date in words the signer reads aloud —
    # "hôm nay, ngày 11 tháng 08 năm 2026" — so the parts are offered
    # separately as well as joined.
    today = today or date.today()
    values["today.date"] = _date(today)
    values["today.day"] = f"{today.day:02d}"
    values["today.month"] = f"{today.month:02d}"
    values["today.year"] = str(today.year)
    return values


def value_names() -> list[str]:
    """Every placeholder name the system can fill — the founder's cheat sheet."""
    return sorted(document_values())


def _namespace(
    prefix: str, record: Mapping[str, Any] | None, fields: Iterable[str]
) -> dict[str, str | None]:
    record = record or {}
    return {f"{prefix}.{name}": _text(record.get(name)) for name in fields}


def _text(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return _date(value.date())
    if isinstance(value, date):
        return _date(value)
    return str(value)


def _date(value: date) -> str:
    """Dates as Vietnam writes them on paper."""
    return f"{value.day:02d}/{value.month:02d}/{value.year}"


def _money(amount: Any) -> str | None:
    """An amount in whole đồng — the symbol belongs to the template's prose."""
    if amount is None or amount == "":
        return None
    return format_vnd(amount)


def _pct(value: Any) -> str | None:
    if value is None or value == "":
        return None
    number = float(value)
    written = f"{number:.2f}".rstrip("0").rstrip(".")
    return f"{written.replace('.', ',')}%"


# -- writing a starter template --

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
    'content-types">'
    '<Default Extension="rels" ContentType="application/'
    'vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)
_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
    'relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
    'officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/>'
    "</Relationships>"
)


def build_docx(paragraphs: Sequence[str]) -> bytes:
    """The smallest real .docx that holds these paragraphs.

    Not a document generator — a document generator is exactly what this
    ticket decided not to build. It exists so a preview stack can boot
    with a starter template in the library, and so the tests have a
    fixture that is a genuine Word file rather than a hand-rolled zip.
    """
    body = "".join(
        f'<w:p><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'
        for text in paragraphs
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/'
        'wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _ROOT_RELS)
        archive.writestr("word/document.xml", document)
    return out.getvalue()

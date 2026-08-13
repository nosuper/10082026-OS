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
from html.parser import HTMLParser
from io import BytesIO
from typing import Any, Iterable, Mapping, Sequence
from xml.sax.saxutils import escape, unescape

from auraos.lib.money import format_vnd

# What a placeholder looks like in the founder's template. Narrow on
# purpose — a brace around prose, an unclosed pair or anything with a
# space in it is not a placeholder, so ordinary writing is safe. An
# undotted name still matches: `{{TODO}}` is a placeholder nothing can
# fill, which the founder should be told rather than left to print.
PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*)\s*\}\}")

# What lands on the page where a value could not be filled. Vietnamese,
# because the person proofreading the printout is: the English-UI
# decision is about the app's chrome, not about the paperwork.
MISSING_MARKER = "«thiếu: {name}»"
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
    """A generated paper and every placeholder it could not fill.

    `missing` and `unknown` are kept apart because they ask the reader
    for different things: a missing value is fixed by opening the client
    (or picking the freelancer) and filling the field in; an unknown name
    is one no version of this system will ever fill, so the template is
    what needs editing.
    """

    document: bytes
    missing: tuple[str, ...] = ()
    unknown: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return not self.missing and not self.unknown


@dataclass
class _Report:
    """Names that could not be filled, in the order they were met."""

    missing: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)

    def note(self, name: str, known: bool) -> None:
        target = self.missing if known else self.unknown
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
    """Every placeholder a template asks for, in reading order, once each."""
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
                content = _fill_xml(
                    content.decode("utf-8"), values, report
                ).encode("utf-8")
            written.writestr(item, content)

    return Filled(
        document=out.getvalue(),
        missing=tuple(report.missing),
        unknown=tuple(report.unknown),
    )


def _fill_xml(xml: str, values: Mapping[str, Any], report: _Report) -> str:
    """One document part, filled. Paragraphs with no placeholder are untouched."""
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
        marker = MISSING_MARKER if known else UNKNOWN_MARKER
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

    So is the deal. A job carries the deal's title, client and quoted
    totals already, and the rest of a Deal is where the founder-only
    numbers live — commission, the profit chain. Opening that record to
    templates would put a permlevel behind a placeholder, where the one
    thing nobody can see is who is about to read the printout.
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


def fillable_placeholders() -> list[str]:
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


@dataclass(frozen=True)
class FilledHtml:
    """A web preview of a paper and everything it could not fill."""

    html: str
    missing: tuple[str, ...] = ()
    unknown: tuple[str, ...] = ()


def fill_html(source: str, values: Mapping[str, Any]) -> FilledHtml:
    """The template's own HTML with values dropped in — the on-screen
    preview and print view (A5 round 3).

    Values are escaped on the way in: they come from records, and a
    company name must never execute as markup. An unfillable name keeps
    the exact «…» marker the printed docx would carry, wrapped in
    ``<mark data-gap>`` so the screen can highlight it.
    """
    report = _Report()

    def replace(match: re.Match) -> str:
        name = match.group(1)
        known = name in values
        value = values.get(name)
        if value is None or value == "":
            report.note(name, known)
            marker = (MISSING_MARKER if known else UNKNOWN_MARKER).format(name=name)
            return f'<mark data-gap="1">{escape(marker)}</mark>'
        return escape(str(value))

    return FilledHtml(
        html=PLACEHOLDER.sub(replace, source),
        missing=tuple(report.missing),
        unknown=tuple(report.unknown),
    )


# -- building a .docx from HTML written in the app's editor --

# The subset the web editor produces that survives into the paper.
# Anything else degrades to its text — a paper is clauses and headings,
# not a layout engine.
_HEADING_SIZES = {"h1": 32, "h2": 28, "h3": 26}  # half-points
_ALIGNMENTS = {"center": "center", "right": "right", "justify": "both"}


class _HtmlPaper(HTMLParser):
    """Parses the editor's HTML into paragraphs of formatted runs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.paragraphs: list[dict] = []
        self._runs: list[dict] = []
        self._bold = 0
        self._italic = 0
        self._underline = 0
        self._size: int | None = None
        self._align: str | None = None
        self._lists: list[dict] = []
        self._in_block = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("strong", "b"):
            self._bold += 1
        elif tag in ("em", "i"):
            self._italic += 1
        elif tag == "u":
            self._underline += 1
        elif tag == "br":
            self._runs.append({"break": True})
        elif tag in ("ul", "ol"):
            self._lists.append({"ordered": tag == "ol", "count": 0})
        elif tag in ("p", "h1", "h2", "h3", "li"):
            self._open_block(tag, attrs)

    def handle_endtag(self, tag):
        if tag in ("strong", "b"):
            self._bold = max(0, self._bold - 1)
        elif tag in ("em", "i"):
            self._italic = max(0, self._italic - 1)
        elif tag == "u":
            self._underline = max(0, self._underline - 1)
        elif tag in ("ul", "ol"):
            if self._lists:
                self._lists.pop()
        elif tag in ("p", "h1", "h2", "h3", "li"):
            self._close_block()

    def handle_data(self, data):
        if not data:
            return
        # Text outside any block (legacy plain fragments) still prints.
        if not self._in_block and data.strip():
            self._open_block("p", {})
        if self._in_block:
            self._runs.append(
                {
                    "text": data,
                    "bold": self._bold > 0 or self._size is not None,
                    "italic": self._italic > 0,
                    "underline": self._underline > 0,
                    "size": self._size,
                }
            )

    def _open_block(self, tag, attrs):
        self._close_block()
        self._in_block = True
        self._size = _HEADING_SIZES.get(tag)
        style = attrs.get("style") or ""
        self._align = next(
            (
                word_value
                for css_value, word_value in _ALIGNMENTS.items()
                if f"text-align: {css_value}" in style
                or f"text-align:{css_value}" in style
            ),
            None,
        )
        if tag == "li" and self._lists:
            entry = self._lists[-1]
            entry["count"] += 1
            prefix = f"{entry['count']}. " if entry["ordered"] else "• "
            indent = "    " * (len(self._lists) - 1)
            self._runs.append({"text": indent + prefix, "bold": False,
                               "italic": False, "underline": False, "size": None})

    def _close_block(self):
        if not self._in_block:
            return
        self.paragraphs.append({"align": self._align, "runs": self._runs})
        self._runs = []
        self._in_block = False
        self._size = None
        self._align = None

    def close(self):
        super().close()
        self._close_block()


def _run_xml(run: dict) -> str:
    if run.get("break"):
        return "<w:r><w:br/></w:r>"
    props = ""
    if run.get("bold"):
        props += "<w:b/>"
    if run.get("italic"):
        props += "<w:i/>"
    if run.get("underline"):
        props += '<w:u w:val="single"/>'
    if run.get("size"):
        props += f'<w:sz w:val="{run["size"]}"/><w:szCs w:val="{run["size"]}"/>'
    rpr = f"<w:rPr>{props}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(run["text"])}</w:t></w:r>'


def _paragraph_xml(paragraph: dict) -> str:
    ppr = (
        f'<w:pPr><w:jc w:val="{paragraph["align"]}"/></w:pPr>'
        if paragraph.get("align")
        else ""
    )
    runs = "".join(_run_xml(run) for run in paragraph["runs"])
    return f"<w:p>{ppr}{runs}</w:p>"


def html_to_docx(source: str) -> bytes:
    """A .docx built from the web editor's HTML (A5 round 3).

    Word's own vocabulary for what the editor offers: bold, italic,
    underline, three heading sizes, alignment, bullet and numbered
    lists (as visible prefixes). Placeholders pass through as text and
    are filled exactly like an uploaded template's.
    """
    parser = _HtmlPaper()
    parser.feed(source)
    parser.close()
    body = "".join(_paragraph_xml(p) for p in parser.paragraphs) or "<w:p/>"
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


def docx_paragraph_texts(data: bytes) -> list[str]:
    """Every paragraph's visible text, in order.

    The preview of an uploaded template: its formatting stays in the
    .docx, but every word — and every gap marker — belongs on screen
    before anything is generated (A5 round 3).
    """
    archive = _archive(data)
    xml = archive.read("word/document.xml").decode("utf-8")
    return [
        unescape("".join(_TEXT.findall(paragraph)))
        for paragraph in _PARAGRAPH.findall(xml)
    ]


def looks_like_html(source: str) -> bool:
    """Which builder a template_source belongs to: the web editor's
    HTML, or the legacy plain paragraphs the first seeds used."""
    return (source or "").lstrip().startswith("<")


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

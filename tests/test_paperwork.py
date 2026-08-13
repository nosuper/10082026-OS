"""The docx paperwork seam (T11, issue #13), framework-free.

Three things have to be true before any of this is worth attaching to a
job:

1. **A placeholder is filled however Word chose to store it.** Word
   splits a typed word across runs for reasons of its own (a spell-check
   pass, a stray formatting toggle), so ``{{client.tax_code}}`` is
   routinely three fragments in the XML. A filler that only handles the
   tidy case works on the template the developer typed and fails on the
   one the founder did.
2. **Nothing is silently blanked.** A missing tax code has to reach the
   printed page as something a human eye catches, and reach the caller
   as a list, because the whole point of generated paperwork is that
   nobody reads it as carefully as they read the first one.
3. **Everything else survives.** A template carries a letterhead image,
   a table, a signature block and a font; filling it must return the
   same file with the words changed, not a re-rendered approximation.

Runs anywhere: pytest, no Frappe, no Word.
"""

import zipfile
from datetime import date
from io import BytesIO

import pytest

from auraos.lib.paperwork import (
    UNKNOWN_MARKER,
    build_docx,
    document_values,
    fill_docx,
    placeholders_in_docx,
)

# -- helpers: docx files shaped the way Word really writes them --


def runs_xml(runs):
    """A paragraph's worth of <w:r> elements, one per run of text."""
    return "".join(
        f"<w:r><w:rPr><w:b/></w:rPr><w:t>{text}</w:t></w:r>" for text in runs
    )


def paragraph_xml(runs):
    return f"<w:p>{runs_xml(runs)}</w:p>"


def document_xml(paragraphs):
    """A word/document.xml whose paragraphs are lists of runs."""
    body = "".join(paragraph_xml(runs) for runs in paragraphs)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/'
        'wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )


def docx_with(parts):
    """A zip holding exactly `parts` - enough to exercise the filler."""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in parts.items():
            archive.writestr(
                name, content if isinstance(content, bytes) else content.encode()
            )
    return buffer.getvalue()


def split_runs_docx(paragraphs):
    return docx_with({"word/document.xml": document_xml(paragraphs)})


def text_of(data, part="word/document.xml"):
    """Every <w:t> in a part, joined - what a reader would see."""
    import re

    xml = zipfile.ZipFile(BytesIO(data)).read(part).decode()
    return "".join(re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", xml, re.DOTALL))


# -- filling --


def test_fills_a_placeholder_that_sits_in_one_run():
    data = split_runs_docx([["Khách hàng: {{client.company_name}}"]])

    filled = fill_docx(data, {"client.company_name": "Công ty Chungify"})

    assert text_of(filled.document) == "Khách hàng: Công ty Chungify"
    assert filled.missing == ()
    assert filled.unknown == ()


def test_fills_a_placeholder_word_split_across_runs():
    """The case that matters: Word stored one placeholder as three runs.

    Nothing in the template looks different to the founder who typed it,
    so a filler that misses this fails on real files while passing on
    every fixture a developer writes by hand.
    """
    data = split_runs_docx([["Mã số thuế: {{clie", "nt.tax", "_code}}"]])

    filled = fill_docx(data, {"client.tax_code": "0312345678"})

    assert text_of(filled.document) == "Mã số thuế: 0312345678"


def test_fills_a_placeholder_split_at_its_braces():
    """The other half of the same problem - the braces themselves split."""
    data = split_runs_docx([["{", "{client.tax_code}", "}"]])

    filled = fill_docx(data, {"client.tax_code": "0312345678"})

    assert text_of(filled.document) == "0312345678"


def test_tolerates_spaces_inside_the_braces():
    data = split_runs_docx([["{{ client.tax_code }}"]])

    filled = fill_docx(data, {"client.tax_code": "0312345678"})

    assert text_of(filled.document) == "0312345678"


def test_text_around_a_split_placeholder_keeps_its_own_runs():
    """Only the placeholder's runs are rewritten; the rest is untouched.

    A contract's bold clause number and its plain body live in separate
    runs of the same paragraph. Collapsing the paragraph into one run to
    make filling easy would flatten the formatting of every document we
    generate.
    """
    data = split_runs_docx([["Điều 1. ", "Giá trị hợp đồng: ", "{{quote.total}}"]])

    filled = fill_docx(data, {"quote.total": "250.000.000"})
    xml = zipfile.ZipFile(BytesIO(filled.document)).read("word/document.xml").decode()

    assert xml.count("<w:r>") == 3
    assert xml.count("<w:b/>") == 3
    # Still three runs, each holding its own words. (Their <w:t> gains
    # xml:space="preserve" - "Điều 1. " ends in a space Word would
    # otherwise drop, so the attribute is a fix, not a side effect.)
    assert '<w:t xml:space="preserve">Điều 1. </w:t>' in xml
    assert text_of(filled.document) == "Điều 1. Giá trị hợp đồng: 250.000.000"


def test_a_placeholder_never_reaches_across_paragraphs():
    """An unclosed brace stays a defect in its own paragraph.

    Joining the whole document to find placeholders would let a stray
    `{{` on one line swallow everything up to the next `}}` pages later.
    """
    data = split_runs_docx([["Bên A: {{client.company_name"], ["Bên B: }}"]])

    filled = fill_docx(data, {"client.company_name": "Chungify"})

    assert text_of(filled.document) == (
        "Bên A: {{client.company_nameBên B: }}"
    )


def test_a_value_carrying_xml_characters_is_escaped():
    """Company names contain & - a filler that forgets breaks the file."""
    data = split_runs_docx([["{{client.company_name}}"]])

    filled = fill_docx(data, {"client.company_name": "Ogilvy & Mather <VN>"})
    xml = zipfile.ZipFile(BytesIO(filled.document)).read("word/document.xml").decode()

    assert "Ogilvy &amp; Mather &lt;VN&gt;" in xml
    # And it still parses as XML, which is the actual thing at stake.
    zipfile.ZipFile(BytesIO(filled.document))
    assert text_of(filled.document) == "Ogilvy &amp; Mather &lt;VN&gt;"


def test_an_escaped_placeholder_is_still_found():
    """Word escapes as it likes; the placeholder is the decoded text."""
    data = docx_with(
        {
            "word/document.xml": document_xml([["A &amp; B {{client.tax_code}}"]])
        }
    )

    filled = fill_docx(data, {"client.tax_code": "0312345678"})

    assert text_of(filled.document) == "A &amp; B 0312345678"


def test_leading_and_trailing_spaces_in_a_filled_run_are_preserved():
    """Word drops whitespace unless the run says to keep it."""
    data = split_runs_docx([["{{client.company_name}}"]])

    filled = fill_docx(data, {"client.company_name": "  Chungify  "})
    xml = zipfile.ZipFile(BytesIO(filled.document)).read("word/document.xml").decode()

    assert 'xml:space="preserve"' in xml


def test_headers_and_footers_are_filled_too():
    """Letterhead and page furniture carry placeholders as often as the body."""
    data = docx_with(
        {
            "word/document.xml": document_xml([["Body {{job.code}}"]]),
            "word/header1.xml": document_xml([["Header {{job.code}}"]]),
            "word/footer1.xml": document_xml([["Footer {{job.code}}"]]),
        }
    )

    filled = fill_docx(data, {"job.code": "JOB-0007"})

    assert text_of(filled.document) == "Body JOB-0007"
    assert text_of(filled.document, "word/header1.xml") == "Header JOB-0007"
    assert text_of(filled.document, "word/footer1.xml") == "Footer JOB-0007"


def test_every_other_part_of_the_file_survives_byte_for_byte():
    """A template is a designed document - logo, styles, fonts and all."""
    logo = b"\x89PNG\r\n\x1a\nnot-really-a-png"
    data = docx_with(
        {
            "word/document.xml": document_xml([["{{job.code}}"]]),
            "word/media/image1.png": logo,
            "word/styles.xml": "<styles/>",
            "[Content_Types].xml": "<Types/>",
        }
    )

    filled = fill_docx(data, {"job.code": "JOB-0007"})
    archive = zipfile.ZipFile(BytesIO(filled.document))

    assert archive.read("word/media/image1.png") == logo
    assert archive.read("word/styles.xml") == b"<styles/>"
    assert archive.read("[Content_Types].xml") == b"<Types/>"
    assert archive.namelist() == [
        "word/document.xml",
        "word/media/image1.png",
        "word/styles.xml",
        "[Content_Types].xml",
    ]


def test_a_paragraph_without_placeholders_is_left_exactly_as_it_was():
    """No placeholder, no rewrite - the diff is the words that changed."""
    untouched = paragraph_xml(["Điều 2. Thời hạn thực hiện"])
    data = split_runs_docx(
        [["Điều 2. Thời hạn thực hiện"], ["Mã: {{job.code}}"]]
    )

    filled = fill_docx(data, {"job.code": "JOB-0007"})
    xml = zipfile.ZipFile(BytesIO(filled.document)).read("word/document.xml").decode()

    assert untouched in xml


# -- missing data, surfaced rather than blanked --


def test_a_known_field_with_no_data_is_marked_in_the_document():
    """The client has no tax code on file. The contract says so, loudly."""
    data = split_runs_docx([["Mã số thuế: {{client.tax_code}}"]])

    filled = fill_docx(data, {"client.tax_code": None})

    assert text_of(filled.document) == "Mã số thuế: «thiếu: client.tax_code»"
    assert filled.missing == ("client.tax_code",)
    assert filled.unknown == ()


def test_an_empty_string_counts_as_missing_not_as_filled():
    data = split_runs_docx([["{{client.address}}"]])

    filled = fill_docx(data, {"client.address": ""})

    assert filled.missing == ("client.address",)


def test_a_placeholder_the_system_has_never_heard_of_is_marked_apart():
    """A typo in a template is a different problem from an empty field.

    Both reach the page; only one is fixed by opening the client record.
    """
    data = split_runs_docx([["{{clint.tax_code}}"]])

    filled = fill_docx(data, {"client.tax_code": "0312345678"})

    assert text_of(filled.document) == UNKNOWN_MARKER.format(name="clint.tax_code")
    assert filled.unknown == ("clint.tax_code",)
    assert filled.missing == ()


def test_missing_names_are_reported_once_each_in_the_order_they_appear():
    data = split_runs_docx(
        [
            ["{{client.tax_code}} {{clint.name}}"],
            ["{{client.tax_code}} {{client.address}}"],
        ]
    )

    filled = fill_docx(data, {"client.tax_code": None, "client.address": None})

    assert filled.missing == ("client.tax_code", "client.address")
    assert filled.unknown == ("clint.name",)


def test_a_zero_is_a_value_not_a_blank():
    """0 đồng of VAT is a fact about the deal, not an unfilled field."""
    data = split_runs_docx([["{{quote.vat_amount}}"]])

    filled = fill_docx(data, {"quote.vat_amount": 0})

    assert text_of(filled.document) == "0"
    assert filled.missing == ()


# -- reading a template --


def test_placeholders_in_a_template_are_listed_in_order_without_repeats():
    """What the founder sees before generating: the fields this asks for."""
    data = docx_with(
        {
            "word/document.xml": document_xml(
                [["{{job.title}} {{client.compa", "ny_name}}"], ["{{job.title}}"]]
            ),
            "word/header1.xml": document_xml([["{{job.code}}"]]),
        }
    )

    assert placeholders_in_docx(data) == [
        "job.title",
        "client.company_name",
        "job.code",
    ]


def test_a_file_that_is_not_a_docx_is_refused_by_name():
    with pytest.raises(ValueError, match="docx"):
        placeholders_in_docx(b"this is a PDF, honestly")


# -- the starter template we can write ourselves --


def test_a_built_docx_round_trips_through_the_filler():
    """The seeded starter template has to be a real, fillable docx."""
    data = build_docx(
        ["HỢP ĐỒNG DỊCH VỤ", "Bên A: {{client.company_name}}", "Mã: {{job.code}}"]
    )

    assert placeholders_in_docx(data) == ["client.company_name", "job.code"]

    filled = fill_docx(data, {"client.company_name": "Chungify", "job.code": "JOB-1"})

    assert "Bên A: Chungify" in text_of(filled.document)
    archive = zipfile.ZipFile(BytesIO(filled.document))
    assert archive.testzip() is None
    for required in ("[Content_Types].xml", "_rels/.rels", "word/document.xml"):
        assert required in archive.namelist()


# -- the vocabulary a template may draw on --


def test_document_values_names_every_record_a_paper_can_need():
    values = document_values(
        job={
            "name": "JOB-0007",
            "title": "TVC Tết 2027",
            "stage": "Delivery",
            "files_location": "//nas/jobs/JOB-0007",
            "deal": "DEAL-0003",
            "quote_subtotal": 200_000_000,
            "quote_mf_amount": 20_000_000,
            "quote_vat_amount": 17_600_000,
            "quote_total": 237_600_000,
            "quote_mf_pct": 10,
            "vat_pct": 8,
        },
        client={
            "company_name": "Công ty Chungify",
            "tax_code": "0312345678",
            "address": "12 Nguyễn Huệ, Q1",
            "bank_name": "Vietcombank",
            "bank_account_number": "0071000123456",
            "bank_account_name": "CONG TY CHUNGIFY",
        },
        contact={"full_name": "Chị Hằng", "phone": "0909123456"},
        today=date(2026, 8, 11),
    )

    assert values["job.code"] == "JOB-0007"
    assert values["job.title"] == "TVC Tết 2027"
    assert values["client.company_name"] == "Công ty Chungify"
    assert values["client.tax_code"] == "0312345678"
    assert values["contact.full_name"] == "Chị Hằng"
    assert values["quote.total"] == "237.600.000"
    assert values["quote.vat_pct"] == "8%"
    assert values["today.date"] == "11/08/2026"
    assert values["today.day"] == "11"
    assert values["today.month"] == "08"
    assert values["today.year"] == "2026"


def test_a_party_nobody_selected_is_blank_rather_than_unknown():
    """No freelancer chosen is missing data, not a broken template.

    The difference decides what the founder is told to do about it:
    pick the person, versus fix the placeholder.
    """
    values = document_values(job={"name": "JOB-0007"}, today=date(2026, 8, 11))

    assert "freelancer.full_name" in values
    assert values["freelancer.full_name"] is None
    assert "vendor.company_name" in values
    assert values["vendor.company_name"] is None


def test_a_freelancers_paperwork_fields_are_all_reachable():
    values = document_values(
        job={"name": "JOB-0007"},
        freelancer={
            "full_name": "Nguyễn Văn A",
            "id_number": "079090001234",
            "date_of_birth": date(1990, 4, 2),
            "tax_code": "8012345678",
            "permanent_address": "Số 5, Q. Bình Thạnh",
            "bank_account_number": "9704000123",
        },
        today=date(2026, 8, 11),
    )

    assert values["freelancer.full_name"] == "Nguyễn Văn A"
    assert values["freelancer.id_number"] == "079090001234"
    assert values["freelancer.date_of_birth"] == "02/04/1990"
    assert values["freelancer.permanent_address"] == "Số 5, Q. Bình Thạnh"


def test_money_reads_as_vietnamese_writes_it():
    values = document_values(
        job={"quote_total": 250_000_000, "quote_subtotal": 0},
        today=date(2026, 8, 11),
    )

    assert values["quote.total"] == "250.000.000"
    # Zero is a number, not an absence - it must not read as missing.
    assert values["quote.subtotal"] == "0"


def test_every_value_the_vocabulary_offers_is_a_string_or_none():
    """Nothing reaches the XML as a Decimal, a date or a dict."""
    values = document_values(
        job={"name": "JOB-1", "quote_total": 1_000},
        client={"company_name": "X"},
        today=date(2026, 8, 11),
    )

    assert all(v is None or isinstance(v, str) for v in values.values())


# -- A5 round 3: HTML-authored templates, previews, printable fills --


from auraos.lib.paperwork import (  # noqa: E402
    docx_paragraph_texts,
    fill_html,
    html_to_docx,
    looks_like_html,
)


def test_html_builds_a_docx_with_its_formatting():
    docx = html_to_docx(
        '<h2 style="text-align: center">HỢP ĐỒNG</h2>'
        "<p>Bên B: <strong>{{freelancer.full_name}}</strong></p>"
        "<ul><li>CCCD: 123</li><li>MST: 456</li></ul>"
    )
    xml = zipfile.ZipFile(BytesIO(docx)).read("word/document.xml").decode()
    assert "HỢP ĐỒNG" in xml
    assert '<w:jc w:val="center"/>' in xml
    assert "<w:b/>" in xml
    # Prefix and text are separate runs; read the paragraph as a reader would.
    assert "• CCCD: 123" in docx_paragraph_texts(docx)
    # The placeholder survives as text, ready for fill_docx.
    assert "{{freelancer.full_name}}" in xml


def test_html_docx_paragraphs_read_back_in_order():
    docx = html_to_docx("<p>một</p><p>hai</p><ol><li>ba</li><li>bốn</li></ol>")
    assert docx_paragraph_texts(docx) == ["một", "hai", "1. ba", "2. bốn"]


def test_fill_html_drops_values_in_and_marks_the_gaps():
    filled = fill_html(
        "<p>Tên: {{freelancer.full_name}} - CCCD: {{freelancer.id_number}}"
        " - {{no.such_field}}</p>",
        {"freelancer.full_name": "Ngô Quay Phim", "freelancer.id_number": None},
    )
    assert "Ngô Quay Phim" in filled.html
    assert "«thiếu: freelancer.id_number»" in filled.html
    assert "«không có trường: no.such_field»" in filled.html
    assert '<mark data-gap="1">' in filled.html
    assert filled.missing == ("freelancer.id_number",)
    assert filled.unknown == ("no.such_field",)


def test_fill_html_escapes_record_values():
    filled = fill_html(
        "<p>{{client.company_name}}</p>",
        {"client.company_name": 'Công ty <script>alert("x")</script>'},
    )
    assert "<script>" not in filled.html
    assert "&lt;script&gt;" in filled.html


def test_looks_like_html_separates_the_two_source_kinds():
    assert looks_like_html("<p>hi</p>")
    assert looks_like_html("  \n<h1>hi</h1>")
    assert not looks_like_html("DÒNG MỘT\nDÒNG HAI")


# -- A5 round 6: the symmetric reader - a docx back as styled HTML --


from auraos.lib.paperwork import docx_to_html, highlight_gaps  # noqa: E402


def test_docx_reads_back_with_its_emphasis_and_alignment():
    docx = html_to_docx(
        '<h2 style="text-align: center"><strong>HỢP ĐỒNG</strong></h2>'
        "<p>Bên B: <strong>Ngô Quay Phim</strong> - <em>freelancer</em></p>"
        "<p><u>Điều 1</u></p>"
    )
    html = docx_to_html(docx)
    assert 'style="text-align: center"' in html
    assert "<strong>HỢP ĐỒNG</strong>" in html
    assert "<strong>Ngô Quay Phim</strong>" in html
    assert "<em>freelancer</em>" in html
    assert "<u>Điều 1</u>" in html


def test_docx_line_breaks_survive_the_round_trip():
    docx = html_to_docx("<p>dòng một<br>dòng hai</p>")
    assert "dòng một<br>dòng hai" in docx_to_html(docx)


def test_highlight_gaps_wraps_only_the_markers():
    html = highlight_gaps("<p>Tên: «thiếu: freelancer.full_name» xong</p>")
    assert '<mark data-gap="1">«thiếu: freelancer.full_name»</mark>' in html
    assert html.count("<mark") == 1


def test_docx_tables_come_back_as_tables_in_order():
    # A fee schedule between two paragraphs must stay between them.
    body = (
        "<w:p><w:r><w:t>Trước bảng</w:t></w:r></w:p>"
        "<w:tbl><w:tr>"
        "<w:tc><w:p><w:r><w:t>Hạng mục</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>20.000.000</w:t></w:r></w:p></w:tc>"
        "</w:tr></w:tbl>"
        "<w:p><w:r><w:t>Sau bảng</w:t></w:r></w:p>"
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/'
        f'wordprocessingml/2006/main"><w:body>{body}</w:body></w:document>'
    )
    docx = docx_with({"word/document.xml": document})
    html = docx_to_html(docx)
    assert html.index("Trước bảng") < html.index("<table") < html.index("Sau bảng")
    assert "<td><p>Hạng mục</p></td>" in html
    assert "<strong>20.000.000</strong>" in html
    # The table's own paragraphs are not repeated outside it.
    assert html.count("Hạng mục") == 1


def test_a_signature_block_table_stays_borderless_on_screen():
    # Word draws nothing for a table with no borders and no style -
    # the founder's real signature blocks (A5 round 7).
    body = (
        "<w:tbl><w:tblPr><w:tblW w:w=\"0\" w:type=\"auto\"/></w:tblPr>"
        "<w:tr><w:tc><w:p><w:r><w:t>ĐẠI DIỆN BÊN A</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:p><w:r><w:t>ĐẠI DIỆN BÊN B</w:t></w:r></w:p></w:tc>"
        "</w:tr></w:tbl>"
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/'
        f'wordprocessingml/2006/main"><w:body>{body}</w:body></w:document>'
    )
    html = docx_to_html(docx_with({"word/document.xml": document}))
    assert '<table class="borderless">' in html


def test_a_fee_schedule_with_single_borders_keeps_its_grid():
    body = (
        "<w:tbl><w:tblPr><w:tblBorders>"
        '<w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        "</w:tblBorders></w:tblPr>"
        "<w:tr><w:tc><w:p><w:r><w:t>STT</w:t></w:r></w:p></w:tc></w:tr></w:tbl>"
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/'
        f'wordprocessingml/2006/main"><w:body>{body}</w:body></w:document>'
    )
    html = docx_to_html(docx_with({"word/document.xml": document}))
    assert "<table><tbody>" in html


def test_editor_tables_survive_into_the_docx_and_back():
    docx = html_to_docx(
        "<p>Trên bảng</p>"
        '<table class="borderless"><tbody><tr>'
        "<td><p><strong>BÊN A</strong></p></td><td><p>BÊN B</p></td>"
        "</tr></tbody></table>"
    )
    xml = zipfile.ZipFile(BytesIO(docx)).read("word/document.xml").decode()
    assert "<w:tbl>" in xml
    assert "<w:tblBorders>" not in xml  # borderless in, borderless out
    html = docx_to_html(docx)
    assert '<table class="borderless">' in html
    assert "<strong>BÊN A</strong>" in html

    bordered = html_to_docx("<table><tbody><tr><td><p>x</p></td></tr></tbody></table>")
    bordered_xml = zipfile.ZipFile(BytesIO(bordered)).read("word/document.xml").decode()
    assert "<w:tblBorders>" in bordered_xml

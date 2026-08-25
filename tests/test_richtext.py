"""Pure-python tests for auraos.lib.richtext - no Frappe required.

`Deal.brief` became a Text Editor field in #120, so every brief already
on file has to become the paragraphs its author typed. This is the rule
that conversion runs on, pinned apart from the patch that applies it.

The whole risk here is quiet: the words survive any conversion, so a
wrong one is not noticed on the day it runs. It is noticed months later
when somebody opens an old deal and finds their own writing has become a
wall. So the tests are about shape, not content.

Two rules, and one thing that is not negotiable:

- **A blank line was a paragraph, a single newline was a line break.**
  Those briefs were typed into a textarea, where that is exactly what
  those keys did.
- **A body that already has block tags has been through an editor** and
  is left alone, which is what makes the patch re-runnable.
- **Text is escaped, never trusted.** A brief reading "budget < 200tr"
  is a sentence. Unescaped it is a broken tag and the rest of the
  sentence disappears into it.
"""

from auraos.lib.richtext import from_plain_text, looks_like_html


# -- what was a paragraph --


def test_a_blank_line_was_a_paragraph_break():
    assert from_plain_text("A.\n\nB.") == "<p>A.</p><p>B.</p>"


def test_a_single_newline_was_a_line_break():
    assert from_plain_text("A.\nB.") == "<p>A.<br>B.</p>"


def test_both_at_once_keep_their_own_meanings():
    assert from_plain_text("A.\nB.\n\nC.") == "<p>A.<br>B.</p><p>C.</p>"


def test_several_blank_lines_are_still_one_break():
    """Somebody leaning on the return key meant one paragraph, not three
    empty ones."""
    assert from_plain_text("A.\n\n\n\nB.") == "<p>A.</p><p>B.</p>"


def test_windows_line_endings_mean_the_same_thing():
    assert from_plain_text("A.\r\n\r\nB.") == "<p>A.</p><p>B.</p>"


def test_one_line_becomes_one_paragraph():
    assert from_plain_text("TVC 30s cho chiến dịch Trung thu.") == (
        "<p>TVC 30s cho chiến dịch Trung thu.</p>"
    )


# -- what was never written --


def test_an_unwritten_brief_stays_unwritten():
    """Not an empty paragraph, which reads as one somebody cleared."""
    assert from_plain_text("") == ""
    assert from_plain_text(None) == ""


def test_whitespace_alone_is_nothing():
    assert from_plain_text("   \n\n  \t ") == ""


# -- text is text --


def test_an_angle_bracket_survives_as_a_sentence():
    """"budget < 200tr" is what somebody wrote. Unescaped, the browser
    reads it as a tag that never closes and eats the rest of the line."""
    assert from_plain_text("budget < 200tr") == "<p>budget &lt; 200tr</p>"


def test_an_ampersand_survives():
    assert from_plain_text("quay & dựng") == "<p>quay &amp; dựng</p>"


def test_vietnamese_is_left_exactly_alone():
    """No entity-escaping of the language the studio works in."""
    assert from_plain_text("Ngân sách gấp") == "<p>Ngân sách gấp</p>"


def test_something_that_looks_like_a_tag_is_still_text():
    assert from_plain_text("<b>not bold</b>") == "<p>&lt;b&gt;not bold&lt;/b&gt;</p>"


# -- already converted --


def test_a_body_that_has_been_through_an_editor_is_left_alone():
    assert from_plain_text("<p>already</p>") == "<p>already</p>"


def test_conversion_is_idempotent_so_the_patch_can_be_re_run():
    once = from_plain_text("A.\nB.\n\nC.")
    assert from_plain_text(once) == once


def test_looks_like_html_reads_block_tags_and_not_stray_brackets():
    assert looks_like_html("<p>x</p>") is True
    assert looks_like_html("<ul><li>x</li></ul>") is True
    assert looks_like_html("<h2>x</h2>") is True
    assert looks_like_html("a<br>b") is True
    # The one that matters: a sentence with a comparison in it is not HTML.
    assert looks_like_html("budget < 200tr") is False
    assert looks_like_html("2 < 3 and 4 > 1") is False
    assert looks_like_html("") is False


def test_an_inline_tag_alone_does_not_count_as_converted():
    """Nobody's textarea produced <b>, so a body carrying one and no
    block tag is text that happens to contain angle brackets."""
    assert looks_like_html("<b>x</b>") is False

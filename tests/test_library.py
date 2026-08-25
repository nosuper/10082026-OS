"""Pure-python tests for auraos.lib.library - no Frappe required.

The Library tab shows knowledge documents as cards, and a card carries a
line of the document's prose. Getting that line wrong is quiet in the
same way #120's brief conversion was quiet: the document itself is
untouched and still correct, so nothing looks broken. What breaks is the
card, on a screen whose whole job is helping somebody find the document
they half remember.

Three rules, and the first is the one with teeth:

- **Tags come out before entities go in.** "budget &lt; 200tr" is a
  sentence an author typed. Decoded first, that `<` becomes markup and
  the tag stripper eats the rest of the line.
- **A block boundary is a word boundary.** Two paragraphs are two
  sentences, never one run-on word.
- **A snippet that fits carries no ellipsis**, so "..." always means
  there is more document, never decoration.
"""

from auraos.lib.library import snippet, to_plain_text


# -- markup out --


def test_an_unwritten_body_stays_unwritten():
    assert to_plain_text("") == ""
    assert to_plain_text(None) == ""


def test_tags_are_taken_out_and_the_words_kept():
    assert to_plain_text("<p>Đánh giá deal</p>") == "Đánh giá deal"


def test_a_paragraph_boundary_is_a_word_boundary():
    assert to_plain_text("<p>Bước 1</p><p>Bước 2</p>") == "Bước 1 Bước 2"


def test_a_list_reads_as_its_items():
    assert to_plain_text("<ul><li>Cash</li><li>Bridge</li></ul>") == "Cash Bridge"


def test_headings_do_not_glue_to_the_text_under_them():
    assert to_plain_text("<h2>Tier</h2><p>Tier 3</p>") == "Tier Tier 3"


# -- the order that matters --


def test_a_typed_angle_bracket_survives_and_takes_its_sentence_with_it():
    # The failure this guards: decode first and "< 200tr</p>" is a tag.
    assert to_plain_text("<p>budget &lt; 200tr mỗi job</p>") == "budget < 200tr mỗi job"


def test_an_escaped_script_is_words_not_markup():
    assert to_plain_text("<p>&lt;script&gt;</p>") == "<script>"


def test_a_real_script_block_is_not_prose():
    assert to_plain_text("<p>A</p><script>var x = 1;</script><p>B</p>") == "A B"


def test_a_style_block_is_not_prose():
    assert to_plain_text("<style>.a{color:red}</style><p>A</p>") == "A"


def test_a_non_breaking_space_collapses_like_a_space():
    assert to_plain_text("<p>Tier&nbsp;3</p>") == "Tier 3"


def test_runs_of_whitespace_become_one_space():
    assert to_plain_text("<p>A\n\n   B</p>") == "A B"


# -- the cut --


def test_a_short_body_is_returned_whole_and_unmarked():
    assert snippet("<p>Ngắn.</p>") == "Ngắn."


def test_a_body_exactly_at_the_limit_is_not_cut():
    assert snippet("<p>%s</p>" % ("a" * 160)) == "a" * 160


def test_a_long_body_is_cut_on_a_word_boundary():
    body = "<p>%s</p>" % " ".join(["word"] * 60)
    result = snippet(body)
    assert result.endswith("...")
    assert "wor..." not in result
    assert len(result) <= 163


def test_the_cut_marks_that_there_is_more():
    assert snippet("<p>%s</p>" % ("ab " * 200)).endswith("...")


def test_a_single_word_longer_than_the_limit_is_cut_where_it_is():
    # No boundary to fall back to; better a cut word than the whole wall.
    result = snippet("<p>%s</p>" % ("a" * 400))
    assert result == "a" * 160 + "..."


def test_the_limit_is_the_caller_s_to_choose():
    assert snippet("<p>one two three</p>", limit=7) == "one two..."

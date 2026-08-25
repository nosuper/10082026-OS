"""Pure-python tests for auraos.lib.comments - no Frappe required.

T3.4 / issue #28. A deal comment is HTML now: it can name the other
seat and carry a pasted screenshot. Two questions about that HTML are
decisions rather than plumbing, and both are answered here:

- **Who was named** - read out of the editor's markup, before any
  sanitiser has had a chance to drop an attribute it does not know.
- **Whether anything was said** - an empty editor is not an empty
  string, and a comment that is only a picture has no words at all.

The Frappe-side tests (auraos/auraos/doctype/deal/test_deal_collab.py)
prove the API notifies exactly the users named here, and only the ones
allowed to be named.
"""

import pytest

from auraos.lib.comments import is_blank, mentioned_users, visible_text

MENTION = (
    '<span class="mention" data-type="mention" '
    'data-id="{user}" data-label="{label}">@{label}</span>'
)


def mention(user, label="Someone"):
    return MENTION.format(user=user, label=label)


# -- who was named --


def test_no_mention_is_no_one():
    assert mentioned_users("<p>khách muốn quay trước Tết</p>") == []
    assert mentioned_users("") == []
    assert mentioned_users(None) == []


def test_a_mention_yields_its_user_id():
    html = f"<p>{mention('linh@example.com', 'Linh')} xem giúp nhé</p>"
    assert mentioned_users(html) == ["linh@example.com"]


def test_mentions_keep_typing_order_and_appear_once():
    html = (
        f"<p>{mention('a@example.com')} {mention('b@example.com')} "
        f"{mention('a@example.com')}</p>"
    )
    assert mentioned_users(html) == ["a@example.com", "b@example.com"]


def test_a_span_without_the_mention_class_is_not_a_mention():
    html = '<p><span data-id="linh@example.com">@Linh</span></p>'
    assert mentioned_users(html) == []


def test_the_mention_class_may_sit_among_others():
    html = '<p><span class="prose mention x" data-id="a@example.com">@A</span></p>'
    assert mentioned_users(html) == ["a@example.com"]


def test_attribute_quoting_and_order_do_not_matter():
    variants = [
        "<span data-id='a@example.com' class='mention'>@A</span>",
        '<span data-id=a@example.com class=mention>@A</span>',
        '<span  CLASS="mention"  DATA-ID="a@example.com" >@A</span>',
    ]
    for html in variants:
        assert mentioned_users(html) == ["a@example.com"], html


def test_an_entity_encoded_id_is_decoded():
    html = '<span class="mention" data-id="a&#64;example.com">@A</span>'
    assert mentioned_users(html) == ["a@example.com"]


def test_an_empty_mention_id_names_nobody():
    assert mentioned_users('<span class="mention" data-id=" ">@?</span>') == []
    assert mentioned_users('<span class="mention">@?</span>') == []


# -- whether anything was said --


@pytest.mark.parametrize(
    "html",
    ["", None, "<p></p>", "<p><br></p>", "<p>&nbsp;</p>", "   ", "<p>  \n  </p>"],
)
def test_an_empty_editor_is_blank(html):
    assert is_blank(html) is True


def test_words_are_not_blank():
    assert is_blank("<p>đã book đạo diễn</p>") is False


def test_a_comment_that_is_only_a_pasted_image_is_not_blank():
    assert is_blank('<p><img src="/private/files/screenshot.png"></p>') is False


def test_a_comment_that_is_only_a_mention_is_not_blank():
    assert is_blank(f"<p>{mention('linh@example.com', 'Linh')}</p>") is False


# -- what a reader sees --


def test_visible_text_drops_markup_and_collapses_space():
    html = "<p>khách   muốn</p><p>quay&nbsp;trước Tết</p>"
    assert visible_text(html) == "khách muốn quay trước Tết"


def test_visible_text_keeps_the_at_name_of_a_mention():
    html = f"<p>{mention('linh@example.com', 'Linh')} xem giúp</p>"
    assert visible_text(html) == "@Linh xem giúp"

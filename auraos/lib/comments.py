"""What a comment says, read without a database.

A comment stopped being a line of text the moment it could name someone
and carry a pasted screenshot. Two questions about that HTML are pure
text work - who was named in it, and whether anything was actually said
- so they live here rather than in the API adapter, and are pinned by
pytest rather than by a site test.

Nothing here trusts the markup: a mention id is read out of whatever
the editor sent, and the caller checks it against the seats that may
actually be named before anyone is notified.
"""

import re
from html import unescape

# The editor writes a mention as
#   <span class="mention" data-type="mention" data-id="a@b" data-label="A">@A</span>
# Attribute order and quoting are the renderer's business, so match the
# opening tag and read attributes out of it rather than assuming a shape.
_OPEN_SPAN = re.compile(r"<span\b([^>]*)>", re.IGNORECASE)
_IMG = re.compile(r"<img\b", re.IGNORECASE)
_TAG = re.compile(r"<[^>]*>")


def _attribute(attrs, name):
    match = re.search(
        rf"""{name}\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""",
        attrs,
        re.IGNORECASE,
    )
    if not match:
        return ""
    return unescape(next(group for group in match.groups() if group is not None))


def mentioned_users(html):
    """User ids named in a comment, in the order they were typed, once each.

    Read before the content is sanitised: a scrubber that drops unknown
    data attributes would otherwise silently drop the notification while
    leaving the visible "@Name" in place, which is the worst of both.
    """
    found = []
    for attrs in _OPEN_SPAN.findall(html or ""):
        if "mention" not in _attribute(attrs, "class").split():
            continue
        user = _attribute(attrs, "data-id").strip()
        if user and user not in found:
            found.append(user)
    return found


def visible_text(html):
    """The words a reader sees, with the markup and entities gone."""
    text = _TAG.sub(" ", html or "")
    return " ".join(unescape(text).replace("\xa0", " ").split())


def is_blank(html):
    """True when a comment carries neither words nor a picture.

    An empty editor still sends `<p></p>`, and a comment that is nothing
    but a pasted screenshot has no text at all - so neither the raw
    string nor the stripped text answers this on its own.
    """
    if _IMG.search(html or ""):
        return False
    return not visible_text(html)

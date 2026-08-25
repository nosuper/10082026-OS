"""Plain text as HTML, for a field that has become a rich-text one.

Framework-free by contract like the rest of auraos/lib, so the patch that
converts what is already stored and any future caller share one answer
about what a line break was.

The rule is the boring one and it is the point: **a blank line was a
paragraph, a single newline was a line break, and everything else was
text.** Somebody wrote those briefs in a textarea where that is exactly
what those keys did, so that is what they meant.

Text is escaped, never trusted. A brief containing "budget < 200tr" is a
sentence, not a broken tag, and it has to survive as one.
"""

from __future__ import annotations

import re
from html import escape

# A body that already carries a block tag has been through an editor and
# is left exactly as it is. Deliberately a narrow list of the tags this
# app's own toolbar can produce, plus div, rather than "does it contain a
# angle bracket" - which "budget < 200tr" would satisfy.
BLOCK_TAG = re.compile(r"<\s*(p|div|h[1-6]|ul|ol|li|br)\b", re.IGNORECASE)


def looks_like_html(value: str) -> bool:
    """Whether this body has already been written by an editor."""
    return bool(BLOCK_TAG.search(value or ""))


def from_plain_text(value: str | None) -> str:
    """One plain-text body as the paragraphs its author typed.

    Empty in, empty out - an unwritten brief stays unwritten rather than
    becoming an empty paragraph that reads as one somebody cleared.
    """
    text = (value or "").strip()
    if not text:
        return ""
    if looks_like_html(text):
        return text
    paragraphs = re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n"))
    return "".join(
        "<p>{}</p>".format("<br>".join(escape(line) for line in block.split("\n")))
        for block in paragraphs
        if block.strip()
    )

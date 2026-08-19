"""Reading a Library document as something other than its markup.

Framework-free by contract like the rest of auraos/lib. The Library half
of the Documents screen shows knowledge documents as cards, and a card
needs a line of the document's prose - not its HTML, and not its title
repeated.

This is the inverse of `richtext.from_plain_text`, and it deliberately
does not live next to it. That module answers "what did the person who
typed this into a textarea mean"; this one answers "what does this
document say, in one line". One caller each, opposite directions. If a
second caller ever wants plain text out of HTML, this moves there and
the two sit together.

**Tags are stripped before entities are decoded, and the order is the
whole correctness argument.** A body carrying the sentence "budget
&lt; 200tr" is storing a literal `<` that the author typed. Decode
first and that `<` becomes markup to the tag stripper, which then eats
the rest of the sentence - the same failure `richtext` escapes to
prevent, arrived at from the other side.

**Block boundaries are word boundaries.** `<p>Bước 1</p><p>Bước 2</p>`
is two sentences, not "Bước 1Bước 2". Every tag becomes a space and the
spaces are collapsed afterwards, so no rule is needed about which tags
are blocks.
"""

from __future__ import annotations

import re
from html import unescape

# Any tag, including the unclosed fragment a truncated body can end on.
TAG = re.compile(r"<[^>]*>")

# `sanitize_html` leaves these behind and they are not prose.
INVISIBLE = re.compile(r"(?is)<(script|style)\b.*?</\1>")


def to_plain_text(html: str | None) -> str:
    """The words in a rich-text body, with the markup taken out.

    Empty in, empty out - a document with no body reads as one nobody
    has written yet, not as an empty string pretending to be prose.
    """
    if not html:
        return ""
    without_code = INVISIBLE.sub(" ", html)
    # Tags first, then entities: see the module docstring.
    words = unescape(TAG.sub(" ", without_code))
    # `&nbsp;` unescapes to U+00A0, which is not whitespace to `split()`.
    return " ".join(words.replace(" ", " ").split())


def snippet(html: str | None, limit: int = 160) -> str:
    """One line of a document's prose, for a card that is not the document.

    Cut on a word boundary so the preview never ends mid-word, and only
    mark the cut when there is something after it. A snippet that fits
    is the whole text and says so by carrying no ellipsis.
    """
    text = to_plain_text(html)
    if len(text) <= limit:
        return text
    head = text[: limit + 1]
    cut = head.rfind(" ")
    # A single word longer than the limit has no boundary to fall back
    # to, so it is cut where it is rather than returned whole.
    return (head[:cut] if cut > 0 else text[:limit]).rstrip() + "..."

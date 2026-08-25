"""Whether a generated paper has been signed, framework-free (issue #106).

The founder's question is "has the client actually signed it?", and the
answer a filing cabinet gives is one of three words: **Draft** while the
paper has only been generated, **Awaiting signature** once it has gone
out to whoever must sign, **Signed** once it comes back.

Two decisions live here rather than in the API or the screen.

**There is no order.** A paper can be moved back to Draft, because a real
document sometimes has to be redone - a wrong tax code, a renegotiated
figure - and a status set by mistake must not be a one-way door. So the
rule is a vocabulary, not a sequence: any of the three may follow any
other, and nothing else may follow anything.

**A blank reads as Draft.** Rows written before this field existed carry
no status at all, and a blank column in the "what is still unsigned"
view would read as a fourth state nobody agreed to. The read path maps
the absence onto the state it means.

No Frappe imports by contract; the Generated Paper controller and the API
are thin adapters over this module.
"""

from __future__ import annotations

# The stored values. English on the enum like every other status in the
# app, and short enough to be the label a human reads as well.
DRAFT = "Draft"
AWAITING_SIGNATURE = "Awaiting signature"
SIGNED = "Signed"

# Listed in the order a paper usually travels, which is the order the
# screen offers them in - not an order anything enforces.
STATUSES = (DRAFT, AWAITING_SIGNATURE, SIGNED)


def is_status(value) -> bool:
    """Whether this is one of the three, spelled exactly."""
    return value in STATUSES


def validated(value) -> str:
    """The status, or a ValueError naming what was allowed instead.

    Callers turn the ValueError into whatever their framework says to a
    human; this module has no opinion about that.
    """
    if not is_status(value):
        raise ValueError(f"{value!r} is not a paper status: {', '.join(STATUSES)}")
    return value


def can_move(current, target) -> bool:
    """Whether a paper at `current` may be moved to `target`.

    True between any two known statuses, including back to Draft and
    including a move onto the status the paper already carries - marking
    a signed paper signed again is a no-op, not an error.
    """
    return is_status(current) and is_status(target)


def status_or_draft(value) -> str:
    """What a stored status means, with the blank of an older row as Draft.

    Only the blank is forgiven: a value that is not blank and not one of
    the three is a bug somewhere upstream, and hiding it as Draft would
    turn "we never wrote this" into "somebody typed nonsense here".
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return DRAFT
    return validated(value)

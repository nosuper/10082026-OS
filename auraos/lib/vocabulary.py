"""Managed vocabularies - the small editable lists behind a deal's Links.

A deal's **source** and **project type** are not Selects frozen into
code: the founder asked for lists that keep growing as a new expo or a
new kind of job appears (issue #21). T3.2 grew them in the Desk, and the
T3.1+T3.2 walkthrough found the flaw - the founder could not find where
to add a source at all. T3.5 (issue #29) moves the lists onto the SPA
Settings screen, which forces two rules to be written down rather than
implied by whichever screen happens to be open.

**Who manages which list.** Sources are managed by the founder, the
admin seat and the producer - the walkthrough answer that supersedes the
founder-only guard T3.2 built. Project types stay founder and admin: the
type list is what the "what kind of work do we actually do" question is
asked of in six months, so it drifts at the founder's pace, not the
week's. Tags are absent from this module on purpose - they are
open-creation for both operating roles and grow from the deal form.

**What happens to a value already in use.** Two different answers,
because renaming and removing are two different intentions:

- **Rename migrates.** "Expo" becoming "Trade show" is the same source
  under a better name, so every deal already on it follows. Nothing is
  left holding a value that no longer exists, and no deal quietly loses
  where it came from. Merging two values into one is *not* offered:
  renaming onto a name already in the list is refused, because that
  would silently rewrite history for the deals on the target value.
- **Removal refuses while in use.** Deleting a value that deals hold
  could only either blank those deals or leave dangling links, and both
  lose the answer to a question the data is kept for. So a value on even
  one deal cannot be removed; the refusal says how many deals hold it
  and points at renaming instead. Clearing the field on those deals
  first is the deliberate way to say "this really was never a source".

No Frappe imports by contract - `auraos.api` is the thin adapter, and
these rules are testable without a site (tests/test_vocabulary.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

# The two operating roles, as `auraos.setup.install.ROLES` names them.
FOUNDER = "Founder"
PRODUCER = "Producer"

# The admin seat the walkthrough answer names alongside the founder.
# This app grows no "Admin" role of its own: an administrator is whoever
# holds Frappe's own System Manager role (and `Administrator` itself,
# which Frappe does not always list among a session's roles).
ADMIN_ROLES = frozenset({"System Manager", "Administrator"})


@dataclass(frozen=True)
class Vocabulary:
    """One managed list: what it is called, where it lives, who edits it.

    `used_by` is every (doctype, fieldname) pair that Links at this list.
    It is what makes "in use" a count rather than a guess, and it is
    deliberately explicit: a new Link field pointing here has to be added
    to this tuple, or removal would happily delete a value that field
    still holds.
    """

    key: str
    label: str
    doctype: str
    value_field: str
    used_by: tuple[tuple[str, str], ...]
    managed_by: frozenset[str]


SOURCE = Vocabulary(
    key="source",
    label="Deal sources",
    doctype="Deal Source",
    value_field="source_name",
    used_by=(("Deal", "source"),),
    # The walkthrough answer of 2026-08-10: the producer takes calls, so
    # the producer names where they came from.
    managed_by=frozenset({FOUNDER, PRODUCER}),
)

PROJECT_TYPE = Vocabulary(
    key="project_type",
    label="Project types",
    doctype="Project Type",
    value_field="type_name",
    used_by=(("Deal", "project_type"),),
    managed_by=frozenset({FOUNDER}),
)

VOCABULARIES = {vocab.key: vocab for vocab in (SOURCE, PROJECT_TYPE)}


class UnknownVocabulary(KeyError):
    """A key that names no managed list."""


def vocabulary(key) -> Vocabulary:
    """The managed list a key names, or `UnknownVocabulary`."""
    try:
        return VOCABULARIES[key]
    except KeyError:
        raise UnknownVocabulary(key) from None


def may_manage(key, roles: Iterable[str]) -> bool:
    """May a session holding `roles` add / rename / remove in this list?

    The admin seat manages every list; otherwise the list itself says
    who. A role-less session manages nothing, and neither does Crew -
    the vocabularies belong to the deal pipeline, which crew never see.
    """
    held = set(roles or ())
    if held & ADMIN_ROLES:
        return True
    return bool(held & vocabulary(key).managed_by)


def manageable_keys(roles: Iterable[str]) -> tuple[str, ...]:
    """Which lists this session may manage, in declaration order.

    The SPA draws its Settings sections from this: a producer sees the
    sources section and no project-type section at all, rather than a
    section that answers with a permission error when touched.
    """
    return tuple(key for key in VOCABULARIES if may_manage(key, roles))


def clean_value(raw) -> str:
    """The stored form of a typed value, or `ValueError` if it is empty.

    Only the surrounding whitespace is taken off. Case and accents are
    left exactly as typed: "Zalo" and "TikTok" are names, and a list
    that quietly lowercases them reads as broken to the person who typed
    them.
    """
    value = (raw or "").strip()
    if not value:
        raise ValueError("A value cannot be empty")
    return value


def rename_refusal(vocab: Vocabulary, old: str, new: str, existing) -> str | None:
    """Why this rename cannot go ahead, or None if it can.

    Renaming onto a name already in the list would merge two values, and
    a merge rewrites the source of every deal on the target - a decision
    nobody made by typing in a rename box.
    """
    if old == new:
        return None
    if new in set(existing or ()):
        return (
            f"{new} is already in {vocab.label.lower()}. "
            "Renaming onto it would merge the two values and rewrite the "
            "deals on both, so it is refused - remove one instead."
        )
    return None


def removal_refusal(vocab: Vocabulary, value: str, in_use: int) -> str | None:
    """Why this value cannot be removed, or None if it can.

    See the module docstring: a value deals still hold stays, because
    removing it could only blank those deals or dangle their link.
    """
    if not in_use:
        return None
    deals = "deal" if in_use == 1 else "deals"
    those = "that deal" if in_use == 1 else "those deals"
    return (
        f"{value} is still on {in_use} {deals}. Rename it to carry {those} "
        f"across, or clear the value off {those} first - removing it here "
        "would leave them holding a value that no longer exists."
    )

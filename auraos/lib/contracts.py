"""Contract numbering, and the partner abbreviation it is built from (#139).

Framework-free on purpose: what a contract is called is a rule the
company owns, and it should be readable and testable without a site.

The shape is `{TYPE}{DDMMYY}/AURA-{PARTNER}` - `HDDV200826/AURA-SUMO`.
Two decisions inside it are the founder's and are worth stating here,
because both look like oversights to anyone who assumes the usual:

**The date is the signing date, not the generation date.** A contract is
identified by when it was agreed. Regenerating the same paper a week
later because a typo was fixed must not rename the agreement.

**There is no central counter.** Date plus partner is what makes the
number unique, and a machine-invented sequence would read as an issued
serial - implying a register the company does not keep and a continuity
it cannot promise. A same-day second contract with the same partner
takes a `-2` suffix, which is visibly an ordinal within a day rather
than a position in a ledger.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Iterable

# The legal-form words a Vietnamese company name opens with. Dropped
# before abbreviating, because every client has them and none of them
# distinguishes anybody: abbreviating "Công ty TNHH SUMO" without this
# gives CTTS, which names the company form rather than the company.
LEGAL_FORMS = (
    "công ty tnhh mtv",
    "công ty tnhh một thành viên",
    "công ty cổ phần",
    "công ty tnhh",
    "công ty",
    "cong ty",
    "ctcp",
    "tnhh",
    "co., ltd",
    "co ltd",
    "ltd",
    "jsc",
)

# Long enough to stay recognisable, short enough to read inside a
# filename and a contract header. Not a storage limit - the field takes
# whatever the founder types over the suggestion.
MAX_SUGGESTION = 12
MAX_INITIALS = 6


def fold(text: str) -> str:
    """Vietnamese to bare ASCII letters, preserving reading order.

    `đ`/`Đ` is handled before the decomposition because it is a distinct
    letter rather than a `d` with a mark: NFD leaves it alone, so it
    would otherwise survive into a supposedly-ASCII code.
    """
    if not text:
        return ""
    swapped = text.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", swapped)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _strip_legal_form(name: str) -> str:
    lowered = name.strip().lower()
    for form in LEGAL_FORMS:
        if lowered.startswith(form):
            return name.strip()[len(form) :].strip(" .,-")
    return name.strip()


def suggest_short_code(company_name: str) -> str:
    """A partner abbreviation proposed from the company's name.

    A suggestion, never an answer: it is written into an editable field
    and the founder overrides it whenever the company is known by
    something the name does not contain. The rules are deliberately dull
    so the suggestion is predictable rather than clever.

    One distinctive word becomes that word. Several become their
    initials, which is how these are abbreviated in practice - "Xưởng
    phim Bình Minh" is XPBM on a folder tab, not XUONGPHIM.
    """
    trimmed = _strip_legal_form(company_name or "")
    words = [word for word in re.split(r"[^0-9A-Za-zÀ-ỹ]+", fold(trimmed)) if word]
    if not words:
        return ""
    if len(words) == 1:
        return words[0][:MAX_SUGGESTION].upper()
    return "".join(word[0] for word in words)[:MAX_INITIALS].upper()


def normalise_short_code(value: str) -> str:
    """What a typed short code becomes before it is stored or used.

    The number is read aloud, typed into emails and used in filenames,
    so a code with a space or a slash in it would produce a contract
    number that cannot be any of those things. Folded, stripped to
    letters and digits, uppercased.
    """
    return re.sub(r"[^0-9A-Za-z]+", "", fold(value or "")).upper()


# The kind that owns a job's contract number. BBNT and DNTT are written
# about a contract rather than being one, so they carry the HDDV's
# number instead of minting their own.
CONTRACT_KIND = "HDDV"
CHILD_KINDS = ("BBNT", "DNTT")


def number_for(
    kind: str,
    signed_on: date,
    short_code: str,
    taken: Iterable[str] = (),
    parent_number: str | None = None,
) -> str | None:
    """The number a paper of this kind carries, or None if it carries none.

    Three answers, and the middle one is the reason this is a function
    rather than a call to `contract_number`:

    - **A contract mints its own.** HDDV, from date and partner.
    - **A child paper inherits.** BBNT and DNTT are written *about* a
      contract, so they repeat its number rather than deriving one that
      would agree today and drift the moment either side changed. If the
      parent has not been generated yet, this returns None rather than
      minting one, because a delivery note quoting a contract number
      that no contract carries is worse than one quoting none.
    - **Everything else carries nothing.** Blank kind is a real state,
      not an omission: the phụ lục is an attachment, and a number on it
      would imply an agreement it does not contain.
    """
    kind = (kind or "").upper()
    if not kind:
        return None
    if kind in CHILD_KINDS:
        return parent_number or None
    if kind != CONTRACT_KIND:
        return None
    return contract_number(kind, signed_on, short_code, taken)


def contract_number(
    kind: str,
    signed_on: date,
    short_code: str,
    taken: Iterable[str] = (),
) -> str:
    """The number a paper of this kind carries, given who and when.

    `taken` is whatever numbers already exist for this kind, date and
    partner; the first free `-N` is used. It is passed in rather than
    queried so this stays a rule instead of a database call, and so a
    caller can decide for itself what "already exists" means.
    """
    code = normalise_short_code(short_code)
    if not code:
        raise ValueError("a contract number needs the partner's short code")
    stem = f"{kind.upper()}{signed_on.strftime('%d%m%y')}/AURA-{code}"
    existing = set(taken)
    if stem not in existing:
        return stem
    # Starts at 2 because the unsuffixed number is the first one. A
    # "-1" would imply a "-0" somewhere and invite the reader to look
    # for a sequence that does not exist.
    suffix = 2
    while f"{stem}-{suffix}" in existing:
        suffix += 1
    return f"{stem}-{suffix}"

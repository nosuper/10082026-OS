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


# The kinds that own a contract number. BBNT and DNTT are written
# *about* a contract rather than being one, so they carry their
# parent's number instead of minting their own.
#
# Two contract kinds, not one: HDDV is the client contract and HDCC the
# vendor one, and both are agreements this company signs. Written as a
# tuple rather than a constant because the single-kind form encoded
# "HDDV is the only thing that can be a parent", which was true by
# accident and would have been wrong the first time anything was
# written about a vendor contract.
CONTRACT_KINDS = ("HDDV", "HDCC")
CHILD_KINDS = ("BBNT", "DNTT")


KNOWN_KINDS = CONTRACT_KINDS + CHILD_KINDS


def number_for(
    kind: str,
    signed_on: date,
    short_code: str,
    taken: Iterable[str] = (),
    parent_number: str | None = None,
) -> str | None:
    """The number this paper is issued under - its OWN, whatever its kind.

    Every kind in the standard has a prefix of its own: HDDV, HDCC,
    BBNT, DNTT. A payment request is a document with an identity, not
    only a pointer at a contract.

    This once returned the parent's number for a child paper, which read
    "inherit the parent's number" as "have no number of your own". Those
    are different claims, and the template caught it: the DNTT asks for
    both its own serial and the contract's, in two different sentences.
    The inheritance ruling governs the parent *reference* - see
    `parent_reference` - not the paper's identity.

    Blank kind still carries nothing: the phụ lục is an attachment.

    `parent_number` is accepted and ignored here so callers can pass one
    set of arguments to both functions.
    """
    kind = (kind or "").upper()
    if kind not in KNOWN_KINDS:
        return None
    return contract_number(kind, signed_on, short_code, taken)


def parent_reference(kind: str, parent_number: str | None) -> str | None:
    """The contract a child paper is written *about*, or None.

    Copied, never re-derived - a re-derivation would agree today and
    drift the moment either side moved, and a paper quoting a contract
    number no contract carries is worse than one quoting none.

    A contract has no parent: HDDV and HDCC are the agreement itself.
    """
    if (kind or "").upper() not in CHILD_KINDS:
        return None
    return parent_number or None


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


# -- what a two-part contract says about payment (#139/#146) ----------------

#: The plan shape a two-part contract can describe. The founder's rule:
#: "đa phần là 2 mốc, 3 mốc thì sẽ có hợp đồng 3 mốc" - most deals are
#: two milestones, and a three-milestone deal gets a three-milestone
#: contract rather than a two-milestone one that quietly leaves a third
#: of the money undescribed.
TWO_PART = 2


def payment_split(milestones):
    """The deposit and final halves of a plan, or why they cannot be said.

    Returns `(values, refusal)`. `refusal` is None when the plan fits.

    **The first milestone is always the deposit** - "mốc đầu auto là
    cọc" - so that half never needs asking about.

    **The final half is only sayable when the plan has exactly two
    milestones.** Against three, "final" could mean the last one or
    everything after the deposit, and those differ by a quarter of the
    contract value. A wrong percentage here is not a display bug: it is
    a number on a document somebody signs. So this refuses, names the
    shape it found, and leaves the gap visible - the same choice as a
    child paper carrying no number rather than minting a plausible one.

    A plan's three-milestone default is internal tracking, not a claim
    about what any contract says.
    """
    rows = list(milestones or [])
    if not rows:
        return {}, "no_milestones"

    values = {
        "deposit_pct": rows[0].get("pct"),
        "deposit_amount": rows[0].get("amount"),
    }
    if len(rows) != TWO_PART:
        return values, f"plan_has_{len(rows)}"

    values["final_pct"] = rows[1].get("pct")
    values["final_amount"] = rows[1].get("amount")
    return values, None


# -- what a freelancer contract says about the fee (#148) -------------------

def freelancer_fee(net):
    """The three figures a freelancer contract states, from the net fee.

    The company's pricing convention, which this must not restate in its
    own terms: **a freelancer quotes a net figure and the company bears
    10% PIT on the gross**, so gross = net / 0.9 and the tax = net / 9.
    That is `lib/pricing.py`'s TaxType.CA_NHAN arithmetic, and there is a
    test here comparing the two so a rate changed in one cannot survive
    in the other.

    The template's own wording is what decides which figure goes on
    which line, and it was read rather than assumed: "phí dịch vụ là
    [TỔNG PHÍ] VNĐ (bao gồm 10% thuế TNCN - Bên A khấu trừ và đóng thay
    cho Bên B tương ứng [SỐ TIỀN TNCN] VNĐ)". So TỔNG PHÍ is the GROSS,
    stated as tax-inclusive, and the withholding is named beside it.

    A contract stating gross-with-withholding and one stating
    net-plus-employer-burden carry the same three numbers into different
    lines, which is why this is not obvious from the numbers alone.

    Returns None for anything unreadable, so a fee nobody entered leaves
    a visible gap rather than a plausible zero.
    """
    from decimal import Decimal

    if net is None or net == "":
        return None
    try:
        amount = Decimal(str(net))
    except Exception:
        return None
    if amount < 0:
        return None
    gross = amount / Decimal("0.9")
    return {
        "gross": gross,
        "tax": amount / 9,
        "net": amount,
    }

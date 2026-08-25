"""Numbers written out in Vietnamese words (#145).

On a Vietnamese contract the words are the authoritative reading of the
figure. If the words and the digits disagree, what was agreed is
ambiguous - so this is a correctness problem, not a formatting one, and
it is framework-free and exhaustively tested for that reason.

The rules that are not obvious to a reader coming from English, each of
which has a test:

**Five changes its name after a ten.** `năm` alone, `lăm` after `mười`
or `mươi` - mười lăm, hai mươi lăm. Writing "mười năm" says "ten years".

**One changes after a twenty.** `một` alone and after `mười`, but `mốt`
after `mươi` - hai mươi mốt, never hai mươi một. Eleven stays mười một.

**Four changes too, but only after `mươi`.** hai mươi tư, and mười bốn
rather than mười tư. This is the convention Vietnamese contracts use;
`bốn` is not wrong in speech, but paperwork says tư.

**Ten is two different words.** `mười` as the tens digit, `mươi` after
another digit - mười, hai mươi.

**An empty tens place is spoken, not skipped.** `linh` - một trăm linh
năm, not "một trăm năm", which would say five hundred.

**An empty hundreds place inside a larger number is spoken too.** một
nghìn không trăm linh năm. Dropping it turns 1005 into 1050 to the ear.

**Checked against published rules, not against our ear** (#145). The
accounting convention for invoices, which is what these contracts
follow, states the three contested digits as thresholds rather than as
habits, and this module implements them as written:

  một when the tens digit is <= 1, mốt when it is >= 2;
  bốn when the tens digit is <= 1, tư when it is >= 2;
  năm when the tens digit is 0, lăm when it is > 0.

That is why fourteen is mười bốn and twenty-four is hai mươi tư - the
same rule, either side of its threshold, which is exactly the founder's
"tuỳ thuộc vào số tiền".

  - Quy tắc viết số tiền bằng chữ trên hóa đơn, citing Thông tư
    26/2015/TT-BTC:
    https://luatvietnam.vn/tin-phap-luat/quy-tac-moi-nhat-ve-viet-so-tien-bang-chu-tren-hoa-don-230-17634-article.html
  - Cách viết số tiền bằng chữ trên hóa đơn:
    https://luatminhkhue.vn/cach-viet-so-tien-bang-chu-tren-hoa-don-ke-toan-doanh-nghiep-can-luu-y.aspx

**Two variants those sources do not settle, named rather than hidden:**

`linh` versus `lẻ` for the empty tens place. Both are current - linh is
the northern and more formal form, lẻ the southern. This module writes
linh, and a test pins it, so switching is one line and a visible diff
rather than a silent drift.

`đồng` versus `đồng chẵn`. Invoices sometimes close a whole amount with
chẵn to mark that nothing follows the unit. Not implemented, because VND
here is always whole and the suffix would be decoration on every line;
if the founder wants it, it is one constant.
"""

from __future__ import annotations

from decimal import Decimal

UNITS = ("không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín")

# 10^3, 10^6, 10^9 - the groups Vietnamese counts in.
SCALES = ("", "nghìn", "triệu", "tỷ")

CURRENCY = "đồng"


def _under_hundred(tens: int, unit: int, spoken_tens: bool) -> list[str]:
    """The tens and units of one group.

    `spoken_tens` says whether a hundreds digit was read out before this,
    which is what decides between "linh năm" and a bare "năm".
    """
    words: list[str] = []
    if tens == 0:
        if unit == 0:
            return words
        if spoken_tens:
            words.append("linh")
        words.append(UNITS[unit])
        return words

    if tens == 1:
        words.append("mười")
        if unit == 5:
            words.append("lăm")  # mười lăm, never mười năm
        elif unit:
            words.append(UNITS[unit])  # mười bốn, not mười tư
        return words

    words.append(UNITS[tens])
    words.append("mươi")
    if unit == 1:
        words.append("mốt")  # hai mươi mốt
    elif unit == 4:
        words.append("tư")  # hai mươi tư
    elif unit == 5:
        words.append("lăm")  # hai mươi lăm
    elif unit:
        words.append(UNITS[unit])
    return words


def _group(value: int, force_hundreds: bool) -> list[str]:
    """One group of three digits.

    `force_hundreds` is set for every group after the most significant
    one: 1005 is "một nghìn không trăm linh năm", because a silent
    hundreds place turns it into 1050 to the ear.
    """
    hundreds, rest = divmod(value, 100)
    tens, unit = divmod(rest, 10)

    words: list[str] = []
    if hundreds or force_hundreds:
        words.append(UNITS[hundreds])
        words.append("trăm")
    words.extend(_under_hundred(tens, unit, spoken_tens=bool(hundreds or force_hundreds)))
    return words


def in_words(value, currency: bool = True) -> str:
    """A whole number written out. Empty string for anything unreadable.

    Returns "" rather than raising or guessing when the value is None,
    blank or not a number: the caller is a template, and a contract with
    a visible gap is safer than one carrying a plausible wrong figure.

    `currency=False` gives a bare count - day terms are read as "bảy",
    not "bảy đồng".
    """
    if value is None or value == "":
        return ""
    try:
        number = int(Decimal(str(value)))
    except Exception:
        return ""
    if number < 0:
        return ""

    if number == 0:
        return f"{UNITS[0]} {CURRENCY}" if currency else UNITS[0]

    # Groups of three, least significant first.
    groups: list[int] = []
    while number:
        number, part = divmod(number, 1000)
        groups.append(part)

    words: list[str] = []
    top = len(groups) - 1
    for index in range(top, -1, -1):
        part = groups[index]
        if part == 0:
            # A silent group still needs its scale when something
            # smaller follows it: 1_000_005 is "một triệu không trăm
            # linh năm", and skipping the group entirely would read as
            # "một triệu năm".
            continue
        words.extend(_group(part, force_hundreds=index != top))
        if SCALES[index]:
            words.append(SCALES[index])

    if currency:
        words.append(CURRENCY)
    return " ".join(words)

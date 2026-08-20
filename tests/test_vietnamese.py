"""Numbers in Vietnamese words (#145).

Enumerated, not sampled. The words are the authoritative reading of a
contract's figure, so every boundary the language has is written out
here rather than trusted to a spot check.
"""

from auraos.lib.vietnamese import in_words


def bare(value):
    return in_words(value, currency=False)


class TestTheDigits:
    def test_each_digit_alone(self):
        assert [bare(n) for n in range(10)] == [
            "không",
            "một",
            "hai",
            "ba",
            "bốn",
            "năm",
            "sáu",
            "bảy",
            "tám",
            "chín",
        ]


class TestFiveChangesItsName:
    """`năm` alone, `lăm` after a ten. "mười năm" would say ten years."""

    def test_five_alone_is_nam(self):
        assert bare(5) == "năm"

    def test_fifteen_is_lam(self):
        assert bare(15) == "mười lăm"

    def test_twenty_five_is_lam(self):
        assert bare(25) == "hai mươi lăm"

    def test_ninety_five_is_lam(self):
        assert bare(95) == "chín mươi lăm"

    def test_five_in_the_hundreds_place_stays_nam(self):
        assert bare(500) == "năm trăm"


class TestOneChangesAfterTwenty:
    """`một` alone and after mười; `mốt` after mươi."""

    def test_one_alone(self):
        assert bare(1) == "một"

    def test_eleven_stays_mot(self):
        assert bare(11) == "mười một"

    def test_twenty_one_is_mot(self):
        assert bare(21) == "hai mươi mốt"

    def test_ninety_one_is_mot(self):
        assert bare(91) == "chín mươi mốt"


class TestFourChangesAfterMuoi:
    """`tư` after mươi, `bốn` after mười - the paperwork convention."""

    def test_fourteen_is_bon(self):
        assert bare(14) == "mười bốn"

    def test_twenty_four_is_tu(self):
        assert bare(24) == "hai mươi tư"

    def test_four_alone_is_bon(self):
        assert bare(4) == "bốn"

    def test_four_hundred_is_bon(self):
        assert bare(400) == "bốn trăm"


class TestTenIsTwoWords:
    def test_muoi_as_the_tens_digit(self):
        assert bare(10) == "mười"

    def test_muoi_after_another_digit(self):
        assert bare(20) == "hai mươi"
        assert bare(30) == "ba mươi"


class TestTheEmptyPlacesAreSpoken:
    def test_linh_fills_an_empty_tens(self):
        # "một trăm năm" would say five hundred.
        assert bare(105) == "một trăm linh năm"
        assert bare(101) == "một trăm linh một"

    def test_a_full_tens_needs_no_linh(self):
        assert bare(110) == "một trăm mười"
        assert bare(150) == "một trăm năm mươi"

    def test_an_empty_hundreds_inside_a_larger_number_is_spoken(self):
        # Dropping it turns 1005 into 1050 to the ear.
        assert bare(1005) == "một nghìn không trăm linh năm"

    def test_the_leading_group_does_not_get_a_phantom_hundred(self):
        assert bare(5) == "năm"
        assert bare(50) == "năm mươi"


class TestTheScales:
    def test_thousand_million_billion(self):
        assert bare(1_000) == "một nghìn"
        assert bare(1_000_000) == "một triệu"
        assert bare(1_000_000_000) == "một tỷ"

    def test_a_silent_group_keeps_the_number_readable(self):
        assert bare(1_000_005) == "một triệu không trăm linh năm"

    def test_a_long_number_reads_end_to_end(self):
        assert (
            bare(1_234_567_890)
            == "một tỷ hai trăm ba mươi tư triệu năm trăm sáu mươi bảy "
            "nghìn tám trăm chín mươi"
        )


class TestTheStudiosOwnAmounts:
    """Real figures from the seed and the walkthrough."""

    def test_ten_million(self):
        assert in_words(10_000_000) == "mười triệu đồng"

    def test_twelve_and_a_half_million(self):
        assert in_words(12_500_000) == "mười hai triệu năm trăm nghìn đồng"

    def test_one_and_a_half_million(self):
        assert in_words(1_500_000) == "một triệu năm trăm nghìn đồng"

    def test_nine_hundred_thousand(self):
        assert in_words(900_000) == "chín trăm nghìn đồng"

    def test_four_million(self):
        assert in_words(4_000_000) == "bốn triệu đồng"


class TestTheTwoModes:
    def test_currency_carries_the_suffix(self):
        assert in_words(7) == "bảy đồng"

    def test_a_day_count_does_not(self):
        # terms.deposit_days in words is "bảy", not "bảy đồng".
        assert bare(7) == "bảy"


class TestWhatItRefusesToGuess:
    """A gap is safer than a plausible wrong figure on a contract."""

    def test_nothing_becomes_nothing(self):
        assert in_words(None) == ""
        assert in_words("") == ""

    def test_words_that_are_not_numbers_become_nothing(self):
        assert in_words("abc") == ""

    def test_a_negative_is_refused_rather_than_read(self):
        # No contract line is negative, and "âm" on one would be a
        # figure nobody meant to write.
        assert in_words(-5) == ""

    def test_zero_is_a_number_and_reads_as_one(self):
        assert in_words(0) == "không đồng"
        assert bare(0) == "không"

    def test_a_decimal_string_reads_its_whole_part(self):
        # VND is not written in fractions; the digits alongside are
        # already rounded by the money formatter.
        assert in_words("1500000.00") == "một triệu năm trăm nghìn đồng"

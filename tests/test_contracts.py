"""Contract numbering and partner abbreviation (#139).

Pure python, no site. Runs under the repo's pytest job.
"""

from datetime import date

from auraos.lib.contracts import (
    contract_number,
    fold,
    normalise_short_code,
    suggest_short_code,
)


class TestFold:
    def test_vietnamese_marks_come_off(self):
        assert fold("Bình Minh") == "Binh Minh"
        assert fold("Xưởng phim") == "Xuong phim"

    def test_d_with_stroke_is_a_letter_not_a_mark(self):
        # NFD does not decompose đ, so stripping combining marks alone
        # leaves it behind and the "ASCII" code is not ASCII.
        assert fold("Đông Đô") == "Dong Do"
        assert fold("đồng") == "dong"

    def test_empty_is_empty_rather_than_an_error(self):
        assert fold("") == ""


class TestSuggestShortCode:
    def test_one_distinctive_word_is_used_whole(self):
        assert suggest_short_code("SUMO") == "SUMO"

    def test_the_legal_form_is_dropped_before_abbreviating(self):
        # The whole point: every client is a Công ty, so including it
        # abbreviates the company form rather than the company.
        assert suggest_short_code("Công ty TNHH SUMO") == "SUMO"
        assert suggest_short_code("Công ty Cổ phần SUMO") == "SUMO"
        assert suggest_short_code("CTCP SUMO") == "SUMO"

    def test_several_words_become_their_initials(self):
        assert suggest_short_code("Xưởng phim Bình Minh") == "XPBM"

    def test_marks_never_reach_the_suggestion(self):
        assert suggest_short_code("Điện Ảnh") == "DA"
        assert suggest_short_code("Đông Đô") == "DD"

    def test_a_long_single_word_is_cut_not_rejected(self):
        assert suggest_short_code("Truyenthongsangtaovietnam") == "TRUYENTHONGS"

    def test_a_nameless_company_suggests_nothing_rather_than_guessing(self):
        assert suggest_short_code("") == ""
        assert suggest_short_code("   ") == ""
        assert suggest_short_code("Công ty TNHH") == ""


class TestNormaliseShortCode:
    def test_what_is_typed_becomes_usable_in_a_filename(self):
        assert normalise_short_code("su mo") == "SUMO"
        assert normalise_short_code("su/mo") == "SUMO"
        assert normalise_short_code(" Bình  Minh ") == "BINHMINH"

    def test_digits_survive(self):
        assert normalise_short_code("K2") == "K2"


class TestContractNumber:
    def test_the_shape_the_founder_specified(self):
        assert (
            contract_number("HDDV", date(2026, 8, 20), "SUMO")
            == "HDDV200826/AURA-SUMO"
        )

    def test_the_date_is_two_digit_day_month_year(self):
        # A single-digit day must not shorten the number - 02 not 2.
        assert contract_number("HDDV", date(2026, 1, 2), "SUMO").startswith(
            "HDDV020126/"
        )

    def test_other_kinds_use_the_same_shape(self):
        assert (
            contract_number("BBNT", date(2026, 8, 20), "SUMO")
            == "BBNT200826/AURA-SUMO"
        )

    def test_a_second_contract_the_same_day_takes_a_suffix(self):
        taken = ["HDDV200826/AURA-SUMO"]
        assert (
            contract_number("HDDV", date(2026, 8, 20), "SUMO", taken)
            == "HDDV200826/AURA-SUMO-2"
        )

    def test_the_suffix_starts_at_two_because_the_first_has_none(self):
        # A -1 would imply a -0 and invite a reader to look for a
        # sequence the company does not keep.
        taken = ["HDDV200826/AURA-SUMO"]
        assert "-1" not in contract_number("HDDV", date(2026, 8, 20), "SUMO", taken)

    def test_it_walks_past_every_number_already_taken(self):
        taken = [
            "HDDV200826/AURA-SUMO",
            "HDDV200826/AURA-SUMO-2",
            "HDDV200826/AURA-SUMO-3",
        ]
        assert (
            contract_number("HDDV", date(2026, 8, 20), "SUMO", taken)
            == "HDDV200826/AURA-SUMO-4"
        )

    def test_a_different_day_is_not_a_collision(self):
        taken = ["HDDV200826/AURA-SUMO"]
        assert (
            contract_number("HDDV", date(2026, 8, 21), "SUMO", taken)
            == "HDDV210826/AURA-SUMO"
        )

    def test_a_different_partner_is_not_a_collision(self):
        taken = ["HDDV200826/AURA-SUMO"]
        assert (
            contract_number("HDDV", date(2026, 8, 20), "XPBM", taken)
            == "HDDV200826/AURA-XPBM"
        )

    def test_a_typed_code_is_normalised_into_the_number(self):
        assert (
            contract_number("HDDV", date(2026, 8, 20), "su mo")
            == "HDDV200826/AURA-SUMO"
        )

    def test_no_short_code_is_refused_rather_than_guessed(self):
        # Generation asks for the code when it is missing. A number
        # built without one would be HDDV200826/AURA- and would look
        # like a real number with a truncated tail.
        try:
            contract_number("HDDV", date(2026, 8, 20), "")
        except ValueError:
            return
        raise AssertionError("a missing short code must raise, not produce a stem")

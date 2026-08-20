"""Contract numbering and partner abbreviation (#139).

Pure python, no site. Runs under the repo's pytest job.
"""

from datetime import date

from auraos.lib.contracts import (
    contract_number,
    fold,
    normalise_short_code,
    number_for,
    payment_split,
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


class TestNumberFor:
    """Which papers mint a number, which inherit one, which carry none."""

    def test_a_contract_mints_its_own(self):
        assert (
            number_for("HDDV", date(2026, 8, 20), "SUMO")
            == "HDDV200826/AURA-SUMO"
        )

    def test_a_child_repeats_the_parent_rather_than_deriving(self):
        # Same date and partner, so a re-derivation would agree today.
        # It inherits anyway, because agreeing today is what two
        # derivations always do until one of them changes.
        parent = "HDDV200826/AURA-SUMO"
        for kind in ("BBNT", "DNTT"):
            assert (
                number_for(kind, date(2026, 8, 20), "SUMO", parent_number=parent)
                == parent
            )

    def test_a_child_inherits_the_parents_suffix_too(self):
        parent = "HDDV200826/AURA-SUMO-2"
        assert (
            number_for("BBNT", date(2026, 8, 20), "SUMO", parent_number=parent)
            == parent
        )

    def test_a_child_with_no_parent_carries_nothing_rather_than_minting(self):
        # A delivery note quoting a contract number that no contract
        # carries is worse than one quoting none.
        assert number_for("BBNT", date(2026, 8, 20), "SUMO") is None

    def test_a_blank_kind_carries_no_number(self):
        # The phu luc is an attachment. A number on it would imply an
        # agreement it does not contain.
        assert number_for("", date(2026, 8, 20), "SUMO") is None
        assert number_for(None, date(2026, 8, 20), "SUMO") is None

    def test_an_unknown_kind_carries_nothing_rather_than_inventing(self):
        assert number_for("XXXX", date(2026, 8, 20), "SUMO") is None

    def test_the_vendor_contract_mints_its_own_too(self):
        # HDCC joined HDDV when vendor contracts became numbered. The
        # single-kind form encoded "HDDV is the only thing that can be a
        # parent", which was true by accident.
        assert (
            number_for("HDCC", date(2026, 8, 20), "SUMO")
            == "HDCC200826/AURA-SUMO"
        )

    def test_a_child_can_inherit_from_a_vendor_contract(self):
        # Nothing is written about a vendor contract today. The code
        # must not assume that, or the first one will silently carry no
        # number at all.
        parent = "HDCC200826/AURA-SUMO"
        assert (
            number_for("BBNT", date(2026, 8, 20), "SUMO", parent_number=parent)
            == parent
        )


class TestPaymentSplit:
    """cọc and cuối, and the plans that cannot say them (#146)."""

    def two(self):
        return [{"pct": 50, "amount": 5_000_000}, {"pct": 50, "amount": 5_000_000}]

    def three(self):
        return [
            {"pct": 50, "amount": 5_000_000},
            {"pct": 25, "amount": 2_500_000},
            {"pct": 25, "amount": 2_500_000},
        ]

    def test_a_two_milestone_plan_fills_both_halves(self):
        values, refusal = payment_split(self.two())
        assert refusal is None
        assert values == {
            "deposit_pct": 50,
            "deposit_amount": 5_000_000,
            "final_pct": 50,
            "final_amount": 5_000_000,
        }

    def test_the_first_milestone_is_always_the_deposit(self):
        # "mốc đầu auto là cọc" - true whatever the split is, so this
        # half never needs a question.
        values, _ = payment_split(
            [{"pct": 30, "amount": 3_000_000}, {"pct": 70, "amount": 7_000_000}]
        )
        assert values["deposit_pct"] == 30

    def test_three_milestones_refuse_the_final_half_rather_than_guess(self):
        # "final" could be the last milestone or everything after the
        # deposit, and those differ by a quarter of the contract value.
        values, refusal = payment_split(self.three())
        assert refusal == "plan_has_3"
        assert "final_pct" not in values
        assert "final_amount" not in values

    def test_the_deposit_still_fills_when_the_final_cannot(self):
        # Refusing the half we cannot say must not withhold the half we
        # can - the deposit is the first milestone whatever follows it.
        values, refusal = payment_split(self.three())
        assert refusal
        assert values["deposit_pct"] == 50

    def test_an_empty_plan_says_so(self):
        values, refusal = payment_split([])
        assert (values, refusal) == ({}, "no_milestones")
        assert payment_split(None) == ({}, "no_milestones")

    def test_one_milestone_is_refused_too(self):
        # Not a two-part contract either. Named by its shape so the
        # message can say what it found.
        _, refusal = payment_split([{"pct": 100, "amount": 10_000_000}])
        assert refusal == "plan_has_1"


class TestFreelancerFee:
    """The fee triple, pinned against pricing.py's own arithmetic (#148)."""

    def test_the_template_states_the_gross_as_tax_inclusive(self):
        from auraos.lib.contracts import freelancer_fee

        # net 9,000,000 -> gross 10,000,000, tax 1,000,000.
        out = freelancer_fee(9_000_000)
        assert int(out["gross"]) == 10_000_000
        assert int(out["tax"]) == 1_000_000
        assert int(out["net"]) == 9_000_000

    def test_it_agrees_with_pricing_rather_than_restating_the_rate(self):
        # The rate lives in pricing.py. If somebody changes it there and
        # not here, this fails rather than the two quietly disagreeing on
        # a signed contract.
        from decimal import Decimal

        from auraos.lib.contracts import freelancer_fee

        net = Decimal("7_500_000".replace("_", ""))
        out = freelancer_fee(net)
        assert out["gross"] == net / Decimal("0.9")
        assert out["tax"] == net / 9

    def test_the_three_figures_reconcile(self):
        from auraos.lib.contracts import freelancer_fee

        out = freelancer_fee(9_000_000)
        assert out["net"] + out["tax"] == out["gross"]

    def test_no_fee_is_a_gap_not_a_zero(self):
        from auraos.lib.contracts import freelancer_fee

        assert freelancer_fee(None) is None
        assert freelancer_fee("") is None
        assert freelancer_fee("abc") is None
        assert freelancer_fee(-1) is None

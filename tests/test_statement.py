"""Pure-python tests for auraos.lib.statement - no Frappe required (#150).

Reading someone else's document is a different job from computing our
own numbers, and these are the decisions that follow from that:

- **A statement that fails its own arithmetic is refused**, loudly and
  saying where. The bank's totals, the opening-to-closing walk and the
  running balance are three separate claims and a failure names which.
- **References are read only where a reference could be.** An
  eight-digit run is what a contract number looks like *and* what a
  trace code looks like, so the pattern fires only in a description
  that mentions a contract, and only when the digits read as a date.
- **Matching suggests, and only when it is not guessing.** Exact amount
  and agreeing direction or nothing; ambiguity is reported as ambiguity
  rather than resolved by picking the nearer one.
- **Some lines can never match, and the module says why.** Tax to the
  treasury, bank interest, cash into the company's own box: three kinds
  of movement AuraOS keeps no record of at all.

The fixtures below are the shapes of the real July 2026 statement -
including its two ways of writing money in one sheet - with the
company's own details left out. The anonymised file the seam tests read
lives beside them.
"""

from datetime import date, datetime

import pytest

from auraos.lib import statement


def line(**overrides):
    """One transaction row as the reader hands it over."""
    row = {
        "effective_on": "01/07/2026",
        "transacted_at": "01/07/2026 01:23:20",
        "sequence": "2621",
        "description": "TAM UNG CONG TAC PHI",
        "withdrawn": "1.0E7",
        "deposited": None,
        "running_balance": "4.9621339E7",
    }
    row.update(overrides)
    return row


def entry(**overrides):
    """One ledger entry as the Frappe side assembles it for matching."""
    one = {
        "name": "CLE-0001",
        "amount": -10_000_000,
        "entry_date": date(2026, 7, 1),
        "references": set(),
    }
    one.update(overrides)
    return one


class TestMoneyArrivesTwoWays:
    def test_the_table_writes_money_in_scientific_notation(self):
        assert statement.to_amount("1.0E7") == 10_000_000
        assert statement.to_amount("4.9621339E7") == 49_621_339

    def test_the_summary_block_writes_it_grouped_with_commas(self):
        assert statement.to_amount("59,621,339.00") == 59_621_339

    def test_a_blank_cell_is_no_money_rather_than_unknown(self):
        """The out and in columns are exclusive on every row, so the
        empty one is a statement about direction, not a gap."""
        assert statement.to_amount(None) == 0
        assert statement.to_amount("") == 0

    def test_something_that_is_not_a_number_is_refused(self):
        with pytest.raises(ValueError):
            statement.to_amount("Ngày hiệu lực")


class TestReadingTheTable:
    def test_a_withdrawal_reads_as_money_out(self):
        (read,) = statement.read_lines([line()])

        assert read["amount"] == -10_000_000
        assert read["direction"] == statement.OUT
        assert read["effective_on"] == date(2026, 7, 1)
        assert read["transacted_at"] == datetime(2026, 7, 1, 1, 23, 20)

    def test_a_deposit_reads_as_money_in(self):
        (read,) = statement.read_lines(
            [line(withdrawn=None, deposited="9.639E7", running_balance="1.04011339E8")]
        )

        assert read["amount"] == 96_390_000
        assert read["direction"] == statement.IN

    def test_the_transacted_moment_is_kept_apart_from_the_effective_day(self):
        """The sample carries a payment transacted on the 1st and
        effective on the 2nd. Which one a match should use is a decision,
        and collapsing them here would take it away."""
        (read,) = statement.read_lines(
            [line(effective_on="02/07/2026", transacted_at="01/07/2026 18:16:41")]
        )

        assert read["effective_on"] == date(2026, 7, 2)
        assert read["transacted_at"].date() == date(2026, 7, 1)


class TestAStatementMustAgreeWithItself:
    def sound(self):
        summary = {
            "opening": 59_621_339,
            "withdrawn": 22_000_000,
            "deposited": 96_390_000,
            "closing": 134_011_339,
        }
        lines = statement.read_lines(
            [
                line(withdrawn="1.0E7", running_balance="4.9621339E7"),
                line(sequence="2622", withdrawn="1.2E7", running_balance="3.7621339E7"),
                line(
                    sequence="2625",
                    withdrawn=None,
                    deposited="9.639E7",
                    running_balance="1.34011339E8",
                ),
            ]
        )
        return summary, lines

    def test_a_statement_that_adds_up_says_nothing(self):
        summary, lines = self.sound()

        assert statement.complaints(summary, lines) == []

    def test_a_total_that_disagrees_is_named(self):
        summary, lines = self.sound()
        summary["withdrawn"] = 21_000_000

        (said,) = statement.complaints(summary, lines)

        assert "22000000" in said and "21000000" in said

    def test_the_walk_from_opening_to_closing_is_its_own_claim(self):
        summary, lines = self.sound()
        summary["closing"] = 1

        said = statement.complaints(summary, lines)

        assert any("closing balance" in one for one in said)

    def test_a_running_balance_that_slips_says_which_line(self):
        """The only one of the three that says *where*, which is what a
        person needs to go and look at the sheet."""
        summary, lines = self.sound()
        lines[1]["running_balance"] = 999

        said = statement.complaints(summary, lines)

        assert any("line 2622" in one for one in said)

    def test_a_dropped_row_shows_up_as_a_disagreement(self):
        """The check is the parser's own alarm as much as the bank's: a
        row silently lost reads exactly like a statement that does not
        add up, and both must refuse the import."""
        summary, lines = self.sound()

        said = statement.complaints(summary, lines[:-1])

        assert said


class TestReferencesAreReadWhereReferencesCanBe:
    def test_a_dashed_contract_number(self):
        assert statement.references("AURA THANH TOAN HDDV 0107-2026") == {
            "HDDV:0107-2026"
        }

    def test_the_same_contract_written_as_an_eight_digit_run(self):
        """`19052026HDDV` and `1905-2026` are one contract written two
        ways, and normalising is what lets a payment meet its job. The
        digits run straight into letters here, which is why the pattern
        cannot lean on a word boundary."""
        assert statement.references("TT SO 19052026HDDV GD 6189MSCBD2ERPVEB") == {
            "HDDV:1905-2026"
        }

    def test_an_invoice_number(self):
        assert "HD:10" in statement.references("THANH TOAN HOA DON SO 10")

    def test_a_line_carrying_both(self):
        found = statement.references(
            "THANH TOAN PHAN CON LAI HOA DON SO 13 - HDDV 2805-2026 SCALLION-AURA"
        )

        assert found == {"HD:13", "HDDV:2805-2026"}

    def test_digits_in_a_description_with_no_contract_in_it_are_not_references(self):
        """The guard that keeps this safe. Without the hint, a bank's own
        trace code would attach money to a job it has nothing to do
        with."""
        assert statement.references("CHUYEN TIEN 6189MSCBD2ERPVEB 20260731") == set()

    def test_an_eight_digit_run_that_is_not_a_date_is_not_a_contract(self):
        assert statement.references("THANH TOAN HDDV 99999999") == set()


class TestTheMovementsAuraosDoesNotModel:
    def test_tax_paid_to_the_treasury(self):
        said = statement.unmodelled("NTDT+KB:0112-KBNN KHU VUC II+MST:0318790381")

        assert said and "treasury" in said

    def test_bank_interest(self):
        assert "interest" in statement.unmodelled("##LAI NHAP VON#")

    def test_cash_moved_into_the_company_box(self):
        said = statement.unmodelled("AURA PRODUCTIONS RUT QUY TIEN MAT")

        assert said and "#151" in said

    def test_an_ordinary_payment_is_not_one_of_them(self):
        """So the three above are claims about those kinds rather than a
        function that says yes to everything."""
        assert statement.unmodelled("TAM UNG CONG TAC PHI") is None


class TestMatchingSuggestsAndNeverDecides:
    def out_line(self, **overrides):
        (read,) = statement.read_lines([line(**overrides)])
        return read

    def test_an_entry_of_the_same_amount_and_day_is_a_candidate(self):
        (found,) = statement.candidates(self.out_line(), [entry()])

        assert found["entry"] == "CLE-0001"
        assert found["confidence"] == statement.WEAK

    def test_a_shared_reference_makes_it_strong(self):
        found = statement.candidates(
            self.out_line(description="AURA THANH TOAN HDDV 0107-2026"),
            [entry(references={"HDDV:0107-2026"})],
        )

        assert found[0]["confidence"] == statement.STRONG
        assert found[0]["shared_references"] == ["HDDV:0107-2026"]

    def test_an_amount_that_is_nearly_right_is_not_a_candidate(self):
        """Two facts a thousand đồng apart are two facts. Offering them
        as one invites somebody to confirm away a real discrepancy."""
        assert statement.candidates(self.out_line(), [entry(amount=-9_999_000)]) == []

    def test_money_going_the_other_way_is_not_a_candidate(self):
        assert statement.candidates(self.out_line(), [entry(amount=10_000_000)]) == []

    def test_an_entry_outside_the_window_is_not_a_candidate(self):
        far = entry(entry_date=date(2026, 7, 20))

        assert statement.candidates(self.out_line(), [far]) == []

    def test_the_window_exists_because_the_bank_posts_late(self):
        late = entry(entry_date=date(2026, 6, 29))

        (found,) = statement.candidates(self.out_line(), [late])

        assert found["days_apart"] == 2

    def test_two_indistinguishable_entries_produce_no_suggestion(self):
        """Reported as ambiguity rather than resolved by ranking: from
        here they are the same, and a person with the job in front of
        them can tell."""
        found = statement.candidates(
            self.out_line(), [entry(), entry(name="CLE-0002")]
        )

        assert len(found) == 2
        assert statement.suggestion(found) is None

    def test_one_strong_candidate_beside_a_weak_one_is_suggested(self):
        found = statement.candidates(
            self.out_line(description="AURA THANH TOAN HDDV 0107-2026"),
            [entry(name="CLE-0002"), entry(references={"HDDV:0107-2026"})],
        )

        suggested = statement.suggestion(found)

        assert suggested["entry"] == "CLE-0001"
        assert suggested["confidence"] == statement.STRONG

    def test_nothing_matching_suggests_nothing(self):
        assert statement.suggestion(statement.candidates(self.out_line(), [])) is None

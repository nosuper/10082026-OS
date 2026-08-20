"""The settlement arithmetic (#153).

The refusal cases are enumerated as thoroughly as the happy ones,
because this is the only module in the family whose wrong answer is a
demand for money on a document somebody signs.
"""

from decimal import Decimal

from auraos.lib.settlement import BANDS, band, refusals, summary


class TestOneBand:
    def test_the_ordinary_case(self):
        row = band(contracted=10_000_000, settled=12_000_000, collected=5_000_000)
        assert row["difference"] == 2_000_000
        assert row["remaining"] == 7_000_000

    def test_an_overrun_is_positive_and_an_underrun_negative(self):
        # The sign is the document's meaning, not a display choice.
        assert band(10_000_000, 12_000_000, 0)["difference"] == 2_000_000
        assert band(10_000_000, 8_000_000, 0)["difference"] == -2_000_000

    def test_remaining_is_measured_against_the_settled_value(self):
        # Billing the contracted figure after a scope reduction would
        # demand money the settlement just agreed to drop.
        row = band(contracted=10_000_000, settled=8_000_000, collected=5_000_000)
        assert row["remaining"] == 3_000_000

    def test_nothing_collected_yet_owes_the_whole_settled_value(self):
        # Zero collected is a fact, not an absence.
        row = band(10_000_000, 10_000_000, 0)
        assert row["collected"] == 0
        assert row["remaining"] == 10_000_000

    def test_a_fully_paid_job_leaves_nothing(self):
        # The one case where a remaining of zero is the truth.
        row = band(10_000_000, 10_000_000, 10_000_000)
        assert row["remaining"] == 0

    def test_an_overpayment_is_reported_not_clamped(self):
        # A negative remaining means we owe the client. Clamping it to
        # zero would hide a refund.
        row = band(10_000_000, 10_000_000, 12_000_000)
        assert row["remaining"] == -2_000_000


class TestItRefusesRatherThanGuessing:
    """The point of the module. A zero here gets signed."""

    def test_no_settled_value_means_no_remaining(self):
        row = band(contracted=10_000_000, settled=None, collected=5_000_000)
        assert row["remaining"] is None
        assert row["difference"] is None

    def test_no_settled_value_does_not_withhold_what_is_known(self):
        # Refusing the figures we cannot state must not suppress the
        # ones we can - the same rule as the payment split's deposit.
        row = band(contracted=10_000_000, settled=None, collected=5_000_000)
        assert row["contracted"] == 10_000_000
        assert row["collected"] == 5_000_000

    def test_no_collection_total_means_no_remaining(self):
        # Distinct from "collected nothing". Unknown is not zero, and
        # treating it as zero would state the full value as owed.
        row = band(10_000_000, 10_000_000, None)
        assert row["collected"] is None
        assert row["remaining"] is None

    def test_no_contracted_value_means_no_difference(self):
        row = band(None, 12_000_000, 5_000_000)
        assert row["difference"] is None
        assert row["remaining"] == 7_000_000

    def test_blank_and_unparseable_are_absences_not_zeroes(self):
        for bad in (None, "", "abc", "—"):
            assert band(10_000_000, bad, 0)["remaining"] is None

    def test_a_decimal_string_is_a_number(self):
        assert band("10000000", "10000000.00", "0")["remaining"] == Decimal("10000000")


class TestTheWholeTable:
    def rows(self):
        return summary(
            contracted={"pre_vat": 10_000_000, "vat": 800_000, "total": 10_800_000},
            settled={"pre_vat": 12_000_000, "vat": 960_000, "total": 12_960_000},
            collected={"pre_vat": 5_000_000, "vat": 400_000, "total": 5_400_000},
        )

    def test_every_band_is_stated(self):
        rows = self.rows()
        assert set(rows) == set(BANDS)
        assert rows["total"]["remaining"] == 7_560_000

    def test_the_total_is_not_derived_from_the_other_two(self):
        # Deriving it would turn one unknown band into a total that
        # understates the bill by exactly that band - which for VAT is
        # how an invoice quietly loses its tax.
        rows = summary(
            contracted={"pre_vat": 10_000_000, "total": 10_800_000},
            settled={"pre_vat": 10_000_000, "total": 10_800_000},
            collected={"pre_vat": 0, "total": 0},
        )
        assert rows["vat"]["settled"] is None
        assert rows["total"]["remaining"] == 10_800_000

    def test_an_empty_call_states_nothing_rather_than_zeroes(self):
        rows = summary()
        for name in BANDS:
            assert rows[name]["remaining"] is None
            assert rows[name]["settled"] is None


class TestRefusalsAreNamed:
    def test_each_missing_source_is_named_for_a_person(self):
        rows = summary(
            contracted={"pre_vat": 10_000_000, "vat": 800_000, "total": 10_800_000},
            settled={"pre_vat": 10_000_000},
            collected={"pre_vat": 0, "vat": 0, "total": 0},
        )
        said = refusals(rows)
        assert "vat: no settled value" in said
        assert "total: no settled value" in said
        assert "pre_vat: no settled value" not in said

    def test_a_complete_table_refuses_nothing(self):
        assert refusals(self_complete()) == ()


def self_complete():
    return summary(
        contracted={name: 1 for name in BANDS},
        settled={name: 1 for name in BANDS},
        collected={name: 0 for name in BANDS},
    )

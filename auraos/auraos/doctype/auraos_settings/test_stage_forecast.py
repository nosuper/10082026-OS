"""Contract tests for the cash forecast (#102, spec #81).

The arithmetic is pinned framework-free in tests/test_forecast.py. This
file is the other seam: the payload the React screen reads, and the five
things only a database can show.

1. **A projection cannot travel under a cash name.** The guard runs over
   the real wire payload here, not only over the pure module's dict, so
   an endpoint that decorated the report with a `total` on the way out
   would fail. #101 put a cash balance beside this figure on the same
   dashboard; that one is a fact and this one is an estimate multiplied
   by a guess, and the payload is where the two are told apart.
2. **The stage vocabulary is the Deal Select's**, checked against the
   doctype meta rather than against a second list written by hand.
3. **The Single-defaults trap is closed.** A settings table nobody has
   written falls back to the house defaults and says `configured: false`,
   never to 0% - and the patch writes real rows, idempotently, without
   overwriting a dial the founder has since set. Lost's legitimate 0 is
   kept as a row, which is the only thing that distinguishes it from a
   field nobody ever wrote.
4. **Changing a probability changes the forecast on the next read**,
   with nothing cached in between and no stored figure to go stale.
5. **The forecast is the founder's.** A producer is refused by the
   server, and refused because AuraOS Settings refuses them - never
   because a screen decided not to ask.

Runs via: bench --site <site> run-tests --app auraos
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from auraos.api import (
    set_stage_forecast_rules,
    stage_forecast_rules,
    weighted_pipeline_forecast,
)
from auraos.auraos.doctype.deal.test_deal import FOUNDER, PRODUCER, make_deal
from auraos.lib import forecast
from auraos.patches import seed_stage_forecast
from auraos.tests.contract import (
    assert_counts,
    assert_iso_date,
    assert_keys,
    assert_money,
)
from auraos.tests.utils import make_test_user

REPORT_KEYS = [
    "basis",
    "as_of",
    "weighted_projection",
    "open_pipeline",
    "deal_count",
    "months",
    "stages",
    "unruled",
    "unruled_pipeline",
]

MONTH_KEYS = ["month", "weighted_projection", "open_pipeline", "deal_count", "deals"]

STAGE_KEYS = [
    "stage",
    "win_probability_pct",
    "lead_days",
    "configured",
    "contributes",
    "deal_count",
    "open_pipeline",
    "weighted_projection",
    "month",
]

DEAL_KEYS = [
    "deal",
    "title",
    "stage",
    "deal_value",
    "value_basis",
    "win_probability_pct",
    "lead_days",
    "weighted_projection",
    "month",
]

RULE_KEYS = ["stage", "win_probability_pct", "lead_days", "configured", "contributes"]

BUDGET = 150_000_000


class StageForecastTestCase(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        make_test_user(FOUNDER, "Founder")
        make_test_user(PRODUCER, "Producer")

    def setUp(self):
        frappe.set_user("Administrator")
        self.clear_open_deals()
        self.clear_rules()

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def clear_open_deals(self):
        """A studio whose pipeline is empty - the starting state.

        Only the open ones: a won deal is somebody's job and the jobs
        link to it, and the forecast never reads Won or Lost anyway.
        """
        frappe.db.delete("Deal", {"stage": ["not in", list(forecast.RESOLVED)]})

    def clear_rules(self):
        """A settings table nobody has ever written - the trap's state."""
        frappe.db.delete(
            "Deal Stage Forecast", {"parenttype": "AuraOS Settings"}
        )
        frappe.clear_document_cache("AuraOS Settings", "AuraOS Settings")

    def seed(self):
        seed_stage_forecast.execute()

    def rule_for(self, stage, rules=None):
        rows = rules if rules is not None else stage_forecast_rules()["stages"]
        (row,) = [row for row in rows if row["stage"] == stage]
        return row

    def stage_of(self, report, stage):
        (row,) = [row for row in report["stages"] if row["stage"] == stage]
        return row

    def month_of(self, report, key):
        (row,) = [row for row in report["months"] if row["month"] == key]
        return row

    def row_for(self, report, deal):
        rows = [
            row for month in report["months"] for row in month["deals"] if row["deal"] == deal
        ]
        self.assertEqual(len(rows), 1, f"{deal} should appear once in the forecast")
        return rows[0]

    def store(self, stage, win_probability_pct, lead_days):
        """Store one stage's dials, leaving the rest unconfigured."""
        return set_stage_forecast_rules(
            frappe.as_json(
                [
                    {
                        "stage": stage,
                        "win_probability_pct": win_probability_pct,
                        "lead_days": lead_days,
                    }
                ]
            )
        )


class TestTheShapeOfTheForecast(StageForecastTestCase):
    def test_the_report_has_exactly_the_documented_keys(self):
        assert_keys(self, weighted_pipeline_forecast(), REPORT_KEYS)

    def test_a_month_row_has_exactly_the_documented_keys(self):
        report = weighted_pipeline_forecast()

        assert_keys(self, report["months"][0], MONTH_KEYS, "month")

    def test_a_stage_row_has_exactly_the_documented_keys(self):
        report = weighted_pipeline_forecast()

        assert_keys(self, report["stages"][0], STAGE_KEYS, "stage")

    def test_a_deal_row_has_exactly_the_documented_keys(self):
        make_deal(stage="Negotiation", estimated_budget=BUDGET)

        report = weighted_pipeline_forecast()

        assert_keys(self, _first_deal(report), DEAL_KEYS, "deal")

    def test_money_crosses_the_wire_as_whole_dong(self):
        make_deal(stage="Negotiation", estimated_budget=BUDGET)

        report = weighted_pipeline_forecast()

        assert_money(self, report, "weighted_projection", "open_pipeline", "unruled_pipeline")
        assert_counts(self, report, "deal_count")
        for month in report["months"]:
            assert_money(
                self, month, "weighted_projection", "open_pipeline", where="month"
            )
            assert_counts(self, month, "deal_count", where="month")
        for stage in report["stages"]:
            assert_money(
                self, stage, "weighted_projection", "open_pipeline", where="stage"
            )
        assert_money(
            self, _first_deal(report), "deal_value", "weighted_projection", where="deal"
        )

    def test_the_day_it_was_computed_crosses_the_wire_as_an_iso_date(self):
        assert_iso_date(self, weighted_pipeline_forecast()["as_of"], "as_of")

    def test_a_month_is_a_calendar_key_the_screen_does_not_have_to_parse(self):
        report = weighted_pipeline_forecast()

        for month in report["months"]:
            year, sep, number = month["month"].partition("-")
            self.assertEqual(sep, "-")
            self.assertEqual(len(year), 4)
            self.assertTrue(1 <= int(number) <= 12)


class TestTheProjectionIsNeverNamedLikeCash(StageForecastTestCase):
    def test_no_figure_on_the_wire_is_named_the_way_money_in_the_bank_is(self):
        make_deal(stage="Negotiation", estimated_budget=BUDGET)

        offenders = forecast.cash_shaped_keys(weighted_pipeline_forecast())

        self.assertEqual(
            offenders,
            set(),
            "a projection reached the wire under a name that reads as cash",
        )

    def test_the_weighted_figure_is_named_apart_from_the_unweighted_one(self):
        make_deal(stage="Negotiation", estimated_budget=BUDGET)
        self.store("Negotiation", 70, 30)

        report = weighted_pipeline_forecast()

        self.assertIn("weighted_projection", report)
        self.assertIn("open_pipeline", report)
        self.assertNotEqual(report["weighted_projection"], report["open_pipeline"])

    def test_the_payload_says_out_loud_what_it_is(self):
        report = weighted_pipeline_forecast()

        self.assertEqual(report["basis"], forecast.PROJECTION_BASIS)
        self.assertIn("projection", report["basis"])


class TestTheDialsAreTheDealsOwnStages(StageForecastTestCase):
    def test_the_stage_vocabulary_is_the_deal_selects_and_not_a_second_list(self):
        options = frappe.get_meta("Deal").get_field("stage").options.split("\n")

        self.assertEqual(list(forecast.STAGES), options)

    def test_the_settings_table_offers_exactly_those_stages(self):
        options = frappe.get_meta("Deal Stage Forecast").get_field("stage").options.split("\n")

        self.assertEqual(list(forecast.STAGES), options)

    def test_every_stage_comes_back_whether_or_not_it_is_configured(self):
        rules = stage_forecast_rules()["stages"]

        self.assertEqual([row["stage"] for row in rules], list(forecast.STAGES))
        assert_keys(self, rules[0], RULE_KEYS, "rule")


class TestTheSingleDefaultsTrap(StageForecastTestCase):
    def test_a_table_nobody_wrote_falls_back_to_the_defaults_not_to_zero(self):
        # The whole trap: on a Single, an unwritten Int reads back as 0,
        # and a pipeline weighted at 0% renders as an empty screen that
        # looks like "no deals" rather than "not configured".
        rules = stage_forecast_rules()["stages"]

        for row in rules:
            if row["stage"] in forecast.RESOLVED:
                continue
            self.assertGreater(row["win_probability_pct"], 0, row["stage"])
            self.assertFalse(row["configured"], row["stage"])

    def test_an_unconfigured_pipeline_still_forecasts_something(self):
        make_deal(stage="Negotiation", estimated_budget=BUDGET)

        report = weighted_pipeline_forecast()

        self.assertEqual(report["weighted_projection"], 105_000_000)

    def test_the_patch_writes_a_row_for_every_stage_with_the_seeded_dials(self):
        self.seed()

        rules = stage_forecast_rules()["stages"]

        self.assertEqual(
            [row["win_probability_pct"] for row in rules], [10, 20, 30, 50, 70, 100, 0]
        )
        self.assertTrue(all(row["configured"] for row in rules))

    def test_lost_is_seeded_at_zero_and_the_row_is_what_says_so(self):
        self.seed()

        lost = self.rule_for("Lost")

        self.assertEqual(lost["win_probability_pct"], 0)
        # A stored 0 and an unwritten field are the same number. Only the
        # row can carry the difference, so the row is what is checked.
        self.assertTrue(lost["configured"])

    def test_the_patch_is_idempotent_and_never_restates_a_founders_dial(self):
        self.store("Negotiation", 35, 10)

        self.seed()
        self.seed()

        rules = stage_forecast_rules()["stages"]
        self.assertEqual([row["stage"] for row in rules], list(forecast.STAGES))
        self.assertEqual(self.rule_for("Negotiation", rules)["win_probability_pct"], 35)
        self.assertEqual(self.rule_for("Negotiation", rules)["lead_days"], 10)
        self.assertEqual(
            frappe.db.count(
                "Deal Stage Forecast", {"parenttype": "AuraOS Settings"}
            ),
            len(forecast.STAGES),
        )

    def test_a_founder_may_store_a_deliberate_zero_and_it_survives(self):
        self.store("Quote Sent", 0, 45)

        row = self.rule_for("Quote Sent")

        self.assertEqual(row["win_probability_pct"], 0)
        self.assertTrue(row["configured"])

    def test_a_stage_the_deal_select_does_not_have_is_refused(self):
        with self.assertRaises(frappe.ValidationError):
            self.store("Pitch", 15, 20)

    def test_a_probability_outside_nought_to_a_hundred_is_refused(self):
        with self.assertRaises(frappe.ValidationError):
            self.store("Negotiation", 140, 30)


class TestTheForecastIsDerivedOnEveryRead(StageForecastTestCase):
    def test_a_deal_contributes_its_value_times_its_stages_probability(self):
        self.seed()
        deal = make_deal(stage="Negotiation", estimated_budget=BUDGET)

        row = self.row_for(weighted_pipeline_forecast(), deal.name)

        self.assertEqual(row["deal_value"], BUDGET)
        self.assertEqual(row["win_probability_pct"], 70)
        self.assertEqual(row["weighted_projection"], 105_000_000)

    def test_a_deal_at_each_stage_lands_in_the_month_its_lead_time_reaches(self):
        self.seed()
        today = frappe.utils.getdate(frappe.utils.today())
        for stage in forecast.STAGES:
            if stage in forecast.RESOLVED:
                continue
            with self.subTest(stage=stage):
                deal = make_deal(stage=stage, estimated_budget=BUDGET)
                probability, lead_days = forecast.DEFAULT_RULES[stage]

                row = self.row_for(weighted_pipeline_forecast(), deal.name)

                self.assertEqual(row["weighted_projection"], BUDGET * probability // 100)
                self.assertEqual(row["month"], forecast.expected_month(today, lead_days))
                frappe.delete_doc("Deal", deal.name, force=True)

    def test_changing_a_probability_changes_the_forecast_on_the_next_read(self):
        self.seed()
        deal = make_deal(stage="Negotiation", estimated_budget=BUDGET)
        before = self.row_for(weighted_pipeline_forecast(), deal.name)

        self.store("Negotiation", 35, 30)
        after = self.row_for(weighted_pipeline_forecast(), deal.name)

        self.assertEqual(before["weighted_projection"], 105_000_000)
        self.assertEqual(after["weighted_projection"], 52_500_000)

    def test_changing_a_lead_time_moves_the_money_to_another_month(self):
        self.seed()
        deal = make_deal(stage="Negotiation", estimated_budget=BUDGET)
        before = self.row_for(weighted_pipeline_forecast(), deal.name)

        self.store("Negotiation", 70, 120)
        after = self.row_for(weighted_pipeline_forecast(), deal.name)

        self.assertNotEqual(before["month"], after["month"])

    def test_no_weighted_figure_is_stored_on_any_deal(self):
        # The claim the whole screen rests on. If a column held this
        # number, the endpoint could disagree with the deals under it.
        fields = {field.fieldname for field in frappe.get_meta("Deal").fields}

        self.assertEqual(fields & {"weighted_projection", "forecast_month"}, set())

    def test_the_headline_is_the_sum_of_the_months_and_of_the_stages(self):
        self.seed()
        make_deal(stage="Negotiation", estimated_budget=BUDGET)
        make_deal(stage="Brief Received", estimated_budget=100_000_000)

        report = weighted_pipeline_forecast()

        self.assertEqual(
            report["weighted_projection"],
            sum(row["weighted_projection"] for row in report["months"]),
        )
        self.assertEqual(
            report["weighted_projection"],
            sum(row["weighted_projection"] for row in report["stages"]),
        )

    def test_the_pipeline_it_weighs_is_the_one_in_the_database(self):
        self.seed()
        make_deal(stage="Negotiation", estimated_budget=BUDGET)
        make_deal(stage="Quote Sent", estimated_budget=100_000_000)

        report = weighted_pipeline_forecast()
        in_the_database = frappe.db.sql(
            """select sum(estimated_budget) from tabDeal
               where stage not in ('Won', 'Lost')"""
        )[0][0]

        self.assertEqual(report["open_pipeline"], int(in_the_database or 0))


class TestWhichNumberIsWeighted(StageForecastTestCase):
    def test_a_quote_the_client_holds_is_weighted_rather_than_the_budget(self):
        self.seed()
        deal = make_deal(stage="Quote Sent", estimated_budget=250_000_000)
        # The version, the token and the status are the controller's;
        # what matters here is the frozen total the client is holding.
        quote = frappe.get_doc(
            {
                "doctype": "Deal Quote",
                "deal": deal.name,
                "title": deal.title,
                "total": 116_721_000,
            }
        ).insert(ignore_permissions=True)
        self.assertEqual(
            frappe.db.get_value("Deal", deal.name, "latest_quote"), quote.name
        )

        row = self.row_for(weighted_pipeline_forecast(), deal.name)

        self.assertEqual(row["deal_value"], 116_721_000)
        self.assertEqual(row["value_basis"], forecast.QUOTED)
        self.assertEqual(row["weighted_projection"], 58_360_500)

    def test_a_deal_nobody_has_priced_is_weighted_on_the_clients_budget(self):
        self.seed()
        deal = make_deal(stage="Quote Sent", estimated_budget=250_000_000)

        row = self.row_for(weighted_pipeline_forecast(), deal.name)

        self.assertEqual(row["deal_value"], 250_000_000)
        self.assertEqual(row["value_basis"], forecast.ESTIMATED)


class TestNothingIsAnAnswer(StageForecastTestCase):
    def test_a_studio_with_no_open_deals_reads_as_zero_rather_than_an_error(self):
        report = weighted_pipeline_forecast(months=6)

        self.assertEqual(report["weighted_projection"], 0)
        self.assertEqual(report["open_pipeline"], 0)
        self.assertEqual(report["deal_count"], 0)
        self.assertEqual(len(report["months"]), 6)
        self.assertTrue(all(row["weighted_projection"] == 0 for row in report["months"]))

    def test_a_stage_with_no_open_deals_is_a_row_of_zeros_not_a_gap(self):
        self.seed()
        make_deal(stage="Negotiation", estimated_budget=BUDGET)

        quiet = self.stage_of(weighted_pipeline_forecast(), "Brief Received")

        self.assertEqual(quiet["deal_count"], 0)
        self.assertEqual(quiet["weighted_projection"], 0)
        self.assertIsNone(quiet["month"])

    def test_a_won_deal_is_not_counted_twice_against_its_jobs_receivables(self):
        self.seed()
        make_deal(stage="Won", estimated_budget=BUDGET)

        report = weighted_pipeline_forecast()

        self.assertEqual(report["weighted_projection"], 0)
        self.assertFalse(self.stage_of(report, "Won")["contributes"])


class TestTheForecastIsTheFoundersView(StageForecastTestCase):
    def test_a_producer_is_refused_the_forecast_by_the_server(self):
        frappe.set_user(PRODUCER)

        with self.assertRaises(frappe.PermissionError):
            weighted_pipeline_forecast()

    def test_a_producer_is_refused_the_dials(self):
        frappe.set_user(PRODUCER)

        with self.assertRaises(frappe.PermissionError):
            stage_forecast_rules()

    def test_a_producer_cannot_move_a_probability(self):
        frappe.set_user(PRODUCER)

        with self.assertRaises(frappe.PermissionError):
            self.store("Negotiation", 100, 0)

    def test_the_founder_may_read_and_set(self):
        frappe.set_user(FOUNDER)

        self.assertIn("stages", stage_forecast_rules())
        self.assertIn("weighted_projection", weighted_pipeline_forecast())


def _first_deal(report):
    for month in report["months"]:
        if month["deals"]:
            return month["deals"][0]
    raise AssertionError("the forecast carried no deal rows")

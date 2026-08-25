"""Pure-python tests for auraos.lib.forecast - no Frappe required.

This projection is an estimate multiplied by a guess, sitting on a
dashboard next to a cash balance that is a fact, so the rules underneath
it are worth pinning apart from any doctype:

- **The payload cannot call a projection by a cash name.** Checked as a
  whole-payload sweep rather than by spot-checking one key, so a figure
  added next year under `total` fails here before it reaches a screen.
- **A deal is worth the best number written down for it.** The quote the
  client holds beats the deal's own pricing beats the client's budget,
  and the row says which one answered.
- **An absent stage rule falls back to the house default, never to 0.**
  Lost is legitimately 0, so a stored 0 and an unwritten field cannot be
  told apart by value - only by whether the rule exists.
- **Changing a probability changes the forecast**, because nothing is
  stored and nothing is cached. Proved here on the arithmetic and again
  at the seam against a real settings row.
- **Nothing is an answer.** No deals at a stage, and no deals at all,
  read as zero across the horizon rather than as an error or a gap.
- **The three arrangements agree.** The headline is the sum of the
  months is the sum of the stages is the sum of the deal rows.

The Frappe-side surface is a thin adapter over these functions and gates
them to the founder; that boundary is tested at the seam, in
auraos/auraos/doctype/auraos_settings/test_stage_forecast.py.
"""

from datetime import date

import pytest

from auraos.lib.forecast import (
    BREAKDOWN,
    BRIEF_RECEIVED,
    CASH_WORDS,
    DEFAULT_RULES,
    ESTIMATED,
    LOST,
    NEGOTIATION,
    PRICED,
    PROJECTION_BASIS,
    QUOTE_SENT,
    QUOTED,
    RESOLVED,
    STAGES,
    UNVALUED,
    WON,
    StageRule,
    cash_shaped_keys,
    contribution,
    deal_value,
    default_rule,
    expected_month,
    guarded,
    horizon,
    is_open,
    projection,
    rule_for,
    stage_rules,
    weighted,
)

TODAY = date(2026, 8, 19)


def deal(stage=QUOTE_SENT, name="DEAL-0001", **fields):
    return {"name": name, "title": "Tết TVC", "stage": stage, **fields}


def month_of(report, key):
    return next(row for row in report["months"] if row["month"] == key)


def stage_of(report, stage):
    return next(row for row in report["stages"] if row["stage"] == stage)


# -- the payload may not call a projection by a cash name --


def test_no_figure_in_the_report_is_named_the_way_money_in_the_bank_is():
    report = projection(
        [deal(estimated_budget=100_000_000), deal(BREAKDOWN, "DEAL-0002", quote_total=50_000_000)],
        today=TODAY,
    )

    assert cash_shaped_keys(report) == set()


def test_the_guard_walks_every_row_not_only_the_top_level():
    report = projection([deal(estimated_budget=100_000_000)], today=TODAY)
    month_of(report, "2026-10")["deals"][0]["total"] = 1

    assert cash_shaped_keys(report) == {"total"}


def test_the_guard_catches_a_cash_word_on_the_end_of_a_longer_name():
    assert cash_shaped_keys({"weighted_total": 1}) == {"weighted_total"}
    assert cash_shaped_keys({"projected_income": 1}) == {"projected_income"}


def test_a_report_that_named_a_figure_like_cash_is_refused_not_merely_flagged():
    # The half that survives a refactor: this is not a test asserting a
    # convention, it is the module refusing to hand out the payload.
    with pytest.raises(ValueError) as refusal:
        guarded({"weighted_projection": 1, "total": 2})

    assert "total" in str(refusal.value)


def test_a_report_named_honestly_passes_through_untouched():
    report = {"weighted_projection": 1, "open_pipeline": 2}

    assert guarded(report) is report


def test_the_names_this_projection_travels_under_are_not_cash_words():
    assert "weighted_projection" not in CASH_WORDS
    assert cash_shaped_keys({"weighted_projection": 1, "open_pipeline": 2}) == set()


def test_the_report_says_what_it_is_measured_on():
    report = projection([], today=TODAY)

    assert report["basis"] == PROJECTION_BASIS
    assert "projection" in report["basis"]
    assert report["as_of"] == "2026-08-19"


# -- the dials --


def test_every_stage_of_the_deal_select_has_a_house_default():
    assert sorted(DEFAULT_RULES) == sorted(STAGES)


def test_the_seeded_probabilities_are_the_ones_the_ticket_names():
    assert [DEFAULT_RULES[stage][0] for stage in STAGES] == [10, 20, 30, 50, 70, 100, 0]


def test_every_stage_has_a_lead_time_and_the_open_ones_are_in_the_future():
    for stage in STAGES:
        lead = DEFAULT_RULES[stage][1]
        assert lead >= 0
        if stage not in RESOLVED:
            assert lead > 0, f"{stage} would bill this month whatever happens"


def test_an_unconfigured_stage_falls_back_to_its_default_and_says_so():
    (rule,) = [row for row in stage_rules([]) if row.stage == NEGOTIATION]

    assert rule.win_probability_pct == 70
    assert rule.lead_days == 30
    assert rule.configured is False


def test_a_stored_row_wins_over_the_default():
    (rule,) = [
        row
        for row in stage_rules([{"stage": NEGOTIATION, "win_probability_pct": 40, "lead_days": 10}])
        if row.stage == NEGOTIATION
    ]

    assert (rule.win_probability_pct, rule.lead_days) == (40, 10)
    assert rule.configured is True


def test_a_stored_zero_is_kept_because_lost_is_legitimately_zero():
    (rule,) = [
        row
        for row in stage_rules([{"stage": LOST, "win_probability_pct": 0, "lead_days": 0}])
        if row.stage == LOST
    ]

    assert rule.win_probability_pct == 0
    # The whole trap: this 0 and the default 0 are the same number, and
    # only `configured` can tell the founder's decision from silence.
    assert rule.configured is True
    assert default_rule(LOST).configured is False


def test_a_stage_nobody_configured_never_reads_as_zero_percent():
    for rule in stage_rules([]):
        if rule.stage in RESOLVED:
            continue
        assert rule.win_probability_pct > 0, f"{rule.stage} would weight a real pipeline to nothing"


def test_every_stage_comes_back_in_pipeline_order_whatever_was_stored():
    rules = stage_rules([{"stage": LOST, "win_probability_pct": 0, "lead_days": 0}])

    assert [rule.stage for rule in rules] == list(STAGES)


def test_a_stored_rule_for_a_stage_the_select_dropped_is_kept_not_silently_lost():
    rules = stage_rules([{"stage": "Pitch", "win_probability_pct": 15, "lead_days": 20}])

    assert [rule.stage for rule in rules][-1] == "Pitch"
    assert rule_for(rules, "Pitch").configured is True


def test_a_stage_no_rule_reaches_answers_none_rather_than_zero():
    assert rule_for(stage_rules([]), "Pitch") is None


# -- what a deal is worth --


def test_a_quote_the_client_holds_beats_the_deals_own_pricing_and_its_budget():
    value, basis = deal_value(
        {"quoted_total": 116_721_000, "quote_total": 90_000_000, "estimated_budget": 250_000_000}
    )

    assert (value, basis) == (116_721_000, QUOTED)


def test_the_deals_own_pricing_beats_the_clients_budget():
    value, basis = deal_value({"quote_total": 6_177_600, "estimated_budget": 200_000_000})

    assert (value, basis) == (6_177_600, PRICED)


def test_a_deal_nobody_has_priced_is_worth_what_the_client_said():
    assert deal_value({"estimated_budget": 100_000_000}) == (100_000_000, ESTIMATED)


def test_a_zero_at_a_rung_is_silence_and_falls_through():
    # A Currency column is never null, so 0 means "nothing recorded".
    assert deal_value({"quoted_total": 0, "quote_total": 0, "estimated_budget": 150_000_000}) == (
        150_000_000,
        ESTIMATED,
    )


def test_a_deal_with_no_number_anywhere_is_worth_nothing_and_says_which():
    assert deal_value({}) == (0, UNVALUED)


# -- the weighting itself --


def test_a_deal_contributes_its_value_times_the_stages_probability():
    assert weighted(100_000_000, 10) == 10_000_000
    assert weighted(150_000_000, 70) == 105_000_000
    assert weighted(116_721_000, 50) == 58_360_500


def test_a_hundred_percent_is_the_value_and_zero_percent_is_nothing():
    assert weighted(250_000_000, 100) == 250_000_000
    assert weighted(250_000_000, 0) == 0


def test_the_contribution_is_rounded_to_whole_dong_half_away_from_zero():
    assert weighted(333, 50) == 167


# -- which month it lands in --


def test_the_month_is_todays_month_plus_the_stages_lead_time():
    assert expected_month(TODAY, 0) == "2026-08"
    assert expected_month(TODAY, 30) == "2026-09"
    assert expected_month(TODAY, 90) == "2026-11"


def test_a_lead_time_that_crosses_a_year_end_lands_in_the_new_year():
    assert expected_month(date(2026, 12, 20), 30) == "2027-01"


def test_a_negative_lead_time_lands_now_rather_than_in_the_past():
    assert expected_month(TODAY, -60) == "2026-08"


def test_the_horizon_starts_this_month_and_is_contiguous():
    assert horizon(TODAY, 4) == ["2026-08", "2026-09", "2026-10", "2026-11"]


def test_the_horizon_rolls_over_the_year():
    assert horizon(date(2026, 11, 1), 3) == ["2026-11", "2026-12", "2027-01"]


def test_a_horizon_of_nothing_is_still_one_month():
    assert horizon(TODAY, 0) == ["2026-08"]


# -- won and lost are not pipeline --


def test_won_and_lost_deals_are_not_pipeline():
    assert is_open(deal(BRIEF_RECEIVED)) is True
    assert is_open(deal(WON)) is False
    assert is_open(deal(LOST)) is False


def test_a_won_deal_is_not_counted_because_its_job_is_already_receivable():
    report = projection(
        [deal(WON, estimated_budget=180_000_000), deal(LOST, "DEAL-0002", estimated_budget=9_000)],
        today=TODAY,
    )

    assert report["weighted_projection"] == 0
    assert report["deal_count"] == 0


def test_the_resolved_stages_still_appear_on_the_settings_table():
    report = projection([], today=TODAY)

    assert stage_of(report, WON)["win_probability_pct"] == 100
    assert stage_of(report, WON)["contributes"] is False
    assert stage_of(report, LOST)["contributes"] is False


# -- the projection --


def test_each_open_deal_contributes_value_times_probability_in_its_month():
    report = projection(
        [
            deal(BRIEF_RECEIVED, "DEAL-0045", estimated_budget=100_000_000),
            deal(NEGOTIATION, "DEAL-0005", estimated_budget=150_000_000),
        ],
        today=TODAY,
    )

    # Brief Received: 10% of 100tr, 90 days out.
    assert month_of(report, "2026-11")["weighted_projection"] == 10_000_000
    # Negotiation: 70% of 150tr, 30 days out.
    assert month_of(report, "2026-09")["weighted_projection"] == 105_000_000
    assert report["weighted_projection"] == 115_000_000


def test_the_unweighted_pipeline_travels_beside_the_weighted_projection():
    report = projection([deal(NEGOTIATION, estimated_budget=150_000_000)], today=TODAY)

    assert report["open_pipeline"] == 150_000_000
    assert report["weighted_projection"] == 105_000_000
    assert report["open_pipeline"] != report["weighted_projection"]


def test_the_headline_is_the_sum_of_the_months_and_of_the_stages_and_of_the_rows():
    report = projection(
        [
            deal(BRIEF_RECEIVED, "DEAL-0045", estimated_budget=100_000_000),
            deal(NEGOTIATION, "DEAL-0005", estimated_budget=150_000_000),
            deal(QUOTE_SENT, "DEAL-0006", quoted_total=116_721_000),
            deal(BREAKDOWN, "DEAL-0016", quote_total=6_177_600, estimated_budget=200_000_000),
        ],
        today=TODAY,
    )

    by_month = sum(row["weighted_projection"] for row in report["months"])
    by_stage = sum(row["weighted_projection"] for row in report["stages"])
    by_deal = sum(
        row["weighted_projection"] for month in report["months"] for row in month["deals"]
    )

    assert report["weighted_projection"] == by_month == by_stage == by_deal


def test_a_deal_row_carries_which_number_was_weighted():
    report = projection(
        [deal(BREAKDOWN, quote_total=6_177_600, estimated_budget=200_000_000)], today=TODAY
    )
    (row,) = month_of(report, "2026-10")["deals"]

    assert row["deal_value"] == 6_177_600
    assert row["value_basis"] == PRICED
    assert row["weighted_projection"] == 1_853_280


def test_changing_a_probability_changes_the_forecast():
    deals = [deal(NEGOTIATION, estimated_budget=150_000_000)]

    before = projection(deals, stage_rules([]), today=TODAY)
    after = projection(
        deals,
        stage_rules([{"stage": NEGOTIATION, "win_probability_pct": 35, "lead_days": 30}]),
        today=TODAY,
    )

    assert before["weighted_projection"] == 105_000_000
    assert after["weighted_projection"] == 52_500_000


def test_changing_a_lead_time_moves_the_money_to_another_month():
    deals = [deal(NEGOTIATION, estimated_budget=150_000_000)]

    moved = projection(
        deals,
        stage_rules([{"stage": NEGOTIATION, "win_probability_pct": 70, "lead_days": 90}]),
        today=TODAY,
    )

    assert month_of(moved, "2026-09")["weighted_projection"] == 0
    assert month_of(moved, "2026-11")["weighted_projection"] == 105_000_000


# -- nothing is an answer --


def test_a_stage_with_no_open_deals_reads_as_zero_rather_than_being_absent():
    report = projection([deal(NEGOTIATION, estimated_budget=150_000_000)], today=TODAY)
    quiet = stage_of(report, BRIEF_RECEIVED)

    assert quiet["deal_count"] == 0
    assert quiet["open_pipeline"] == 0
    assert quiet["weighted_projection"] == 0
    assert quiet["month"] is None


def test_a_studio_with_no_open_deals_at_all_reads_as_zero_across_the_horizon():
    report = projection([], today=TODAY, months=6)

    assert report["weighted_projection"] == 0
    assert report["open_pipeline"] == 0
    assert report["deal_count"] == 0
    assert len(report["months"]) == 6
    assert all(row["weighted_projection"] == 0 for row in report["months"])
    assert [row["stage"] for row in report["stages"]] == list(STAGES)


def test_a_month_with_nothing_in_it_is_still_a_month():
    report = projection([deal(NEGOTIATION, estimated_budget=150_000_000)], today=TODAY, months=3)

    assert [row["month"] for row in report["months"]] == ["2026-08", "2026-09", "2026-10"]
    assert month_of(report, "2026-10")["deal_count"] == 0


def test_money_landing_past_the_horizon_is_still_on_the_report():
    # A 90 day lead reaches November; the caller only asked for two
    # months. Dropping it would make the headline disagree with the rows.
    report = projection(
        [deal(BRIEF_RECEIVED, estimated_budget=100_000_000)], today=TODAY, months=2
    )

    assert month_of(report, "2026-11")["weighted_projection"] == 10_000_000
    assert sum(row["weighted_projection"] for row in report["months"]) == 10_000_000


def test_a_deal_nothing_governs_is_carried_out_rather_than_weighted_to_nothing():
    report = projection(
        [{"name": "DEAL-0099", "stage": "Pitch", "estimated_budget": 80_000_000}], today=TODAY
    )

    assert report["deal_count"] == 0
    assert report["weighted_projection"] == 0
    assert report["unruled_pipeline"] == 80_000_000
    assert report["unruled"][0]["stage"] == "Pitch"


def test_one_contribution_carries_everything_needed_to_check_it_by_hand():
    row = contribution(
        deal(QUOTE_SENT, quoted_total=116_721_000),
        StageRule(QUOTE_SENT, 50, 45, configured=True),
        TODAY,
    )

    assert row["deal_value"] == 116_721_000
    assert row["win_probability_pct"] == 50
    assert row["lead_days"] == 45
    assert row["weighted_projection"] == 58_360_500
    assert row["month"] == "2026-10"

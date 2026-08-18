"""Pure-python tests for auraos.lib.finance - no Frappe required.

The finance screens ask three questions of data the app already stores,
and each one has a rule underneath it worth pinning independently of the
framework:

- **Money in is cash.** A milestone counts in the month the payment was
  recorded, not the month it fell due or was invoiced. Get this wrong and
  the studio reads an accrual number as its bank balance.
- **Money out keeps its whole shape.** Every expense lands in a month and
  a category - including the ones naming no category, which go to the one
  Uncategorised bucket rather than quietly out of the total - and carries
  whose money paid it.
- **Money owed ages from the terms, not from the due date.** The buckets
  are built on auraos.lib.milestones, so the ageing ladder and the nudge
  on the jobs board cannot disagree about who is late.

Empty ranges and empty months are answers, not errors: a chart missing
January reads as a shorter year rather than an empty month.

The Frappe-side surface (auraos.api.finance_income / finance_expenses /
finance_receivables) is a thin adapter over these functions.
"""

from datetime import datetime, timedelta

from auraos.lib.finance import (
    AGEING_BUCKETS,
    DAYS_1_30,
    DAYS_31_60,
    DAYS_61_90,
    DAYS_90_PLUS,
    NOT_DUE,
    ageing_bucket,
    expense_report,
    income_report,
    month_keys,
    receivables_report,
)
from auraos.lib.milestones import INVOICED, NOT_REQUESTED, PAID, REQUESTED
from auraos.lib.settlement import FROM_ADVANCE, FROM_COMPANY, UNCATEGORISED

NOW = datetime(2026, 8, 10, 9, 30)
TERMS = 7

NHAT_MINH = "COM-0001"
VIET_TIEN = "COM-0002"


def payment(paid_on, amount, company=NHAT_MINH, company_name="Nhất Minh"):
    return {
        "name": "row-1",
        "paid_on": paid_on,
        "amount": amount,
        "company": company,
        "company_name": company_name,
    }


def spend(spent_on, amount, category=None, paid_from=FROM_ADVANCE):
    return {
        "name": "EXP-00001",
        "spent_on": spent_on,
        "amount": amount,
        "category": category,
        "paid_from": paid_from,
    }


def owed(due_on, amount=10_000_000, status=INVOICED, title="Đặt cọc 40%"):
    return {
        "name": "ms-1",
        "title": title,
        "amount": amount,
        "status": status,
        "due_on": due_on,
        "job": "JOB-0114",
        "job_title": "TVC Tết 2027",
        "company": NHAT_MINH,
        "company_name": "Nhất Minh",
    }


def days_ago(days):
    return NOW - timedelta(days=days)


# -- the months a range touches --


def test_a_range_inside_one_month_is_one_month():
    assert month_keys("2026-08-01", "2026-08-31") == ["2026-08"]


def test_a_range_names_every_month_it_touches_including_empty_ones():
    assert month_keys("2026-06-28", "2026-09-02") == [
        "2026-06",
        "2026-07",
        "2026-08",
        "2026-09",
    ]


def test_a_range_crossing_a_year_end_keeps_counting():
    assert month_keys("2026-11-15", "2027-02-01") == [
        "2026-11",
        "2026-12",
        "2027-01",
        "2027-02",
    ]


def test_a_range_that_ends_before_it_starts_touches_no_months():
    assert month_keys("2026-08-31", "2026-08-01") == []


def test_a_range_missing_a_bound_touches_no_months():
    assert month_keys(None, "2026-08-01") == []
    assert month_keys("2026-08-01", None) == []


# -- money in: cash, by month, by client --


def test_an_empty_range_reports_zero_rather_than_raising():
    report = income_report([], "2026-08-31", "2026-08-01")
    assert report["months"] == []
    assert report["total"] == 0
    assert report["count"] == 0


def test_a_range_with_no_payments_still_prints_its_months():
    report = income_report([], "2026-07-01", "2026-08-31")
    assert [month["month"] for month in report["months"]] == ["2026-07", "2026-08"]
    assert [month["total"] for month in report["months"]] == [0, 0]
    assert [month["clients"] for month in report["months"]] == [[], []]
    assert report["total"] == 0


def test_income_is_bucketed_by_the_month_the_payment_was_recorded():
    report = income_report(
        [payment("2026-07-15", 40_000_000), payment("2026-08-03", 25_000_000)],
        "2026-07-01",
        "2026-08-31",
    )
    assert [(m["month"], m["total"]) for m in report["months"]] == [
        ("2026-07", 40_000_000),
        ("2026-08", 25_000_000),
    ]
    assert report["total"] == 65_000_000
    assert report["count"] == 2


def test_the_last_day_of_a_month_belongs_to_that_month_and_the_first_to_the_next():
    report = income_report(
        [payment("2026-07-31", 10_000_000), payment("2026-08-01", 20_000_000)],
        "2026-07-01",
        "2026-08-31",
    )
    assert [(m["month"], m["total"]) for m in report["months"]] == [
        ("2026-07", 10_000_000),
        ("2026-08", 20_000_000),
    ]


def test_a_payment_on_either_edge_of_the_range_is_inside_it():
    report = income_report(
        [payment("2026-08-01", 1_000_000), payment("2026-08-31", 2_000_000)],
        "2026-08-01",
        "2026-08-31",
    )
    assert report["total"] == 3_000_000


def test_a_payment_outside_the_range_is_not_counted():
    report = income_report(
        [payment("2026-07-31", 9_000_000), payment("2026-09-01", 9_000_000)],
        "2026-08-01",
        "2026-08-31",
    )
    assert report["total"] == 0
    assert report["count"] == 0


def test_a_payment_stamped_with_a_datetime_lands_in_its_month():
    report = income_report(
        [payment(datetime(2026, 8, 31, 23, 45), 5_000_000)], "2026-08-01", "2026-08-31"
    )
    assert report["months"][0]["total"] == 5_000_000


def test_a_month_breaks_down_per_client_biggest_first():
    report = income_report(
        [
            payment("2026-08-02", 20_000_000, VIET_TIEN, "Việt Tiến"),
            payment("2026-08-05", 50_000_000),
            payment("2026-08-09", 30_000_000),
        ],
        "2026-08-01",
        "2026-08-31",
    )
    clients = report["months"][0]["clients"]
    assert [(c["company"], c["total"], c["count"]) for c in clients] == [
        (NHAT_MINH, 80_000_000, 2),
        (VIET_TIEN, 20_000_000, 1),
    ]
    assert clients[0]["company_name"] == "Nhất Minh"
    assert report["months"][0]["total"] == 100_000_000


def test_income_declares_the_basis_and_the_range_it_answered_for():
    report = income_report([], "2026-01-01", "2026-08-31")
    assert report["basis"] == "cash"
    assert report["date_from"] == "2026-01-01"
    assert report["date_to"] == "2026-08-31"


def test_income_is_whole_dong_never_a_float():
    report = income_report([payment("2026-08-02", 33_333_333.5)], "2026-08-01", "2026-08-31")
    total = report["months"][0]["total"]
    assert isinstance(total, int) and total == 33_333_334


def test_income_carries_no_founder_number():
    report = income_report([payment("2026-08-02", 10_000_000)], "2026-08-01", "2026-08-31")
    forbidden = {
        "commission",
        "commission_pct",
        "total_commission",
        "cm",
        "profit_before_tax",
        "tndn",
        "net_profit",
        "vat_payable",
    }
    assert not forbidden & set(report)
    assert not forbidden & set(report["months"][0])
    assert not forbidden & set(report["months"][0]["clients"][0])


# -- money out: by month, by category, by whose money --


def test_an_empty_expense_range_reports_zero_rather_than_raising():
    report = expense_report([], "2026-08-31", "2026-08-01")
    assert report["months"] == []
    assert report["categories"] == []
    assert report["total"] == 0
    assert report["paid_from"] == {FROM_ADVANCE: 0, FROM_COMPANY: 0}


def test_a_month_with_no_spend_still_prints_with_both_sources_zeroed():
    report = expense_report([], "2026-08-01", "2026-08-31")
    month = report["months"][0]
    assert month["total"] == 0
    assert month["categories"] == []
    assert month["paid_from"] == {FROM_ADVANCE: 0, FROM_COMPANY: 0}


def test_spend_is_bucketed_by_the_month_it_was_spent():
    report = expense_report(
        [spend("2026-07-31", 3_000_000, "Crew"), spend("2026-08-01", 4_000_000, "Crew")],
        "2026-07-01",
        "2026-08-31",
    )
    assert [(m["month"], m["total"]) for m in report["months"]] == [
        ("2026-07", 3_000_000),
        ("2026-08", 4_000_000),
    ]
    assert report["total"] == 7_000_000
    assert report["count"] == 2


def test_categories_roll_up_across_the_whole_range_biggest_first():
    report = expense_report(
        [
            spend("2026-07-04", 5_000_000, "Crew"),
            spend("2026-08-04", 6_000_000, "Crew"),
            spend("2026-08-06", 20_000_000, "Equipment"),
        ],
        "2026-07-01",
        "2026-08-31",
    )
    assert report["categories"] == [
        {"category": "Equipment", "total": 20_000_000},
        {"category": "Crew", "total": 11_000_000},
    ]


def test_an_expense_naming_no_category_lands_in_uncategorised():
    report = expense_report(
        [spend("2026-08-04", 1_200_000), spend("2026-08-05", 800_000, "")],
        "2026-08-01",
        "2026-08-31",
    )
    assert report["categories"] == [{"category": UNCATEGORISED, "total": 2_000_000}]
    assert report["months"][0]["total"] == 2_000_000


def test_uncategorised_prints_last_however_big_it_is():
    report = expense_report(
        [spend("2026-08-04", 90_000_000), spend("2026-08-05", 1_000_000, "Crew")],
        "2026-08-01",
        "2026-08-31",
    )
    assert [row["category"] for row in report["categories"]] == ["Crew", UNCATEGORISED]


def test_spend_is_split_by_whose_money_paid_it():
    report = expense_report(
        [
            spend("2026-08-04", 2_000_000, "Crew", FROM_ADVANCE),
            spend("2026-08-05", 7_000_000, "Equipment", FROM_COMPANY),
        ],
        "2026-08-01",
        "2026-08-31",
    )
    assert report["paid_from"] == {FROM_ADVANCE: 2_000_000, FROM_COMPANY: 7_000_000}
    assert report["months"][0]["paid_from"] == report["paid_from"]


def test_an_expense_that_does_not_say_where_the_money_came_from_reads_as_a_float():
    report = expense_report([spend("2026-08-04", 500_000, "Crew", None)], "2026-08-01", "2026-08-31")
    assert report["paid_from"] == {FROM_ADVANCE: 500_000, FROM_COMPANY: 0}


def test_spend_outside_the_range_is_not_counted():
    report = expense_report(
        [spend("2026-09-01", 9_000_000, "Crew")], "2026-08-01", "2026-08-31"
    )
    assert report["total"] == 0
    assert report["categories"] == []


def test_spend_is_whole_dong_never_a_float():
    report = expense_report([spend("2026-08-04", 1_500_000.4, "Crew")], "2026-08-01", "2026-08-31")
    total = report["categories"][0]["total"]
    assert isinstance(total, int) and total == 1_500_000


# -- money owed: the ageing ladder --


def test_the_ladder_has_five_rungs_in_reading_order():
    assert AGEING_BUCKETS == (NOT_DUE, DAYS_1_30, DAYS_31_60, DAYS_61_90, DAYS_90_PLUS)


def test_anything_not_past_the_terms_is_not_yet_due():
    assert ageing_bucket(0, overdue=False) == NOT_DUE


def test_the_bucket_edges_are_inclusive_at_the_top():
    assert ageing_bucket(1, overdue=True) == DAYS_1_30
    assert ageing_bucket(30, overdue=True) == DAYS_1_30
    assert ageing_bucket(31, overdue=True) == DAYS_31_60
    assert ageing_bucket(60, overdue=True) == DAYS_31_60
    assert ageing_bucket(61, overdue=True) == DAYS_61_90
    assert ageing_bucket(90, overdue=True) == DAYS_61_90
    assert ageing_bucket(91, overdue=True) == DAYS_90_PLUS


def bucket(report, key):
    return next(rung for rung in report["buckets"] if rung["bucket"] == key)


def test_nothing_owed_reports_every_bucket_zeroed_rather_than_raising():
    report = receivables_report([], now=NOW, terms_days=TERMS)
    assert [rung["bucket"] for rung in report["buckets"]] == list(AGEING_BUCKETS)
    assert all(rung["total"] == 0 and rung["rows"] == [] for rung in report["buckets"])
    assert report["total"] == 0
    assert report["count"] == 0
    assert report["overdue_total"] == 0
    assert report["as_of"] == "2026-08-10"
    assert report["payment_terms_days"] == TERMS


def test_a_milestone_on_its_due_date_is_not_yet_due():
    report = receivables_report([owed(NOW)], now=NOW, terms_days=TERMS)
    row = bucket(report, NOT_DUE)["rows"][0]
    assert row["overdue"] is False
    assert row["days_overdue"] == 0


def test_a_milestone_one_day_past_its_due_date_is_still_inside_the_terms():
    report = receivables_report([owed(days_ago(1))], now=NOW, terms_days=TERMS)
    assert bucket(report, NOT_DUE)["count"] == 1
    assert bucket(report, DAYS_1_30)["count"] == 0


def test_the_last_day_of_the_terms_is_not_late_and_the_next_day_is():
    on_terms = receivables_report([owed(days_ago(TERMS))], now=NOW, terms_days=TERMS)
    assert bucket(on_terms, NOT_DUE)["count"] == 1

    past_terms = receivables_report([owed(days_ago(TERMS + 1))], now=NOW, terms_days=TERMS)
    row = bucket(past_terms, DAYS_1_30)["rows"][0]
    assert row["overdue"] is True
    assert row["days_overdue"] == 1


def test_a_receivable_ages_into_the_bucket_its_lateness_names():
    rows = [
        owed(days_ago(TERMS + 30), amount=1_000_000),
        owed(days_ago(TERMS + 31), amount=2_000_000),
        owed(days_ago(TERMS + 60), amount=3_000_000),
        owed(days_ago(TERMS + 61), amount=4_000_000),
        owed(days_ago(TERMS + 90), amount=5_000_000),
        owed(days_ago(TERMS + 91), amount=6_000_000),
    ]
    report = receivables_report(rows, now=NOW, terms_days=TERMS)
    assert bucket(report, DAYS_1_30)["total"] == 1_000_000
    assert bucket(report, DAYS_31_60)["total"] == 2_000_000 + 3_000_000
    assert bucket(report, DAYS_61_90)["total"] == 4_000_000 + 5_000_000
    assert bucket(report, DAYS_90_PLUS)["total"] == 6_000_000
    assert report["total"] == 21_000_000
    assert report["count"] == 6
    assert report["overdue_total"] == 21_000_000
    assert report["overdue_count"] == 6


def test_a_milestone_nobody_has_invoiced_yet_is_owed_just_the_same():
    report = receivables_report(
        [owed(days_ago(TERMS + 5), status=NOT_REQUESTED)], now=NOW, terms_days=TERMS
    )
    assert bucket(report, DAYS_1_30)["count"] == 1


def test_a_milestone_whose_job_has_not_reached_its_stage_is_not_yet_due():
    report = receivables_report(
        [owed(None, status=NOT_REQUESTED, amount=7_000_000)], now=NOW, terms_days=TERMS
    )
    row = bucket(report, NOT_DUE)["rows"][0]
    assert row["due_on"] is None
    assert row["days_overdue"] == 0
    assert report["total"] == 7_000_000


def test_a_paid_milestone_is_not_a_receivable():
    report = receivables_report([owed(days_ago(90), status=PAID)], now=NOW, terms_days=TERMS)
    assert report["total"] == 0
    assert report["count"] == 0


def test_terms_of_zero_turn_the_nudge_off_and_with_it_every_overdue_bucket():
    report = receivables_report([owed(days_ago(200))], now=NOW, terms_days=0)
    row = bucket(report, NOT_DUE)["rows"][0]
    assert row["overdue"] is False
    assert row["days_overdue"] == 0
    assert report["overdue_total"] == 0


def test_a_receivable_row_says_what_it_is_without_writing_the_sentence():
    report = receivables_report(
        [owed(days_ago(TERMS + 12), amount=86_500_000, status=REQUESTED)],
        now=NOW,
        terms_days=TERMS,
    )
    row = bucket(report, DAYS_1_30)["rows"][0]
    assert row == {
        "milestone": "ms-1",
        "title": "Đặt cọc 40%",
        "job": "JOB-0114",
        "job_title": "TVC Tết 2027",
        "company": NHAT_MINH,
        "company_name": "Nhất Minh",
        "amount": 86_500_000,
        "status": REQUESTED,
        "due_on": days_ago(TERMS + 12).isoformat(),
        "overdue": True,
        "days_overdue": 12,
    }


def test_a_bucket_lists_its_oldest_debt_first():
    report = receivables_report(
        [
            owed(days_ago(TERMS + 3), amount=1_000_000),
            owed(days_ago(TERMS + 20), amount=2_000_000),
            owed(days_ago(TERMS + 9), amount=3_000_000),
        ],
        now=NOW,
        terms_days=TERMS,
    )
    assert [row["days_overdue"] for row in bucket(report, DAYS_1_30)["rows"]] == [20, 9, 3]


def test_a_stored_stamp_read_back_as_text_ages_the_same_as_a_datetime():
    report = receivables_report(
        [owed("2026-07-01 09:30:00")], now=NOW, terms_days=TERMS
    )
    assert bucket(report, DAYS_31_60)["rows"][0]["days_overdue"] == 33


def test_receivables_carry_no_founder_number():
    report = receivables_report([owed(days_ago(30))], now=NOW, terms_days=TERMS)
    forbidden = {
        "commission",
        "commission_pct",
        "total_commission",
        "cm",
        "profit_before_tax",
        "tndn",
        "net_profit",
        "vat_payable",
    }
    assert not forbidden & set(report)
    assert not forbidden & set(bucket(report, DAYS_1_30)["rows"][0])

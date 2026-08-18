"""Pure-python tests for auraos.lib.reporting - no Frappe required.

Two cross-record views the new UI asks for, both derived from records
the app already keeps:

- **Every quote, across every deal.** Today a quote is only reachable
  inside its own deal, so nobody can answer "what is out with clients
  right now". The row that answers it must carry the tracking as
  *fields* - counts and a timestamp - because a list that ships
  "v2 published · not opened" as one string can never be sorted,
  filtered or translated.
- **What a job actually earned.** Quoted against actual, which
  auraos.lib.settlement already compares per category, totalled and set
  beside the money collected. Margin only: commission, CM, profit before
  tax, TNDN, net profit and VAT payable are the founder's boundary, and
  a payload that cannot hold them cannot leak them.

The Frappe-side tests (auraos/auraos/doctype/deal_quote/test_quotation_list.py
and auraos/auraos/doctype/job/test_job_profitability.py) prove the
endpoints go through these functions, scope their reads and refuse an
outsider.
"""

from datetime import datetime

from auraos.lib.reporting import (
    LAST_OPEN,
    PAGE,
    PDF,
    collected,
    margin_pct,
    matches_search,
    open_tracking,
    profit_view,
    quotation_row,
)

# Nothing in either payload may be one of these. The list is the Deal's
# own permlevel-1 block plus the commission rate the job carries.
FOUNDER_ONLY = {
    "commission_pct",
    "total_commission",
    "cm",
    "profit_before_tax",
    "tndn",
    "net_profit",
    "vat_payable",
}

AUG_09 = datetime(2026, 8, 9, 9, 12)
AUG_17 = datetime(2026, 8, 17, 14, 30)


def quote(name="DEAL-0182-Q2", version=2, status="Sent", total=486_000_000, **overrides):
    return {
        "name": name,
        "deal": "DEAL-0182",
        "version": version,
        "status": status,
        "total": total,
        "published_on": AUG_09,
        "sent_on": AUG_09,
        "confirmed_on": None,
        **overrides,
    }


def opened(quote_name, via, events, last_open):
    """A grouped (quote, via) row as the database returns it."""
    return {"quote": quote_name, "via": via, "events": events, LAST_OPEN: last_open}


def row(**overrides):
    """The quote row the list endpoint builds, defaults applied."""
    return quotation_row(
        quote(),
        deal_title="TVC Tết 2027",
        company="COM-0004",
        client="Nhất Minh Beverage",
        url="https://aura.example/quote/abc",
        **overrides,
    )


# -- open tracking arrives as fields, not as a sentence --


def test_a_quote_nobody_opened_reads_as_zeros_rather_than_a_gap():
    """The column exists whether or not the client ever clicked."""
    tracked = row()

    assert tracked["open_count"] == 0
    assert tracked["download_count"] == 0
    assert tracked["last_opened_at"] is None


def test_page_opens_and_pdf_downloads_are_counted_apart():
    """The page's own download button would otherwise score one visit
    as two opens."""
    tracking = open_tracking(
        [
            opened("DEAL-0182-Q2", PAGE, 3, AUG_17),
            opened("DEAL-0182-Q2", PDF, 1, AUG_09),
        ]
    )
    tracked = row(tracking=tracking["DEAL-0182-Q2"])

    assert tracked["open_count"] == 3
    assert tracked["download_count"] == 1


def test_the_last_open_is_the_newest_event_of_either_kind():
    tracking = open_tracking(
        [
            opened("DEAL-0182-Q2", PAGE, 3, AUG_09),
            opened("DEAL-0182-Q2", PDF, 1, AUG_17),
        ]
    )

    assert tracking["DEAL-0182-Q2"][LAST_OPEN] == AUG_17


def test_each_version_of_a_deal_keeps_its_own_opens():
    """Three versions of one deal: the client read the newest twice and
    the first one once, and the list has to say so version by version."""
    tracking = open_tracking(
        [
            opened("DEAL-0182-Q1", PAGE, 1, AUG_09),
            opened("DEAL-0182-Q3", PAGE, 2, AUG_17),
        ]
    )
    versions = [
        quotation_row(
            quote(name=f"DEAL-0182-Q{n}", version=n),
            tracking=tracking.get(f"DEAL-0182-Q{n}"),
        )
        for n in (3, 2, 1)
    ]

    assert [(v["version"], v["open_count"]) for v in versions] == [
        (3, 2),
        (2, 0),
        (1, 1),
    ]


def test_nothing_opened_anywhere_folds_to_nothing():
    assert open_tracking([]) == {}


# -- the row itself --


def test_the_row_names_the_deal_and_the_client_it_belongs_to():
    """A cross-deal list is unreadable without them; the deal's own
    list never needed them."""
    tracked = row()

    assert tracked["deal"] == "DEAL-0182"
    assert tracked["deal_title"] == "TVC Tết 2027"
    assert tracked["client"] == "Nhất Minh Beverage"
    assert tracked["company"] == "COM-0004"


def test_the_row_carries_the_delivery_dates_as_dates():
    tracked = row()

    assert tracked["published_on"] == AUG_09
    assert tracked["sent_on"] == AUG_09
    assert tracked["confirmed_on"] is None
    assert tracked["status"] == "Sent"


def test_the_total_is_whole_dong_not_a_float():
    assert quotation_row(quote(total=486_000_000.4))["total"] == 486_000_000
    assert isinstance(quotation_row(quote(total="486000000"))["total"], int)


def test_a_quote_row_holds_nothing_the_founder_alone_may_see():
    assert FOUNDER_ONLY.isdisjoint(row())


# -- search: the two things a quote is remembered by --


def test_an_empty_search_matches_everything():
    assert matches_search(row(), None)
    assert matches_search(row(), "   ")


def test_a_search_matches_the_deal_title_case_insensitively():
    assert matches_search(row(), "tết")
    assert not matches_search(row(), "Đường")


def test_a_search_matches_the_client_too():
    assert matches_search(row(), "nhất minh")


def test_a_row_with_no_client_yet_is_searchable_without_blowing_up():
    assert not matches_search(quotation_row(quote()), "minh")


# -- what a job earned --

QUOTED_TOTAL = 486_000_000
REVENUE_EX_VAT = 450_000_000  # subtotal + management fee; VAT is the client's


def milestone(pct, amount, status):
    return {"pct": pct, "amount": amount, "status": status}


def job(actual_cost=300_000_000, milestones=(), quoted_cost=320_000_000):
    return profit_view(
        quoted_total=QUOTED_TOTAL,
        revenue_ex_vat=REVENUE_EX_VAT,
        quoted_cost=quoted_cost,
        actual_cost=actual_cost,
        milestones=milestones,
    )


PLAN = (
    milestone(50, 243_000_000, "Paid"),
    milestone(25, 121_500_000, "Invoiced"),
    milestone(25, 121_500_000, "Not requested"),
)


def test_only_a_paid_milestone_is_money_in():
    """Invoiced is money asked for; the difference is the whole point of
    the collection flow."""
    assert collected(PLAN) == 243_000_000
    assert job(milestones=PLAN)["collected"] == 243_000_000


def test_what_is_left_is_measured_against_the_quoted_total():
    earned = job(milestones=PLAN)

    assert earned["uncollected"] == QUOTED_TOTAL - 243_000_000
    assert earned["collected"] + earned["uncollected"] == earned["quoted_total"]


def test_a_job_with_no_milestones_has_collected_nothing_and_is_owed_it_all():
    """A job converted before anyone planned the billing still reads."""
    earned = job(milestones=[])

    assert earned["collected"] == 0
    assert earned["uncollected"] == QUOTED_TOTAL


def test_a_job_with_nothing_spent_yet_keeps_the_whole_revenue():
    earned = job(actual_cost=0)

    assert earned["actual_cost"] == 0
    assert earned["margin"] == REVENUE_EX_VAT
    assert earned["margin_pct"] == 100.0


def test_margin_is_the_revenue_the_company_keeps_less_what_it_paid_out():
    earned = job(actual_cost=300_000_000)

    assert earned["revenue_ex_vat"] == REVENUE_EX_VAT
    assert earned["margin"] == 150_000_000
    assert round(earned["margin_pct"], 4) == round(150 / 450 * 100, 4)


def test_a_job_that_overspent_its_quoted_cost_reads_negative():
    """Catering ran over on day 2 and the shoot ate the difference; the
    number has to say so, not stop at zero."""
    earned = job(actual_cost=470_000_000, quoted_cost=320_000_000)

    assert earned["actual_cost"] > earned["quoted_cost"]
    assert earned["margin"] == -20_000_000
    assert earned["margin_pct"] < 0


def test_the_printed_margin_is_exactly_the_printed_parts():
    earned = job(actual_cost=300_000_000.5)

    assert earned["margin"] == earned["revenue_ex_vat"] - earned["actual_cost"]
    assert all(
        isinstance(earned[field], int)
        for field in (
            "quoted_total",
            "collected",
            "uncollected",
            "revenue_ex_vat",
            "quoted_cost",
            "actual_cost",
            "margin",
        )
    )


def test_a_job_quoted_at_nothing_has_no_margin_percentage():
    """0% would read as a job breaking even, which is a different claim."""
    assert margin_pct(0, 0) is None
    assert profit_view(
        quoted_total=0, revenue_ex_vat=0, quoted_cost=0, actual_cost=0
    )["margin_pct"] is None


def test_a_job_payload_holds_nothing_the_founder_alone_may_see():
    """Margin and money in are producer-visible by decision; the profit
    chain is not, and this payload has no room for it."""
    assert FOUNDER_ONLY.isdisjoint(job(milestones=PLAN))

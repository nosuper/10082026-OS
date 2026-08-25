"""Pure-python tests for auraos.lib.quote - no Frappe required.

Two rules live here because both are decisions, not plumbing (T6 / spec
#2, stories 20–25):

- The **guest serialization boundary**: what a client may read off a
  published quote. Expressed as a whitelist so that adding an internal
  field to the Deal Quote schema can never leak it by default.
- The **silence nudge condition**: when a sent quote counts as ignored.

The Frappe-side tests (auraos/**/test_deal_quote.py) prove the web page
and API actually go through these functions.
"""

from datetime import datetime, timedelta
from decimal import Decimal as D

import pytest

from auraos.lib.quote import (
    CLIENT_PACKAGE_FIELDS,
    CLIENT_PHASE_FIELDS,
    CLIENT_QUOTE_FIELDS,
    client_entries,
    phase_groups,
    client_view,
    delivery_state,
    needs_nudge,
    quote_chain,
    quote_totals,
)


def quote(**overrides):
    """A published quote as the controller hands it over: every field of
    the Deal Quote row, internals included."""
    row = {
        "name": "DEAL-0001-Q2",
        "deal": "DEAL-0001",
        "version": 2,
        "token": "abc123",
        "status": "Sent",
        "title": "Brand film - Q4 campaign",
        "client_name": "Acme JSC",
        "published_on": datetime(2026, 8, 1, 9, 0),
        "quote_mf_pct": 10,
        "vat_pct": 8,
        "subtotal": 100_000_000,
        "mf_amount": 10_000_000,
        "vat_amount": 8_800_000,
        "total": 118_800_000,
        "notes": "Valid for 30 days.",
        # Internals - none of these may cross the boundary.
        "quote_margin": 40_000_000,
        "quote_margin_pct": 33.9,
        "commission_pct": 5,
        "total_commission": 5_940_000,
        "cm": 34_060_000,
        "net_profit": 27_248_000,
        "floor_breached": 1,
        "owner": "founder@aura.local",
        "packages": [
            {
                "title": "Human resources",
                "description": "Director, DOP, crew for 3 shoot days",
                "price": 60_000_000,
                # Internals on the package row too.
                "default_price": 58_400_000,
                "variance": 1_600_000,
                "price_override": 60_000_000,
            },
            {
                "title": "Equipment",
                "description": "Camera, lighting, grip",
                "price": 40_000_000,
                "default_price": 40_000_000,
                "variance": 0,
                "price_override": 0,
            },
        ],
    }
    row.update(overrides)
    return row


# -- the guest serialization boundary --


def test_client_view_keeps_only_whitelisted_quote_fields():
    view = client_view(quote())
    # `sections`, `phase_groups` and `line_phase_groups` are derived
    # presentation, built only from whitelisted package, line and phase
    # fields - no new data crosses the boundary. `phases` is the frozen
    # phase rows, themselves whitelisted by CLIENT_PHASE_FIELDS and
    # asserted below.
    assert set(view) == set(CLIENT_QUOTE_FIELDS) | {
        "packages",
        "sections",
        "phases",
        "phase_groups",
        "line_phase_groups",
    }


def test_client_view_keeps_only_whitelisted_phase_fields():
    """The same guard the packages get, for the same reason: adding a
    field to Deal Quote Phase must not publish it by accident."""
    view = client_view(
        quote(phases=[{"title": "Tiền kỳ", "blurb": "Chuẩn bị", "idx": 1,
                       "parent": "DQ-0001", "owner": "founder@auraos.test"}])
    )

    assert [set(one) for one in view["phases"]] == [set(CLIENT_PHASE_FIELDS)]
    assert view["phases"][0]["title"] == "Tiền kỳ"


def test_client_view_keeps_only_whitelisted_package_fields():
    view = client_view(quote())
    for package in view["packages"]:
        assert set(package) == set(CLIENT_PACKAGE_FIELDS)


@pytest.mark.parametrize(
    "internal",
    [
        "quote_margin",
        "quote_margin_pct",
        "commission_pct",
        "total_commission",
        "cm",
        "net_profit",
        "floor_breached",
        "owner",
        "deal",
    ],
)
def test_client_view_drops_every_internal_field(internal):
    assert internal not in client_view(quote())


@pytest.mark.parametrize("internal", ["default_price", "variance", "price_override"])
def test_client_view_drops_internal_package_fields(internal):
    for package in client_view(quote())["packages"]:
        assert internal not in package


def test_client_view_carries_the_client_facing_numbers():
    view = client_view(quote())
    assert view["total"] == 118_800_000
    assert view["subtotal"] == 100_000_000
    assert view["vat_amount"] == 8_800_000
    assert [p["price"] for p in view["packages"]] == [60_000_000, 40_000_000]
    assert view["packages"][0]["title"] == "Human resources"


def test_client_view_never_leaks_an_unknown_field():
    # The regression this whitelist exists for: a new column on Deal
    # Quote must not reach the client until someone adds it here.
    view = client_view(quote(secret_new_field="overhead is 80m/month"))
    assert "secret_new_field" not in view


def test_client_view_tolerates_missing_optional_fields():
    view = client_view({"title": "Bare quote", "packages": []})
    assert view["title"] == "Bare quote"
    assert view["packages"] == []
    assert view["total"] is None


# -- the totals the client adds up --


def test_quote_totals_are_built_from_the_package_prices():
    totals = quote_totals([60_000_000, 40_000_000], mf_rate=D("0.1"), vat_rate=D("0.08"))
    assert totals.subtotal == 100_000_000
    assert totals.mf_amount == 10_000_000
    assert totals.vat_amount == D("8800000.0")
    assert totals.total == D("118800000.0")


def test_an_overridden_package_price_moves_the_quote_total():
    # The bug this pins: a producer rounds a package up, the client sees
    # the rounded price - and the Total must be the number they get when
    # they add the packages up themselves, or the page contradicts itself.
    plain = quote_totals([58_400_000, 40_000_000], mf_rate=D("0.1"), vat_rate=D("0.08"))
    rounded = quote_totals([60_000_000, 40_000_000], mf_rate=D("0.1"), vat_rate=D("0.08"))
    assert rounded.subtotal - plain.subtotal == 1_600_000
    assert rounded.total > plain.total


def test_quote_totals_of_no_packages_are_zero():
    totals = quote_totals([], mf_rate=D("0.1"), vat_rate=D("0.08"))
    assert (totals.subtotal, totals.mf_amount, totals.vat_amount, totals.total) == (0, 0, 0, 0)


def test_vat_applies_to_the_management_fee_too():
    totals = quote_totals([100_000_000], mf_rate=D("0.1"), vat_rate=D("0.08"))
    assert totals.vat_amount == (totals.subtotal + totals.mf_amount) * D("0.08")


# -- what the client is offered --


def package(title, price, description=None):
    return {"title": title, "description": description, "price": price}


def cost_line(idx, description, package_title, quote_price):
    return {
        "idx": idx,
        "description": description,
        "package": package_title,
        "quote_price": quote_price,
    }


def test_client_entries_lists_packages_first():
    entries = client_entries(
        [package("Human resources", 60_000_000), package("Equipment", 40_000_000)],
        [cost_line(1, "Đạo diễn", "Human resources", 60_000_000)],
    )
    assert [e["title"] for e in entries] == ["Human resources", "Equipment"]


def test_a_line_in_no_package_becomes_its_own_entry():
    # The founder prices some items as standalone packages and quotes
    # them straight - an unassigned line is an offer, not an error.
    entries = client_entries(
        [package("Equipment", 40_000_000)],
        [
            cost_line(1, "Thuê thiết bị", "Equipment", 40_000_000),
            cost_line(2, "Drone operator", None, 12_000_000),
        ],
    )
    assert [e["title"] for e in entries] == ["Equipment", "Drone operator"]
    assert entries[1]["price"] == 12_000_000


def test_a_standalone_line_without_a_description_still_gets_a_name():
    entries = client_entries([], [cost_line(3, "", None, 5_000_000)])
    assert entries[0]["title"] == "Item 3"


# -- the profit chain the client's price implies --


CHAIN = dict(
    cost_basis=D(70_000_000),
    input_vat=D(4_000_000),
    mf_rate=D("0.1"),
    vat_rate=D("0.08"),
    commission_rate=D("0.05"),
)


def test_margin_is_measured_against_what_the_client_pays():
    chain = quote_chain([100_000_000], **CHAIN)
    assert chain.revenue_ex_vat == 110_000_000
    assert chain.margin == 110_000_000 - 70_000_000


def test_rounding_a_package_up_raises_the_margin():
    # Issue #32: the breakdown used to measure margin against the
    # line-based total, so an override moved the client's price without
    # moving the margin, the margin %, or the floor warning.
    plain = quote_chain([98_400_000], **CHAIN)
    rounded = quote_chain([100_000_000], **CHAIN)
    assert rounded.margin > plain.margin
    assert rounded.margin - plain.margin == (100_000_000 - 98_400_000) * D("1.1")


def test_commission_is_taken_on_the_client_facing_revenue():
    chain = quote_chain([100_000_000], **CHAIN)
    assert chain.total_commission == chain.revenue_ex_vat * D("0.05")
    assert chain.cm == chain.margin - chain.total_commission


def test_the_profit_chain_runs_to_net_profit():
    chain = quote_chain([100_000_000], **CHAIN)
    assert chain.profit_before_tax == (
        chain.revenue_ex_vat - D(70_000_000) - chain.total_commission
    )
    assert chain.tndn == chain.profit_before_tax * D("0.2")
    assert chain.net_profit == chain.profit_before_tax - chain.tndn


def test_vat_payable_is_output_vat_less_input_vat():
    chain = quote_chain([100_000_000], **CHAIN)
    assert chain.vat_payable == chain.vat_amount - D(4_000_000)


def test_margin_fraction_is_none_without_revenue():
    assert quote_chain([], **CHAIN).margin_fraction is None


def test_margin_fraction_is_margin_over_revenue():
    chain = quote_chain([100_000_000], **CHAIN)
    assert chain.margin_fraction == chain.margin / chain.revenue_ex_vat


# -- which version the deal's status follows --


def version(n, status):
    return {"name": f"DEAL-0001-Q{n}", "version": n, "status": status}


def test_delivery_state_of_a_deal_with_no_versions_is_nothing():
    assert delivery_state([]) is None


def test_the_only_version_speaks_for_the_deal():
    assert delivery_state([version(1, "Published")])["version"] == 1


def test_republishing_does_not_unsend_the_version_the_client_holds():
    # The regression: a quote sent 10 days ago, then re-published with a
    # tweak, must keep saying "Sent" - otherwise it drops out of the
    # nudge and dies of silence, which is the whole point of T6.
    versions = [version(2, "Published"), version(1, "Sent")]
    assert delivery_state(versions)["version"] == 1


def test_the_newest_delivered_version_wins():
    versions = [version(3, "Sent"), version(2, "Sent"), version(1, "Confirmed")]
    assert delivery_state(versions)["version"] == 3


def test_a_confirmed_older_version_still_speaks_over_a_fresh_draft():
    versions = [version(2, "Published"), version(1, "Confirmed")]
    assert delivery_state(versions)["status"] == "Confirmed"


def test_nothing_delivered_yet_falls_back_to_the_newest():
    versions = [version(2, "Published"), version(1, "Published")]
    assert delivery_state(versions)["version"] == 2


# -- the silence nudge --

SENT_ON = datetime(2026, 8, 1, 9, 0)


def test_no_nudge_before_the_silence_window_elapses():
    assert not needs_nudge(
        status="Sent", sent_on=SENT_ON, now=SENT_ON + timedelta(days=4, hours=23), silence_days=5
    )


def test_nudge_once_the_silence_window_elapses():
    assert needs_nudge(
        status="Sent", sent_on=SENT_ON, now=SENT_ON + timedelta(days=5), silence_days=5
    )


def test_no_nudge_for_a_confirmed_quote():
    assert not needs_nudge(
        status="Confirmed", sent_on=SENT_ON, now=SENT_ON + timedelta(days=30), silence_days=5
    )


def test_no_nudge_for_a_published_but_unsent_quote():
    # Published means the page exists; the client may never have been
    # given the link, so silence says nothing.
    assert not needs_nudge(
        status="Published", sent_on=None, now=SENT_ON + timedelta(days=30), silence_days=5
    )


def test_no_nudge_without_a_sent_timestamp():
    assert not needs_nudge(
        status="Sent", sent_on=None, now=SENT_ON + timedelta(days=30), silence_days=5
    )


@pytest.mark.parametrize("silence_days", [0, None])
def test_zero_silence_days_turns_the_nudge_off(silence_days):
    assert not needs_nudge(
        status="Sent", sent_on=SENT_ON, now=SENT_ON + timedelta(days=365),
        silence_days=silence_days,
    )


# -- detail levels (A3, playbook §3.3) --


from auraos.lib.quote import (  # noqa: E402
    line_sections,
    lump_sum_entry,
    quantity_display,
)


def test_quantity_reads_the_way_a_bid_writes_it():
    assert quantity_display(2, "người", 3, "ngày") == "2 người × 3 ngày"


def test_quantity_of_one_with_no_unit_is_silence_not_noise():
    assert quantity_display(1, "", 1, None) == ""
    assert quantity_display(1, "", 3, "ngày") == "3 ngày"


def test_quantity_keeps_a_bare_count_above_one():
    assert quantity_display(10, "", 3, "ngày") == "10 × 3 ngày"


def test_quantity_drops_trailing_zeroes():
    assert quantity_display(2.5, "ngày", 1, "") == "2.5 ngày"


def _lines():
    return [
        {"package": "Crew", "description": "Đạo diễn", "qty1": 1,
         "qty1_unit": "người", "qty2": 3, "qty2_unit": "ngày",
         "quote_price": 20_000_000},
        {"package": "Crew", "description": "Quay phim", "qty1": 2,
         "qty1_unit": "người", "qty2": 3, "qty2_unit": "ngày",
         "quote_price": 28_000_000},
        {"package": None, "description": "Flycam", "qty1": 1,
         "qty1_unit": "", "qty2": 1, "qty2_unit": "",
         "quote_price": 6_900_000, "idx": 3},
    ]


def test_sections_group_lines_under_their_package():
    sections = line_sections(
        [{"title": "Crew", "description": "Crew!", "price": 48_000_000}],
        _lines(),
    )
    assert [s["title"] for s in sections] == ["Crew", "Flycam"]
    crew = sections[0]
    assert [line["description"] for line in crew["lines"]] == [
        "Đạo diễn",
        "Quay phim",
    ]
    assert crew["lines"][0]["quantity"] == "1 người × 3 ngày"
    # A standalone line is its own section, price and all, no sub-lines.
    assert sections[1]["price"] == 6_900_000
    assert sections[1]["lines"] == []


def test_an_override_is_folded_back_into_the_lines():
    # The founder's A3 verdict: no Adjustment row - an overridden
    # package must read as if it was simply quoted that way. 45tr
    # offered over 20+28tr of lines → 18,75tr and 26,25tr.
    sections = line_sections(
        [{"title": "Crew", "description": None, "price": 45_000_000}],
        [line for line in _lines() if line["package"] == "Crew"],
    )
    amounts = [line["quote_price"] for line in sections[0]["lines"]]
    assert amounts == [18_750_000, D("26250000")]
    assert sum(amounts) == 45_000_000


def test_the_rescale_remainder_lands_on_the_last_line():
    # A target that doesn't divide cleanly must still close exactly.
    sections = line_sections(
        [{"title": "Crew", "description": None, "price": 45_000_001}],
        [line for line in _lines() if line["package"] == "Crew"],
    )
    amounts = [line["quote_price"] for line in sections[0]["lines"]]
    assert sum(amounts) == 45_000_001


def test_a_section_matching_its_lines_keeps_them_untouched():
    sections = line_sections(
        [{"title": "Crew", "description": None, "price": 48_000_000}],
        [line for line in _lines() if line["package"] == "Crew"],
    )
    assert [line["quote_price"] for line in sections[0]["lines"]] == [
        20_000_000,
        28_000_000,
    ]


def test_each_line_carries_its_marked_up_unit_rate():
    sections = line_sections(
        [{"title": "Crew", "description": None, "price": 48_000_000}],
        [line for line in _lines() if line["package"] == "Crew"],
    )
    director, camera = sections[0]["lines"]
    # 20tr over 1 × 3 ngày → 6.666.667/ngày; 28tr over 2 × 3 → 4.666.667.
    assert director["unit_rate"] == 6_666_667
    assert camera["unit_rate"] == 4_666_667
    assert director["qty1_display"] == "1"
    assert director["qty2_display"] == "3"


def test_lump_sum_collapses_the_offer_but_keeps_the_scope():
    entry = lump_sum_entry(
        "Social series - 6 tập",
        [
            {"title": "Crew", "price": 48_000_000},
            {"title": "Equipment", "price": 31_350_000},
        ],
    )
    assert entry["title"] == "Social series - 6 tập"
    assert entry["description"] == "Crew, Equipment"
    assert entry["price"] == 79_350_000


def test_client_line_fields_never_name_the_cost_side():
    from auraos.lib.quote import CLIENT_LINE_FIELDS

    for internal in ("unit_price", "markup_pct", "vendor_mf_pct",
                     "tax_type", "cost_basis", "margin"):
        assert internal not in CLIENT_LINE_FIELDS


def test_a_standalone_entry_and_its_frozen_line_print_once():
    # The publish freezes a standalone line twice over: as its own
    # package entry AND as a frozen line. The page must print it once.
    sections = line_sections(
        [
            {"title": "Crew", "description": None, "price": 48_000_000},
            {"title": "Flycam", "description": None, "price": 6_900_000},
        ],
        _lines(),
    )
    assert [s["title"] for s in sections] == ["Crew", "Flycam"]
    assert sections[1]["price"] == 6_900_000


# -- phases: how a client reads a job split into parts (#43) --
#
# The arithmetic is a sum. What these pin is **which group an entry lands
# in and in what order the groups print** - the four ways a phased quote
# misleads while looking tidy:
#
# - Unphased entries buried at the end, where the items outside the plan
#   are exactly the ones a client should meet first.
# - An empty phase printed as a heading with a zero under it, which reads
#   as a defect in the document.
# - A package whose phase was renamed underneath it quietly vanishing -
#   money the client is being asked for, gone to keep a layout tidy.
# - Subtotals that are not the sum of the rows above them.


def a_phase(title, blurb=None):
    return {"title": title, "blurb": blurb}


def an_entry(title, price, phase=None):
    return {"title": title, "description": None, "price": price, "phase": phase}


PRE = "Tiền kỳ"
PRODUCTION = "Sản xuất"


def test_unphased_entries_come_first_and_carry_no_heading():
    """The founder prices a reshoot day outside the shape of the job.

    Naming a phase "Other" for it would be naming something on the
    client's behalf; putting it last would bury the items that sit
    outside the plan.
    """
    groups = phase_groups(
        [a_phase(PRE), a_phase(PRODUCTION)],
        [
            an_entry("Kịch bản", 10_000_000, PRE),
            an_entry("Quay bổ sung", 5_000_000),
            an_entry("Quay chính", 40_000_000, PRODUCTION),
        ],
    )

    assert [group["title"] for group in groups] == [None, PRE, PRODUCTION]
    assert [one["title"] for one in groups[0]["entries"]] == ["Quay bổ sung"]
    assert groups[0]["blurb"] is None


def test_phases_print_in_the_order_they_were_declared():
    """Not alphabetical, and not the order packages happen to be in:
    pre-production comes before post because the founder said so."""
    groups = phase_groups(
        [a_phase(PRODUCTION), a_phase(PRE)],
        [an_entry("Kịch bản", 1, PRE), an_entry("Quay chính", 2, PRODUCTION)],
    )

    assert [group["title"] for group in groups] == [PRODUCTION, PRE]


def test_a_phase_carries_its_own_blurb():
    groups = phase_groups(
        [a_phase(PRE, "Chuẩn bị trước khi bấm máy")],
        [an_entry("Kịch bản", 1, PRE)],
    )

    assert groups[0]["blurb"] == "Chuẩn bị trước khi bấm máy"


def test_an_empty_phase_is_not_printed():
    """A heading with no rows and a zero under it reads as a mistake in
    the document rather than as a phase nobody filled.

    The founder can see it is empty in the editor, where it still
    exists. The client gets the offer, not the shape of the form.
    """
    groups = phase_groups(
        [a_phase(PRE), a_phase(PRODUCTION)],
        [an_entry("Kịch bản", 1, PRE)],
    )

    assert [group["title"] for group in groups] == [PRE]


def test_a_quote_with_no_unphased_entries_opens_on_its_first_phase():
    """The unphased group is dropped when empty like any other."""
    groups = phase_groups(
        [a_phase(PRE)], [an_entry("Kịch bản", 1, PRE)]
    )

    assert [group["title"] for group in groups] == [PRE]


def test_an_entry_naming_an_undeclared_phase_is_kept_and_put_last():
    """A package whose phase was renamed underneath it must not vanish.

    Money the client is being asked for is never the thing that
    disappears to keep a layout tidy. Last, in the order first met, so
    the founder sees it is adrift without the client losing the line.
    """
    groups = phase_groups(
        [a_phase(PRE)],
        [
            an_entry("Kịch bản", 1, PRE),
            an_entry("Hậu kỳ", 2, "Hậu kỳ"),
            an_entry("Grade", 3, "Hậu kỳ"),
        ],
    )

    assert [group["title"] for group in groups] == [PRE, "Hậu kỳ"]
    assert [one["title"] for one in groups[-1]["entries"]] == ["Hậu kỳ", "Grade"]


def test_a_subtotal_is_the_sum_of_the_rows_printed_above_it():
    groups = phase_groups(
        [a_phase(PRE)],
        [
            an_entry("Kịch bản", 10_000_000, PRE),
            an_entry("Casting", 2_500_000, PRE),
            an_entry("Quay bổ sung", 5_000_000),
        ],
    )

    for group in groups:
        assert group["subtotal"] == sum(one["price"] for one in group["entries"])
    assert groups[0]["subtotal"] == 5_000_000
    assert groups[1]["subtotal"] == 12_500_000


def test_every_entry_lands_in_exactly_one_group():
    """The groups account for the whole quote, which is what lets a
    reader add the subtotals up and reach the quote's own subtotal."""
    entries = [
        an_entry("Kịch bản", 10_000_000, PRE),
        an_entry("Quay chính", 40_000_000, PRODUCTION),
        an_entry("Quay bổ sung", 5_000_000),
        an_entry("Grade", 7_000_000, "Chưa khai báo"),
    ]

    groups = phase_groups([a_phase(PRE), a_phase(PRODUCTION)], entries)

    placed = [one for group in groups for one in group["entries"]]
    assert len(placed) == len(entries)
    assert sum(group["subtotal"] for group in groups) == sum(
        one["price"] for one in entries
    )


def test_a_quote_with_no_phases_at_all_is_one_unlabelled_group():
    """Every quote sent before #43 existed, and every quote the founder
    never split. The page must read exactly as it did."""
    groups = phase_groups(
        [], [an_entry("Trọn gói", 50_000_000)]
    )

    assert [group["title"] for group in groups] == [None]
    assert groups[0]["subtotal"] == 50_000_000


def test_no_phases_and_no_entries_is_no_groups():
    assert phase_groups([], []) == []

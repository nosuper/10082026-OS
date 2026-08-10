"""Pure-python tests for auraos.lib.quote — no Frappe required.

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
    CLIENT_QUOTE_FIELDS,
    client_view,
    delivery_state,
    needs_nudge,
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
        "title": "Brand film — Q4 campaign",
        "client_name": "Acme JSC",
        "published_on": datetime(2026, 8, 1, 9, 0),
        "quote_mf_pct": 10,
        "vat_pct": 8,
        "subtotal": 100_000_000,
        "mf_amount": 10_000_000,
        "vat_amount": 8_800_000,
        "total": 118_800_000,
        "notes": "Valid for 30 days.",
        # Internals — none of these may cross the boundary.
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
    assert set(view) == set(CLIENT_QUOTE_FIELDS) | {"packages"}


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
    # the rounded price — and the Total must be the number they get when
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


# -- which version the deal's status follows --


def version(n, status):
    return {"name": f"DEAL-0001-Q{n}", "version": n, "status": status}


def test_delivery_state_of_a_deal_with_no_versions_is_nothing():
    assert delivery_state([]) is None


def test_the_only_version_speaks_for_the_deal():
    assert delivery_state([version(1, "Published")])["version"] == 1


def test_republishing_does_not_unsend_the_version_the_client_holds():
    # The regression: a quote sent 10 days ago, then re-published with a
    # tweak, must keep saying "Sent" — otherwise it drops out of the
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

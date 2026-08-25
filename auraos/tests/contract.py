"""Shared assertions for the reporting API contract (issue #83, spec #81).

The React app is a separate frontend that talks to Frappe over HTTP, so
the JSON these endpoints return stopped being an internal detail and
became the interface between two systems. This module holds the four
promises spec #81 makes about that interface, in one place so that all
five endpoints are held to the same one:

1. **Every documented key is present**, at every level of nesting, so
   renaming a field fails a test rather than a screen.
2. **Money crosses the wire as integer đồng** - not a float, not a
   string, not a Decimal.
3. **Dates cross the wire as ISO strings**, parseable by the frontend
   without a format guess.
4. **The founder profit chain is never in a payload a producer can
   ask for**, checked as a whole key set rather than by spot-checking
   names, so a founder field added next year cannot ride along
   unnoticed.

Nothing here re-tests arithmetic. That a month's total equals the sum of
its client rows is a rule, and rules are pinned framework-free in
`tests/` against the pure module. A contract test that also added the
parts up would pin the same rule twice and make the cheap failure - a
renamed key - no cheaper to find.
"""

from datetime import date, datetime
from typing import Mapping

# The Deal's permlevel-1 block plus the commission rate. Defined once
# because five endpoints have to agree about it: adding a founder field
# here is what makes every contract test start guarding it.
FOUNDER_ONLY = frozenset(
    {
        "commission_pct",
        "total_commission",
        "cm",
        "profit_before_tax",
        "tndn",
        "net_profit",
        "vat_payable",
    }
)


def assert_keys(case, payload, expected, where="payload"):
    """The key set, exactly - no key missing and no key invented."""
    case.assertEqual(sorted(payload), sorted(expected), f"{where} key set")


def assert_money(case, payload, *fields, where="payload"):
    """Whole đồng as a Python int.

    `type(...) is int` rather than isinstance: a bool is an int to
    isinstance, and a Decimal that survived to the wire is exactly the
    bug this catches.
    """
    for field in fields:
        case.assertIn(field, payload, f"{where} is missing {field}")
        value = payload[field]
        case.assertIs(
            type(value),
            int,
            f"{where}.{field} is {type(value).__name__} {value!r}, not whole đồng",
        )


def assert_counts(case, payload, *fields, where="payload"):
    """A count is a plain int too - the screen renders it, never parses it."""
    for field in fields:
        case.assertIn(field, payload, f"{where} is missing {field}")
        case.assertIs(
            type(payload[field]),
            int,
            f"{where}.{field} is not a count",
        )


def assert_iso_date(case, value, where="date"):
    """A calendar day as `2026-08-01`, round-tripping through date."""
    case.assertIsInstance(value, str, f"{where} is {type(value).__name__}, not a string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        case.fail(f"{where} is {value!r}, not an ISO date")
    case.assertEqual(parsed.isoformat(), value, f"{where} is not a bare ISO date")


def assert_iso_timestamp(case, value, where="timestamp"):
    """A moment as an ISO 8601 string the frontend can parse unaided."""
    case.assertIsInstance(value, str, f"{where} is {type(value).__name__}, not a string")
    try:
        datetime.fromisoformat(value)
    except ValueError:
        case.fail(f"{where} is {value!r}, not an ISO timestamp")


def assert_no_founder_chain(case, payload, where="payload"):
    """No founder-only key anywhere in the payload, however deep.

    Walked rather than checked at the top level: income comes back as
    months of client rows and receivables as buckets of milestone rows,
    and a leak two levels down is still a leak.
    """
    if isinstance(payload, Mapping):
        leaked = FOUNDER_ONLY.intersection(payload)
        case.assertEqual(
            leaked, set(), f"{where} carries founder-only {sorted(leaked)}"
        )
        for key, value in payload.items():
            assert_no_founder_chain(case, value, f"{where}.{key}")
    elif isinstance(payload, (list, tuple)):
        for index, item in enumerate(payload):
            assert_no_founder_chain(case, item, f"{where}[{index}]")

"""Seed data for a preview stack — never real, never preserved.

A walkthrough should start with something to click, not an empty site:
before this existed, every preview began with someone hand-building a
company, a deal, cost lines and packages, and the T6 walkthrough missed
the silence nudge entirely because no aged quote existed to trigger it.

**This file belongs to the branch.** The base below is what every
feature needs; a ticket adds its own case to `FEATURE_SEEDS` in the same
commit as the feature, so its screen is reachable the moment the stack
boots. Everything here is idempotent — running it twice changes nothing.

Run by scripts/preview.sh; by hand:

    bench --site dev.localhost execute auraos.setup.seed.run
"""

import frappe

COMPANY = "Chungify Media"
CONTACT = "Chị Hằng"

# One deal per pipeline stage worth looking at, so the board is never
# empty and drag-and-drop has somewhere to go.
DEALS = [
    {"title": "TVC Tết 2027", "stage": "Brief Received"},
    {"title": "Social series — 6 tập", "stage": "Breakdown"},
    {"title": "Phim doanh nghiệp Vinamilk", "stage": "Negotiation"},
]

# A breakdown that exercises every offered tax type, with two packages
# and one line quoted standalone (the founder prices some items that way).
COST_LINES = [
    {
        "description": "Đạo diễn",
        "package": "Human resources",
        "qty1": 1, "qty1_unit": "người", "qty2": 3, "qty2_unit": "ngày",
        "unit_price": 5_000_000, "tax_type": "Cá nhân", "markup_pct": 20,
    },
    {
        "description": "Quay phim + trợ lý",
        "package": "Human resources",
        "qty1": 2, "qty1_unit": "người", "qty2": 3, "qty2_unit": "ngày",
        "unit_price": 3_500_000, "tax_type": "Cá nhân", "markup_pct": 20,
    },
    {
        "description": "Thuê thiết bị",
        "package": "Equipment",
        "qty1": 1, "qty2": 3, "qty2_unit": "ngày",
        "unit_price": 8_000_000, "tax_type": "Công ty",
        "vendor_mf_pct": 5, "markup_pct": 10,
    },
    {
        "description": "Ăn uống đoàn",
        "package": "Equipment",
        "qty1": 10, "qty2": 3,
        "unit_price": 150_000, "tax_type": "Không hoá đơn", "markup_pct": 10,
    },
    {
        # Deliberately in no package: quoted as its own line.
        "description": "Flycam",
        "qty1": 1, "qty2": 1,
        "unit_price": 6_000_000, "tax_type": "Công ty", "markup_pct": 15,
    },
]

PACKAGES = [
    {"title": "Human resources", "description": "Director, DOP and crew for three shoot days"},
    {"title": "Equipment", "description": "Camera, lighting, grip and unit catering"},
]


def run():
    """Build the base data, then every registered feature seed."""
    company = ensure_company()
    ensure_contact(company)
    deals = [ensure_deal(company, **deal) for deal in DEALS]
    priced = ensure_breakdown(deals[1])

    for name, seed in FEATURE_SEEDS.items():
        seed(priced)
        print(f"seeded: {name}")

    frappe.db.commit()
    print(f"seed complete — {len(deals)} deals on {company}")


# -- base --


def ensure_company():
    existing = frappe.db.exists("Party Company", {"company_name": COMPANY})
    if existing:
        return existing
    return frappe.get_doc(
        {
            "doctype": "Party Company",
            "company_name": COMPANY,
            "tax_code": "0312345678",
        }
    ).insert(ignore_permissions=True).name


def ensure_contact(company):
    if frappe.db.exists("Party Contact", {"full_name": CONTACT}):
        return
    frappe.get_doc(
        {
            "doctype": "Party Contact",
            "full_name": CONTACT,
            "company": company,
            "email": "hang@chungify.example",
            "phone": "0901234567",
        }
    ).insert(ignore_permissions=True)


def founder():
    """Whoever holds the Founder role — Administrator on a fresh site."""
    holders = frappe.get_all(
        "Has Role",
        filters={"role": "Founder", "parenttype": "User"},
        pluck="parent",
    )
    return holders[0] if holders else "Administrator"


def ensure_deal(company, title, stage):
    existing = frappe.db.exists("Deal", {"title": title})
    if existing:
        return existing
    return frappe.get_doc(
        {
            "doctype": "Deal",
            "title": title,
            "company": company,
            "stage": stage,
            "deal_owner": founder(),
            "estimated_budget": 150_000_000,
        }
    ).insert(ignore_permissions=True).name


def ensure_breakdown(deal_name):
    """Give one deal a full breakdown, priced and packaged."""
    deal = frappe.get_doc("Deal", deal_name)
    if not deal.cost_lines:
        for row in COST_LINES:
            deal.append("cost_lines", dict(row))
        for row in PACKAGES:
            deal.append("packages", dict(row))
        deal.save(ignore_permissions=True)
    return deal.name


# -- per-feature seeds; a ticket adds its own here --


def seed_t6_quote_delivery(deal_name):
    """T6: a published quote, sent long enough ago to be nudged.

    Without this the silence badge cannot be seen at all — the founder
    walked T6 and reported "No I don't see the badge" for exactly this
    reason.
    """
    from auraos.auraos.doctype.deal_quote.deal_quote import publish

    if frappe.db.exists("Deal Quote", {"deal": deal_name}):
        return

    quote = publish(deal_name, notes="Valid for 30 days. 50% deposit on signing.")
    quote.mark_sent()

    sent_on = frappe.utils.add_to_date(frappe.utils.now_datetime(), days=-8)
    frappe.db.set_value("Deal Quote", quote.name, "sent_on", sent_on)
    frappe.db.set_value("Deal", deal_name, "quote_sent_on", sent_on)

    # An open, so the log has something in it.
    frappe.get_doc(
        {
            "doctype": "Deal Quote Open",
            "quote": quote.name,
            "opened_on": frappe.utils.add_to_date(sent_on, days=1),
            "via": "Page",
            "ip_address": "203.0.113.7",
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
        }
    ).insert(ignore_permissions=True)


FEATURE_SEEDS = {
    "T6 quote delivery": seed_t6_quote_delivery,
}

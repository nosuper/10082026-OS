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

    echo 'from auraos.setup.seed import run; run()' \
        | bench --site dev.localhost console

(`bench execute` cannot run this: it evals the dotted path against its
own module globals, where `auraos` is not a name.)
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

# The deal T7 wins and turns into a job — kept out of DEALS so the
# pipeline board still shows a deal per interesting stage.
WON_DEAL = "MV — Hà Anh Tuấn"

# Two rounds used: the walkthrough's own third round is the chargeable one.
REVISION_NOTES = [
    "Khách muốn đổi nhạc nền và cắt bớt 10 giây",
    "Sửa màu tối hơn ở cảnh cuối",
]

# How the seeded job gets paid: keyed by title so the seed can tell its
# own plan from the standard two-milestone one a conversion creates.
MILESTONES = {
    "Đặt cọc": {"title": "Đặt cọc", "pct": 30, "trigger_stage": "Pre-production"},
    "Sau quay": {"title": "Sau quay", "pct": 40, "trigger_stage": "Post-production"},
    "Nghiệm thu": {"title": "Nghiệm thu", "pct": 30, "trigger_stage": "Client sign-off"},
}

PACKAGES = [
    {"title": "Human resources", "description": "Director, DOP and crew for three shoot days"},
    {"title": "Equipment", "description": "Camera, lighting, grip and unit catering"},
]


def run():
    """Build the base data, then every registered feature seed."""
    ensure_founder_role()
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
            # The invoice-request text reads these off the client record;
            # without an address the walkthrough sees a half message.
            "address": "12 Nguyễn Huệ, Phường Bến Nghé, Quận 1, TP.HCM",
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


def founder_holders():
    return frappe.get_all(
        "Has Role",
        filters={"role": "Founder", "parenttype": "User"},
        pluck="parent",
    )


def ensure_founder_role():
    """Give Administrator the Founder role if nobody holds it.

    A deal's owner must hold an operating role, and that check reads
    explicit Has Role rows — Administrator's implicit access to
    everything does not count. On a fresh site nobody holds it, so
    seeding a deal would fail before it began.
    """
    if founder_holders():
        return
    user = frappe.get_doc("User", "Administrator")
    user.append_roles("Founder")
    user.save(ignore_permissions=True)


def founder():
    """Whoever holds the Founder role — Administrator on a fresh site."""
    holders = founder_holders()
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


def seed_t7_job_in_production(deal_name):
    """T7: a won deal that became a job, mid-revision.

    Its own deal rather than the quoted one: converting the deal T6
    seeds would drag it out of the pipeline the quote walkthrough needs.
    The job is parked one round short of a chargeable change order, so
    logging a revision on the preview shows both the ⚠ flag and the
    stage moving itself back to Post.
    """
    from auraos.auraos.doctype.job.job import create_from_deal

    company = frappe.db.get_value("Deal", deal_name, "company")
    won = ensure_deal(company, title=WON_DEAL, stage="Brief Received")
    ensure_breakdown(won)

    if frappe.db.exists("Job", {"deal": won}):
        return

    deal = frappe.get_doc("Deal", won)
    deal.stage = "Won"
    deal.save(ignore_permissions=True)

    job = create_from_deal(won)
    job.files_location = f"//nas/jobs/{job.name}"
    job.stage = "Client review"
    job.save(ignore_permissions=True)

    # Each round the way it really happens: the job comes back to
    # Client review, the client asks again, the revision sends it back.
    for note in REVISION_NOTES:
        back_to_feedback(job.name)
        frappe.get_doc("Job", job.name).log_revision(note)

    # Left sitting at Client review: the next revision is the interesting one.
    back_to_feedback(job.name)


def back_to_feedback(job_name):
    job = frappe.get_doc("Job", job_name)
    job.stage = "Client review"
    job.save(ignore_permissions=True)


def seed_t10_payment_milestones(deal_name):
    """T10: a three-stage collection with one payment gone quiet.

    A converted job starts with both milestones unrequested and the
    deposit only just due, so a fresh stack would show no nudge at all —
    the hole the T6 walkthrough fell into with the silence badge. This
    walks one job through the flow: the deposit collected, the shoot
    payment invoiced three weeks ago and still unpaid, the final not due
    until the client signs off.
    """
    won = frappe.db.exists("Deal", {"title": WON_DEAL})
    job_name = frappe.db.exists("Job", {"deal": won}) if won else None
    if not job_name:
        return

    job = frappe.get_doc("Job", job_name)
    if [row.title for row in job.payment_milestones] == list(MILESTONES):
        return

    job.set(
        "payment_milestones",
        [dict(row) for row in MILESTONES.values()],
    )
    job.payment_milestones[0].status = "Paid"
    job.payment_milestones[1].status = "Invoiced"
    job.save(ignore_permissions=True)

    # Aged past any sane payment terms, so the board's nudge is visible
    # the moment the stack boots.
    frappe.db.set_value(
        "Job Payment Milestone",
        job.payment_milestones[1].name,
        "due_on",
        frappe.utils.add_to_date(frappe.utils.now_datetime(), days=-21),
        update_modified=False,
    )


FEATURE_SEEDS = {
    "T6 quote delivery": seed_t6_quote_delivery,
    "T7 job in production": seed_t7_job_in_production,
    "T10 payment milestones": seed_t10_payment_milestones,
}

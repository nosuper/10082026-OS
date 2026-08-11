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


# T11: a contract template with a hole in it on purpose.
#
# The walkthrough has to see the thing this ticket is about — a field
# that could not be filled, marked on the page — and a template where
# everything resolves would show only the happy half. `client.address`
# is the gap: the seeded company has a tax code but no address, so the
# founder can watch the marker disappear by filling the record in,
# rather than being told it would.
STARTER_CONTRACT = [
    "HỢP ĐỒNG DỊCH VỤ SẢN XUẤT",
    "",
    "Hôm nay, ngày {{today.day}} tháng {{today.month}} năm {{today.year}},",
    "chúng tôi gồm:",
    "",
    "BÊN A (Bên thuê dịch vụ): {{client.company_name}}",
    "Mã số thuế: {{client.tax_code}}",
    "Địa chỉ: {{client.address}}",
    "Người liên hệ: {{contact.full_name}} — {{contact.phone}}",
    "",
    "Điều 1. Nội dung công việc",
    "Bên B thực hiện: {{job.title}} (mã công việc {{job.code}}).",
    "",
    "Điều 2. Giá trị hợp đồng",
    "Tổng giá trị: {{quote.total}} đồng (đã bao gồm VAT {{quote.vat_pct}}).",
    "",
    "Điều 3. Ký kết",
    "Hợp đồng được lập thành 02 bản, mỗi bên giữ 01 bản.",
    "",
    "ĐẠI DIỆN BÊN A                    ĐẠI DIỆN BÊN B",
]

STARTER_TEMPLATE = "Hợp đồng dịch vụ (mẫu)"


def seed_t11_paperwork(deal_name):
    """T11: a starter contract in the library, ready to generate from.

    Written here rather than committed as a .docx so the sample is
    reviewable text in a diff instead of an opaque blob — and so the
    walkthrough can compare what the template asks for with what comes
    out the other side.
    """
    from auraos.lib.paperwork import build_docx

    if frappe.db.exists("Paperwork Template", {"template_name": STARTER_TEMPLATE}):
        return

    uploaded = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": "hop-dong-dich-vu-mau.docx",
            "is_private": 1,
            "content": build_docx(STARTER_CONTRACT),
        }
    ).insert(ignore_permissions=True)

    frappe.get_doc(
        {
            "doctype": "Paperwork Template",
            "template_name": STARTER_TEMPLATE,
            "template_file": uploaded.file_url,
            "notes": "Starter sample — replace with the company's real contract.",
        }
    ).insert(ignore_permissions=True)


FEATURE_SEEDS = {
    "T6 quote delivery": seed_t6_quote_delivery,
    "T7 job in production": seed_t7_job_in_production,
    "T11 paperwork templates": seed_t11_paperwork,
}

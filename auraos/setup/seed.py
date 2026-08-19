"""Seed data for a preview stack - never real, never preserved.

A walkthrough should start with something to click, not an empty site:
before this existed, every preview began with someone hand-building a
company, a deal, cost lines and packages, and the T6 walkthrough missed
the silence nudge entirely because no aged quote existed to trigger it.

**This file belongs to the branch.** The base below is what every
feature needs; a ticket adds its own case to `FEATURE_SEEDS` in the same
commit as the feature, so its screen is reachable the moment the stack
boots. Everything here is idempotent - running it twice changes nothing.

Run by scripts/preview.sh; by hand:

    echo 'from auraos.setup.seed import run; run()' \
        | bench --site dev.localhost console

(`bench execute` cannot run this: it evals the dotted path against its
own module globals, where `auraos` is not a name.)
"""

import frappe

from auraos.lib.richtext import from_plain_text

COMPANY = "Chungify Media"
CONTACT = "Chị Hằng"

# Two briefs that a plain textarea could not have held, because
# `Deal.brief` is a Text Editor field as of #120 and a seed of
# one-liners means the next person to touch that editor tests it
# against one-liners too.
#
# Written as plain text and converted on the way in through
# auraos.lib.richtext - the same function the migration patch uses - so
# there is one answer to what a blank line meant, and so this does not
# depend on whether that patch has already been logged against the site.
# It has, on any site that has migrated, and Frappe runs a patch once.
MULTI_PARAGRAPH_BRIEF = """Khách muốn một chuỗi 6 clip cho 3 cửa hàng mới.

Mỗi clip 30 giây, quay trong 2 ngày, ưu tiên ánh sáng tự nhiên.
Cần bản dọc cho TikTok và bản ngang cho YouTube.

Deadline đợt 1: trước khai trương 2 tuần."""

MARKUP_CHARACTER_BRIEF = """Ngân sách < 1.5 tỷ & đã duyệt sơ bộ.

Hạng mục: sân khấu & âm thanh, 2 camera, livestream đa nền tảng.
Điều kiện: nếu vượt < 10% thì báo trước, > 10% phải ký phụ lục."""

# One deal per pipeline stage worth looking at, so the board is never
# empty and drag-and-drop has somewhere to go. Budgets deliberately
# differ (A1): identical figures would make the per-column totals
# unreadable as totals.
DEALS = [
    {
        "title": "TVC Tết 2027",
        "stage": "Brief Received",
        "project_type": "TVC",
        "estimated_budget": 220_000_000,
        "positioning": "Brand",
    },
    {
        "title": "Social series - 6 tập",
        "stage": "Breakdown",
        "project_type": "Social Video",
        "estimated_budget": 90_000_000,
        "positioning": "Bridge",
    },
    {
        "title": "Phim doanh nghiệp Vinamilk",
        "stage": "Negotiation",
        "project_type": "TVC",
        "estimated_budget": 150_000_000,
        "positioning": "Cash",
    },
    # -- the walkthrough rows (#122) ------------------------------------
    #
    # Every stage occupied, both ends included. A pipeline sitting
    # entirely in Quote Sent is the most realistic shape for a busy week
    # and the least useful one to check against: every row gets the same
    # weighting, so a reader that ignored stage entirely would still
    # draw a plausible screen.
    #
    # Values are round triệu on purpose. A job's costs can be messy
    # because nobody adds those up by hand; a deal's value is the one
    # figure somebody checks with their eyes, and 220 + 500 is
    # checkable where 187.436.000 + 462.119.000 is an act of faith.
    {
        "title": "Viral clip - chuỗi cà phê",
        "stage": "De-brief",
        "project_type": "Social Video",
        "estimated_budget": 500_000_000,
        "positioning": "Bridge",
        "brief": MULTI_PARAGRAPH_BRIEF,
    },
    {
        "title": "Livestream sự kiện ra mắt",
        "stage": "Quote Sent",
        "project_type": "Event",
        "estimated_budget": 1_200_000_000,
        "positioning": "Cash",
        "brief": MARKUP_CHARACTER_BRIEF,
    },
    # A real value that has to be weighted to nothing. Deliberately not
    # an empty one: an empty Lost deal contributes zero because it has
    # nothing to contribute, so a reader that had forgotten about Lost
    # entirely would still show the right total. This one is only zero
    # if the weighting is real.
    {
        "title": "Booking KOL - huỷ giữa chừng",
        "stage": "Lost",
        "project_type": "Social Video",
        "estimated_budget": 300_000_000,
        "positioning": "Cash",
        # Not optional: Deal.validate_lost_reason throws without one, so
        # a Lost row with no reason is a seed that dies rather than a
        # deal that is quietly wrong. It also gives the lost-reason
        # breakdown a row to count.
        "lost_reason": "Price",
        "lost_note": "Khách chốt với bên báo giá thấp hơn 20%.",
    },
    # No budget and no quote. It has to contribute nothing without
    # breaking whatever it lands in - an unpriced enquiry is a normal
    # thing for a studio to be carrying, not a malformed record.
    {
        "title": "Thư mời hợp tác - chưa rõ ngân sách",
        "stage": "Brief Received",
        "project_type": "TVC",
        "estimated_budget": None,
    },
]


# The deal A1 ages past the weekly ritual's seven days, so the amber
# badge is visible the moment the stack boots.
STALE_DEAL = "Phim doanh nghiệp Vinamilk"

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
    # A second line with no invoice behind it, so the exposure tile can
    # show both of its states at once: this one gets a replacement
    # invoice recorded against it, the one above does not. With a single
    # no-invoice line the screen can only ever show one of them, and a
    # tile that has never rendered a covered row is a tile whose covered
    # branch nobody has looked at.
    {
        "description": "Thuê bãi đỗ xe đoàn",
        "qty1": 1, "qty1_unit": "ngày", "qty2": 2, "qty2_unit": "buổi",
        "unit_price": 1_500_000, "tax_type": "Không hoá đơn",
    },
    {
        # Deliberately in no package: quoted as its own line.
        "description": "Flycam",
        "qty1": 1, "qty2": 1,
        "unit_price": 6_000_000, "tax_type": "Công ty", "markup_pct": 15,
    },
]

# The deal T7 wins and turns into a job - kept out of DEALS so the
# pipeline board still shows a deal per interesting stage.
WON_DEAL = "MV - Hà Anh Tuấn"

# Two rounds used: the walkthrough's own third round is the chargeable one.
REVISION_NOTES = [
    "Khách muốn đổi nhạc nền và cắt bớt 10 giây",
    "Sửa màu tối hơn ở cảnh cuối",
]

# How the seeded job gets paid - a three-stage collection, so the
# walkthrough sees more than the standard 50/50 a conversion creates.
MILESTONES = [
    {"title": "Đặt cọc", "pct": 30, "trigger_stage": "Pre-production"},
    {"title": "Sau quay", "pct": 40, "trigger_stage": "Post-production"},
    {"title": "Nghiệm thu", "pct": 30, "trigger_stage": "Client sign-off"},
]

PACKAGES = [
    {"title": "Human resources", "description": "Director, DOP and crew for three shoot days"},
    {"title": "Equipment", "description": "Camera, lighting, grip and unit catering"},
]

# The float T8 leaves open on that job, and the receipts against it. The
# arithmetic is meant to be checkable by hand on the walkthrough:
# 20.000.000 advanced − 11.350.000 spent = 8.650.000 to hand back.
ADVANCE = 20_000_000

FLOAT_EXPENSES = [
    {"amount": 6_000_000, "category": "Human resources",
     "description": "Ứng tiền đạo diễn ngày 1"},
    {"amount": 4_500_000, "category": "Equipment",
     "description": "Thuê thêm đèn ngoài kế hoạch"},
    # No category on purpose: spend nobody quoted still has to be visible.
    {"amount": 850_000, "description": "Gửi xe + cà phê đoàn"},
]

# The founder's own transfer to a vendor: job spend that settles no float.
DIRECT_PAYMENT = {
    "amount": 24_000_000,
    "category": "Equipment",
    "description": "Chuyển khoản thẳng cho vendor thiết bị",
    "paid_from": "Company",
}


def run():
    """Build the base data, then every registered feature seed."""
    ensure_founder_role()
    # Before anything that moves money. Every posting in #99/#100 asks
    # cash_account.default_account() where the money went, and that
    # returns None until a Cash Account exists and Settings names one -
    # at which point ledger.job_expense() returns None too and the
    # advances, expenses and settlements below run and post *nothing*.
    # The flows would look seeded and /finance/accounts would be empty.
    ensure_cash_accounts()
    company = ensure_company()
    ensure_contact(company)
    deals = [ensure_deal(company, **deal) for deal in DEALS]
    priced = ensure_breakdown(deals[1])

    for name, seed in FEATURE_SEEDS.items():
        seed(priced)
        print(f"seeded: {name}")

    frappe.db.commit()
    print(f"seed complete - {len(deals)} deals on {company}")


# -- base --


# Two, not one, because the accounts screen exists to tell them apart:
# with a single account every posting lands in the same column and a
# reader that ignored the account field would draw the same page.
#
# The bank account is FIRST on purpose. CashAccount.after_insert calls
# adopt_as_default, so whichever account is created first becomes where
# every flow posts - and that should be the account a client transfer
# and a vendor payment both move through, not the petty cash box. Order
# here is behaviour, not presentation.
CASH_ACCOUNTS = [
    {
        "account_name": "Tài khoản VCB",
        "note": "Seed data - tài khoản công ty, nơi tiền khách chuyển về.",
    },
    {
        "account_name": "Quỹ tiền mặt",
        "note": "Seed data - tiền mặt tại văn phòng.",
    },
]


def ensure_cash_accounts():
    """The accounts every money flow posts against, and the default.

    The default is normally set for us: the first account inserted
    adopts it. This still checks afterwards, because a site can reach a
    state the insert path cannot fix - a stored default naming an
    account somebody deleted - and in that state every posting resolves
    to None and the flows run silently doing nothing.

    Idempotent like the rest of the file.
    """
    from auraos.auraos.doctype.cash_account.cash_account import (
        DEFAULT_FIELD,
        default_account,
    )

    for row in CASH_ACCOUNTS:
        if frappe.db.exists("Cash Account", {"account_name": row["account_name"]}):
            continue
        frappe.get_doc({"doctype": "Cash Account", **row}).insert(ignore_permissions=True)

    # default_account() is the reader's own answer, dangling link check
    # included, so this asks the same question the postings will ask.
    if default_account():
        return
    fallback = frappe.db.get_value(
        "Cash Account", {"account_name": CASH_ACCOUNTS[0]["account_name"]}
    )
    frappe.db.set_single_value("AuraOS Settings", DEFAULT_FIELD, fallback)


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
    explicit Has Role rows - Administrator's implicit access to
    everything does not count. On a fresh site nobody holds it, so
    seeding a deal would fail before it began.
    """
    if founder_holders():
        return
    user = frappe.get_doc("User", "Administrator")
    user.append_roles("Founder")
    user.save(ignore_permissions=True)


def founder():
    """Whoever holds the Founder role - Administrator on a fresh site."""
    holders = founder_holders()
    return holders[0] if holders else "Administrator"


def ensure_deal(
    company,
    title,
    stage,
    project_type=None,
    estimated_budget=150_000_000,
    positioning=None,
    brief=None,
    lost_reason=None,
    lost_note=None,
):
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
            "project_type": project_type,
            "estimated_budget": estimated_budget,
            "positioning": positioning,
            # Plain text in, HTML out, through the same converter the
            # migration patch uses. Written here rather than left for
            # the patch because Frappe runs a patch once per site and
            # has already run this one anywhere that has migrated - a
            # seeded brief would stay plain text in a Text Editor field
            # and render its paragraphs as one line.
            "brief": from_plain_text(brief) if brief else None,
            "lost_reason": lost_reason,
            "lost_note": lost_note,
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

    Without this the silence badge cannot be seen at all - the founder
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


# T6.1a: who the quote says it is from.
#
# No logo - a seeded image would be a binary blob in the repo for a
# walkthrough that is better served by the founder uploading the real
# one and watching the letterhead change. Every text field is filled so
# the empty-field rules can be checked by *clearing* one on the preview,
# which is the direction that actually needs seeing.
COMPANY_IDENTITY = {
    "company_name": "Aura Productions",
    "tax_code": "0312345678",
    "address": "12 Nguyễn Huệ, Quận 1, TP.HCM",
    "phone": "028 3822 1234",
    "email": "hello@auraproductions.example",
    "website": "auraproductions.example",
    "bank_name": "Vietcombank",
    "bank_account_number": "0071000123456",
    "bank_account_name": "CONG TY TNHH AURA PRODUCTIONS",
    "signatory_name": "Nguyễn Anh Chung",
    "signatory_title": "Giám đốc",
}


def seed_t6_1a_company_identity(deal_name):
    """T6.1a: a letterhead on the quote page and PDF.

    Written only where nothing is set: a preview where the founder has
    typed their real details in must not have them overwritten by the
    next boot.
    """
    settings = frappe.get_doc("AuraOS Settings")
    for field, value in COMPANY_IDENTITY.items():
        if not settings.get(field):
            settings.set(field, value)
    settings.save(ignore_permissions=True)


def seed_t8_money_out(deal_name):
    """T8: the same job mid-shoot, holding a float nobody has settled.

    Everything the money screen shows needs rows behind it: a float with
    receipts against it, spend that landed outside every package, and a
    direct payment that has to *not* move the float.
    """
    job = frappe.db.get_value("Job", {"title": WON_DEAL})
    if not job or frappe.db.exists("Job Advance", {"job": job}):
        return

    frappe.get_doc(
        {
            "doctype": "Job Advance",
            "job": job,
            "recipient": founder(),
            "amount": ADVANCE,
            "transferred_on": frappe.utils.add_days(frappe.utils.today(), -6),
            "note": "Tiền mặt cho đoàn quay",
        }
    ).insert(ignore_permissions=True)

    for offset, expense in enumerate(FLOAT_EXPENSES + [DIRECT_PAYMENT]):
        frappe.get_doc(
            {
                "doctype": "Job Expense",
                "job": job,
                "paid_by": founder(),
                "spent_on": frappe.utils.add_days(frappe.utils.today(), offset - 5),
                **expense,
            }
        ).insert(ignore_permissions=True)


def seed_t10_payment_milestones(deal_name):
    """T10: a three-stage collection with one payment gone quiet.

    A converted job starts with both milestones unrequested and the
    deposit only just due, so a fresh stack would show no nudge at all -
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
    planned = [row["title"] for row in MILESTONES]
    if [row.title for row in job.payment_milestones] == planned:
        return

    job.set("payment_milestones", [dict(row) for row in MILESTONES])
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


# T11: a contract template with a hole in it on purpose.
#
# The walkthrough has to see the thing this ticket is about - a field
# that could not be filled, marked on the page - and a template where
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
    "Người liên hệ: {{contact.full_name}} - {{contact.phone}}",
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
    reviewable text in a diff instead of an opaque blob - and so the
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
            "notes": "Starter sample - replace with the company's real contract.",
        }
    ).insert(ignore_permissions=True)


def seed_a1_stale_deal(deal_name):
    """A1: one deal aged past seven days in its stage.

    The board's age badge turns amber past STALE_DAYS, and a fresh seed
    is all zero-day deals - without this row the walkthrough could only
    be told the badge exists, the hole the T6 silence badge fell into.
    The *stage log* is backdated, not `modified`: the badge reads when
    the deal entered its current stage.
    """
    stale = frappe.db.exists("Deal", {"title": STALE_DEAL})
    if not stale:
        return
    last = frappe.get_all(
        "Deal Stage Log",
        filters={"parenttype": "Deal", "parent": stale},
        fields=["name"],
        order_by="idx desc",
        limit=1,
    )
    if not last:
        return
    frappe.db.set_value(
        "Deal Stage Log",
        last[0].name,
        "changed_on",
        frappe.utils.add_to_date(frappe.utils.now_datetime(), days=-12),
        update_modified=False,
    )


# A5 round 2: a freelancer contract in the library, written through the
# web-editor path (template_source → built .docx) - so the walkthrough
# sees both the editor's product and the freelancer picker on a job.
FREELANCER_CONTRACT = "Hợp đồng cộng tác viên (mẫu)"

# HTML, as the rich editor writes it - headings, bold labels, alignment
# all survive into the built .docx via html_to_docx.
FREELANCER_CONTRACT_SOURCE = "".join(
    [
        '<h2 style="text-align: center">HỢP ĐỒNG CỘNG TÁC VIÊN</h2>',
        "<p>Hôm nay, ngày {{today.day}} tháng {{today.month}} năm "
        "{{today.year}}, chúng tôi gồm:</p>",
        "<p><strong>BÊN A (Bên thuê):</strong> công ty - theo giấy phép kinh doanh.</p>",
        "<p><strong>BÊN B (Cộng tác viên):</strong> {{freelancer.full_name}}</p>",
        "<ul>",
        "<li>CCCD: {{freelancer.id_number}}</li>",
        "<li>Mã số thuế cá nhân: {{freelancer.tax_code}}</li>",
        "<li>Địa chỉ: {{freelancer.permanent_address}}</li>",
        "<li>Điện thoại: {{freelancer.phone}}</li>",
        "</ul>",
        "<h3>Điều 1. Công việc</h3>",
        "<p>Bên B tham gia sản xuất: {{job.title}} (mã {{job.code}}).</p>",
        "<h3>Điều 2. Thanh toán</h3>",
        "<p>Thù lao theo thỏa thuận, khấu trừ 10% thuế TNCN theo quy định.</p>",
        "<p>Chuyển khoản: {{freelancer.bank_name}} - "
        "{{freelancer.bank_account_number}}.</p>",
        "<p><strong>ĐẠI DIỆN BÊN A</strong>          <strong>BÊN B</strong></p>",
    ]
)


def seed_a5_freelancer_contract(deal_name):
    if frappe.db.exists(
        "Paperwork Template", {"template_name": FREELANCER_CONTRACT}
    ):
        return
    frappe.get_doc(
        {
            "doctype": "Paperwork Template",
            "template_name": FREELANCER_CONTRACT,
            "template_source": FREELANCER_CONTRACT_SOURCE,
            "notes": "Written in the web editor - edit it on the Paperwork page.",
        }
    ).insert(ignore_permissions=True)


def seed_123_no_invoice_exposure(deal_name):
    """#123: the founder's tax tile with all three of its states showing.

    Exposure is money that moved, so every row here is a real payment
    rather than a quoted line. #11 seeded this by writing a second
    expense to stand for the replacement invoice, which is what #123
    removed: a covering expense adds its amount to the job's cost and
    posts a ledger entry for money that never moved. The invoice is a
    field on the payment now.

    Three states, because a tile whose covered branch has never rendered
    is a branch nobody has looked at:

    1. **Stated and exposed** - paid against a Không hoá đơn line, no
       invoice. This is the number the founder is meant to act on.
    2. **Stated and covered** - the same, with an invoice number on it,
       so it drops out of the exposure and into the covered total.
    3. **Unattributed** - the float expenses seeded by T8 name no line
       at all, so they count as at risk until somebody points them at
       one. Nothing extra is needed for this; it is already true, and it
       is the half the founder asked to be counted rather than hidden.

    Deliberately smaller than the float spend beside it, so the tile's
    two halves are told apart by eye rather than by arithmetic.
    """
    job = frappe.db.get_value("Job", {"title": WON_DEAL})
    if not job or frappe.db.exists("Job Expense", {"cost_line": ["is", "set"]}):
        return

    doc = frappe.get_doc("Job", job)
    lines = {
        row.description: row
        for row in doc.cost_lines
        if row.tax_type == "Không hoá đơn"
    }
    exposed = lines.get("Ăn uống đoàn")
    covered = lines.get("Thuê bãi đỗ xe đoàn")
    if not exposed or not covered:
        return

    payments = [
        {
            "amount": 4_200_000,
            "description": "Cơm đoàn 3 ngày quay",
            "cost_line": exposed.name,
            "invoice_no": None,
        },
        {
            "amount": 3_000_000,
            "description": "Bãi đỗ xe đoàn",
            "cost_line": covered.name,
            # The paper arrived. Recorded on the payment, not as a
            # second one - the founder did not pay the bãi đỗ xe twice.
            "invoice_no": "0001234",
        },
    ]
    for offset, payment in enumerate(payments):
        frappe.get_doc(
            {
                "doctype": "Job Expense",
                "job": job,
                "paid_by": founder(),
                "paid_from": "Company",
                "spent_on": frappe.utils.add_days(frappe.utils.today(), -4 - offset),
                **payment,
            }
        ).insert(ignore_permissions=True)


# Far enough back to be a different calendar month whatever day the seed
# runs on. A month is the bucket every finance report counts in, and one
# month of activity cannot tell a sum from a passthrough.
LAST_MONTH_DAYS = 40


def seed_108_a_second_month(deal_name):
    """#108: activity in two months, and months with none between.

    The profit and loss runs along whatever range is asked for, so a
    site whose every record landed this week renders one populated row
    and a column of zeros. That looks the same whether the report works
    or whether it is quietly bucketing everything into today - and the
    zeroed rows, with a dash where the margin cannot be measured, are
    the case a founder should see working before they trust the screen.
    """
    job = frappe.db.get_value("Job", {"title": WON_DEAL})
    if not job:
        return
    spent_on = frappe.utils.add_days(frappe.utils.today(), -LAST_MONTH_DAYS)
    if frappe.db.exists("Job Expense", {"job": job, "spent_on": spent_on}):
        return

    frappe.get_doc(
        {
            "doctype": "Job Expense",
            "job": job,
            "paid_by": founder(),
            "amount": 12_000_000,
            "spent_on": spent_on,
            "paid_from": "Company",
            "category": "Equipment",
            "description": "Đặt cọc thiết bị tháng trước",
        }
    ).insert(ignore_permissions=True)

    # Money in that month too, so the row is a profit and not just a
    # loss - a P&L whose only non-empty month is negative never shows a
    # positive margin, and the margin pill has two tones.
    paid = [
        row for row in frappe.get_doc("Job", job).payment_milestones
        if row.status == "Paid"
    ]
    if paid:
        frappe.db.set_value(
            "Job Payment Milestone", paid[0].name, "paid_on", spent_on,
            update_modified=False,
        )


def seed_106_paper_states(deal_name):
    """#106: a paper in each status, including one walked back.

    Draft, awaiting signature and signed are three different rows on the
    paperwork screen, and the interesting one is the fourth case: a
    paper that was Signed and is not any more. That is the transition
    the status field exists to survive, and it cannot be seen on a site
    where every paper has only ever moved forwards.
    """
    from auraos.api import set_paper_status
    from auraos.lib.paper_status import AWAITING_SIGNATURE, DRAFT, SIGNED

    papers = frappe.get_all("Generated Paper", pluck="name", order_by="creation asc")
    if len(papers) < 3:
        return
    # Already walked: the third paper only reads Draft again after this
    # has run, because a generated paper starts with no status at all.
    if frappe.db.get_value("Generated Paper", papers[2], "status") == DRAFT:
        return

    # Through the endpoint, not through db.set_value. The doctype carries
    # status_changed_by and status_changed_on, and a status written
    # straight into the column leaves both empty - a paper that changed
    # hands with no record of who or when, which is the same defect as a
    # ledger row inserted by hand instead of posted by a flow.
    set_paper_status(papers[0], SIGNED)
    set_paper_status(papers[1], AWAITING_SIGNATURE)
    set_paper_status(papers[2], SIGNED)
    set_paper_status(papers[2], DRAFT)


FEATURE_SEEDS = {
    "T6 quote delivery": seed_t6_quote_delivery,
    "T6.1a company identity": seed_t6_1a_company_identity,
    "T7 job in production": seed_t7_job_in_production,
    "T8 money out": seed_t8_money_out,
    "T10 payment milestones": seed_t10_payment_milestones,
    "T11 paperwork templates": seed_t11_paperwork,
    "A1 stale deal": seed_a1_stale_deal,
    "A5 freelancer contract": seed_a5_freelancer_contract,
    # Ordered after T8 and T10: both of these read records those seeds
    # create, and a dict preserves insertion order.
    "#123 no-invoice exposure": seed_123_no_invoice_exposure,
    "#108 a second month": seed_108_a_second_month,
    "#106 paper states": seed_106_paper_states,
}

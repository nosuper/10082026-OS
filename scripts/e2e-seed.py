"""Deterministic records for the disposable Playwright site.

**The seed is the fixture.** A spec that builds its own records is
testing its own setup; asserting against a shape it did not create is
the property that makes a spec worth having. The exception is a record
the spec must create and destroy to prove a derivation - #121's
cover-then-uncover is one, because proving a status is derived means
writing and deleting the thing it derives from.

**Every ensure_* states what the data is rather than returning early
when it exists.** A spec is allowed to edit a seeded value; the seed's
job is to be able to put it back. Returning early makes it an
initialiser, and then the first spec that mutates something leaves a
site no reseed corrects - which is how a budget nobody seeded survived
on this site for weeks, and how one cost line made two suites disagree.

**Nothing here is backdated with `db.set_value`.** Writing a date that a
posting derives from, without letting the posting re-derive, is what
made the walkthrough dataset report the same money in July on one screen
and August on another. Dates are written through the record's own save
so the ledger reconciles against them.
"""

import os

import frappe
from frappe.utils import add_months, today

from auraos.auraos.doctype.job.job import STAGES, CLOSED_STAGE, create_from_deal
from auraos.api import generate_job_paperwork, set_paper_status


PRODUCER = os.environ["E2E_PRODUCER_USER"]
PRODUCER_PASSWORD = os.environ["E2E_PRODUCER_PASSWORD"]
COMPANY = "Playwright Client"
DEAL = "Playwright Existing Deal"

# The deal above stays at Brief Received because the deals specs assert
# against it. Jobs are converted from their own deals, so seeding a job
# never has to move a deal another spec is reading.
JOB_DEAL = "Playwright Job Deal"
CLOSED_DEAL = "Playwright Closed Deal"

# What run() prints once the site is written and committed, and the only
# thing scripts/e2e.sh will accept as proof the seed finished. Spelled by
# concatenation on both sides so neither the checker nor the checked can
# match itself: this file is read into the console as text, and a literal
# here would travel with it.
SEEDED_MARKER = "AURAOS_SEED" "_OK"

# Where a seeded job is open. Taken from the head of STAGES rather than
# written out, for the same reason CLOSED_STAGE is taken from its tail:
# insert a stage before Pre-production and this moves with it.
OPEN_STAGE = STAGES[0]

# Two accounts, because one cannot show money moving between places.
BANK = "Playwright Bank"
PETTY = "Playwright Petty Cash"

# Two templates, and the papers below are generated one from each -
# deliberately not two from the same one. A generated file is named
# `{job} - {template} - {stamp}` at MINUTE resolution and job_paperwork()
# ties a status to a file by that name, so two papers off one template
# inside the same minute share a name and show one status between them.
# A person generating two papers hits different minutes and never sees
# it; a seed makes both at once, which is what a seed is for. Same defect
# as the file_url dedupe, arriving through the name instead of the url.
TEMPLATE = "Playwright Contract"
HANDOVER_TEMPLATE = "Playwright Biên bản nghiệm thu"

# The quoted line whose treatment carries tax exposure to whatever spends
# against it, and the ordinary one beside it - the contrast is the point:
# an expense against NO_INVOICE_LINE is exposed, one against INVOICED_LINE
# is not, and that is what makes attribution lower the figure.
NO_INVOICE_LINE = "Playwright location fees"
INVOICED_LINE = "Playwright director"

# Months are relative so the finance screens' default ranges always
# contain them. The gap is the assertion: expenses in this month, the
# collected milestone two months back, and empty months between.
SPENT_ON = today()
COLLECTED_ON = add_months(today(), -2)


def ensure_user():
    if not frappe.db.exists("User", PRODUCER):
        frappe.get_doc(
            {
                "doctype": "User",
                "email": PRODUCER,
                "first_name": "Playwright",
                "last_name": "Producer",
                "user_type": "System User",
                "send_welcome_email": 0,
            }
        ).insert(ignore_permissions=True)

    user = frappe.get_doc("User", PRODUCER)
    has_role = frappe.db.exists(
        "Has Role",
        {"parent": PRODUCER, "parenttype": "User", "role": "Producer"},
    )
    if not has_role:
        user.append_roles("Producer")
    user.new_password = PRODUCER_PASSWORD
    user.save(ignore_permissions=True)


def ensure_company():
    name = frappe.db.exists("Party Company", {"company_name": COMPANY})
    if name:
        return name
    return frappe.get_doc(
        {"doctype": "Party Company", "company_name": COMPANY}
    ).insert(ignore_permissions=True).name


def ensure_deal(company):
    """The seeded deal, restored to its seeded values rather than merely
    created once.

    Same argument as ensure_breakdown below, which was given it first
    because the breakdown line was the one implicated at the time. This
    function kept the older shape - return early if the deal exists - and
    that leaves `estimated_budget` as an initialiser: the deals spec edits
    it to 12.500.000 and never puts it back, so from the second run
    onwards the site carries a budget nobody seeded and no reseed ever
    corrects it. Nothing asserted on it, so it drifted quietly.

    A spec that changes a seeded value is allowed to. The seed's job is
    to be able to say what the state *is*.
    """
    existing = frappe.db.exists("Deal", {"title": DEAL})
    if existing:
        deal = frappe.get_doc("Deal", existing)
        deal.company = company
        deal.stage = "Brief Received"
        deal.deal_owner = PRODUCER
        # #117 lets a spec move this deal to Lost, which writes a reason
        # and a note the doctype then requires to stay consistent with the
        # stage. Clearing them here is part of saying what the state is.
        deal.lost_reason = None
        deal.lost_note = None
        deal.estimated_budget = 10_000_000
        deal.save(ignore_permissions=True)
        return
    frappe.get_doc(
        {
            "doctype": "Deal",
            "title": DEAL,
            "company": company,
            "stage": "Brief Received",
            "deal_owner": PRODUCER,
            "estimated_budget": 10_000_000,
        }
    ).insert(ignore_permissions=True)


def ensure_breakdown():
    """One priced line and one package, so the breakdown editor has
    something on screen the moment the spec opens it (A2).

    Restores the seeded figures rather than returning early when a line
    already exists. Two suites share this site and the Vue breakdown
    spec edits this very line to 5.500.000 before putting it back - so
    when that spec dies in between, as it does whenever the box is busy
    enough for a five second wait to lapse, the restore never runs and
    the React suite reads 2 x 5.500.000 and fails on a number nobody
    typed. A seed that only creates is an initialiser; a seed has to be
    able to say what the state is, not just that some state exists.
    """
    deal = frappe.get_doc("Deal", {"title": DEAL})
    if deal.cost_lines:
        line = deal.cost_lines[0]
        line.qty1 = 1
        line.qty2 = 2
        line.unit_price = 4_000_000
        line.tax_type = "Cá nhân"
        line.markup_pct = 20
        deal.save(ignore_permissions=True)
        return
    deal.append(
        "packages",
        {"title": "Crew", "description": "Playwright crew package"},
    )
    deal.append(
        "cost_lines",
        {
            "description": "Playwright director",
            "package": "Crew",
            "qty1": 1,
            "qty2": 2,
            "unit_price": 4_000_000,
            "tax_type": "Cá nhân",
            "markup_pct": 20,
        },
    )
    deal.save(ignore_permissions=True)


def ensure_cash_accounts():
    """Two accounts, and one of them made the default.

    **Setting the default is not decoration.** `cash_account.default_account()`
    returns None when the setting is unset, and Job.on_update says what
    that means in its own comment: a company with no cash account posts
    nothing at all. So without this, every flow below runs, saves
    cleanly, and posts silently nothing - and a spec would read the empty
    ledger as a defect in the ledger rather than as a seed that never
    gave it anywhere to write.
    """
    for name in (BANK, PETTY):
        if not frappe.db.exists("Cash Account", name):
            frappe.get_doc(
                {"doctype": "Cash Account", "account_name": name}
            ).insert(ignore_permissions=True)

    settings = frappe.get_doc("AuraOS Settings")
    if settings.default_cash_account != BANK:
        settings.default_cash_account = BANK
        settings.save(ignore_permissions=True)


def ensure_won_deal(title, company):
    """A deal at Won, so it can become a job.

    Its own deal rather than DEAL, which the deals specs read at Brief
    Received. Two quoted lines with different tax treatments: the
    Không hoá đơn one is what carries exposure to the money spent
    against it, and the ordinary one is the control that proves
    attribution can also take money *out* of the figure.
    """
    existing = frappe.db.exists("Deal", {"title": title})
    deal = (
        frappe.get_doc("Deal", existing)
        if existing
        else frappe.get_doc({"doctype": "Deal", "title": title})
    )
    deal.company = company
    deal.stage = "Won"
    deal.deal_owner = PRODUCER
    deal.estimated_budget = 60_000_000

    if not deal.packages:
        deal.append("packages", {"title": "Crew", "description": "Playwright crew"})
    wanted = {
        INVOICED_LINE: {"tax_type": "Cá nhân", "unit_price": 4_000_000},
        NO_INVOICE_LINE: {"tax_type": "Không hoá đơn", "unit_price": 3_000_000},
    }
    have = {row.description: row for row in deal.cost_lines}
    for description, values in wanted.items():
        row = have.get(description)
        if row is None:
            row = deal.append(
                "cost_lines",
                {"description": description, "package": "Crew", "qty1": 1, "qty2": 1},
            )
        row.qty1 = 1
        row.qty2 = 1
        row.markup_pct = 20
        row.package = "Crew"
        for field, value in values.items():
            setattr(row, field, value)

    deal.save(ignore_permissions=True)
    return deal


def ensure_job(title, company):
    """The job a deal became, with its quoted lines carried across, and
    stated open rather than returned as found.

    Saying the stage is what makes a second pass behave like a first.
    This function returned the existing job untouched, which was fine on
    a disposable site and wrong everywhere else, in two ways that only
    show up on the second seed:

    - **It let the closed job stay closed.** `ensure_closed_job` calls
      this and then writes expenses, and `reject_change_after_close` is
      stage-only - no dirty check, no no-op check - so it throws on a
      re-seed that changes nothing. That throw landed before `run()`
      reached `commit()`, so the whole second pass rolled back and the
      re-seed restored nothing at all (#135).
    - **It let the open job drift.** A spec that moves this job leaves it
      moved, and "an open job beside a closed one" quietly becomes two
      closed jobs. Nothing raises; the contrast just stops existing,
      which is the failure the pair is here to prevent.

    Reopening here rather than inside `ensure_closed_job` because the
    stage is this function's to state either way: the job it returns is
    open, and the caller that wants it closed says so afterwards.
    """
    deal = ensure_won_deal(title, company)
    existing = frappe.db.exists("Job", {"deal": deal.name})
    if not existing:
        return create_from_deal(deal.name)
    job = frappe.get_doc("Job", existing)
    if job.stage != OPEN_STAGE:
        job.stage = OPEN_STAGE
        job.save(ignore_permissions=True)
    return job


def line_named(job, description):
    """The carried cost line's child-row name.

    Expenses link to a line by that name, and it must be a line on this
    job - a name from another job would quietly attribute the money, and
    on a Không hoá đơn line quietly move a tax exposure with it.
    """
    for row in job.cost_lines:
        if row.description == description:
            return row.name
    return None


def ensure_expense(job, description, **values):
    """One expense, stated rather than merely created.

    Keyed on its description within the job, so re-running restores the
    amount, the date, the link and the invoice number a spec may have
    edited.
    """
    existing = frappe.db.exists(
        "Job Expense", {"job": job.name, "description": description}
    )
    expense = (
        frappe.get_doc("Job Expense", existing)
        if existing
        else frappe.get_doc(
            {"doctype": "Job Expense", "job": job.name, "description": description}
        )
    )
    expense.spent_on = SPENT_ON
    expense.category = "Crew"
    # Explicitly cleared, not merely defaulted: a spec that sets an
    # invoice number and does not remove it must not leave the next run
    # reading a covered row where the seed says uncovered.
    expense.cost_line = None
    expense.invoice_no = None
    for field, value in values.items():
        setattr(expense, field, value)
    expense.save(ignore_permissions=True)
    return expense


def ensure_exposure_states(job):
    """The three states the exposure tile distinguishes, plus the control.

    - **stated, uncovered** - spends against a Không hoá đơn line and has
      no invoice. Exposure the company knows about.
    - **stated, covered** - the same, with an invoice number on the
      payment. Paper obtained after the fact, so it leaves the figure.
    - **unattributed** - names no quoted line, so nobody has said what it
      is. Counted as exposed because understating is the error that costs
      money at an audit, and reported apart because "we know" and "nobody
      has said" are different degrees of knowledge.
    - **the control** - spends against the ordinary line, and is not in
      the tile at all. Without it a spec cannot tell a working exclusion
      from a tile that simply lists everything.
    """
    exposed_line = line_named(job, NO_INVOICE_LINE)
    ordinary_line = line_named(job, INVOICED_LINE)

    ensure_expense(
        job,
        "Playwright location cash",
        amount=1_500_000,
        paid_from="Company",
        cost_line=exposed_line,
    )
    ensure_expense(
        job,
        "Playwright location cash, invoiced later",
        amount=900_000,
        paid_from="Company",
        cost_line=exposed_line,
        invoice_no="PW-INV-0001",
    )
    ensure_expense(
        job,
        "Playwright uncategorised cash",
        amount=400_000,
        paid_from="Company",
    )
    ensure_expense(
        job,
        "Playwright director fee",
        amount=4_000_000,
        paid_from="Company",
        cost_line=ordinary_line,
    )


def ensure_float(job):
    """An advance, and a payment out of it that must post nothing.

    Seeded as a pair with the Company-paid expenses above, and that
    pairing is the assertion. `paid_by_company()` posts for Company and
    stays silent for Advance, so on a site where *nothing* posted, "the
    float posted nothing" would be true for the wrong reason. The
    comparison is what proves the rule: same job, same shape, one entry
    between them.
    """
    existing = frappe.db.exists(
        "Job Advance", {"job": job.name, "recipient": PRODUCER}
    )
    advance = (
        frappe.get_doc("Job Advance", existing)
        if existing
        else frappe.get_doc(
            {"doctype": "Job Advance", "job": job.name, "recipient": PRODUCER}
        )
    )
    advance.amount = 5_000_000
    advance.transferred_on = SPENT_ON
    advance.save(ignore_permissions=True)

    ensure_expense(
        job,
        "Playwright taxi out of the float",
        amount=250_000,
        paid_from="Advance",
    )


def ensure_collected_milestone(job):
    """One milestone collected two months back.

    Written on the row and saved through the job, never with
    `db.set_value`: Job.on_update posts collections after the save, so
    the ledger entry derives its date from what the milestone now claims.
    Setting the column directly is what made one screen say July and
    another say August about the same money.
    """
    job = frappe.get_doc("Job", job.name)
    if not job.payment_milestones:
        return job
    first = job.payment_milestones[0]
    first.status = "Paid"
    first.paid_on = COLLECTED_ON
    first.invoice_no = "PW-MS-0001"
    for row in job.payment_milestones[1:]:
        # Stated, so a spec that collects a second one is undone.
        row.status = "Not requested"
        row.paid_on = None
    job.save(ignore_permissions=True)
    return job


def ensure_closed_job(company):
    """A second job, closed, so "closed vs open" has two sides.

    One job cannot demonstrate a distinction: a margin-by-job screen
    that had lost the split entirely would still satisfy a spec that
    only ever sees an open job.

    **Order matters and it is not arbitrary.** #123 locks a job's
    spending once it reaches Complete, so the expenses go on first and
    the close comes last. Reordering these two statements raises an
    exception that reads as a bug in this seed, when it is the lock
    doing its job.

    **That ordering is within one pass, and persistence reverses it.**
    On a second seed the close already happened, in a previous run,
    before this function is entered at all - so the expenses below are
    written against a job that is already Complete and the lock throws
    however carefully these two statements are ordered here. What makes
    the order hold across passes is `ensure_job` stating the job open,
    which happens on the line below (#135). Guarding the axis you are
    looking along is not the same as bounding the hazard.
    """
    job = ensure_job(CLOSED_DEAL, company)
    ensure_expense(
        job,
        "Playwright closed job spend",
        amount=2_000_000,
        paid_from="Company",
        cost_line=line_named(job, INVOICED_LINE),
    )
    job = frappe.get_doc("Job", job.name)
    if job.stage != CLOSED_STAGE:
        job.stage = CLOSED_STAGE
        job.save(ignore_permissions=True)
    return job


def ensure_paperwork(job):
    """Two templates, and a paper generated from each.

    Two templates rather than two papers from one: the generated file is
    named `{job} - {template} - {stamp}` at minute resolution, and
    job_paperwork() ties a status to a file by that name. Two papers off
    one template inside a minute therefore share a name and show one
    status between them - invisible to a person, who never generates two
    in the same minute, and guaranteed for a seed, which makes both at
    once.

    The template is seeded as HTML source rather than an uploaded .docx:
    Paperwork Template.validate() builds the file from that source, so
    there is no fixture binary in the repo and the template is a real
    one.

    The paper goes through `api.generate_job_paperwork`, not
    `paperwork_template.generate`. **That distinction is the whole of
    whether the Paperwork tab has anything on it.** `generate()` fills
    the docx and attaches a File to the job; the registry row the screen
    lists is written by `_register_paper`, which only the endpoint
    calls. Seeding with `generate()` alone produces a file that exists,
    hangs off the job, and is invisible from the screen under test -
    a spec would then be reading an empty registry and calling it a bug
    in the registry.

    The placeholder is a field that actually fills from the job, so a
    spec asserting placeholders resolve finds a filled value rather than
    braces that came back untouched.
    """
    contract = ensure_template(
        TEMPLATE,
        "<p>Hợp đồng cho {{job.title}}</p>"
        "<p>Khách hàng: {{client.company_name}}</p>"
        "<p>Mã số thuế: {{client.tax_code}}</p>",
    )
    handover = ensure_template(
        HANDOVER_TEMPLATE,
        "<p>Biên bản nghiệm thu - {{job.title}}</p>"
        "<p>Bên A: {{client.company_name}}</p>",
    )

    # Both statuses stated, because the contrast is the fixture: one
    # paper waiting and one settled. A single status is a presence, and
    # a presence cannot show that the screen reads the field at all.
    ensure_paper(job, contract, "Draft")
    ensure_paper(job, handover, "Signed")

    return contract


def ensure_template(name, source):
    """One template, seeded as HTML rather than an uploaded .docx.

    Paperwork Template.validate() builds the .docx from template_source,
    so this is a real template with a real file behind it and no fixture
    binary enters the repo.
    """
    existing = frappe.db.exists("Paperwork Template", {"template_name": name})
    template = (
        frappe.get_doc("Paperwork Template", existing)
        if existing
        else frappe.get_doc({"doctype": "Paperwork Template", "template_name": name})
    )
    template.disabled = 0
    template.template_source = source
    template.save(ignore_permissions=True)
    return template


def ensure_paper(job, template, status):
    """One generated paper, at the status this seed says it is in.

    The status is an argument with no default because both papers need
    stating and only one of them used to be. The handover's `Signed` was
    the only asserted status by accident: the contract took whatever
    `generate_job_paperwork` happened to leave and a re-seed restored
    neither, so a spec that signed the contract left it signed for every
    later pass (#134).

    Set through `set_paper_status` rather than written on the doc, so
    `status_changed_by` and `status_changed_on` are filled by the
    controller that owns them instead of left null for a screen to
    render as a blank.
    """
    existing = frappe.db.exists(
        "Generated Paper", {"job": job.name, "template": template.name}
    )
    if not existing:
        generate_job_paperwork(job.name, template.name)
        existing = frappe.db.exists(
            "Generated Paper", {"job": job.name, "template": template.name}
        )
    if not existing:
        return None
    paper = frappe.get_doc("Generated Paper", existing)
    if paper.status != status:
        set_paper_status(paper.name, status)
        paper = frappe.get_doc("Generated Paper", existing)
    return paper


def ensure_library_document():
    """The SOP, via the patch that owns its text.

    Calling the patch rather than restating the document here: it is
    idempotent, it keys off the title, and it is the one place the SOP's
    139 lines live. A copy in this file would be a second copy to keep
    in step, and the first one to drift.
    """
    from auraos.patches import seed_sop_deals_library_document

    seed_sop_deals_library_document.execute()


def run():
    company = ensure_company()
    ensure_user()
    ensure_deal(company)
    ensure_breakdown()

    ensure_cash_accounts()

    job = ensure_job(JOB_DEAL, company)
    ensure_exposure_states(job)
    ensure_float(job)
    ensure_collected_milestone(job)
    ensure_paperwork(job)

    ensure_closed_job(company)
    ensure_library_document()

    frappe.db.commit()

    # Said last, and only here. `bench console` exits 0 even when the code
    # it ran raised, so scripts/e2e.sh cannot read success from the exit
    # status and reads it from this line instead. After commit() rather
    # than before it: everything above rolls back if anything throws, and
    # a marker printed before the commit would announce a site that was
    # never written (#133).
    print(SEEDED_MARKER)

"""Deterministic records for the disposable Playwright site."""

import os

import frappe


PRODUCER = os.environ["E2E_PRODUCER_USER"]
PRODUCER_PASSWORD = os.environ["E2E_PRODUCER_PASSWORD"]
COMPANY = "Playwright Client"
DEAL = "Playwright Existing Deal"


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


def run():
    ensure_user()
    ensure_deal(ensure_company())
    ensure_breakdown()
    frappe.db.commit()

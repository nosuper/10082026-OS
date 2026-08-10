import frappe

# The two operating roles of the company. Permissions on sensitive
# DocTypes are granted to Founder only; the permission regression tests
# in each sensitive DocType's test module are the proof that Producer
# cannot see them.
ROLES = ("Founder", "Producer")

# The party role tags a company or person can carry. A fixed vocabulary:
# growing it is a founder Desk chore, not a code change.
PARTY_ROLES = ("Client", "Vendor", "Freelancer")

# Founder-confirmed starting vocabularies (issue #21). Both are
# founder-expandable doctypes, not frozen Selects — the founder asked
# for the source list to keep growing.
DEAL_SOURCES = ("Website", "Referral", "Zalo", "Expo")
PROJECT_TYPES = ("TVC", "Social Video", "Event", "Documentary")


def after_install():
    create_roles()
    create_party_roles()
    create_deal_vocabularies()


def after_migrate():
    # Seeds must also reach sites that installed the app before the
    # seed existed; every seeding function here is idempotent.
    create_roles()
    create_party_roles()
    create_deal_vocabularies()


def create_roles():
    for role_name in ROLES:
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc(
                {"doctype": "Role", "role_name": role_name, "desk_access": 1}
            ).insert(ignore_permissions=True)


def create_party_roles():
    for role_name in PARTY_ROLES:
        if not frappe.db.exists("Party Role", role_name):
            frappe.get_doc(
                {"doctype": "Party Role", "role_name": role_name}
            ).insert(ignore_permissions=True)


def create_deal_vocabularies():
    for source_name in DEAL_SOURCES:
        if not frappe.db.exists("Deal Source", source_name):
            frappe.get_doc(
                {"doctype": "Deal Source", "source_name": source_name}
            ).insert(ignore_permissions=True)
    for type_name in PROJECT_TYPES:
        if not frappe.db.exists("Project Type", type_name):
            frappe.get_doc(
                {"doctype": "Project Type", "type_name": type_name}
            ).insert(ignore_permissions=True)

import frappe

# The two operating roles of the company. Permissions on sensitive
# DocTypes are granted to Founder only; the permission regression tests
# in each sensitive DocType's test module are the proof that Producer
# cannot see them.
ROLES = ("Founder", "Producer")

# The third kind of user (T7.1, issue #41): a designer, editor or
# colourist who opens the job they are working on and sees no money.
# One role, not one per craft - the craft is a field on the task, so
# the money boundary is proven blind once rather than once per trade.
CREW_ROLE = "Crew"

# The party role tags a company or person can carry. A fixed vocabulary:
# growing it is a founder Desk chore, not a code change.
PARTY_ROLES = ("Client", "Vendor", "Freelancer")

# Founder-confirmed starting vocabularies (issue #21). Both are
# founder-expandable doctypes, not frozen Selects - the founder asked
# for the source list to keep growing.
DEAL_SOURCES = ("Website", "Referral", "Zalo", "Expo")
PROJECT_TYPES = ("TVC", "Social Video", "Event", "Documentary")

# The trades a job task can belong to. A starting vocabulary, not a
# frozen one: Craft is a founder-expandable doctype like Deal Source.
CRAFTS = ("Producing", "Camera", "Editing", "Design", "Colour", "Sound")


def after_install():
    create_roles()
    create_party_roles()
    create_deal_vocabularies()
    create_crafts()


def after_migrate():
    # Seeds must also reach sites that installed the app before the
    # seed existed; every seeding function here is idempotent.
    create_roles()
    create_party_roles()
    create_deal_vocabularies()
    create_crafts()


def create_roles():
    for role_name in (*ROLES, CREW_ROLE):
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc(
                {"doctype": "Role", "role_name": role_name, "desk_access": 1}
            ).insert(ignore_permissions=True)


def _seed(doctype, fieldname, values):
    for value in values:
        if not frappe.db.exists(doctype, value):
            frappe.get_doc({"doctype": doctype, fieldname: value}).insert(
                ignore_permissions=True
            )


def create_party_roles():
    _seed("Party Role", "role_name", PARTY_ROLES)


def create_deal_vocabularies():
    _seed("Deal Source", "source_name", DEAL_SOURCES)
    _seed("Project Type", "type_name", PROJECT_TYPES)


def create_crafts():
    _seed("Craft", "craft_name", CRAFTS)

import frappe

# The two operating roles of the company. Permissions on sensitive
# DocTypes are granted to Founder only; the permission regression tests
# in each sensitive DocType's test module are the proof that Producer
# cannot see them.
ROLES = ("Founder", "Producer")

# The party role tags a company or person can carry. A fixed vocabulary:
# growing it is a founder Desk chore, not a code change.
PARTY_ROLES = ("Client", "Vendor", "Freelancer")


def after_install():
    create_roles()
    create_party_roles()


def after_migrate():
    # Seeds must also reach sites that installed the app before the
    # seed existed; every seeding function here is idempotent.
    create_roles()
    create_party_roles()


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

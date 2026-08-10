import frappe

# The two operating roles of the company. Permissions on sensitive
# DocTypes are granted to Founder only; the permission regression tests
# in each sensitive DocType's test module are the proof that Producer
# cannot see them.
ROLES = ("Founder", "Producer")


def after_install():
    create_roles()


def create_roles():
    for role_name in ROLES:
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc(
                {"doctype": "Role", "role_name": role_name, "desk_access": 1}
            ).insert(ignore_permissions=True)

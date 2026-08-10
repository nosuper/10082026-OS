"""Shared helpers for Frappe site tests."""

import frappe


def make_test_user(email, role=None):
    """Create (or fetch) a System User; grant the app role if given."""
    if not frappe.db.exists("User", email):
        frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": email.split("@")[0].title(),
                "user_type": "System User",
                "send_welcome_email": 0,
            }
        ).insert(ignore_permissions=True)
    if role:
        user = frappe.get_doc("User", email)
        user.append_roles(role)
        user.save(ignore_permissions=True)

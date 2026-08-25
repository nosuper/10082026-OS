import frappe


def get_context(context):
    # The React SPA shell is Jinja-rendered; hand it a CSRF token so the app
    # can make POST calls (saves, inserts, logout) as a logged-in user.
    csrf_token = frappe.sessions.get_csrf_token()
    frappe.db.commit()
    context.csrf_token = csrf_token
    return context

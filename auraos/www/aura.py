import frappe


def get_context(context):
    # The SPA shell is Jinja-rendered; hand it a CSRF token so
    # frappe-ui's frappeRequest can make POST calls (saves, inserts).
    csrf_token = frappe.sessions.get_csrf_token()
    frappe.db.commit()
    context.csrf_token = csrf_token
    return context

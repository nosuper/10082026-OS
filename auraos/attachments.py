"""Who may hang a file on what.

Core File permissions let any System User create a File and point it at
any document, so every doctype in this app that accepts attachments
needs a gate of its own. The gate is one rule - you may attach to what
you may write - and it lives here rather than on any one doctype
because the second doctype to need it (Job, once T11 started attaching
generated paperwork) proved it was never a Deal rule.
"""

import frappe

# Attaching to any of these requires write permission on the document
# itself. A doctype absent from this set falls back to core Frappe's
# permissions, which is only safe where the doctype is not sensitive.
GUARDED = ("Deal", "Job")


def check_attachment_permission(doc, method=None):
    """doc_events hook on File: attaching requires write on the target."""
    if doc.flags.ignore_permissions:
        return
    if doc.attached_to_doctype in GUARDED:
        frappe.has_permission(
            doc.attached_to_doctype, "write", doc=doc.attached_to_name, throw=True
        )

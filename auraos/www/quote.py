"""The public quote page: /quote/<token>.

Guest-visible by design - the client has no account, the token is the
authorization (spec #2, story 20). The page never reads the Deal; it
renders the frozen Deal Quote snapshot through the whitelist in
auraos.lib.quote, so internals cannot reach a client even by mistake.
"""

import frappe

from auraos.auraos.doctype.deal_quote.deal_quote import (
    client_context,
    find_by_token,
    pdf_url,
    record_open,
)


def get_context(context):
    # A quote page must never be cached: the open event is the point.
    context.no_cache = 1
    context.no_sidebar = 1
    context.no_breadcrumbs = 1

    quote = find_by_token(frappe.form_dict.token)
    if not quote:
        # A client following a dead link deserves a sentence, not a
        # stack trace - so this renders our own page at 404 rather than
        # throwing into Frappe's error handler (T6 walkthrough).
        context.not_found = True
        context.title = "Quote not found"
        context.http_status_code = 404
        frappe.local.response["http_status_code"] = 404
        return context

    context.update(client_context(quote))
    context.title = quote.title or "Quote"
    context.pdf_url = pdf_url(quote.token)

    record_open(quote.name, via="Page")
    return context

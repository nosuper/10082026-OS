"""The public quote page: /quote/<token>.

Guest-visible by design — the client has no account, the token is the
authorization (spec #2, story 20). The page never reads the Deal; it
renders the frozen Deal Quote snapshot through the whitelist in
auraos.lib.quote, so internals cannot reach a client even by mistake.
"""

import frappe

from auraos.auraos.doctype.deal_quote.deal_quote import (
    client_context,
    record_open,
    resolve_token,
)


def get_context(context):
    # A quote page must never be cached: the open event is the point.
    context.no_cache = 1
    context.no_sidebar = 1
    context.no_breadcrumbs = 1

    quote = resolve_token(frappe.form_dict.token)
    context.update(client_context(quote))
    context.title = quote.title or "Quote"
    context.pdf_url = f"/api/method/auraos.api.quote_pdf?token={quote.token}"

    record_open(quote.name, via="Page")
    return context

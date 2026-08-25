"""Deal.brief became a Text Editor field, so its plain text becomes HTML (#120).

Every brief already on file was typed into a textarea, where a blank line
was a paragraph and a newline was a line break. Rendered as HTML without
conversion, all of that collapses to one run-on paragraph. The words
survive either way, which is exactly why nobody would notice: the loss
turns up months later, when somebody opens an old deal and finds their
own writing has become a wall.

Conversion is auraos.lib.richtext's, so this and any future caller agree
about what a line break was.

Re-runnable. A brief that already carries a block tag has been through
an editor and is left alone, so running this twice does not wrap a
paragraph in a paragraph.
"""

import frappe

from auraos.lib.richtext import from_plain_text, looks_like_html


def execute():
    rows = frappe.get_all("Deal", filters={"brief": ["is", "set"]}, fields=["name", "brief"])
    for row in rows:
        if not row.brief or looks_like_html(row.brief):
            continue
        # update_modified=False: rewriting how a brief is stored is not
        # somebody editing that deal today, and `modified` is what a
        # stale-save check reads.
        frappe.db.set_value(
            "Deal", row.name, "brief", from_plain_text(row.brief), update_modified=False
        )

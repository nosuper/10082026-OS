"""Papers generated before #106 read as Draft, not as blank.

The Select's default is a document-layer default: Frappe applies it when
a document is *created*, and every registry row already in the table was
created before the field existed. Whether the column's own DDL default
reaches those rows depends on how the schema change happens to be
applied, which is not a thing to leave "has the client signed it?"
resting on - a blank there would read as a fourth state, and would drop
out of a filter on any of the three.

So: default for new rows, this patch for the old ones. Idempotent - it
only touches rows with nothing in the column.
"""

import frappe

from auraos.lib.paper_status import DRAFT


def execute():
    frappe.db.sql(
        """
        UPDATE `tabGenerated Paper`
        SET status = %s
        WHERE status IS NULL OR status = ''
        """,
        DRAFT,
    )

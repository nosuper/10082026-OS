"""Reading AuraOS Settings, where 0 is a setting and not an absence.

Both nudges (quote silence, payment terms) treat 0 as "never nudge", so
every reader has to tell a deliberate 0 from a value nobody has set.
`frappe.db.get_single_value` cannot: it casts a missing Int to 0. And a
value *is* missing more often than it looks - a Single's row is only
written when its document is saved, so a field added by a later
migration has no stored value on any existing site, and reading it as a
deliberate 0 would quietly switch the nudge off.

Reading the settings document instead leaves an unset field as None,
which is the whole point.
"""

import frappe


def setting(fieldname, default):
    """One AuraOS Settings value, or the house default if none is stored."""
    value = frappe.get_cached_doc("AuraOS Settings").get(fieldname)
    return default if value is None else value

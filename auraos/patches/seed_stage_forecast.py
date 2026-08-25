"""Write the forecast dials the founder has never been asked for (#102).

AuraOS Settings is a Single, and a Single's row is only written when its
document is saved - so a field or a table added by a migration has no
stored value on any site that already exists. A `default` declared on
the doctype is not applied retroactively either. That is a trap twice
over here:

- an unwritten Int reads back as **0**, and a forecast silently weighted
  at 0% renders as an empty screen that reads "no pipeline" rather than
  "not configured";
- **Lost is legitimately 0**, so a stored 0 and an unwritten field are
  indistinguishable by value. Nothing downstream can tell them apart, and
  no reader should be asked to try.

So the rows are written, explicitly, once, here - the same way the three
backfills beside this file wrote what a migration could not. After this
runs, every stage of the Deal Select has a row a founder can see and
edit in Settings, and a 0 in the probability column means somebody chose
it.

Idempotent, and safe to re-run: only stages with no row are appended, so
a founder who has since set their own probability - or deliberately
deleted a row - is never overwritten by a second pass. The house
defaults come from auraos.lib.forecast rather than being retyped, so
this patch and the module that reads the table cannot disagree about
what "unconfigured" is worth.
"""

import frappe

from auraos.lib import forecast


def execute():
    settings = frappe.get_single("AuraOS Settings")
    stored = {(row.stage or "").strip() for row in settings.stage_forecast}
    missing = [stage for stage in forecast.STAGES if stage not in stored]
    if not missing:
        return

    for stage in missing:
        win_probability_pct, lead_days = forecast.DEFAULT_RULES[stage]
        settings.append(
            "stage_forecast",
            {
                "stage": stage,
                "win_probability_pct": win_probability_pct,
                "lead_days": lead_days,
            },
        )
    settings.flags.ignore_permissions = True
    settings.save()

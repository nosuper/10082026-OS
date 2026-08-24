# ADR 0003: Renaming a vocabulary value migrates; removing one in use is refused

- Status: accepted
- Date: 2026-08-25
- Ticket: #29 (T3.5), following the T3.1+T3.2 walkthrough answers of 2026-08-10

## Context

T3.5 moves the managed vocabularies - deal **sources** and **project
types** - out of the Desk and onto the SPA Settings screen, because the
walkthrough found the Desk entry point undiscoverable: the founder could
not find where to add a source at all.

Putting add / rename / remove in front of the two operating roles forces
an answer to a question the Desk never asked out loud: **what happens to
the deals already holding a value when that value is renamed or
removed?** A Link field can only end up in one of four states, and three
of them lose information:

1. the deals follow the value across (migrate),
2. the deals are blanked,
3. the deals keep a name that no longer exists (a dangling link),
4. the change is refused.

Sources and project types are exactly the fields the "where does our
work actually come from, and what kind of work is it" question will be
asked of in six months. Silently blanking or dangling them makes that
question unanswerable, and worse, unanswerable without saying so.

## Decision

**Renaming migrates.** "Expo" becoming "Trade show" is the same value
under a better name, so `rename_vocabulary_value` renames the record and
every deal on it follows. Nothing is blanked and nothing dangles. The
rename also writes the row's own value field, because these DocTypes are
named from it (`autoname: field:source_name`).

**Renaming never merges.** Renaming onto a name already in the list is
refused. A merge would rewrite the source of every deal on the *target*
value as well, and nobody decides that by typing in a rename box. The
way to collapse two values is to move the deals deliberately and then
remove the empty one.

**Removing a value in use is refused.** A value on even one deal cannot
be removed. The refusal names the value, counts the deals holding it,
and points at the two ways forward: rename it if what it needs is a
better name, or clear it off those deals first if it really was never a
source. Clearing the field on a deal is a deliberate act on that deal;
deleting a list value is not.

**The margin floor stays founder-only.** Opening the Settings page to
the producer for the sources list changes nothing about the numbers on
that page: the page draws sections per permission, and the settings
single is still founder-read/write only.

## Consequences

- The lists only ever grow through use. An abandoned value with deals on
  it stays visible in Settings (labelled with its count) until someone
  moves those deals. That is the intended cost: the alternative hides
  the fact that history is being edited.
- The vocabulary lists are now renameable DocTypes (`allow_rename: 1`),
  so `frappe.rename_doc` carries the Link updates.
- Every new Link field pointing at a managed list must be added to that
  list's `used_by` in `auraos/lib/vocabulary.py`, or removal would stop
  seeing it. The seam is deliberately explicit about this rather than
  scanning the schema, so the omission is a code review away from being
  caught.
- Tags are not covered here. They stay open-creation from the deal form
  for both operating roles (walkthrough answer), and nothing links to a
  tag but the deal's own child table.

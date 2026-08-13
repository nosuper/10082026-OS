# A5 acceptance walkthrough — do the admin pages warn you before the paperwork does?

**Purpose:** decide whether ticket [#61 (A5: Admin pages UX pass)](https://github.com/nosuper/10082026-OS/issues/61) is complete, or send it back for fixes.

**From:** Claude (the implementing agent) — **To:** the founder — **How your answers will be used:** the next Claude session reads this file top to bottom, treats every passed step as a verified acceptance criterion, turns each design answer into either code or a follow-up ticket, and acts on the verdict at the bottom.

## Context

The last Phase A ticket — the three quiet pages. The theme: **say what's missing before it bites.**

- **Contacts** gets a *Paperwork* column: exactly which contract fields a record lacks (companies: tax code / address / bank; people: CCCD / tax code / bank). These are the same holes that print as «thiếu: …» markers on a generated contract — now visible where they can be fixed. Tabs show counts; typing `missing` in search filters to every incomplete record.
- **Settings**: the three warning switches (margin floor, quote silence, payment terms) wear a **"currently off"** chip when 0. While testing I also set the live values on this site: floor 20, terms 7 — so the floor warning and the overdue strip are now ON.
- **Paperwork**: the "Fills:" line wraps as chips instead of running off the card.

## How to answer

**Rough effort:** ~5 minutes.

## 0. Before you start

**http://192.168.1.94:8000/aura** — Ctrl+Shift+R.

## 1. Contacts — the holes

**Do this:** open Contacts. Read the Paperwork column on both tabs; type `missing` into search; click a flagged record and fill one missing field; save.
**Expect:** the label updates (e.g. "missing address, bank" → "missing bank"); counts on the tabs; search finds the incomplete ones.

Pass / fail:

>

## 2. Settings — no more silent zeros

**Do this:** open Settings.
**Expect:** margin floor shows 20 and payment terms 7 (I saved them); silence 5. Set any of them to 0 → an amber **currently off** chip appears next to the label.

Pass / fail:

>

## 3. Paperwork — chips

**Do this:** open Paperwork, look at the template's "Fills:" line.
**Expect:** wrapping chips inside the card, nothing running off the edge; unknown placeholders (if any) amber with a warning icon.

Pass / fail:

>

## 4. Phase A retrospective

This closes Phase A (A1–A5). Before I move to Phase B (tier + positioning fields) and C (hardening gate): across the whole app today, what's the roughest remaining edge you'd want smoothed before your team touches it?

>

## Verdict

- [ ] **GO** — merge it; Phase B/C starts
- [ ] **GO with notes**
- [ ] **NO-GO** — fix the failed steps first

>

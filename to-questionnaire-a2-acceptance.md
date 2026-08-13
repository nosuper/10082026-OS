# A2 acceptance walkthrough - can you price a job without fighting the screen?

**Purpose:** decide whether ticket [#55 (A2: Breakdown editor UX pass)](https://github.com/nosuper/10082026-OS/issues/55) is complete, or send it back for fixes.

**From:** Claude (the implementing agent) - **To:** the founder - **How your answers will be used:** the next Claude session reads this file top to bottom, treats every passed step as a verified acceptance criterion, turns each design answer into either code or a follow-up ticket, and acts on the verdict at the bottom.

## Context

Your longest-sitting screen. Three complaints drove this ticket: your A1 verdict on raw digits (it applied hardest here - Unit Price was a raw number field on the screen where money is typed most), the 18-column table that always scrolled sideways, and Save living at the top of a long page.

What changed: **Unit Price and package Override format as you type** (gõ `5250000` → ô hiện `5.250.000`). An Override that was never set displays **blank with "auto"**, not a confusing `0`. The four metadata columns (Item Category, Cost Phase, Source Type, Source Contact) hide behind a **"Detail columns"** menu - off by default, your choice remembered - so the table fits the screen. The **header is sticky**: title, stage, Save and an **"Unsaved changes"** flag never scroll away, and **Ctrl+S (Cmd+S)** saves from anywhere. Stage chip colors now match the board. Row buttons are real icons; the tax dropdown no longer truncates "Không hoá đơn".

Automation: CI green on the branch (pure pytest, site suite, Playwright including a new breakdown spec that pins the formatted money field, the dirty→save flow, and detail-column persistence). Pricing math untouched - parity tests against your xlsx unchanged.

## How to answer

**Rough effort:** ~7 minutes. Answer in the `>` blocks; if a step fails, say what you saw.

## 0. Before you start

Test at **http://192.168.1.94:8000/aura** - login `Administrator / admin`, **Ctrl+Shift+R first**. Open **Social series - 6 tập → Breakdown** (hover card → ₫ icon).

## 1. The table fits

**Do this:** open the breakdown on your usual screen size.
**Expect:** no sideways scrolling; you see Description, Package, quantities, Unit Price, Tax, MF/Markup and the three computed money columns at once.

Pass / fail:

> Pass with notes (round 1): datalist pickers felt like bare dialogs; Qty/Unit headers ambiguous; no autosave or missing-field warning; Unit Price/Override misaligned; quote lacks qty/unit; asked whether the playbook's three quote-detail levels are met (no - moved to A3). All UI notes shipped in round 2.

## 2. Money reads as money

**Do this:** click a Unit Price and type `5250000`. Then clear an Override on a package, then type `9000000` into it, then clear it again.
**Expect:** every keystroke shows dots (`5.250.000`); an empty Override reads `auto`, never `0`; Variance turns amber only while a real override is set.

Pass / fail:

> Pass, except: the founder DOES quote 0-đồng packages (discount/FOC) - restored in round 2 via has_price_override.

## 3. Detail columns

**Do this:** open "Detail columns", tick Item Category and Cost Phase. Reload the page.
**Expect:** the columns appear, and are still there after the reload. Untick → gone again.

Pass / fail:

> Pass.

## 4. Sticky save + dirty flag

**Do this:** change any number, scroll to the bottom, look at the header. Press Ctrl+S.
**Expect:** "Unsaved changes - Ctrl+S saves" appears the moment you edit and vanishes when the save lands; the Save button never left your sight while scrolling.

Pass / fail:

> Pass ("oke").

## 5. Design questions

### 5.1 One capability quietly changed

With the new Override field, typing `0` clears it (auto) - an override of literally **0 đồng** (a package shown to the client as free) is no longer possible from this screen. The engine still supports it. Have you ever priced a package at 0 on purpose (khuyến mãi/miễn phí), or is this fine to leave as-is?

> Yes - FOC/discount packages are real; shipped in round 2.

### 5.2 What still hurts

After A1+A2, what's the next worst thing about pricing a job in here - anything slower than your xlsx still?

> UX still not easy to read/operate, columns unclear - addressed in round 2 with numbered headers, right-aligned inputs and the tinted computed zone.

## Round 2 - the founder's answers (in-session, 2026-08-12) and what shipped

Steps 3, 4 passed; 1 and 2 passed **with notes**, all addressed the same
day (commit "A2 round 2"): Item Category and Package became query-style
comboboxes (click shows options, typing filters, free text still grows
the vocabulary); Qty/Unit headers numbered 1/2; every numeric input
right-aligned under its header; computed columns tinted behind a
divider; **autosave** ~2.5s after the last edit with a red-border
warning while a line is missing its description; **0-đồng override
restored** - a new `has_price_override` Check carries "is this set", so
FOC/discount packages price at 0 on the client quote (5.1 answered:
yes, the founder quotes free packages).

**Still open, moved to A3:** quantities/units are not shown on the
client-facing quote, and the playbook's three quote-detail levels (lump
sum / grouped by package / full AICP line-by-line) are not selectable -
today every quote renders as grouped packages only. A3 (client quote
page) will carry a per-deal "detail level" choice.

## Verdict

- [x] **GO** - merge it; A3 (client quote page) starts
- [ ] **GO with notes**
- [ ] **NO-GO** - fix the failed steps first

> GO given in-session 2026-08-12 ("ok tiếp tục bước tiếp theo") after round 2 was verified on the dev stack. Quote detail levels move to A3.

# A1 acceptance walkthrough - does the deals screen answer Monday's questions at a glance?

**Purpose:** decide whether ticket [#53 (A1: Deals board & table UX pass)](https://github.com/nosuper/10082026-OS/issues/53) is complete, or send it back for fixes.

**From:** Claude (the implementing agent) - **To:** the founder - **How your answers will be used:** the next Claude session reads this file top to bottom, treats every passed step as a verified acceptance criterion, turns each design answer into either code or a follow-up ticket, and acts on the verdict at the bottom.

## Context

This is the first ticket of **Phase A**: your go-live gate is UX, not looks - *"ít bước nhất, không phải nghĩ, không sợ bấm nhầm"* - with Monday/ClickUp as the bar. The deals screen goes first because it's the one you open every morning.

What changed: the board's columns now carry a colored dot, a count and a **budget total** (the playbook's 3X pipeline coverage is read off these); every card shows its budget and project type, and wears an **age badge** that turns amber once the deal has sat in one stage past 7 days - your weekly ritual, answered without a click. Both views gained **search and an owner filter**. The table pins its **Add** button so it can't scroll out of reach, right-aligns money, shows "1d/3h" style update times, and totals whatever the current filter shows. Dragging a card now highlights the column it's about to drop into, and card actions appear on hover instead of overflowing the card edge.

Automation is green: 267 pure pytest, the Frappe site suite (two new tests for the age endpoint; one pre-existing site-data failure noted for Phase C, also fails on clean main), the Playwright e2e suite, frontend build clean.

What automation cannot judge is the thing Phase A is about: **whether this is now faster and calmer than your spreadsheet.** That's this walkthrough.

## How to answer

**Rough effort:** about 10 minutes of clicking, plus the design questions.

Answer in the `>` blocks. Partial answers and "I don't know" are useful - flag anything you're unsure of rather than skipping it. If a step fails, say what you saw rather than only "no".

## 0. Before you start

The **preview stack** for this ticket is at **http://192.168.1.94:8001/aura** - login `Administrator` / `admin`.

**Hard-refresh first (Ctrl+Shift+R)** - the browser caches the old app otherwise.

The seed gives each deal a different budget (220tr / 90tr / 150tr) so the column totals are checkable by eye, and **Phim doanh nghiệp Vinamilk** enters the stack already 12 days deep in Negotiation.

## 1. The board - Monday morning in one look

### 1.1 Column headers

**Do this:** open the board, look only at the column headers.
**Expect:** each stage has a colored dot, a deal count, and a right-hand total (e.g. `220tr`). Hover a total → the exact figure.

_Why this matters: the playbook's weekly review starts with "how much is in each column vs the revenue target" - this row is meant to replace opening a spreadsheet to know it._

Pass / fail, and what you saw:

>

### 1.2 The amber badge

**Do this:** find the Vinamilk card in Negotiation.
**Expect:** an amber `11d`-ish badge on the card's bottom-right; hover it → "In Negotiation for 11 days". Other cards show a quiet gray `1d` or nothing.

Pass / fail:

>

### 1.3 Cards

**Do this:** read one card cold.
**Expect:** title, client, **budget**, project type, owner - no clipped text, nothing overflowing the card edge. Hover the card → a small ₫ icon appears top-right (Breakdown & Quote); on the Won card the `Job →` chip is always visible.

Pass / fail:

>

### 1.4 Drag with feedback

**Do this:** drag any card slowly across two or three columns before dropping it. Then drag it back.
**Expect:** whichever column you're over glows blue while you hold the card over it - you always know where the drop will land. Column totals update after the drop.

Pass / fail:

>

## 2. Search & filter (both views)

**Do this:** type `tvc` in the search box; then clear it and pick an owner in "All owners".
**Expect:** the board and table shrink to matching deals as you type - title, client name and project type all match; the count next to "Deals" and the column totals follow the filter.

Pass / fail:

>

## 3. The table

### 3.1 Add is always reachable

**Do this:** switch to Table, shrink the browser window until the table scrolls sideways, scroll fully left.
**Expect:** the **Add** button stays pinned at the right edge, always visible. The top row creates a deal from whatever you type (Enter in a text field also submits).

Pass / fail:

>

### 3.2 Reading a row

**Do this:** look at any row.
**Expect:** stage as a colored pill matching the board's colors; budget right-aligned in the money column; "Updated" as `1d` / `3h` (hover → the timestamp); a one-line hint *below* the table instead of a column repeating "Click a cell to edit"; the filtered count + total on the bottom-right.

Pass / fail:

>

### 3.3 Inline edit still calm

**Do this:** click a budget cell, change the number, press Enter. Click the title's pencil (appears on row hover) and rename inline. Press Esc mid-edit somewhere.
**Expect:** exactly what the hint line promises - Enter saves, Esc cancels, the dialog never opens unless you click the title itself.

Pass / fail:

>

## 4. Design questions

### 4.1 Language

The app's UI is English ("Deals", "Add", "Silent", "All owners") while the team, the docs and the data are Vietnamese. Before I polish the remaining screens: should the UI switch to Vietnamese, stay English, or mix (Vietnamese labels, English domain words like Deal/Job)?

_My read: a Vietnamese team hits "no thinking" faster in Vietnamese, and we have no foreign users on the horizon - but it touches every screen, so it's one decision, made once, now._

>

### 4.2 The bar

Put this screen next to Monday/ClickUp in your head. What still feels slower, noisier or more confusing than those - anything you'd fix before the team sees it?

>

### 4.3 What's next

A2 per the agreed order is the **breakdown editor** (your longest-sitting screen). Still right, or has clicking this preview changed your mind about what hurts most?

>

## Verdict

- [x] **GO** - merge it; A2 starts
- [ ] **GO with notes** - merge, and the notes above become follow-ups
- [ ] **NO-GO** - fix the failed steps first

> Answered in-session on 2026-08-12 (chat, not this file). Steps 1.3, 2,
> 3.1–3.3, 4.3 passed. Four fixes were requested and shipped the same
> day (commit 092ff7a): 1.1 "tr" → "triệu"; 1.2 "d" → "days"; 1.4 drag
> felt laggy → optimistic move on drop; 4.2 raw digits in money inputs
> confused → VndInput formats as typed. 4.1 decided: **UI stays English,
> data stays Vietnamese.** Founder verified the fixes on the dev stack
> and said "oke triển khai tiếp" - GO. A2 (breakdown editor) is next.

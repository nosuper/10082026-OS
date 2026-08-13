# Phase B acceptance walkthrough — does every deal know its tier before the data arrives?

**Purpose:** decide whether ticket [#63 (Phase B: Tier + positioning)](https://github.com/nosuper/10082026-OS/issues/63) is complete, or send it back for fixes.

**From:** Claude (the implementing agent) — **To:** the founder — **How your answers will be used:** the next Claude session reads this file top to bottom, treats every passed step as a verified acceptance criterion, turns each design answer into either code or a follow-up ticket, and acts on the verdict at the bottom.

## Context — round 2

Round 1 asked you to fill **two** fields; you called that confusing, and you were right. The playbook already holds the correlation (§2.2: *positioning segment → Tier 3 bất kể giá trị*), so now **positioning is the input, tier is the output**:

- The deal form asks **one** question — Positioning (Cash / Bridge / Brand) — the strategic call only you can make.
- **Tier derives itself** and shows as a live chip in the form: Brand (or a job type flagged as positioning-segment) → Tier 3 whatever it pays; otherwise the budget thresholds (50/200 triệu, Settings). It keeps tracking as budget or positioning change.
- You can still **pin** a tier by hand in the table (e.g. ≥2 shoot days → Tier 2 — a fact the system can't see). A pinned tier never gets re-derived; clearing it hands it back to the rules.

## How to answer

**Rough effort:** ~4 minutes. Test at **http://192.168.1.94:8000/aura**, Ctrl+Shift+R.

## 1. One question, tier follows live

**Do this:** open New Deal — type budget `30000000`, watch the Tier chip; change to `250000000`; then set Positioning to Brand with budget back at `30000000`.
**Expect:** chip reads Tier 1 → Tier 3 → Tier 3 (Brand wins over money), updating as you type. No tier select anywhere in the form.

Pass / fail:

>

## 2. Tier follows the deal, not just the form

**Do this:** save a deal at `30000000` (Tier 1); later edit it and raise the budget to `250000000`.
**Expect:** tier moves to Tier 3 by itself — it's derived, not frozen at creation.

Pass / fail:

>

## 3. Pinning by hand

**Do this:** in the deals **table**, set that deal's Tier column to Tier 2 (pretend it has 2 shoot days); then change its budget again.
**Expect:** Tier 2 stays — the form shows "pinned by hand". Clear the Tier cell (blank option) and the rules take it back.

Pass / fail:

>

## 4. The board reads it

**Do this:** look at the deals board and table.
**Expect:** tier chips on cards (T1 gray / T2 blue / T3 violet, positioning in the tooltip); Positioning column editable inline; Tier column only for pinning.

Pass / fail:

>

## 5. Your thresholds

**Do this:** Settings → Tier thresholds — change Tier 2 to `100000000`, save, open New Deal at `90000000`.
**Expect:** chip reads Tier 1. (Put it back after.)

Pass / fail:

>

## 6. Positioning-segment job types

Which Project Types should count as *đúng định vị* (auto Tier 3 even when Positioning is left empty)? Today none are flagged — tell me the list (e.g. TVC?) and I'll flag them, or you can tick "Positioning Segment" on the Project Type in the Desk yourself.

>

## Verdict

- [ ] **GO** — merge it; Phase C (hardening gate) starts
- [ ] **GO with notes**
- [ ] **NO-GO** — fix the failed steps first

>

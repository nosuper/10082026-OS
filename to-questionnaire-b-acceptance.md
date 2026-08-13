# Phase B acceptance walkthrough - does every deal know its tier before the data arrives?

**Purpose:** decide whether ticket [#63 (Phase B: Tier + positioning)](https://github.com/nosuper/10082026-OS/issues/63) is complete, or send it back for fixes.

**From:** Claude (the implementing agent) - **To:** the founder - **How your answers will be used:** the next Claude session reads this file top to bottom, treats every passed step as a verified acceptance criterion, turns each design answer into either code or a follow-up ticket, and acts on the verdict at the bottom.

## Context - round 3

Round 2 made positioning the input and tier the output. Round 3 adds your three requests: every classification dial now lives in **Settings** (thresholds, the cash/bridge/brand mix targets, and which job types count as positioning-segment), an **SOP link** sits under the Positioning field, and the em-dash sweep is ticket [#65](https://github.com/nosuper/10082026-OS/issues/65).

## How to answer

**Rough effort:** ~5 minutes. Test at **http://192.168.1.94:8000/aura**, Ctrl+Shift+R.

## 1. One question, tier follows live

**Do this:** open New Deal - type budget `30000000`, watch the Tier chip; change to `250000000`; then set Positioning to Brand with budget back at `30000000`.
**Expect:** chip reads Tier 1 → Tier 3 → Tier 3 (Brand wins over money), updating as you type. No tier select anywhere in the form.

Pass / fail:

>

## 2. The SOP is one click from the decision

**Do this:** under the Positioning select, click "SOP: cách đánh giá & phân loại deal".
**Expect:** a new tab with the classification SOP (Bước 1 positioning, Bước 2 tier, process-depth table); your half-filled form still open behind it. Is the SOP content right?

Pass / fail:

>

## 3. Tier follows the deal, and pinning still works

**Do this:** save a deal at `30000000` (Tier 1); raise its budget to `250000000` - tier should move to Tier 3 by itself. Then in the **table**, set its Tier to Tier 2 and change the budget again - Tier 2 stays ("pinned by hand" in the form). Clear the Tier cell and the rules take it back.

Pass / fail:

>

## 4. All the dials in Settings

**Do this:** Settings - the classification block now holds: tier thresholds, positioning mix targets (%), and checkboxes for positioning-segment job types. Change the mix to 60/25/15 and save; reopen New Deal.
**Expect:** the Positioning labels read ~60% / ~25% / ~15%, and the SOP page shows the same numbers. (Put it back after, or leave your real targets.)

Pass / fail:

>

## 5. Flag a positioning-segment type yourself

**Do this:** in that same Settings block, tick a job type you consider *đúng định vị* (e.g. TVC), save, then create a deal of that type at `10000000` with Positioning left empty.
**Expect:** chip reads Tier 3 - the type flag alone is enough.

Pass / fail:

>

## 6. Your real numbers

While you are in Settings: set the mix targets and tick the real positioning-segment types for the company today (they are yours to change each quarter). List what you ticked here so the record survives:

>

## Verdict

- [x] **GO** - merge it; Phase C (hardening gate) starts (founder, from chat 2026-08-13: "B is okay to go for now")
- [ ] **GO with notes**
- [ ] **NO-GO** - fix the failed steps first

>

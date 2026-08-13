# Phase B acceptance walkthrough — does every deal know its tier before the data arrives?

**Purpose:** decide whether ticket [#63 (Phase B: Tier + positioning)](https://github.com/nosuper/10082026-OS/issues/63) is complete, or send it back for fixes.

**From:** Claude (the implementing agent) — **To:** the founder — **How your answers will be used:** the next Claude session reads this file top to bottom, treats every passed step as a verified acceptance criterion, turns each design answer into either code or a follow-up ticket, and acts on the verdict at the bottom.

## Context

The last schema change before go-live: `tier` and `positioning` on every deal, so the quarterly reviews (margin by tier, 70/20/10 mix) have data from the first real deal. The tier suggests itself — positioning-segment job types are Tier 3 whatever they pay, then the budget thresholds (Settings, 50/200 triệu default) decide — and your explicit choice always wins. Positioning is yours alone to set.

## How to answer

**Rough effort:** ~4 minutes. Test at **http://192.168.1.94:8000/aura**, Ctrl+Shift+R.

## 1. The suggestion

**Do this:** create a deal with budget `30000000` — check its Tier in the dialog after saving. Repeat with `60000000` and `250000000`.
**Expect:** Tier 1 / Tier 2 / Tier 3, filled in by themselves.

Pass / fail:

>

## 2. Your word wins

**Do this:** on one of those deals, set Tier manually to something else and save; change the budget; save again.
**Expect:** your tier stays.

Pass / fail:

>

## 3. The board reads it

**Do this:** look at the deals board and table.
**Expect:** tier chips on cards (T1 gray / T2 blue / T3 violet, positioning in the tooltip); Tier and Positioning columns editable inline in the table.

Pass / fail:

>

## 4. Your thresholds

**Do this:** Settings → Tier thresholds — change Tier 2 to `100000000`, save, create a deal at `90000000`.
**Expect:** suggested Tier 1. (Put it back after.)

Pass / fail:

>

## 5. Positioning-segment job types

Which Project Types should count as *đúng định vị* (auto Tier 3)? Today none are flagged — tell me the list (e.g. TVC?) and I'll flag them, or you can tick "Positioning Segment" on the Project Type in the Desk yourself.

>

## Verdict

- [ ] **GO** — merge it; Phase C (hardening gate) starts
- [ ] **GO with notes**
- [ ] **NO-GO** — fix the failed steps first

>

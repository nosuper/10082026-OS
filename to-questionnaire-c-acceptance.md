# Phase C acceptance walkthrough - does the machine hold before we wire it to the world?

**Purpose:** decide whether ticket [#67 (Phase C: hardening gate)](https://github.com/nosuper/10082026-OS/issues/67) is complete, or send it back for fixes.

**From:** Claude (the implementing agent) - **To:** the founder - **How your answers will be used:** the next Claude session reads this file top to bottom, treats every passed step as a verified acceptance criterion, turns each design answer into either code or a follow-up ticket, and acts on the verdict at the bottom.

## Context

The gate before production wiring (D) and go-live (E). What happened in it:

- **§4 money law fixed**: a new job's default plan is now *Đặt cọc (không hoàn lại) 50% / Bắt đầu post 25% / Trước khi giao file 25%* - the balance falls due at the Delivery gate, money before files. The old default collected it after sign-off.
- **Full test suite green on the lived-in dev site** (355 site tests + 301 pure) - three tests that only passed on a pristine CI site were made data-proof.
- **One breakdown assembly** (lib/breakdown): the live editor and the saved deal now compute through the same code, pinned by 10 new pure tests.
- **Em-dash sweep** (#65) and the redo-vocabulary rename rode along.
- **A simulated deal ran end-to-end without a stumble** - I left the trail on dev for you to inspect: DEAL-0028 → quote v1 (sent, confirmed, 1 guest open) → Won → JOB-0029 (deposit paid, 10tr advanced, 8tr spent, 1 contract generated).

## How to answer

**Rough effort:** ~3 minutes. Test at **http://192.168.1.94:8000/aura**, Ctrl+Shift+R.

## 1. The money order of a new job

**Do this:** open **JOB-0029** → Money tab.
**Expect:** three milestones - deposit marked *không hoàn lại* and already Paid (33tr collected), *Bắt đầu post* at Post-production, *Trước khi giao file* at **Delivery** (not after sign-off). Does this default match how you actually want to be paid? If your standing split differs (40/30/30?), say so and it becomes the default.

Pass / fail:

> Pass (founder, 2026-08-13)

## 2. The simulated trail reads true

**Do this:** skim the trail: deal DEAL-0028 (T2 · Bridge chip), its quote link (v1, confirmed, 1 open), the job's stat strip (Collected 33tr / Uncollected 33tr / Spent 8tr of 40tr · 10tr advanced), and the generated contract listed under Paperwork.
**Expect:** every number agrees with every other screen; nothing feels mysterious.

Pass / fail:

> Fail-note (founder): "no job code so I can't see where DEAL-0028 is" - record codes are not visible/searchable in the lists. Fix follows the merge.

## 3. The dash

**Do this:** glance at any screen you use daily (board, job money, milestones).
**Expect:** no long dash "—" anywhere in the UI copy; empty money cells show "-".

Pass / fail:

> Pass (founder, 2026-08-13)

## Note for later phases (no action now)

Production-site settings (margin floor 20, silence 5, terms 7, tier thresholds, positioning rules) must be re-entered when the production site exists in Phase D - Frappe does not migrate Single defaults. Recorded in #67.

## Verdict

- [x] **GO** - merge it; Phase D (production wiring + backups) starts (founder, 2026-08-13 - with the record-code note above)
- [ ] **GO with notes**
- [ ] **NO-GO** - fix the failed steps first

>

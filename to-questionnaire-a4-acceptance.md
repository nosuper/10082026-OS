# A4 acceptance walkthrough — does the production side feel like the deals side now?

**Purpose:** decide whether ticket [#59 (A4: Jobs board & job money UX pass)](https://github.com/nosuper/10082026-OS/issues/59) is complete, or send it back for fixes.

**From:** Claude (the implementing agent) — **To:** the founder — **How your answers will be used:** the next Claude session reads this file top to bottom, treats every passed step as a verified acceptance criterion, turns each design answer into either code or a follow-up ticket, and acts on the verdict at the bottom.

## Context

The A1 treatment, applied to production: the jobs board gets stage color dots, **per-column quoted totals** ("102 triệu"), search, richer cards and the instant drag you asked for on deals. Every remaining money input in the app now formats as you type — the advance and expense amounts on the job page, and the **phone expense screen** used on set. Emoji became icons; the job header wears its stage color.

One thing I noticed while testing: the **overdue-payment strip** on the jobs board (the "tiền chưa thu" chaser) is currently silent on this site because `payment_terms_days` in Settings reads as unset. That's a settings task queued for the hardening phase, not a bug in this ticket — but if you want the strip visible today, set Payment terms days = 7 in Settings.

## How to answer

**Rough effort:** ~6 minutes. Answer in the `>` blocks.

## 0. Before you start

**http://192.168.1.94:8000/aura/jobs** — `Administrator / admin`, **Ctrl+Shift+R**.

## 1. The board

**Do this:** look at the Jobs board; drag the MV job to another stage and back.
**Expect:** colored dots per stage, "102 triệu" on the column holding the job, the card showing quoted total + revisions chip, the target column glowing while you hold the card over it, and the drop landing instantly.

Pass / fail:

>

## 2. Search

**Do this:** type `mv` (or the client's name) into Search jobs.
**Expect:** the board narrows as you type; the count next to "Jobs" follows.

Pass / fail:

>

## 3. Money inputs on the job page

**Do this:** open the MV job. In **Money out**, type `2000000` into the Advance amount; same in the Expenses row.
**Expect:** the field shows `2.000.000` as you type — same behavior as the breakdown editor now. (No need to actually record them.)

Pass / fail:

>

## 4. The phone screen

**Do this:** open **Log expense on phone →** (ideally on your actual phone via http://192.168.1.94:8000/aura — same login), type an amount one-handed.
**Expect:** the big amount field formats as you type, cursor lands in it on open, categories are one tap, Log button shows the amount.

Pass / fail:

>

## 5. What still hurts

Anything on the job page that still fights you — layout, ordering of the panels, wording?

>

## Round 2 — the job detail, reshaped like the market apps

Your note ("cải thiện UX phần job detail, bao gồm cả phần chi tiêu —
tham khảo các app tương tự") landed as a redesign:

- **Sticky header** (title · code · client · stage) and a **clickable
  production stepper** — the pipeline as a progress bar, one click to
  move the job.
- **Stat strip**: Quoted / Collected (with progress bar) / Uncollected
  (with overdue badge) / Spent (with advanced context) — the job's
  money before any scrolling.
- **Three tabs** — Production / Money / Paperwork — replace the long
  scroll; the Money tab carries a red dot while anything is overdue.
- **Budget bars** replace the "Where the money went" table: each
  category fills toward its quoted cost, turns red past it; unplanned
  spend is all red.

### Round-2 checks

**R2.1** Open the MV job: does the top (stepper + numbers) answer
"where is this job and how is its money" without scrolling?

>

**R2.2** Click a stepper stage to move the job (and back). Comfortable,
or does it feel dangerous?

>

**R2.3** Money tab: do the budget bars read instantly — green under,
red over, unplanned all-red?

>

## Round 3 — the founder's answers (in-session, 2026-08-13) and what shipped

R1, R2 passed. R3 brought four verdicts, all shipped: (1) editing a
milestone's % rebalances the untouched rows to land on 100% by itself
(Requested/Invoiced/Paid rows never move); (2) "Money out" renamed
**Cash advanced**, and every advance now prints as its own dated line —
a history, not a per-person sum — with the per-holder float kept under
"Currently holding" for settlement; (3) the "log expense on phone" link
is gone — the expense/advance forms reshape into the big-thumb stacked
layout below `sm` automatically, and money tables scroll inside their
cards on a phone; (4) covered by (2).

### Round-3 checks

**R3.1** Edit a milestone % on a plan with two-plus unpaid milestones —
do the others follow so the total stays 100?

>

**R3.2** Cash advanced: does the dated history + "Currently holding"
split read right?

>

**R3.3** Open the job on your phone — does the expense form come up
big-thumb by itself now?

>

## Round 4 — the founder's answers (in-session, 2026-08-13) and what shipped

R3.1 "no" diagnosed: the mechanics worked, but on the MV job every
milestone is already Paid — nothing is allowed to move, and the
silence read as failure. Now Requested rows may rebalance too (only
Invoiced/Paid stay locked) and an amber line explains exactly which
share is frozen when the plan can't reach 100 by itself. R3.2 "too
much on the page": the advance/expense forms collapse behind
"+ Record advance" / "+ Log expense". R3.3: the app now opens on a
**Home dashboard** — pipeline / in-production / overdue / silent-quote
cards, a Quick expense card, and a Needs-attention list.

### Round-4 checks

**R4.1** Add two unpaid milestones, change one's % — does the other
follow now, and does the amber note explain the frozen share?

>

**R4.2** Money tab: calmer with the forms behind buttons?

>

**R4.3** Open http://192.168.1.94:8000/aura — is Home the right first
screen, and does Quick expense log correctly?

>

## Verdict

- [x] **GO** — merge it; A5 (paperwork, contacts, settings) starts
- [ ] **GO with notes**
- [ ] **NO-GO** — fix the failed steps first

>

> GO given in-session 2026-08-13 ("ok go tieeps di") after round 4.

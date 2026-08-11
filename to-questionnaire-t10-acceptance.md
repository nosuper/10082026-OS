# T10 acceptance walkthrough — does the money-in side chase itself?

**Purpose:** decide whether ticket [#12 (T10: Payment milestones & invoice-request generator)](https://github.com/nosuper/10082026-OS/issues/12) is complete, or send it back for fixes.

**From:** Claude (the implementing agent) — **To:** the founder — **How your answers will be used:** the next Claude session reads this file top to bottom, treats every passed step as a verified acceptance criterion, turns each design answer into either code or a follow-up ticket, and acts on the verdict at the bottom.

## Context

T10 is money-in. A job carries **payment milestones** — a name, a percentage of the quoted total, and the production stage that makes them fall due. Each one walks the collection flow *chưa yêu cầu → đã yêu cầu KT → đã xuất HĐ → đã thanh toán*. One that goes unpaid past the payment terms raises a **nudge**. And one click builds the invoice-request text — client tax info and amounts prefilled — ready to paste into Zalo for the accountant.

It's merged to main (PR [#47](https://github.com/nosuper/10082026-OS/pull/47)) and CI is green.

The arithmetic and the state machine are already pinned by tests and do **not** need your clicks: amounts as a share of the quoted total, shares adding to the total, rounding never inventing or losing a đồng, whole-đồng amounts, the four states in order, unknown states refused, each state stamping its own time, stepping back clearing what it undoes, due-on-trigger-stage, dragging a job back un-duing a milestone nobody has acted on, overdue arithmetic, and VAT splitting back out of an invoice amount.

What automation cannot judge: whether the nudge catches your eye when you're not looking for it, whether the invoice text is something you'd actually paste to your accountant without editing it, and whether the milestone defaults match how you really bill.

## How to answer

**Rough effort:** about 15 minutes of clicking, plus however long the design questions take you.

**No deadline from my side** — this is the last of the four tickets in this batch waiting on a human.

Answer in the `>` blocks. Partial answers and "I don't know" are useful. If a step fails, say what you saw rather than only "no".

## 0. Before you start

The **preview stack** is at **http://192.168.1.94:8096/aura** — login `Administrator` / `admin`. It's built from `main`, so T8 (advances and settlement) and T11 (paperwork) are alongside it.

**Hard-refresh first (Ctrl+Shift+R)** — the browser caches the old app otherwise.

The job **MV — Hà Anh Tuấn** is seeded mid-collection, deliberately not from a standing start:

- **Đặt cọc** — 30%, falls due at Pre-production — already **paid**.
- **Sau quay** — 40%, falls due at Post-production — **invoiced three weeks ago and still unpaid**, so it is past the payment terms and should be nudging the moment you land.
- **Nghiệm thu** — 30%, falls due at Client sign-off — **not due yet**.

_A freshly converted job would show both milestones unrequested and nothing overdue — which is the hole the T6 walkthrough fell into with the silence badge, so this one is aged on purpose._

## 1. The nudge

### 1.1 Land on the jobs board without being told where to look

**Do this:** open `/aura/jobs`.
**Expect:** a strip at the top — the uncollected amount in đồng, how many milestones are past the payment terms, and the job they belong to.

_Why this matters: this is the only criterion in the ticket that's about being interrupted rather than about a number being right. If you have to go looking for it, it has failed._

Pass / fail, and did it catch your eye:

>

### 1.2 Is it on the right screen?

The ticket says "overdue milestones nudge the founder's dashboard". There is no dashboard yet — [#14 (T12: Overhead log & break-even dashboard)](https://github.com/nosuper/10082026-OS/issues/14) builds that, and the Jobs board carries the nudge until it does. Both read the same overdue list, so they can't disagree later.

Good enough to call this criterion met, or does it need the dashboard first?

>

### 1.3 The payment terms are a setting

**Do this:** Settings → Payment Terms (days), currently 7. Change it to 30, save, go back to the jobs board.
**Expect:** the *Sau quay* milestone is 21 days past due, so at 30 days it should stop nudging. Put it back to 7 afterwards.

Pass / fail:

>

## 2. The collection flow

### 2.1 Read the milestones on the job

**Do this:** open **MV — Hà Anh Tuấn**, find the milestones panel.
**Expect:** three rows with their names, percentages, amounts and statuses; the overdue one marked, in red, with how late it is.

Pass / fail:

>

### 2.2 Walk one forward

**Do this:** move *Nghiệm thu* from *chưa yêu cầu* to *đã yêu cầu KT*.
**Expect:** it takes, and the time it happened is recorded.

Pass / fail:

>

### 2.3 Are those four states the ones you actually use?

They're the four from the ticket. Now that you're looking at them on a real job — right names, right number of them, anything missing between two of them?

>

## 3. The invoice request

### 3.1 Generate it

**Do this:** on the overdue *Sau quay* milestone, click **Invoice request**.
**Expect:** the text appears below and lands on your clipboard.

Pass / fail:

>

### 3.2 Read it as your accountant would

**Do this:** paste it into Zalo — actually paste it, don't just read it on screen.

**Expect:** the client's tax info and the amount, prefilled, in a shape you'd send without editing.

_Why this matters: this is the criterion most likely to be almost-right. "Correct" and "sendable without retyping" are different bars, and only you know which side of it this lands on._

Pass / fail, and what you'd change about the wording:

>

### 3.3 Anything missing from it?

Payment deadline, bank details, the job code, a reference number, the VAT split shown separately — anything your accountant asks for every time that isn't in there?

>

## 4. Scope calls I made that you may veto

### 4.1 Milestone **amounts derive from the quoted total** and aren't typed in — so re-pricing moves them. Right call, or do you sometimes need to bill a figure that isn't a clean percentage?

>

### 4.2 A milestone falls due from a **production stage**, not a date. So the money follows the work rather than a calendar. Keep it, or do you also need fixed-date milestones?

>

### 4.3 **Payment terms are one global number**, not per client or per deal. Enough, or does it need to vary?

>

### 4.4 Dragging a job **backwards** un-dues a milestone nobody has acted on, but a milestone you've already asked for stays due wherever the board sits. Is that the behaviour you'd expect?

>

## 5. Anything else

### Anything you saw — a number you'd want on the screen, a step you do by hand that this could take, something about how you chase clients that this doesn't fit — that we didn't ask about?

>

## Verdict

### Is T10 complete?

**Accept** (close #12) — or **send back**, listing what has to change first:

>

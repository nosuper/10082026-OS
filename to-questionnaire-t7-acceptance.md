# T7 acceptance walkthrough - does a won deal become a usable job?

**Purpose:** decide whether ticket [#9 (T7: Won deal to Job - production stages & revision counter)](https://github.com/nosuper/10082026-OS/issues/9) is complete, or send it back for fixes.

**From:** Claude (the implementing agent) - **To:** the founder - **How your answers will be used:** the next Claude session reads this file top to bottom, treats every passed step as a verified acceptance criterion, turns each design answer into either code or a follow-up ticket, and acts on the verdict at the bottom.

## Context

T7 turns a won deal into a **job**: the breakdown, packages, client and links carry across with nothing re-entered, the job moves through the fixed production stages, and the feedback loop counts **revision rounds** - with the third one flagged as a chargeable **change order**.

Automation is green: 176/176 Frappe site tests on a fresh site (30 of them new for T7), 103 pure pytest, frontend build clean. T6 (the hosted quote page) is merged in, so this branch has everything main has.

What automation cannot judge: whether the job screen is the thing you'd actually open during a shoot, whether the stage names match how you and Linh talk, and several scope calls I made that you may veto. That's what this walkthrough is for.

## How to answer

**Rough effort:** about 20 minutes of clicking, plus however long the design questions take you.

**No deadline from my side** - but T8 (advances, expenses and settlement) attaches to exactly these jobs, so it's the thing waiting on this.

Answer in the `>` blocks. Partial answers and "I don't know" are useful - flag anything you're unsure of rather than skipping it. If a step fails, say what you saw rather than only "no"; that's usually enough for me to fix it without a second round.

## 0. Before you start

The **preview stack** for this ticket is up at **http://192.168.1.94:8007/aura** - login `Administrator` / `admin`.

**Hard-refresh first (Ctrl+Shift+R)** - the browser caches the old app otherwise, and every "it didn't change" report so far has been that.

It is seeded with four deals and one job already in production:

- **Social series - 6 tập** (Quote Sent) - the one with a real breakdown, packages and a published quote version already sent to the client. Use this one for the conversion test below.
- **MV - Hà Anh Tuấn** - already won, already a job, sitting at Feedback with two revision rounds used. Logging a third there is the interesting click.
- **TVC Tết 2027** (Brief Received) and **Phim doanh nghiệp Vinamilk** (Negotiation) - background, so the board isn't empty.

## 1. Conversion - "nothing is re-entered"

### 1.1 Drag **Social series - 6 tập** to **Won** on the deal board

**Do this:** open `/aura/deals`, drag the card into the Won column.
**Expect:** a dialog - *"Social series - 6 tập" is won* - offering to create the job now.

Pass / fail, and what you saw:

> Okay.

### 1.2 Accept the offer

**Do this:** click **Create job**.
**Expect:** you land on the new job's page, at stage Pre-production.

Pass / fail:

> Works.

### 1.3 Check that the deal's work carried across

**Do this:** read the job page - the packages table, the Client panel, the Links panel, the "Quoted (at conversion)" totals.
**Expect:** the same cost lines, packages, prices, company, contact and links as the deal, with the same numbers.

_Why this matters: the whole point of story 26 is that the quote's work carries into production untouched - if anything has to be retyped, this ticket has failed its main job._

Pass / fail, and anything missing:

> Yes.

### 1.4 Try to convert the same deal twice

**Do this:** go back to `/aura/deals`. The Won card now shows **Job →** instead of **+ Job**. Click it.
**Expect:** it opens the existing job rather than making a second one.

Pass / fail:

> Yes.

### 1.5 The job's breakdown and totals are **read-only** - a snapshot of what was won. Re-pricing still happens on the deal. Is that the right split, or do you need to re-price inside a job?

> Yes - but I can still change a line item's number even though the total doesn't change. Should lock the edit.

### 1.6 A deal converts **once**. Do you ever need two jobs from one deal - a retainer split into separate shoots, say?

> Maybe. It hasn't happened, or it has and I don't know about it.

## 2. The jobs board and the stages

### 2.1 Open the jobs board

**Do this:** click **Jobs** in the nav (`/aura/jobs`).
**Expect:** a column per stage; **MV - Hà Anh Tuấn** in Feedback with a "2 revisions" badge, and your new job in Pre-production carrying a "no files location" badge - conversion doesn't invent a folder for you.

Pass / fail:

> Pass.

### 2.2 Move a job between stages

**Do this:** drag your new job from Pre-production to Shoot, then back.
**Expect:** it sticks after a refresh, and the move is recorded (who moved it, when) in the job's stage history.

Pass / fail:

> Pass.

### 2.3 The stages are: Pre-production → Shoot → Post → Feedback → Delivery → Nghiệm thu → Chờ thanh toán → Done. Are these the names you and Linh actually use, in this order?

> Use English - production English.
>
> **Chosen:** Pre-production → Production → Post-production → Client review → Delivery → Client sign-off → Awaiting payment → Complete. Built and on the preview.

### 2.4 A job can be dragged to **any** stage, forwards or backwards, including straight to Done. Should any move be blocked?

_Why this matters: the fixed stage set was decided; whether the order is enforced was not._

> Not sure, suggest me.
>
> **Suggested, and left as built:** don't block anything. You are two people who both know where a job really is; a blocked move just gets worked around by mistyping something else, and the stage history already records who moved what, when. If a job ever lands in Complete by accident, dragging it back costs one second and leaves a trail. Say the word if you'd rather Complete were one-way.

### 2.5 Jobs got their **own board** rather than living on the deal board. Right call?

> Yes.

## 3. Revision rounds and the redo

### 3.1 Open **MV - Hà Anh Tuấn** and read its Revisions panel

**Do this:** click the card on the jobs board.
**Expect:** two rounds listed with their notes, authors and times; the line "2 of 2 included rounds used"; and a warning that the next round is past the included ones.

Pass / fail:

> Pass.

### 3.2 Log the third round

**Do this:** type what the client asked for and click **Log revision**.
**Expect:** three things at once - the round is flagged **⚠ chargeable change order**, the job's stage moves to **Post** on its own, and a line tells you it did.

_Why this matters: this is the redo you asked for at the T6 walkthrough - "need a redo / automatically change stage if need revision after feedback"._

Pass / fail, and whether the stage move was clear enough:

> Pass.

### 3.3 Check the board agrees

**Do this:** go back to `/aura/jobs`.
**Expect:** the job now sits in the **Post** column, carrying a **⚠ Change order · 3 rounds** badge.

Pass / fail:

> Pass.

### 3.4 **Two rounds are included, the third is chargeable.** Is 2 the right number?

> Should be changeable per job.

### 3.5 The redo sends the job back to **Post** - where the edit happens. Is that the stage a redo belongs in?

> Okay.

### 3.6 A revision logged **before** Post (Pre-production, Shoot) leaves the stage alone - there is no cut to redo yet. Right call?

> Okay.

### 3.7 The redo **stops at Delivery**. A revision logged at Nghiệm thu, Chờ thanh toán or Done is still counted and still flagged chargeable, but the job stays where it is - past sign-off a change request is a new negotiation, not a redo. Is that the right place to draw the line?

_Why this matters: the alternative is that a note typed against a delivered, invoiced job silently pulls it back onto the production board._

> Okay.

### 3.8 A revision round can be logged at **any** stage, not only Feedback. I read the ticket's "revision counter on feedback" as where it's *shown*, not where it's *allowed*. Do you want it restricted to Feedback?

> Agree with you - leave it loggable at any stage.

### 3.9 A revision round can be **deleted** by whoever can edit the job, which lowers the count and can clear the change-order flag. Should logged rounds be immutable once saved - or is deleting a mistyped round something you and Linh need?

> Only the Founder and Producer roles.
>
> **Already true, nothing to build:** a Job is writable only by Founder and Producer (plus System Manager, the admin role), so those are the only people who can delete a round today. Left as is.

### 3.10 Each round records the note, who logged it, and when. Is anything missing you'd want at settlement time - an estimated cost of the round, say?

>

## 4. Files location

### 4.1 Set a files location on your new job

**Do this:** at the top of the job page, type a folder (the placeholder suggests `//nas/jobs/<job code>`), click **Save**, then hard-refresh.
**Expect:** it sticks, and the "no files location" badge disappears from the board card.

Pass / fail, and whether it's prominent enough:

> Okay.

### 4.2 It's free text today, only *hinted* with the job code. Should the system build the path for you from a root folder you set once in Settings?

_Why this matters: "shared folder by job code" is a convention the system currently suggests but doesn't enforce._

> Leave it free text for now - the job code stays a hint, not a rule.

## 5. Scope calls I made that you may veto

### 5.1 The job also carries the quote parameters, totals and the **commission rate** - founder-only, invisible to Linh, the same boundary as on the deal. That's groundwork for T8's expenses-vs-quoted. Keep it, or strip the job back to the breakdown alone?

> Okay.

### 5.2 T6 landed while T7 was waiting, so a deal can now have published **quote versions**. The job carries the deal's *live* breakdown, not the version the client confirmed - so re-pricing a deal after the client agreed would hand the job numbers they never saw. Should the job instead point at, and carry, the confirmed version?

_Why this matters: T8's settlement compares real spend against "what was quoted", and that's the number the client agreed to._

> Leave as is: the job carries the deal's live breakdown. Revisit if you ever re-price a deal after the client has agreed.

### 5.3 Every job has an **owner** (you or Linh), same rule as deals. Not asked for in the ticket - useful, or noise?

> Useful.

## 6. Anything else

### Anything you saw during the walkthrough - wording, layout, something missing you'd reach for during a shoot, a worry about how this meets T8 - that we didn't ask about?

> A job should have tasks, a gantt and a kanban, and other roles - designer, editor - should be able to get in without seeing any finance.
>
> **Filed as [#41](https://github.com/nosuper/10082026-OS/issues/41), not built here.** The scheduling half is ordinary work; the crew-access half is a permission design (the money surface is most of a job's fields, and this repo's standing rule is to prove a founder-only number unreachable through the document API, the list API *and* search). That's a ticket of its own, not a patch on T7.

## Verdict

### Is T7 complete?

**Accept** (close #9 and merge) - or **send back**, listing what has to change first:

> Accepted, with four things sent back. All four are done and on the preview:
>
> 1. **1.5 - the carried breakdown is now frozen.** The controller refuses any change to the carried cost lines, packages and quote numbers, so read-only holds through the API and not just the form. Re-pricing stays on the deal; everything production owns (title, client, owner, stage, links, files location, revisions) is still editable.
> 2. **2.3 - the stages are production English.** Pre-production → Production → Post-production → Client review → Delivery → Client sign-off → Awaiting payment → Complete.
> 3. **3.4 - included revision rounds are per job**, defaulting to 2 and editable on the job page. The chargeable flag follows the number in both directions, so lowering it re-flags rounds already logged.
> 4. **2.4 and 3.9 - answered, nothing built.** Free stage movement stays; only Founder and Producer can delete a round, which was already the case.
>
> 185/185 Frappe site tests, 103 pure pytest, frontend build clean.
>
> **Still open, deliberately:** 1.6 (whether one deal ever needs two jobs) is unresolved - it stays one-job-per-deal until it bites. 3.10 went unanswered, so a revision round still records only note, author and time.

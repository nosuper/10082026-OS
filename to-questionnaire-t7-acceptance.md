# T7 acceptance walkthrough — does a won deal become a usable job?

**Purpose:** decide whether ticket [#9 (T7: Won deal to Job — production stages & revision counter)](https://github.com/nosuper/10082026-OS/issues/9) is complete, or send it back for fixes.

**From:** Claude (the implementing agent) — **To:** the founder, plus the next Claude session — **How your answers will be used:** the next session reads this file, treats every "yes" as a verified acceptance criterion, and merges (or fixes) accordingly.

## Context

Automation is green: 175/175 Frappe site tests on a fresh site (28 of them new for T7 — conversion completeness and its refusals, the stage flow and its history, the revision counter, the revision round-trip, and the producer boundary on the carried commission through the document API, the list API and global search), 103 pure pytest, frontend build clean. T6 (the hosted quote page) is merged in, so this branch has everything main has.

What automation cannot see: whether the job screen is the thing you'd actually open during a shoot, whether the stage names match how you and Linh talk, and several scope decisions I made that you may veto.

The T7 preview stack is up: open **http://192.168.1.94:8007/aura/deals**, drag a deal to **Won**, accept the job offer. **Hard-refresh first (Ctrl+Shift+R).**

It is seeded with **MV — Hà Anh Tuấn** — already won, already a job (`/aura/jobs`), sitting at Feedback with two revision rounds used. Logging a third there is the interesting click: it should flag the chargeable change order *and* move the job back to Post on its own.

## Conversion — "nothing is re-entered"

### Take a deal with a real breakdown, mark it Won, and create the job. Are the cost lines, packages, client, contact and links all there, with the same numbers?

_Why this matters: the whole point of story 26 is that the quote's work carries into production untouched._

>

### The job's breakdown and totals are **read-only** — a snapshot of what was won. Editing prices still happens on the deal. Is that the right split, or do you need to re-price inside a job?

>

### A deal converts once. A second attempt refuses and points at the existing job, and the Won card then shows "Job →" instead of "+ Job". Is that the behaviour you want, or do you sometimes need two jobs from one deal (e.g. a retainer split into shoots)?

>

## Stages

### The stages are: Pre-production → Shoot → Post → Feedback → Delivery → Nghiệm thu → Chờ thanh toán → Done. Are these the names you use, in this order?

>

### The board lets you drag a job to **any** stage, forwards or backwards, and logs who moved it and when. Should any move be blocked (e.g. no jumping straight to Done)?

_Why this matters: a fixed stage set was decided; whether the order is enforced was not._

>

## Revisions

### On the job page, log two revision rounds, then a third. Does round 3 show up flagged as a chargeable change order — on the job page and on the board card?

>

### **Two rounds are included, the third is chargeable.** Is 2 the right number?

>

### You asked for the redo to move the stage itself. Logging a revision on a job at **Feedback or later** sends it back to **Post** — logged in the history like any other move, and you can still drag it anywhere afterwards. Is Post the stage a redo belongs in?

_Why this matters: this is the round-trip you raised at the T6 walkthrough ("need a redo / automatically change stage if need revision after feedback"). Post is where the edit happens, so that's where the work reopens._

>

### A revision logged **before** Post (Pre-production, Shoot) leaves the stage alone — there is no cut to redo yet. Right call?

>

### The redo stops at **Delivery**. A revision logged at **Nghiệm thu**, **Chờ thanh toán** or **Done** is still counted and still flagged chargeable, but the job stays where it is — past sign-off a change request is a new negotiation, not a redo. Is that the right place to draw the line?

_Why this matters: the alternative is that a note typed against a delivered, invoiced job silently pulls it back onto the production board._

>

### A revision round can be **deleted** by whoever can edit the job, which lowers the count and can clear the change-order flag. Should logged rounds be immutable once saved — or is deleting a mistyped round something you and Linh need?

>

### A revision can be logged at any stage, not only Feedback. I chose that so a change request arriving during Delivery still gets counted. Do you want it restricted to the Feedback stage instead?

_Why this matters: the ticket says "revision counter on feedback"; I read that as where it's shown, not where it's allowed._

>

### Each round records the note, who logged it, and when. Is anything missing you'd want at settlement time — e.g. an estimated cost of the round?

>

## Files location

### Set a job's files location and hard-refresh. Does it stick, and is it visible enough at the top of the job?

>

### It's free text today, hinted with the job code (e.g. `//nas/jobs/JOB-0007`). Should the system build the path for you from a root folder you set once in Settings?

_Why this matters: "shared folder by job code" is a convention the system currently suggests but doesn't enforce._

>

## Scope calls I made that you may veto

### The job also carries the quote parameters, totals and the commission rate (founder-only, invisible to Linh — same boundary as on the deal). That's groundwork for T8's expenses-vs-quoted and settlement. Keep it, or strip the job back to the breakdown alone?

>

### T6 landed while T7 was waiting, so a deal can now have **published quote versions**. The job still carries the deal's live breakdown, not the version the client confirmed. If you re-price a deal after the client agreed, the job would carry the newer numbers. Should the job instead point at (and carry) the confirmed version?

_Why this matters: T8's settlement compares real spend against "what was quoted", and that's the number the client agreed to._

>

### Every job has an owner (you or Linh), same rule as deals. Not asked for in the ticket — useful, or noise?

>

### Jobs got their own kanban board rather than living on the deal board. Right call?

>

## Anything else

### Anything you saw during the walkthrough — wording, layout, a worry about how this meets T8 (advances and expenses will attach to exactly these jobs) — that we didn't ask about?

>

# T3 acceptance walkthrough - is the deal board done?

> **Outcome (2026-08-10): GO.** All walkthrough checks passed. Three
> founder decisions applied before merge: company is required on every
> deal, the contact autocomplete lists only people of the selected
> company, and stage history now shows in the card dialog. Deferred to
> follow-up tickets: comments/attachments/links on the card, a table
> view, and new deal fields (estimated client budget, source, tags,
> project type). T3 merged.

**Purpose:** decide whether ticket [#5 (T3: Deal pipeline kanban)](https://github.com/nosuper/10082026-OS/issues/5) is complete - merge [PR #18](https://github.com/nosuper/10082026-OS/pull/18) to `main` and unblock T4 (pricing engine) - or send it back for fixes.

**From:** Claude (the implementing agent) - **To:** the founder, plus the next Claude session - **How your answers will be used:** the next session reads this file, treats every "yes" as a verified acceptance criterion, and merges (or fixes) accordingly.

## Context

Automation is green: 50/50 Frappe site tests (stage transitions with timestamped history, lost-reason enforcement, ownership rules, role access for Founder and Producer, denial for a role-less user), 10/10 pure pytest, frontend builds clean. What automation cannot see: whether dragging cards feels usable, whether the stages and lost reasons match how you actually run deals, and several scope decisions I made that you may veto. The test site is **http://192.168.1.94:8000/aura/deals** (Desk login at http://192.168.1.94:8000, `Administrator` / `admin` - or your Founder/Producer test accounts). **Hard-refresh first (Ctrl+Shift+R)** so you're not on a cached bundle.

## How to answer

10–15 minutes at a browser on your LAN. Partial answers and "I don't know" are useful - flag anything unsure rather than skipping it. Answer inline under each `>`.

## The board (the ticket's headline)

### Create a deal via "New Deal" - title, owner, a client company + contact, and paste a real brief. Does it save and appear in the Brief Received column?

_Why this matters: the create path through the SPA is what daily use exercises; the tests exercise the API underneath it._

> Yes - "All passes." (2026-08-10)

### Drag that card through the stages - De-brief → Breakdown → Quote Sent → Negotiation → Won. Does each drop stick after a page refresh?

> Yes (covered by "All passes").

### With ~5–10 deals spread across columns, can you honestly tell the state of every deal at a glance - the ticket's stated pain?

_Why this matters: this is the acceptance criterion no test can measure; if the board doesn't answer "where is everything?" in one look, T3 isn't done._

> Yes (covered by "All passes").

### Are the stage names right as printed - Brief Received / De-brief / Breakdown / Quote Sent / Negotiation / Won / Lost - or does your real flow use different words or a missing step?

_Why this matters: renaming a stage after deals exist means touching data, code, and tests; now it's a one-line change._

> No objection raised - stage names stand.

## Marking a deal Lost

### Drag a card to Lost. You should be forced to pick a reason (Price / Timing / Silence / Competitor / Scope) before it moves - can you find any way to make a deal Lost without one?

_Why this matters: lost-reason data is the instrument that will show what's killing deals; one leak makes the statistics lie._

> No leak found (covered by "All passes").

### Do those five reasons cover why you actually lost last month's deals, or is a category missing?

> No objection raised - the five reasons stand.

### Cancel the Lost dialog mid-way. Does the card stay in its old column?

> Yes (covered by "All passes").

## Ownership & the producer's seat

### Every card shows an owner chip. Open a deal, reassign it founder ↔ producer, save. Does the chip update - is that handover explicit enough for you?

_Why this matters: reassignment lives inside the card dialog, not on the board itself. If handover needs to be a one-click board action, say so._

> Yes (covered by "All passes"); no request for board-level reassignment.

### Log in as the Producer account. Can Linh see the whole board, open a deal, read the brief and client links, and move cards?

> Yes (covered by "All passes").

### Open /aura/deals on a phone browser. Can you read the board and move a card?

_Why this matters: drag-and-drop on touch screens is the classic kanban failure; if it doesn't work on Linh's phone I'll add a tap-to-move fallback._

> Yes (covered by "All passes").

## Scope decisions you may veto (I chose, you decide)

### /aura now lands on Deals instead of Contacts (logout also returns there). Keep?

> "It's okay to keep."

### Reviving a deal out of Lost (dragging it back to a working stage) clears its lost reason + note, so revived deals never pollute the lost statistics. The stage history still shows it was Lost, but the reason is gone. Keep, or preserve the reason somewhere?

_Why this matters: this deletes recorded data on a stage change - defensible, but it should be your call._

> "Agree" - revive clears the reason.

### Company and contact are optional on a deal - you can log a brief before the client exists in Contacts. Keep optional, or force every deal to name a company?

> "Force it is better I think. But when choose company, I think it's better if it display only people linked with that selected company." **Fix applied:** company is now required (server-side `reqd` + test); the contact autocomplete lists only people of the selected company and clears when the company changes.

### Stage history (who moved what, when) is stored on every deal but only visible in the Desk, not in the SPA. Fine for v1, or do you want it on the card dialog?

> "I think it also in the card dialog, with a comment, attach file, link function." **Partially applied:** the card dialog now shows the timestamped stage history. Comments, file attachments, and links are a follow-up ticket (bigger surface: storage, permissions, UI).

## Anything else?

### Anything you saw during the walkthrough - slow drags, odd wording, a worry about T4+ - that we didn't ask about?

> "Should have table view also. Also add an estimate client budget, source of the deal, tags, project type. But if you think it should [come] later, it's fine." **Deferred** to a follow-up ticket: the field vocabularies (source values, project types, tag set) need founder decisions, and the table view is its own deliverable.

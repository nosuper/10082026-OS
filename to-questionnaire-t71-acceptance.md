# T7.1 acceptance walkthrough - can crew work a job without seeing its money?

**Purpose:** decide whether ticket [#41 (T7.1: Job tasks, gantt and kanban - with crew access that sees no money)](https://github.com/nosuper/10082026-OS/issues/41) is complete, or send it back for fixes.

**From:** Claude (the implementing agent) - **To:** the founder - **How your answers will be used:** the next Claude session reads this file top to bottom, treats every passed step as a verified acceptance criterion, turns each design answer into either code or a follow-up ticket, and acts on the verdict at the bottom.

## Context

You asked for this at the T7 walkthrough, when I asked what we hadn't asked about:

> "Job should have tasks, gantt, kanban and let other role can access such as designer, editor,... without seeing any finance"

Two halves, and the second one was the work.

**The plan.** A job now has **tasks**: a title, a **craft** (editing, design, colour…), who is doing it, a start and a due date, and a status. One plan, read three ways - a **list** to write it, a **task board** to work it, and a **task timeline** (the gantt) to see whether it fits. All three live on a new **Tasks** tab on the job page.

**The third kind of user.** There is now a **Crew** role. A crew session holds **no permission on Job at all** - not read, not list, not search. What they get instead is `/my-work`: the jobs they hold a task on, and on each one the plan, the files location and the brief links. Nothing carried from the deal, no packages, no quote totals, no milestones, no commission, and no deal to follow back to the pricing.

That is the design decision I most want you to look at. The alternative was to keep crew on the job page with the money fields hidden, which would have meant holding the line field by field across the whole job and every money endpoint hanging off it. Making Job simply unreachable is one boundary instead of thirty, and it is proven the same way the founder-only spike note is: document API, list API and global search, plus every money endpoint on a job.

**Four triage questions you had open, and the answers I built on** - each is a question below if you want to change it:

- **One Crew role**, not one per craft. Craft is a field on the task.
- Crew see **only jobs they hold a task on**.
- Tasks are **pure scheduling** - a task carries no money at all, and there is a test that fails the day someone adds an amount to one.
- **All three views** ship now, gantt included.

Automation is green: the new site tests cover the task seam, the crew boundary and the one write a crew member may make; the frontend build is clean.

## How to answer

**Rough effort:** about 25 minutes of clicking - and it needs you to log out and back in once, as a crew member.

Answer in the `>` blocks. Partial answers and "I don't know" are useful. If a step fails, say what you saw rather than only "no".

## 0. Before you start

The **preview stack** for this ticket is at **/aura** on the stack's URL - login `Administrator` / `admin`.

**Hard-refresh first (Ctrl+Shift+R)** - the browser caches the old app otherwise.

Two crew accounts are seeded, both with password `auraos-crew-preview`:

- **editor@aura.local** (Minh Dựng) - holds three editing tasks on the job
- **designer@aura.local** (Lan Thiết kế) - holds one, and it is overdue

The job **MV - Hà Anh Tuấn** is seeded with ten tasks running from twelve days ago to eight days ahead, so the timeline has bars either side of today.

## 1. The plan, as the person running the job

### 1.1 Open the job's Tasks tab

**Do this:** `/aura/jobs`, open **MV - Hà Anh Tuấn**, click the new **Tasks** tab.
**Expect:** a list of ten tasks, an overdue badge in the header, and three view buttons - List, Board, Timeline.

Pass / fail, and what you saw:

>

### 1.2 Write a task

**Do this:** click **Add task**, type a title, pick a craft and a person, set a start and a due date, press Enter.
**Expect:** it appears in the list in date order.

Pass / fail:

>

### 1.3 Edit one in place

**Do this:** in the List view, change a title, a date, a craft and an owner directly in the row.
**Expect:** each change saves as you leave the field, with no Save button to hunt for.

_Why this matters: a plan that takes a dialog per edit does not get kept up to date, and a plan nobody updates is worse than none._

Pass / fail:

>

### 1.4 The task board

**Do this:** switch to **Board**. Drag a card between columns.
**Expect:** five columns - To do, In progress, Blocked, In review, Done - and the card moves as you drop it, the way the jobs board does.

Pass / fail:

>

### 1.5 The timeline

**Do this:** switch to **Timeline**.
**Expect:** one bar per dated task against a month ruler, a red line at today, bars coloured by status, and the undated task listed underneath as **Not scheduled** rather than silently missing.

_Why this matters: this is the gantt you asked for by name. Tell me if it is not the shape you meant - a plain calendar month grid and a dependency-arrow gantt are both different things, and they cost different amounts._

Pass / fail, and whether it is the shape you meant:

>

## 2. The crew boundary - the part that matters

### 2.1 Log in as the editor

**Do this:** log out. Log in as `editor@aura.local` / `auraos-crew-preview`. You land on `/aura/my-work`.
**Expect:** one nav item - **My work** - and one job in the list, with your open task count.

Pass / fail:

>

### 2.2 Look for money

**Do this:** open the job. Read the whole page. Then try to reach the money on purpose: put `/aura/jobs` in the address bar, then `/aura/deals`, then the job's own URL `/aura/jobs/JOB-0002`.

**Expect:** the job page shows its title, client, stage, files location, brief links and the full plan - and nothing else. The three URLs you typed either bounce you back to My work or show a permission error. No quoted total anywhere, no packages, no cost lines, no milestones.

_Why this matters: this is the ticket. If a number you would not show a freelancer appears anywhere on this screen, or a typed URL gets one, say exactly where and I will treat it as a leak, not a nitpick._

Pass / fail, and anything you found:

>

### 2.3 Move your own card

**Do this:** in Board view, drag your own task to another column. Then try to drag **Key visual cho poster** - the designer's card.
**Expect:** yours moves. Hers does not - the card is not draggable, and its status shows as a pill rather than a dropdown.

Pass / fail:

>

### 2.4 Can you see the whole plan, or only your own tasks?

**Do this:** count the tasks on the board as the editor.
**Expect:** all ten - the whole plan of the job you are on, including other people's tasks and who holds them.

_Why this matters: this was a judgement call. A board showing only your own three cards is not a board, and knowing the colourist starts on Thursday is not knowing what the colourist is paid. But it does mean an editor can see the shape of the whole job and who else is on it - tell me if that is too much._

Pass / fail, and whether you want it narrowed to their own tasks only:

>

### 2.5 Log back in as yourself

**Do this:** log out, log back in as Administrator, open the same job.
**Expect:** everything is where it was - the money, the packages, the milestones - and the Tasks tab shows the same plan, now editable.

Pass / fail:

>

## 3. The design questions I'd like settled

### 3.1 Is one **Crew** role enough, or do you want Editor / Designer / Colourist as separate roles?

Today the craft is a label on the task and everyone holds the same role. Separate roles would let permissions diverge per trade later - but every craft you add becomes a code change, and the money boundary has to be proven blind once per role.

>

### 3.2 What else should crew see about the job, and what should they not?

They currently get: title, job code, production stage, client company name, files location, brief links, and the whole task plan with names.

They do not get: the client contact's name and phone, the revision rounds and their notes, the deal it came from, and anything priced.

Anything on the second list you want moved to the first, or the other way round?

>

### 3.3 Should a task be able to depend on another one?

I left dependencies out. A task carries dates and a status; nothing says "grade cannot start until the edit is approved", and the timeline draws no arrows.

_Why this matters: dependencies are what turn a bar chart into a gantt in the project-management sense, and they are also where the complexity is - cycles, cascading dates, what happens when a task slips. Worth it, or is a dated plan enough for a shoot?_

>

### 3.4 Should crew be able to add a task of their own?

Today they cannot - they may move their own card and add a note to it, and that is all. Planning is the producer's.

>

## 4. Scope calls you may veto

### 4.1 **Crew hold no permission on Job whatsoever**, and read a purpose-built money-free view instead. It is the strongest version of what you asked for and the easiest to prove; the cost is that a crew screen only ever shows what I have explicitly put on it. Right call?

>

### 4.2 A task **carries no money**, so nothing on this plan feeds T8 settlement. A freelancer's fee stays a cost line on the deal and an expense on the job. Keep it that way, or should a task eventually carry what that person is being paid for it?

>

### 4.3 **Statuses are fixed** - To do, In progress, Blocked, In review, Done - because the columns of a board are its whole shape. Are those the five you want, in that order?

>

### 4.4 **Crafts are founder-expandable** and seeded with Producing, Camera, Editing, Design, Colour, Sound. Missing any?

>

### 4.5 An **undated task** is allowed - it sits on the board and is listed beside the timeline rather than getting a bar. Or should a task have to be dated before it can exist?

>

## 5. Anything else

### Anything you saw - wording, a screen that reads wrong on a phone, something a designer would ask for on their first day - that we didn't ask about?

>

## Verdict

### Is T7.1 complete?

**Accept** (close #41 and merge the PR) - or **send back**, listing what has to change first:

>

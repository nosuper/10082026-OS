# AuraOS

One shared system for a small video production house: deal pipeline, cost
breakdowns and quotes, jobs, money tracking, paperwork and a founder-only
overhead view. This file is the project's glossary — the words we use, and
the ones we deliberately don't.

## Quote delivery

**Package**:
A client-facing group of cost lines carrying its own description and price — what a client reads instead of our line-level costs. A cost line belonging to no package is quoted as a package of its own.
_Avoid_: bundle, group, section, item

**Quote version**:
An immutable snapshot of a deal's packages and totals, reachable at its own tokenised URL. Re-pricing produces a new version; a published one is never edited.
_Avoid_: quote (unqualified), proposal, estimate

**Publish**:
To create a quote version. Distinct from sending it — publishing only makes the link exist.
_Avoid_: generate, issue, release

**Sent**:
A published version the producer has handed to the client. Starts the silence clock.
_Avoid_: delivered, shared, out

**Confirmed**:
A sent version the client has agreed to. Does not by itself win the deal.
_Avoid_: accepted, approved, signed

**Silence nudge**:
The flag raised on a deal whose sent version has gone unanswered past the configured window.
_Avoid_: reminder, follow-up, alert

**Margin floor**:
The single global margin percentage below which any quote warns, without revealing where the number comes from.
_Avoid_: minimum margin, threshold, floor price

## Production

**Job**:
A won deal in production, carrying that deal's breakdown, packages and client unchanged. One deal becomes at most one job, and the numbers it carries are a snapshot — pricing is still edited on the deal.
_Avoid_: project, production, gig, booking

**Production stage**:
Where a job sits in the fixed flow from Pre-production to Done. Both operating roles may move a job to any stage, forwards or back, and every move is logged.
_Avoid_: status, phase, step

**Revision round**:
One request for changes from the client, logged against a job with its note, author and time. Rounds are numbered from their order, never typed in.
_Avoid_: revision (unqualified), amend, edit, feedback round

**Redo**:
The round-trip a revision round sets off: a job the client has already been shown goes back to the stage where the work is redone, without anyone dragging the card.
_Avoid_: rework, reopen, bounce back

**Change order**:
A revision round past the included ones — chargeable, and flagged as such wherever the job appears.
_Avoid_: extra, overage, out of scope

**Files location**:
The shared folder a job's material lives in, named after the job code.
_Avoid_: path, directory, drive, storage

## Environments

**Preview stack**:
A throwaway environment serving one ticket's branch, for a human to click through. Disposable by definition: nothing on it is backed up and any of it can be rebuilt from the branch.
_Avoid_: preview environment, dev site, staging, the box

**Walkthrough**:
The founder clicking through a preview stack to accept or reject a ticket. The judgement automated tests cannot make.
_Avoid_: UAT, QA, demo, acceptance testing

**Seed data**:
Data a branch creates at stack boot so its own feature is visible. Never real, never preserved.
_Avoid_: smoke data, fixtures, demo data, test data

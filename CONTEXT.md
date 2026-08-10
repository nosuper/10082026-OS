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

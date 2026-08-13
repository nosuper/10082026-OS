# T1 acceptance walkthrough - is the scaffold done?

> **Outcome (2026-08-10): GO.** First pass found a real blocker - `/aura`
> was a white screen (missing `sites/assets/auraos` symlink; fixed in
> init.sh + CI, with a new regression test asserting asset
> servability). On re-test the founder confirmed: page renders with a
> working button; Desk login works; a Founder-role user
> (anhchung.work@gmail.com) can read/edit/comment on Founder Spike
> Note; the Producer-role user (Linh) has no access. Mobile check and
> fresh-machine boot were not exercised - accepted as-is. T1 merged.

**Purpose:** decide whether ticket [#3 (T1: Scaffold)](https://github.com/nosuper/10082026-OS/issues/3) is complete - merge `feat/t1-scaffold` to `main` and start T2 - or send it back for fixes.

**From:** Claude (the implementing agent) - **To:** the founder, plus the next Claude session - **How your answers will be used:** the next session reads this file, treats every "yes" as a verified acceptance criterion, and merges (or fixes) accordingly.

## Context

T1's automated evidence is already in: CI is green (pure pytest 10/10, frontend build, Frappe site tests 11/11 including the producer-permission proof), and the same suite passed on the live test deployment in LXC 102. What automation cannot see is a human at the browser: whether the thing *looks and feels* deployed, and whether the docs would actually get you through a bad evening. The test site is **http://192.168.1.94:8000** (login `Administrator` / `admin`); the placeholder page is **http://192.168.1.94:8000/aura**.

## How to answer

10–15 minutes at a browser on your LAN. Partial answers and "I don't know" are useful - flag anything unsure rather than skipping it. Answer inline under each `>`.

## The placeholder page (the criterion CI proves only halfway)

### Does http://192.168.1.94:8000/aura render a styled AuraOS card with a working click-counter button?

_Why this matters: CI only asserts the HTML shell serves; a broken asset path or CSS failure would still pass that test. Your eyes are the real check on "the Vue toolchain works end-to-end"._

>

### Does the page also load on your phone's browser?

_Why this matters: the spec's expense-logging flows (T8) assume Linh works from a phone on a shoot; catching a mobile-hostile toolchain now is cheap._

>

## Login and Desk

### Can you log in at http://192.168.1.94:8000 as Administrator / admin and reach the Desk?

>

### In the Desk, can you find the DocType "Founder Spike Note" and open/create one?

_Why this matters: proves the app's schema actually installed into the site you're looking at, not just the CI site._

>

## The permission boundary (worth one manual pass before sensitive data exists)

### Create a user for yourself with only the "Founder" role, log in as it, and open a Founder Spike Note. Does it work?

>

### Create a second user with only the "Producer" role, log in as it, and try to reach Founder Spike Note - via the search bar and by URL (`/app/founder-spike-note`). Is it fully invisible/blocked?

_Why this matters: the automated proof covers document API, list API, REST, and global search. A human poking the actual UI is the last access path nobody scripted._

>

## Evening-maintenance reality

### Open README.md and follow only its instructions to check on the deployment (logs, restart). Could you do it without asking Claude?

_Why this matters: the acceptance criterion is "instructions suited to evening-hobby maintenance" - the only qualified judge of that is you._

>

### Is one first-boot on your own machine or a fresh container worth doing before merge, or do you accept the LXC boot as proof the compose file works?

_Why this matters: the compose path has been booted exactly once, on this LXC. Accepting that is fine - but it should be a decision, not an oversight._

>

## Anything else?

### Anything you saw during the walkthrough - slow pages, odd wording, a worry about T2+ - that we didn't ask about?

>

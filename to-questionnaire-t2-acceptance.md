# T2 acceptance walkthrough — are Contacts done?

**Purpose:** decide whether ticket [#4 (T2: Contacts)](https://github.com/nosuper/10082026-OS/issues/4) is complete — merge [PR #17](https://github.com/nosuper/10082026-OS/pull/17) to `main` and unblock T3 — or send it back for fixes.

**From:** Claude (the implementing agent) — **To:** the founder, plus the next Claude session — **How your answers will be used:** the next session reads this file, treats every "yes" as a verified acceptance criterion, and merges (or fixes) accordingly.

## Context

Automation is green: 26/26 Frappe site tests (required fields, company linking, multi role tags, role access via document and REST APIs, negative access for a role-less user), 10/10 pure pytest, and a live REST smoke on the test site. You reported a reload loop on `/aura/contacts` — that was a real bug (missing CSRF token turned the guest-redirect into a login ping-pong); it's fixed and deployed. What automation cannot see: whether the page behaves in a real browser, whether the form fits how you actually record parties, and two scope decisions I made that you may veto. The test site is **http://192.168.1.94:8000/aura/contacts** (Desk login at http://192.168.1.94:8000, `Administrator` / `admin`).

## How to answer

10–15 minutes at a browser on your LAN. **Hard-refresh first (Ctrl+Shift+R)** — your browser cached the broken bundle. Partial answers and "I don't know" are useful — flag anything unsure rather than skipping it. Answer inline under each `>`.

## The reload-loop fix (your bug report)

### After a hard refresh, does /aura/contacts load once and stay put — no reload loop — while logged in?

_Why this matters: this is the bug you hit; a stale cached bundle can make it look unfixed._

>

### Log out and open /aura/contacts. Are you bounced to the login page once, and returned to Contacts after logging in?

>

## Create, edit, browse (the ticket's core criterion)

### Create a company via "New Company" — name, tax code, bank details, a role tag. Does it save and appear in the list?

_Why this matters: saving from the UI is the exact path the CSRF bug broke; the REST smoke test bypassed it._

>

### Create a person via "New Person" — link them to that company with the autocomplete, tick two role tags (e.g. Vendor + Freelancer). Reopen the record: are the company link and both tags still there?

>

### Edit an existing record (change a phone number, add a tag). Do the changes stick after reopening?

>

### Enter a real Vietnamese name and address with full diacritics (e.g. "Nguyễn Trần Phương Thảo"). Does it display correctly in the list and dialog after saving?

_Why this matters: English UI holding Vietnamese data is a spec requirement; encoding bugs surface exactly here._

>

### Does the search box and the role-tag filter ("All roles" dropdown) narrow the list the way you'd expect — could you find a party "in seconds"?

>

## The producer's seat

### Log in as the Producer-role user (Linh's account) and open /aura/contacts. Can she see and edit companies and people?

_Why this matters: "both founder and producer can find and edit any party" is an acceptance criterion; automated tests prove the permission, not the UI experience._

>

### Open /aura/contacts on a phone browser. Is the list usable and can a record be opened and edited?

_Why this matters: Linh works from a phone on shoots; contacts is her first daily screen._

>

## Scope decisions you may veto (I chose, you decide)

### I added fields beyond the ticket: website/address/notes on companies; Zalo, CCCD (ID number), notes on people. Keep them, or trim any?

_Why this matters: unrequested fields are clutter if you'll never fill them; removal is cheap now, annoying after data exists._

>

### Producer can also **delete** parties (ticket only required read/write). Keep, or make delete founder-only?

_Why this matters: this is an access-policy decision the spec didn't make — it should be yours, not mine._

>

### Role tags are Client / Vendor / Freelancer, growable by you in Desk (Party Role). Does this vocabulary match how you think about parties, or is something missing (e.g. "Partner", "Accountant")?

>

## Anything else?

### Anything you saw during the walkthrough — slow pages, odd wording, a worry about T3+ — that we didn't ask about?

>

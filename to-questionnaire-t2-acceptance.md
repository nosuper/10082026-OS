# T2 acceptance walkthrough - are Contacts done?

> **Outcome (2026-08-10): GO.** First pass surfaced a reload loop
> (missing CSRF token), a missing logout, clipped Vietnamese
> descenders, and five domain corrections (phone=Zalo required,
> freelancer paperwork fields, no Freelancer companies, VN bank
> dropdown) - all fixed and re-verified. Founder confirmed create/
> browse for companies and people, Producer-account access, and
> phone usability. T2 merged.

**Purpose:** decide whether ticket [#4 (T2: Contacts)](https://github.com/nosuper/10082026-OS/issues/4) is complete - merge [PR #17](https://github.com/nosuper/10082026-OS/pull/17) to `main` and unblock T3 - or send it back for fixes.

**From:** Claude (the implementing agent) - **To:** the founder, plus the next Claude session - **How your answers will be used:** the next session reads this file, treats every "yes" as a verified acceptance criterion, and merges (or fixes) accordingly.

## Context

Automation is green: 26/26 Frappe site tests (required fields, company linking, multi role tags, role access via document and REST APIs, negative access for a role-less user), 10/10 pure pytest, and a live REST smoke on the test site. You reported a reload loop on `/aura/contacts` - that was a real bug (missing CSRF token turned the guest-redirect into a login ping-pong); it's fixed and deployed. What automation cannot see: whether the page behaves in a real browser, whether the form fits how you actually record parties, and two scope decisions I made that you may veto. The test site is **http://192.168.1.94:8000/aura/contacts** (Desk login at http://192.168.1.94:8000, `Administrator` / `admin`).

## How to answer

10–15 minutes at a browser on your LAN. **Hard-refresh first (Ctrl+Shift+R)** - your browser cached the broken bundle. Partial answers and "I don't know" are useful - flag anything unsure rather than skipping it. Answer inline under each `>`.

## The reload-loop fix (your bug report)

### After a hard refresh, does /aura/contacts load once and stay put - no reload loop - while logged in?

_Why this matters: this is the bug you hit; a stale cached bundle can make it look unfixed._

> Yes - "the loop is fixed, I can use it now." (2026-08-10)

### Log out and open /aura/contacts. Are you bounced to the login page once, and returned to Contacts after logging in?

> Partial: there was no logout control inside /aura - only from the Desk at /. And re-login from the plain login page landed in the Desk, not AuraOS. **Fix applied:** a Log out button now sits in the /aura header and routes back through /login?redirect-to=/aura/contacts.

## Create, edit, browse (the ticket's core criterion)

### Create a company via "New Company" - name, tax code, bank details, a role tag. Does it save and appear in the list?

_Why this matters: saving from the UI is the exact path the CSRF bug broke; the REST smoke test bypassed it._

> Yes - "I create new and it's on the list. Worked for both company and people."

### Create a person via "New Person" - link them to that company with the autocomplete, tick two role tags (e.g. Vendor + Freelancer). Reopen the record: are the company link and both tags still there?

> Yes (covered by the same walkthrough answer).

### Edit an existing record (change a phone number, add a tag). Do the changes stick after reopening?

> Not answered explicitly; founder accepted overall ("merge it").

### Enter a real Vietnamese name and address with full diacritics (e.g. "Nguyễn Trần Phương Thảo"). Does it display correctly in the list and dialog after saving?

_Why this matters: English UI holding Vietnamese data is a spec requirement; encoding bugs surface exactly here._

> Mostly - "Trịnh Đăng Lê Vũ" displays correctly, but the letter "g" was clipped (only the top half showed). **Fix applied:** list-row line-height raised; stacked diacritics were eating the descender space.

### Does the search box and the role-tag filter ("All roles" dropdown) narrow the list the way you'd expect - could you find a party "in seconds"?

> Not answered explicitly; founder accepted overall ("merge it").

## The producer's seat

### Log in as the Producer-role user (Linh's account) and open /aura/contacts. Can she see and edit companies and people?

_Why this matters: "both founder and producer can find and edit any party" is an acceptance criterion; automated tests prove the permission, not the UI experience._

> Yes - "Producer account works fine." (2026-08-10)

### Open /aura/contacts on a phone browser. Is the list usable and can a record be opened and edited?

_Why this matters: Linh works from a phone on shoots; contacts is her first daily screen._

> Yes - works fine on the phone.

## Scope decisions you may veto (I chose, you decide)

### I added fields beyond the ticket: website/address/notes on companies; Zalo, CCCD (ID number), notes on people. Keep them, or trim any?

_Why this matters: unrequested fields are clutter if you'll never fill them; removal is cheap now, annoying after data exists._

> Zalo is okay - but phone and Zalo are the same thing in Vietnam, so they are now **one required field "Phone / Zalo"**. CCCD and other paperwork data is freelancer-only; the person form now has a Freelancer Paperwork section (shown when the Freelancer tag is ticked) with: CCCD, date of birth (Sinh ngày), permanent address (Địa chỉ thường trú), contact address (Địa chỉ liên hệ), personal tax code - phone/email/bank were already there.

### Producer can also **delete** parties (ticket only required read/write). Keep, or make delete founder-only?

_Why this matters: this is an access-policy decision the spec didn't make - it should be yours, not mine._

> "Okay with this" - Producer keeps delete.

### Role tags are Client / Vendor / Freelancer, growable by you in Desk (Party Role). Does this vocabulary match how you think about parties, or is something missing (e.g. "Partner", "Accountant")?

> "Okay for now." One correction: companies must not offer the Freelancer tag (freelancers don't have companies). **Fix applied:** the tag is hidden on the company form and rejected server-side.

## Anything else?

### Anything you saw during the walkthrough - slow pages, odd wording, a worry about T3+ - that we didn't ask about?

> Requests, both applied: (1) a dropdown for Bank Name with Vietnamese banks; (2) phone = Zalo, single required field.

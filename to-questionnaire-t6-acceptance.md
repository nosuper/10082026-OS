# T6 acceptance walkthrough — is the hosted quote page done?

**Purpose:** decide whether ticket [#8 (T6: Hosted quote page — versions, token URL, PDF, silence nudge)](https://github.com/nosuper/10082026-OS/issues/8) is complete — merge to `main` and close the deal-losing triad (track → price → send) — or send it back for fixes.

**From:** Claude (the implementing agent) — **To:** the founder, plus the next Claude session — **How your answers will be used:** the next session reads this file, treats every "yes" as a verified acceptance criterion, applies the fixes you ask for, and merges (or opens follow-up tickets) accordingly.

## Context

T6 is the first thing in this system a **person outside the company** will ever see. Publishing a breakdown freezes its packages and totals into a numbered version with its own random link; the client opens that link with no login, downloads a PDF of the same page, and we record every open. You mark a version sent, then confirmed; a sent quote that goes quiet past a configurable window gets flagged on the board.

What automation covers: 138 pure tests (the guest field whitelist, which version speaks for a deal, the nudge condition) all green on this machine. 23 new Frappe site tests — token access, version immutability, the guest serialization boundary, open events, PDF/page parity, the nudge — are written but **have not been run yet**: this machine has no bench and no Docker, so CI is their first run. Treat their result as a gate before you merge, not as something already proven.

What automation cannot see: whether a page you'd actually send a client looks like a quote from your company, whether the English wording is right, whether the publish → send → chase loop fits how you and Linh really work, and four scope decisions I made that you may veto.

## How to answer

20–25 minutes, with one real deal's breakdown already built (the T5 walkthrough deal is fine). Answer inline under each `>`. Partial answers and "I don't know" are useful — flag anything you're unsure of rather than skipping it.

**Before you start:** the T6 branch has to be deployed to the test site (192.168.1.94) — the quote link only means anything on a real hostname. Ask the next session to deploy it, then **hard-refresh (Ctrl+Shift+R)**. Open a deal → **₫ Breakdown** → the **Client-facing quote** panel is on the right, under the totals.

## Publishing and versions (the ticket's headline)

### Publish a quote from a real breakdown. Open the link it gives you in a private/incognito window — no login. Is what the client sees the offer you meant to send?

_Why this matters: this is the one screen in the whole system a client reads. Everything else is scaffolding around it._

>

### Change a package price on the breakdown and publish again. Does the **first** link still show the old price, unchanged, while the new link shows the new one?

_Why this matters: "wrong version sent" is the failure versioning exists to stop — the old link must keep saying exactly what the client already read._

>

### Is version numbering (v1, v2, v3…) enough for you to know which one you sent to whom, or do you need to name versions ("after the call", "budget cut")?

>

### Try opening a made-up link — take a real quote URL and change a few characters. Do you get a plain 404 rather than anything about the deal?

>

## What the client sees

### Read the page as a client would. Is anything on it a number or a word a client must never see?

_Why this matters: the code enforces a whitelist — the client can only see fields we named deliberately — but you know what "internal" means better than the whitelist does._

>

### Is the page presentable enough to send to a real client tomorrow, or does it need your branding first — logo, company name and tax code, contact block, payment terms?

_Why this matters: I built the page with no branding at all. If it needs your letterhead to be sendable, that's a fix now, not a follow-up._

>

### The page is in English (Package / Subtotal / Management fee / VAT / Total), as the spec asks. Is English right for every client you'd send this to, or do some need Vietnamese?

>

### Package title, description and price are all the client sees per package. Is a description enough to explain what they're buying, or do you need line-level detail (without the costs) for some jobs?

>

### There's a free-text note under the totals (validity, payment terms). Is one note block enough, or do you want standing terms that appear on every quote automatically?

>

## PDF

### Hit **Download PDF** on the quote page. Is the PDF the same offer as the page, and would you attach it to a Zalo message as-is?

>

### Is a PDF that looks like the web page what you want, or should the PDF look like a formal document (letterhead, signature block, page numbers)?

>

## Opens and follow-up timing

### Open a quote link from your phone (mobile data, not office wifi). Back in the panel, click the opens count. Does the log show that open, with a time you'd trust?

_Why this matters: story 22 is about **when** it was opened, because that's what decides when you chase._

>

### Page opens and PDF downloads are counted separately. Is that split useful to you, or just noise?

>

### Every open is recorded — including yours and Linh's when you check the link. Should we try to exclude internal opens, or is a raw count you interpret yourself fine?

>

## Sent, confirmed, and the silence nudge

### Mark a version **sent**. Does the deal move to Quote Sent on the board, and does the deal show the send date?

>

### Set the silence window in Settings to 1 day, then have the next session backdate a sent quote. Does the ⏰ **Silent** badge appear on the board card?

>

### What is the right silence window in real life — 3 days, 5, 7? (It's one number in Settings; I defaulted to 5.)

_Why this matters: too short and you nag good clients; too long and deals die of silence, which is the whole reason this exists._

>

### A badge on the card is the whole nudge — no email, no daily digest. Is seeing it when you open the board enough, or do you need it pushed to you?

>

### **Confirmed** currently means only "the client said yes" — it doesn't move the deal to Won or create anything. Is that the right boundary, or should confirming a quote do more?

>

## Scope decisions you may veto (I chose, you decide)

### Marking a quote sent **automatically moves the deal to Quote Sent** (only from the earlier stages — a deal already in Negotiation is left alone). Keep, or should marking sent change only the quote's status and leave the board to you?

_Why this matters: the reviewer called this scope creep — the ticket asks for status on the deal, not stage changes. I kept it because story 25 says pipeline state should reflect reality. Your call decides it._

>

### Every open stores the viewer's **IP address and browser**, visible to you and Linh. Useful for telling a real client open from your own, or more visitor tracking than you want to keep?

>

### A quote link **never expires** and has no password — anyone the client forwards it to can read it forever. Fine for v1, or do you want links to expire (say 30 days) or be revocable?

_Why this matters: the token is the only lock on that page. Adding expiry later is easy; deciding you needed it after a link leaks is not._

>

### Published versions **cannot be edited** — a typo in a package description means publishing v2. You can still delete a version outright (that 404s its link). Is "publish a new version" an acceptable fix for a typo, or do you need to correct a live page?

>

## Anything else?

### Anything you saw during the walkthrough — wording on the client page, something missing before you'd send this to a real client, a worry about T7 (won deal → job) — that we didn't ask about?

>

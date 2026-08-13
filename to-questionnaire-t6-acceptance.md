# T6 acceptance walkthrough - is the hosted quote page done?

> **Outcome (2026-08-10): GO on the ticket's own criteria, with the
> quote page explicitly not client-ready yet.** The founder confirmed
> publishing, versioning, the guest link, the PDF and the sent/confirmed
> loop all work. Four fixes applied during the walkthrough: a plain
> "Quote not found" page instead of Frappe's error screen, cost lines
> outside every package now publish as their own standalone entries
> (the founder's veto), an accidental "confirmed" can be undone, and the
> quote link now shows on the deal card. Deferred to follow-up issues:
> branding and formal-document layout ([#31](https://github.com/nosuper/10082026-OS/issues/31)),
> margin following the price the client actually pays
> ([#32](https://github.com/nosuper/10082026-OS/issues/32) - the one
> open correctness gap), richer open tracking
> ([#33](https://github.com/nosuper/10082026-OS/issues/33)), link names /
> expiry / revocation ([#34](https://github.com/nosuper/10082026-OS/issues/34)),
> and the immutability-vs-live-edit decision
> ([#35](https://github.com/nosuper/10082026-OS/issues/35)). The revision
> round-trip went to T7 ([#9](https://github.com/nosuper/10082026-OS/issues/9)).

**Purpose:** decide whether ticket [#8 (T6: Hosted quote page - versions, token URL, PDF, silence nudge)](https://github.com/nosuper/10082026-OS/issues/8) is complete - merge to `main` and close the deal-losing triad (track → price → send) - or send it back for fixes.

**From:** Claude (the implementing agent) - **To:** the founder, plus the next Claude session - **How your answers will be used:** the next session reads this file, treats every "yes" as a verified acceptance criterion, applies the fixes you ask for, and merges (or opens follow-up tickets) accordingly.

## Context

T6 is the first thing in this system a **person outside the company** will ever see. Publishing a breakdown freezes its packages and totals into a numbered version with its own random link; the client opens that link with no login, downloads a PDF of the same page, and we record every open. You mark a version sent, then confirmed; a sent quote that goes quiet past a configurable window gets flagged on the board.

What automation covers: 142 pure tests and 28 Frappe site tests - token access, version immutability, the guest serialization boundary, open events, PDF/page parity, the nudge - all green on the test box. Running them there for the first time turned up three real bugs, now fixed; one of them changes pricing behaviour you need to sign off on (the first two questions under **Packages and what the client pays**). Two unrelated tests still fail on that box, on 56 leftover rows from the buggy build - nothing to do with the code, and CI builds a clean site each run.

What automation cannot see: whether a page you'd actually send a client looks like a quote from your company, whether the English wording is right, whether the publish → send → chase loop fits how you and Linh really work, and four scope decisions I made that you may veto.

## How to answer

20–25 minutes, with one real deal's breakdown already built (the T5 walkthrough deal is fine). Answer inline under each `>`. Partial answers and "I don't know" are useful - flag anything you're unsure of rather than skipping it.

**Before you start:** T6 is already deployed to the test site - open **http://192.168.1.94:8000/aura/deals** and **hard-refresh (Ctrl+Shift+R)**. Open a deal → **₫ Breakdown** → the **Client-facing quote** panel is on the right, under the totals. Two things to know about that box: it was serving T7 until this deploy, so T7's job data on it is gone (its code is safe on its own branch); and quote links there are `http://192.168.1.94:8000/quote/<token>`, which only work inside the office network - judge the page, not the shareability.

## Publishing and versions (the ticket's headline)

### Publish a quote from a real breakdown. Open the link it gives you in a private/incognito window - no login. Is what the client sees the offer you meant to send?

_Why this matters: this is the one screen in the whole system a client reads. Everything else is scaffolding around it._

> "Incognito worked."

### Change a package price on the breakdown and publish again. Does the **first** link still show the old price, unchanged, while the new link shows the new one?

_Why this matters: "wrong version sent" is the failure versioning exists to stop - the old link must keep saying exactly what the client already read._

> "Worked."

### Is version numbering (v1, v2, v3…) enough for you to know which one you sent to whom, or do you need to name versions ("after the call", "budget cut")?

> "It's okay for now. Later custom link name function." **Deferred to [#34](https://github.com/nosuper/10082026-OS/issues/34)** (named links, alongside expiry and revocation).

### Try opening a made-up link - take a real quote URL and change a few characters. Do you get a plain 404 rather than anything about the deal?

> "It shows a screen like attached → I prefer with only 404 link than code block showing like this." **Fix applied:** a dead link now renders a plain "Quote not found" page - one sentence telling the reader to ask for a current link - at HTTP 404, instead of falling through to Frappe's error screen with its traceback. Verified live on the test site; a site test asserts the page carries no traceback.

## Packages and what the client pays

### Override a package price upward (round 58.4m up to 60m), publish, and look at the client's Total. It is now **1.6m higher** than before the rounding. Is that what rounding a package up should mean - you charge more?

_Why this matters: this is the one behaviour the deployment changed. Until now the override moved only the package's printed price and the internal variance; the total you charged came from the cost lines and never moved, so the page showed an offer that didn't add up to its own Total. I made the client's Total follow the package prices. The alternative is that rounding is cosmetic - the client's Total stays put and one package silently subsidises another._

> "Yes, and quote worked, the new version updated with override price - but the breakdown still uses the markup price to calculate the margin." **Confirmed, and a real gap found:** the client now pays the overridden price, but the breakdown's margin, margin %, floor warning and the founder profit chain all still start from the line-based total, so they are wrong by the amount of any override. **Raised as [#32](https://github.com/nosuper/10082026-OS/issues/32)** - the one open correctness issue on this ticket. It was left out of T6 because it changes T5's stored numbers and the whole profit chain, which deserves its own test pass rather than a walkthrough patch.

### Because of that, publishing now **refuses** if any cost line belongs to no package, telling you which line to assign. Right call, or do you need to publish with lines left out?

_Why this matters: with the Total built from package prices, an unassigned line is money we'd quietly absorb. Refusing is the safe reading - but if you deliberately keep some costs out of the client's offer (contingency you're absorbing on purpose), this blocks a real workflow and should be a warning instead._

> "Some line items are standalone package. We just markup it and build quote, not assign to any package." **Vetoed - fix applied:** the refusal is gone. A cost line in no package now publishes as its own client-facing entry, titled with the line's description and priced at its marked-up quote price, listed after the real packages. Nothing is absorbed and nothing is blocked. Publishing is only refused when there is nothing at all to show.

### The client sees Subtotal → Management fee (10%) → VAT (8%) → Total as separate lines. Is showing the management fee to the client right, or should it be folded into the package prices?

_Why this matters: it's a one-line change now and an awkward conversation with a client later._

> "Correct." Kept as separate lines.

## What the client sees

### Read the page as a client would. Is anything on it a number or a word a client must never see?

_Why this matters: the code enforces a whitelist - the client can only see fields we named deliberately - but you know what "internal" means better than the whitelist does._

> "It's okay for now. We just need to customize and branded this page later." No leak found; branding **deferred to [#31](https://github.com/nosuper/10082026-OS/issues/31)**.

### Is the page presentable enough to send to a real client tomorrow, or does it need your branding first - logo, company name and tax code, contact block, payment terms?

_Why this matters: I built the page with no branding at all. If it needs your letterhead to be sendable, that's a fix now, not a follow-up._

> "As I said above. It needs to be more detail, more polish with branding." **Deferred to [#31](https://github.com/nosuper/10082026-OS/issues/31).** Treat the page as internally correct but not yet client-ready - that ticket is the gate before a real client sees one.

### The page is in English (Package / Subtotal / Management fee / VAT / Total), as the spec asks. Is English right for every client you'd send this to, or do some need Vietnamese?

> "Nah, it's okay." English stands.

### Package title, description and price are all the client sees per package. Is a description enough to explain what they're buying, or do you need line-level detail (without the costs) for some jobs?

> "Yes, it's need a section divider, I may break it into other phase…" **Deferred to [#31](https://github.com/nosuper/10082026-OS/issues/31)** (section dividers by phase, more per-package detail).

### There's a free-text note under the totals (validity, payment terms). Is one note block enough, or do you want standing terms that appear on every quote automatically?

> "1 is enough for now, but can add function to add, remove section." **Deferred to [#31](https://github.com/nosuper/10082026-OS/issues/31)** (add/remove sections).

## PDF

### Hit **Download PDF** on the quote page. Is the PDF the same offer as the page, and would you attach it to a Zalo message as-is?

> Answered together with the next question.

### Is a PDF that looks like the web page what you want, or should the PDF look like a formal document (letterhead, signature block, page numbers)?

> "Yes. It should look like formal document, so we can print out and attach like an appendix of contract." **Deferred to [#31](https://github.com/nosuper/10082026-OS/issues/31)** - and it raises the bar there: the PDF is not just a styled page, it's a contract appendix.

## Opens and follow-up timing

### Open a quote link from your phone (mobile data, not office wifi). Back in the panel, click the opens count. Does the log show that open, with a time you'd trust?

_Why this matters: story 22 is about **when** it was opened, because that's what decides when you chase._

> "I see the logs, but it should be more detail like which device opened, location…" Logging works; **detail deferred to [#33](https://github.com/nosuper/10082026-OS/issues/33)**.

### Page opens and PDF downloads are counted separately. Is that split useful to you, or just noise?

> "Whatever. Need a long run test." Kept as is; revisit once there's real traffic.

### Every open is recorded - including yours and Linh's when you check the link. Should we try to exclude internal opens, or is a raw count you interpret yourself fine?

> Not answered directly, but covered by the "which device, location" ask - **telling internal opens from client opens is part of [#33](https://github.com/nosuper/10082026-OS/issues/33)**.

## Sent, confirmed, and the silence nudge

### Mark a version **sent**. Does the deal move to Quote Sent on the board, and does the deal show the send date?

> "Yes, but need a redo / automatically change stage if need revision after feedback. And if I marked confirmed by accident, no turning back." **Two outcomes:** the revision round-trip is a T7 concern and was **raised on [#9](https://github.com/nosuper/10082026-OS/issues/9)**; the one-way confirm is **fixed** - marking a confirmed quote sent again withdraws the confirmation and keeps the original send time. The button reads "Undo confirm" on a confirmed version.

### Set the silence window in Settings to 1 day, then have the next session backdate a sent quote. Does the ⏰ **Silent** badge appear on the board card?

> "No, I don't see the badge." **Not a bug - no data could trigger it.** The only deal with a quote was DEAL-0009, confirmed and sent the same day: confirmed quotes are never nudged, and nothing had aged. **A demo deal now exists on the test site** - "NUDGE DEMO - silent 8 days" (DEAL-0012), sent 8 days ago and still open - and the nudge query returns it, so the badge renders on its card. Worth 30 seconds to confirm you can see it.

### What is the right silence window in real life - 3 days, 5, 7? (It's one number in Settings; I defaulted to 5.)

_Why this matters: too short and you nag good clients; too long and deals die of silence, which is the whole reason this exists._

> "5 day is good, will track and see." Default kept at 5.

### A badge on the card is the whole nudge - no email, no daily digest. Is seeing it when you open the board enough, or do you need it pushed to you?

> "Yes, I think so." Board badge is enough for v1.

### **Confirmed** currently means only "the client said yes" - it doesn't move the deal to Won or create anything. Is that the right boundary, or should confirming a quote do more?

> "Keep."

## Scope decisions you may veto (I chose, you decide)

### Marking a quote sent **automatically moves the deal to Quote Sent** (only from the earlier stages - a deal already in Negotiation is left alone). Keep, or should marking sent change only the quote's status and leave the board to you?

_Why this matters: the reviewer called this scope creep - the ticket asks for status on the deal, not stage changes. I kept it because story 25 says pipeline state should reflect reality. Your call decides it._

> "Yes." Kept - the reviewer's scope-creep objection is overruled by the founder.

### Every open stores the viewer's **IP address and browser**, visible to you and Linh. Useful for telling a real client open from your own, or more visitor tracking than you want to keep?

> Answered above - he wants **more**, not less: device and location. See [#33](https://github.com/nosuper/10082026-OS/issues/33).

### A quote link **never expires** and has no password - anyone the client forwards it to can read it forever. Fine for v1, or do you want links to expire (say 30 days) or be revocable?

_Why this matters: the token is the only lock on that page. Adding expiry later is easy; deciding you needed it after a link leaks is not._

> "Add both of it, but for later." **Deferred to [#34](https://github.com/nosuper/10082026-OS/issues/34)** (expiry + revocation).

### Published versions **cannot be edited** - a typo in a package description means publishing v2. You can still delete a version outright (that 404s its link). Is "publish a new version" an acceptable fix for a typo, or do you need to correct a live page?

> "I think edit live is great." **Conflicts with the ticket's immutability criterion, so it needs a decision rather than a patch - raised as [#35](https://github.com/nosuper/10082026-OS/issues/35)** with a proposed middle path: editable while Published, frozen once Sent, so nothing changes under a client who is already holding the link.

## Anything else?

### Anything you saw during the walkthrough - wording on the client page, something missing before you'd send this to a real client, a worry about T7 (won deal → job) - that we didn't ask about?

> "Quote link (maybe the latest or all version) should show in the deal card. UI need a tweak but maybe it for later." **Fix applied** for the link: each board card now carries a 🔗 v*N* button opening the current version's client page in a new tab. Showing *all* versions on the card, and the broader UI tweak, **deferred to [#31](https://github.com/nosuper/10082026-OS/issues/31)**.

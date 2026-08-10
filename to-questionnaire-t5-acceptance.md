# T5 acceptance walkthrough — is the breakdown & quote editor done?

> **Outcome (2026-08-10): GO, pending founder's merge call.** All
> walkthrough checks passed; the math matches the xlsx to the đồng and
> the producer/founder boundary held. Four fixes applied before merge:
> Cty 10% removed from the offered tax types, floor setting moved to a
> founder-only Settings page, direct ₫ Breakdown shortcut on board
> cards, and inline package creation from a line's package cell.
> Deferred to follow-up tickets: cost-line metadata fields
> (category/phase/source), drag-to-reorder + breakdown UI polish +
> standalone entry point, and the floor-derivation session (parallel
> with T6). Note: PR #22 and PR #23 (T3.1/T3.2) overlap on 8 files —
> whichever merges second resolves conflicts.

**Purpose:** decide whether ticket [#7 (T5: Breakdown & quote editor)](https://github.com/nosuper/10082026-OS/issues/7) is complete — merge [PR #22](https://github.com/nosuper/10082026-OS/pull/22) to `main` and unblock T6 (hosted quote page) — or send it back for fixes.

**From:** Claude (the implementing agent) — **To:** the founder, plus the next Claude session — **How your answers will be used:** the next session reads this file, treats every "yes" as a verified acceptance criterion, and merges (or fixes) accordingly.

## Context

Automation is green: 28 new Frappe site tests for T5 (stored values agree with the pricing engine, package sum/override/variance, floor behavior, and the permission battery — producer blind to commission via document API, list API, and global-search content), 79/79 whole-app site tests on the box, 108 pure pytest, CI green on a clean checkout. What automation cannot see: whether the editor grid is usable for real breakdown work, whether the numbers match the xlsx you trust, and several scope decisions I made that you may veto. The test site serves the T5 branch: open **http://192.168.1.94:8000/aura/deals**, open any deal, hit **"Breakdown & Quote →"** in the dialog. **Hard-refresh first (Ctrl+Shift+R).** For producer-view checks, log in as your Producer test account; as Administrator/Founder you see everything.

## How to answer

15–20 minutes with a real past job's numbers at hand (the debugged xlsx open beside it is ideal). Partial answers and "I don't know" are useful — flag anything unsure rather than skipping it. Answer inline under each `>`.

## The editor and the math (the ticket's headline)

### Rebuild a real past breakdown — the same lines, quantities, unit prices, tax types, vendor MF and markups as your xlsx. Do the line quote prices, subtotal, MF, VAT and total match the spreadsheet to the đồng?

_Why this matters: the xlsx is the normative math; the parity test covers the engine, but this is the first time your own numbers flow through the whole stack._

> Yes — matches to the đồng. Requested extra line fields: item name/category, phase (pre-production / production / post-production / appendix), source (internal / freelancer / vendor). **Deferred to a follow-up ticket** (field vocabularies need founder sign-off; source may become the spec's contact link, story 2).

### While typing, do the computed columns and the totals panel update on their own (about half a second after you stop typing), without pressing anything?

> Yes.

### Reorder lines with ↑ / ↓, delete one, add one back, then Save and hard-refresh. Is the breakdown exactly as you left it?

> Yes — but wants drag-to-reorder instead of arrows. **Deferred to the breakdown-UI polish ticket.**

### Are the tax type labels right as printed — Công ty / Cty 10% / Cá nhân / Không hoá đơn — and do they cover every kind of cost line you actually have?

_Why this matters: adding a tax type later touches the engine, the doctype, and the tests; renaming one now is a one-line change._

> "We don't have Công ty 10%. Company only charge 8%." **Fix applied:** Cty 10% removed from the offered tax types (the engine keeps it — the xlsx stays the math authority). Confirmed: internal work carries no invoice → Không hoá đơn is correct.

### Is a 2-unit line honest to how you cost work — e.g. 2 người × 3 ngày — including the unit labels being free text?

> Yes.

## Packages

### Create two packages (e.g. "Human resources", "Equipment"), assign lines to them, and give one a custom description. Does each package's price equal the sum of its member lines' quote prices?

> "Where to create packages? It should be able to create if isn't exist when breakdown also." **Fix applied:** typing a new name in a line's package cell now creates the package on the spot (datalist input replaces the dropdown). Noted: "This is only breakdown module. I don't see quotation build module" — correct; the client-facing quote page is T6, which renders exactly these packages.

### Override one package's price (round it up or down). Does the variance column show exactly the difference against the member sum, in amber?

_Why this matters: the override is allowed to break the link to cost — but never silently; the variance is the tether._

> Not explicitly answered; covered by automation (variance stored and shown) — no objection raised.

### Delete a package that has member lines. The lines should quietly become ungrouped rather than blocking the save. Is that the right behavior for you?

> Yes.

## The margin floor

### In the founder panel, set the global floor % to something just above the margin of your rebuilt quote. Does a red warning banner appear at the top of the editor?

> Yes.

### Log in as the Producer account, open the same breakdown. Does Linh see the warning banner — while the founder panel (commission, profit chain, floor editor) is entirely absent from her page?

_Why this matters: this is the ticket's central boundary — the warning must reach her without the numbers behind it._

> Yes.

### Still as Producer: can she see everything she needs to price competently — costs, markups, quote prices, and the margin itself?

> Yes.

### Back as founder, set the floor to your intended real value (or leave it 0 = off for now). Spec first-action item: we still owe a session where we derive the true floor from one month of overhead — when do you want to do that?

> "Parallel with T6, create other issues for this." **Follow-up issue created** for the floor-derivation session.

## Founder-only numbers

### In the founder panel, check commission (CMF), CM, lợi nhuận trước thuế, TNDN 20%, net profit, and VAT phải nộp against your xlsx for the same job. Do they match?

> Yes.

### Change the commission % (e.g. 5 → 0) and save. Do the founder numbers move while the producer-visible quote stays identical?

> Yes.

### As Producer, try to find the commission anywhere — the deal dialog, the breakdown page, the Desk list view, global search. Any leak?

_Why this matters: the automated battery covers the API paths; your eyes cover the UI paths a test can't enumerate._

> "I will report later if found." Treated as no leak observed; the automated battery remains the standing proof.

## Scope decisions you may veto (I chose, you decide)

### Founder numbers are never stored — CMF/CM/profit are recomputed on demand and exist only on the breakdown page. This means Desk list views and exports can never show them (a leak-proofing choice), but also that you can't e.g. sort deals by profit in the Desk. Keep?

> "Don't really understand what that mean." **Kept as is** (explained in chat: profit numbers exist only on the breakdown page, never in Desk lists/exports — the leak-proofing choice). Revisit if Desk-side profit views are ever wanted.

### Floor 0 means "off": until you set a real floor, even a loss-making quote raises no warning — and you cannot express a literal 0% floor meaning "warn on any loss". Keep, or should 0 warn on negative margin?

_Why this matters: this is the one behavior in the ticket that silently does nothing until you act._

> "Floor setting should be in another window such as company setting — it should be global variables because it depend on the company finance." **Fix applied:** floor editing moved to a founder-only Settings page (/aura/settings, nav entry visible to founder only); the breakdown panel now just shows the current floor with a link. The 0-means-off behavior stands unchallenged.

### A package price override of 0 ₫ is treated as "no override" (the currency field can't tell empty from zero), so a free package can't be expressed. Fine for v1?

> Fine for v1.

### The editor lives behind "Breakdown & Quote →" inside the deal dialog — two clicks from the board. Fine, or do you want a direct shortcut on the card?

> "Also need direct shortcut with can choose exist deals or create new deal directly in this." **Fix applied:** each board card now has a direct "₫ Breakdown" shortcut. A standalone breakdown entry point with deal picker / create-new is **deferred to the UI polish ticket.**

## Anything else?

### Anything you saw during the walkthrough — sluggish typing in the grid, odd wording, a worry about T6 (the client-facing quote page will render exactly these packages) — that we didn't ask about?

> "Better UI with box border, aligned label, field to better view. No quote view so I can't comment further." **Deferred to the breakdown-UI polish ticket**; the quote view is T6.

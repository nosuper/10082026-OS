# T5 acceptance walkthrough — is the breakdown & quote editor done?

**Purpose:** decide whether ticket [#7 (T5: Breakdown & quote editor)](https://github.com/nosuper/10082026-OS/issues/7) is complete — merge [PR #22](https://github.com/nosuper/10082026-OS/pull/22) to `main` and unblock T6 (hosted quote page) — or send it back for fixes.

**From:** Claude (the implementing agent) — **To:** the founder, plus the next Claude session — **How your answers will be used:** the next session reads this file, treats every "yes" as a verified acceptance criterion, and merges (or fixes) accordingly.

## Context

Automation is green: 28 new Frappe site tests for T5 (stored values agree with the pricing engine, package sum/override/variance, floor behavior, and the permission battery — producer blind to commission via document API, list API, and global-search content), 79/79 whole-app site tests on the box, 108 pure pytest, CI green on a clean checkout. What automation cannot see: whether the editor grid is usable for real breakdown work, whether the numbers match the xlsx you trust, and several scope decisions I made that you may veto. The test site serves the T5 branch: open **http://192.168.1.94:8000/aura/deals**, open any deal, hit **"Breakdown & Quote →"** in the dialog. **Hard-refresh first (Ctrl+Shift+R).** For producer-view checks, log in as your Producer test account; as Administrator/Founder you see everything.

## How to answer

15–20 minutes with a real past job's numbers at hand (the debugged xlsx open beside it is ideal). Partial answers and "I don't know" are useful — flag anything unsure rather than skipping it. Answer inline under each `>`.

## The editor and the math (the ticket's headline)

### Rebuild a real past breakdown — the same lines, quantities, unit prices, tax types, vendor MF and markups as your xlsx. Do the line quote prices, subtotal, MF, VAT and total match the spreadsheet to the đồng?

_Why this matters: the xlsx is the normative math; the parity test covers the engine, but this is the first time your own numbers flow through the whole stack._

>

### While typing, do the computed columns and the totals panel update on their own (about half a second after you stop typing), without pressing anything?

>

### Reorder lines with ↑ / ↓, delete one, add one back, then Save and hard-refresh. Is the breakdown exactly as you left it?

>

### Are the tax type labels right as printed — Công ty / Cty 10% / Cá nhân / Không hoá đơn — and do they cover every kind of cost line you actually have?

_Why this matters: adding a tax type later touches the engine, the doctype, and the tests; renaming one now is a one-line change._

>

### Is a 2-unit line honest to how you cost work — e.g. 2 người × 3 ngày — including the unit labels being free text?

>

## Packages

### Create two packages (e.g. "Human resources", "Equipment"), assign lines to them, and give one a custom description. Does each package's price equal the sum of its member lines' quote prices?

>

### Override one package's price (round it up or down). Does the variance column show exactly the difference against the member sum, in amber?

_Why this matters: the override is allowed to break the link to cost — but never silently; the variance is the tether._

>

### Delete a package that has member lines. The lines should quietly become ungrouped rather than blocking the save. Is that the right behavior for you?

>

## The margin floor

### In the founder panel, set the global floor % to something just above the margin of your rebuilt quote. Does a red warning banner appear at the top of the editor?

>

### Log in as the Producer account, open the same breakdown. Does Linh see the warning banner — while the founder panel (commission, profit chain, floor editor) is entirely absent from her page?

_Why this matters: this is the ticket's central boundary — the warning must reach her without the numbers behind it._

>

### Still as Producer: can she see everything she needs to price competently — costs, markups, quote prices, and the margin itself?

>

### Back as founder, set the floor to your intended real value (or leave it 0 = off for now). Spec first-action item: we still owe a session where we derive the true floor from one month of overhead — when do you want to do that?

>

## Founder-only numbers

### In the founder panel, check commission (CMF), CM, lợi nhuận trước thuế, TNDN 20%, net profit, and VAT phải nộp against your xlsx for the same job. Do they match?

>

### Change the commission % (e.g. 5 → 0) and save. Do the founder numbers move while the producer-visible quote stays identical?

>

### As Producer, try to find the commission anywhere — the deal dialog, the breakdown page, the Desk list view, global search. Any leak?

_Why this matters: the automated battery covers the API paths; your eyes cover the UI paths a test can't enumerate._

>

## Scope decisions you may veto (I chose, you decide)

### Founder numbers are never stored — CMF/CM/profit are recomputed on demand and exist only on the breakdown page. This means Desk list views and exports can never show them (a leak-proofing choice), but also that you can't e.g. sort deals by profit in the Desk. Keep?

>

### Floor 0 means "off": until you set a real floor, even a loss-making quote raises no warning — and you cannot express a literal 0% floor meaning "warn on any loss". Keep, or should 0 warn on negative margin?

_Why this matters: this is the one behavior in the ticket that silently does nothing until you act._

>

### A package price override of 0 ₫ is treated as "no override" (the currency field can't tell empty from zero), so a free package can't be expressed. Fine for v1?

>

### The editor lives behind "Breakdown & Quote →" inside the deal dialog — two clicks from the board. Fine, or do you want a direct shortcut on the card?

>

## Anything else?

### Anything you saw during the walkthrough — sluggish typing in the grid, odd wording, a worry about T6 (the client-facing quote page will render exactly these packages) — that we didn't ask about?

>

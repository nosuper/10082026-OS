# T3.3 acceptance walkthrough - is the editable deals table done?

**Purpose:** decide whether [#27 (T3.3: Deals table UX)](https://github.com/nosuper/10082026-OS/issues/27) is complete, or whether inline editing, blank-row creation, configurable columns, or remembered views need fixes.

**From:** Codex (the implementing agent) - **To:** the founder, plus the next agent session - **How your answers will be used:** the next session will treat each “yes” as a verified acceptance criterion and turn any failed or awkward check into a concrete fix.

## Context

T3.3 changes `/aura/deals` so the Table view is a working surface rather than a read-only list. Cells can be edited in place, a blank first row creates deals without opening the card, only the deal title opens the existing card dialog, optional columns can be hidden, and each logged-in user’s column and Board/Table choices are remembered in that browser. Server saves still pass through the same Deal validation as the dialog. Automation is green: all 42 focused Deal tests, 190 whole-app Frappe tests, and 152 pure tests pass, and the frontend production build succeeds. What automation cannot establish is whether editing the table is fast and clear enough for daily use.

## How to answer

Allow 10–15 minutes in a browser. Open **http://192.168.1.94:8000/aura/deals** and hard-refresh first (**Ctrl+Shift+R**). Use a disposable deal where possible. Answer directly under each `>`. Partial answers and “I don’t know” are useful-flag uncertainty rather than skipping a check.

## Inline editing

### Switch to Table, click a Company, Stage, Owner, Budget, Source, or Project Type cell, change it, then reload. Did the saved value survive the reload?

_Why this matters: this is the main speed improvement-ordinary changes should no longer require opening and saving the full deal card._

>

### Click the pencil beside a deal title, change the title, press Enter, and reload. Did the new title persist?

>

### Edit a deal’s Tags cell using comma-separated existing tags. After leaving the cell and reloading, are exactly those tags shown?

>

### Enter `-1` in a Budget cell. Does the table reject it with a useful error while the previously saved budget remains unchanged after reload?

_Why this matters: inline editing must not bypass the validation already enforced by the deal card._

>

### Change a Stage cell to Lost. Are you required to provide a lost reason before the deal moves?

>

## Creating a deal as a row

### Fill Title and Company in the blue blank row, optionally fill the other visible fields, then click Add. Is the deal created without the card dialog opening?

>

### Reload after creating that deal. Is it still present with Brief Received as its default stage and you as its owner unless you selected someone else?

>

### Try Add with Title or Company empty. Is creation rejected without producing a partial or broken deal?

>

## Click behavior

### Click the title of an existing deal. Does it open the same full card dialog as before?

>

### Click elsewhere in that row. Does an editable cell become an editor without the card dialog opening?

>

### Return to Board and open, drag, and save a deal. Does the original board workflow still behave normally?

_Why this matters: T3.3 changes the Table interaction, not the established Board behavior._

>

## Columns and remembered choices

### Open Columns and hide several optional columns. After reloading or leaving and returning to Deals, are your selected columns still the ones shown?

>

### Are Title and Company visibly pinned in the column picker so the blank creation row can never lose its required inputs?

>

### Select Table, reload, and leave and revisit `/aura/deals`. Does it consistently return to Table rather than Board?

>

### Log in as the Producer in the same browser. Can that user choose a different view and different columns without changing the founder’s saved choices?

_Why this matters: preferences are separated by logged-in user, even when two people use the same browser._

>

### Preferences currently follow each user only within the browser where they chose them; they do not sync to another phone or computer. Is that sufficient, or must these choices follow the account across devices?

_Why this matters: cross-device preferences require server storage and are a separate implementation decision._

>

## Daily usability

### With a realistic number of deals, does the editable table feel faster than opening cards for routine updates?

>

### On the device where the table will actually be used, are inputs, dropdowns, errors, and the horizontal layout readable and easy to operate?

>

### Is any displayed field incorrectly editable, or is any field you routinely need still read-only or missing?

>

## Anything else?

### Did you notice any lost edits, confusing click target, slow response, awkward wording, or other behavior we did not ask about?

>

# A5 acceptance walkthrough — do the admin pages warn you before the paperwork does?

**Purpose:** decide whether ticket [#61 (A5: Admin pages UX pass)](https://github.com/nosuper/10082026-OS/issues/61) is complete, or send it back for fixes.

**From:** Claude (the implementing agent) — **To:** the founder — **How your answers will be used:** the next Claude session reads this file top to bottom, treats every passed step as a verified acceptance criterion, turns each design answer into either code or a follow-up ticket, and acts on the verdict at the bottom.

## Context

The last Phase A ticket — the three quiet pages. The theme: **say what's missing before it bites.**

- **Contacts** gets a *Paperwork* column: exactly which contract fields a record lacks (companies: tax code / address / bank; people: CCCD / tax code / bank). These are the same holes that print as «thiếu: …» markers on a generated contract — now visible where they can be fixed. Tabs show counts; typing `missing` in search filters to every incomplete record.
- **Settings**: the three warning switches (margin floor, quote silence, payment terms) wear a **"currently off"** chip when 0. While testing I also set the live values on this site: floor 20, terms 7 — so the floor warning and the overdue strip are now ON.
- **Paperwork**: the "Fills:" line wraps as chips instead of running off the card.

## How to answer

**Rough effort:** ~5 minutes.

## 0. Before you start

**http://192.168.1.94:8000/aura** — Ctrl+Shift+R.

## 1. Contacts — the holes

**Do this:** open Contacts. Read the Paperwork column on both tabs; type `missing` into search; click a flagged record and fill one missing field; save.
**Expect:** the label updates (e.g. "missing address, bank" → "missing bank"); counts on the tabs; search finds the incomplete ones.

Pass / fail:

>

## 2. Settings — no more silent zeros

**Do this:** open Settings.
**Expect:** margin floor shows 20 and payment terms 7 (I saved them); silence 5. Set any of them to 0 → an amber **currently off** chip appears next to the label.

Pass / fail:

>

## 3. Paperwork — chips

**Do this:** open Paperwork, look at the template's "Fills:" line.
**Expect:** wrapping chips inside the card, nothing running off the edge; unknown placeholders (if any) amber with a warning icon.

Pass / fail:

>

## 4. Phase A retrospective

This closes Phase A (A1–A5). Before I move to Phase B (tier + positioning fields) and C (hardening gate): across the whole app today, what's the roughest remaining edge you'd want smoothed before your team touches it?

>

## Round 2 — the founder's answers (in-session, 2026-08-13) and what shipped

Paperwork grew three ways on your note: (1) **templates are written and
edited on the website** — "Write one here" opens an editor with every
placeholder as a click-to-insert chip; the .docx is rebuilt server-side
on save; web templates wear a "web" chip and an Edit button (uploaded
Word ones still work, edited in Word); (2) **Generated papers** — every
paper ever generated is registered in one searchable list with who it
was for; (3) generating for **vendor / freelancer** was already wired
(the pickers appear when a template names them) — what was missing was
a template that used it, so the seed ships "Hợp đồng cộng tác viên
(mẫu)", and the freelancer picker now puts the job's own crew first.

### Round-2 checks

**R2.1** Paperwork → Edit "Hợp đồng cộng tác viên (mẫu)": change a
line, click a placeholder chip to insert it, save. Does the Fills list
follow?

>

**R2.2** Open the MV job → Paperwork tab → pick the freelancer contract.
Does a Freelancer picker appear, generate a filled contract, and does
the paper show up under Paperwork → Generated papers?

>

**R2.3** Anything still missing from paperwork before your team uses it?

>

## Round 3 — the founder's answers (in-session, 2026-08-13) and what shipped

(1) Clicking a web template's name opened a download — now it opens the
editor (download lives behind a small icon). (2) The editor became a
document editor: TipTap with the full toolbar (headings, bold/italic/
underline, lists, alignment), and the built .docx keeps that
formatting via a new HTML→Word translator. (3) **Preview & print on
the web**: a Preview button on the job shows the filled paper on
screen, every gap highlighted amber exactly where it would print, and
Print opens the browser's print dialog — the .docx stays as the
record.

### Round-3 checks

**R3.1** Paperwork → click "Hợp đồng cộng tác viên (mẫu)" — does the
rich editor open, looking like the document (centered heading, bold,
bullets)? Format something, save, download the .docx — did it survive?

>

**R3.2** MV job → Paperwork → chọn hợp đồng CTV → Preview với và không
chọn freelancer — gaps amber đúng chỗ? Print ra giấy đẹp?

>

**R3.3** Còn gì thiếu trước khi đóng Phase A?

>

## Round 4 — the founder's answers (in-session, 2026-08-13) and what shipped

Editor and preview both become **document windows** (4xl modals), and
the preview is now a full rich editor holding the filled paper — the
PandaDoc shape: template → filled draft → approve. Type over a gap and
the counter follows; **Print** prints the edited draft; **Save .docx
to job** keeps exactly what you approved (built through the same
HTML→Word translator) and registers it under Generated papers. The
standing instruction — research a feature's market UX before building
it — is recorded in my working memory.

### Round-4 checks

**R4.1** Paperwork → click a web template: does it open as a proper
document window now?

**R4.2** Job → Preview & edit: edit the filled draft (type over a gap),
Print, and Save .docx to job — does the saved file match what you
edited, and appear in Generated papers?

>

## Round 5 — the founder's answers (in-session, 2026-08-13) and what shipped

The rule "titles open a reading window; actions live inside" is now
everywhere: template titles (uploaded ones preview as text, and Edit
converts them to web templates with placeholders carried over),
Generated-papers rows, and the job's documents table. The standalone
Generate button is gone — Preview opens the filled draft and Generate
sits inside it (untouched draft → original file with its Word
formatting; edited draft → what you approved). In the editor,
placeholders are @chips: type @ for suggestions, click a palette chip
to insert; saved back as {{…}}.

### Round-5 checks

**R5.1** Click every kind of title — uploaded template, web template,
generated paper, document on the job. Does each open a window with
Print/Download (and Edit where it belongs), nothing downloading
directly?

>

**R5.2** In the editor, type @ — do the field suggestions appear, and
do inserted chips survive save & regenerate?

>

**R5.3** Job → Preview → Generate inside the window: does the
untouched draft keep your uploaded contract's exact formatting, and an
edited draft save what you approved?

>

## Round 6 — the founder's answers (in-session, 2026-08-13) and what shipped

(1) @ now suggests for real — frappe-ui's own popup dies silently in a
modal, so the editor has its own dropdown: type @, keep typing to
filter, click to insert the chip. (2) Uploaded Word files keep their
look on screen: a symmetric docx→HTML reader carries bold/italic/
underline/alignment/line-breaks into every preview; Word-only styling
stays in the file, which the untouched-draft Generate still uses
byte-for-byte.

### Round-6 checks

**R6.1** Editor: type `@fre` — dropdown at the caret, filtering as you
type, click inserts a chip?

>

**R6.2** Click your uploaded contract's title — does the preview keep
its bold headings and alignment now?

>

## Round 7 — the founder's answers (in-session, 2026-08-13) and what shipped

(1) The generated file's link in the success note now opens the
reading window — the last click-to-download is gone. (2) docx→HTML
learned tables: fee schedules and signature blocks render as real
bordered tables, in document order, on screen and in print. Verified
against the founder's own uploaded contract (1 table, 24 bold runs,
11 centered lines all present). On the platform question, see the
answer given in-session: the limits are docx-in-browser limits, not
Frappe's — recommendation is to keep this stack to go-live and revisit
a self-hosted ONLYOFFICE only if daily use demands full Word fidelity.

### Round-7 checks

**R7.1** Generate a paper — does its filename in the green note open
the window (not download)?

>

**R7.2** Your uploaded contract's preview — bảng và khối ký tên hiện
đủ chưa, in ra có kẻ khung không?

>

## Round 8 — the founder's answers (in-session, 2026-08-13) and what shipped

The uploaded contract library (docs/samples, kept out of git — real
data) drove the fix: borders now come from the document itself.
docx→HTML reads each table's border settings — your signature blocks
render borderless, your fee schedules keep their grid — and the
HTML→Word translator writes tables too (bordered by default,
borderless when marked), so an edited draft no longer drops or
re-borders a signature block. An editor border-toggle button remains
open — for now a borderless table only enters a web template via an
uploaded original or an edited draft of one.

### Round-8 checks

**R8.1** Preview your real HDDV/BBNT templates — khối ký tên không kẻ
khung, bảng hạng mục có kẻ khung, cả trên màn hình lẫn khi Print?

>

## Verdict

- [x] **GO** — merge it; Phase B/C starts
- [ ] **GO with notes**
- [ ] **NO-GO** — fix the failed steps first

>

> GO given in-session 2026-08-13 ("go") after round 8. Phase A (A1–A5) closes.

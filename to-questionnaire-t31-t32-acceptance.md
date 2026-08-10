# T3.1 + T3.2 acceptance walkthrough — is the deal card done?

**Purpose:** decide whether [#20 (T3.1: card collaboration)](https://github.com/nosuper/10082026-OS/issues/20) and [#21 (T3.2: table view + fields)](https://github.com/nosuper/10082026-OS/issues/21) are complete — merge [PR #23](https://github.com/nosuper/10082026-OS/pull/23) to `main` — or send them back for fixes. Two answers in here are **blocking**: the project-type list and who may create tags.

**From:** Claude (the implementing agent) — **To:** the founder, plus Linh for the producer checks, plus the next Claude session — **How your answers will be used:** the next session reads this file, treats every "yes" as a verified acceptance criterion, applies the vocabulary decisions, and merges (or fixes) accordingly.

## Context

T3.1 adds three things to the deal card dialog: a **comment thread**, **file attachments**, and **labelled links** (Drive folder, reference video). T3.2 adds a **Board ↔ Table toggle** on the deals page and four new fields — **estimated client budget**, **source**, **tags**, **project type**.

Automation is green: 76/76 Frappe site tests (comments/attachments/links created and read as both Founder and Producer, role-less user denied on all three; the four fields persist; unknown source/type/tag values rejected; Linh can see the budget), 108 pure pytest, frontend builds clean, GitHub CI green. What automation cannot see: whether the dialog is still usable now that it carries five sections, whether the table earns its place next to the board, and several vocabulary and scope decisions that are yours.

Two of your answers from the ticket are already built in: **source values are Website / Referral / Zalo / Expo and the list is expandable** (you add more in Desk, no code change), and **Linh can see the budget**. What you did *not* answer — the project-type list and the tag rules — I chose provisionally, and those are the two blocking questions below.

The test site is **http://192.168.1.94:8000/aura/deals** (Desk login at http://192.168.1.94:8000; `Administrator` / `admin`, or your own `anhchung.work@gmail.com` for the Founder seat and Linh's `plinhcontact@gmail.com` for the Producer seat). **Hard-refresh first (Ctrl+Shift+R)** so you're not on a cached bundle.

> **Note on the test site:** it is currently running **PR #23 only**. T5 (breakdown & quote editor, PR #22) is *not* on it right now — the two branches touch the same files and staging them together would produce a tree matching neither. Tell me when you want the box flipped back to T5 for its own walkthrough; it's one command.

## How to answer

15–20 minutes at a browser on your LAN, plus 2 minutes of Linh's time for the producer section. Partial answers and "I don't know" are useful — flag anything unsure rather than skipping it. Answer inline under each `>`.

## Blocking decisions (I need these two before merge)

### Project type: I seeded TVC / Social Video / Event / Documentary. Is that your real list — anything to rename, remove, or add?

_Why this matters: these are the ticket's example values, not your words. Every deal from here on gets tagged with one, so a wrong vocabulary quietly poisons the "what kind of work do we actually do" question you'll ask this data in six months. Like sources, the list stays expandable in Desk — I just want your v1 right._

>

### Tags: right now **both you and Linh** can invent a new tag while editing a deal. Keep it open, or restrict tag creation to you (like sources)?

_Why this matters: open means the vocabulary grows naturally but drifts ("gấp", "urgent", "GAP" as three tags). Restricted means it stays clean but Linh has to ask you every time. Sources are founder-only; tags are the one place I left open, and it's reversible either way._

>

### Sources — Website / Referral / Zalo / Expo. Does that cover where last quarter's deals actually came from, or is something missing?

>

## The card dialog (T3.1)

### Open any deal. Write a comment, save nothing, reload the page. Is the comment there, with the right name and time on it?

_Why this matters: comments post immediately and independently of the Save button — that's deliberate, but it's the opposite of how the rest of the dialog behaves, so I want to know if it confused you._

>

### Attach a real file (a brief PDF, a reference image). Does it upload, appear in the list, and open when you click it?

>

### Add a link — label it "Drive folder" and paste a real Drive URL. Then hit Save and reload. Is it still there and does it open?

_Why this matters: links are the one collaboration feature that only persists when you press Save; comments and files save themselves. If that split feels wrong, say so now._

>

### The dialog now has: fields, brief, details, links, attachments, comments, stage history. Scroll it top to bottom on the deal you use most. Is it still workable, or has it become a wall?

_Why this matters: this is the criterion no test can measure. If it's too long, the fix is to split collaboration into a second tab — cheap now, annoying later._

>

### Anything you'd expect from a comment thread that isn't there — editing your own comment, deleting one, @mentioning Linh, an email when someone comments?

_Why this matters: I built the minimum the ticket asked for. Frappe gives edit/delete/mentions almost free, but each one is a decision about what the thread is for._

>

## The table view (T3.2)

### Toggle Board → Table. Is the same set of deals there, and does clicking a row open the same card dialog?

>

### Click each column header to sort — title, company, stage, owner, budget, source, project type, tags, updated. Does every one sort sensibly, including Vietnamese names?

>

### The table shows nine columns. Too many, too few, or wrong ones — what would you actually want to see at a glance in a list?

_Why this matters: the ticket asked for five (title, company, stage, owner, updated); I added budget, source, project type and tags because they're the new fields and hiding them would make them invisible. Trimming is easy._

>

### Board is the default view every time you land on the page — the toggle doesn't remember your choice. Fine, or should it stick?

>

## The new fields

### Open a deal, fill in budget / source / project type / a couple of tags, save, reload. Do all four stick?

>

### The budget shows as a plain number (e.g. `250.000.000`) with no ₫ and no shorthand. Right for you, or would you rather see `250tr` / `250,000,000 ₫`?

_Why this matters: you'll read this number more than any other on the page._

>

### Add a tag that doesn't exist yet — type it and press Add. Does it appear immediately, and is it offered as a suggestion on the next deal?

>

## Linh's seat (2 minutes of her time)

### Log in as Linh (`plinhcontact@gmail.com`). Can she comment, attach a file, add a link, and see the budget on a deal?

_Why this matters: you confirmed budget is fine for her to see. Everything else in T3.1 was built for both seats — this is the check that no permission rule quietly locked her out._

>

### Try to add a new **source** as Linh. It should refuse (sources are founder-only). Does it?

_Why this matters: this is the guard rail behind your "expandable list" answer — expandable by you, not by everyone._

>

### On her phone browser, does the table view read at all, or is it a horizontal-scroll mess?

_Why this matters: the board already works on her phone. If the table doesn't, I'd rather know than assume she'll only use it on a laptop._

>

## Scope decisions you may veto (I chose, you decide)

### Attachments are uploaded as **private** files — only logged-in AuraOS users can open them, and the link won't work if you paste it to a client. Keep private, or do you need shareable links?

>

### Comments are plain text — no formatting, no images pasted inline. Enough for "khách muốn quay trước Tết", or do you need more?

>

### Source and project type are stored as small editable lists rather than fixed dropdowns baked into the code — so you can add "TikTok" or "Corporate" yourself in Desk under the same menu where you manage Party Roles. Is that discoverable enough, or do you want a settings screen in the SPA?

_Why this matters: it's the mechanism that makes your "should be expandable" answer real, but it only works if you can find it._

>

### A link you type is checked to start with `http://` or `https://` before it's accepted. Any real link you'd want to save that this would reject?

>

## Anything else?

### Anything you saw during the walkthrough — a slow load, odd wording, a worry about the next tickets — that we didn't ask about?

>

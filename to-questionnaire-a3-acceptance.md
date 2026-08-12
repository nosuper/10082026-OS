# A3 acceptance walkthrough — does the quote speak at your client's level?

**Purpose:** decide whether ticket [#57 (A3: Quote detail levels)](https://github.com/nosuper/10082026-OS/issues/57) is complete, or send it back for fixes.

**From:** Claude (the implementing agent) — **To:** the founder — **How your answers will be used:** the next Claude session reads this file top to bottom, treats every passed step as a verified acceptance criterion, turns each design answer into either code or a follow-up ticket, and acts on the verdict at the bottom.

## Context

Your A2 question — *"báo giá chia theo các loại, gom package hoặc tiêu chuẩn breakdown AICP, cái này đã đáp ứng chưa?"* — the answer was no. Now it is: the breakdown page carries a **Quote detail level** choice, frozen into each published version:

- **Package totals** — what every quote has been until today (unchanged default)
- **Line by line** — AICP-style: each package with its price, member lines beneath as `2 người × 3 ngày` with their sell amounts. If you override a package's price (round-up or FOC), an **Adjustment** line closes the arithmetic so the client's own sum always matches.
- **Lump sum** — one figure for the whole job; the scope still reads in its description.

What never appears at any level: unit cost, markup, vendor MF, tax routing — those aren't even frozen into a version, so they can't leak.

Automation: 277 pure tests, 45 quote site tests (publish at each level, page rendering, frozen-line immutability, cost-side leak checks), e2e suite — CI green.

## How to answer

**Rough effort:** ~8 minutes. Answer in the `>` blocks.

## 0. Before you start

**http://192.168.1.94:8000/aura** — `Administrator / admin`, **Ctrl+Shift+R**. Open **Social series — 6 tập → Breakdown**. The deal is already set to **Line by line** with v2 published from my verification — you'll publish v3+ as you go.

## 1. Line by line

**Do this:** the level select (above the CLIENT-FACING QUOTE box) already says Line by line. Open the published v2 client link.
**Expect:** an Item / Quantity / Amount table — packages bold with their price, lines beneath (`1 người × 3 ngày · 20.000.000`), Flycam once as its own row. Try the PDF too.

_This is the triple-bid format an agency compares line-by-line (playbook §3.3)._

Pass / fail:

>

## 2. The Adjustment line

**Do this:** set an Override on a package (e.g. Equipment → `30000000`), publish a new version, open its link.
**Expect:** the package shows 30.000.000; beneath its lines an **Adjustment** row carries the negative difference, so the lines still add to the package price.

Pass / fail — and does "Adjustment" read right to your clients, or should it say something else (e.g. "Ưu đãi")?

>

## 3. Lump sum

**Do this:** switch the level to **Lump sum**, publish, open the link.
**Expect:** a single row — deal title, package names in the description, one price — then MF/VAT/Total as usual.

Pass / fail:

>

## 4. Package totals unchanged

**Do this:** switch back to **Package totals**, publish, open.
**Expect:** exactly the quote you've been sending all along.

Pass / fail:

>

## 5. Design questions

### 5.1 Where quantities came from

Line-by-line shows the **sell** amount per line (giá đã markup). A real AICP bid also shows a per-line *rate* column (đơn giá bán = amount ÷ quantity). I left rate out — amount is authoritative and a divided-back rate can look "lẻ" (e.g. 6.416.667/ngày). Want a Rate column anyway?

>

### 5.2 The storefront itself

This page is the one thing outsiders see. Typography, spacing, the letterhead, the totals block — anything that still doesn't look like a document you'd proudly send?

>

## Verdict

- [ ] **GO** — merge it; A4 (job page + phone expense screen) starts
- [ ] **GO with notes**
- [ ] **NO-GO** — fix the failed steps first

>

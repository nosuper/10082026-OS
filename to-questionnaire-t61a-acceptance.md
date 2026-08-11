# T6.1a acceptance walkthrough — does the quote look like a document you'd attach to a contract?

**Purpose:** decide whether ticket [#42 (T6.1a: Company identity & formal document layout on the quote)](https://github.com/nosuper/10082026-OS/issues/42) is complete, or send it back for fixes.

**From:** Claude (the implementing agent) — **To:** the founder — **How your answers will be used:** the next Claude session reads this file top to bottom, treats every passed step as a verified acceptance criterion, turns each design answer into either code or a follow-up ticket, and acts on the verdict at the bottom.

## Context

T6.1a puts the company on its own quote. The page and the PDF carry a **letterhead** — logo, name, tax code, contact block — read live from AuraOS Settings, and the PDF now reads as a formal document rather than a screenshot of a web page: a slim continuation header on pages 2+, "Page X of Y" and the tax code in the footer of every page, and a two-column **signature block** with space for a wet signature and the seal.

Automation is green: 218 pure pytest, the full Frappe site suite, the Playwright browser suite (6/6), frontend build clean. Main is merged in, so this branch has T8, T10, T11 and T5.1 alongside it.

The mechanical half is already pinned by tests and does **not** need your clicks: the client-facing whitelist (a new settings field cannot leak onto a client's page), the guest boundary, live branding not freezing a version, "Page X of Y" against a real five-page render, the logo surviving the PDF pipeline, and a producer being unable to read or write the company block.

What automation cannot judge is the thing this ticket is actually about: **whether it looks right on paper.** That's what this walkthrough is for — and one of the questions below is big enough that I'd rather you saw it before deciding.

## How to answer

**Rough effort:** about 15 minutes of clicking, plus a printer for one step, plus however long the design questions take you.

**No deadline from my side** — but T6.1's two siblings (phases, package detail) edit this same template and are queued behind it.

Answer in the `>` blocks. Partial answers and "I don't know" are useful — flag anything you're unsure of rather than skipping it. If a step fails, say what you saw rather than only "no"; that's usually enough for me to fix it without a second round.

## 0. Before you start

The **preview stack** for this ticket is at **http://192.168.1.94:8061/aura** — login `Administrator` / `admin`.

**Hard-refresh first (Ctrl+Shift+R)** — the browser caches the old app otherwise, and every "it didn't change" report so far has been that.

Settings is seeded with a full company block — Aura Productions, tax code, an address in Quận 1, phone, email, website, Vietcombank details, and you as signatory. **Deliberately no logo**: a seeded image would be a binary blob in the repo, and uploading the real one is the direction that actually needs seeing.

Use **Social series — 6 tập** for the quote steps — it's the deal with a real breakdown, packages and a published version already sent.

## 1. The letterhead

### 1.1 Look at the quote page

**Do this:** open the deal, then its published quote's client link (the tokenised URL).
**Expect:** a letterhead across the top — company name, tax code, and the contact block — above the offer.

Pass / fail, and what you saw:

>

### 1.2 Upload the real logo

**Do this:** Settings → Company Identity → upload the company logo → Save. Reload the quote page.
**Expect:** the logo at the top left of the letterhead, at a sensible size (it's capped at about 4rem tall, 14rem wide).

_Why this matters: this is the one field nobody has ever seen filled, and logo files are the usual source of "it's enormous" or "it's a smear"._

Pass / fail, and how it looked:

>

### 1.3 Clear a field and watch its line disappear

**Do this:** clear the website (or the phone) in Settings, Save, reload the quote page.
**Expect:** that line simply isn't there — no label with a blank beside it, no gap where it used to be. Put it back afterwards.

Pass / fail:

>

## 2. The PDF as a printed document

### 2.1 Download the PDF

**Do this:** from the quote page, take the PDF export.
**Expect:** the letterhead on page 1; on page 2 onwards a slim line at the top with the company name and the quote number; on every page a footer with the tax code and "Page X of Y".

Pass / fail, and what the pages looked like:

>

### 2.2 The signature block

**Do this:** go to the end of the PDF.
**Expect:** two columns — **For the client** (name blank, for them to fill in) and **For Aura Productions** with your name and title — each over a space and a rule reading "Name, title, date and seal" / "Signature, date and seal".

Pass / fail:

>

### 2.3 Print it on A4 and sign it

**Do this:** actually print the PDF and put a signature and the company seal in your column.

**Expect:** enough room. The gap is about 1.9 cm today.

_Why this matters: this is the whole point of the ticket and the one thing no test can answer. A company seal is around 3.5–4 cm across; if 1.9 cm of white space isn't enough to sign into and stamp over, the number needs to change and I'd rather change it now than after you've sent one to a client._

Pass / fail, and how much space it actually wants:

>

### 2.4 Does it read as a document you'd attach to a contract as an appendix?

**Do this:** look at the printed page as a whole — margins, weight of the letterhead, where the eye lands.

Pass / fail, and what's off:

>

## 3. The design question I'd like settled

### 3.1 The document is entirely in English. Should it be Vietnamese?

Right now a client reads: **Payment** over the bank block, **For the client** / **For Aura Productions** over the signature columns, **Name, title, date and seal**, **Tax code**, and **Page 1 of 3** in the footer. Meanwhile the seeded milestones next door are *Đặt cọc*, *Sau quay*, *Nghiệm thu*, and the quote goes to a Vietnamese client to be attached to a Vietnamese contract.

_Why this matters: the internal app being in English is a settled thing — this is the one surface a client reads, and it's the surface that gets stapled to a legal document. Changing it later means changing it after quotes are already out. It's also not a five-minute job if it has to be bilingual or switchable per client, so I'd rather know the shape now._

Which do you want:

- **English as it is** — leave it.
- **Vietnamese throughout** — one language, the client's.
- **Bilingual** — both on the page, the way many VN contracts run.
- **Switchable** — a setting, or per client.

>

## 4. Scope calls I made that you may veto

### 4.1 The company lives on **AuraOS Settings**, not on a Party Company row — so there is one company, not a record you could accidentally have two of. Settled in the grilling; still the right call now you've seen it?

>

### 4.2 **Bank name is free text** here, rather than the 36-option bank list used on Party Company and Party Contact. My reasoning: one vocabulary copied a third time is worse than typing the bank once. Agree, or should it be the same dropdown?

>

### 4.3 The signature block is **PDF only** — the web page never shows it, because nothing is signed on a screen. Keep it that way?

>

### 4.4 The bank block prints if **any** of its three fields is filled, on the theory that half a bank block still tells a client where to pay. Or should a partial block be suppressed entirely?

>

## 5. Anything else

### Anything you saw — wording, layout, something a client would ask about, something missing before this goes out for real — that we didn't ask about?

>

## Verdict

### Is T6.1a complete?

**Accept** (close #42 and merge PR [#52](https://github.com/nosuper/10082026-OS/pull/52)) — or **send back**, listing what has to change first:

>

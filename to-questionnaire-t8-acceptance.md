# T8 acceptance walkthrough — does the money on a job add up?

**Purpose:** decide whether ticket [#10 (T8: Advances, expenses & one-click settlement)](https://github.com/nosuper/10082026-OS/issues/10) is complete, or send it back for fixes.

**From:** Claude (the implementing agent) — **To:** the founder — **How your answers will be used:** the next Claude session reads this file top to bottom, treats every passed step as a verified acceptance criterion, turns each design answer into either code or a follow-up ticket, and acts on the verdict at the bottom.

## Context

T8 is the money-out half of a job. You hand Linh cash for a shoot (an **advance**); she logs what she spends on her phone as it happens; you log the big items you pay vendors directly. The job then answers two questions on its own: **who owes whom** (one click to settle), and **where the money went** against what the deal was quoted at.

The second one is free because an expense's **category** is one of the entries the client was quoted — a package, or a line quoted on its own. Nobody maintains a second list.

Automation is green: 226/226 Frappe site tests on a fresh site (41 of them new for T8), 128 pure pytest (25 new), frontend build clean.

What automation cannot judge: whether logging an expense on a phone is actually fast enough to happen during a shoot, whether "quoted cost" is the number you want spend compared against, and half a dozen permission calls I made that you may veto.

## How to answer

**Rough effort:** about 20 minutes of clicking — **some of it on your phone**, which is the point of section 2 — plus however long the design questions take you.

**No deadline from my side.** T9 (no-invoice replacement tracking) and T10 (payment milestones) both attach to these records, so this is what they are waiting on.

Answer in the `>` blocks. Partial answers and "I don't know" are useful — flag anything you're unsure of rather than skipping it. If a step fails, say what you saw rather than only "no"; that's usually enough for me to fix it without a second round.

## 0. Before you start

The **preview stack** for this ticket is up at **http://192.168.1.94:8008/aura** — login `Administrator` / `admin`.

**Hard-refresh first (Ctrl+Shift+R)** — the browser caches the old app otherwise, and every "it didn't change" report so far has been that.

It carries T7's seeded job forward, now mid-shoot. Open **Jobs → MV — Hà Anh Tuấn** and you'll find, under the revisions panel:

- **20.000.000 ₫ advanced** to you, six days ago.
- **Three expenses out of that float** — 6.000.000 (Human resources), 4.500.000 (Equipment), 850.000 with no category at all.
- **One direct payment** of 24.000.000 to an equipment vendor, marked **company** — money out on the job that is nobody's float.

So the float standing open is **20.000.000 − 11.350.000 = 8.650.000 ₫**, and that is the number the Settle button should offer to close.

## 1. The float — advance, spend, settle

### 1.1 Read the money panel

**Do this:** open the job and scroll to **Money out**.
**Expect:** one row saying you were advanced 20.000.000, have spent 11.350.000 out of it, float 8.650.000, with the wording **"Administrator returns 8.650.000"** and a **Settle** button.

Pass / fail, and whether the wording tells you who pays whom:

>

### 1.2 Record another advance

**Do this:** in the **Advance** row at the bottom of that panel, pick a recipient, type `5000000`, click **Record**.
**Expect:** advanced goes to 25.000.000 and the float to 13.650.000.

Pass / fail:

>

### 1.3 Log an expense from the job page

**Do this:** in the **Expenses** panel, type an amount, pick a category, say what it was for, click **Log**.
**Expect:** it appears in the ledger dated today, and the float drops by exactly that amount.

Pass / fail:

>

### 1.4 Settle

**Do this:** click **Settle**, then **Confirm**.
**Expect:** a line telling you what was handed back, the float now **0** and marked **Settled** — and the ledger above unchanged, because settling closes a float, it doesn't erase what it closed.

Pass / fail:

>

### 1.5 Carry on spending after settling

**Do this:** log one more expense.
**Expect:** the float starts again from that expense — the job is not "closed" by a settlement, and the next advance opens a fresh one.

_Why this matters: a shoot that settles at the halfway point and carries on is normal; the alternative design would have made settlement final._

Pass / fail:

>

### 1.6 A settled amount can never be edited afterwards — it records a transfer that already happened. To correct a mistake you advance, spend or settle again. Is that the right stance, or do you need to fix a wrong settlement in place?

>

## 2. The phone test (this is the one that matters)

### 2.1 Open the quick-entry screen on your phone

**Do this:** on your phone, go to **http://192.168.1.94:8008/aura/jobs/**`<job code>`**/expense** — or tap **Log expense on phone →** at the top of the money panel and send yourself the link.
**Expect:** one screen — how much of your advance is left, a big amount box with the number keypad already up, the job's categories as tappable chips, an optional note, a receipt button and one big Log button.

Pass / fail, and what it looks like on your actual phone:

>

### 2.2 Time yourself

**Do this:** pretend you have just paid for something. Type the amount, tap a category, tap **Log**. Count the seconds.
**Expect:** under 15 seconds, and the screen resets ready for the next one with the amount box already focused and the float updated.

_Why this matters: the ticket's acceptance criterion is literally "usable in under 15 seconds". If it isn't, the logging doesn't happen and none of the rest of this is worth anything._

How many seconds, and what slowed you down:

>

### 2.3 Photograph a receipt

**Do this:** tap **📷 Receipt**, take a photo of anything, then log the expense.
**Expect:** a thumbnail appears before you save, and afterwards the ledger row on the job page carries a **📷 receipt** link that opens it.

Pass / fail:

>

### 2.4 The screen shows **your** float only. Should it also show what Linh is holding on the same job?

_Why this matters: it's her screen most of the time — but a founder standing on set may want the whole picture._

>

### 2.5 Anything missing from that screen you'd reach for on a shoot?

>

## 3. Where the money went

### 3.1 Read the actual-vs-quoted table

**Do this:** on the job page, find **Where the money went**.
**Expect:** a row per quoted entry — Human resources, Equipment, Flycam — plus **Uncategorised** for the 850.000 nobody assigned. Every category shows up whether or not anything has been spent on it.

Pass / fail:

>

### 3.2 The comparison is against **quoted cost** — what that category was expected to *pay out*, which for Equipment is 31.716.000: the vendor cost, the vendor management fee and the VAT on their invoice. It is **not** the price the client is charged for that package. Is that the comparison you want?

_Why this matters: comparing cash out to a client price mixes two different kinds of money and makes every package look wildly profitable mid-shoot. The client-facing prices are still in the Packages panel above._

>

### 3.2a Human resources reads **36.000.000**, not the 40.000.000 the profit chain uses for the same lines. The difference is the **PIT on the freelancers** — the company remits it later through the accountant, and nobody hands it over on a shoot, so counting it would leave every crew-heavy package permanently reading "under budget". Right call, or do you want the freelancer PIT in this column?

>

### 3.3 An expense's category can only be one of the entries the deal quoted; anything else has to be left blank, and lands in **Uncategorised**. Should free-typed categories be allowed?

_Why this matters: locking the list is what makes actual-vs-quoted complete by construction. Free text would let the table quietly develop holes._

>

### 3.4 Would you want this table at the **top** of the job page during a shoot, above the revisions panel?

>

## 4. Direct payments

### 4.1 Log one

**Do this:** in the Expenses panel, log an amount with **company paid** selected.
**Expect:** it joins the ledger with a **company** tag, counts in the money-out totals and in its category — and changes nobody's float.

Pass / fail:

>

### 4.2 The job page's form makes you **pick** whose money it was — there is no default, and Log stays disabled until you choose. (The phone screen still assumes "from advance", because that is what somebody holding a float is doing.) Is being asked every time on this form right, or would you rather it defaulted and you corrected it?

_Why this matters: it's the one field that changes who owes whom. Defaulting it to "from advance" meant a founder logging a bank transfer to a vendor quietly opened a float in his own name, and the screen then offered to pay him back 24 million he had never lent._

>

### 4.3 You can also log what **someone else** paid (the Paid by dropdown) — for a receipt Linh sends you on Zalo. It lands on her float, not yours. Right call?

>

## 5. Permission calls you may veto

### 5.1 **Only you can record an advance.** Linh sees the float she is holding but cannot add one — the ticket's story 30 is yours ("advances I transfer to Linh"). Should she be able to record cash she received?

>

### 5.2 **Only you can settle.** Linh sees the float and the wording but has no Settle button. Right?

>

### 5.3 **Either of you can log an expense, and either of you can delete one.** There is no approval step: what Linh logs is final the moment she saves it. Do you want expenses she logs to need your approval, or to be uneditable once saved?

_Why this matters: an approval queue is real work and real friction on a shoot; deletion is the current escape hatch for a mistyped amount._

>

### 5.4 A receipt photo is **private** and readable by whoever can read its expense — so you can see Linh's, and nobody outside the two roles can see any of them. Confirm that's the boundary you want?

>

## 6. Scope calls I made that you may veto

### 6.1 An advance is **per job**. There is no company-wide float that gets drawn down across several shoots. Is per-job right, or does Linh really hold one running float?

>

### 6.2 An expense carries **no tax type** — no Công ty / Cá nhân / Không hoá đơn like a cost line does. That's deliberate: T9 (#11) is the no-invoice replacement tracking ticket, and it will attach to these expense records. Agree it waits for T9?

>

### 6.3 There is **no OCR and no parsing** of the receipt photo — you type the amount. (The spec puts AI expense parsing in v1.5.) Still agreed?

>

### 6.4 Settlement records the amount and the direction, but not **how** the money moved — cash, bank transfer, or offset against her next advance. Do you want that recorded?

>

### 6.5 Nothing here appears on the **jobs board** yet — no "float open" or "over budget" badge on the card. Worth adding, and which one?

>

## 7. Anything else

### Anything you saw during the walkthrough — wording, layout, a number that looks wrong, something you'd reach for during a settlement — that we didn't ask about?

>

## Verdict

### Is T8 complete?

**Accept** (close #10 and merge) — or **send back**, listing what has to change first:

>

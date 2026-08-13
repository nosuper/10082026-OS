# AuraOS

One shared system for a small video production house: deal pipeline, cost
breakdowns and quotes, jobs, money tracking, paperwork and a founder-only
overhead view. This file is the project's glossary - the words we use, and
the ones we deliberately don't.

## Pricing

**Profit cost basis**:
The complete direct cost of a job used to calculate margin, including the effect of each cost line's tax type. Distinct from partial cash-spend notes or an incomplete COGS estimate.
_Avoid_: COGS, cash paid, recorded expenses

## Quote delivery

**Package**:
A client-facing group of cost lines carrying its own description and price - what a client reads instead of our line-level costs. A cost line belonging to no package is quoted as a package of its own.
_Avoid_: bundle, group, section, item

**Phase**:
An ordered, named group of packages on a quote, carrying its own blurb and its own subtotal - how a client reads a job split into pre-production, production and post. A package belonging to no phase is quoted on its own, ahead of the first phase. Distinct from a production stage: a phase is what the client is offered, a production stage is where a job sits once we are making it.
_Avoid_: section, group, block, stage

**Quote preview**:
A mutable client-facing view of a deal at its tokenised URL, refreshed from the breakdown while only authenticated internal users have seen it. It becomes a quote version when marked Sent or first opened by a guest.
_Avoid_: draft version, editable version, live quote

**Quote version**:
A quote preview frozen into an immutable snapshot of the deal's packages and totals when handed to a client or first opened by a guest. Re-pricing after that produces a new preview at a new tokenised URL.
_Avoid_: quote (unqualified), proposal, estimate

**Publish**:
To create a quote preview at a tokenised URL. Distinct from sending it - publishing only makes the mutable preview link exist.
_Avoid_: generate, issue, release

**Sent**:
A quote version the producer has handed to the client. Marking a preview Sent freezes it and starts the silence clock.
_Avoid_: delivered, shared, out

**Confirmed**:
A sent version the client has agreed to. Does not by itself win the deal.
_Avoid_: accepted, approved, signed

**Silence nudge**:
The flag raised on a deal whose sent version has gone unanswered past the configured window.
_Avoid_: reminder, follow-up, alert

**Quote number**:
What a printed quote calls itself - the version's record identifier with its version appended, `DQ-0007-v2`. The identifier alone stops being an answer the moment a second version exists, so a page detached from its PDF is matched back by this.
_Avoid_: reference, quote ID, document number

**Letterhead**:
The company's own identity at the top of a quote - logo, name, tax code and contact block, read live from settings rather than frozen into the version. Distinct from the offer below it: changing the letterhead never re-issues a quote.
_Avoid_: header, branding, masthead, company block

**Signature block**:
The two columns at the end of a quote PDF, ours filled from settings and the client's left blank, with room for a wet signature and the seal. On the PDF only - the web page never shows it, because nothing is signed on a screen.
_Avoid_: sign-off, signing area, e-signature

**Margin floor**:
The single global margin percentage below which any quote warns, without revealing where the number comes from.
_Avoid_: minimum margin, threshold, floor price

## Production

**Job**:
A won deal in production, carrying that deal's breakdown, packages and client unchanged. One deal becomes at most one job, and the numbers it carries are a snapshot - pricing is still edited on the deal.
_Avoid_: project, production, gig, booking

**Production stage**:
Where a job sits in the fixed flow from Pre-production to Complete. Both operating roles may move a job to any stage, forwards or back, and every move is logged.
_Avoid_: status, phase, step

**Revision round**:
One request for changes from the client, logged against a job with its note, author and time. Rounds are numbered from their order, never typed in.
_Avoid_: revision (unqualified), amend, edit, feedback round

**Redo**:
The round-trip a revision round sets off: a job the client has already been shown goes back to the stage where the work is redone, without anyone dragging the card.
_Avoid_: rework, reopen, bounce back

**Change order**:
A revision round past the included ones - chargeable, and flagged as such wherever the job appears.
_Avoid_: extra, overage, out of scope

**Files location**:
The shared folder a job's material lives in, named after the job code.
_Avoid_: path, directory, drive, storage

## Money out

**Advance**:
Company cash handed to one person for one job, to spend on it and account for. Recorded with its recipient, because it is money the company is still owed until the receipts come back.
_Avoid_: float (that's what it leaves behind), petty cash, loan, top-up

**Float**:
What an advance leaves in someone's hands: what they were advanced, less what they have spent out of it. Negative when they have covered a shortfall from their own pocket.
_Avoid_: balance, outstanding, petty cash, running total

**Expense**:
One payment out on a job - amount, category, optionally a photo of the receipt. Actual money that left, as distinct from a cost line, which is what a deal was priced at.
_Avoid_: cost, spend, purchase, receipt

**Category**:
The quote entry an expense belongs to: a package, or a cost line the deal quoted on its own. The categories a job offers are exactly what its client was quoted, which is what makes actual-vs-quoted free.
_Avoid_: type, bucket, tag, cost centre

**Direct payment**:
An expense the company paid the vendor itself rather than out of anyone's float. It counts against the job's money out and settles nobody's float.
_Avoid_: company expense, big item, direct cost

**Settlement**:
The transfer that closes a float, recorded with the direction it moved: the holder returns what is left, or the company tops them up. A job carries on paying for things afterwards, on a fresh float.
_Avoid_: reconciliation, payout, clearing, closing

**Quoted cost**:
What a category was expected to pay out in cash - each line's cost after the vendor management fee, plus the VAT on an invoice-bearing one. What an expense is compared against, never the price the client is charged for it, and never the profit cost basis, which is grossed up by a freelancer's PIT that no shoot ever hands over.
_Avoid_: budget, estimate, quoted price, allocation
## Money in

**Payment milestone**:
A named share of a job's quoted total the client owes, carrying its own percentage and the production stage that makes it due. Amounts are always derived from the quote, never typed in.
_Avoid_: instalment, payment term, tranche, invoice

**Trigger stage**:
The production stage that makes a payment milestone due. Reaching it, or passing it, starts the payment clock.
_Avoid_: due stage, milestone stage, deadline

**Collection status**:
Where a milestone stands with the client's money: Not requested (chưa yêu cầu) → Requested (đã yêu cầu KT) → Invoiced (đã xuất HĐ) → Paid (đã thanh toán). Movable in both directions, like every status in this app.
_Avoid_: payment status, invoice state, dunning stage

**Payment terms**:
The single global number of days a due milestone may stay uncollected before it nudges. 0 disables the nudge, as with the margin floor.
_Avoid_: grace period, credit terms, net days

**Invoice request**:
The Vietnamese text handed to the external accountant on Zalo asking them to issue an invoice - client tax details and the amount split out of its VAT. Generating it changes nothing; marking the milestone Requested is a separate act.
_Avoid_: invoice, billing request, hoá đơn (unqualified)

## Paperwork

**Paperwork template**:
A .docx the founder designed in Word - letterhead, clauses, signature block, seal space - with placeholders typed where values belong. Generating from one never changes it; the company signs on paper, so the file is the design and the system only does the typing.
_Avoid_: form, mail merge, boilerplate, document type

**Placeholder**:
`{{client.tax_code}}` typed into a template: a namespaced field the system fills from the job and the parties a paper names. A name outside the vocabulary is not a placeholder anything can fill, and says so on the page.
_Avoid_: variable, merge field, token, tag

**Gap marker**:
What a placeholder becomes when it cannot be filled - «thiếu: client.tax_code» where the record holds nothing, «không có trường: …» where no such placeholder exists - printed where the value belongs and reported by name to whoever generated it. Distinct from a blank, which is invisible exactly where it costs most.
_Avoid_: default, fallback, empty value, placeholder (unqualified)

**Paper**:
A paperwork template filled for one job and attached to it - printed, signed by hand and sealed. Generating one never changes the template it came from.
_Avoid_: output, export, contract (unqualified), attachment

## Environments

**Preview stack**:
A throwaway environment serving one ticket's branch, for a human to click through. Disposable by definition: nothing on it is backed up and any of it can be rebuilt from the branch.
_Avoid_: preview environment, dev site, staging, the box

**Walkthrough**:
The founder clicking through a preview stack to accept or reject a ticket. The judgement automated tests cannot make.
_Avoid_: UAT, QA, demo, acceptance testing

**Seed data**:
Data a branch creates at stack boot so its own feature is visible. Never real, never preserved.
_Avoid_: smoke data, fixtures, demo data, test data

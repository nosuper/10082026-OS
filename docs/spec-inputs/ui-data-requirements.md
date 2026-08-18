# AuraOS UI - backend data requirements

Derived by reading every file under `/opt/auraos-design-ref/frontend/src/routes/`,
`/opt/auraos-design-ref/frontend/src/data/` and `/opt/auraos-design-ref/frontend/src/components/aura/`.

The prototype has **zero** network calls. Every number is a literal in
`data/fixture.ts`, `data/finance.ts`, `data/quotations.ts` or inlined in the route file
itself. Mutations are `useState` array pushes that vanish on reload. This document
inventories what each screen would need if it were real.

Where a value in the fixture is *pre-computed but obviously derivable*, it is marked
**[derived]**. Where a value is pre-computed and **not** derivable from anything the
prototype models, it is marked **[NO SOURCE]** and repeated in the "New domain concepts"
section at the end.

Existing backend model referenced throughout (Frappe doctypes under
`/opt/auraos/auraos/auraos/doctype/`): Deal, Deal Cost Line, Deal Package, Deal Quote,
Deal Quote Line, Deal Quote Package, Deal Quote Open, Deal Stage Log, Deal Link, Deal Tag,
Deal Source, Job, Job Expense, Job Advance, Job Settlement, Job Payment Milestone,
Job Revision, Party Company, Party Contact, Party Role, Paperwork Template,
Generated Paper, Cost Item Category, Project Type, AuraOS Settings.

---

## Global shell

**File**: `components/aura/AppShell.tsx`

### Reads
- Current user: display name (`Trần Quốc Bảo`), initials (`TB`), role label (`Founder`).
  Role drives founder-only gating everywhere - see Settings screen. Not currently fetched.
- Nav is a static array. No badge counts, no unread markers.

### Writes
None.

### Notes
- The "Quick actions ⌘K" chip is **presentational only** - it has no handler, no palette,
  no search endpoint.
- Every page title/meta string in the header is passed in as a prop by the route.

---

## 1. Home (`routes/index.tsx`, path `/`)

### Reads

**Header meta** - hardcoded string `"Tuesday 18 August 2026 · 6 open deals · 4 jobs in production"`.
Real version needs: today's date, `count(deals where stage is open)`, `count(jobs where stage is open)`. **[derived]**

**Four stat tiles** (`dashboardTiles`), each `{label, value: currency, sub: string, alert?: bool}`:

| Tile | Value | Sub | Grain / rule |
| --- | --- | --- | --- |
| Pipeline (open deals) | 1,925,000,000 | "6 open deals" | sum of open-deal value + count **[derived]** but see weighting note below |
| In production | 815,000,000 | "4 open jobs" | sum of `quote_total` for jobs in open stages **[derived]** |
| Overdue payments | 86,500,000 | "2 milestones past terms" | sum + count of `Job Payment Milestone` where `due_on < today` and `paid_on is null` **[derived]** |
| Quotes gone quiet | 95,000,000 | "past 7 days" | sum of `deal.quote_total` where latest sent version has no open in > `quote_silence_days`. The literal "past 7 days" must come from `AuraOS Settings.quote_silence_days` **[derived]** |

Note: the Pipeline tile value (1,925,000,000) equals the "Weighted pipeline" figure on the
Deals screen, but the stage tiles on that screen sum to 2,630,000,000. So "Pipeline" here is a
**weighted** number and the weighting rule is **[NO SOURCE]**.

**"Needs attention" list** (`needsAttention`), 3 rows of `{kind, what, amount, age}`:
- `kind` is one of `"Overdue milestone"` | `"Silent quote"` - a union feed over two different
  entities, not one table.
- `what` for a milestone = `"<job title> - <milestone title>"` (e.g. `"Tết campaign cutdowns - 50% on delivery"`).
- `what` for a silent quote = `"<deal title> - <client company>"`.
- `amount` = milestone amount, or quote total.
- `age` = human string `"12 days overdue"` / `"9 days no reply"` **[derived]** from
  `today - due_on` and `today - quote_sent_on`.
- Sort order is not stated; presumably most-overdue first.

**"Margin - TVC Tết 2027" card (founder only)**. Reads from `totals` + `founderBlock` for a
single named deal - the UI hardcodes DEAL-0182. A real version needs a rule for *which* deal
this card shows (largest open? most recently touched?) - **[NO SOURCE]**.
Fields: `quote_total`, `cost` (profit cost basis), `margin`, `commission_pct` + `commission`,
`tndn_rate` + `tndn`, `net_profit`, `margin_pct`, `margin_floor_pct`.
All of these exist on `Deal` today.
Badge text "Above floor" = `margin_pct >= margin_floor_pct` **[derived]**.

**"Jobs in production" table** (`jobsInProduction`), 4 rows of `{job, client, quoted, stage}`.
`stage` values seen: `Production`, `Post-production`, `Delivery`, `Awaiting payment`.
Note these are **English** and differ from the Vietnamese stage names used on the Job detail
screen (`Chuẩn bị, Ghi hình, Hậu kỳ, Bàn giao, Thu tiền`) and from the Jobs index stage list
(`Pre-production, Production, Post-production, Delivery, Awaiting payment`). The stage
vocabulary needs reconciling before the endpoint can be typed.
Bug in the prototype: every row links to `jobId: "JOB-0114"` regardless of row.

**"Quick expense" form** - reads `jobsInProduction` (job picker options) and
`expenseCategories` (`Crew, Equipment, Art, Catering, Transport, Uncategorised`).

### Writes
- **Log expense**: `{job, amount (VND int), category, note}` → create expense.
  Form has `onSubmit={e => e.preventDefault()}` - it does nothing today.
  Note the category list here differs from the one on `/finance/expenses`
  (which adds `Production`, `Post-production`, `Overhead` and drops `Uncategorised`)
  and from `expenseByCategory` in reports (which has `Catering & transport` as one bucket).
  Category taxonomy must be unified; `Cost Item Category` doctype is the obvious home.
- **New deal** button in the header - no handler on this screen.

### Filters / sorts / ranges
None. Everything is a fixed top-N.

### Presentational only
Greeting text "Good morning, Bảo"; the `stageTone` colour map; alert-red styling.

---

## 2. Deals index (`routes/deals.index.tsx`, path `/deals`)

### Reads

**Five stage tiles** (`stageTiles`): `{stage, count, value, focus?}` for
`Lead, Briefed, Breakdown, Negotiating, Won MTD`.
- Grain: **per stage**, count of deals + sum of deal value. **[derived]**
- `Won MTD` is a different grain from the rest - it is *month-to-date closed-won*,
  not a live stage bucket. That mixed grain needs a decision.
- `focus: true` on Breakdown is hardcoded cosmetic emphasis.

**Deal rows** (`seedRows`), fields per row:
- `code` (`DEAL-0182`) - record name
- `name` - `deal.title`
- `client` - rendered as `"<company> · <contact short name>"`, a joined string
- `stage` - one of `Lead, Briefed, Breakdown, Negotiating, Won`
- `quote` - a **prose summary string**: `"v2 published · not opened"`, `"v1 sent · 2 opens"`,
  `"v3 sent · 6 opens"`, `"no quote yet"`. **[derived]** from latest `Deal Quote`
  (version, status) plus `count(Deal Quote Open)`.
- `quoteQuiet` - boolean flag driving the red text. **[derived]** from silence window.
- `tags` - string array, mixing `Deal Tag` values (`TVC`, `Tết`, `Social`, `Corporate`,
  `Launch`, `HR`, `Doc`) with the tier (`Tier 3`). Note `createDeal` builds tags from
  `[positioning, tier]`, so the table conflates three different fields into one tag strip.
- `value` - `deal.quote_total`
- `margin` - `deal.quote_margin_pct`, one decimal
- `idle` - integer days. **[NO SOURCE]** - see new concepts. The UI turns it red at `>= 9`,
  which is a threshold with no setting behind it.

**Card view** (`DealCard`) shows the same fields, no extras.

**Header meta**: `"<n> open deals · 2 quotes awaiting signature"`. The second half is a count
of quotes in a signature-pending state; there is no such status in `Deal Quote`
(`status` is Draft/Sent/Published/Accepted-ish) - **[NO SOURCE]**.

**Card subtitle**: `"Weighted pipeline <1,925,000,000>"` - hardcoded constant `weighted`,
never derived from `rows`. **[NO SOURCE]** - needs a stage→probability table.

### Writes
- **Create deal** (`FormDialog`, `dealFields`) sends:
  `name` (required), `client` company name (required), `contact` person name,
  `stage` (select: Lead/Briefed/Breakdown/Negotiating/Won),
  `positioning` (select: Brand/Corporate/Social/Retail),
  `tier` (select: Tier 1..4), `value` (number, client budget, ₫), `owner` (person name).
  Server-assigns the next `DEAL-nnnn` code. Client and contact arrive as **free text**,
  so the endpoint needs find-or-create semantics against Party Company / Party Contact,
  or the dialog needs to become a link field.
  Note `positioning` options here (Brand/Corporate/Social/Retail) may not match the
  `Deal.positioning` select or `Project Type.is_positioning`.
- **View toggle** table ↔ kanban - client-side only, no persistence of the preference.
- Kanban cards are **not** draggable on this screen (no drag handlers) - so no
  stage-change-by-drag mutation here, despite the board.

### Filters / sorts / groupings
- Free-text filter input (`placeholder="Filter deals…"`) - **not wired**, no state.
- A `Stage · Source · Owner` filter button - **not wired**, opens nothing.
  If made real: filter by stage (multi), source (`Deal Source`), owner (User).
- Kanban grouping: by `stage`, over the fixed list `Lead, Briefed, Breakdown, Negotiating, Won`.
- No sort control. Rows render in fixture order (looks like descending deal code).

---

## 3. Deal breakdown (`routes/deals.$dealCode.index.tsx`, path `/deals/:dealCode`)

This is the internal cost breakdown. Maps almost 1:1 onto `Deal` + `Deal Cost Line`.

### Reads

**Header meta**: `dealCode`, `deal.client` (company), `deal.contact` (`"Chị Phạm Thu Hà, Marketing Director"`
- name + role concatenated), `deal.owner`, `deal.tier`, `deal.positioning`.

**Four tiles**:
- Client budget = `deal.clientBudget` (`Deal.estimated_budget`)
- Total cost = `costTotals.totalCost` = sum of line `subtotal` **[derived]**
- Line-level quote price = `costTotals.totalLineQuote` = sum of line `quotePrice` **[derived]**
- Margin % + floor, with "above floor" / "below floor" text **[derived]**

**Cost line table**, grouped by `phase` with a subtotal row per phase. Per line:
`id` (sequence number), `description`, `category`, `phase`
(`Pre-production | Production | Post-production`), `source`
(`Internal | Freelancer | Vendor`), `contact` (free text - a party name or `"Studio"` or
`"Various"`), `pkg` (`P1|P2|P3` - the package code), `qty1` + `unit1`, optional `qty2` + `unit2`,
`unitPrice`, `taxType` (`Công ty | Cá nhân | Không hoá đơn`), `markup` %,
`subtotal`, `quotePrice`.

Phase group rows show `sum(subtotal)` and `sum(quotePrice)` for the phase. **[derived]**
Grain: **per deal, per phase**.

**Founder-only block** (`founderBlock`): `commission_pct` + `commission`,
`cm_after_commission`, `profit_before_tax`, `tndn_pct` + `tndn`, `vat_payable`, `net_profit`.
All present on `Deal` today.

### Writes
Nothing on this screen mutates - **the cost table is read-only in the prototype**. There is
no add-line, edit-cell, delete-line or reorder control, even though the real product
obviously needs them. Only two navigation actions exist:
- "Convert to quotation" → `/quotations/new`
- "Open quotation" → `/quotations/QUO-0182-2`

Implication: create/update/delete of cost lines is **unspecified by the UI** and must be
designed. The quotation builder does let you *pick* cost lines but not edit them.

### Filters / sorts
Fixed grouping by phase, in the order Pre → Production → Post. No filters, no sort, no search.

---

## 4. Legacy quotation builder (`routes/deals.$dealCode.quote.tsx`, path `/deals/:dealCode/quote`)

Superseded by `/quotations/:quoteRef` but still routable. Package-level only.

### Reads
- `packages[]`: `pkg` code, `title`, `description`, `memberSum` (sum of member cost-line
  quote prices **[derived]**), `override`, `price`, `variance` (= price − memberSum **[derived]**).
- `totals`: `managementFeeRate`, `vatRate`, `cost`, `marginFloorPct`.
- `quoteVersions[]`: `version`, `status` (Sent/Published), `total`, `published` (date string),
  `opens` (prose: `"4 opens, last 09 Aug"` / `"not opened yet"`) **[derived]**.

### Live client-side maths (must be reproduced server-side on save)
```
packagesSubtotal = Σ override[pkg]
managementFee    = round(packagesSubtotal * feeRate / 100)
beforeVat        = packagesSubtotal + managementFee
vat              = round(beforeVat * vatRate / 100)
total            = beforeVat + vat
margin           = total - vat - cost          // i.e. beforeVat - cost
marginPct        = round(margin / (total - vat) * 1000) / 10
belowFloor       = marginPct < marginFloorPct
```

### Writes
- Edit per-package quoted price (digits-only masked input) → `price_override` on `Deal Package`.
- Edit management fee % → `Deal.quote_mf_pct`.
- Edit VAT % → `Deal.vat_pct`.
- Choose client detail level, one of
  `"Package totals - one price per package" | "Package + grouped lines" | "Full line detail"`
  → `Deal.quote_detail_level`.
- "Send to client" button - no handler.
- "Versions" button - no handler.

None of these persist. All four inputs are local state.

---

## 5. Quotations index (`routes/quotations.index.tsx`, path `/quotations`)

### Reads
Per row (`QuoteRow`): `ref` (`QUO-0182-2`), `dealCode`, `deal` title, `client` company,
`version` (`v1`,`v2`,`v3`), `status` (`Draft | Sent | Published | Accepted`), `total`,
`detail` (detail level label), `activity` (prose: `"3 opens, last 17 Aug"`,
`"9 days no reply"`, `"signed 02 Aug"`, `"draft — not sent"`) **[derived]**, and the
derivation differs per status - a signed quote shows its signing date, a silent one shows
its silence age. That branching is a display rule the endpoint should probably encode as
structured fields (`opens_count`, `last_open_at`, `days_silent`, `confirmed_on`) and let
the client format.

**Header meta**: `"<n> versions · awaiting client decision <sum>"`, where the sum is over
rows with status `Sent` or `Published`. **[derived]** - grain: all quotes, all deals.

### Writes
- "New quotation" → navigates to `/quotations/new`. No creation payload here.

### Filters / sorts
- Free-text search across `deal`, `client`, `ref` (case-insensitive substring), client-side.
- Status filter chips: `All | Draft | Sent | Published | Accepted`.
- No sort control, no pagination, no date range.

---

## 6. Quotation builder (`routes/quotations.$quoteRef.tsx`, path `/quotations/:quoteRef`)

The largest screen (1251 lines), four tabs. `:quoteRef === "new"` is the create mode.

### Shared state / reads
- `name` - client-facing document title, editable.
- `status` - `Draft | Published`.
- `lines: QuoteLine[]` - the heart of it. Each line:
  - `id`
  - `kind?: "package" | "divider"` - **dividers are free-text section rows with no price
    and no maths**; they participate in ordering and print, and are skipped by every total.
  - `label` (editable), `note` (editable, client-facing)
  - `templatePkg?` - the `P1/P2/P3` code the line was seeded from
  - `lineIds: number[]` - **membership links to Deal Cost Lines**
  - `qty` + `unit`, optional `qty2` + `unit2`
  - `overrideUnitPrice: number | null` - `null` means "use the summed member price"
- `feeRate`, `vatRate`, `validDays` (quote validity in days)
- `contact` - selected client contact (from `clientContacts`: `name`, `role`, `email`)
- `compareTo` - which other version to diff against
- `shareVersion` - which shared link row is selected

### Derived maths (Editor + PDF)
```
lineUnitPrice(l) = l.overrideUnitPrice ?? Σ costLines[l.lineIds].quotePrice
lineAmount(l)    = round(lineUnitPrice * qty * (qty2 > 0 ? qty2 : 1))   // 0 for dividers
subtotal  = Σ lineAmount
fee       = round(subtotal * feeRate / 100)
beforeVat = subtotal + fee
vat       = round(beforeVat * vatRate / 100)
total     = beforeVat + vat
cost      = Σ costLines[l.lineIds].subtotal      // NB: .subtotal (cost), not .quotePrice
margin    = beforeVat - cost
marginPct = round(margin / beforeVat * 1000) / 10
```
Note the margin basis here (`beforeVat - cost`) is the same as screen 4 but expressed
differently, and the cost basis sums cost-line `subtotal` while the *unit price* sums
cost-line `quotePrice`. Both aggregates over the same membership set. Grain: **per quote line**.

### Tab: Editor

Reads: the line table (Package / Qty / Unit / Qty 2 / Unit 2 / Unit price / Amount),
per-line `memberSum` and member count (`"5 breakdown lines · 71,490,000"`),
expandable member list showing each cost line's `description`, `phase`, `category`,
`source`, `contact`, `qty1/unit1`, `qty2/unit2`, `quotePrice`; a dropdown of *available*
cost lines (all cost lines not already in this line) labelled `"<pkg> · <description> — <price> đ"`.
Also: Terms card (valid days, client contact select, contact email, deal `clientBudget`)
and Margin check card (margin %, margin ₫, before-VAT base, floor marker, above/below pill).

Writes:
- **Rename quotation** → `name`
- **Add package from template** - `packageTemplates` derived from `Deal Package`
  (`pkg`, `title`, `description`, `lineIds` = all cost lines with that pkg, `sum`).
  Creates a line with `qty:1, unit:"package", overrideUnitPrice: null`.
- **Create empty package** - name only, `overrideUnitPrice: 0`, no members.
- **Add text divider** - creates a `kind:"divider"` row.
- **Edit line label / note** (inline text inputs, every keystroke).
- **Edit qty / unit / qty2 / unit2** - unit from a fixed vocabulary
  (`package, job, day, days, shoot day, frames, cast, crew, pax, track, item, set`);
  unit2 may be empty.
- **Edit unit price** (digit-masked) → sets `overrideUnitPrice`.
- **Reset override** → sets `overrideUnitPrice: null`, reverting to the member sum.
- **Add a cost line to a quote line** → append to `lineIds`.
- **Remove a cost line from a quote line** → remove from `lineIds`.
- **Delete a quote line / divider**.
- **Drag-to-reorder** quote lines (HTML5 drag, drop-on-row = insert at that index).
  Needs a persisted `idx` on the quote line child table.
- **Edit fee rate / VAT rate / valid days**.
- **Select client contact** (drives the recipient email used on publish).

### Tab: PDF preview

Reads (all in one page render): letterhead - **hardcoded** `"Aura Production House"`,
`"12 Nguyễn Huệ, Quận 1, TP.HCM · MST 0312345678"` (contradicts the Settings screen, which
says the legal entity is `Công ty TNHH Aura Production`, tax code `0316 552 118`,
address `19 Nguyễn Đình Chiểu, Q1, TP.HCM`). Should read from AuraOS Settings.
Also: quote ref, issue date, `valid <n> days`, quotation name, client company + contact label,
the line table (dividers render as full-width section rows), the totals block, and a footer
with **hardcoded payment terms** `"50% on signing, 50% on delivery"` - which contradicts both
Settings (40/30/30) and the Job detail milestones (40/30/30). Terms text must come from
settings or from the quote.

Writes: "Download PDF" calls `window.print()`. A real build needs a server-rendered PDF
(or at least a stable print stylesheet) plus, per the tracking log, an event when the client
downloads it.

### Tab: Share & tracking

Reads - a table of **every shareable version of this quotation**, per row:
`version`, `name`, `status`, `slug` (tokenised, e.g. `quo-0182-2-x7f2`),
`recipient` (an email address), `published` date, `opens` count **[derived]** (counts log
entries whose `detail` starts with `"Opened"` - i.e. event type is encoded in prose today),
`last activity` timestamp.
Detail panel: share URL `https://aura.studio/q/<slug>`, status, sent-to, opens,
**"Link expiry: <validDays> days"** (reuses the quote validity as link TTL - a rule that
should be made explicit).
Tracking log per version, columns When / Who / Where / Device / Event:
- `when` - `"17 Aug 2026 · 09:12"`
- `who` - `"Chị Phạm Thu Hà"`, `"Unknown (forwarded)"`, or an internal user
- `where` - **geo-IP city + country**, `"Ho Chi Minh City, VN"`
- `device` - **parsed user agent**, `"iPhone · Safari"`
- `detail` - event, seen values: `"Opened link · viewed 2m 41s"` (includes **dwell time**),
  `"Downloaded PDF"`, `"Published v2 · link created"`, `"Draft link created · not sent"`

`Deal Quote Open` today stores only `opened_on`, `via`, `ip_address`, `user_agent`.
Geo city, device label, dwell duration, event type, identified visitor and
publish/create events are all **[NO SOURCE]**.

Writes:
- **Publish / Republish** - sets status Published, appends a publish event to the log,
  creates the share link. Payload: quote id, recipient contact, validity days.
- **Copy link** - clipboard only, but it *selects* the version as a side effect.
- Selecting a share row is view state.

### Tab: Compare

Reads `versionSnapshots[]`: `version`, `name`, `status` (`Draft|Sent|Published|Accepted`),
`published`, `subtotal`, `feeRate`, `vatRate`, `total`, `cost`, and
`lines: {label, amount}[]` - a **frozen snapshot of the priced lines**, not a live join.

Comparison table merges the current lines with the other version's by **label string**
(`mergeLines`), showing per label: this amount, other amount, difference; then a
Total (incl. VAT) row and a Margin % row (difference expressed in "pts").
Other-version margin recomputed as `(subtotal + subtotal*feeRate/100 - cost) / beforeVat`.
An "All options for this deal" table lists every snapshot with subtotal, total, margin %.

Writes: none, only `compareTo` selection.

Note: merging by label is fragile - two lines with the same label collapse. A real diff
should carry stable line ids across versions, or accept label-matching as the spec.

---

## 7. Jobs index (`routes/jobs.index.tsx`, path `/jobs`)

### Reads
Per job row: `job` (title), `client`, `stage`, `quoted` (currency), `code` (`JOB-0114`),
`float` (currency, **can be negative**), `collected` (Vietnamese prose status:
`"Đã thu 50%"`, `"Đã xuất hoá đơn"`, `"Quá hạn 12 ngày"`, `"Chưa thu"`).

`collected` is a **[derived]** rollup over that job's payment milestones, but the exact
rule (which milestone wins when several have different statuses? is "Đã thu 50%" the
*percentage collected* or the name of the collected milestone?) is undefined - flagged below.

Three stat tiles:
- In production = `Σ quoted` over listed jobs **[derived]**
- Crew float outstanding = `Σ max(float, 0)` - explicitly "advance − matched expenses" **[derived]**
- Overdue collections = **hardcoded 86,500,000**, "2 milestones past terms" **[derived]** in
  principle (same figure as Home's Overdue payments tile).

Header meta: `"<n> open jobs · <Σ quoted> ₫ in production"`.

### Writes
- **Create job** (`FormDialog`, `jobFields`): `job` name (required), `client` (required),
  `deal` (linked deal code, free text), `stage` (select from the 5 stages),
  `producer` (person name), `quoted` (₫), `float` (crew float advance, ₫).
  Server assigns `JOB-nnnn`. New jobs start `collected: "Chưa thu"`.
  Note the form lets you set a "crew float advance" at job creation, which in the backend
  model is a `Job Advance` row against a recipient - the form has no recipient field.
- **View toggle** table ↔ kanban. Kanban cards are again **not draggable** - no
  stage-change-by-drag mutation.

### Filters / sorts / groupings
- No search, no filter, no sort.
- Kanban grouping by `stage` over
  `Pre-production, Production, Post-production, Delivery, Awaiting payment`
  (English) with `Awaiting payment` visually focused.

---

## 8. Job detail (`routes/jobs.$jobId.tsx`, path `/jobs/:jobId`)

### Reads

**Header**: job title, `jobId`, client company, producer name (`Trần Mỹ Linh`),
shoot dates (`"Shoot 14–15 Aug 2026"` - a **shoot date range on the job**, which the
backend `Job` doctype does not have).

**Stage rail**: 5 Vietnamese stages `Chuẩn bị, Ghi hình, Hậu kỳ, Bàn giao, Thu tiền`
with `currentStage` index. Third stage vocabulary in the app - must be reconciled.

**Money card (founder only)**:
- `quoted` = quote total
- `actualCost` = 318,400,000 - `Σ` of expenses actually logged **[derived]**
- `committed` = 462,000,000 - **[NO SOURCE]**, spend that is contracted but not yet spent
- `projectedMargin` = 148,900,000 - **[NO SOURCE]**, depends on the committed figure
- `delta` = −2,500,000 "Delta vs quote basis" plus a free-text **cause**
  (`"Cause: catering overrun on day 2 (35 → 41 pax)."`) - **[NO SOURCE]**, both the number
  and the narrative.

**Payment milestones**: per milestone `label` (`"Đặt cọc 40%"`), `due` date, `amount`,
`status` (`Đã thu | Đã xuất hoá đơn | Dự kiến`). Plus a stacked progress bar and the
summary `"40% collected · 30% invoiced · 30% planned"` - **[derived]** as
`Σ pct` grouped by status. `Job Payment Milestone` already carries
`pct/amount/status/due_on/requested_on/invoiced_on/paid_on`.

**Crew float table**: per person `person`, `role`, `advance`, `expenses`;
`float = advance − expenses` **[derived]**, red when negative.
Grain: **per job, per person**. Backend: `Job Advance` (advances) + `Job Expense`
(spend attributed to `paid_by`) + `Job Settlement`.

**Activity & stage log** (labelled "Immutable"): per entry `when`, `who` (person or
`"System"`), `what` (headline), `note`. Seen event kinds:
stage move (`"Stage moved Ghi hình → Hậu kỳ"`), advance issued, revision round logged,
milestone collected. This is a **unified activity feed** over four different tables
(`Deal Stage Log`-equivalent for jobs, `Job Advance`, `Job Revision`,
`Job Payment Milestone`), each rendered to a headline + note string.

**Revision rounds**: `round` (`R1`), `scope` (`In scope | Change order`), `note`,
`amount` (0 for in-scope). Backend `Job Revision` has `round`, `chargeable`, `note`,
`requested_on`, `logged_by` - but **no amount**, and the UI prices change orders.

### Writes
- **Advance stage** (button) → move job to next production stage; must append to the log.
- **Log revision** (button, no handler) → `{note, chargeable/scope, amount?}`.
- **Add expense** → navigates to `/expense`.
- **Settle** button per crew-float row → settle the person's float
  (`Job Settlement`: recipient, amount, direction, advanced, spent).
- **Quote change order** link on chargeable revisions → back to the deal breakdown.

### Filters / sorts
None. Log appears newest-first; milestones in due order; floats in fixture order.

---

## 9. Quick expense (`routes/expense.tsx`, path `/expense`)

Mobile-shaped, one-thumb capture. Scoped to a single job + person via the header
(`"TVC Tết 2027 "Vị Xuân" · JOB-0182 · Trần Mỹ Linh"`) - the **scope is hardcoded**; a real
version needs a job picker or a "my current job" rule.

### Reads
- Float card: `advance` (15,000,000), `spent` (12,590,000), `left = advance − spent` **[derived]**.
  Grain: **per job, per person** - the same aggregate as the crew float table on screen 8.
- Category options = `expenseCategories`.
- "Today & yesterday" list: per row `what`, `cat`, `amount`, `when`
  (relative: `"Today 12:40"`, `"Yesterday"`), `state` (`Pending | Matched`).
  Grain: **the current user's expenses for the last 2 days**, needs a date-window query.
  `Pending | Matched` is a **third expense status vocabulary** (see below).

### Writes
- **Save expense**: `{job, person, amount (int VND, thousands-separated in the input),
  category, note, receipt photo}`. Sets state to `Pending` / "Awaiting producer match".
- **Attach receipt photo** - file/camera upload, needs a binary upload endpoint.
  Backend `Job Expense.photo` is an `Attach Image`, so this exists.

### Status vocabulary clash
Three different sets across the app for the same underlying thing:
- Quick expense: `Pending | Matched`
- Finance expenses: `Đã trả | Chờ trả | Chờ đối chiếu`
- Backend `Job Expense`: no status field at all, only `paid_from`.
These must be unified into one lifecycle before the endpoint can be typed.

---

## 10. Paperwork (`routes/paperwork.tsx`, path `/paperwork`)

Three-pane document workspace: list / editor canvas / right rail.

### Reads
- **Document list**, grouped by `group`: `Hợp đồng dịch vụ`, `Phụ lục`, `Biên bản`.
  Per document: `name`, `party` (a company or a person - `"Nhất Minh Beverage"`,
  `"Vũ Đình Nam"`), `status` (`Draft | Awaiting signature | Signed`),
  `when` (relative time: `"2h ago"`, `"3 days ago"`, `"Yesterday"`, `"1 week ago"`).
- **Editor canvas**: the document body itself - rich text with inline **gap tokens**
  (`{{ngay_ky}}`, `{{nguoi_dai_dien}}`, `{{so_tai_khoan}}`) rendered as chips. In preview
  mode unfilled gaps render as `[ chưa điền ]`. Subtitle shows client + deal code +
  `"saved 2 minutes ago"` (autosave timestamp).
  The rendered body is **hardcoded JSX**, not data - a real build needs stored document
  content (HTML or docx-derived) per document.
- **Gaps rail**: `{token, label}` per unfilled gap, plus a count in the card title
  (`"3 gaps remaining"`) and in the header meta (`"5 documents · 3 gaps remaining on the open draft"`).
  **[derived]** by scanning the body for unfilled tokens. Backend `Paperwork Template` has a
  `placeholders` field, so the token vocabulary exists; the *per-document unfilled set* does not.
- **Version history**: per entry `label` (`"Current draft"`, `"Save 3"`,
  `"Generated from template"`), `when`, `who` (person or `"System"`).

### Writes
- **New from template** → generate a document from a `Paperwork Template`, presumably
  bound to a deal/job and a party.
- **Export .docx** → server-side render.
- **Fill** a gap → set a token value on the document; must decrement the gap count.
- **Restore** a version → revert document body to that snapshot.
- Editing the body itself (autosave, "saved 2 minutes ago") → save document content.
- Rich-text toolbar (undo, redo, block type, bold, italic, underline, list, link)
  - **no handlers**, purely visual, but implies stored formatted content.

### Filters / sorts
- Search box over documents - **not wired**.
- Filter chips `All | Drafts | Awaiting signature | Signed`. Note `"Drafts"` (plural) maps
  to status `"Draft"` via a special case in the filter predicate.
- Grouping by document group is fixed and comes from the data.

---

## 11. Finance dashboard (`routes/finance.index.tsx`, path `/finance`)

### Reads
- **Cash on hand** = `Σ cashAccounts[].balance`, sub `"4 accounts incl. crew float"`. **[NO SOURCE]** - see new concepts.
- **Income YTD** = `Σ monthly[].income`; sub shows `Σ monthly[].expense`. **[derived]** from a
  monthly series that itself needs a recognition rule.
- **Profit YTD** = income − expense; sub `"Margin <pct>%"` where
  `pct = round(profit/income*1000)/10`. **[derived]**
- **Overdue receivables** = `Σ amount` and count over income rows with status `Quá hạn`. **[derived]**
- **Income vs expense** - `monthly[]` of `{month, income, expense}`, Jan–Aug 2026, with a
  per-month profit and two proportional bars scaled to `max(income, expense)` across the series.
  Grain: **per calendar month**. Badge `"Profit every month"` is hardcoded, not computed.
- **Cash accounts** list: `{name, balance, kind}` where kind ∈
  `Ngân hàng | Tiền mặt | Tạm ứng`. Subtitle "Live balances".
- **Where the money goes** - `expenseByCategory[]` of `{category, amount}`, YTD.
  Grain: **per category, YTD**. Categories: `Crew, Equipment, Art, Post-production,
  Catering & transport, Overhead`.
- **Receivables ageing** - `{bucket, amount}` for
  `Chưa đến hạn | 1–30 ngày | 31–60 ngày | 60+ ngày`. Grain: **per ageing bucket**.
- **Payables ageing** - same buckets, over unpaid expenses.

### Writes
None. "Open report" navigates to `/finance/reports`.

### Filters / date ranges
Header meta declares the range: `"YTD Jan–Aug 2026 · VND · all figures exclude VAT unless noted"`.
There is **no control** to change the period on this screen - the range is implicit.

---

## 12. Finance / Income (`routes/finance.income.tsx`, path `/finance/income`)

### Reads
Per invoice row (`IncomeRow`): `id` (`IN-2081`), `date` (paid-on, or `"—"`),
`client`, `deal` (deal code), `invoice` (invoice number `INV-0182-1`), `amount` (excl. VAT),
`vat` (absolute ₫, ~10% of amount in the fixture), `method` (`Chuyển khoản | Tiền mặt`),
`status` (`Đã thu | Chờ thu | Quá hạn`), `due` (due date).

Three stat tiles, all **[derived]** over the full row set (not the filtered set):
- Collected = `Σ amount where status = Đã thu`
- Outstanding = `Σ amount where status ≠ Đã thu`
- Overdue = `Σ amount where status = Quá hạn`

Header meta: `"<n> invoices · Jan–Aug 2026"`.

### Writes
**Create invoice** (`FormDialog`): `client` (required, free text), `deal` (deal code, free text),
`invoice` (invoice number, free text - **user-supplied, not server-generated**),
`amount` (text, digits stripped, excl. VAT, required), `vatPct` (select `10 | 8 | 0`
- note VAT is entered as a **rate** but stored as an **amount**: `vat = round(amount*vatPct/100)`),
`method` (select), `due` (date as free text, e.g. `"30 Sep 2026"`), `status` (select).
The row's `date` (paid-on) is auto-set to today iff status is `Đã thu` - i.e. **status change
implies a payment date**. Server assigns `IN-nnnn`.

Implied but absent mutations: mark-paid on an existing row, edit, delete, attach the
invoice PDF. There is no row action of any kind.

### Filters / sorts
- Status chips `All | Đã thu | Chờ thu | Quá hạn`, client-side.
- No search, no sort, no date range, no pagination.

---

## 13. Finance / Expenses (`routes/finance.expenses.tsx`, path `/finance/expenses`)

### Reads
Per expense row (`ExpenseRow`): `id` (`EX-4412`), `date`, `what` (description),
`category`, `job` (job code or `"—"` for overhead), `payee` (company or person name),
`taxType` (`Công ty | Cá nhân | Không hoá đơn`), `amount`,
`status` (`Đã trả | Chờ trả | Chờ đối chiếu`).

Three tiles **[derived]** over all rows:
- Paid = `Σ where Đã trả`, "Settled with payee"
- Due to pay = `Σ where Chờ trả`, "Approved, not paid"
- Waiting on receipts = `Σ where Chờ đối chiếu`, "Float not yet matched"

Plus the same **Spend by category** YTD aggregate as the dashboard.

Header meta: `"<n> entries · Jan–Aug 2026"`.

### Writes
**Create expense** (`FormDialog`): `what` (required), `category` (select:
`Crew, Equipment, Art, Catering, Transport, Production, Post-production, Overhead`),
`job` (select from a **hardcoded list** `JOB-0182, JOB-0171, JOB-0166, —`),
`payee` (free text), `taxType` (select), `amount` (text, digits stripped, required),
`status` (select). Date auto-set to today. Server assigns `EX-nnnn`.

No mark-paid, edit, delete, receipt-attach or match-to-float action exists on a row.

### Filters / sorts
- Status chips `All | Đã trả | Chờ trả | Chờ đối chiếu`, client-side.
- No search, no job filter, no category filter, no date range - despite the category
  taxonomy and job link being present on every row.

---

## 14. Finance / Reports (`routes/finance.reports.tsx`, path `/finance/reports`)

### Reads
- **Period selector**: `Q1 | Q2 | Q3 (đang mở) | YTD 2026`. **The selection changes only the
  header text** - every figure below is YTD regardless. A real endpoint needs a period
  parameter (quarter or YTD) and the quarter definitions.
  Header meta: `"<period> · VND · cash basis"` - **cash basis** is asserted here and matters
  for how income/expense months are computed.
- Four tiles:
  - Revenue = `Σ monthly.income`, "Recognised"
  - Direct cost = `ytd.expense − overhead`, where overhead is
    `expenseByCategory.find(c => c.category === "Overhead").amount` - a **category-name
    string match** driving a P&L split. Needs a proper direct/indirect flag on the category.
  - Overhead
  - Net profit + margin %
- **P&L by month** table: per month `income`, `expense`, `profit`, `margin %`
  (`round(profit/income*1000)/10`), with a Total row. Margin pill turns positive/ember at
  the **hardcoded 20%** threshold (should be `margin_floor_pct`).
  Grain: **per calendar month**.
- **Margin by job** (`jobProfitability[]`): `job` code, `name`, `revenue`, `cost`;
  profit and margin % **[derived]**; bars scaled to `max(revenue)`.
  Grain: **per job**. Covers "closed and open jobs".
- **Tax position** (`taxLines[]`): `{label, amount}` with signed amounts -
  `VAT đầu ra (Q3)` +111.4M, `VAT đầu vào được trừ` −62.8M,
  `TNCN khấu trừ freelancer` +24.6M, `TNDN tạm tính 20%` +96.2M, and a total
  `"Ước tính phải nộp"` = `Σ amounts`. Grain: **per tax line, per period**.
  Disclaimer "Estimate only".

### Writes
- **Export XLSX** button - no handler. Implies a server-side export of the report for the
  selected period.

### Filters
Period chips only (currently inert).

---

## 15. Finance / Forecast (`routes/finance.forecast.tsx`, path `/finance/forecast`)

Entirely forward-looking; nothing here maps to an existing entity.

### Reads
- `forecast[]` per month (Sep–Dec 2026): `{month, committed, weighted, expense, confidence}`
  - `committed` - income from jobs already won
  - `weighted` - pipeline income already multiplied by something
  - `confidence` - 0.75, 0.6, 0.45, 0.35, displayed as a % pill, green at `>= 0.6`
  - `expense` - projected outgoings per month
  Grain: **per future month**. All four fields **[NO SOURCE]**.
- `opening` cash = `Σ cashAccounts[].balance`, labelled "1 Sep 2026".
- Scenario definitions (client-side constants): `conservative (×0.5)`, `base (×1.0)`,
  `upside (×1.35)`, each with a note.

### Derived projection (client-side, must move server-side or be specified as a client rule)
```
income[m]  = committed[m] + round(weighted[m] * scenarioFactor)
net[m]     = income[m] - expense[m]
balance[m] = balance[m-1] + net[m]          // seeded with opening cash
closing    = balance[last]
avgBurn    = round(Σ expense / months)
runway     = round(closing / avgBurn * 10) / 10      // in months
lowest     = min(balance[])                  // drives "Never goes negative"
```
Runway tile turns red at `< 3` months (hardcoded threshold).

Also a **scenarios side-by-side** table: for each of the three scenarios, total income and
closing cash. Note this table uses `totalExpense` from the *currently selected* scenario,
which is scenario-independent, so it happens to be correct - but the coupling is accidental.

Comparison sub: `"vs <Σ monthly.income> ₫ Jan–Aug"` - joins realised and forecast series.

### Writes
None. Scenario selection is view state.

---

## 16. Contacts / Companies (`routes/contacts.companies.tsx`, path `/contacts/companies`)

### Reads
Per company: `name`, `type` (`Client | Vendor | Crew | Partner`), `contact` (primary contact
display name), `deals` (**count** of linked deals **[derived]**), `taxCode`,
`billed` (**"Billed to date"**, currency **[derived]** - sum of invoices to this company),
`address`, `bank` (single string `"Vietcombank · 0071 0007 12345"` - the backend splits this
into `bank_name`, `bank_account_number`, `bank_account_name`),
`people[]` (`{name, role}`), `dealList[]` (deal titles).

Header meta counts by type: `"5 companies · 1 client, 3 vendor, 1 partner"` - **[derived]**
`groupBy(type)`.

Detail drawer shows address, bank, billed to date, people list, linked deals list.

### Writes
- **Create company** (`FormDialog`): `name` (required), `type` (select),
  `taxCode`, `contact` (required, primary contact name), `role` (contact's role),
  `address`, `bank` (one free-text line). Creating a company also **creates its first
  person** (`people: [{name: contact, role: role || "Primary contact"}]`) - a compound
  mutation.
- **"Add person to <company>"** button in the drawer - no handler.

### Filters / sorts
- Free-text search over `name` and `contact`, client-side.
- Type chips `All | Client | Vendor | Crew | Partner`.
- No sort, no pagination.

---

## 17. Contacts / People (`routes/contacts.people.tsx`, path `/contacts/people`)

### Reads
Per person: `name`, `phone`, `email`, `company` (name or `"—"` for unaffiliated
freelancers), `tags[]` (`Client, Crew, Director, DOP, Internal, Producer, Vendor, Editor`
- these mix **party type** with **craft role**), `roles[]` of `{role, deal}` - i.e.
**"roles across deals"**, the person's function on each deal they touched. **[derived]**
from cost-line `source_contact` and deal/job contact links.

Header meta: `"<n> contacts · roles resolved across deals"`.

### Writes
- **New person** button - **no handler**. Payload would be name, phone, email, company, tags.
- Company field in the drawer is an editable `<input defaultValue>` with **no onChange and
  no save** - implies an update-person mutation that was never wired.

### Filters / sorts
- Free-text search over `name` and `company`.
- Tag chips `All | Client | Crew | Vendor | Internal` (a subset of the tags actually present
  - `Director`, `DOP`, `Producer`, `Editor` are shown but not filterable).
- No sort.

---

## 18. Settings (`routes/settings.tsx`, path `/settings`)

Every field is an uncontrolled `<input defaultValue>`; "Save changes" has no handler.
So this screen is a **complete read/write list of studio-wide config** with no persistence.

### Reads / writes (all singleton config)
**Pricing floors**
- `margin_floor_pct` (%) - hint text `"Current deal sits at 22.2%"` **[derived]**, and
  oddly deal-specific for a global settings page
- `management_fee_pct` (%)
- `vat_pct` (%)
- `founder_commission_pct` (CMF, %)

**Default markup by source** - a table of `{source, markup %, note}`:
`Internal 20%`, `Freelancer 15%`, `Vendor 20%`, `Không hoá đơn 10%`.
Note the fourth row mixes the **source** axis with the **tax type** axis - cost lines carry
both `source` and `taxType` independently, so a 4-row table keyed on a blended axis
cannot express the real matrix.

**Payment terms** - default milestone split: `Đặt cọc 40%`, `Sau ghi hình 30%`,
`Bàn giao 30%`; `net_terms_days` 15; `overdue_nudge_days` 3
(hint: `"Adds the deal to Attention Required on Home"` - this is the rule behind the
Home "Needs attention" feed).

**Letterhead & documents** - `legal_entity`, `tax_code`, `registered_address`,
`bank_account`, and a `contract_number_format` template
`HĐ-{year}/AURA-{client_code}-{seq}` (read-only display, not an input).

**Roles** - four roles with capability prose:
- Founder - everything incl. margin, commission, net profit
- Producer - deals, jobs, expenses, paperwork; **no margin figures**
- Accountant - milestones, invoices, settlements, exports
- Crew - quick expense entry on their **own float only**

This is the authoritative statement of the permission model. Note "Founder-only data stays
gated on the server" in the card subtitle - founder blocks must not be sent to
non-founder clients at all, not merely hidden.

---

## 19. Layout-only / infrastructure routes

`routes/deals.$dealCode.tsx`, `routes/quotations.tsx`, `routes/finance.tsx` are bare
`<Outlet />` layouts. `routes/__root.tsx` provides the QueryClient, HTML shell, fonts,
404 page and error boundary. **No backend requirement.**

---

# Consolidated model

## Entities

Legend: **[E]** already exists in the Frappe app, **[E+]** exists but needs new fields,
**[NEW]** no counterpart today.

### Sales

**1. Deal** **[E+]**
`code`, `title`, `stage` (Lead/Briefed/Breakdown/Negotiating/Won + Lost),
`owner`, `company`, `contact`, `tier`, `positioning`, `project_type`, `source`,
`tags[]`, `estimated_budget` (client budget), `brief`, `links[]`,
`quote_mf_pct`, `vat_pct`, `commission_pct`, `quote_detail_level`,
`quote_subtotal`, `quote_mf_amount`, `quote_vat_amount`, `quote_total`,
`quote_margin`, `quote_margin_pct`, `floor_breached`,
`quote_status`, `latest_quote`, `quote_sent_on`,
`total_commission`, `cm`, `profit_before_tax`, `tndn`, `net_profit`, `vat_payable`.
*New fields needed*: `idle_days` (derived), `weighted_value` (derived), `last_activity_on`.

**2. Deal Cost Line** **[E]** (child of Deal)
`idx`, `description`, `item_category`, `cost_phase`, `source_type`, `source_contact`,
`package`, `qty1`, `qty1_unit`, `qty2`, `qty2_unit`, `unit_price`, `tax_type`,
`markup_pct`, `vendor_mf_pct`, `subtotal`, `cost_basis`, `input_vat`, `quote_price`, `margin`.
*The UI never edits these* - CRUD for cost lines is unspecified.

**3. Deal Package** **[E]** (child of Deal)
`pkg` code (P1/P2/P3), `title`, `description`, `default_price` (member sum),
`has_price_override`, `price_override`, `price`, `variance`.

**4. Deal Stage Log** **[E]** - `from_stage`, `to_stage`, `changed_on`, `changed_by`.

### Quoting

**5. Quote (Deal Quote)** **[E+]**
`ref` (`QUO-0182-2`), `deal`, `version` label (`v2`, `v2-B`, `v2-C` - **the UI uses
suffixed option labels, not just integers**), `name`/`title` (client-facing document title),
`status` (Draft/Sent/Published/Accepted/Confirmed), `token`/`slug`, `detail_level`,
`client_name`, `client_address`, `client_tax_code`, `client_contact`, `recipient_email`,
`mf_pct`, `vat_pct`, `subtotal`, `mf_amount`, `vat_amount`, `total`,
`cost` (frozen cost basis for margin), `published_on`, `sent_on`, `confirmed_on`.
*New fields*: `valid_days` (quote validity / link expiry), `recipient_email`,
`cost` snapshot, non-integer version labels.

**6. Quote Line** **[E+]** (child of Quote)
`idx` (**drag-reorder needs this persisted**), `kind` (`package | divider`) **[NEW field]**,
`label`, `note`, `template_pkg`, `cost_line_ids[]` **[NEW - membership link to
Deal Cost Line]**, `qty1`, `unit1`, `qty2`, `unit2`,
`override_unit_price` (nullable - null means "sum the members") **[NEW semantics]**,
`amount` (derived).

**7. Quote Version Snapshot** **[E+]** - the Compare tab reads frozen
`{version, name, status, published, subtotal, feeRate, vatRate, total, cost, lines[]}`.
Today `Deal Quote` + `Deal Quote Package` roughly cover this; the snapshot must include
the frozen `cost` so historical margin can be recomputed.

**8. Quote Share Link** **[NEW]**
`quote`, `slug`, `recipient_email`, `published_on`, `expires_on`, `status`, `created_by`.
Today the token lives on `Deal Quote`, but the UI shows **one link per version with its own
recipient**, and a draft can have a link that was never sent.

**9. Quote Activity Event** **[E+]** (`Deal Quote Open` today)
`quote`/`share_link`, `occurred_on`, `event_type`
(`opened | downloaded_pdf | published | link_created`) **[NEW]**,
`actor_label` (identified contact, internal user, or `"Unknown (forwarded)"`) **[NEW]**,
`geo_city`, `geo_country` **[NEW]**, `device_label` (`"iPhone · Safari"`) **[NEW]**,
`dwell_seconds` **[NEW]**, `ip_address`, `user_agent`.

### Production

**10. Job** **[E+]**
`code` (`JOB-0114`), `title`, `stage`, `owner`/producer, `deal`, `company`, `contact`,
`quote_subtotal/mf/vat/total`, `mf_pct`, `vat_pct`, `commission_pct`,
`included_revision_rounds`, `revision_rounds`, `change_order_due`,
`files_location`, `links[]`, `cost_lines[]`, `packages[]`, `stage_history[]`.
*New fields*: `shoot_start` / `shoot_end` (the header shows "Shoot 14–15 Aug 2026"),
`committed_cost`, `projected_margin`, `delta_vs_quote`, `delta_cause` (free text).

**11. Job Payment Milestone** **[E]** (child of Job)
`title`, `pct`, `trigger_stage`, `amount`, `status`
(`Dự kiến | Đã xuất hoá đơn | Đã thu` + overdue), `due_on`,
`requested_on`, `invoiced_on`, `paid_on`.

**12. Job Revision** **[E+]**
`round`, `chargeable` (→ `In scope | Change order`), `note`, `requested_on`, `logged_by`.
*New field*: `amount` (the UI prices change orders at 18,500,000 ₫).

**13. Job Advance** **[E]** - `job`, `recipient`, `amount`, `transferred_on`, `note`.

**14. Job Settlement** **[E]** - `job`, `recipient`, `amount`, `direction`,
`advanced`, `spent`, `settled_on`, `settled_by`, `note`.

**15. Expense** **[E+]** (`Job Expense` today)
`code` (`EX-4412`), `job` (**must become optional** - overhead expenses have `job: "—"`),
`spent_on`, `description`, `category`, `payee` **[NEW]**, `tax_type` **[NEW]**,
`amount`, `status` **[NEW]**, `paid_by`, `paid_from`, `photo`,
`matched_advance` / float-matching link **[NEW]**.

**16. Job Activity Event** **[NEW, or a view]**
The job log unions stage moves, advances, revisions and milestone collections into
`{occurred_on, actor, headline, note}`. Either a materialised feed table or a
server-side union view.

### Parties

**17. Party Company** **[E+]**
`name`, `type`/`role_tags` (Client/Vendor/Crew/Partner), `tax_code`, `address`,
`phone`, `email`, `website`, `bank_name`, `bank_account_number`, `bank_account_name`, `notes`.
*Derived reads needed*: `deals_count`, `billed_to_date`, `people[]`, `deal_list[]`.

**18. Party Contact** **[E]**
`full_name`, `company`, `role_tags[]`, `phone`, `email`, `id_number`, `date_of_birth`,
`tax_code`, `permanent_address`, `contact_address`, bank fields, `notes`.
*Derived read needed*: `roles_across_deals[] = {role, deal}`.

**19. Party Role** / **Deal Tag** / **Deal Source** / **Project Type** /
**Cost Item Category** **[E]** - reference lists behind the filter chips and selects.

### Money

**20. Invoice** **[NEW]** (income row)
`code` (`IN-2081`), `invoice_no` (`INV-0182-1`, user-supplied), `client`, `deal`,
`amount` (excl. VAT), `vat_pct`, `vat_amount`, `method` (`Chuyển khoản | Tiền mặt`),
`status` (`Chờ thu | Đã thu | Quá hạn`), `due_on`, `paid_on`.
Overlaps heavily with `Job Payment Milestone` but is keyed to a **deal**, carries an
invoice number and a payment method, and is created standalone. Needs a decision:
one entity or two (see new concepts).

**21. Cash Account** **[NEW]**
`name`, `kind` (`Ngân hàng | Tiền mặt | Tạm ứng`), `balance`.

### Documents

**22. Paperwork Template** **[E]** - `template_name`, `template_file`, `template_source`,
`placeholders`, `disabled`, `notes`.

**23. Document** **[E+]** (`Generated Paper` today)
`name`, `group` (`Hợp đồng dịch vụ | Phụ lục | Biên bản`) **[NEW]**, `party`
(company **or** person), `deal`/`job`, `template`, `status`
(`Draft | Awaiting signature | Signed`) **[NEW]**, `body` (editable rich text) **[NEW]**,
`updated_on`, `file_url`.

**24. Document Gap** **[NEW]** - `document`, `token` (`{{ngay_ky}}`), `label`, `value`, `filled`.

**25. Document Version** **[NEW]** - `document`, `label`, `body_snapshot`, `saved_on`, `saved_by`.

### Config

**26. AuraOS Settings** **[E+]** (singleton)
Existing: `margin_floor_pct`, `quote_silence_days`, `payment_terms_days`, company block,
bank block, signature block, tier thresholds, positioning percentages.
*New*: `management_fee_pct` default, `vat_pct` default, `founder_commission_pct` default,
`overdue_nudge_days`, default milestone split (`40/30/30` as a table of
`{title, pct, trigger_stage}`), `contract_number_format`, and **default markup by source**.

**27. Source Markup Default** **[NEW]** (child of settings)
`source` (Internal/Freelancer/Vendor/Không hoá đơn), `markup_pct`, `note`.

**28. Role / permission profile** **[NEW as data]** - Founder / Producer / Accountant / Crew.
Frappe roles can carry this, but the founder-only field gating must be enforced server-side.

**Total: 28 entities**, of which 15 exist today, 5 exist but need new fields, and
**8 are entirely new** (Quote Share Link, Cash Account, Invoice, Document Gap,
Document Version, Source Markup Default, Job Activity Event, plus the Forecast
Assumption entity described under new concepts).

---

## Aggregates and reports

| # | Aggregate | Grain | Used by | Notes |
| --- | --- | --- | --- | --- |
| A1 | Open pipeline value + count | whole company | Home tile | weighted, rule undefined |
| A2 | In-production value + open job count | whole company | Home, Jobs | `Σ quote_total` |
| A3 | Overdue milestone total + count | whole company | Home, Jobs | `due_on < today`, unpaid |
| A4 | Silent-quote value + count | whole company | Home | window = `quote_silence_days` |
| A5 | Needs-attention feed | union of milestones + quotes | Home | ordered by age |
| A6 | Deal counts + value | **per stage** | Deals tiles | plus a Won-MTD bucket at a different grain |
| A7 | Deal quote-state summary | **per deal** | Deals table | latest version, status, opens count |
| A8 | Deal idle days | **per deal** | Deals table | red at ≥ 9d |
| A9 | Cost totals + quote totals | **per deal, per phase** | Breakdown | `Σ subtotal`, `Σ quote_price` |
| A10 | Package member sum | **per deal package** | Breakdown, Quote builder | `Σ member quote_price` |
| A11 | Quote line member sum & cost | **per quote line** | Quote builder | price sums `quote_price`, cost sums `subtotal` |
| A12 | Quote totals chain | **per quote** | 4 screens | subtotal → fee → beforeVat → VAT → total |
| A13 | Margin & margin % vs floor | **per quote / per deal** | 5 screens | basis is always before-VAT |
| A14 | Opens count + last activity | **per quote version** | Quotations, Share tab | counts `event_type = opened` |
| A15 | Quote version diff by line label | **pair of versions** | Compare tab | full outer join on label |
| A16 | Awaiting-decision value | whole company | Quotations header | `status ∈ {Sent, Published}` |
| A17 | Crew float balance | **per job, per person** | Job detail, Quick expense, Jobs list | `advance − matched expenses` |
| A18 | Crew float outstanding | whole company | Jobs tiles | `Σ max(float, 0)` |
| A19 | Milestone collection split | **per job** | Job detail | `Σ pct` grouped by status |
| A20 | Job collection summary string | **per job** | Jobs list | rule undefined |
| A21 | Job actual cost | **per job** | Job detail | `Σ expenses` |
| A22 | Job committed cost & projected margin | **per job** | Job detail | source undefined |
| A23 | Job activity feed | **per job** | Job detail | union of 4 tables |
| A24 | Income vs expense series | **per calendar month** | Finance dash, Reports, Forecast | recognition rule needed |
| A25 | YTD income / expense / profit / margin % | period | Finance dash, Reports | |
| A26 | P&L by month with per-month margin % | **per month** | Reports | |
| A27 | Direct cost vs overhead split | period | Reports | currently a category-name string match |
| A28 | Expense by category | **per category, YTD** | Finance dash, Expenses | 6 buckets |
| A29 | Receivables ageing | **per bucket** (`Chưa đến hạn / 1–30 / 31–60 / 60+`) | Finance dash | |
| A30 | Payables ageing | **per bucket** (same 4) | Finance dash | |
| A31 | Collected / outstanding / overdue | whole company | Income | by invoice status |
| A32 | Paid / due / unmatched | whole company | Expenses | by expense status |
| A33 | Job profitability | **per job** | Reports | revenue, cost, profit, margin % |
| A34 | Tax position | **per tax line, per period** | Reports | VAT out, VAT in, TNCN, TNDN, total |
| A35 | Cash on hand | whole company | Finance dash, Forecast | `Σ account balances` |
| A36 | Forecast projection | **per future month, per scenario** | Forecast | income, net, running balance |
| A37 | Runway / avg burn / lowest balance | period, per scenario | Forecast | red under 3 months |
| A38 | Company counts by type | whole directory | Companies header | |
| A39 | Deals count + billed-to-date | **per company** | Companies | |
| A40 | Roles across deals | **per person** | People | from cost lines + deal/job links |
| A41 | Gap count | **per document** and whole workspace | Paperwork | unfilled tokens |

---

## Mutations

### Deals
1. `createDeal(name, client, contact, stage, positioning, tier, budget, owner)` → assigns `DEAL-nnnn`
2. `updateDealStage(deal, stage)` - implied by the kanban but **not wired**
3. Cost line create / update / delete / reorder - **entirely unspecified by the UI**

### Quoting
4. `createQuotation(deal)` (from `/quotations/new` or "Convert to quotation")
5. `renameQuotation(quote, name)`
6. `addQuoteLineFromTemplate(quote, pkg)` - copies title, description, member cost lines
7. `createEmptyQuoteLine(quote, label)`
8. `addDivider(quote, label)`
9. `updateQuoteLine(line, {label, note, qty, unit, qty2, unit2, overrideUnitPrice})`
10. `resetQuoteLineOverride(line)` → `overrideUnitPrice = null`
11. `addCostLineToQuoteLine(line, costLineId)`
12. `removeCostLineFromQuoteLine(line, costLineId)`
13. `deleteQuoteLine(line)`
14. `reorderQuoteLines(quote, orderedIds[])`
15. `updateQuoteTerms(quote, {feeRate, vatRate, validDays, contactId})`
16. `updateQuoteDetailLevel(deal|quote, level)` (legacy screen)
17. `updatePackagePriceOverride(package, price)` (legacy screen)
18. `publishQuote(quote, {recipientEmail, validDays})` → creates share link, logs event, sets Published
19. `republishQuote(quote)`
20. `sendQuoteToClient(quote)` - button exists on the legacy screen, no handler
21. `renderQuotePdf(quote)` - currently `window.print()`
22. *(implicit)* `recordQuoteOpen(slug, ip, ua, dwell)` - a **public/guest** endpoint

### Jobs
23. `createJob(name, client, deal, stage, producer, quoted, floatAdvance)` → assigns `JOB-nnnn`
24. `advanceJobStage(job)` → next stage, appends to log
25. `logRevision(job, {note, scope, amount?})`
26. `settleFloat(job, person)` → creates a Job Settlement
27. *(implied)* `issueAdvance(job, person, amount)` - appears in the log, no UI control

### Money
28. `createInvoice(client, deal, invoiceNo, amount, vatPct, method, due, status)` → assigns `IN-nnnn`;
    sets `paid_on = today` if status is `Đã thu`
29. `createExpense(what, category, job|null, payee, taxType, amount, status)` → assigns `EX-nnnn`
30. `quickExpense(job, person, amount, category, note, receiptPhoto)` → status Pending
31. `uploadReceipt(expense, file)` - camera/file upload
32. *(implied, no control exists)* mark-invoice-paid, mark-expense-paid, match-expense-to-float,
    edit/delete for both

### Contacts
33. `createCompany(name, type, taxCode, contact, role, address, bank)` - **also creates the
    first Party Contact**
34. `addPersonToCompany(company, name, role)` - button, no handler
35. `createPerson(name, phone, email, company, tags)` - button, no handler
36. `updatePersonCompany(person, company)` - input exists, never saves

### Paperwork
37. `generateDocumentFromTemplate(template, deal|job, party)`
38. `saveDocumentBody(document, body)` - autosave, "saved 2 minutes ago"
39. `fillGap(document, token, value)`
40. `restoreDocumentVersion(document, versionId)`
41. `exportDocx(document)`

### Config
42. `saveSettings({marginFloorPct, managementFeePct, vatPct, commissionPct,
    markupsBySource[], milestoneSplit[], netTermsDays, overdueNudgeDays,
    legalEntity, taxCode, address, bankAccount})`

### Reports
43. `exportReportXlsx(period)`

**43 mutations**, of which **21 have no handler at all** in the prototype (they are buttons
that do nothing) and a further set are implied by displayed data with no control.

---

# Genuinely new domain concepts

Each of these appears in the UI with no counterpart in the current backend model, and each
needs a **product decision** before it can be built.

### N1. Cash account and cash balance
`finance.ts:cashAccounts` - four accounts with a `kind` of `Ngân hàng`, `Tiền mặt`, `Tạm ứng`
and a `balance`, summed into "Cash on hand" and used as the opening balance for the forecast.

**Decisions required**
- Is a balance **stored and manually reconciled**, or **computed from a ledger** of movements?
  Nothing in the app records a cash movement, so today it can only be manual.
- If computed, every invoice payment, expense payment, advance and settlement must post to
  an account - meaning `paid_from` / `paid_into` becomes mandatory on those entities.
- What is the `Tạm ứng` ("Float held by crew", 27,100,000 ₫) account? It looks like the
  *sum of outstanding crew floats* presented as an account. If so it is derived, not stored,
  and double-counting risk exists against A18.
- Are opening balances entered per account with a start date?

### N2. Invoice as a distinct entity from Payment Milestone
The Income screen creates standalone invoices keyed to a **deal**, with a user-typed invoice
number, a payment method and a VAT amount. Job payment milestones carry `invoiced_on` and
`paid_on` for the same money.

**Decisions required**
- Is an invoice created **from** a milestone (1:1), or independently?
- Can one invoice span several milestones, or several invoices settle one milestone?
- Is the invoice number issued by AuraOS (a sequence/format like the contract number format)
  or transcribed from the accounting system / e-invoice provider?
- Is `Quá hạn` a **stored status** or purely `due_on < today AND paid_on IS NULL`?
  The create form offers `Quá hạn` as a choice, which suggests stored - that will drift.
- Invoices are shown excl. VAT with a separate VAT amount; milestones show a
  VAT-inclusive amount (294,624,000 = 40% of 736,560,000). The two screens disagree on
  the basis. Which is authoritative?

### N3. Forecast / projection model
`finance.ts:forecast` - per future month `committed`, `weighted`, `expense`, `confidence`,
run through three scenario multipliers.

**Decisions required**
- **Committed income per month**: which future money counts? Unpaid milestones of won jobs
  bucketed by `due_on`? Signed-but-uninvoiced work? What about work with no dated milestone?
- **Weighted pipeline per month**: needs (a) a probability per deal stage or per deal, and
  (b) an **expected close/bill month** per deal - the Deal doctype has neither. Is the
  weighting `value × stage_probability`, and is the month the expected close month or the
  expected payment month?
- **Confidence per month** (0.75 → 0.35) is shown as a single number for the whole month.
  Is it the weighted-average probability of that month's pipeline **[derived]**, or a
  judgement the founder enters **[stored]**? The fixture's monotonic decay suggests a
  hand-set "the further out, the less I trust it" curve.
- **Projected expense per month**: from committed job cost schedules, from an overhead
  run-rate, or a manual budget?
- **Scenario factors** (0.5 / 1.0 / 1.35): fixed constants, or configurable? Note the
  upside factor can push weighted pipeline above 100% probability, which needs justifying.
- **Runway**: currently `closing_cash / avg_monthly_expense`, red under 3 months. Is
  average burn the right denominator (it includes production cost, which only occurs if
  the revenue also occurs), or should it be overhead-only burn?

### N4. Deal idle days and the silence clock
`idle: 1 | 2 | 5 | 9 | 14 | 21` days, red at ≥ 9.

**Decisions required**
- Idle since **what**? Last stage change, last quote sent, last client open, last note,
  or last touch of any kind?
- Is the red threshold `quote_silence_days` (already in settings) or a separate
  `deal_idle_days` setting? The Deals screen's 9-day threshold and the Home tile's
  "past 7 days" are two different numbers today.
- Do weekends/holidays count?

### N5. Weighted pipeline value
Home tile and the Deals card subtitle both show 1,925,000,000 while the stage tiles sum
to 2,630,000,000.

**Decisions required**
- A probability per stage (Lead x%, Briefed y%, Breakdown z%, Negotiating w%) - what are
  the numbers, and are they configurable?
- Is `Won MTD` excluded from the weighted figure (it appears to be)?
- Is the weight applied to `quote_total` (incl. VAT) or to before-VAT revenue? Mixing VAT
  into a pipeline number would overstate it by 8%.

### N6. Job committed cost, projected margin and delta-vs-quote
Job detail shows `committed 462,000,000`, `projectedMargin 148,900,000`,
`delta −2,500,000` and a free-text **cause**.

**Decisions required**
- What makes a cost "committed"? A signed vendor paperwork record? A booked crew member?
  An approved-but-unpaid expense? There is no purchase-order concept anywhere in the app.
- Is projected margin `quote_beforeVat − max(committed, actual)`, or
  `− (actual + remaining_budgeted)`?
- Delta is "vs quote basis" - the difference between the job's *snapshot* cost basis and
  the current projection. Which snapshot: the deal's cost basis at win time?
- Is the **cause** a manually written note per job, or derived from the largest
  overrunning cost line? The fixture's phrasing ("catering overrun on day 2, 35 → 41 pax")
  is specific enough to be either.

### N7. Expense lifecycle and float matching
Three status vocabularies (`Pending|Matched`, `Đã trả|Chờ trả|Chờ đối chiếu`, and no status
at all in the backend), plus a "Waiting on receipts / float not yet matched" aggregate.

**Decisions required**
- One lifecycle for all expenses, or two (a crew-float capture flow and an
  accounts-payable flow)? `Chờ đối chiếu` (awaiting reconciliation) is a float concept;
  `Chờ trả` (awaiting payment) is a payables concept. They are not points on one line.
- What does "matched" mean concretely - a producer approving the entry, a receipt photo
  being present, or the entry being offset against a specific `Job Advance`?
- Who can move an expense between states (the Roles card says Crew can only enter on their
  own float)?
- Can an expense exist with **no job** (the Overhead row has `job: "—"`)? If so `Job Expense`
  must be renamed/relaxed and overhead needs its own home.

### N8. Job collection summary
Jobs list shows a single prose cell per job: `"Đã thu 50%"`, `"Đã xuất hoá đơn"`,
`"Quá hạn 12 ngày"`, `"Chưa thu"`.

**Decisions required**
- Precedence: if a job has one collected milestone, one invoiced and one overdue, which
  wins? The fixture implies overdue beats everything, then percentage collected.
- Is "50%" the sum of collected milestone percentages, or `collected_amount / quote_total`?
- Is this a stored denormalised field or computed per request?

### N9. Quote share link with per-version recipient and rich open tracking
Geo city, device label, dwell seconds, identified visitor, `"Unknown (forwarded)"`,
`Downloaded PDF` and `link created` events, link expiry tied to quote validity.

**Decisions required**
- **Privacy/legal**: is IP geolocation of a client acceptable, and for how long is it kept?
- How is a visitor identified as `"Chị Phạm Thu Hà"` rather than unknown - a per-recipient
  token in the URL? If so, each recipient needs their own slug and the "one link per
  version" model in the UI is wrong.
- Dwell time requires a heartbeat or unload beacon on the public quote page - is that in scope?
- Does the link genuinely expire after `validDays`, and what does a client see afterwards?
- Does re-publishing invalidate the previous link, or does the UI's "Republish" keep it?

### N10. Document workspace: gaps, statuses, versions
Paperwork shows editable document bodies, unfilled `{{token}}` gaps with a running count,
a Draft → Awaiting signature → Signed lifecycle, and a restorable version history.
Today `Generated Paper` is just a produced file.

**Decisions required**
- Are documents stored as **editable content** in AuraOS (HTML? a docx round-trip?) or
  generated-once files? The toolbar, autosave and version history all imply the former,
  which is a significant scope change.
- Who advances a document to Signed, and does that trigger anything (a milestone becoming
  due, a deal becoming won)?
- Are gap values reusable across documents for the same party (fill `so_tai_khoan` once)?
- Is version history every autosave, or explicit saves only? The fixture shows named
  saves ("Save 2", "Save 3") plus a system-generated origin.

### N11. Revenue/expense recognition basis for the monthly series
Reports declare **cash basis**, the Finance dashboard says
"all figures exclude VAT unless noted", and Reports labels revenue "Recognised".

**Decisions required**
- Cash basis (money moved) or accrual (invoice issued)? The two screens use the same
  `monthly[]` array for both claims.
- Does an income month key off `paid_on` or `due_on`?
- Are the monthly figures VAT-exclusive? Invoices store amount excl. VAT, so probably yes -
  but then cash-on-hand (which is VAT-inclusive money) is on a different basis.
- Which expense categories count as direct cost vs overhead? Currently a **string match on
  the literal `"Overhead"`** - this needs a flag on `Cost Item Category`.

### N12. Tax position lines
`VAT đầu ra (Q3)`, `VAT đầu vào được trừ`, `TNCN khấu trừ freelancer`,
`TNDN tạm tính 20%`, summed to `Ước tính phải nộp`.

**Decisions required**
- Output VAT: from invoices' `vat` amounts in the period.
- Input VAT: cost lines already carry `input_vat`, but only lines with `tax_type = Công ty`
  should be deductible - confirm.
- TNCN withheld from freelancers: what rate, on which cost lines (`tax_type = Cá nhân`),
  and is it withheld at payment or at expense entry?
- TNDN "tạm tính 20%": 20% of what base, over what period, and does the estimate carry
  forward losses?
- Is the period a quarter (the label says Q3) while every other figure on the page is YTD?
  That inconsistency is in the fixture as written.

### N13. Ageing buckets
`Chưa đến hạn | 1–30 ngày | 31–60 ngày | 60+ ngày` for both receivables and payables.

**Decisions required**
- Aged from `due_on` or from invoice/expense date?
- Are the bucket boundaries fixed or configurable?
- Payables ageing implies expenses have a **due date**, which no expense field carries today.

### N14. Which deal the Home founder margin card shows
The card is hardcoded to DEAL-0182 and titled with that deal's name.

**Decisions required**: largest open deal, most recently edited, the one in Breakdown, or a
founder-pinned deal?

### N15. Default markup matrix
Settings offers four markup defaults keyed on a blend of `source` and `tax_type`.

**Decisions required**
- Is markup keyed on `source_type` (Internal/Freelancer/Vendor) alone, on `tax_type`
  alone, or on the pair? The current 4-row table cannot express the 3×3 matrix that the
  cost line actually supports.
- Can a category override the source default? Cost lines in the fixture use 10/15/18/20%,
  and 18% (Art department) matches no default at all.

### N16. Quote version labelling
`v1`, `v2`, `v2-B`, `v2-C` - options branching off a version, not a linear sequence.
`Deal Quote.version` is an `Int`.

**Decisions required**: are options siblings of a version (v2-B is an alternative to v2) or
children? Which one is "the" quote for pipeline value? Compare treats them all as peers.

### N17. Stage vocabularies
Four different sets are in play:
- Deals: `Lead, Briefed, Breakdown, Negotiating, Won` (+ `Won MTD` tile)
- Jobs list/kanban: `Pre-production, Production, Post-production, Delivery, Awaiting payment`
- Job detail rail: `Chuẩn bị, Ghi hình, Hậu kỳ, Bàn giao, Thu tiền`
- Home jobs table: `Production, Post-production, Delivery, Awaiting payment`
- Cost line phase: `Pre-production, Production, Post-production`

**Decisions required**: one canonical job stage list with Vietnamese labels and English
keys; confirm that cost-line *phase* is a separate axis from job *stage* (CONTEXT.md says
it is - phase is client-facing, stage is production-facing).

### N18. "2 quotes awaiting signature"
The Deals header counts quotes in a signature-pending state. `Deal Quote.status` has no
such value, and the app has no signature capture (CONTEXT.md explicitly says nothing is
signed on a screen).

**Decision required**: does this mean "Sent, unanswered", "Confirmed but contract unsigned"
(i.e. it reads the Paperwork document status), or should the string be dropped?

---

# Presentational only - no backend needed

- **Sidebar navigation** - static array of routes, icons and section headings; no counts,
  no badges, no permission filtering (though the Roles card implies there should be).
- **"Quick actions ⌘K"** chip in the header - no palette, no handler, no search.
- **404 page and error boundary** (`__root.tsx`) plus `lib/error-capture.ts`,
  `lib/error-page.ts`, `lib/lovable-error-reporting.ts` - dev tooling that posts to the
  Lovable preview harness. Should be deleted, not ported.
- **Tone/colour maps** everywhere (`stageTone`, `statusTone`, `taxTone`, `typeTone`,
  `tagTone`, `pillTones`) - pure styling lookups keyed on status strings.
- **`Bar` component** proportional widths, `KanbanBoard` height measurement, dot-grid
  background, `Card` tone variants, drag opacity and the ember drop indicator.
- **Table ↔ Kanban view toggle** - view state only, not persisted, and no drag-to-change-stage
  behind it on either board.
- **Tab selection** on the quotation builder and the finance sub-nav.
- **Copy-to-clipboard** on share links - browser API, though the *slug* is server data.
- **`window.print()`** for "Download PDF" - the real thing needs a server render, but the
  button itself is client-only today.
- **The rich-text toolbar** in Paperwork (undo, redo, block type, bold, italic, underline,
  list, link) - all decorative buttons with no handlers.
- **The whole of `components/ui/`** (52 shadcn files: accordion, carousel, chart, command,
  menubar, sidebar, etc.) - **unused by every route**. The aura routes only use
  `components/aura/*`. Dead weight.
- **Hardcoded prose** that should become data but is currently just text:
  the PDF letterhead block, the PDF payment-terms footer, the contract body in Paperwork,
  the "Cause: catering overrun" line, "Profit every month", "Good morning, Bảo",
  "Estimate only — confirm with the accountant before filing", and the
  "The client sees exactly this page" helper text.
- **`vnd()` formatting** (`Intl.NumberFormat("vi-VN")`) and the `Money` component's
  `₫` suffix - display concerns; the API should return integers.

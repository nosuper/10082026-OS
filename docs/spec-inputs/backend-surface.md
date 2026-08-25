# AuraOS backend surface - inventory as of 2026-08-18 (branch `main`, commit 9558030)

Scope: `/opt/auraos/auraos/` only. (`/opt/auraos/.claude/worktrees/...` holds a stale
copy of `api.py`; ignored throughout.)

Headline numbers:

- **55 whitelisted methods**, all in `/opt/auraos/auraos/api.py`. Exactly one is
  `allow_guest=True` (`quote_pdf`).
- **28 doctypes** under `/opt/auraos/auraos/auraos/doctype/`: 17 normal, 10 child
  tables, 1 Single.
- **0 query reports, 0 dashboard charts, 0 number cards, 0 workspaces, 0 scheduler
  events, 0 fixtures.** `hooks.py` declares only `after_install`/`after_migrate`, one
  `File.before_insert` doc event, a global-search list, and two website route rules.

---

## 1. Whitelisted API methods

All in `auraos/api.py`. "Gate" column names the actual server-side check.

### Deals - table/board plumbing

| # | Method (args) | Returns | Gate |
|---|---|---|---|
| 1 | `operating_users()` | `[{name, full_name}]` - enabled users holding Founder or Producer | `has_permission("Deal","read")` |
| 2 | `update_deal_table_row(deal, values)` | row dict: `name,title,company,stage,deal_owner,estimated_budget,source,project_type,quote_status,quote_sent_on,modified,tags[]` | `doc.check_permission("write")`; `values` restricted to `DEAL_TABLE_EDITABLE_FIELDS` (title, company, stage, deal_owner, estimated_budget, source, project_type, deal_tags) - unknown keys throw by name |
| 3 | `create_deal_table_row(values)` | same row dict | `has_permission("Deal","create")` + same field whitelist |
| 4 | `deal_comments(deal)` | `[{name, content, comment_email, comment_by, creation}]` asc | `_check_deal_permission(deal,"read")` |
| 5 | `add_deal_comment(deal, content)` | one comment dict | `_check_deal_permission(deal,"write")` |
| 6 | `deal_attachments(deal)` | `[{name, file_name, file_url, file_size, owner, creation}]` desc | `_check_deal_permission(deal,"read")` |
| 7 | `deal_tags_map()` | `{deal_name: [tag,...]}` | `has_permission("Deal","read")`, then child rows scoped to `frappe.get_list("Deal")` |
| 8 | `deal_stage_entries()` | `{deal_name: datetime}` - when each deal entered its current stage | same pattern |

`_check_deal_permission` / `_check_job_permission` (api.py:140-160) are the reusable
doc-level gates: existence check (DoesNotExistError) then
`frappe.has_permission(dt, ptype, doc=..., throw=True)`. They exist because the reads
that follow use `frappe.get_all`, which skips row-level permissions.

### Breakdown / pricing

| # | Method | Returns | Gate |
|---|---|---|---|
| 9 | `compute_breakdown(lines, quote_mf_pct=10, vat_pct=8, commission_pct=None, packages=None)` | `{lines[], packages[], subtotal, management_fee, vat, total, margin, margin_pct, floor_breached}` plus `founder{commission_pct, total_commission, cm, profit_before_tax, tndn, net_profit, total_input_vat, vat_payable, margin_floor_pct}` **only for Founder sessions**. Each `lines[]` entry carries `subtotal, cost_basis, input_vat, quote_price, margin` plus echoed metadata `item_category, cost_phase, source_type, source_contact`. Each `packages[]` entry: `title, description, default_price, price, variance, overridden`. | `has_permission("Deal","read")` + `_is_founder()` for the founder block; a producer-supplied `commission_pct` is silently replaced with `DEFAULT_COMMISSION_PCT = 5` |
| 10 | `deal_profit(deal)` | founder block for a saved deal | **Hard role check**: `if not _is_founder(): throw(PermissionError)`, then `doc.check_permission("read")` |

### Quote delivery

| # | Method | Returns | Gate |
|---|---|---|---|
| 11 | `publish_quote(deal, notes=None)` | quote dict (below) | delegated to `deal_quote.publish` → `deal.check_permission("write")` |
| 12 | `deal_quotes(deal)` | `[{name, version, status, total, published_on, sent_on, confirmed_on, url, pdf_url, opens, downloads, last_open}]`, newest first | `_check_deal_permission(deal,"read")` |
| 13 | `deal_quote_links()` | `{deal: {version, status, url}}` for every permitted deal - the current version only | `has_permission("Deal","read")` + `get_list` scoping |
| 14 | `quote_opens(quote)` | `[{opened_on, via, ip_address}]`, limit 50 | deal-level read via the quote's `deal` |
| 15 | `mark_quote_sent(quote)` | quote dict | `_check_deal_permission(deal,"write")` |
| 16 | `mark_quote_confirmed(quote)` | quote dict | same |
| 17 | `silent_quote_deals()` | `{silence_days, deals:[{name,title,quote_status,quote_sent_on,latest_quote}]}` | `has_permission("Deal","read")`; `silent_deals()` itself uses `get_list` |
| 18 | `quote_pdf(token)` | PDF response (side effect: records a `PDF` open) | **`allow_guest=True`** - the 32-char token is the whole authorization |

### Jobs

| # | Method | Returns | Gate |
|---|---|---|---|
| 19 | `create_job_from_deal(deal)` | `{name, title, stage}` | `_check_deal_permission(deal,"read")`; the insert enforces Job create |
| 20 | `jobs_by_deal()` | `{deal: job}` | `has_permission("Job","read")` + `get_list` |
| 21 | `log_job_revision(job, note)` | `{name, revision_rounds, change_order_due, round, chargeable, stage, redo}` | `_check_job_permission(job,"write")` |

### Money out on a job

| # | Method | Returns | Gate |
|---|---|---|---|
| 22 | `job_money(job)` | `{advances[], expenses[], settlements[], floats[{holder,advanced,spent,settled,amount,direction}], categories[{title,quoted,actual,variance}], advanced_total, spent_total, quoted_total, may_advance, may_settle}` | `_check_job_permission(job,"read")`. `may_*` are `has_permission("Job Advance"/"Job Settlement","create")` - capability hints for the UI, not the gate |
| 23 | `job_expense_categories(job)` | `[title]` in quote order | job read |
| 24 | `record_job_advance(job, recipient, amount, transferred_on=None, note=None)` | `{name, float}` | job **write** + create permission on Job Advance (founder-only doctype perm) |
| 25 | `log_job_expense(job, amount, category=None, description=None, spent_on=None, paid_by=None, paid_from=None, photo=None)` | `{name, amount, category, photo, float}` | job write; `_attach_photo` only re-parents an unattached File the caller owns |
| 26 | `settle_job(job, holder, note=None)` | `{name, recipient, amount, direction, settled_on, float}` | job write + create on Job Settlement (founder-only) |

`ADVANCE_FIELDS`, `EXPENSE_FIELDS`, `SETTLEMENT_FIELDS` (api.py:545-553) define the row
shapes returned.

### Payment milestones

| # | Method | Returns | Gate |
|---|---|---|---|
| 27 | `job_milestones(job)` | `{payment_terms_days, milestones:[milestone_view]}` | job read |
| 28 | `save_job_milestones(job, milestones)` | same as 27 | job write; only `title/pct/trigger_stage` accepted, amounts always derived |
| 29 | `set_milestone_status(job, milestone, status, invoice_no=None)` | one `milestone_view` | job write; a number is only accepted with `Invoiced` |
| 30 | `milestone_invoice_request(job, milestone)` | `{text, invoice_no, invoiced_on, amount, vat_pct, net, vat}` - the Zalo message plus the figures it is built from | job read |
| 31 | `overdue_milestones()` | `{payment_terms_days, milestones:[{...milestone_view, job, job_title, company}]}` **across all permitted jobs** | `has_permission("Job","read")`; `overdue()` scopes by `get_list("Job")` |

`milestone_view` shape: `name, idx, title, pct, trigger_stage, amount, status, due_on,
requested_on, invoiced_on, paid_on, invoice_no, invoice_vat_pct, overdue, days_overdue`.

`invoice_no` and `invoice_vat_pct` are the invoice itself, kept beside the moment it
was issued: both are null until `invoiced_on` exists, both are cleared if the milestone
walks back before it, and the rate is captured once at issue so today's rate cannot
restate an invoice the client already holds.

### Paperwork

| # | Method | Returns | Gate |
|---|---|---|---|
| 32 | `paperwork_templates()` | non-disabled templates: `name, template_name, template_file, template_source, notes, disabled, placeholders, unknown_placeholders, needs_vendor, needs_freelancer` | `has_permission("Paperwork Template","read")` |
| 33 | `paperwork_library()` | `{can_manage, placeholders[], templates[]}` (all, incl. retired) | read; `can_manage` = create permission |
| 34 | `generate_job_paperwork(job, template, vendor=None, freelancer=None)` | `{name, file_name, file_url, missing[], unknown[]}` | job **write** + template read |
| 35 | `job_paperwork(job)` | files attached to the job | job read |
| 36 | `save_job_paperwork_draft(job, template, html, vendor=None, freelancer=None)` | `{name, file_name, file_url}` | job write + template read |
| 37 | `preview_template(template)` | `{html, web, file_url}` | template read |
| 38 | `preview_paper(file_url)` | `{html}` | resolves the File, requires it be attached to a Job, then job read |
| 39 | `preview_job_paperwork(job, template, vendor=None, freelancer=None)` | preview payload from `paperwork_template.preview` | job read + template read |
| 40 | `generated_papers()` | registry rows: `name, job, template, template_name, vendor, freelancer, file_name, file_url, owner, creation, vendor_label, freelancer_label` | `has_permission("Generated Paper","read")` + `get_list` (row perms apply) |
| 41 | `job_parties(job)` | `{freelancers:[{name, full_name}]}` from the job's own cost lines | job read |

### Settings and classification dials

| # | Method | Returns | Gate |
|---|---|---|---|
| 42 | `get_margin_floor()` | float | `has_permission("AuraOS Settings","read")` → **effectively founder-only** |
| 43 | `set_margin_floor(pct)` | float | Settings **write** |
| 44 | `get_tier_thresholds()` | `{tier2, tier3}` | Settings read |
| 45 | `set_tier_thresholds(tier2=None, tier3=None)` | same | Settings write |
| 46 | `get_positioning_rules()` | `{mix:{cash,bridge,brand}, project_types:[{name,is_positioning}]}` | Settings read |
| 47 | `set_positioning_rules(cash, bridge, brand, positioning_types)` | same | Settings write |
| 48 | `classification_hints()` | `{cash,bridge,brand}` mix only | `has_permission("Deal","read")` - deliberately producer-visible |
| 49 | `preview_tier(estimated_budget=0, project_type=None, positioning=None)` | tier string | Deal read - computed server-side so a producer never learns the thresholds |
| 50 | `get_quote_silence_days()` | int | Settings read |
| 51 | `set_quote_silence_days(days)` | int | Settings write |
| 52 | `get_payment_terms_days()` | int | Settings read |
| 53 | `set_payment_terms_days(days)` | int | Settings write |
| 54 | `get_company_identity()` | the 12 `COMPANY_FIELDS` as stored | Settings read |
| 55 | `set_company_identity(values)` | same | Settings write + field whitelist (`COMPANY_FIELDS`) - anything else refused by name |

Note the `_save_setting(fieldname, value)` helper (api.py:1169) shared by 43/51/53.

`get_margin_floor` doubles as the **frontend's founder probe** (see §4).

---

## 2. Doctypes

`/opt/auraos/auraos/auraos/doctype/` - 28 total. Child tables marked (child).

### Deal domain

**Deal** (`format:DEAL-{####}`, title field `title`, track_changes) - a sales
opportunity from brief to won/lost; carries the whole cost breakdown and the derived
quote chain.
- Header: `title` Data; `stage` Select (Brief Received | De-brief | Breakdown | Quote
  Sent | Negotiation | Won | Lost); `deal_owner` Link User.
- Client: `company` Link Party Company (reqd); `contact` Link Party Contact.
- Brief: `brief` Text.
- Details: `estimated_budget` Currency; `source` Link Deal Source; `project_type` Link
  Project Type; `tier` Select (Tier 1/2/3); `tier_is_manual` Check (hidden);
  `positioning` Select (Cash | Bridge | Brand); `deal_tags` Table MultiSelect → Deal
  Tag Item.
- Tables: `deal_links` → Deal Link; `cost_lines` → Deal Cost Line; `packages` → Deal
  Package; `stage_history` → Deal Stage Log (read-only).
- Params: `quote_mf_pct` Percent (10); `vat_pct` Percent (8); **`commission_pct`
  Percent, permlevel 1**, default 5; `quote_detail_level` Select (Package totals | Line
  by line | Lump sum).
- Computed, producer-visible, read-only: `quote_subtotal`, `quote_mf_amount`,
  `quote_vat_amount`, `quote_total`, `quote_margin`, `quote_margin_pct`,
  `floor_breached`.
- Quote delivery mirror, read-only: `quote_status` (Not Sent | Published | Sent |
  Confirmed), `latest_quote` Link Deal Quote, `quote_sent_on` Datetime.
- **Founder-only block, all permlevel 1 and read-only**: `total_commission`, `cm`,
  `profit_before_tax`, `tndn`, `net_profit`, `vat_payable`.
- Lost: `lost_reason` Select (Price | Timing | Silence | Competitor | Scope),
  `lost_note`.
- Perms: Founder / Producer / System Manager full at level 0; **permlevel 1 granted to
  Founder and System Manager only**.

**Deal Cost Line** (child) - one row of the internal cost breakdown; the input to the
pricing engine. Inputs: `description`, `item_category` Link Cost Item Category,
`cost_phase` Select (Pre/Production/Post/Appendix), `source_type` Select
(Internal|Freelancer|Vendor), `source_contact` Link Party Contact, `package` Data,
`qty1`/`qty2` Float with `qty1_unit`/`qty2_unit`, `unit_price` Currency, `tax_type`
Select (Công ty | Cá nhân | Không hoá đơn), `vendor_mf_pct`, `markup_pct`. Computed
read-only: `subtotal`, `cost_basis`, `input_vat`, `quote_price`, `margin`.

**Deal Package** (child) - a client-facing bundle of cost lines. `title`,
`description`, `has_price_override` Check, `price_override` Currency; computed
read-only `default_price`, `price`, `variance`.

**Deal Link** (child) - a labelled URL on a deal or job: `label`, `url`. Reused by Job
as `job_links`.

**Deal Stage Log** (child) - one stage move: `from_stage`, `to_stage`, `changed_on`,
`changed_by`. Reused by Job.

**Deal Tag Item** (child) - `deal_tag` Link Deal Tag. **Deal Tag** - founder-managed tag
vocabulary (`tag_name`). **Deal Source** (`source_name`) and **Project Type**
(`type_name` + `is_positioning` Check) - founder-managed vocabularies; Producer read
only (Deal Tag and Cost Item Category also allow Producer create).

**Cost Item Category** - `category_name`; the line-item taxonomy.

### Quote domain

**Deal Quote** (`format:{deal}-Q{version}`) - an immutable published snapshot of a
deal's offer. `deal` Link, `version` Int, `status` Select (Published | Sent |
Confirmed), `token` Data (32-char server hash); frozen bill-to block `title`,
`client_name`, `client_address`, `client_tax_code`, `client_contact`, `detail_level`,
`notes`; tables `packages` → Deal Quote Package and `lines` → Deal Quote Line; totals
`quote_mf_pct`, `vat_pct`, `subtotal`, `mf_amount`, `vat_amount`, `total`; tracking
`published_on`, `sent_on`, `confirmed_on`. Producer may create but **not delete**.

**Deal Quote Package** (child) - `title`, `description`, `price` (all read-only).
**Deal Quote Line** (child) - `package`, `description`, `qty1`, `qty1_unit`, `qty2`,
`qty2_unit`, `quote_price`. Only frozen for line-by-line quotes.

**Deal Quote Open** (`hash`) - one client page view or PDF download: `quote`,
`opened_on`, `via` Select (Page | PDF), `ip_address`, `user_agent`. Inserted with
`ignore_permissions` from the guest page. Nobody but System Manager may create.

### Job domain

**Job** (`format:JOB-{####}`, track_changes) - a won deal in production; carries a
frozen snapshot of the deal's money.
- `title`, `stage` Select (Pre-production | Production | Post-production | Client
  review | Delivery | Client sign-off | Awaiting payment | Complete), `job_owner`,
  `files_location`, `deal` Link (read-only), `company`, `contact`.
- `job_links` → Deal Link.
- Feedback: `included_revision_rounds` Int (2), `revision_rounds` Int (read-only),
  `change_order_due` Check (read-only), `revisions` → Job Revision.
- `payment_milestones` → Job Payment Milestone.
- Carried snapshot, read-only: `cost_lines` → Deal Cost Line, `packages` → Deal
  Package, `quote_mf_pct`, `vat_pct`, `quote_subtotal`, `quote_mf_amount`,
  `quote_vat_amount`, `quote_total`; **`commission_pct` permlevel 1**.
- `stage_history` → Deal Stage Log.
- Perms mirror Deal, including permlevel 1 = Founder + System Manager.

**Job Payment Milestone** (child) - a slice of the quoted total the client owes.
`title`, `pct` Percent, `trigger_stage` Select (the 8 job stages), `amount` Currency
(derived, read-only), `status` Select (Not requested | Requested | Invoiced | Paid),
`due_on`, `requested_on`, `invoiced_on`, `paid_on` (all derived).

**Job Revision** (child) - one client revision round: `round` Int (derived),
`chargeable` Check (derived), `requested_on`, `logged_by`, `note`.

**Job Advance** (`ADV-{#####}`) - company cash handed to a person for a job: `job`,
`recipient` Link User, `amount`, `transferred_on` Date, `note`. **Producer is read-only;
only Founder/System Manager may create, write, delete.**

**Job Expense** (`EXP-{#####}`) - one payment out on a shoot: `job`, `amount`,
`category` Data, `spent_on` Date, `paid_by` Link User, `paid_from` Select (Advance |
Company), `description`, `photo` Attach Image. Founder and Producer both have full CRUD.

**Job Settlement** (`STL-{#####}`) - the record of a float being closed: `job`,
`recipient`, `amount`, `direction` Select (Return | Top-up), `advanced`, `spent`,
`settled_on`, `settled_by`, `note` - everything except `note` read-only.
**Producer is read-only; Founder-only create.**

### Paperwork

**Paperwork Template** (`PWT-{####}`) - a .docx or web-HTML contract template:
`template_name`, `template_file` Attach, `template_source` Long Text, `disabled` Check,
`notes`, `placeholders` Small Text (read-only, extracted). **Producer read/print/report
only; Founder owns the library.**

**Generated Paper** (`GP-{#####}`) - registry row for every document ever generated:
`job`, `template`, `template_name`, `vendor` Link Party Company, `freelancer` Link
Party Contact, `file_name`, `file_url`. Producer may create and read, not delete/write.

### Parties and settings

**Party Company** (`COM-{####}`) - a client, vendor or supplier: `company_name`,
`role_tags` → Party Role Tag, `tax_code`, `address`, `phone`, `email`, `website`,
`bank_name` Select (36 Vietnamese banks), `bank_account_number`, `bank_account_name`,
`notes`. Note: bank details on the **counterparty**, not on us as an account balance.

**Party Contact** (`PER-{####}`) - a person: `full_name`, `company`, `role_tags`,
`phone` (reqd), `email`, freelancer block (`id_number`, `date_of_birth`, `tax_code`,
`permanent_address`, `contact_address`), the same bank triple, `notes`.

**Party Role** (`role_name`) + **Party Role Tag** (child, `party_role`) - the
Client/Vendor/Freelancer vocabulary.

**AuraOS Settings** (Single) - `margin_floor_pct` Percent, `quote_silence_days` Int (5),
company identity (`logo`, `company_name`, `tax_code`, `address`, `phone`, `email`,
`website`), bank block (`bank_name`, `bank_account_number`, `bank_account_name`),
signature (`signatory_name`, `signatory_title`), `payment_terms_days` Int (7),
`tier2_threshold`/`tier3_threshold` Currency, `positioning_cash_pct` /
`positioning_bridge_pct` / `positioning_brand_pct` Int.
**Perms: Founder and System Manager only - no Producer row at all.**

**Founder Spike Note** (`FSN-{####}`) - `title`, `note`. No business logic; exists as
the permission-proof fixture (Founder + System Manager only).

---

## 3. Derived / computed logic already in Python

Four framework-free modules under `auraos/lib/` hold the arithmetic; the doctype
controllers and `api.py` are thin adapters. **All of it is reusable by a reporting UI
without a Frappe session** - the modules take plain mappings and return dataclasses or
dicts.

### `lib/money.py` (26 lines)
`to_decimal`, `round_vnd` (half away from zero, Excel-compatible), `format_vnd`
(dot-separated đồng). Everything money-shaped funnels through these.

### `lib/pricing.py` (262 lines) - the engine
Normative source is `docs/samples/cost-breakdown-template.xlsx`; xlsx column letters are
in the comments.
- `TaxType` enum: Công ty (8% VAT), Cty 10%, Cá nhân (PIT gross-up ÷ 0.9), Không hoá
  đơn. `TaxType.parse` is case- and hóa/hoá-insensitive.
- `compute_line(CostLine, DealParams) -> ComputedLine`: subtotal, cost after vendor MF,
  VAT/PIT, **profit cost basis**, input VAT, internal gross, marked-up unit price, line
  total/budget, quote MF, after-MF, VAT, subtotal-with-VAT, **margin**, margin %, **CMF
  (commission)**, **CM**, CM %.
- `compute_quote(...) -> QuoteResult`: subtotal, management fee, output VAT, total,
  revenue ex VAT, total profit cost basis, **total commission**, **profit before tax**,
  **TNDN at 20 %** (`TNDN_RATE`), **net profit**, total input VAT, **VAT payable**.
- `package_price(member_line_totals, override) -> PackagePrice` (default, price,
  variance, overridden).
- `is_floor_breached(margin_pct, floor_pct)` - `None` margin always breaches (fails safe).

### `lib/quote.py` (474 lines) - client-facing projection, versioning, nudge
- `COMPANY_FIELDS` / `CLIENT_QUOTE_FIELDS` / `CLIENT_PACKAGE_FIELDS` /
  `CLIENT_LINE_FIELDS` - the guest whitelists. `client_view(quote)` and
  `company_view(settings)` are copy-only projections (`has_bank`, `has_contact`,
  `has_letterhead` flags for empty blocks).
- `quote_number(name, version)` → `DQ-0007-v2`.
- `client_entries(packages, lines)` - what the client is offered, in reading order:
  packages first, then any cost line in no package as its own entry. **This same rule
  drives expense categories** (see settlement).
- `line_sections`, `_rescaled_lines` - an overridden package price is folded back into
  its member lines proportionally, remainder on the last line, so the client's own
  arithmetic always closes. `quantity_display` ("2 người × 3 ngày"), `_unit_rate`.
- `lump_sum_entry(title, entries)` - collapse to one line, scope preserved in the
  description.
- `quote_totals(package_prices, mf_rate, vat_rate) -> QuoteTotals` - subtotal from the
  **printed** package prices (not the engine total), MF on subtotal, VAT on both.
- **`quote_chain(package_prices, cost_basis, input_vat, mf_rate, vat_rate,
  commission_rate) -> QuoteChain`** - the full profit chain measured against what the
  client actually pays: subtotal, mf_amount, vat_amount, total, revenue_ex_vat, margin,
  margin_fraction, total_commission, cm, profit_before_tax, tndn, net_profit,
  vat_payable. **This is the single most reusable computation in the codebase for any
  profitability report.**
- `delivery_state(versions)` - the newest *delivered* version, not the newest published
  one. `needs_nudge(status, sent_on, now, silence_days)` - 0 disables.

### `lib/breakdown.py` (152 lines) - the one assembly
`breakdown_view(line_rows, package_rows, *, quote_mf_pct, vat_pct, commission_pct,
margin_floor_pct)` composes pricing + quote into one dict (rounded whole đồng):
`lines[]`, `packages[]`, `subtotal`, `management_fee`, `vat`, `total`, `margin`,
`margin_pct`, `floor_breached`, and a separate `founder{}` sub-dict. `rate(pct)` turns a
Percent field into a fraction. **Callers: `api.compute_breakdown` (live editor) and
`Deal.breakdown_view` (persisted) - deliberately one builder so the two cannot drift.**

### `lib/settlement.py` (260 lines) - float and actual-vs-quoted
- Constants: `FROM_ADVANCE`/`FROM_COMPANY`, `RETURN`/`TOP_UP`/`EVEN`, `UNCATEGORISED`.
- `floats(advances, expenses, settlements) -> [Float]` and `float_for(holder, ...)`.
  Float = advanced − spent-from-advance − settled; `direction_of(amount)` gives
  Return/Top-up/Even. Only `paid_from == "Advance"` expenses touch a float.
- `categories(packages, cost_lines)` - the allowed expense categories, same rule as
  `quote.client_entries`.
- `category_actuals(packages, cost_lines, expenses) -> [CategoryActual(title, quoted,
  actual, variance)]` - **per-package quoted-vs-actual cost**; unknown categories fall
  into one trailing `Uncategorised` row. `_handed_over(line)` defines the quoted side as
  cash actually paid out (subtotal × (1+vendor MF) + input VAT), deliberately *not* the
  PIT-grossed profit cost basis.
- `totals(advances, expenses, categories) -> Totals(advanced, spent, quoted)`.

### `lib/milestones.py` (273 lines) - money in
- **`milestone_amounts(total, percents)`** - cumulative rounding so the shares sum
  exactly to the quoted total.
- `allocated_pct(percents)`; `invoice_split(amount, vat_pct) -> InvoiceSplit(net, vat)`
  - back out VAT from a VAT-inclusive milestone.
- `stage_reached(stage, trigger, stages)` - reached, not equalled.
- `due_stamp(reached, due_on, status, now)` - stamped once, never restarted; un-dues
  only while status is Not requested.
- **`is_overdue(status, due_on, now, terms_days)`** and **`days_overdue(...)`** - days
  past the *terms*, not days since due; terms of 0 disables.
- `stamps_for(status, current, now)` - the four-step collection flow's timestamps, with
  clean walk-back.
- `format_pct`, `vnd_with_symbol`, `invoice_request_text(client, milestone, job_title,
  vat_pct)` - the Vietnamese Zalo message to the accountant.

### `lib/paperwork.py` (857 lines)
Placeholder extraction and filling for .docx and web-HTML templates, `document_values()`
(the five placeholder namespaces: job / quote / client+contact / vendor / freelancer /
today), `fillable_placeholders()`, `fill_docx`, `fill_html`, `html_to_docx`,
`docx_to_html`, `highlight_gaps`. Notably `quote.*` placeholders expose only subtotal,
mf_amount, vat_amount, total, mf_pct, vat_pct - **the Deal is deliberately not a
placeholder namespace, so no permlevel-1 number can leak through a template.**

### Controller-level derivations

| Where | What it computes |
|---|---|
| `deal.py: margin_floor_pct()` | reads the Single via `db.get_single_value` (works inside a Producer session) |
| `deal.py: tier2_threshold/tier3_threshold` | defaults 50 M / 200 M đồng via `settings.setting` |
| `deal.py: derive_tier(budget, project_type, positioning)` | Brand or a positioning-flagged Project Type ⇒ Tier 3; else the two budget thresholds; no budget ⇒ None |
| `deal.py: Deal.apply_tier` | keeps the tier derived unless a human pinned it (`tier_is_manual`) |
| `deal.py: floor_breached(margin_fraction)` | 0 floor never warns |
| `deal.py: append_stage_change(doc)` | writes a Deal Stage Log row on insert or stage change - shared by Deal and Job |
| `deal.py: holds_operating_role(user)` | explicit `Has Role` lookup (not `get_roles`, which reports everything for Administrator) |
| `deal.py: Deal.compute_breakdown` | persists the producer-visible outputs onto the doc and its child rows |
| `deal.py: Deal.store_founder_chain` | persists `total_commission, cm, profit_before_tax, tndn, net_profit, vat_payable` with `db_set` in `on_update` (must be post-save: Frappe resets permlevel-1 fields a producer touches) |
| `deal_quote.py: next_version`, `publish`, `frozen_lines`, `client_block` | quote versioning, freeze, and the frozen bill-to block |
| `deal_quote.py: reject_content_changes` | published quotes are immutable except `status`/`sent_on`/`confirmed_on` |
| `deal_quote.py: before_insert` | **token = `frappe.generate_hash(length=32)`**, server-generated only |
| `deal_quote.py: sync_deal_quote_state` | mirrors `latest_quote`, `quote_status`, `quote_sent_on` onto the Deal via `db.set_value` |
| `deal_quote.py: advance_deal_stage` | marking sent moves a pre-send deal to "Quote Sent" |
| `deal_quote.py: silence_days / silent_deals` | the quote-silence nudge |
| `deal_quote.py: page_url / pdf_url / client_context / record_open` | public quote URLs and the open log |
| `job.py: create_from_deal` | won-deal guard, duplicate guard, carries cost lines/packages/links, seeds `DEFAULT_MILESTONES` 50/25/25 |
| `job.py: reject_snapshot_changes` | `FROZEN_FIELDS` + `FROZEN_TABLES` - the carried breakdown cannot be edited on the job |
| `job.py: number_revisions / included_rounds / redo_stage_for` | round numbering, `chargeable` past the included count, `change_order_due`, and the Post-production redo bounce |
| `job.py: expense_categories` / `carry_commission` | delegate to settlement / `db_set` past permlevel |
| `job_payment_milestone.py: apply_to` | derives every milestone amount, due date and stamp on save |
| `job_payment_milestone.py: validate_plan` | >100 % allocation throws; <100 % allowed |
| `job_payment_milestone.py: milestone_view` | adds `overdue` + `days_overdue` |
| `job_payment_milestone.py: overdue()` | **cross-job** overdue list, scoped by `get_list("Job")` |
| `job_payment_milestone.py: request_text` | pulls the client's tax code off Party Company |
| `job_settlement.py` | `direction_of(amount)`, frozen-field guard |
| `job_expense.py: validate_category` | category must be one of the job's quoted entries (this is what makes actual-vs-quoted whole) |
| `job_advance.py: validate_recipient` | only Founder/Producer may hold a float |
| `settings.py: setting(fieldname, default)` | reads the cached Single so an unset Int is `None`, not a deliberate 0 |
| `attachments.py: check_attachment_permission` | `File.before_insert` hook - attaching to Deal or Job requires write on the target |

---

## 4. Permission model

There is **no custom permission-query hook, no `has_permission` doctype hook, no
`permission_query_conditions`**. The boundary is built from four mechanisms, in order of
strength:

**(a) Doctype-level role permissions (the primary boundary).** Founder-only or
Founder-write doctypes:

| Doctype | Producer gets |
|---|---|
| AuraOS Settings | **nothing at all** |
| Founder Spike Note | **nothing at all** |
| Job Advance | read / print / export / report only - **no create, write, delete** |
| Job Settlement | read / print / export / report only - **no create** |
| Paperwork Template | read / print / report only |
| Deal Quote | everything except delete |
| Generated Paper | create / read / print / export, no write or delete |
| Deal Source, Party Role, Project Type | read only |
| Deal Tag, Cost Item Category | read + create, no write/delete |
| Deal, Job, Job Expense, Party Company, Party Contact | full CRUD, same as Founder |

**(b) Field-level permlevel 1.** On **Deal**: `commission_pct`, `profit_section`,
`total_commission`, `cm`, `profit_before_tax`, `tndn`, `net_profit`, `vat_payable`. On
**Job**: `commission_pct`. Permlevel-1 read+write is granted to **Founder and System
Manager only**. Frappe strips these from `get_doc`, `get_list` and form submissions for
a Producer session - which is why `Deal.store_founder_chain` and `Job.carry_commission`
have to write them with `db_set` *after* the save (both methods document this).

**(c) Explicit Python role checks - exactly two, both in `api.py`:**
```python
def _is_founder():                       # api.py:253
    return "Founder" in frappe.get_roles()
```
- `compute_breakdown` (api.py:296, 315): a non-founder's supplied `commission_pct` is
  discarded in favour of the 5 % default, and the `founder` key is deleted from the
  response before it is (conditionally) re-added.
- `deal_profit` (api.py:328-329): `frappe.throw(_("Only the Founder may see the profit
  chain"), frappe.PermissionError)`.

Everywhere else the check is `frappe.has_permission(...)` against a doctype, which
resolves through (a) - so "founder-only" for settings, advances, settlements and the
template library is really "the Producer role has no permission row".

**(d) Doc-level gates in front of permission-skipping reads.** `_check_deal_permission`
and `_check_job_permission` (api.py:140-160), plus the
`permitted = frappe.get_list(...)` scoping used by `deal_tags_map`,
`deal_stage_entries`, `deal_quote_links` and `job_payment_milestone.overdue()`. These
matter because those endpoints then use `frappe.get_all`, which bypasses row-level
permissions; the comments say so explicitly.

**Related guards:** `holds_operating_role(user)` uses an explicit `Has Role` row lookup
rather than `frappe.get_roles`, because `get_roles` returns every role for
Administrator. `attachments.check_attachment_permission` closes the core-Frappe hole
where any System User could attach a File to any document.

### Is any founder-only data protected only in the UI?

**No - nothing founder-sensitive is UI-only.** The frontend's founder flag
(`frontend/src/App.vue:15-23`, repeated in `pages/HomePage.vue:268-279`) is a *probe*,
not a gate: it calls `auraos.api.get_margin_floor` and sets `isFounder = true` only if
the server answers. It hides the Settings nav item and two margin cards, all of whose
data comes from endpoints the server independently refuses. `DealBreakdownPage.vue:470`
renders the founder card on `v-if="live?.founder"` - i.e. on the presence of the
server-gated key, not on a client-side role guess. The code comments state the rule
outright ("The UI is never the permission boundary").

Two things worth flagging as *deliberate* non-secrets rather than leaks:
- **Margin is producer-visible.** `compute_breakdown` returns `margin`, `margin_pct`,
  `floor_breached` and per-line `margin`/`cost_basis` to any Deal reader. Only
  commission / CM / profit / TNDN / VAT-payable are founder-gated. The stored Deal
  fields agree (`quote_margin`, `quote_margin_pct` are permlevel 0).
- **Money-in is producer-visible on purpose.** `job_payment_milestone.py:9-12` documents
  the decision: a producer sees the quoted total, milestone amounts, due dates and
  overdue state.

One genuine sharp edge for a future UI: `job_money` returns `may_advance` / `may_settle`
booleans so the screen can hide controls; those are hints derived from
`frappe.has_permission`, and the server still refuses the write - but a new UI must not
treat their absence as the only guard.

---

## 5. What is NOT there

Definitive answers. Nothing below exists in any doctype, whitelisted method, lib
function, report, dashboard chart or scheduler job.

| Asked for | Exists? | What is there instead |
|---|---|---|
| **Cash or bank account model** | **NO** | Bank *details* exist as text fields on Party Company, Party Contact and AuraOS Settings (`bank_name`, `bank_account_number`, `bank_account_name`) - printed on quotes and contracts. There is no account entity, no balance, no opening balance, no transaction ledger against an account, no reconciliation. The closest thing to a balance anywhere is `settlement.Float`, which is one *person's* outstanding advance on one *job*. |
| **Financial forecast or projection** | **NO** | No forward-looking anything. `estimated_budget` on a Deal is an input field, never aggregated. `preview_tier` classifies a single deal. There is no pipeline-weighted revenue, no expected-cash-in schedule, no runway. Milestone `due_on` is per-job and only ever queried for the overdue case. |
| **Cross-deal quote listing** | **NO** (partial primitive only) | `deal_quotes(deal)` is single-deal. `deal_quote_links()` is cross-deal but returns only `{deal: {version, status, url}}` for the *current* version - no totals, no dates, no open counts. `silent_quote_deals()` is cross-deal but filtered to sent-and-quiet. There is no "all quote versions across all deals with totals and status". |
| **Income/expense reporting aggregated by month or category** | **NO** | Aggregation by *category* exists but only **within one job**: `settlement.category_actuals` via `job_money(job)`. Nothing aggregates across jobs, and **nothing anywhere groups by month** - `spent_on`, `transferred_on` and the milestone timestamps are stored but never bucketed. No Frappe query report exists to do it either. |
| **Accounts receivable / payable views** | **NO** (a partial AR nudge only) | `overdue_milestones()` is the nearest thing: cross-job, but restricted to milestones already past the payment terms, and it returns no aging buckets, no per-client rollup, no total-outstanding. Everything not yet overdue (Not requested / Requested / Invoiced but within terms) is invisible to it. **Accounts payable does not exist in any form** - there is no vendor bill, no due date on an expense, no unpaid-supplier concept. Job Expense records money *already* spent. |
| **Per-job profitability** | **NO** | The profit chain (`quote_chain`, and the persisted `total_commission / cm / profit_before_tax / tndn / net_profit / vat_payable`) lives on the **Deal**, and is computed from *quoted* costs, not actual spend. A Job carries `quote_total` and its permlevel-1 `commission_pct` but **no profit fields at all** - `Job.json` has no `cm`, no `net_profit`, no `profit_before_tax`. `job_money` compares actual expenses against *quoted cost* per category (variance), which is cost control, not profit: it never touches revenue, commission or tax. Nobody computes "what this job actually earned". |

### Other notable absences

- No customer/client-level rollup of any kind (no "revenue by client", no client P&L).
- No time period model - no fiscal year, no month/quarter entity, no closing.
- No invoice document. Invoicing is an external accountant, reached by a Zalo message
  (`milestone_invoice_request`); the app records only that a milestone reached the
  `Invoiced` status.
- No overhead, salary or fixed-cost model. TNDN (20 %) is the only tax computed at the
  entity level, and it is computed per deal.
- No currency other than VND; `round_vnd` assumes whole đồng throughout.
- No notification, email or scheduled job. Both "nudges" (quote silence, overdue
  milestones) are pull-only endpoints the SPA polls.

### What a reporting UI would most likely reuse as-is

1. `lib/quote.quote_chain(...)` - the whole profit chain from a set of prices.
2. `lib/breakdown.breakdown_view(...)` - one call, the entire money view of any
   breakdown, founder block separable.
3. `lib/settlement.category_actuals / floats / totals` - quoted-vs-actual and float
   maths, given plain rows.
4. `lib/milestones.milestone_amounts / is_overdue / days_overdue / invoice_split` - the
   receivable side.
5. `lib/money.round_vnd / format_vnd` - the rounding contract the rest of the system
   assumes.

All five are Frappe-free and take plain mappings, so a new aggregation layer can call
them over `frappe.get_all` rows without going through the doctype controllers.

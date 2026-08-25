# AuraOS front-end rebuild — Attio Clean / Producer Desk

Rebuild the AuraOS UI on the chosen direction (light near-white canvas, faint dot grid,
white cards with hairline borders, Space Grotesk + DM Sans, single ember accent) while
keeping every piece of backend logic in the Frappe app untouched.

## What stays exactly as it is

- All Python: `auraos/api.py`, DocType controllers, `auraos/lib/*` (pricing, breakdown,
  quote, settlement, milestones, paperwork), permissions, attachment guard.
- The guest quote page's server side (`www/quote.py`, `templates/includes/quote_body.html`,
  `CLIENT_QUOTE_FIELDS` whitelist) — the client-facing quote and PDF are not part of this
  rebuild.
- All existing endpoint names, payload shapes and status vocabularies. The new UI calls the
  same `auraos.api.*` methods with the same arguments.
- Test harnesses: pytest, Frappe site tests, and the Playwright suite in `frontend/e2e/`
  stay the source of truth. Selectors the e2e specs rely on are preserved.

## What gets rebuilt

The Vue 3 layer in `frontend/src` — every page and component, screen by screen:

1. **Design system + shell.** Tokens, dot-grid canvas, fixed 256px sidebar (Home, Deals,
   Jobs, Paperwork, Contacts with **Companies** and **People** as separate sub-items,
   Settings + founder-only items), sticky header with a Quick Actions field (`/` and ⌘K),
   user block at the sidebar foot.
2. **Home dashboard.** The chosen bento layout: Attention Required (silence nudges,
   quotes pending signature), founder-only dark Margin card, full-width Active Production
   table with stage pills, Cash Flow Milestones, Advances & Float.
3. **Deals + Deal breakdown.** Pipeline list with stage/tag/source filters; the breakdown
   and pricing editor (cost lines, packages, phases, margin floor warning, quote publish /
   send / version history) rebuilt on the new primitives, same server calls.
4. **Jobs + Job detail.** Stage flow with logged moves, revision rounds and change orders,
   money panel (advances, floats, expenses, settlement), milestones panel with the
   Vietnamese collection statuses, quoted-vs-actual per category.
5. **Paperwork as a document workspace, Contacts, Settings.** Paperwork becomes a
   Google-Docs-like surface (detailed below); plus parties and roles, and global settings
   (margin floor, payment terms, letterhead).

Mobile expense entry (`JobExpensePage`) is treated as its own single-column screen, since
that is the one screen used on a phone on set.

## Paperwork: document workspace

Three panes, replacing the old template-list-and-generate form:

- **Document list** (middle rail): search, status filters (All / Drafts / Awaiting
  signature / Signed as the existing statuses allow), template folders as groups, rows
  showing document name, party, status pill, relative date. "New from template" starts a
  generation from a Paperwork Template with a Deal/Party picked.
- **Editor canvas** (main): the generated document rendered as an A4 page in a rich text
  editor (TipTap), with an Edit / Preview toggle and a compact toolbar (undo/redo, block
  style, bold/italic/underline, lists, link). Preview is an HTML render of the filled
  template styled as the printed page — not a PDF viewer.
- **Right rail**: gap markers surfaced as a "N gaps remaining" card listing each unfilled
  token with a Fill action that jumps to and replaces it inline; below it, version history
  (current + previous saves with time and author) with restore.

Export to `.docx` stays as it is today (server-side, via `lib/paperwork.py`). No share
links and no signature flow are built — documents stay internal: generate, edit, fill
gaps, export.

## Contacts: companies and people as separate surfaces

Instead of tabs inside a single Contacts page, the sidebar exposes **Companies** and
**People** as two distinct routes under a collapsible Contacts group. Both surfaces share
a unified search and a right-side detail drawer, but their lists and fields differ.

- **Companies** (`/contacts/companies`): table of Party Companies with type pills
  (Client / Vendor / Crew / Partner), primary contact, deal count, and tax code. Clicking
  a row opens a side drawer showing addresses, bank details, linked deals, and the
  company’s roles (people who belong to it). Add/edit opens a form dialog.
- **People** (`/contacts/people`): table of individual contacts with name, phone, email,
  role tags, and the company they belong to. Clicking a row opens a side drawer showing all
  roles across deals (e.g. “Client on Project X”, “Producer on Project Y”), contact info,
  and deal links. The company field is editable in-place.
- **New actions** in each list create the correct entity directly: “New company” vs
  “New person”. Adding a person from a company drawer pre-fills the company field.
- Search filters across both surfaces: type, tag, and deal. The URL keeps the active
  sub-route (`/contacts/companies` or `/contacts/people`) so refresh and deep links work.

Shared primitives: `ContactDrawer`, `CompanyForm`, `PersonForm`, `RoleList`, `TypePill`.


## Deals: table-first pipeline

- Header shows open count and quotes awaiting signature, plus a Table / Pipeline view
  toggle (table is the default; pipeline is the same data as stage columns).
- Filter bar: text filter, then Stage / Source / Tag / Owner dropdowns, with the weighted
  pipeline total pinned right.
- Five stage summary tiles (Lead, Briefed, Quoted, Negotiating, Won MTD) each with count
  and value; the current-attention stage is outlined in the accent.
- Table columns: Deal (name + code + phase-of-total), Client (company · contact), Stage
  pill, Quote state (version, sent/opened/accepted, opens count), Tags, Value, Margin,
  Idle days. Margin is founder-only and is served by a founder-gated endpoint, not hidden
  in the UI. Idle days and unopened quotes render in the accent as the nudge signal.

## Job detail: one job, everything in place

- Sticky header: breadcrumb + job code, project name, deal/phase/producer/shoot dates,
  actions (Log revision, Add expense, Advance stage), and a horizontal stage rail with the
  Vietnamese stage vocabulary and the current stage filled in the accent.
- Activity & stage log (main column): immutable, timestamped events — stage moves,
  advances issued, revisions logged, milestones paid — with the consequence spelled out on
  the line (e.g. a revision that needs a change order flags the unquoted amount).
- Money panel (founder-only dark card): quoted, actual cost, committed, projected margin,
  and the delta vs the quote basis with its cause.
- Payment milestones: each milestone with due date, amount and status (paid / invoiced /
  planned) plus a single stacked progress bar.
- Crew float: per-person float with positive, zero and negative states, and a Settle
  action; float is derived (advance − matched expenses), never stored.
- Revisions: rounds tagged in-scope vs change-order, with a "Quote change order" action
  that hands off to the deal's pricing surface.

## API contract step (before Phase 2)

Each screen gets an explicit response shape documented alongside it, so the UI does not
read DocType internals: `deal_list`, `deal_breakdown`, `job_detail`, `job_money`,
`paperwork_document`, `contact_list`. Founder-only fields (margin, profit basis) live in
separately gated endpoints so the permission boundary stays on the server. This is a
documentation and endpoint-shaping step, not a rewrite of `api.py` — though splitting
`api.py` into `api/deal.py`, `api/job.py`, `api/paperwork.py` is recommended alongside it.

## Shared primitives to build first

`AppShell`, `SidebarNav`, `QuickActions`, `BentoCard`, `DataTable`, `StatusPill`,
`MoneyValue` (tabular VND, grouped thousands, no decimals), `VndInput`, `ComboInput`,
`FormDialog`, `EmptyState`, `Toast`. Pages compose these; no page invents its own chrome.


## Ordering

Phase 1 design system + shell + Home. Phase 2 Deals + breakdown. Phase 3 Jobs + money +
milestones. Phase 4 Paperwork, Contacts, Settings, mobile expense. Each phase is a working
site — nothing is half-migrated at the end of a phase.

## Technical notes

- Vue 3 + Vite stays. Tailwind moves to a token set matching the direction:
  canvas `#fbfbfa`, ink `#1a1a1a`, muted `#6b6b6b`, border `#e8e8e7`, accent `#e85d3a`,
  radius 12px, dot grid `radial-gradient(circle, #e8e8e7 1px, transparent 1px)` at 24px.
  Fonts loaded via `<link>` in `frontend/index.html`.
- frappe-ui stays for resources/auth (`createResource`, `createListResource`) and for
  Autocomplete/Dialog primitives, but its default visual styling is overridden by our own
  components so screens do not read as stock frappe-ui.
- Colors, spacing and radii are tokens only — no hardcoded hex in components.
- Founder-only cards render off a role check, and the underlying founder data stays
  server-gated; the UI never becomes the permission boundary.
- Build output path is unchanged (`auraos/public/aura` + `auraos/www/aura.html`), so Frappe
  keeps serving `/aura`.
- Paperwork editor: TipTap (`@tiptap/vue-3` + StarterKit, Underline, Link) with a custom
  inline node for gap markers so tokens stay addressable and countable after edits. The
  document body is stored as TipTap JSON; export keeps going through the existing
  `.docx` path, with the edited body converted back to the template's token positions.
- One backend touch is unavoidable here: `Generated Paper` needs a field to hold the
  edited body JSON (and, for version history, saved revisions). That is the only Python
  change in the plan and I will flag it for your approval before writing it — everything
  else stays frontend-only.


## Working constraint

This Lovable workspace cannot run a Frappe bench, so the rebuilt Vue files are authored
here and verified by you in your Docker dev site (`docker compose up -d`, `npm run dev`)
and by `./scripts/e2e.sh`. I will keep each phase self-contained so you can pull, look,
and reject a phase without unwinding the others.

## Not in this plan

Backend changes, new features, schema changes, the client quote page/PDF, and production
deployment (T13).

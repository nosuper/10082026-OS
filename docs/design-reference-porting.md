# Porting the Lovable design reference into the Vue app

Founder decision, 2026-08-18: **option A.** The Lovable output is a design reference, not the next version of the app. The live Vue frontend stays; screens are ported across one at a time, the way Phase 1 was.

## Why not adopt it directly

Branch `feat/attio-clean-phase2` (commit `638c4e6`) deletes the entire Vue frontend - 54 files, every page and component, plus the Playwright suite - and replaces it with a React + TanStack Start app. Three things make it a rewrite rather than an upgrade:

- **No backend.** Grepping all 22 routes for `auraos.api`, `/api/method` and `frappe` returns nothing. Every figure is hardcoded in `src/data/`.
- **A different deployment model.** The Vue app is a SPA that Frappe serves at `/aura` via `auraos/www/aura.html`. The React app is SSR with its own Node server, and its nitro build targets `cloudflare-module` - preview is `wrangler dev`, deploy is `wrangler deploy`. Nothing writes into `auraos/`.
- **The test suite goes with it.** `frontend/e2e/` (8 passing specs) is deleted.

Adopting it means rebuilding the data layer, authentication, role gating, file upload and .docx generation, then choosing somewhere to run a Node server next to Frappe. That is weeks of work, and the app is unusable in the meantime.

## Where the reference lives

Kept checked out permanently as a git worktree so both stacks can have their own `node_modules`:

```
/opt/auraos-design-ref          worktree on feat/attio-clean-phase2
/opt/auraos                     main checkout, the real Vue app
```

To view it:

```bash
cd /opt/auraos-design-ref/frontend
npm install          # first time only
npx vite dev --host 0.0.0.0 --port 8950
```

Then `http://192.168.1.94:8950`. No login - the data is fake, so every screen opens directly.

`vite preview` does **not** work on this build: nitro emits to `.output/` for Cloudflare while the preview plugin looks for `dist/server/server.js`. Use dev mode, or `npx wrangler dev`.

## Screen map

What the reference actually asks for, sorted by what it costs.

### Restyle only - the screen and its API already exist

| Reference route | Vue page | Notes |
| --- | --- | --- |
| `deals.index.tsx` | `DealsPage.vue` | Board plus table, both already built |
| `deals.$dealCode.quote.tsx` | `DealBreakdownPage.vue` | The densest screen; port last of this group |
| `jobs.index.tsx` | `JobsPage.vue` | |
| `jobs.$jobId.tsx` | `JobPage.vue` | Three tabs already exist |
| `expense.tsx` | `JobExpensePage.vue` | Reference drops the job from the path (`/expense`); the real route is `/jobs/:name/expense` and should stay job-scoped |
| `paperwork.tsx` | `PaperworkPage.vue` | |
| `settings.tsx` | `SettingsPage.vue` | Founder-gated, keep the denied state |
| `contacts.companies.tsx`, `contacts.people.tsx` | `ContactsPage.vue` | Phase 1 already added the route aliases; this finishes the split into two real pages |
| `index.tsx` | `HomePage.vue` | Already ported in Phase 1 - diff it rather than redo it |

### New views over data we already hold

Cheaper than they look. Nothing new in the domain, but each needs an aggregate API endpoint.

| Reference route | Built from | Missing |
| --- | --- | --- |
| `quotations.index.tsx` | Deal Quote records across all deals | A cross-deal list endpoint; today quotes are only reachable inside their deal |
| `quotations.$quoteRef.tsx` | Deal Quote plus its versions and open tracking | Mostly a presentation of `QuotePanel.vue` as a full page. 1,251 lines - the largest file in the reference |
| `deals.$dealCode.index.tsx` | Deal | Today the deal record is a dialog, not a page. Promoting it to a page is a real IA change - decide deliberately |

### Genuinely new - needs backend work

The whole `finance.*` section, five screens. `src/data/finance.ts` declares `monthly`, `forecast`, `incomeRows`, `expenseRows`, `expenseByCategory`, `cashAccounts`, `receivables`, `payables`, `jobProfitability`.

Most of that is derivable from what already exists:

- **receivables** - payment milestones not yet collected
- **income** - milestones marked paid
- **expenses / expenseByCategory** - job expenses, already categorised
- **payables** - freelancer and vendor amounts on cost lines
- **jobProfitability** - quote total against actual cost, already computed per job

Two are new concepts with nothing behind them:

- **cashAccounts** - the company has no account model at all
- **forecast** - no projection logic exists

So Finance is roughly "five reporting screens over existing data, plus a cash-account model and a forecast rule". Scope those two before promising the section.

### Do not lose

`SopDeals.vue` (`/sop/deals`), the Vietnamese deal-classification SOP, has **no counterpart in the reference**. It is linked from the deal form and from Settings. Keep it.

## Rules when porting

- The target is Vue 3 + frappe-ui. Take tokens, layout and hierarchy from the reference; do not copy React component structure.
- `ink` and `surface` are reserved names in frappe-ui's Tailwind preset. Our tokens are `carbon` and `paper`. See the memory note and `README-phase1.md`.
- Body face is Be Vietnam Pro. Any new face must be checked against `Tết`, `Vị Xuân`, `Gốm Sứ`, `Người Giữ Lửa` before adoption - DM Sans failed exactly this.
- **No em dashes.** The reference carries 132 across 25 files, including the page titles. Strip them on the way in, and put the rule in the Lovable project prompt so it stops arriving.
- Every ported screen keeps its existing API calls and role gating. A restyle must not quietly change what the server is asked for.
- `./scripts/e2e.sh` must stay green. It currently passes 8/8.

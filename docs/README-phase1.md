# AuraOS front-end rebuild — Phase 1 (design system + shell + Home)

Drop-in files for the Frappe repo. Paths are relative to the repo root.

## Files

| File | Action |
| --- | --- |
| `frontend/index.html` | replace — adds Space Grotesk / DM Sans / JetBrains Mono `<link>`s |
| `frontend/tailwind.config.cjs` | replace — Attio Clean tokens (canvas, ink, hairline, accent, radii, dot grid) |
| `frontend/src/index.css` | replace — base layer + `.aura-canvas`, `.aura-card`, `.aura-card-founder`, `.aura-num`, `.aura-eyebrow` |
| `frontend/src/App.vue` | replace — now only auth/role probe + `<AppShell>` |
| `frontend/src/components/AppShell.vue` | new |
| `frontend/src/components/SidebarNav.vue` | new — Contacts split into Companies / People, founder group |
| `frontend/src/components/QuickActions.vue` | new — `/` and ⌘K focus |
| `frontend/src/components/BentoCard.vue` | new — `founder` inverts, `attention` outlines in ember |
| `frontend/src/components/DataTable.vue` | new — column defs + per-key cell slots |
| `frontend/src/components/StatusPill.vue` | new |
| `frontend/src/components/MoneyValue.vue` | new — wraps existing `utils/money` |
| `frontend/src/components/EmptyState.vue` | new |
| `frontend/src/pages/HomePage.vue` | replace — bento dashboard |

Existing `VndInput.vue`, `ComboInput.vue`, `utils/money.js`, `utils/frappeError.js`,
`data/milestones.js` are used as-is and unchanged.

## Backend

No Python changed. `HomePage.vue` calls exactly the same endpoints as before:
`auraos.api.overdue_milestones`, `auraos.api.silent_quote_deals`,
`auraos.api.job_expense_categories`, `auraos.api.log_job_expense`,
`auraos.api.get_margin_floor`, plus `Deal` / `Job` list resources with the same fields.

## Router — one change needed

`SidebarNav` links to `/contacts/companies` and `/contacts/people`. Until Phase 4 builds
those pages, add aliases in `frontend/src/router.js` so the links resolve:

```js
{ path: "/contacts", redirect: "/contacts/companies" },
{ path: "/contacts/companies", component: ContactsPage },
{ path: "/contacts/people", component: ContactsPage },
```

`ContactsPage` is replaced properly in Phase 4.

## Verify locally

```bash
docker compose up -d
cd frontend && npm run dev      # then open /aura
./scripts/e2e.sh                # Playwright suite
```

Nav-related e2e selectors: the top-level links keep their visible labels
(Home, Deals, Jobs, Paperwork, Settings). If a spec asserts a `Contacts` link,
it now needs `Companies` or `People`.

## Checks before Phase 2

1. Fonts load and headings render in Space Grotesk, numerals in JetBrains Mono.
2. Founder session sees the dark Margin card and the Founder nav group; a producer
   session sees neither, and the server still refuses the founder data.
3. Quick expense still logs against a job (float updates as before).
4. Phone width: sidebar hides, mobile nav row scrolls, expense card is usable one-handed.

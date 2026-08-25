# AuraOS front-end rebuild - Phase 1 (design system + shell + Home)

Drop-in files for the Frappe repo. Paths are relative to the repo root.

## Files

| File | Action |
| --- | --- |
| `frontend/index.html` | replace - adds Space Grotesk / Be Vietnam Pro / JetBrains Mono `<link>`s |
| `frontend/tailwind.config.cjs` | replace - Attio Clean tokens (canvas, paper, carbon, hairline, accent, radii, dot grid) |
| `frontend/src/index.css` | replace - base layer + `.aura-canvas`, `.aura-card`, `.aura-card-founder`, `.aura-num`, `.aura-eyebrow` |
| `frontend/src/App.vue` | replace - now only auth/role probe + `<AppShell>` |
| `frontend/src/components/AppShell.vue` | new |
| `frontend/src/components/SidebarNav.vue` | new - Contacts split into Companies / People, founder group |
| `frontend/src/components/QuickActions.vue` | new - `/` and ⌘K focus |
| `frontend/src/components/BentoCard.vue` | new - `founder` inverts, `attention` outlines in ember |
| `frontend/src/components/DataTable.vue` | new - column defs + per-key cell slots |
| `frontend/src/components/StatusPill.vue` | new |
| `frontend/src/components/MoneyValue.vue` | new - wraps existing `utils/money` |
| `frontend/src/components/EmptyState.vue` | new |
| `frontend/src/pages/HomePage.vue` | replace - bento dashboard |

Existing `VndInput.vue`, `ComboInput.vue`, `utils/money.js`, `utils/frappeError.js`,
`data/milestones.js` are used as-is and unchanged.

## Backend

No Python changed. `HomePage.vue` calls exactly the same endpoints as before:
`auraos.api.overdue_milestones`, `auraos.api.silent_quote_deals`,
`auraos.api.job_expense_categories`, `auraos.api.log_job_expense`,
`auraos.api.get_margin_floor`, plus `Deal` / `Job` list resources with the same fields.

## Router - one change needed

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

## Amendments applied on integration (2026-08-18)

Three things had to change before Phase 1 would build or render correctly.

1. **`ink` and `surface` are reserved names in frappe-ui's Tailwind preset**, which
   declares them as nested scales (`ink-gray-1`, `ink-amber-2`) in the `textColor`,
   `backgroundColor`, `fill`, `stroke` and `placeholder` namespaces. A namespace entry
   beats `theme.extend.colors`, so a flat `colors.ink` gives `bg-ink` but no bare
   `text-ink`, and the build fails on `@apply text-ink` while `bg-canvas` in the same
   rule succeeds. Their scale cannot be merged either: frappe-ui's `exports` map
   publishes only `./tailwind`. Our tokens were renamed **`ink` -> `carbon`** and
   **`surface` -> `paper`**. `accent.ink` is a sub-key and does not clash.
2. **DM Sans has no vietnamese subset** on Google Fonts - no U+1EA0-1EF9 - so every
   tone-marked vowel fell back mid-word in the body face, which carries nearly all of
   this app's text. Replaced with **Be Vietnam Pro**. Space Grotesk and JetBrains Mono
   were checked and do cover Vietnamese. Any future face must be verified against
   `Tết`, `Vị Xuân`, `Gốm Sứ`, `Người Giữ Lửa` before adoption.
3. **`scripts/e2e.sh` reported success on a failed suite.** Its `trap cleanup EXIT`
   returned the exit code of `compose down`, and its readiness gate polled
   `/api/method/ping`, which answers long before a server-rendered page does - so
   Playwright's global setup timed out navigating to `/login` with zero tests run, and
   the script still exited 0. The trap now re-raises the original status and the gate
   warms `/login` itself.

Fonts load from Google Fonts over the public internet. Staff on a disconnected office
network fall back to system faces; a self-hosted copy is worth considering, and is worth
requiring for the client-facing quote page (#80).

<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

# Building a screen

Read this before converting a screen from its fixture to real data. Everything
below is already decided. Follow it rather than inventing an alternative: the
screens are built in parallel and the only thing keeping them consistent is
that they all do these things the same way.

`src/routes/index.tsx` (the Home dashboard) is the worked example. It reads
three doctype lists, three whitelisted methods and one mutation, and it shows
loading, empty, permission-denied and network failure. Copy its shape.

## Rules

- No em dash anywhere, in code, comments, or UI copy. Use a short dash. Company
  rule, no exceptions.
- The frontend never computes money. If a total is not on the payload, it is a
  backend ticket, not a `reduce` on the screen. Summing a list you already
  fetched is fine; deriving margin, tax or commission is not.
- The server returns structured values and never formatted prose. Formatting is
  `src/lib/format.ts` and nowhere else.
- Never hide a field for permission reasons. The server already refuses it; the
  UI only decides what is worth showing.

## Reading data

`src/lib/queries.ts`. Three hooks, all backed by `@tanstack/react-query`.

```tsx
const jobs = useList<JobRow>({
  doctype: "Job",
  fields: ["name", "title", "stage", "quote_total"],
  filters: { stage: ["!=", "Complete"] },
  orderBy: "modified desc",
});

const owed = useMethod<OverduePayload>("auraos.api.overdue_milestones");
const cats = useMethod<string[]>("auraos.api.job_expense_categories", { job }, { enabled: !!job });

const deal = useDoc<Deal>("Deal", dealCode);
```

- The limit on `useList` defaults to every row you may read, not Frappe's own
  default of 20. Pass `limit` only when you want fewer.
- `args` are part of the cache key, so two screens asking the same question
  share one request. That is how the founder probe and the dashboard's margin
  card make one call between them.
- Declare the payload type in the screen file. Move it to a shared file only
  once a second screen needs the same shape.

## Writing data

```tsx
const log = useMethodMutation<Result, Args>("auraos.api.log_job_expense", {
  invalidate: [listsOf("Job Expense")],
  onSuccess: (result) => setConfirmation(`Logged ${vnd(result.amount)} ₫`),
});

log.mutate({ job, amount, category });
```

CSRF is attached to every request by `src/lib/frappe.ts`. There is nothing to
remember and nothing to pass. Use `mutate`, not `await mutateAsync` without a
catch: that is the one way to produce an unhandled rejection.

## Loading, empty and errors

`src/components/aura/states.tsx`. Do not write your own.

```tsx
<QueryState query={jobs} empty={{ title: "No jobs in production." }}>
  {(rows) => <JobsTable rows={rows} />}
</QueryState>

<QueryStates queries={[jobs, companies]} isEmpty={() => rows.length === 0} empty={{...}}>
  {() => <JobsTable rows={rows} />}
</QueryStates>

<Stat label="Pipeline" value={<Figure query={deals}><Money value={total} /></Figure>} />
```

`QueryState` resolves loading, error and empty; you only write the happy path.
A failure renders `ErrorState`, which already knows the difference between a
permission refusal, an expired session, a validation message and a dead
connection, and shows the server's own sentences when it sent any. Errors reach
you as `FrappeError` with `kind`, `status` and `messages` (see `lib/frappe.ts`).

## Formatting

`src/lib/format.ts`. `vnd`, `vndWithSign`, `parseVnd`, `formatDate`,
`formatDateTime`, `formatDateLong`, `overdueLabel`, `countLabel`.

Money is grouped whole đồng with the đồng sign, always in full digits. Never
abbreviate to "1,9 tỷ". In JSX use `<Money value={n} />` from
`components/aura/primitives.tsx`, which is the `vnd` formatter plus the sign.

## Session

```tsx
const session = useSession(); // userId, userName, initials, isFounder, isLoading, logout
```

`isFounder` comes from the server, not the browser: it is a successful read of
a founder-only endpoint. Never derive a role from an email or a cookie.

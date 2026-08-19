// The Home dashboard, on real data.
//
// This is the reference screen for the data layer: every other screen ticket
// can copy the shape of it. Nothing here computes money the server could have
// computed, nothing formats a number outside lib/format.ts, and every request
// goes through lib/queries.ts.

import { createFileRoute, Link } from "@tanstack/react-router";
import { AlertTriangle, ArrowUpRight, CheckCircle2, Clock } from "lucide-react";
import { useState } from "react";

import { AppShell } from "@/components/aura/AppShell";
import { useSession } from "@/components/aura/SessionProvider";
import { Card, Money, Pill, Stat, Td, Th } from "@/components/aura/primitives";
import { ErrorState, Figure, QueryState, QueryStates } from "@/components/aura/states";
import { countLabel, formatDateLong, overdueLabel, parseVnd, percent, vnd } from "@/lib/format";
import { listsOf, useList, useMethod, useMethodMutation } from "@/lib/queries";
import { FOUNDER_PROBE } from "@/lib/session";

/**
 * The founder's no-invoice tax exposure (issue #11).
 *
 * Pinned by tests/test_exposure.py and the seam tests in
 * auraos/auraos/doctype/job_expense/test_no_invoice_cover.py. Money is whole
 * integer đồng; `covered` is derived from whether an expense says it covers
 * the line, and is stored on no doctype anywhere.
 */
export type ExposureLine = {
  job: string | null;
  job_title: string | null;
  line: string | null;
  description: string | null;
  amount: number;
  covered: boolean;
  covering_expenses: string[];
  covering_count: number;
  covering_total: number;
  spent_on: string | null;
};

export type ExposureReport = {
  /** What was measured, printed rather than asserted by the screen. */
  basis: string;
  rate_pct: number;
  uncovered_total: number;
  tndn_exposure: number;
  uncovered_count: number;
  covered_total: number;
  covered_count: number;
  /** Only the uncovered ones: this is a list of invoices to chase. */
  lines: ExposureLine[];
};

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Home - AuraOS production ops" },
      {
        name: "description",
        content:
          "Pipeline, jobs in production, overdue payments and quiet quotes on one producer desk.",
      },
      { property: "og:title", content: "Home - AuraOS production ops" },
      {
        property: "og:description",
        content: "Pipeline, jobs in production, overdue payments and quiet quotes at a glance.",
      },
    ],
  }),
  component: HomePage,
});

// -- what the server sends. Declared beside the screen that reads it; a shape
// -- only moves into a shared file once a second screen needs the same one.

type DealRow = {
  name: string;
  title: string | null;
  stage: string;
  estimated_budget: number | null;
};

type JobRow = {
  name: string;
  title: string | null;
  stage: string;
  quote_total: number | null;
  company: string | null;
};

type CompanyRow = { name: string; company_name: string | null };

type OverdueMilestone = {
  name: string;
  job: string;
  job_title: string | null;
  title: string | null;
  amount: number | null;
  days_overdue: number;
};

type OverduePayload = { payment_terms_days: number; milestones: OverdueMilestone[] };

type SilentDeal = { name: string; title: string | null; quote_sent_on: string | null };

type SilentPayload = { silence_days: number; deals: SilentDeal[] };

type ExpenseResult = { name: string; amount: number; category: string | null };

/**
 * The weighted pipeline projection (#102), narrowed to what this tile reads.
 *
 * Note the field names, which are the point rather than a detail. The tile
 * beside this one adds up `estimated_budget` and calls itself Pipeline: that is
 * the unweighted figure, every open deal at face value. This one is every open
 * deal multiplied by the probability of the stage it sits at - an estimate
 * times a guess - and the server refuses to call it a total, a balance or an
 * income so that no screen can print it as money the studio has. The label here
 * is a courtesy; `weighted_projection` is the guarantee.
 */
type ForecastTile = {
  basis: string;
  weighted_projection: number;
  open_pipeline: number;
  deal_count: number;
};

// The eight canonical job stages (spec #81). Anything else reads neutral.
const stageTone: Record<string, string> = {
  Production: "ink",
  "Awaiting payment": "ember",
  Complete: "positive",
};

const RESOLVED_DEAL_STAGES = new Set(["Won", "Lost"]);

function greeting(hour = new Date().getHours()): string {
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function sum(values: Array<number | null | undefined>): number {
  return values.reduce<number>((total, value) => total + (value ?? 0), 0);
}

/**
 * The uncovered lines worth chasing first: biggest cash, at most five. A sort
 * and a slice of the server's own rows - nothing on the tile is added up here.
 */
function biggestUncovered(lines: ExposureLine[]): ExposureLine[] {
  return [...lines].sort((a, b) => b.amount - a.amount).slice(0, 5);
}

function HomePage() {
  const session = useSession();

  // -- the four reads this screen is built from --
  const deals = useList<DealRow>({
    doctype: "Deal",
    fields: ["name", "title", "stage", "estimated_budget"],
    orderBy: "modified desc",
  });

  const jobs = useList<JobRow>({
    doctype: "Job",
    fields: ["name", "title", "stage", "quote_total", "company"],
    orderBy: "modified desc",
  });

  const companies = useList<CompanyRow>({
    doctype: "Party Company",
    fields: ["name", "company_name"],
  });

  const overdue = useMethod<OverduePayload>("auraos.api.overdue_milestones");
  const silent = useMethod<SilentPayload>("auraos.api.silent_quote_deals");

  // Same query key as the founder probe in SessionProvider, so this is a cache
  // read rather than a second request.
  const marginFloor = useMethod<number>(FOUNDER_PROBE, undefined, {
    retry: false,
    staleTime: Number.POSITIVE_INFINITY,
  });

  // Founder-only, and asked only when the session is one: the server refuses a
  // producer outright, so firing this for them would be a guaranteed 403 on
  // every dashboard load. The gate is the server's; this only avoids the noise.
  const exposure = useMethod<ExposureReport>("auraos.api.no_invoice_exposure", undefined, {
    enabled: session.isFounder,
    retry: false,
  });

  // Founder-only for the same reason, and refused by the server rather than
  // hidden by the browser: the projection is the founder's own probability
  // dials multiplied by deal values a producer already knows, so handing it
  // over would hand the dials back by division.
  const forecast = useMethod<ForecastTile>(
    "auraos.api.weighted_pipeline_forecast",
    { months: 6 },
    { enabled: session.isFounder, retry: false },
  );

  const openDeals = (deals.data ?? []).filter((row) => !RESOLVED_DEAL_STAGES.has(row.stage));
  const openJobs = (jobs.data ?? []).filter((row) => row.stage !== "Complete");
  const milestones = overdue.data?.milestones ?? [];
  const silentDeals = silent.data?.deals ?? [];

  const companyName = new Map(
    (companies.data ?? []).map((c) => [c.name, c.company_name ?? c.name]),
  );

  const attention = [
    ...milestones.map((row) => ({
      key: `overdue-${row.name}`,
      kind: "Overdue milestone",
      what: row.job_title || row.job,
      detail: [row.title, overdueLabel(row.days_overdue)].filter(Boolean).join(" · "),
      amount: row.amount ?? 0,
      job: row.job,
    })),
    ...silentDeals.map((row) => ({
      key: `silent-${row.name}`,
      kind: "Silent quote",
      what: row.title || row.name,
      detail: `quote sent, no reply for ${countLabel(silent.data?.silence_days ?? 0, "day")}`,
      amount: 0,
      job: null as string | null,
    })),
  ];

  const meta = [
    formatDateLong(new Date()),
    deals.isSuccess ? countLabel(openDeals.length, "open deal") : null,
    jobs.isSuccess ? `${countLabel(openJobs.length, "job")} in production` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  const firstName = session.userName.trim().split(/\s+/).slice(-1)[0] || session.userName;

  return (
    <AppShell
      title={`${greeting()}, ${firstName}`}
      meta={meta}
      actions={
        <Link
          to="/deals"
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          Open the pipeline <ArrowUpRight className="size-3.5" />
        </Link>
      }
    >
      <div className="space-y-5">
        <div
          className={`grid gap-3 sm:grid-cols-2 ${
            session.isFounder ? "xl:grid-cols-5" : "xl:grid-cols-4"
          }`}
        >
          <Stat
            label="Pipeline · open deals"
            value={
              <Figure query={deals}>
                <Money value={sum(openDeals.map((d) => d.estimated_budget))} />
              </Figure>
            }
            sub={
              deals.isSuccess
                ? `${countLabel(openDeals.length, "deal")} at estimated budget, unweighted`
                : undefined
            }
          />
          {/* The weighted figure, named apart from the unweighted one above it
              in the payload and not only in this label. Founder-only, and the
              card is absent for a producer because the server refuses the read.
              See routes/finance.forecast.tsx for the whole screen. */}
          {session.isFounder ? (
            <Stat
              label="Weighted projection · not cash"
              value={
                <Figure query={forecast}>
                  <Money value={forecast.data?.weighted_projection ?? 0} />
                </Figure>
              }
              // Names its own base on purpose. The tile to the left adds up
              // estimated budgets; this one weights the better number where
              // there is one - a sent quote beats a budget - so the two start
              // from different figures and a founder is owed that in writing
              // rather than left to wonder at the gap.
              sub={
                forecast.isSuccess
                  ? `Next 6 months · weighted from ${vnd(forecast.data?.open_pipeline ?? 0)} ₫ of quoted or budgeted value`
                  : undefined
              }
            />
          ) : null}
          <Stat
            label="In production"
            value={
              <Figure query={jobs}>
                <Money value={sum(openJobs.map((j) => j.quote_total))} />
              </Figure>
            }
            sub={jobs.isSuccess ? countLabel(openJobs.length, "job") : undefined}
          />
          <Stat
            label="Overdue payments"
            alert={milestones.length > 0}
            value={
              <Figure query={overdue}>
                <Money value={sum(milestones.map((m) => m.amount))} />
              </Figure>
            }
            sub={overdue.isSuccess ? countLabel(milestones.length, "milestone") : undefined}
          />
          <Stat
            label="Quotes gone quiet"
            alert={silentDeals.length > 0}
            value={
              <Figure query={silent} width="3rem">
                <span className="num">{silentDeals.length}</span>
              </Figure>
            }
            sub={
              silent.isSuccess
                ? `past ${countLabel(silent.data?.silence_days ?? 0, "day")}`
                : undefined
            }
          />
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <Card
            className="lg:col-span-2"
            title="Needs attention"
            subtitle="Money that has stopped moving, worst first"
          >
            <QueryStates
              queries={[overdue, silent]}
              isEmpty={() => attention.length === 0}
              empty={{
                title: "Nothing chasing you.",
                detail: "No overdue milestones, no silent quotes.",
                icon: <CheckCircle2 className="size-6" strokeWidth={1.5} />,
              }}
            >
              {() => (
                <ul className="divide-y divide-border">
                  {attention.map((item) => (
                    <li key={item.key} className="flex flex-wrap items-center gap-3 px-4 py-3">
                      <AlertTriangle className="size-4 shrink-0 text-ember" strokeWidth={1.75} />
                      <div className="min-w-0 flex-1">
                        {item.job ? (
                          <Link
                            to="/jobs/$jobId"
                            params={{ jobId: item.job }}
                            className="truncate text-sm font-medium hover:text-ember"
                          >
                            {item.what}
                          </Link>
                        ) : (
                          <Link
                            to="/deals"
                            className="truncate text-sm font-medium hover:text-ember"
                          >
                            {item.what}
                          </Link>
                        )}
                        <div className="mt-0.5 text-xs text-muted-foreground">
                          {item.kind} · <span className="text-ember">{item.detail}</span>
                        </div>
                      </div>
                      {item.amount ? (
                        <Money value={item.amount} className="text-sm font-semibold" />
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </QueryStates>
          </Card>

          {/* Founder only. The card is absent for a producer because the server
              refuses the read, not because the browser decided to hide it. */}
          {session.isFounder ? (
            <Card tone="ink" title="Margin floor" subtitle="Founder only">
              <div className="space-y-3 p-4">
                <div className="flex items-baseline gap-2">
                  <span className="num text-3xl font-semibold">
                    <Figure query={marginFloor} width="4rem">
                      {marginFloor.data ?? 0}%
                    </Figure>
                  </span>
                  <span className="text-xs text-primary-foreground/50">of quote value</span>
                </div>
                <p className="text-xs leading-relaxed text-primary-foreground/60">
                  Quotes below the floor are blocked at publish, not at send. The breakdown shows
                  the cause line by line.
                </p>
                <Link
                  to="/settings"
                  className="block text-xs text-primary-foreground/70 hover:text-primary-foreground"
                >
                  Adjust the floor and the defaults
                </Link>
              </div>
            </Card>
          ) : null}

          {/* Founder only, same reason as the card above: the server refuses
              the read. A producer records that the replacement invoice
              arrived; what it costs the company in tax is not theirs. */}
          {session.isFounder ? (
            <Card title="No-invoice exposure" subtitle="Founder only">
              <div className="space-y-3 p-4">
                <div className="flex items-baseline gap-2">
                  <span className="num text-3xl font-semibold text-ember">
                    <Figure query={exposure} width="7rem">
                      <Money value={exposure.data?.tndn_exposure ?? 0} />
                    </Figure>
                  </span>
                  <span className="text-xs text-muted-foreground">
                    TNDN at {percent(exposure.data?.rate_pct)}
                  </span>
                </div>
                <p className="text-xs leading-relaxed text-muted-foreground">
                  On{" "}
                  <Money
                    value={exposure.data?.uncovered_total ?? 0}
                    className="font-medium text-foreground"
                  />{" "}
                  of cost handed over with no invoice and no replacement on file, across{" "}
                  {countLabel(exposure.data?.uncovered_count ?? 0, "line")}. Carried until the paper
                  arrives, not billed to a month.
                </p>
                <QueryState
                  query={exposure}
                  loadingRows={2}
                  isEmpty={() => (exposure.data?.lines.length ?? 0) === 0}
                  empty={{
                    title: "Every no-invoice cost has its replacement.",
                    detail: "Nothing here is exposed.",
                    icon: <CheckCircle2 className="size-6" strokeWidth={1.5} />,
                  }}
                >
                  {(report) => (
                    <ul className="space-y-1.5 border-t border-border pt-3">
                      {biggestUncovered(report.lines).map((row) => (
                        <li key={row.line} className="flex items-baseline gap-2 text-xs">
                          <span className="truncate">{row.description || "Untitled line"}</span>
                          <Link
                            to="/jobs/$jobId"
                            params={{ jobId: row.job ?? "" }}
                            className="label-caps shrink-0 hover:text-foreground"
                          >
                            {row.job_title || row.job}
                          </Link>
                          <Money value={row.amount} className="ml-auto shrink-0" />
                        </li>
                      ))}
                    </ul>
                  )}
                </QueryState>
              </div>
            </Card>
          ) : null}
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <Card
            className="lg:col-span-2"
            title="Jobs in production"
            subtitle={jobs.isSuccess ? countLabel(openJobs.length, "open job") : undefined}
            action={
              <Link
                to="/jobs"
                className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-ember"
              >
                All jobs <ArrowUpRight className="size-3.5" />
              </Link>
            }
          >
            <QueryStates
              queries={[jobs, companies]}
              isEmpty={() => openJobs.length === 0}
              empty={{
                title: "No jobs in production.",
                detail: "A won deal becomes a job, and it lands here.",
                icon: <Clock className="size-6" strokeWidth={1.5} />,
              }}
            >
              {() => (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="border-b border-border">
                      <tr>
                        <Th>Job</Th>
                        <Th>Client</Th>
                        <Th className="text-right">Quoted</Th>
                        <Th>Stage</Th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {openJobs.map((job) => (
                        <tr key={job.name} className="hover:bg-secondary/50">
                          <Td className="font-medium">
                            <Link to="/jobs/$jobId" params={{ jobId: job.name }}>
                              {job.title || job.name}
                            </Link>
                            <div className="num text-[11px] text-muted-foreground">{job.name}</div>
                          </Td>
                          <Td className="text-muted-foreground">
                            {job.company ? (companyName.get(job.company) ?? job.company) : "-"}
                          </Td>
                          <Td className="text-right">
                            <Money value={job.quote_total ?? 0} />
                          </Td>
                          <Td>
                            <Pill tone={stageTone[job.stage] ?? "neutral"}>{job.stage}</Pill>
                          </Td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </QueryStates>
          </Card>

          <QuickExpense jobs={openJobs} jobsQuery={jobs} />
        </div>
      </div>
    </AppShell>
  );
}

/**
 * The one mutation on this screen, and the proof that a POST from a signed-in
 * user passes CSRF. It is also the pattern for every write in the app: mutate,
 * never await mutateAsync, and read the failure off the mutation.
 */
function QuickExpense({
  jobs,
  jobsQuery,
}: {
  jobs: JobRow[];
  jobsQuery: ReturnType<typeof useList<JobRow>>;
}) {
  const [job, setJob] = useState("");
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("");
  const [note, setNote] = useState("");
  const [logged, setLogged] = useState("");

  // Categories belong to the job, so the request waits for one to be picked.
  const categories = useMethod<string[]>(
    "auraos.api.job_expense_categories",
    { job },
    { enabled: Boolean(job) },
  );

  const logExpense = useMethodMutation<ExpenseResult, Record<string, unknown>>(
    "auraos.api.log_job_expense",
    {
      invalidate: [listsOf("Job Expense")],
      onSuccess: (result) => {
        setLogged(`Logged ${vnd(result.amount)} ₫ on ${job}.`);
        setAmount("");
        setNote("");
      },
    },
  );

  const value = parseVnd(amount);

  return (
    <Card title="Quick expense" subtitle="Log a cost against a job">
      <QueryState
        query={jobsQuery}
        isEmpty={() => jobs.length === 0}
        empty={{ title: "No open job to spend on." }}
      >
        {() => (
          <form
            className="space-y-3 p-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (!job || !value) return;
              setLogged("");
              logExpense.mutate({
                job,
                amount: value,
                category: category || null,
                description: note || null,
              });
            }}
          >
            <label className="block">
              <span className="label-caps">Job</span>
              <select
                value={job}
                onChange={(event) => {
                  setJob(event.target.value);
                  setCategory("");
                  setLogged("");
                }}
                className="mt-1 w-full rounded-lg border border-border bg-background px-2.5 py-2 text-sm"
              >
                <option value="">Which job...</option>
                {jobs.map((row) => (
                  <option key={row.name} value={row.name}>
                    {row.title || row.name} · {row.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="label-caps">Amount (VND)</span>
              <input
                inputMode="numeric"
                value={value ? vnd(value) : ""}
                onChange={(event) => setAmount(event.target.value)}
                placeholder="0"
                className="num mt-1 w-full rounded-lg border border-border bg-background px-2.5 py-2 text-right text-sm"
              />
            </label>

            <label className="block">
              <span className="label-caps">Category</span>
              <select
                value={category}
                disabled={!job}
                onChange={(event) => setCategory(event.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-background px-2.5 py-2 text-sm disabled:text-muted-foreground"
              >
                <option value="">Uncategorised</option>
                {(categories.data ?? []).map((title) => (
                  <option key={title} value={title}>
                    {title}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="label-caps">Note (optional)</span>
              <input
                value={note}
                onChange={(event) => setNote(event.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-background px-2.5 py-2 text-sm"
              />
            </label>

            <button
              type="submit"
              disabled={!job || !value || logExpense.isPending}
              className="w-full rounded-lg bg-ember px-3 py-2 text-sm font-medium text-ember-foreground transition-opacity hover:opacity-90 disabled:opacity-40"
            >
              {logExpense.isPending ? "Logging..." : value ? `Log ${vnd(value)} ₫` : "Log expense"}
            </button>

            {logged ? <p className="text-xs text-positive">{logged}</p> : null}
            {logExpense.isError ? (
              <ErrorState error={logExpense.error} className="px-0 py-2" />
            ) : null}
          </form>
        )}
      </QueryState>
    </Card>
  );
}

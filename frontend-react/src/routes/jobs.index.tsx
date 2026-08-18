// The Jobs board, on real data.
//
// Every job in flight across the eight production stages, with the money
// clients still owe at the top of the page. The screen this replaces is
// frontend/src/pages/JobsPage.vue, running in production: the doctype, the
// field list, the stage names and the save call are the same, because the
// backend is unchanged.
//
// There is deliberately no "New job" control. A job exists because a deal was
// won, never because a button was pressed.

import { createFileRoute, Link } from "@tanstack/react-router";
import { AlertCircle, AlertTriangle, Briefcase, Clock, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/aura/AppShell";
import { Card, Money, Pill } from "@/components/aura/primitives";
import { ErrorState, Loading, QueryStates } from "@/components/aura/states";
import { countLabel, overdueLabel } from "@/lib/format";
import { listsOf, resultOf, useList, useMethod, useMethodMutation } from "@/lib/queries";

export const Route = createFileRoute("/jobs/")({
  head: () => ({
    meta: [
      { title: "Jobs in production - AuraOS" },
      {
        name: "description",
        content:
          "Every open job across the eight production stages, with quoted value and the money clients still owe.",
      },
      { property: "og:title", content: "Jobs in production - AuraOS" },
      {
        property: "og:description",
        content: "Stage flow, quoted value, revision state and uncollected milestones per job.",
      },
    ],
  }),
  component: JobsPage,
});

// -- what the server sends --

type JobRow = {
  name: string;
  title: string | null;
  stage: string;
  company: string | null;
  job_owner: string | null;
  files_location: string | null;
  revision_rounds: number | null;
  change_order_due: number | null;
  quote_total: number | null;
  modified: string | null;
};

type CompanyRow = { name: string; company_name: string | null };

type OverdueMilestone = {
  name: string;
  job: string;
  job_title: string | null;
  title: string | null;
  amount: number | null;
  status: string | null;
  days_overdue: number;
};

type OverduePayload = { payment_terms_days: number; milestones: OverdueMilestone[] };

/**
 * The agreed production flow, in board order. Mirrors
 * auraos/auraos/doctype/job/job.py STAGES and the Job doctype's own Select
 * options; the server is the authority and refuses anything else.
 */
const STAGES = [
  "Pre-production",
  "Production",
  "Post-production",
  "Client review",
  "Delivery",
  "Client sign-off",
  "Awaiting payment",
  "Complete",
];

const JOB_FIELDS = [
  "name",
  "title",
  "stage",
  "company",
  "job_owner",
  "files_location",
  "revision_rounds",
  "change_order_due",
  "quote_total",
  "modified",
];

/** The one column the board wants the reader's eye on. */
const FOCUS_STAGE = "Awaiting payment";

function sum(values: Array<number | null | undefined>): number {
  return values.reduce<number>((total, value) => total + (value ?? 0), 0);
}

/** A typed search only becomes a request once the typing stops. */
function useSettled(value: string, delay = 250): string {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return settled;
}

function JobsPage() {
  const [search, setSearch] = useState("");
  const needle = useSettled(search.trim());

  const companies = useList<CompanyRow>({
    doctype: "Party Company",
    fields: ["name", "company_name"],
  });

  const companyName = useMemo(
    () => new Map((companies.data ?? []).map((row) => [row.name, row.company_name ?? row.name])),
    [companies.data],
  );

  // Searching a client means searching the company's display name, which lives
  // on Party Company and not on the Job. The codes that match go into the
  // server's own OR group, so the filtering still happens in the database and
  // the board is never a filtered view of a truncated list.
  const orFilters = useMemo<unknown[][] | undefined>(() => {
    if (!needle) return undefined;
    const like = `%${needle.replace(/[\\%_]/g, "\\$&")}%`;
    const clauses: unknown[][] = [
      ["title", "like", like],
      ["name", "like", like],
    ];
    const matches = [...companyName.entries()]
      .filter(([code, label]) => `${label} ${code}`.toLowerCase().includes(needle.toLowerCase()))
      .map(([code]) => code);
    if (matches.length) clauses.push(["company", "in", matches]);
    return clauses;
  }, [needle, companyName]);

  const jobs = useList<JobRow>({
    doctype: "Job",
    fields: JOB_FIELDS,
    orderBy: "modified desc",
    ...(orFilters ? { orFilters } : {}),
  });

  // Overdue money. The server decides what counts as late, so this board and
  // the dashboard cannot disagree about it.
  const overdue = useMethod<OverduePayload>("auraos.api.overdue_milestones");

  // -- moving a job between stages --
  //
  // The card moves before the server answers, because a drop that waits out a
  // round trip reads as lag. `moved` holds the optimistic stage until the
  // refetched list says the same thing, so there is no flash back to the old
  // column, and a refusal puts the card back where it came from.
  const [moved, setMoved] = useState<Record<string, string>>({});
  const [dragged, setDragged] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState<string | null>(null);

  const setStage = useMethodMutation<
    unknown,
    { doctype: string; name: string; fieldname: Record<string, string> }
  >("frappe.client.set_value", {
    invalidate: [listsOf("Job"), resultOf("auraos.api.overdue_milestones")],
  });

  useEffect(() => {
    const rows = jobs.data;
    if (!rows) return;
    setMoved((prev) => {
      const next = { ...prev };
      let changed = false;
      for (const row of rows) {
        if (next[row.name] === row.stage) {
          delete next[row.name];
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [jobs.data]);

  const rows = useMemo(
    () =>
      (jobs.data ?? []).map((row) => {
        const pending = moved[row.name];
        return pending ? { ...row, stage: pending } : row;
      }),
    [jobs.data, moved],
  );

  const byStage = useMemo(() => {
    const map = new Map<string, JobRow[]>();
    for (const row of rows) {
      const bucket = map.get(row.stage);
      if (bucket) bucket.push(row);
      else map.set(row.stage, [row]);
    }
    return map;
  }, [rows]);

  const boardTotal = sum(rows.map((row) => row.quote_total));

  function move(job: JobRow, stage: string) {
    if (job.stage === stage) return;
    const from = job.stage;
    setMoved((prev) => ({ ...prev, [job.name]: stage }));
    setStage.mutate(
      { doctype: "Job", name: job.name, fieldname: { stage } },
      {
        onError: () => {
          setMoved((prev) => ({ ...prev, [job.name]: from }));
        },
      },
    );
  }

  return (
    <AppShell
      title="Jobs"
      meta={
        <>
          <span>
            {jobs.isSuccess ? countLabel(rows.length, "job") : "Loading"}
            {boardTotal ? (
              <>
                {" · "}
                <Money value={boardTotal} className="text-xs" /> in production
              </>
            ) : null}
          </span>
          <div className="mt-0.5">
            Won deals in production - new jobs are created from the deal board.
          </div>
        </>
      }
      actions={
        <div className="relative">
          <Search
            className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground"
            strokeWidth={1.75}
            aria-hidden="true"
          />
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search jobs"
            aria-label="Search jobs"
            className="w-56 rounded-lg border border-border bg-card py-2 pr-3 pl-8 text-sm placeholder:text-muted-foreground focus:border-border-strong focus:outline-none"
          />
        </div>
      }
    >
      <div className="space-y-5">
        <OverdueStrip query={overdue} />

        <Card
          title="Production board"
          subtitle="Drag a card to move the job. Both roles may move one."
        >
          <QueryStates
            queries={[jobs, companies]}
            isEmpty={() => rows.length === 0}
            empty={
              needle
                ? {
                    title: "No job matches that search.",
                    detail: "Search runs on the server across job title, code and client.",
                    icon: <Search className="size-6" strokeWidth={1.5} />,
                  }
                : {
                    title: "No jobs yet - mark a deal Won on the deal board to create one.",
                    icon: <Briefcase className="size-6" strokeWidth={1.5} />,
                  }
            }
          >
            {() => (
              <div className="overflow-x-auto p-3">
                <div className="flex min-w-max items-stretch gap-3">
                  {STAGES.map((stage) => {
                    const items = byStage.get(stage) ?? [];
                    const focus = stage === FOCUS_STAGE;
                    const over = dragOver === stage;
                    return (
                      <div
                        key={stage}
                        onDragOver={(event) => {
                          event.preventDefault();
                          setDragOver(stage);
                        }}
                        onDragLeave={(event) => {
                          if (event.currentTarget.contains(event.relatedTarget as Node | null)) {
                            return;
                          }
                          setDragOver((current) => (current === stage ? null : current));
                        }}
                        onDrop={(event) => {
                          event.preventDefault();
                          setDragOver(null);
                          const job = rows.find((row) => row.name === dragged);
                          setDragged(null);
                          if (job) move(job, stage);
                        }}
                        className={`flex w-[272px] shrink-0 flex-col rounded-xl border transition-colors ${
                          over
                            ? "border-ember bg-ember-soft"
                            : focus
                              ? "border-ember bg-card"
                              : "border-border bg-card"
                        }`}
                      >
                        <div className="flex items-baseline gap-2 border-b border-border px-3 py-2.5">
                          <span className="label-caps truncate">{stage}</span>
                          <span className="num shrink-0 rounded-md bg-secondary px-1.5 py-0.5 text-[11px] text-muted-foreground">
                            {items.length}
                          </span>
                          {items.length ? (
                            <Money
                              value={sum(items.map((row) => row.quote_total))}
                              className="ml-auto shrink-0 text-[11px] text-muted-foreground"
                            />
                          ) : null}
                        </div>

                        <div className="dot-grid flex min-h-24 flex-1 flex-col gap-2 rounded-b-xl p-2">
                          {items.length === 0 ? (
                            <div className="rounded-lg border border-dashed border-border px-3 py-6 text-center text-[11px] text-muted-foreground">
                              Nothing here
                            </div>
                          ) : (
                            items.map((job) => (
                              <JobCard
                                key={job.name}
                                job={job}
                                client={
                                  job.company ? (companyName.get(job.company) ?? job.company) : null
                                }
                                dragging={dragged === job.name}
                                onDragStart={() => setDragged(job.name)}
                                onDragEnd={() => {
                                  setDragged(null);
                                  setDragOver(null);
                                }}
                              />
                            ))
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </QueryStates>

          {setStage.isError ? (
            <ErrorState error={setStage.error} className="border-t border-border px-4 py-4" />
          ) : null}
        </Card>
      </div>
    </AppShell>
  );
}

/**
 * The money strip: what clients owe past the company's payment terms, and the
 * loudest thing on the page. The figure and the count are the server's, from
 * auraos.api.overdue_milestones, so nothing here is a browser's opinion of
 * what counts as late.
 */
function OverdueStrip({ query }: { query: ReturnType<typeof useMethod<OverduePayload>> }) {
  if (query.isPending) return <Loading rows={2} className="rounded-xl border border-border p-4" />;

  if (query.isError) {
    return (
      <Card>
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      </Card>
    );
  }

  const milestones = query.data?.milestones ?? [];
  if (milestones.length === 0) return null;

  const terms = query.data?.payment_terms_days ?? 0;

  return (
    <section className="overflow-hidden rounded-xl border border-ember bg-card">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-ember/30 bg-ember-soft px-4 py-3">
        <AlertCircle className="size-5 shrink-0 text-ember" strokeWidth={1.75} aria-hidden="true" />
        <div className="min-w-0">
          <div className="label-caps text-ember">Uncollected</div>
          <Money
            value={sum(milestones.map((row) => row.amount))}
            className="mt-0.5 block text-xl font-semibold text-ember"
          />
        </div>
        <p className="text-xs text-ember sm:ml-auto sm:text-right">
          {countLabel(milestones.length, "milestone")} past the {terms}-day payment terms
        </p>
      </div>

      <ul className="divide-y divide-border px-4">
        {milestones.map((row) => (
          <li key={row.name} className="flex flex-wrap items-baseline gap-x-2 gap-y-1 py-2">
            <Link
              to="/jobs/$jobId"
              params={{ jobId: row.job }}
              className="min-w-0 truncate text-sm font-medium hover:text-ember"
            >
              {row.job_title || row.job}
            </Link>
            {row.title ? (
              <span className="min-w-0 truncate text-xs text-muted-foreground">{row.title}</span>
            ) : null}
            <Pill tone="ember" className="shrink-0">
              <Clock className="size-3" strokeWidth={1.75} aria-hidden="true" />
              {overdueLabel(row.days_overdue)}
            </Pill>
            {row.status ? (
              <span className="shrink-0 text-xs text-muted-foreground">{row.status}</span>
            ) : null}
            <Money value={row.amount ?? 0} className="ml-auto shrink-0 text-sm font-medium" />
          </li>
        ))}
      </ul>
    </section>
  );
}

/**
 * One job on the board. Everything on the card is a stored field: the quoted
 * total, the revision count and whether those rounds have become a chargeable
 * change order, and whether anybody has recorded where the files live.
 */
function JobCard({
  job,
  client,
  dragging,
  onDragStart,
  onDragEnd,
}: {
  job: JobRow;
  client: string | null;
  dragging: boolean;
  onDragStart: () => void;
  onDragEnd: () => void;
}) {
  const rounds = job.revision_rounds ?? 0;
  const flags = Boolean(job.change_order_due) || rounds > 0 || !job.files_location;

  return (
    <Link
      to="/jobs/$jobId"
      params={{ jobId: job.name }}
      draggable
      onDragStart={(event) => {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", job.name);
        onDragStart();
      }}
      onDragEnd={onDragEnd}
      className={`block cursor-grab rounded-lg border border-border bg-card p-3 transition-shadow hover:border-border-strong hover:shadow-sm ${
        dragging ? "opacity-50" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="min-w-0 flex-1 truncate text-sm leading-snug font-medium">
          {job.title || job.name}
        </span>
        <span className="num shrink-0 text-[11px] text-muted-foreground">{job.name}</span>
      </div>

      {client ? <div className="mt-1 truncate text-xs text-muted-foreground">{client}</div> : null}

      {job.quote_total ? (
        <Money value={job.quote_total} className="mt-2.5 block text-sm font-semibold" />
      ) : null}

      {flags ? (
        <div className="mt-2 flex flex-wrap items-center gap-1 border-t border-border pt-2">
          {job.change_order_due ? (
            <span title="Revision rounds past the included ones - chargeable">
              <Pill tone="ember">
                <AlertTriangle className="size-3" strokeWidth={1.75} aria-hidden="true" />
                Change order · {countLabel(rounds, "round")}
              </Pill>
            </span>
          ) : rounds > 0 ? (
            <Pill>{countLabel(rounds, "revision")}</Pill>
          ) : null}
          {!job.files_location ? (
            <span title="No shared folder recorded yet">
              <Pill>no files location</Pill>
            </span>
          ) : null}
        </div>
      ) : null}
    </Link>
  );
}

// One job, end to end, on real data.
//
// The producer's working screen: where the job has got to, what the client has
// paid against what they were quoted, what has gone out to the crew, and what
// has been printed off it. It replaces frontend/src/pages/JobPage.vue and its
// three panels, running in production - the same doctype, the same endpoints
// and the same words, because the backend is unchanged.
//
// The four tabs are shown and hidden rather than mounted and unmounted, so a
// half-typed milestone plan is still there when the reader comes back from the
// paperwork tab.
//
// **Tasks is the same panel a crew member reads** (#41, ported at #165). The
// difference is not the component, it is what the server says the session may
// do: `job_tasks` answers `can_plan`, and a producer gets the planning surface
// while an editor gets their own card and nothing else. Nothing about the plan
// is money, which is what makes one component safe for both.

import { createFileRoute, Link } from "@tanstack/react-router";
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  DollarSign,
  FileText,
  Film,
  ListChecks,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import { AppShell } from "@/components/aura/AppShell";
import { JobMilestonesPanel } from "@/components/aura/JobMilestonesPanel";
import { JobTasks } from "@/components/aura/JobTasks";
import { JobMoneyPanel } from "@/components/aura/JobMoneyPanel";
import { JobPaperworkPanel } from "@/components/aura/JobPaperworkPanel";
import { Card, Money, Pill, Stat, Td, Th } from "@/components/aura/primitives";
import { ErrorState, Figure, QueryState } from "@/components/aura/states";
import {
  INCLUDED_REVISION_ROUNDS,
  LAST_REDOABLE_STAGE,
  PAID,
  REDO_STAGE,
  STAGES,
  type JobDoc,
  type MilestonesPayload,
  type MoneyPayload,
  type SetValueArgs,
  docKey,
} from "@/components/aura/job";
import { countLabel, formatDateTime, vnd } from "@/lib/format";
import { listsOf, resultOf, useDoc, useList, useMethod, useMethodMutation } from "@/lib/queries";

export const Route = createFileRoute("/jobs/$jobId")({
  head: () => ({
    meta: [
      { title: "Job detail - production, money and paperwork | AuraOS" },
      {
        name: "description",
        content:
          "One job: production stage, quoted against collected and spent, payment milestones, crew float and paperwork.",
      },
      { property: "og:title", content: "Job detail - production, money and paperwork" },
      {
        property: "og:description",
        content: "Stage flow, quoted against collected, milestones, crew float and revisions.",
      },
    ],
  }),
  component: JobDetail,
});

type CompanyRow = { name: string; company_name: string | null };

type RevisionResult = { round: number; stage: string; redo: boolean };

const TABS = ["Production", "Tasks", "Money", "Paperwork"] as const;
type Tab = (typeof TABS)[number];

const TAB_ICONS = {
  Production: Film,
  Tasks: ListChecks,
  Money: DollarSign,
  Paperwork: FileText,
};

function JobDetail() {
  const { jobId } = Route.useParams();

  const job = useDoc<JobDoc>("Job", jobId);
  // Both of these are read by a panel as well, with the same arguments, so the
  // page and the panel share one request rather than asking twice.
  const milestones = useMethod<MilestonesPayload>("auraos.api.job_milestones", { job: jobId });
  const money = useMethod<MoneyPayload>("auraos.api.job_money", { job: jobId });
  // The same query the jobs board runs, so this is a cache read on the way in.
  const companies = useList<CompanyRow>({
    doctype: "Party Company",
    fields: ["name", "company_name"],
  });

  const [tab, setTab] = useState<Tab>("Production");

  // The chip moves before the server answers, because a stage change that waits
  // out a round trip reads as lag. A refusal puts it back.
  const [movedTo, setMovedTo] = useState<string | null>(null);

  const setStage = useMethodMutation<unknown, SetValueArgs>("frappe.client.set_value", {
    invalidate: [
      docKey("Job", jobId),
      resultOf("auraos.api.job_milestones"),
      listsOf("Job"),
      resultOf("auraos.api.overdue_milestones"),
    ],
  });

  const doc = job.data;

  useEffect(() => {
    if (doc && movedTo === doc.stage) setMovedTo(null);
  }, [doc, movedTo]);

  const stage = movedTo ?? doc?.stage ?? "";

  function moveTo(option: string) {
    if (!doc || option === stage) return;
    setMovedTo(option);
    setStage.mutate(
      { doctype: "Job", name: jobId, fieldname: { stage: option } },
      { onError: () => setMovedTo(null) },
    );
  }

  // Summing the milestone rows the screen already has is not the frontend
  // deciding money: every amount in the sum is the server's own figure,
  // derived from the quoted total when the plan was saved.
  const rows = milestones.data?.milestones ?? [];
  const collected = rows
    .filter((row) => row.status === PAID)
    .reduce((total, row) => total + (row.amount ?? 0), 0);
  const quoted = doc?.quote_total ?? 0;
  const collectedPct = quoted ? Math.min(100, Math.round((collected / quoted) * 100)) : 0;
  const uncollected = Math.max(0, quoted - collected);
  const overdueCount = rows.filter((row) => row.overdue).length;

  const companyName = doc?.company
    ? ((companies.data ?? []).find((row) => row.name === doc.company)?.company_name ?? doc.company)
    : null;

  return (
    <AppShell
      title={doc?.title || jobId}
      meta={
        <span className="flex flex-wrap items-center gap-x-2">
          <Link to="/jobs" className="inline-flex items-center hover:text-ember">
            <ChevronLeft className="size-3.5" /> Jobs
          </Link>
          <span className="num">{jobId}</span>
          {companyName ? <span>· {companyName}</span> : null}
          {doc?.job_owner ? <span>· {doc.job_owner}</span> : null}
        </span>
      }
      actions={
        doc ? (
          <div className="flex items-center gap-2">
            <span
              className={`size-1.5 rounded-full ${stage === "Complete" ? "bg-positive" : "bg-ember"}`}
              aria-hidden="true"
            />
            <select
              value={stage}
              aria-label="Production stage"
              onChange={(event) => moveTo(event.target.value)}
              className="rounded-lg border border-border bg-card px-2.5 py-2 text-sm outline-none focus:border-border-strong"
            >
              {STAGES.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
        ) : null
      }
    >
      <QueryState query={job} loadingRows={6}>
        {(loaded) => (
          <div className="space-y-5">
            {/* Production progress as a chip trail: where the job is, and one
                click to move it. */}
            <div className="flex flex-wrap items-center gap-1 rounded-xl border border-border bg-card p-2">
              {STAGES.map((option, index) => {
                const at = STAGES.indexOf(stage);
                return (
                  <div key={option} className="flex items-center gap-1">
                    <button
                      type="button"
                      title={`Move to ${option}`}
                      onClick={() => moveTo(option)}
                      className={`rounded-md border px-2.5 py-1 text-xs transition-colors ${
                        index === at
                          ? "border-ember bg-ember text-ember-foreground"
                          : index < at
                            ? "border-border bg-secondary text-foreground"
                            : "border-transparent text-muted-foreground hover:border-border"
                      }`}
                    >
                      {option}
                    </button>
                    {index < STAGES.length - 1 ? (
                      <ChevronRight className="size-3 shrink-0 text-border-strong" />
                    ) : null}
                  </div>
                );
              })}
            </div>

            {setStage.isError ? (
              <Card>
                <ErrorState error={setStage.error} />
              </Card>
            ) : null}

            {/* The job's money at a glance: collected against quoted is the
                number the founder chases. */}
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <Stat label="Quoted" value={<Money value={quoted} />} />

              <Stat
                label="Collected"
                value={
                  <Figure query={milestones}>
                    <span className="text-positive">
                      <Money value={collected} />
                    </span>
                  </Figure>
                }
                sub={milestones.isSuccess ? `${collectedPct}% of the quote` : undefined}
              />

              <Stat
                label="Uncollected"
                alert={overdueCount > 0}
                value={
                  <Figure query={milestones}>
                    <Money value={uncollected} />
                  </Figure>
                }
                sub={
                  milestones.isSuccess && overdueCount
                    ? `${countLabel(overdueCount, "milestone")} overdue`
                    : undefined
                }
              />

              <Stat
                label="Spent"
                value={
                  <Figure query={money}>
                    <Money value={money.data?.spent_total ?? 0} />
                  </Figure>
                }
                sub={
                  money.data
                    ? `of ${vnd(money.data.quoted_total)} ₫ quoted costs · ${vnd(
                        money.data.advanced_total,
                      )} ₫ advanced`
                    : undefined
                }
              />
            </div>

            <div role="tablist" className="flex items-center gap-1 border-b border-border">
              {TABS.map((name) => {
                const Icon = TAB_ICONS[name];
                return (
                  <button
                    key={name}
                    type="button"
                    role="tab"
                    id={`tab-${name}`}
                    aria-selected={tab === name}
                    aria-controls={`panel-${name}`}
                    onClick={() => setTab(name)}
                    className={`-mb-px inline-flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
                      tab === name
                        ? "border-ember text-foreground"
                        : "border-transparent text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Icon className="size-3.5 shrink-0" strokeWidth={1.75} aria-hidden="true" />
                    {name}
                    {name === "Money" && overdueCount ? (
                      <span
                        className="ml-1 inline-block size-1.5 rounded-full bg-ember"
                        title="Overdue payments"
                      />
                    ) : null}
                  </button>
                );
              })}
            </div>

            {/* Hidden, not unmounted: an unsaved plan or a half-filled expense
                form survives a trip to another tab. */}
            <div
              role="tabpanel"
              id="panel-Production"
              aria-labelledby="tab-Production"
              hidden={tab !== "Production"}
            >
              <ProductionTab doc={loaded} companyName={companyName} />
            </div>

            <div
              role="tabpanel"
              id="panel-Tasks"
              aria-labelledby="tab-Tasks"
              hidden={tab !== "Tasks"}
            >
              <JobTasks
                job={jobId}
                emptyMessage="Write the plan: what has to happen, who is doing it and by when."
              />
            </div>

            <div
              role="tabpanel"
              id="panel-Money"
              aria-labelledby="tab-Money"
              hidden={tab !== "Money"}
              className="space-y-4"
            >
              <JobMilestonesPanel job={jobId} />
              <JobMoneyPanel job={jobId} />
            </div>

            <div
              role="tabpanel"
              id="panel-Paperwork"
              aria-labelledby="tab-Paperwork"
              hidden={tab !== "Paperwork"}
            >
              <JobPaperworkPanel job={jobId} />
            </div>
          </div>
        )}
      </QueryState>
    </AppShell>
  );
}

/**
 * The work itself: where the files live, what the client has asked to be
 * changed, what the deal sold, and the stage moves that got the job here.
 */
function ProductionTab({ doc, companyName }: { doc: JobDoc; companyName: string | null }) {
  const [location, setLocation] = useState<string | null>(null);
  const [rounds, setRounds] = useState<number | null>(null);
  const [note, setNote] = useState("");
  const [redoNotice, setRedoNotice] = useState("");

  const invalidate = [docKey("Job", doc.name), listsOf("Job")];

  const setValue = useMethodMutation<unknown, SetValueArgs>("frappe.client.set_value", {
    invalidate,
    onSuccess: (_result, args) => {
      // Let the stored value take over again once it matches what was typed.
      if ("files_location" in args.fieldname) setLocation(null);
      if ("included_revision_rounds" in args.fieldname) setRounds(null);
    },
  });

  const revision = useMethodMutation<RevisionResult, Record<string, unknown>>(
    "auraos.api.log_job_revision",
    {
      invalidate,
      onSuccess: (result) => {
        setNote("");
        setRedoNotice(
          result.redo ? `Round ${result.round} logged - this job is back in ${result.stage}.` : "",
        );
      },
    },
  );

  const storedLocation = doc.files_location ?? "";
  const filesLocation = location ?? storedLocation;
  const storedRounds = doc.included_revision_rounds ?? INCLUDED_REVISION_ROUNDS;
  const includedRounds = rounds ?? storedRounds;

  const used = doc.revision_rounds ?? 0;
  const nextIsChargeable = used >= includedRounds;
  // Mirrors redo_stage_for on the server: between being shown a cut and signing
  // it off, a revision sends the job back to the edit.
  const at = STAGES.indexOf(doc.stage);
  const redoOnLog = at > STAGES.indexOf(REDO_STAGE) && at <= STAGES.indexOf(LAST_REDOABLE_STAGE);

  const history = [...doc.stage_history].reverse();
  const failure = setValue.error ?? revision.error;

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <div className="space-y-4 lg:col-span-2">
        <Card title="Files" subtitle="The answer to where this job lives">
          <div className="space-y-2 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <input
                value={filesLocation}
                aria-label="Files location"
                placeholder={`Shared folder for this job code - e.g. //nas/jobs/${doc.name}`}
                onChange={(event) => setLocation(event.target.value)}
                className="min-w-0 flex-1 rounded-lg border border-border bg-background px-2.5 py-1.5 text-sm outline-none focus:border-border-strong"
              />
              <button
                type="button"
                disabled={filesLocation === storedLocation || setValue.isPending}
                onClick={() =>
                  setValue.mutate({
                    doctype: "Job",
                    name: doc.name,
                    fieldname: { files_location: filesLocation },
                  })
                }
                className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-secondary disabled:opacity-40"
              >
                Save
              </button>
            </div>
            {!doc.files_location ? (
              <p className="text-xs text-ember">
                No folder recorded yet - files still live on someone's personal drive.
              </p>
            ) : null}
          </div>
        </Card>

        <Card
          title="Revisions"
          subtitle={countLabel(doc.revisions.length, "round")}
          action={
            <div className="flex flex-wrap items-center justify-end gap-3">
              {doc.change_order_due ? (
                <Pill tone="ember">Round {used} · chargeable change order</Pill>
              ) : (
                <span className="text-xs text-muted-foreground">
                  {used} of {includedRounds} included rounds used
                </span>
              )}
              <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
                Included rounds
                <input
                  type="number"
                  min={0}
                  value={includedRounds}
                  onChange={(event) => setRounds(event.target.valueAsNumber || 0)}
                  onBlur={() => {
                    if (includedRounds === storedRounds) return;
                    setValue.mutate({
                      doctype: "Job",
                      name: doc.name,
                      fieldname: { included_revision_rounds: includedRounds },
                    });
                  }}
                  className="num w-14 rounded-md border border-border bg-background px-1.5 py-0.5 text-right text-xs outline-none focus:border-border-strong"
                />
              </label>
            </div>
          }
        >
          {doc.revisions.length ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-border">
                  <tr>
                    <Th className="w-14">#</Th>
                    <Th className="w-40">Requested</Th>
                    <Th>What the client asked for</Th>
                    <Th className="w-40">By</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {doc.revisions.map((row) => (
                    <tr key={row.name}>
                      <Td className="num">
                        <span className="inline-flex items-center gap-1">
                          {row.round}
                          {row.chargeable ? (
                            <AlertTriangle
                              className="size-3 text-ember"
                              strokeWidth={1.75}
                              aria-label="Chargeable"
                            />
                          ) : null}
                        </span>
                      </Td>
                      <Td className="num text-xs whitespace-nowrap text-muted-foreground">
                        {formatDateTime(row.requested_on)}
                      </Td>
                      <Td>{row.note}</Td>
                      <Td className="text-xs whitespace-nowrap text-muted-foreground">
                        {row.logged_by}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="px-4 py-6 text-center text-sm text-muted-foreground">
              No revision rounds logged.
            </p>
          )}

          <div className="space-y-1.5 border-t border-border px-4 py-3">
            <div className="flex flex-wrap items-center gap-2">
              <input
                value={note}
                aria-label="Revision note"
                placeholder="What did the client ask for?"
                onChange={(event) => setNote(event.target.value)}
                onKeyUp={(event) => {
                  if (event.key === "Enter" && note.trim()) {
                    setRedoNotice("");
                    revision.mutate({ job: doc.name, note });
                  }
                }}
                className="min-w-0 flex-1 rounded-lg border border-border bg-background px-2.5 py-1.5 text-sm outline-none focus:border-border-strong"
              />
              <button
                type="button"
                disabled={!note.trim() || revision.isPending}
                onClick={() => {
                  setRedoNotice("");
                  revision.mutate({ job: doc.name, note });
                }}
                className="rounded-lg bg-ember px-3 py-1.5 text-xs font-medium text-ember-foreground hover:opacity-90 disabled:opacity-40"
              >
                {revision.isPending ? "Logging..." : "Log revision"}
              </button>
            </div>
            {redoNotice ? <p className="text-xs text-ember">{redoNotice}</p> : null}
            {nextIsChargeable ? (
              <p className="text-xs text-ember">
                The next round is past the included ones - it will be flagged as a chargeable change
                order.
              </p>
            ) : null}
            {redoOnLog ? (
              <p className="text-xs text-muted-foreground">
                Logging a revision sends this job back to {REDO_STAGE}.
              </p>
            ) : null}
          </div>
        </Card>

        <Card title="Packages" subtitle="Carried from the deal">
          {doc.packages.length ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-border">
                  <tr>
                    <Th className="w-56">Package</Th>
                    <Th>Description</Th>
                    <Th className="text-right">Price</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {doc.packages.map((row) => (
                    <tr key={row.name}>
                      <Td className="font-medium">{row.title}</Td>
                      <Td className="text-muted-foreground">{row.description}</Td>
                      <Td className="text-right">
                        <Money value={row.price ?? 0} />
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="px-4 py-6 text-center text-sm text-muted-foreground">
              The deal had no packages.
            </p>
          )}
        </Card>

        {failure ? (
          <Card>
            <ErrorState error={failure} />
          </Card>
        ) : null}
      </div>

      <div className="space-y-4">
        <Card title="Client">
          <dl className="space-y-1.5 p-4 text-sm">
            <Row label="Company" value={companyName || doc.company || "-"} />
            {doc.contact ? <Row label="Contact" value={doc.contact} /> : null}
            <Row label="Owner" value={doc.job_owner || "-"} />
            {doc.deal ? (
              <div className="flex justify-between gap-3">
                <dt className="text-muted-foreground">From deal</dt>
                <dd>
                  <Link
                    to="/deals/$dealCode"
                    params={{ dealCode: doc.deal }}
                    className="num text-ember hover:underline"
                  >
                    {doc.deal}
                  </Link>
                </dd>
              </div>
            ) : null}
          </dl>
        </Card>

        {doc.job_links.length ? (
          <Card title="Links">
            <ul className="space-y-1.5 p-4 text-sm">
              {doc.job_links.map((row) => (
                <li key={row.name}>
                  <a
                    href={row.url ?? "#"}
                    target="_blank"
                    rel="noopener"
                    className="text-ember hover:underline"
                  >
                    {row.label || row.url}
                  </a>
                </li>
              ))}
            </ul>
          </Card>
        ) : null}

        <Card title="Quoted" subtitle="At conversion">
          <dl className="space-y-1.5 p-4 text-sm">
            <Row label="Subtotal" value={<Money value={doc.quote_subtotal ?? 0} />} />
            <Row label="Management fee" value={<Money value={doc.quote_mf_amount ?? 0} />} />
            <Row label="VAT" value={<Money value={doc.quote_vat_amount ?? 0} />} />
            <div className="flex justify-between gap-3 border-t border-border pt-1.5">
              <dt className="font-medium">Total</dt>
              <dd>
                <Money value={doc.quote_total ?? 0} />
              </dd>
            </div>
          </dl>
        </Card>

        <Card title="Stage log" subtitle="Every move, newest first">
          {history.length ? (
            <ul className="divide-y divide-border">
              {history.map((row) => (
                <li key={row.name} className="px-4 py-2.5">
                  <div className="text-sm">
                    {row.from_stage ? `${row.from_stage} → ` : ""}
                    {row.to_stage}
                  </div>
                  <div className="num mt-0.5 text-[11px] text-muted-foreground">
                    {formatDateTime(row.changed_on)} · {row.changed_by}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-4 py-6 text-center text-sm text-muted-foreground">
              No stage moves recorded.
            </p>
          )}
        </Card>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right">{value}</dd>
    </div>
  );
}

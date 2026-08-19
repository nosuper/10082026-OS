// Who owes us money, how long they have owed it, and which jobs made money.
//
// Two reads, both of them whole-picture questions rather than range reports:
// auraos.api.finance_receivables and auraos.api.job_profitability. Neither
// takes a date window - what is owed is owed today, and a job's margin is the
// margin it has reached - so this screen deliberately carries no range control.
// The Dashboard, Income and Expenses tabs share one through
// components/aura/FinanceRange; putting a copy of it here would be a control
// that changed nothing.
//
// Every figure on the screen is the server's own. The ageing ladder, its five
// rungs, the per-bucket totals and the per-job margin all arrive computed; the
// only arithmetic here is picking a bar's scale, which is never printed.
//
// A milestone whose job has not reached its trigger stage has no due date and
// sits in "not yet due" on purpose. It is still money owed on a signed job, so
// the ladder carries the full uncollected contract value rather than quietly
// dropping the row.
//
// Margin is producer-visible by decision and the endpoint says so: there is no
// commission, CM, profit before tax, TNDN or net profit on either payload, and
// nothing here reaches for one.

import { createFileRoute, Link } from "@tanstack/react-router";
import { AlertTriangle, ArrowUpRight, CalendarClock, Wallet } from "lucide-react";
import { useState } from "react";

import { AppShell } from "@/components/aura/AppShell";
import { Bar, FinanceTabs } from "@/components/aura/FinanceTabs";
import { scaleOf } from "@/components/aura/FinanceRange";
import { Card, Money, Pill, Stat, Td, Th } from "@/components/aura/primitives";
import { Figure, QueryState } from "@/components/aura/states";
import { countLabel, formatDate, overdueLabel } from "@/lib/format";
import { useMethod } from "@/lib/queries";

// -- what the server sends --
//
// Pinned by the contract tests in
// auraos/auraos/doctype/job_payment_milestone/test_finance_receivables.py and
// auraos/auraos/doctype/job/test_job_profitability.py. Money is whole integer
// đồng everywhere, `days_overdue` is a count and never a sentence, and
// `margin_pct` is a float that is null when there was no revenue to earn it on.

export type ReceivableRow = {
  milestone: string;
  title: string | null;
  job: string;
  job_title: string | null;
  company: string | null;
  company_name: string | null;
  amount: number;
  status: string;
  /** ISO timestamp, or null while the job has not reached the trigger stage. */
  due_on: string | null;
  overdue: boolean;
  days_overdue: number;
};

export type AgeingBucket = {
  bucket: string;
  total: number;
  count: number;
  rows: ReceivableRow[];
};

export type ReceivablesReport = {
  as_of: string | null;
  payment_terms_days: number;
  /** All five rungs, always, in reading order. */
  buckets: AgeingBucket[];
  total: number;
  count: number;
  overdue_total: number;
  overdue_count: number;
};

export type ProfitRow = {
  name: string;
  title: string | null;
  company: string | null;
  client: string | null;
  stage: string;
  quoted_total: number;
  collected: number;
  uncollected: number;
  revenue_ex_vat: number;
  quoted_cost: number;
  actual_cost: number;
  margin: number;
  /** Null when the job was quoted at nothing: no revenue, so no percentage. */
  margin_pct: number | null;
};

export const Route = createFileRoute("/finance/receivables")({
  head: () => ({
    meta: [
      { title: "Receivables - who owes us, and what each job earned | AuraOS" },
      {
        name: "description",
        content:
          "Uncollected milestones aged into not due, 1-30, 31-60, 61-90 and over 90 days, with quoted against collected and spent per job.",
      },
      { property: "og:title", content: "Receivables - AuraOS" },
      {
        property: "og:description",
        content: "Money owed by age, and the margin each job has reached.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ReceivablesPage,
});

/**
 * The rungs in words. The server sends keys - `not_due`, `90+` - because the
 * wording and its language are the frontend's choice, so this is where they
 * become English and nowhere else.
 */
const BUCKET_LABELS: Record<string, string> = {
  not_due: "Not yet due",
  "1-30": "1-30 days",
  "31-60": "31-60 days",
  "61-90": "61-90 days",
  "90+": "Over 90 days",
};

function bucketLabel(key: string): string {
  return BUCKET_LABELS[key] ?? key;
}

/** How alarming a rung is. Not due is calm; past 30 days is ember. */
function bucketTone(key: string): "ink" | "ember" | "muted" {
  if (key === "not_due") return "muted";
  if (key === "1-30") return "ink";
  return "ember";
}

/**
 * A percentage, to one decimal, grouped the Vietnamese way like every other
 * number on the screen. It lives here rather than in lib/format.ts because
 * this is the only screen with a percentage on it so far; the moment a second
 * one needs it, it belongs in the shared formatter.
 */
const PERCENT = new Intl.NumberFormat("vi-VN", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

function percent(value: number | null | undefined, blank = "-"): string {
  if (value === null || value === undefined || Number.isNaN(value)) return blank;
  return `${PERCENT.format(value)}%`;
}

/**
 * The rung a founder wants to land on: the oldest one with debt on it, because
 * the oldest debt is the one that needs a phone call. A pick out of the
 * server's own list, not a calculation.
 */
function worstBucket(buckets: AgeingBucket[]): AgeingBucket | null {
  for (let i = buckets.length - 1; i >= 0; i -= 1) {
    const bucket = buckets[i];
    if (bucket && bucket.count > 0) return bucket;
  }
  return buckets[0] ?? null;
}

/** The client's name, falling back to the code, then to a plain admission. */
function clientOf(row: { company_name: string | null; company: string | null }): string {
  return row.company_name || row.company || "Unknown client";
}

/** Lateness in words. `days_overdue` is a number; format.ts turns it into one. */
function Lateness({ row }: { row: ReceivableRow }) {
  if (!row.overdue) {
    return (
      <span className="text-xs text-muted-foreground">
        {row.due_on ? "Within terms" : "No due date yet"}
      </span>
    );
  }
  return <Pill tone="ember">{overdueLabel(row.days_overdue)}</Pill>;
}

function AgeingLadder({
  report,
  selected,
  onPick,
}: {
  report: ReceivablesReport | undefined;
  selected: AgeingBucket | null;
  onPick: (bucket: string) => void;
}) {
  const buckets = report?.buckets ?? [];
  const scale = scaleOf(buckets.map((bucket) => bucket.total));

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="border-b border-border">
          <tr>
            <Th>Age</Th>
            <Th className="w-full">Share of what is owed</Th>
            <Th className="text-right">Milestones</Th>
            <Th className="text-right">Owed</Th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {buckets.map((bucket) => (
            <tr
              key={bucket.bucket}
              onClick={() => onPick(bucket.bucket)}
              className={`cursor-pointer transition-colors hover:bg-secondary/50 ${
                selected?.bucket === bucket.bucket ? "bg-secondary/60" : ""
              }`}
            >
              <Td className="font-medium whitespace-nowrap">{bucketLabel(bucket.bucket)}</Td>
              <Td>
                <Bar value={bucket.total} max={scale} tone={bucketTone(bucket.bucket)} />
              </Td>
              <Td className="num text-right text-xs text-muted-foreground">{bucket.count}</Td>
              <Td className="text-right">
                <Money
                  value={bucket.total}
                  className={
                    bucket.total === 0
                      ? "text-muted-foreground"
                      : bucketTone(bucket.bucket) === "ember"
                        ? "text-ember"
                        : ""
                  }
                />
              </Td>
            </tr>
          ))}
        </tbody>
        <tfoot className="border-t border-border">
          <tr>
            <Td className="label-caps">Owed in total</Td>
            <Td />
            <Td className="num text-right text-xs text-muted-foreground">{report?.count ?? 0}</Td>
            <Td className="text-right font-semibold">
              <Money value={report?.total ?? 0} />
            </Td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

function ReceivableRows({ rows }: { rows: ReceivableRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="border-b border-border">
          <tr>
            <Th>Job</Th>
            <Th>Client</Th>
            <Th>Milestone</Th>
            <Th className="text-right">Amount</Th>
            <Th>Due</Th>
            <Th>Lateness</Th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((row) => (
            <tr key={row.milestone} className="hover:bg-secondary/50">
              <Td>
                <Link
                  to="/jobs/$jobId"
                  params={{ jobId: row.job }}
                  className="font-medium hover:text-ember"
                >
                  {row.job_title || row.job}
                </Link>
                <div className="num text-[11px] text-muted-foreground">{row.job}</div>
              </Td>
              <Td>
                <div className="max-w-[14rem] truncate" title={clientOf(row)}>
                  {clientOf(row)}
                </div>
              </Td>
              <Td>
                <div>{row.title || "Untitled milestone"}</div>
                <div className="text-[11px] text-muted-foreground">{row.status}</div>
              </Td>
              <Td className="text-right">
                <Money value={row.amount} className={row.overdue ? "text-ember" : ""} />
              </Td>
              <Td className="num text-xs whitespace-nowrap text-muted-foreground">
                {formatDate(row.due_on)}
              </Td>
              <Td>
                <Lateness row={row} />
              </Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ProfitRows({ rows }: { rows: ProfitRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="border-b border-border">
          <tr>
            <Th>Job</Th>
            <Th>Stage</Th>
            <Th className="text-right">Quoted</Th>
            <Th className="text-right">Collected</Th>
            <Th className="text-right">Uncollected</Th>
            <Th className="text-right">Revenue ex VAT</Th>
            <Th className="text-right">Cost so far</Th>
            <Th className="text-right">Margin</Th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((row) => {
            const overspent = row.margin < 0;
            return (
              <tr key={row.name} className="hover:bg-secondary/50">
                <Td className="max-w-[16rem]">
                  <Link
                    to="/jobs/$jobId"
                    params={{ jobId: row.name }}
                    className="block truncate font-medium hover:text-ember"
                    title={row.title ?? row.name}
                  >
                    {row.title || row.name}
                  </Link>
                  <div
                    className="truncate text-[11px] text-muted-foreground"
                    title={row.client ?? ""}
                  >
                    {row.client || row.company || "Unknown client"}
                  </div>
                </Td>
                <Td className="whitespace-nowrap">
                  <Pill>{row.stage}</Pill>
                </Td>
                <Td className="text-right">
                  <Money value={row.quoted_total} />
                </Td>
                <Td className="text-right">
                  <Money
                    value={row.collected}
                    className={row.collected === 0 ? "text-muted-foreground" : "text-positive"}
                  />
                </Td>
                <Td className="text-right">
                  <Money
                    value={row.uncollected}
                    className={row.uncollected === 0 ? "text-muted-foreground" : ""}
                  />
                </Td>
                <Td className="text-right">
                  <Money value={row.revenue_ex_vat} />
                </Td>
                <Td className="text-right whitespace-nowrap">
                  <Money
                    value={row.actual_cost}
                    className={row.actual_cost > row.quoted_cost ? "text-ember" : ""}
                  />
                  <div className="mt-0.5 text-[11px] text-muted-foreground">
                    of <Money value={row.quoted_cost} className="text-[11px]" /> quoted
                  </div>
                </Td>
                <Td className="text-right whitespace-nowrap">
                  <Money value={row.margin} sign className={overspent ? "text-ember" : ""} />
                  <div className="mt-0.5">
                    <Pill
                      tone={row.margin_pct === null ? "neutral" : overspent ? "ember" : "positive"}
                    >
                      {percent(row.margin_pct)}
                    </Pill>
                  </div>
                </Td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ReceivablesPage() {
  const [picked, setPicked] = useState<string | null>(null);

  const receivables = useMethod<ReceivablesReport>("auraos.api.finance_receivables");
  const profit = useMethod<ProfitRow[]>("auraos.api.job_profitability");

  const report = receivables.data;
  const buckets = report?.buckets ?? [];
  const selected = buckets.find((bucket) => bucket.bucket === picked) ?? worstBucket(buckets);
  const notDue = buckets.find((bucket) => bucket.bucket === "not_due");
  const jobs = profit.data ?? [];

  return (
    <AppShell
      title="Receivables"
      meta={
        report
          ? `Owed as of ${formatDate(report.as_of)} · terms ${countLabel(report.payment_terms_days, "day")}`
          : "Owed as of today"
      }
      actions={
        <Link
          to="/finance/income"
          className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium transition-colors hover:bg-secondary"
        >
          Money already in <ArrowUpRight className="size-3.5" />
        </Link>
      }
    >
      <div className="space-y-5">
        <FinanceTabs />

        <p className="flex items-start gap-2 rounded-xl border border-border bg-secondary/40 px-4 py-3 text-xs leading-relaxed text-muted-foreground">
          <Wallet className="mt-0.5 size-4 shrink-0" strokeWidth={1.75} />
          <span>
            <strong className="font-medium text-foreground">Owed today, not over a range.</strong>{" "}
            Every uncollected milestone on a signed job counts, not only the ones past the terms. A
            milestone whose job has not reached its trigger stage has no due date yet and sits in
            "not yet due", so what you see is the full uncollected contract value.
          </span>
        </p>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Stat
            label="Owed in total"
            value={
              <Figure query={receivables}>
                <Money value={report?.total ?? 0} />
              </Figure>
            }
            sub={
              receivables.isSuccess
                ? `${countLabel(report?.count ?? 0, "milestone")} uncollected`
                : undefined
            }
          />
          <Stat
            label="Past the terms"
            value={
              <Figure query={receivables}>
                <Money value={report?.overdue_total ?? 0} />
              </Figure>
            }
            sub={
              receivables.isSuccess
                ? `${countLabel(report?.overdue_count ?? 0, "milestone")} to chase`
                : undefined
            }
            alert={(report?.overdue_total ?? 0) > 0}
          />
          <Stat
            label="Not yet due"
            value={
              <Figure query={receivables}>
                <Money value={notDue?.total ?? 0} />
              </Figure>
            }
            sub={
              receivables.isSuccess
                ? `${countLabel(notDue?.count ?? 0, "milestone")} still to fall due`
                : undefined
            }
          />
          <Stat
            label="Payment terms"
            value={
              <Figure query={receivables} width="4rem">
                <span className="num">{report?.payment_terms_days ?? 0}</span>
              </Figure>
            }
            sub="Days after the due date before a milestone counts late"
          />
        </div>

        <Card
          title="How old the debt is"
          subtitle="All five rungs, every time, including the empty ones"
          action={
            selected ? (
              <span className="label-caps">Showing {bucketLabel(selected.bucket)}</span>
            ) : null
          }
        >
          <QueryState
            query={receivables}
            loadingRows={5}
            isEmpty={() => buckets.length === 0}
            empty={{
              title: "The ageing ladder came back empty.",
              detail:
                "The report always carries five rungs, so this is a server answer worth reporting.",
              icon: <AlertTriangle className="size-6" strokeWidth={1.5} />,
            }}
          >
            {() => <AgeingLadder report={report} selected={selected} onPick={setPicked} />}
          </QueryState>
        </Card>

        <Card
          title={selected ? `Owed: ${bucketLabel(selected.bucket)}` : "What is owed"}
          subtitle="Oldest debt first, with the job, the client and the milestone that carries it"
        >
          <QueryState
            query={receivables}
            loadingRows={4}
            isEmpty={() => (selected?.rows.length ?? 0) === 0}
            empty={{
              title: selected
                ? `Nothing sits in ${bucketLabel(selected.bucket).toLowerCase()}.`
                : "Nobody owes us anything.",
              detail: "Pick another rung above to see what does.",
              icon: <CalendarClock className="size-6" strokeWidth={1.5} />,
            }}
          >
            {() => <ReceivableRows rows={selected?.rows ?? []} />}
          </QueryState>
        </Card>

        <Card
          title="What each job earned"
          subtitle="Quoted against collected and against what it has actually cost. Open jobs, most recently touched first."
          action={<Pill tone="ink">Margin, not the profit chain</Pill>}
        >
          <QueryState
            query={profit}
            loadingRows={5}
            isEmpty={() => jobs.length === 0}
            empty={{
              title: "No open jobs to measure.",
              detail: "A job leaves this list when it reaches Complete.",
            }}
          >
            {() => <ProfitRows rows={jobs} />}
          </QueryState>
        </Card>

        <p className="text-xs text-muted-foreground">
          Margin is revenue excluding VAT less what the job has actually paid out, so an overspent
          job reads negative. Commission, profit before tax and net profit are a different question
          behind a different door, and no call on this screen asks for them.
        </p>
      </div>
    </AppShell>
  );
}

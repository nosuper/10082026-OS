// What the company costs to run, and whether the work it booked covered it
// (#14).
//
// Four reads and five writes, and every figure on the screen arrives already
// worked out. auraos.api.break_even(date_from, date_to) answers the line
// itself, auraos.api.overhead_log(date_from, date_to) the payments behind it,
// auraos.api.overheads_due() the standing costs whose month has come round
// unrecorded, auraos.api.recurring_overheads() the standing costs themselves.
// **Nothing here is computed in the browser** - not a month's overhead, not a
// contribution, not a surplus, not the run rate. The only arithmetic on this
// file is picking a bar's scale, which is never printed.
//
// **Show, don't suggest.** #14 says it in as many words, and it is the reason
// this screen has no "recommended floor", no suggested price and no button
// that writes one. The margin floor is set in Settings, by the founder,
// against things this app cannot see - the quarter ahead, who is about to
// leave, what a client is worth keeping. This screen is the evidence for that
// judgement, not a substitute for it. The payload carries no key a screen
// could render as advice, and the contract test in
// auraos/auraos/doctype/job/test_break_even.py fails if one appears.
//
// **The two sides of the line are dated by different things, and the screen
// says so on its face.** An overhead falls in the month the money left the
// account. A job's margin is its whole life's margin, counted in the month the
// job was booked - because that is the month somebody said yes at that price,
// which is the decision being checked. Both bases are read off the payload
// rather than asserted here, and the caveats are printed rather than worded by
// this file: a screen that had to invent the words for a limit is the one most
// likely to invent them wrongly.
//
// **A surplus made of open jobs is shown as one.** An open job is still
// spending, so its margin can only fall. The final half - the jobs that have
// finished - is printed beside the whole, because a month can be in surplus on
// everything it booked and in shortfall on everything it has finished, and
// those are different facts.
//
// **A standing cost is a template, and this screen never turns one into a
// payment on its own.** A Company Expense posts to the cash ledger, so an
// invented one makes the cash screens disagree with the bank statement. What
// is due is offered, ticked and confirmed - twelve forms a year become twelve
// clicks, and no đồng is posted that nobody decided.
//
// Founder-only, decided by the server. Every endpoint here throws
// PermissionError for anyone else and the doctypes underneath grant no
// Producer row, so a producer opening this URL gets the permission card every
// refusal in this app renders. Nothing is hidden here to bring that about -
// the tab is absent for a producer only so the nav stays honest.

import { createFileRoute } from "@tanstack/react-router";
import { CalendarClock, Repeat, Scale, Wallet } from "lucide-react";
import { useState } from "react";

import { AppShell } from "@/components/aura/AppShell";
import {
  FinanceRangeBar,
  MonthLabel,
  rangeLabel,
  scaleOf,
  useFinanceRange,
} from "@/components/aura/FinanceRange";
import { Bar, FinanceTabs } from "@/components/aura/FinanceTabs";
import { Card, Money, Pill, Stat, Td, Th, inputClass } from "@/components/aura/primitives";
import { ErrorState, Figure, QueryState } from "@/components/aura/states";
import { countLabel, formatDate, parseVnd, percent, vnd } from "@/lib/format";
import { resultOf, useMethod, useMethodMutation } from "@/lib/queries";

// -- what the server sends --
//
// Pinned by the pure tests in tests/test_breakeven.py and tests/test_recurring.py
// and by the contract test in auraos/auraos/doctype/job/test_break_even.py.
// Money is whole integer đồng at every level; `coverage_pct` is a float that is
// null - never 0 - when there was no overhead to cover, because a month that
// spent nothing on itself had nothing to cover rather than covering none of it.

type BreakEvenMonth = {
  month: string;
  overhead: number;
  /** A purchase the accountant may spread over years. Beside the line, never inside it. */
  flagged_overhead: number;
  overhead_count: number;
  contribution: number;
  /** The half that cannot move: jobs that have finished spending. */
  final_contribution: number;
  provisional_contribution: number;
  job_count: number;
  final_count: number;
  /** Signed. Below zero the month's work did not pay for the month. */
  surplus: number;
  final_surplus: number;
  coverage_pct: number | null;
  covered: boolean;
};

type BreakEvenJob = {
  job: string;
  title: string | null;
  client: string | null;
  stage: string;
  is_final: boolean;
  booked_on: string;
  month: string;
  revenue_ex_vat: number;
  actual_cost: number;
  margin: number;
  margin_pct: number | null;
};

type BreakEvenReport = {
  date_from: string;
  date_to: string;
  contribution_basis: string;
  overhead_basis: string;
  months: BreakEvenMonth[];
  total: Omit<BreakEvenMonth, "month">;
  jobs: BreakEvenJob[];
  unbooked: { count: number; margin: number; jobs: BreakEvenJob[] };
  flagged: { total: number; count: number };
  by_category: { category: string | null; total: number; count: number }[];
  caveats: { figure: string; why: string }[];
  committed: {
    months: { month: string; committed: number; count: number }[];
    committed_total: number;
    /** The run rate as it stands, taken from the last month rather than averaged. */
    monthly_committed: number;
  };
};

type OverheadRow = {
  name: string;
  spent_on: string;
  amount: number;
  category: string | null;
  description: string | null;
  supplier: string | null;
  invoice_no: string | null;
  for_depreciation: 0 | 1;
  recurring: string | null;
  recurring_month: string | null;
};

type OverheadLog = {
  date_from: string;
  date_to: string;
  rows: OverheadRow[];
  overheads: {
    basis: string;
    paid_total: number;
    count: number;
    by_category: { category: string | null; total: number; count: number }[];
    flagged: { total: number; count: number };
  };
  input_vat: { basis: string; vat_total: number; count: number };
};

type StandingCost = {
  name: string;
  label: string;
  amount: number;
  category: string | null;
  paid_from: string | null;
  supplier: string | null;
  description: string | null;
  day_of_month: number | null;
  starts_on: string;
  ends_on: string | null;
  disabled: 0 | 1;
};

type StandingCosts = {
  rows: StandingCost[];
  schedule: {
    months: { month: string; committed: number; count: number }[];
    committed_total: number;
    monthly_committed: number;
  };
};

type DueRow = {
  template: string;
  label: string;
  month: string;
  due_on: string;
  amount: number;
  category: string | null;
};

type DueReport = { basis: string; rows: DueRow[]; count: number; amount_total: number };

/** Every key that changes when an overhead is written, in one place. */
const OVERHEAD_QUERIES = [
  resultOf("auraos.api.break_even"),
  resultOf("auraos.api.overhead_log"),
  resultOf("auraos.api.overheads_due"),
  resultOf("auraos.api.recurring_overheads"),
  resultOf("auraos.api.period_tax_position"),
  resultOf("auraos.api.cash_accounts"),
];

export const Route = createFileRoute("/finance/overhead")({
  head: () => ({
    meta: [
      { title: "Overhead - what the company costs to run | AuraOS" },
      {
        name: "description",
        content:
          "The monthly overhead log, the standing costs behind it, and the break-even line: what the company paid for its own upkeep against the margin of the work it booked.",
      },
      { property: "og:title", content: "Overhead - AuraOS" },
      {
        property: "og:description",
        content: "Overhead against booked margin, month by month. Founder only.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: OverheadPage,
});

/** A month that did not pay for itself is the one that needs the eye. */
function surplusTone(surplus: number): string {
  return surplus < 0 ? "ember" : "positive";
}

function OverheadPage() {
  const [range, setRange] = useFinanceRange();

  const line = useMethod<BreakEvenReport>("auraos.api.break_even", {
    date_from: range.from,
    date_to: range.to,
  });
  const log = useMethod<OverheadLog>("auraos.api.overhead_log", {
    date_from: range.from,
    date_to: range.to,
  });

  const report = line.data;
  const months = report?.months ?? [];
  const total = report?.total;

  // One scale across both sides of every bar, so a tall contribution bar and a
  // short overhead bar underneath it mean what they look like they mean.
  const scale = scaleOf(months.flatMap((month) => [month.contribution, month.overhead]));

  return (
    <AppShell
      title="Overhead"
      meta={`What the company costs to run · ${rangeLabel(range)}`}
      actions={<Pill tone="ink">Founder only</Pill>}
    >
      <div className="space-y-5">
        <FinanceTabs />

        <FinanceRangeBar range={range} onChange={setRange} />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Stat
            label="Overhead in range"
            value={
              <Figure query={line}>
                <Money value={total?.overhead ?? 0} />
              </Figure>
            }
            sub={
              line.isSuccess
                ? `${countLabel(total?.overhead_count ?? 0, "payment")} · run rate ${vnd(
                    report?.committed.monthly_committed ?? 0,
                  )}₫/month`
                : undefined
            }
          />
          <Stat
            label="Contribution"
            value={
              <Figure query={line}>
                <Money value={total?.contribution ?? 0} />
              </Figure>
            }
            sub={
              line.isSuccess
                ? `${countLabel(total?.job_count ?? 0, "job")} booked · ${
                    total?.final_count ?? 0
                  } finished`
                : undefined
            }
          />
          <Stat
            label={(total?.surplus ?? 0) < 0 ? "Shortfall" : "Surplus"}
            value={
              <Figure query={line}>
                <Money value={total?.surplus ?? 0} sign />
              </Figure>
            }
            sub={line.isSuccess ? "Contribution less overhead" : undefined}
            alert={(total?.surplus ?? 0) < 0}
          />
          <Stat
            label="Upkeep covered"
            value={
              <Figure query={line} width="4rem">
                <span className="num">{percent(total?.coverage_pct ?? null)}</span>
              </Figure>
            }
            sub={
              line.isSuccess
                ? total?.coverage_pct === null
                  ? "Nothing was spent on the company itself"
                  : "How much of the upkeep the booked work paid for"
                : undefined
            }
          />
        </div>

        {/* The bases, on the screen's face rather than in a tooltip. A reader
            who tries to reconcile the contribution side against Income should
            be told why it will not match before they try. */}
        {report ? (
          <p className="flex items-start gap-2 rounded-xl border border-border bg-secondary/40 px-4 py-3 text-xs leading-relaxed text-muted-foreground">
            <Scale className="mt-0.5 size-4 shrink-0" strokeWidth={1.75} />
            <span>
              <strong className="font-medium text-foreground">
                The two sides are dated by different things.
              </strong>{" "}
              Overhead is {report.overhead_basis}. Contribution is {report.contribution_basis}.
            </span>
          </p>
        ) : null}

        <Card
          title="Break-even by month"
          subtitle="What the month's booked work left behind, against what the company spent on itself"
        >
          <QueryState
            query={line}
            loadingRows={6}
            isEmpty={() => months.length === 0}
            empty={{
              title: "That range covers no months.",
              detail: "Pick a range that ends on or after the day it starts.",
              icon: <CalendarClock className="size-6" strokeWidth={1.5} />,
            }}
          >
            {() => (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b border-border">
                    <tr>
                      <Th>Month</Th>
                      <Th className="w-full">Contribution against overhead</Th>
                      <Th className="text-right">Contribution</Th>
                      <Th className="text-right">Overhead</Th>
                      <Th className="text-right">Surplus</Th>
                      <Th className="text-right">Covered</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {months.map((month) => (
                      <tr key={month.month} className="hover:bg-secondary/50">
                        <Td className="whitespace-nowrap">
                          <MonthLabel month={month.month} />
                        </Td>
                        <Td>
                          <div className="space-y-1">
                            <Bar value={month.contribution} max={scale} tone="ink" />
                            <Bar value={month.overhead} max={scale} tone="ember" />
                          </div>
                        </Td>
                        <Td className="text-right">
                          <Money value={month.contribution} />
                          {month.provisional_contribution !== 0 ? (
                            <div className="mt-0.5 text-xs text-muted-foreground">
                              {vnd(month.final_contribution)}₫ final
                            </div>
                          ) : null}
                        </Td>
                        <Td className="text-right text-muted-foreground">
                          <Money value={month.overhead} />
                          {month.flagged_overhead !== 0 ? (
                            <div className="mt-0.5 text-xs">
                              +{vnd(month.flagged_overhead)}₫ for depreciation
                            </div>
                          ) : null}
                        </Td>
                        <Td className="text-right">
                          <Money
                            value={month.surplus}
                            sign
                            className={month.surplus < 0 ? "text-ember" : ""}
                          />
                        </Td>
                        <Td className="text-right">
                          <Pill tone={surplusTone(month.surplus)}>
                            {percent(month.coverage_pct)}
                          </Pill>
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="border-t border-border">
                    <tr className="font-semibold">
                      <Td className="label-caps">Range</Td>
                      <Td />
                      <Td className="text-right">
                        <Money value={total?.contribution ?? 0} />
                      </Td>
                      <Td className="text-right text-muted-foreground">
                        <Money value={total?.overhead ?? 0} />
                      </Td>
                      <Td className="text-right">
                        <Money value={total?.surplus ?? 0} sign />
                      </Td>
                      <Td className="num text-right">{percent(total?.coverage_pct ?? null)}</Td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </QueryState>

          {/* Printed, not worded here. A screen that had to invent the words
              for a limit is the one most likely to invent them wrongly. */}
          {report ? (
            <div className="space-y-2 border-t border-border px-4 py-3">
              <p className="label-caps">What this line does not say</p>
              {report.caveats.map((caveat) => (
                <p key={caveat.figure} className="text-xs leading-relaxed text-muted-foreground">
                  <strong className="font-medium text-foreground">{caveat.figure}</strong> —{" "}
                  {caveat.why}.
                </p>
              ))}
            </div>
          ) : null}
        </Card>

        <BookedWork line={line} />

        <StandingCostsDue />

        <StandingCostList range={range} />

        <OverheadLogCard log={log} range={range} />
      </div>
    </AppShell>
  );
}

/**
 * The jobs behind the line, finished ones first.
 *
 * A sort and a partition of the server's own rows - no figure here comes out
 * of this. `is_final` is the server's verdict rather than a stage name
 * compared in the browser, because which stage ends a job is not this file's
 * to know.
 */
function BookedWork({ line }: { line: ReturnType<typeof useMethod<BreakEvenReport>> }) {
  const jobs = line.data?.jobs ?? [];
  const unbooked = line.data?.unbooked;
  const byMargin = [...jobs].sort((a, b) => b.margin - a.margin);
  const finished = byMargin.filter((row) => row.is_final);
  const running = byMargin.filter((row) => !row.is_final);

  return (
    <Card
      title="The work behind the line"
      subtitle="Each job's whole-life margin, counted in the month it was booked"
      action={
        line.isSuccess ? (
          <span className="label-caps">
            {countLabel(finished.length, "finished job")} · {countLabel(running.length, "job")}{" "}
            still running
          </span>
        ) : null
      }
    >
      <QueryState
        query={line}
        loadingRows={4}
        isEmpty={() => jobs.length === 0}
        empty={{
          title: "No work was booked in this range.",
          detail:
            "A job appears here in the month its won deal was converted, which is the month the work was taken on at the price being judged.",
          icon: <Scale className="size-6" strokeWidth={1.5} />,
        }}
      >
        {() => (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-border">
                <tr>
                  <Th>Booked</Th>
                  <Th className="w-full">Job</Th>
                  <Th className="text-right">Revenue</Th>
                  <Th className="text-right">Spent</Th>
                  <Th className="text-right">Margin</Th>
                  <Th className="text-right">Final?</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {[...finished, ...running].map((row) => (
                  <tr key={row.job} className="hover:bg-secondary/50">
                    <Td className="num text-xs whitespace-nowrap">{formatDate(row.booked_on)}</Td>
                    <Td>
                      <div className="font-medium">{row.title || row.job}</div>
                      <div className="mt-0.5 text-xs text-muted-foreground">
                        {row.client ? `${row.client} · ` : ""}
                        {row.stage}
                      </div>
                    </Td>
                    <Td className="text-right">
                      <Money value={row.revenue_ex_vat} />
                    </Td>
                    <Td className="text-right text-muted-foreground">
                      <Money value={row.actual_cost} />
                    </Td>
                    <Td className="text-right">
                      <Money
                        value={row.margin}
                        sign
                        className={row.margin < 0 ? "text-ember" : ""}
                      />
                      <div className="mt-0.5 text-xs text-muted-foreground">
                        {percent(row.margin_pct)}
                      </div>
                    </Td>
                    <Td className="text-right">
                      <Pill tone={row.is_final ? "ink" : "outline"}>
                        {row.is_final ? "Final" : "Still spending"}
                      </Pill>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </QueryState>

      {/* A job with no booking date belongs to no month. Visible rather than
          merely absent from a total, because a job the founder cannot see is
          worse than one in a bucket labelled "no date". */}
      {unbooked && unbooked.count > 0 ? (
        <p className="border-t border-border px-4 py-3 text-xs leading-relaxed text-muted-foreground">
          {countLabel(unbooked.count, "job")} carries no booking date and is in no month here. Its
          margin is <Money value={unbooked.margin} className="text-foreground" />.
        </p>
      ) : null}
    </Card>
  );
}

/**
 * Standing costs whose month has come round with nothing recorded against it.
 *
 * Due, never overdue: whether the landlord has been paid is a fact about a bank
 * account, and this only knows what has been typed. The basis is read off the
 * payload rather than worded here.
 *
 * Ticked and confirmed rather than posted on a timer. A Company Expense moves
 * money in the cash ledger, so nothing writes one without the founder saying
 * that it happened.
 */
function StandingCostsDue() {
  const [ticked, setTicked] = useState<Set<string>>(new Set());
  const due = useMethod<DueReport>("auraos.api.overheads_due");
  const record = useMethodMutation<
    { written: unknown[]; skipped: { template: string; month: string }[] },
    Record<string, unknown>
  >("auraos.api.record_recurring_overheads", {
    invalidate: OVERHEAD_QUERIES,
    onSuccess: () => setTicked(new Set()),
  });

  const rows = due.data?.rows ?? [];
  const keyOf = (row: DueRow) => `${row.template}:${row.month}`;
  const chosen = rows.filter((row) => ticked.has(keyOf(row)));
  // The screen adds nothing the server has not: this is the sum of the rows
  // the founder ticked, which is a selection rather than a figure.
  const chosenTotal = chosen.reduce((sum, row) => sum + row.amount, 0);

  const toggle = (row: DueRow) => {
    const next = new Set(ticked);
    const key = keyOf(row);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    setTicked(next);
  };

  return (
    <Card
      title="Standing costs due"
      subtitle={due.data?.basis ?? "Months that have come round with nothing recorded against them"}
      action={
        rows.length > 0 ? (
          <button
            type="button"
            onClick={() => setTicked(new Set(rows.map(keyOf)))}
            className="rounded-lg border border-border px-2 py-1 text-xs hover:bg-secondary"
          >
            Tick all
          </button>
        ) : null
      }
    >
      <QueryState
        query={due}
        loadingRows={3}
        isEmpty={() => rows.length === 0}
        empty={{
          title: "Nothing is waiting to be recorded.",
          detail:
            "Every month each standing cost has run in has a payment against it. A month still ahead is never offered here.",
          icon: <Repeat className="size-6" strokeWidth={1.5} />,
        }}
      >
        {() => (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-border">
                  <tr>
                    <Th />
                    <Th className="w-full">What</Th>
                    <Th>Month</Th>
                    <Th>Falls on</Th>
                    <Th className="text-right">Amount</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {rows.map((row) => (
                    <tr key={keyOf(row)} className="hover:bg-secondary/50">
                      <Td>
                        <input
                          type="checkbox"
                          aria-label={`Record ${row.label} for ${row.month}`}
                          checked={ticked.has(keyOf(row))}
                          onChange={() => toggle(row)}
                        />
                      </Td>
                      <Td>
                        <span className="font-medium">{row.label}</span>
                        {row.category ? (
                          <span className="ml-2 text-xs text-muted-foreground">{row.category}</span>
                        ) : null}
                      </Td>
                      <Td className="num text-xs whitespace-nowrap">
                        <MonthLabel month={row.month} />
                      </Td>
                      <Td className="num text-xs whitespace-nowrap">{formatDate(row.due_on)}</Td>
                      <Td className="text-right">
                        <Money value={row.amount} />
                      </Td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="border-t border-border">
                  <tr className="font-semibold">
                    <Td />
                    <Td className="label-caps">
                      {countLabel(due.data?.count ?? 0, "month")} waiting
                    </Td>
                    <Td />
                    <Td />
                    <Td className="text-right">
                      <Money value={due.data?.amount_total ?? 0} />
                    </Td>
                  </tr>
                </tfoot>
              </table>
            </div>
            <div className="flex flex-wrap items-center gap-3 border-t border-border p-4">
              <button
                type="button"
                disabled={chosen.length === 0 || record.isPending}
                onClick={() =>
                  record.mutate({
                    rows: chosen.map((row) => ({ template: row.template, month: row.month })),
                  })
                }
                className="rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
              >
                {record.isPending
                  ? "Recording..."
                  : `Record ${countLabel(chosen.length, "payment")} · ${vnd(chosenTotal)}₫`}
              </button>
              <span className="text-xs leading-relaxed text-muted-foreground">
                Each one becomes a payment on the overhead log and moves money out of its account.
                Correct the amount there if the month came out different.
              </span>
            </div>
            {record.data && record.data.skipped.length > 0 ? (
              <p className="border-t border-border px-4 py-3 text-xs text-muted-foreground">
                {countLabel(record.data.skipped.length, "month")} was already recorded and was
                skipped rather than written twice.
              </p>
            ) : null}
            {record.error ? <ErrorState error={record.error} /> : null}
          </>
        )}
      </QueryState>
    </Card>
  );
}

/** The standing costs themselves, and what they commit the company to. */
function StandingCostList({ range }: { range: { from: string; to: string } }) {
  const [editing, setEditing] = useState<StandingCost | null>(null);
  const [adding, setAdding] = useState(false);
  const costs = useMethod<StandingCosts>("auraos.api.recurring_overheads", {
    date_from: range.from,
    date_to: range.to,
  });
  const remove = useMethodMutation<{ deleted: string }, Record<string, unknown>>(
    "auraos.api.delete_recurring_overhead",
    { invalidate: OVERHEAD_QUERIES },
  );

  const rows = costs.data?.rows ?? [];

  return (
    <Card
      title="Standing costs"
      subtitle="Rent, salaries, subscriptions - what the company owes every month whether or not it has been written down"
      action={
        <div className="flex items-center gap-2">
          {costs.isSuccess ? (
            <span className="label-caps">
              {vnd(costs.data?.schedule.monthly_committed ?? 0)}₫ a month
            </span>
          ) : null}
          <button
            type="button"
            onClick={() => {
              setAdding(true);
              setEditing(null);
            }}
            className="rounded-lg border border-border px-2 py-1 text-xs hover:bg-secondary"
          >
            Add
          </button>
        </div>
      }
    >
      <QueryState
        query={costs}
        loadingRows={3}
        isEmpty={() => rows.length === 0 && !adding}
        empty={{
          title: "No standing cost recorded yet.",
          detail:
            "Add the rent, the salaries and the subscriptions once, and each month comes round on this screen to be confirmed instead of typed again.",
          icon: <Repeat className="size-6" strokeWidth={1.5} />,
        }}
      >
        {() => (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-border">
                <tr>
                  <Th className="w-full">What</Th>
                  <Th>Day</Th>
                  <Th>Runs</Th>
                  <Th className="text-right">Each month</Th>
                  <Th />
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {rows.map((row) => (
                  <tr key={row.name} className="hover:bg-secondary/50">
                    <Td>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{row.label}</span>
                        {row.disabled ? <Pill>Paused</Pill> : null}
                      </div>
                      {row.category ? (
                        <div className="mt-0.5 text-xs text-muted-foreground">{row.category}</div>
                      ) : null}
                    </Td>
                    <Td className="num text-xs">{row.day_of_month ?? 1}</Td>
                    <Td className="text-xs whitespace-nowrap text-muted-foreground">
                      {formatDate(row.starts_on)}
                      {row.ends_on ? ` – ${formatDate(row.ends_on)}` : " –"}
                    </Td>
                    <Td className="text-right">
                      <Money value={row.amount} />
                    </Td>
                    <Td className="whitespace-nowrap text-right">
                      <button
                        type="button"
                        onClick={() => {
                          setEditing(row);
                          setAdding(false);
                        }}
                        className="rounded-lg border border-border px-2 py-1 text-xs hover:bg-secondary"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => remove.mutate({ name: row.name })}
                        className="ml-1 rounded-lg border border-border px-2 py-1 text-xs hover:bg-secondary"
                      >
                        Delete
                      </button>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </QueryState>

      {remove.error ? <ErrorState error={remove.error} /> : null}

      {adding || editing ? (
        <StandingCostForm
          cost={editing}
          onDone={() => {
            setAdding(false);
            setEditing(null);
          }}
        />
      ) : null}
    </Card>
  );
}

/**
 * One standing cost, created or amended.
 *
 * Amending changes what the company is committed to from now on. It restates
 * no payment already recorded - those carry their own amounts, where a
 * correction is visible beside the money it changed.
 */
function StandingCostForm({ cost, onDone }: { cost: StandingCost | null; onDone: () => void }) {
  const [label, setLabel] = useState(cost?.label ?? "");
  const [amount, setAmount] = useState(cost ? String(cost.amount) : "");
  const [category, setCategory] = useState(cost?.category ?? "");
  const [day, setDay] = useState(String(cost?.day_of_month ?? 1));
  const [startsOn, setStartsOn] = useState(cost?.starts_on ?? "");
  const [endsOn, setEndsOn] = useState(cost?.ends_on ?? "");

  const categories = useMethod<string[]>("auraos.api.company_expense_categories");
  const save = useMethodMutation<StandingCost, Record<string, unknown>>(
    "auraos.api.save_recurring_overhead",
    { invalidate: OVERHEAD_QUERIES, onSuccess: onDone },
  );

  const value = parseVnd(amount);
  // Refused by the server too - this only keeps the screen from offering a
  // button that would be rejected.
  const sound = Boolean(label.trim() && value > 0 && startsOn);

  return (
    <div className="space-y-3 border-t border-border p-4">
      <p className="label-caps">{cost ? `Amend ${cost.label}` : "New standing cost"}</p>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        <input
          aria-label="What it is"
          placeholder="What it is - Tiền thuê văn phòng"
          value={label}
          onChange={(event) => setLabel(event.target.value)}
          className={inputClass}
        />
        <input
          aria-label="Amount each month"
          inputMode="numeric"
          placeholder="Amount each month"
          value={value ? vnd(value) : amount}
          onChange={(event) => setAmount(event.target.value)}
          className={`num ${inputClass}`}
        />
        <select
          aria-label="Category"
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          className={inputClass}
        >
          <option value="">No category</option>
          {(categories.data ?? []).map((one) => (
            <option key={one} value={one}>
              {one}
            </option>
          ))}
        </select>
        <input
          aria-label="Day of the month"
          inputMode="numeric"
          placeholder="Day of the month"
          value={day}
          onChange={(event) => setDay(event.target.value)}
          className={`num ${inputClass}`}
        />
        <input
          aria-label="First month"
          type="date"
          value={startsOn}
          onChange={(event) => setStartsOn(event.target.value)}
          className={`num ${inputClass}`}
        />
        <input
          aria-label="Last month, if it has stopped"
          type="date"
          value={endsOn}
          onChange={(event) => setEndsOn(event.target.value)}
          className={`num ${inputClass}`}
        />
      </div>
      <p className="text-xs leading-relaxed text-muted-foreground">
        The day is where it usually falls; 31 means month end and lands on the 28th in February.
        Leave the last month empty while it is still running. A cost that has stopped gets a last
        month rather than being deleted - that keeps the history of what the company used to pay
        for, and once any payment has been recorded from it deleting is refused outright.
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={!sound || save.isPending}
          onClick={() =>
            save.mutate({
              name: cost?.name ?? null,
              values: {
                label: label.trim(),
                amount: value,
                category: category || null,
                day_of_month: Number(day) || 1,
                starts_on: startsOn,
                ends_on: endsOn || null,
              },
            })
          }
          className="rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
        >
          {save.isPending ? "Saving..." : cost ? "Save" : "Add"}
        </button>
        <button
          type="button"
          onClick={onDone}
          className="rounded-lg border border-border px-3 py-2 text-xs hover:bg-secondary"
        >
          Cancel
        </button>
      </div>
      {save.error ? <ErrorState error={save.error} /> : null}
    </div>
  );
}

/** The payments themselves - the standing ones and the one-offs, together. */
function OverheadLogCard({
  log,
  range,
}: {
  log: ReturnType<typeof useMethod<OverheadLog>>;
  range: { from: string; to: string };
}) {
  const rows = log.data?.rows ?? [];
  const totals = log.data?.overheads;

  return (
    <Card
      title="Overhead log"
      subtitle={totals?.basis ?? "What the company paid for its own upkeep"}
      action={
        log.isSuccess ? (
          <span className="label-caps">{countLabel(totals?.count ?? 0, "payment")}</span>
        ) : null
      }
    >
      <OneOffEntry range={range} />

      <QueryState
        query={log}
        loadingRows={5}
        isEmpty={() => rows.length === 0}
        empty={{
          title: "Nothing was paid on the company itself in this range.",
          detail:
            "Rent, salaries, subscriptions and one-off purchases land here. Standing costs arrive by being confirmed above; anything else is typed once.",
          icon: <Wallet className="size-6" strokeWidth={1.5} />,
        }}
      >
        {() => (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-border">
                <tr>
                  <Th>Paid</Th>
                  <Th className="w-full">What</Th>
                  <Th>Category</Th>
                  <Th className="text-right">Amount</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {rows.map((row) => (
                  <tr key={row.name} className="hover:bg-secondary/50">
                    <Td className="num text-xs whitespace-nowrap">{formatDate(row.spent_on)}</Td>
                    <Td>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{row.description || row.name}</span>
                        {/* Which payments came from a standing cost and which
                            were typed. The two read differently when a month
                            looks wrong. */}
                        {row.recurring ? <Pill>{row.recurring_month}</Pill> : null}
                        {row.for_depreciation ? <Pill tone="outline">Depreciation</Pill> : null}
                      </div>
                      {row.supplier ? (
                        <div className="mt-0.5 text-xs text-muted-foreground">{row.supplier}</div>
                      ) : null}
                    </Td>
                    <Td className="text-xs text-muted-foreground">{row.category ?? "-"}</Td>
                    <Td className="text-right">
                      <Money value={row.amount} />
                    </Td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="border-t border-border">
                <tr className="font-semibold">
                  <Td className="label-caps">Range</Td>
                  <Td />
                  <Td />
                  <Td className="text-right">
                    <Money value={totals?.paid_total ?? 0} />
                  </Td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </QueryState>

      {totals && totals.flagged.count > 0 ? (
        <p className="border-t border-border px-4 py-3 text-xs leading-relaxed text-muted-foreground">
          {countLabel(totals.flagged.count, "purchase")} worth{" "}
          <Money value={totals.flagged.total} className="text-foreground" /> is marked for
          depreciation and sits outside the break-even line. The money still left the account.
        </p>
      ) : null}
    </Card>
  );
}

/**
 * One thing the company bought for itself - the printer, the client lunch.
 *
 * The one-off half of the entry criterion, beside the standing costs that come
 * round on their own. Everything but the amount has a default that is right
 * often enough not to be typed: an expense that is a chore to record is an
 * expense that goes unrecorded, and an unrecorded expense mismatches the
 * accountant's return invisibly.
 */
function OneOffEntry({ range }: { range: { from: string; to: string } }) {
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [spentOn, setSpentOn] = useState("");
  const [depreciation, setDepreciation] = useState(false);

  const categories = useMethod<string[]>("auraos.api.company_expense_categories");
  const log = useMethodMutation<OverheadRow, Record<string, unknown>>(
    "auraos.api.log_company_expense",
    {
      invalidate: OVERHEAD_QUERIES,
      onSuccess: () => {
        setAmount("");
        setDescription("");
      },
    },
  );

  const value = parseVnd(amount);

  return (
    <div className="space-y-2 border-b border-border p-4">
      <div className="flex flex-wrap items-end gap-2">
        <input
          aria-label="Amount"
          inputMode="numeric"
          placeholder="Amount"
          value={value ? vnd(value) : amount}
          onChange={(event) => setAmount(event.target.value)}
          className={`num w-36 ${inputClass}`}
        />
        <input
          aria-label="What it was for"
          placeholder="What it was for"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          className={`min-w-40 flex-1 ${inputClass}`}
        />
        <select
          aria-label="Category"
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          className={`w-44 ${inputClass}`}
        >
          <option value="">No category</option>
          {(categories.data ?? []).map((one) => (
            <option key={one} value={one}>
              {one}
            </option>
          ))}
        </select>
        <input
          aria-label="Day it was paid"
          type="date"
          value={spentOn}
          onChange={(event) => setSpentOn(event.target.value)}
          className={`num w-40 ${inputClass}`}
        />
        <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <input
            type="checkbox"
            checked={depreciation}
            onChange={(event) => setDepreciation(event.target.checked)}
          />
          For depreciation
        </label>
        <button
          type="button"
          disabled={value <= 0 || log.isPending}
          onClick={() =>
            log.mutate({
              amount: value,
              description: description || null,
              category: category || null,
              // Defaulted by the server to today when the founder leaves it
              // alone, which is the day most of these are entered.
              spent_on: spentOn || null,
              for_depreciation: depreciation ? 1 : 0,
            })
          }
          className="rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
        >
          {log.isPending ? "Recording..." : "Record"}
        </button>
      </div>
      <p className="text-xs leading-relaxed text-muted-foreground">
        Recorded against the company rather than a job, and it moves money out of the default
        account. A payment dated outside {rangeLabel(range)} is saved all the same and appears when
        the range reaches it.
      </p>
      {log.error ? <ErrorState error={log.error} /> : null}
    </div>
  );
}

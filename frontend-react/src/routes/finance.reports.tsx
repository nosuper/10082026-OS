// Profit and loss by month, and the margin each job reached.
//
// Two reads: auraos.api.finance_profit_and_loss(date_from, date_to) and
// auraos.api.job_profitability(include_closed=1). Between them they answer the
// whole screen, and that is deliberate - **nothing here is computed in the
// browser from a list of rows**. Every month's income, expense, profit and
// margin arrives already worked out, and so does the range total. The only
// arithmetic on this file is picking a bar's scale, which is never printed.
//
// The P&L is not two payloads zipped together on the client. It could have
// been: finance_income and finance_expenses both return months over the same
// range. But then the browser would own two rules it has no business owning -
// which months line up, and what a margin percentage is in a month nothing
// came in - and would get the second one wrong the way the mockup this screen
// replaces did, printing NaN. auraos.lib.finance.profit_and_loss composes the
// two reports server-side and answers null for a margin it cannot measure.
//
// Both sides are cash. Money in is dated by the day it was received, money out
// by the day it was spent, and the basis is read off the payload rather than
// asserted here.
//
// **Margin by job includes the closed ones.** job_profitability defaults to
// open jobs because its first caller was watching work in progress, but a
// margin report is the other question: a closed job's margin is the only one
// that is final, and a ranking without them would rank the studio on its
// unfinished work. They are grouped apart for exactly that reason.
//
// **There is no tax position card**, and its absence is the point. Nothing in
// AuraOS computes a period tax estimate yet - the profit chain that exists is
// per deal and measured against a quote, not per period - so a card here would
// have to be filled with a plausible-looking number nobody computed. Issue
// #109 builds the endpoint; until it lands this screen says what it does not
// know instead of guessing.
//
// Producer-safe by construction. Both endpoints scope to the jobs the session
// may list, and neither payload carries commission, CM, profit before tax,
// TNDN or net profit - the founder's chain lives behind auraos.api.deal_profit
// and no code path here reaches for it.

import { createFileRoute } from "@tanstack/react-router";
import { CalendarRange, Receipt, Scale } from "lucide-react";

import { AppShell } from "@/components/aura/AppShell";
import {
  FinanceRangeBar,
  MonthLabel,
  rangeLabel,
  scaleOf,
  useFinanceRange,
} from "@/components/aura/FinanceRange";
import { Bar, FinanceTabs } from "@/components/aura/FinanceTabs";
import { Card, Money, Pill, Stat, Td, Th } from "@/components/aura/primitives";
import { Figure, QueryState } from "@/components/aura/states";
import { countLabel, percent } from "@/lib/format";
import { useMethod } from "@/lib/queries";

// -- what the server sends --
//
// Pinned by the pure tests in tests/test_finance.py and by the contract test
// in auraos/auraos/doctype/job/test_job_profitability.py. Money is whole
// integer đồng at every level; `margin_pct` is a float that is null - never 0 -
// when there was no revenue to measure a margin against.

export type ProfitAndLossMonth = {
  month: string;
  month_start: string;
  income: number;
  expense: number;
  profit: number;
  margin_pct: number | null;
  income_count: number;
  expense_count: number;
};

export type ProfitAndLossTotal = {
  income: number;
  expense: number;
  profit: number;
  margin_pct: number | null;
  income_count: number;
  expense_count: number;
};

export type ProfitAndLossReport = {
  date_from: string | null;
  date_to: string | null;
  /** "cash". The screen prints the basis it is told, not one it believes. */
  basis: string;
  months: ProfitAndLossMonth[];
  total: ProfitAndLossTotal;
};

export type JobMarginRow = {
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

/**
 * The last stage in auraos.auraos.doctype.job.job.STAGES. A job that has
 * reached it has stopped costing money, so its margin is final rather than
 * provisional - which is the whole distinction this screen draws.
 */
const CLOSED_STAGE = "Complete";

export const Route = createFileRoute("/finance/reports")({
  head: () => ({
    meta: [
      { title: "Reports - profit and loss by month, margin by job | AuraOS" },
      {
        name: "description",
        content:
          "Income against expense for every month in the range, the profit left over, and the margin each closed and open job reached. Cash basis.",
      },
      { property: "og:title", content: "Reports - AuraOS" },
      {
        property: "og:description",
        content: "Profit and loss by month and margin by job, both on a cash basis.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ReportsPage,
});

/**
 * Jobs split by whether they have finished, biggest margin first inside each
 * group. A sort and a partition of the server's own rows - no figure on the
 * screen comes out of this.
 */
function splitByStage(rows: JobMarginRow[]): { closed: JobMarginRow[]; open: JobMarginRow[] } {
  const byMargin = [...rows].sort((a, b) => b.margin - a.margin);
  return {
    closed: byMargin.filter((row) => row.stage === CLOSED_STAGE),
    open: byMargin.filter((row) => row.stage !== CLOSED_STAGE),
  };
}

/** The tone a margin is read in: overspent is the one that needs the eye. */
function marginTone(row: { margin: number; margin_pct: number | null }): string {
  if (row.margin_pct === null) return "neutral";
  return row.margin < 0 ? "ember" : "positive";
}

function MarginGroup({
  rows,
  scale,
  caption,
}: {
  rows: JobMarginRow[];
  scale: number;
  caption: string;
}) {
  if (rows.length === 0) return null;

  return (
    <div className="space-y-4">
      <p className="label-caps">{caption}</p>
      {rows.map((row) => (
        <div key={row.name} className="space-y-1.5">
          <div className="flex flex-wrap items-baseline gap-2">
            <span className="text-sm font-medium">{row.title || row.name}</span>
            <span className="label-caps">{row.client || row.company || row.name}</span>
            <span className="ml-auto">
              <Pill tone={marginTone(row)}>{percent(row.margin_pct)} margin</Pill>
            </span>
          </div>
          <Bar value={row.revenue_ex_vat} max={scale} tone="ink" />
          <Bar value={row.actual_cost} max={scale} tone="ember" />
          <div className="flex flex-wrap justify-between gap-2 text-xs text-muted-foreground">
            <span>
              Revenue <Money value={row.revenue_ex_vat} className="text-foreground" />
            </span>
            <span>
              Spent <Money value={row.actual_cost} className="text-foreground" />
            </span>
            <span>
              Margin{" "}
              <Money
                value={row.margin}
                sign
                className={row.margin < 0 ? "text-ember" : "text-foreground"}
              />
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

function ReportsPage() {
  const [range, setRange] = useFinanceRange();

  const pnl = useMethod<ProfitAndLossReport>("auraos.api.finance_profit_and_loss", {
    date_from: range.from,
    date_to: range.to,
  });
  const margins = useMethod<JobMarginRow[]>("auraos.api.job_profitability", {
    include_closed: 1,
  });

  const report = pnl.data;
  const months = report?.months ?? [];
  const total = report?.total;
  const jobs = margins.data ?? [];
  const { closed, open } = splitByStage(jobs);

  // One scale across both sides of every bar, so a tall revenue bar and a
  // short cost bar underneath it mean what they look like they mean.
  const monthScale = scaleOf(months.flatMap((month) => [month.income, month.expense]));
  const jobScale = scaleOf(jobs.flatMap((row) => [row.revenue_ex_vat, row.actual_cost]));

  return (
    <AppShell
      title="Reports"
      meta={`Cash basis · ${rangeLabel(range)}`}
      actions={
        report ? (
          <Pill tone="ink">{report.basis === "cash" ? "Cash basis" : report.basis}</Pill>
        ) : null
      }
    >
      <div className="space-y-5">
        <FinanceTabs />

        <FinanceRangeBar range={range} onChange={setRange} />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Stat
            label="Collected in range"
            value={
              <Figure query={pnl}>
                <Money value={total?.income ?? 0} />
              </Figure>
            }
            sub={pnl.isSuccess ? countLabel(total?.income_count ?? 0, "payment") : undefined}
          />
          <Stat
            label="Spent in range"
            value={
              <Figure query={pnl}>
                <Money value={total?.expense ?? 0} />
              </Figure>
            }
            sub={pnl.isSuccess ? countLabel(total?.expense_count ?? 0, "expense") : undefined}
          />
          <Stat
            label="Profit"
            value={
              <Figure query={pnl}>
                <Money value={total?.profit ?? 0} sign />
              </Figure>
            }
            sub={pnl.isSuccess ? "Collected less spent" : undefined}
            alert={(total?.profit ?? 0) < 0}
          />
          <Stat
            label="Margin"
            value={
              <Figure query={pnl} width="4rem">
                <span className="num">{percent(total?.margin_pct)}</span>
              </Figure>
            }
            sub={
              pnl.isSuccess
                ? total?.margin_pct === null
                  ? "No money came in, so there is no margin"
                  : "Profit as a share of what came in"
                : undefined
            }
          />
        </div>

        <Card
          title="Profit and loss by month"
          subtitle="Income, expense and the profit left over, every month in the range"
        >
          <QueryState
            query={pnl}
            loadingRows={6}
            isEmpty={() => months.length === 0}
            empty={{
              title: "That range covers no months.",
              detail: "Pick a range that ends on or after the day it starts.",
              icon: <CalendarRange className="size-6" strokeWidth={1.5} />,
            }}
          >
            {() => (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b border-border">
                    <tr>
                      <Th>Month</Th>
                      <Th className="w-full">Income against expense</Th>
                      <Th className="text-right">Income</Th>
                      <Th className="text-right">Expense</Th>
                      <Th className="text-right">Profit</Th>
                      <Th className="text-right">Margin</Th>
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
                            <Bar value={month.income} max={monthScale} tone="ink" />
                            <Bar value={month.expense} max={monthScale} tone="ember" />
                          </div>
                        </Td>
                        <Td className="text-right">
                          <Money
                            value={month.income}
                            className={month.income === 0 ? "text-muted-foreground" : ""}
                          />
                        </Td>
                        <Td className="text-right text-muted-foreground">
                          <Money value={month.expense} />
                        </Td>
                        <Td className="text-right">
                          <Money
                            value={month.profit}
                            sign
                            className={month.profit < 0 ? "text-ember" : ""}
                          />
                        </Td>
                        <Td className="text-right">
                          <Pill
                            tone={marginTone({
                              margin: month.profit,
                              margin_pct: month.margin_pct,
                            })}
                          >
                            {percent(month.margin_pct)}
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
                        <Money value={total?.income ?? 0} />
                      </Td>
                      <Td className="text-right text-muted-foreground">
                        <Money value={total?.expense ?? 0} />
                      </Td>
                      <Td className="text-right">
                        <Money value={total?.profit ?? 0} sign />
                      </Td>
                      <Td className="num text-right">{percent(total?.margin_pct)}</Td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </QueryState>
        </Card>

        <Card
          title="Margin by job"
          subtitle="Revenue against what the job actually spent, closed jobs first"
          action={
            margins.isSuccess ? (
              <span className="label-caps">
                {countLabel(closed.length, "closed job")} · {countLabel(open.length, "open job")}
              </span>
            ) : null
          }
        >
          <QueryState
            query={margins}
            loadingRows={4}
            empty={{
              title: "No jobs to measure yet.",
              detail: "A job gets a margin once it has been quoted and has started spending.",
              icon: <Scale className="size-6" strokeWidth={1.5} />,
            }}
          >
            {() => (
              <div className="space-y-6 p-4">
                <MarginGroup
                  rows={closed}
                  scale={jobScale}
                  caption="Closed jobs · margin is final"
                />
                <MarginGroup
                  rows={open}
                  scale={jobScale}
                  caption="Open jobs · still spending, margin is provisional"
                />
              </div>
            )}
          </QueryState>
        </Card>

        <p className="flex items-start gap-2 rounded-xl border border-border bg-secondary/40 px-4 py-3 text-xs leading-relaxed text-muted-foreground">
          <Receipt className="mt-0.5 size-4 shrink-0" strokeWidth={1.75} />
          <span>
            <strong className="font-medium text-foreground">
              The tax position is not on this screen yet.
            </strong>{" "}
            Nothing in AuraOS works out a TNDN or VAT figure for a period, and a number nobody
            computed is worse than no number at all - it would get filed. When the estimate exists
            it will appear here with the basis it was measured on written next to it.
          </span>
        </p>
      </div>
    </AppShell>
  );
}

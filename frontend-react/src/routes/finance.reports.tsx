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
// **The tax position card is half a card on purpose** (#109). Output VAT for
// the range is a fact and is here. TNDN for the range is not computed at all,
// and the card prints the reason rather than a figure: every expense in AuraOS
// belongs to a job, so a TNDN number from this data would omit every overhead
// and overstate the tax - the plausible-looking number the guidebook refuses,
// and the one that would get filed. What was a whole empty tile is now a
// smaller one that finally says why it is empty.
//
// **The card carries three bases and writes all three down.** Output VAT and
// input VAT are dated by their invoices, because that is the rule for VAT and
// not a preference. Overheads are dated by the day the money left, because
// that is what the record knows and the accountant recognises costs on their
// own basis. Everything else on this screen is cash basis. **Uniformity was
// never the requirement; silence about it was the danger** - a reader
// reconciling any block against Income is told why it will not match before
// they try.
//
// **The decomposition mirrors a tax return's sections on purpose.** The
// founder's reason for wanting the depreciation flag was that they mean to
// hold the accountant's return beside this screen and check it - so flagged
// purchases are a list with a total rather than an invisible subtraction, and
// the blocks are ordered the way the sections are read.
//
// **One derivation, N renderings.** The overhead block comes from
// `auraos.lib.tax.overheads` and nothing here recomputes it. #14's break-even
// screen shows the same money against booked margin and must render this
// endpoint's block rather than sum the table again - two functions over one
// set of rows is how two screens come to disagree, and the disagreement
// always surfaces in front of whoever is reconciling.
//
// Producer-safe by construction, and the tax card does not break that. The two
// original endpoints scope to the jobs the session may list and neither
// payload carries commission, CM, profit before tax, TNDN or net profit. The
// third is founder-only at the server (auraos.api.period_tax_position throws
// for anyone else) and is not even asked for otherwise - the same shape as the
// dashboard's exposure tile, where a producer's missing tile is a fact about
// them rather than an error.

import { createFileRoute } from "@tanstack/react-router";
import { CalendarRange, Scale } from "lucide-react";

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
import { useSession } from "@/components/aura/SessionProvider";
import { Figure, QueryState } from "@/components/aura/states";
import { countLabel, formatDate, percent } from "@/lib/format";
import { useMethod } from "@/lib/queries";

// -- what the server sends --

type VatRate = { vat_pct: number; gross: number; net: number; vat: number; count: number };

type OverheadCategory = { category: string | null; total: number; count: number };

type FlaggedLine = {
  expense: string;
  spent_on: string;
  category: string | null;
  description: string | null;
  amount: number;
};

type TaxPositionPayload = {
  vat: {
    basis: string;
    gross_total: number;
    net_total: number;
    vat_total: number;
    count: number;
    by_rate: VatRate[];
  };
  input_vat: { basis: string; vat_total: number; count: number } | null;
  overheads: {
    basis: string;
    paid_total: number;
    count: number;
    by_category: OverheadCategory[];
    flagged: { total: number; count: number; lines: FlaggedLine[] };
  } | null;
  tndn_component: {
    standing: boolean;
    of: string;
    uncovered_total: number;
    tndn_exposure: number;
    rate_pct: number;
  } | null;
  not_computed: { figure: string; why: string }[];
};
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
  const session = useSession();

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

        {session.isFounder ? <TaxPosition range={range} /> : null}
      </div>
    </AppShell>
  );
}

/**
 * The period's tax position: the half that is a fact, and the half that is
 * named rather than guessed.
 *
 * Founder-only, and the caller decides whether to render it at all - the
 * server refuses anyone else outright, so asking on a producer's behalf would
 * be a guaranteed 403 on every visit to this screen.
 */
function TaxPosition({ range }: { range: { from: string; to: string } }) {
  const position = useMethod<TaxPositionPayload>("auraos.api.period_tax_position", {
    date_from: range.from,
    date_to: range.to,
  });

  return (
    <Card
      title="Tax position"
      subtitle="Output VAT for the range, and what is still not worked out"
    >
      <QueryState query={position} isEmpty={() => false} loadingRows={2}>
        {(data) => (
          <div className="space-y-4 p-4">
            <div className="grid gap-4 sm:grid-cols-3">
              <Stat label="Output VAT" value={<Money value={data.vat.vat_total} />} />
              <Stat label="Invoiced before VAT" value={<Money value={data.vat.net_total} />} />
              <Stat label="Invoices issued" value={countLabel(data.vat.count, "invoice")} />
            </div>

            {/* The basis, on the card's face rather than in a tooltip. Every
                other figure on this screen is cash basis; this one cannot be,
                and a reader comparing it against Income needs to know that
                before they start rather than after. */}
            <p className="text-xs leading-relaxed text-muted-foreground">
              <strong className="font-medium text-foreground">Not the cash basis</strong> the rest
              of this screen uses: {data.vat.basis}.
            </p>

            {/* Broken out by rate because a return is filed per rate, and one
                summed figure cannot be checked against one. */}
            {data.vat.by_rate.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b border-border">
                    <tr>
                      <Th>VAT rate</Th>
                      <Th className="text-right">Invoices</Th>
                      <Th className="text-right">Before VAT</Th>
                      <Th className="text-right">VAT</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data.vat.by_rate.map((row) => (
                      <tr key={row.vat_pct}>
                        <Td className="num">{percent(row.vat_pct)}</Td>
                        <Td className="num text-right text-xs text-muted-foreground">
                          {row.count}
                        </Td>
                        <Td className="text-right">
                          <Money value={row.net} />
                        </Td>
                        <Td className="text-right">
                          <Money value={row.vat} />
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}

            {/* The other side of the same return: VAT the company was
                charged. Invoice-dated like the block above, and labelled
                as overheads only - job spending carries no VAT fields, so
                this is not everything the company could deduct. */}
            {data.input_vat ? (
              <div className="border-t border-border pt-3">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="label-caps">Input VAT on overheads</span>
                  <span className="text-xs text-muted-foreground">
                    {countLabel(data.input_vat.count, "invoice")}
                  </span>
                </div>
                <div className="mt-1">
                  <Money value={data.input_vat.vat_total} />
                </div>
                <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                  {data.input_vat.basis}.
                </p>
              </div>
            ) : null}

            {/* What the company spent on itself. **A third basis, and the
                card says so** - this one is dated by the day the money
                left, because that is what the record knows; the two VAT
                blocks are dated by their invoices because that is the
                rule for VAT. One basis per figure, every basis written. */}
            {data.overheads ? (
              <div className="border-t border-border pt-3">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="label-caps">Overheads paid</span>
                  <span className="text-xs text-muted-foreground">
                    {countLabel(data.overheads.count, "payment")}
                  </span>
                </div>
                <div className="mt-1">
                  <Money value={data.overheads.paid_total} />
                </div>
                <p className="mt-1 mb-2 text-xs leading-relaxed text-muted-foreground">
                  {data.overheads.basis}.
                </p>

                {data.overheads.by_category.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="border-b border-border">
                        <tr>
                          <Th className="w-full">Category</Th>
                          <Th className="text-right">Payments</Th>
                          <Th className="text-right">Paid</Th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {data.overheads.by_category.map((row) => (
                          <tr key={row.category ?? "uncategorised"}>
                            {/* A payment nobody has classified is shown as
                                that, not dropped - dropping it would make
                                this disagree with the bank by exactly the
                                money nobody has got to yet. */}
                            <Td>{row.category ?? "Uncategorised"}</Td>
                            <Td className="num text-right text-xs text-muted-foreground">
                              {row.count}
                            </Td>
                            <Td className="text-right">
                              <Money value={row.total} />
                            </Td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}

                {/* Listed, never merely subtracted. The founder means to
                    hold the accountant's return beside this and check it
                    line by line, and an invisible subtraction cannot be
                    checked against anything. */}
                {data.overheads.flagged.count > 0 ? (
                  <div className="mt-3 rounded-xl border border-border bg-secondary/40 px-4 py-3">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <span className="label-caps">Flagged for depreciation</span>
                      <span className="text-xs text-muted-foreground">
                        left out of the total above
                      </span>
                    </div>
                    <div className="mt-1">
                      <Money value={data.overheads.flagged.total} />
                    </div>
                    <ul className="mt-2 space-y-1">
                      {data.overheads.flagged.lines.map((line) => (
                        <li
                          key={line.expense}
                          className="flex flex-wrap items-baseline justify-between gap-2 text-xs text-muted-foreground"
                        >
                          <span>
                            <span className="num">{formatDate(line.spent_on)}</span>{" "}
                            {line.description || line.category || line.expense}
                          </span>
                          <Money value={line.amount} />
                        </li>
                      ))}
                    </ul>
                    <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                      Marked to be depreciated rather than expensed now. The accountant may treat
                      them differently - these are listed so the two can be compared, not to decide
                      the answer.
                    </p>
                  </div>
                ) : null}
              </div>
            ) : null}

            {/* Standing, not for the range - and drawn apart from the figures
                above rather than beside them, because an uncovered payment is
                carried from the day it was made until an invoice turns up. Put
                on one axis with a period figure it would read as comparable
                and is not. */}
            {data.tndn_component ? (
              <div className="rounded-xl border border-border bg-secondary/40 px-4 py-3">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="label-caps">TNDN exposure carried now</span>
                  <Pill tone="outline">Not for this range</Pill>
                </div>
                <div className="mt-1 flex flex-wrap items-baseline gap-2">
                  <Money value={data.tndn_component.tndn_exposure} className="text-ember" />
                  <span className="text-xs text-muted-foreground">
                    on <Money value={data.tndn_component.uncovered_total} /> of{" "}
                    {data.tndn_component.of}
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  A component of a TNDN position, not a position: it is the tax on spending that
                  cannot be deducted, which is one input to a figure this screen does not compute.
                </p>
              </div>
            ) : null}

            {/* The gap, in the server's words rather than this file's - the
                list shrinks as tickets land, and a screen that kept its own
                copy would go on describing a hole somebody had filled. */}
            <div className="border-t border-border pt-3">
              <p className="label-caps mb-2">Not worked out here</p>
              <ul className="space-y-1.5">
                {data.not_computed.map((row) => (
                  <li key={row.figure} className="text-xs leading-relaxed text-muted-foreground">
                    <strong className="font-medium text-foreground">{row.figure}</strong> -{" "}
                    {row.why}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </QueryState>
    </Card>
  );
}

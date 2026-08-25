// Money out, on real data.
//
// One read: auraos.api.finance_expenses(date_from, date_to). It returns every
// month in the range - the empty ones included, zero-filled on purpose so a
// chart cannot quietly lose a month - with the categories spent in it, the
// split between company money and somebody's own float, and a rollup of both
// across the whole range.
//
// This is job spend. Overhead has no home in the model yet, so an expense
// exists only against a job, and the screen says as much rather than implying
// it has seen every đồng that left the company.

import { createFileRoute } from "@tanstack/react-router";
import { CalendarRange, Wallet } from "lucide-react";
import { useState } from "react";

import { AppShell } from "@/components/aura/AppShell";
import { Bar, FinanceTabs } from "@/components/aura/FinanceTabs";
import {
  FinanceRangeBar,
  MonthLabel,
  rangeLabel,
  scaleOf,
  useFinanceRange,
  type ExpenseMonth,
  type ExpenseReport,
  type PaidFromSplit,
} from "@/components/aura/FinanceRange";
import { Card, Money, Stat, Td, Th } from "@/components/aura/primitives";
import { Figure, QueryState } from "@/components/aura/states";
import { countLabel } from "@/lib/format";
import { useMethod } from "@/lib/queries";

export const Route = createFileRoute("/finance/expenses")({
  head: () => ({
    meta: [
      { title: "Expenses - money out, by month and by category | AuraOS" },
      {
        name: "description",
        content:
          "Job spend per calendar month and per category, with the split between company money and money somebody advanced out of their own float.",
      },
      { property: "og:title", content: "Expenses - AuraOS" },
      {
        property: "og:description",
        content: "Job spend per month and per category, and whose money paid for it.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ExpensesPage,
});

const EMPTY_SPLIT: PaidFromSplit = { Company: 0, Advance: 0 };

/** The month worth opening on: the latest one anybody spent in. */
function defaultMonth(months: ExpenseMonth[]): ExpenseMonth | null {
  for (let i = months.length - 1; i >= 0; i -= 1) {
    const month = months[i];
    if (month && month.count > 0) return month;
  }
  return months[months.length - 1] ?? null;
}

/**
 * One month's spend as two segments: the company's own money and somebody's
 * float. Both widths come straight off the payload; nothing is added up here,
 * the segments are simply drawn against the biggest month in the range.
 */
function SplitBar({ split, max }: { split: PaidFromSplit; max: number }) {
  const width = (value: number) => (max > 0 ? `${Math.min(100, (value / max) * 100)}%` : "0%");
  return (
    <div className="flex h-2 w-full overflow-hidden rounded-full bg-secondary">
      <div className="h-full bg-primary" style={{ width: width(split.Company) }} />
      <div className="h-full bg-ember" style={{ width: width(split.Advance) }} />
    </div>
  );
}

function SplitKey() {
  return (
    <div className="flex flex-wrap items-center gap-4 border-t border-border px-4 py-3 text-xs text-muted-foreground">
      <span className="inline-flex items-center gap-1.5">
        <span className="size-2 rounded-full bg-primary" /> Company money
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="size-2 rounded-full bg-ember" /> Someone&apos;s own money (float)
      </span>
    </div>
  );
}

function ExpensesPage() {
  const [range, setRange] = useFinanceRange();
  const [picked, setPicked] = useState<string | null>(null);

  const expenses = useMethod<ExpenseReport>("auraos.api.finance_expenses", {
    date_from: range.from,
    date_to: range.to,
  });

  const report = expenses.data;
  const months = report?.months ?? [];
  const selected = months.find((month) => month.month === picked) ?? defaultMonth(months);
  const split = report?.paid_from ?? EMPTY_SPLIT;
  const categories = report?.categories ?? [];
  const biggest = categories[0] ?? null;

  const monthScale = scaleOf(months.map((month) => month.total));
  const categoryScale = scaleOf(categories.map((row) => row.total));
  const monthCategoryScale = scaleOf((selected?.categories ?? []).map((row) => row.total));

  return (
    <AppShell title="Expenses" meta={`Job spend · ${rangeLabel(range)}`}>
      <div className="space-y-5">
        <FinanceTabs />

        <FinanceRangeBar range={range} onChange={setRange} />

        <p className="flex items-start gap-2 rounded-xl border border-border bg-secondary/40 px-4 py-3 text-xs leading-relaxed text-muted-foreground">
          <Wallet className="mt-0.5 size-4 shrink-0" strokeWidth={1.75} />
          <span>
            Every cost logged against a job, dated by the day it was spent. Studio overhead is not
            in here yet - it has nowhere to live in the model, so this is job spend and only job
            spend.
          </span>
        </p>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Stat
            label="Spent in range"
            value={
              <Figure query={expenses}>
                <Money value={report?.total ?? 0} />
              </Figure>
            }
            sub={expenses.isSuccess ? countLabel(report?.count ?? 0, "expense") : undefined}
          />
          <Stat
            label="Company money"
            value={
              <Figure query={expenses}>
                <Money value={split.Company} />
              </Figure>
            }
            sub="Paid to the vendor by the company"
          />
          <Stat
            label="Someone's own money"
            value={
              <Figure query={expenses}>
                <Money value={split.Advance} />
              </Figure>
            }
            sub="Spent out of a float being held"
            alert={split.Advance > 0}
          />
          <Stat
            label="Biggest category"
            value={
              <Figure query={expenses}>
                <Money value={biggest?.total ?? 0} />
              </Figure>
            }
            sub={
              expenses.isSuccess ? (biggest?.category ?? "Nothing spent in this range") : undefined
            }
          />
        </div>

        <Card
          title="Spend by month"
          subtitle="Every month in the range, including the empty ones"
          action={
            selected ? (
              <span className="label-caps">Showing detail for {selected.month}</span>
            ) : null
          }
        >
          <QueryState
            query={expenses}
            loadingRows={6}
            isEmpty={() => months.length === 0}
            empty={{
              title: "That range covers no months.",
              detail: "Pick a range that ends on or after the day it starts.",
              icon: <CalendarRange className="size-6" strokeWidth={1.5} />,
            }}
          >
            {() => (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="border-b border-border">
                      <tr>
                        <Th>Month</Th>
                        <Th className="w-full">Whose money</Th>
                        <Th className="text-right">Company</Th>
                        <Th className="text-right">Own money</Th>
                        <Th className="text-right">Entries</Th>
                        <Th className="text-right">Total</Th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {months.map((month) => (
                        <tr
                          key={month.month}
                          onClick={() => setPicked(month.month)}
                          className={`cursor-pointer transition-colors hover:bg-secondary/50 ${
                            selected?.month === month.month ? "bg-secondary/60" : ""
                          }`}
                        >
                          <Td className="whitespace-nowrap">
                            <MonthLabel month={month.month} />
                          </Td>
                          <Td>
                            <SplitBar split={month.paid_from} max={monthScale} />
                          </Td>
                          <Td className="text-right text-xs text-muted-foreground">
                            <Money value={month.paid_from.Company} />
                          </Td>
                          <Td className="text-right text-xs text-muted-foreground">
                            <Money value={month.paid_from.Advance} />
                          </Td>
                          <Td className="num text-right text-xs text-muted-foreground">
                            {month.count}
                          </Td>
                          <Td className="text-right">
                            <Money
                              value={month.total}
                              className={month.total === 0 ? "text-muted-foreground" : ""}
                            />
                          </Td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="border-t border-border">
                      <tr>
                        <Td className="label-caps">Range</Td>
                        <Td />
                        <Td className="text-right text-xs">
                          <Money value={split.Company} />
                        </Td>
                        <Td className="text-right text-xs">
                          <Money value={split.Advance} />
                        </Td>
                        <Td className="num text-right text-xs text-muted-foreground">
                          {report?.count ?? 0}
                        </Td>
                        <Td className="text-right font-semibold">
                          <Money value={report?.total ?? 0} />
                        </Td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
                <SplitKey />
              </>
            )}
          </QueryState>
        </Card>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Where the money went" subtitle="Category rollup across the whole range">
            <QueryState
              query={expenses}
              loadingRows={5}
              isEmpty={() => categories.length === 0}
              empty={{ title: "Nothing was spent in this range." }}
            >
              {() => (
                <div className="space-y-3 p-4">
                  {categories.map((row) => (
                    <div
                      key={row.category}
                      className="grid grid-cols-[9rem_1fr_auto] items-center gap-3"
                    >
                      <div className="truncate text-sm" title={row.category}>
                        {row.category}
                      </div>
                      <Bar value={row.total} max={categoryScale} tone="muted" />
                      <Money value={row.total} className="w-36 text-right text-xs" />
                    </div>
                  ))}
                </div>
              )}
            </QueryState>
          </Card>

          <Card
            title={selected ? `Inside ${selected.month}` : "Inside the month"}
            subtitle="Categories spent in the month picked above"
          >
            <QueryState
              query={expenses}
              loadingRows={5}
              isEmpty={() => (selected?.categories.length ?? 0) === 0}
              empty={{
                title: selected
                  ? `Nothing was spent in ${selected.month}.`
                  : "Nothing spent in this range.",
                detail: "Pick another month above, or widen the range.",
              }}
            >
              {() => (
                <>
                  <table className="w-full">
                    <thead className="border-b border-border">
                      <tr>
                        <Th>Category</Th>
                        <Th className="w-full">Share of the month</Th>
                        <Th className="text-right">Spent</Th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {(selected?.categories ?? []).map((row) => (
                        <tr key={row.category} className="hover:bg-secondary/50">
                          <Td>
                            <span className="block max-w-[10rem] truncate" title={row.category}>
                              {row.category}
                            </span>
                          </Td>
                          <Td>
                            <Bar value={row.total} max={monthCategoryScale} tone="muted" />
                          </Td>
                          <Td className="text-right">
                            <Money value={row.total} />
                          </Td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-4 py-3 text-xs">
                    <span className="text-muted-foreground">
                      Company money <Money value={selected?.paid_from.Company ?? 0} />
                    </span>
                    <span className="text-muted-foreground">
                      Own money <Money value={selected?.paid_from.Advance ?? 0} />
                    </span>
                  </div>
                </>
              )}
            </QueryState>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}

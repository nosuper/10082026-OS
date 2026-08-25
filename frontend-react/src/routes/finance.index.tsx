// The finance dashboard: money in against money out, month by month.
//
// Two reads, both range reports, both sharing their range with the Income and
// Expenses tabs: auraos.api.finance_income and auraos.api.finance_expenses.
// The args are the cache key, so opening this screen after Income costs one
// request rather than two.
//
// What is deliberately not here: cash on hand, receivables ageing, payables,
// profit and margin. No endpoint serves any of them, and this screen will not
// be the place that invents a profit figure by subtracting one payload from
// another. Money in and money out are what the server can answer, so money in
// and money out are what it shows.

import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowUpRight, CalendarRange } from "lucide-react";

import { AppShell } from "@/components/aura/AppShell";
import { Bar, FinanceTabs } from "@/components/aura/FinanceTabs";
import {
  FinanceRangeBar,
  MonthLabel,
  rangeLabel,
  scaleOf,
  useFinanceRange,
  type ExpenseReport,
  type IncomeMonth,
  type IncomeReport,
  type PaidFromSplit,
} from "@/components/aura/FinanceRange";
import { Card, Money, Pill, Stat } from "@/components/aura/primitives";
import { Figure, QueryState, QueryStates } from "@/components/aura/states";
import { countLabel } from "@/lib/format";
import { useMethod } from "@/lib/queries";

export const Route = createFileRoute("/finance/")({
  head: () => ({
    meta: [
      { title: "Finance - money in and money out by month | AuraOS" },
      {
        name: "description",
        content:
          "Cash collected against job spend, month by month, with a category rollup and the clients who paid. Cash basis.",
      },
      { property: "og:title", content: "Finance - AuraOS" },
      {
        property: "og:description",
        content: "Cash collected against job spend, month by month.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: FinanceDashboard,
});

const EMPTY_SPLIT: PaidFromSplit = { Company: 0, Advance: 0 };

/** The last month anybody was paid in, for the client card. */
function latestPaidMonth(months: IncomeMonth[]): IncomeMonth | null {
  for (let i = months.length - 1; i >= 0; i -= 1) {
    const month = months[i];
    if (month && month.clients.length > 0) return month;
  }
  return null;
}

function FinanceDashboard() {
  const [range, setRange] = useFinanceRange();
  const args = { date_from: range.from, date_to: range.to };

  const income = useMethod<IncomeReport>("auraos.api.finance_income", args);
  const expenses = useMethod<ExpenseReport>("auraos.api.finance_expenses", args);

  const inMonths = income.data?.months ?? [];
  const outMonths = expenses.data?.months ?? [];
  const split = expenses.data?.paid_from ?? EMPTY_SPLIT;
  const categories = expenses.data?.categories ?? [];
  const clientMonth = latestPaidMonth(inMonths);

  // The two series share one scale so a taller bar really is more money.
  const scale = scaleOf([
    ...inMonths.map((month) => month.total),
    ...outMonths.map((month) => month.total),
  ]);
  const categoryScale = scaleOf(categories.map((row) => row.total));
  const clientScale = scaleOf((clientMonth?.clients ?? []).map((row) => row.total));

  // Both reports walk the same range, so the months line up by index. Pairing
  // them is a join, not a calculation: each figure is still the server's.
  const rows = inMonths.map((month, index) => ({
    month: month.month,
    income: month.total,
    expense: outMonths[index]?.total ?? 0,
  }));

  return (
    <AppShell
      title="Finance"
      meta={`Cash basis · ${rangeLabel(range)}`}
      actions={
        <Link
          to="/finance/income"
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          Income detail <ArrowUpRight className="size-3.5" />
        </Link>
      }
    >
      <div className="space-y-5">
        <FinanceTabs />

        <FinanceRangeBar range={range} onChange={setRange} />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Stat
            label="Money in"
            value={
              <Figure query={income}>
                <Money value={income.data?.total ?? 0} />
              </Figure>
            }
            sub={
              income.isSuccess
                ? `${countLabel(income.data?.count ?? 0, "payment")} collected`
                : undefined
            }
          />
          <Stat
            label="Money out"
            value={
              <Figure query={expenses}>
                <Money value={expenses.data?.total ?? 0} />
              </Figure>
            }
            sub={
              expenses.isSuccess
                ? `${countLabel(expenses.data?.count ?? 0, "expense")} on jobs`
                : undefined
            }
          />
          <Stat
            label="Company money out"
            value={
              <Figure query={expenses}>
                <Money value={split.Company} />
              </Figure>
            }
            sub="Paid to the vendor by the company"
          />
          <Stat
            label="Own money out"
            value={
              <Figure query={expenses}>
                <Money value={split.Advance} />
              </Figure>
            }
            sub="Spent out of a float being held"
            alert={split.Advance > 0}
          />
        </div>

        <Card
          title="Money in and money out"
          subtitle="By calendar month. Income is cash collected; spend is what jobs cost."
          action={<Pill tone="ink">Cash basis</Pill>}
        >
          <QueryStates
            queries={[income, expenses]}
            loadingRows={6}
            isEmpty={() => rows.length === 0}
            empty={{
              title: "That range covers no months.",
              detail: "Pick a range that ends on or after the day it starts.",
              icon: <CalendarRange className="size-6" strokeWidth={1.5} />,
            }}
          >
            {() => (
              <div className="space-y-3 p-4">
                {rows.map((row) => (
                  <div
                    key={row.month}
                    className="grid grid-cols-[4rem_1fr_auto] items-center gap-3"
                  >
                    <MonthLabel month={row.month} />
                    <div className="space-y-1">
                      <Bar value={row.income} max={scale} tone="ink" />
                      <Bar value={row.expense} max={scale} tone="ember" />
                    </div>
                    <div className="w-40 space-y-1 text-right">
                      <Money
                        value={row.income}
                        className={`block text-xs ${row.income === 0 ? "text-muted-foreground" : ""}`}
                      />
                      <Money
                        value={row.expense}
                        className={`block text-xs ${row.expense === 0 ? "text-muted-foreground" : "text-ember"}`}
                      />
                    </div>
                  </div>
                ))}
                <div className="flex flex-wrap items-center gap-4 border-t border-border pt-3 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1.5">
                    <span className="size-2 rounded-full bg-primary" /> Money in
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="size-2 rounded-full bg-ember" /> Money out
                  </span>
                  <span>Empty months are shown as zero, not dropped.</span>
                </div>
              </div>
            )}
          </QueryStates>
        </Card>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card
            title="Where the money goes"
            subtitle="Job spend by category across the range"
            action={
              <Link
                to="/finance/expenses"
                className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-ember"
              >
                Expenses <ArrowUpRight className="size-3.5" />
              </Link>
            }
          >
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
            title={clientMonth ? `Who paid us in ${clientMonth.month}` : "Who paid us"}
            subtitle="The latest month money arrived in"
            action={
              <Link
                to="/finance/income"
                className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-ember"
              >
                Income <ArrowUpRight className="size-3.5" />
              </Link>
            }
          >
            <QueryState
              query={income}
              loadingRows={4}
              isEmpty={() => !clientMonth}
              empty={{
                title: "Nobody has paid us in this range.",
                detail: "A milestone counts here on the day it is marked paid.",
              }}
            >
              {() => (
                <div className="space-y-3 p-4">
                  {(clientMonth?.clients ?? []).map((row) => (
                    <div
                      key={row.company ?? "unknown"}
                      className="grid grid-cols-[9rem_1fr_auto] items-center gap-3"
                    >
                      <div
                        className="truncate text-sm"
                        title={row.company_name ?? row.company ?? ""}
                      >
                        {row.company_name || row.company || "Unknown client"}
                      </div>
                      <Bar value={row.total} max={clientScale} tone="ink" />
                      <Money value={row.total} className="w-36 text-right text-xs" />
                    </div>
                  ))}
                </div>
              )}
            </QueryState>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}

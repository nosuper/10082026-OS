// Money in, on real data.
//
// One read: auraos.api.finance_income(date_from, date_to). It answers the
// whole screen - months, a per-client breakdown inside each month, and the
// range total - so there is nothing here to add up and nothing to derive.
//
// The basis is cash and the payload says so. A milestone counts on the day it
// was recorded paid, never the day it fell due and never the day an invoice
// was issued, and the banner at the top of this screen reads that claim off
// `basis` rather than asserting it on its own authority.

import { createFileRoute } from "@tanstack/react-router";
import { Banknote, CalendarRange, TrendingDown, TrendingUp } from "lucide-react";
import { useState } from "react";

import { AppShell } from "@/components/aura/AppShell";
import { Bar, FinanceTabs } from "@/components/aura/FinanceTabs";
import {
  FinanceRangeBar,
  MonthLabel,
  rangeLabel,
  scaleOf,
  useFinanceRange,
  type IncomeMonth,
  type IncomeReport,
} from "@/components/aura/FinanceRange";
import { Card, Money, Pill, Stat, Td, Th } from "@/components/aura/primitives";
import { Figure, QueryState } from "@/components/aura/states";
import { countLabel } from "@/lib/format";
import { useMethod } from "@/lib/queries";

export const Route = createFileRoute("/finance/income")({
  head: () => ({
    meta: [
      { title: "Income - money collected, by month and by client | AuraOS" },
      {
        name: "description",
        content:
          "Cash collected per calendar month, broken down by client. Cash basis: dated by the day the money was received.",
      },
      { property: "og:title", content: "Income - AuraOS" },
      {
        property: "og:description",
        content: "Cash collected per month and per client, on a cash basis.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: IncomePage,
});

/** The month a founder is looking at: the latest one money actually arrived in. */
function defaultMonth(months: IncomeMonth[]): IncomeMonth | null {
  for (let i = months.length - 1; i >= 0; i -= 1) {
    const month = months[i];
    if (month && month.count > 0) return month;
  }
  return months[months.length - 1] ?? null;
}

/** The fattest month in the range. A pick, not a calculation. */
function bestMonth(months: IncomeMonth[]): IncomeMonth | null {
  let best: IncomeMonth | null = null;
  for (const month of months) {
    if (month.count > 0 && (!best || month.total > best.total)) best = month;
  }
  return best;
}

/**
 * Better or worse than the month before, as a direction and nothing else.
 * The two figures are both printed on the screen; the app does not print a
 * difference it worked out itself.
 */
function Direction({ months, at }: { months: IncomeMonth[]; at: number }) {
  const here = months[at];
  const before = months[at - 1];
  if (!here || !before || here.total === before.total) return null;
  const up = here.total > before.total;
  const Icon = up ? TrendingUp : TrendingDown;
  return (
    <Icon
      className={`inline-block size-3.5 ${up ? "text-positive" : "text-ember"}`}
      strokeWidth={2}
      aria-label={up ? `up on ${before.month}` : `down on ${before.month}`}
    />
  );
}

function IncomePage() {
  const [range, setRange] = useFinanceRange();
  const [picked, setPicked] = useState<string | null>(null);

  const income = useMethod<IncomeReport>("auraos.api.finance_income", {
    date_from: range.from,
    date_to: range.to,
  });

  const report = income.data;
  const months = report?.months ?? [];
  const selected = months.find((month) => month.month === picked) ?? defaultMonth(months);
  const top = bestMonth(months);
  const scale = scaleOf(months.map((month) => month.total));
  const clientScale = scaleOf((selected?.clients ?? []).map((row) => row.total));

  return (
    <AppShell
      title="Income"
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

        <p className="flex items-start gap-2 rounded-xl border border-border bg-secondary/40 px-4 py-3 text-xs leading-relaxed text-muted-foreground">
          <Banknote className="mt-0.5 size-4 shrink-0" strokeWidth={1.75} />
          <span>
            <strong className="font-medium text-foreground">
              {report && report.basis !== "cash" ? report.basis : "Cash basis"}.
            </strong>{" "}
            This is money actually collected, dated by the day it was received - not the day it was
            invoiced and not the day it fell due. It is the only figure the studio can spend.
          </span>
        </p>

        <div className="grid gap-3 sm:grid-cols-3">
          <Stat
            label="Collected in range"
            value={
              <Figure query={income}>
                <Money value={report?.total ?? 0} />
              </Figure>
            }
            sub={income.isSuccess ? countLabel(report?.count ?? 0, "payment") : undefined}
          />
          <Stat
            label="Best month"
            value={
              <Figure query={income}>
                <Money value={top?.total ?? 0} />
              </Figure>
            }
            sub={
              income.isSuccess
                ? top
                  ? `${top.month} · ${countLabel(top.count, "payment")}`
                  : "No money collected in this range"
                : undefined
            }
          />
          <Stat
            label="Months in range"
            value={
              <Figure query={income} width="3rem">
                <span className="num">{months.length}</span>
              </Figure>
            }
            sub={
              income.isSuccess
                ? `${countLabel(months.filter((m) => m.count > 0).length, "month")} with money in`
                : undefined
            }
          />
        </div>

        <Card
          title="Collected by month"
          subtitle="Every month in the range, including the empty ones"
          action={
            selected ? (
              <span className="label-caps">Showing clients for {selected.month}</span>
            ) : null
          }
        >
          <QueryState
            query={income}
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
                      <Th className="w-full">Collected</Th>
                      <Th className="text-right">Payments</Th>
                      <Th className="text-right">Total</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {months.map((month, index) => (
                      <tr
                        key={month.month}
                        onClick={() => setPicked(month.month)}
                        className={`cursor-pointer transition-colors hover:bg-secondary/50 ${
                          selected?.month === month.month ? "bg-secondary/60" : ""
                        }`}
                      >
                        <Td className="whitespace-nowrap">
                          <MonthLabel month={month.month} />{" "}
                          <Direction months={months} at={index} />
                        </Td>
                        <Td>
                          <Bar value={month.total} max={scale} tone="ink" />
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
            )}
          </QueryState>
        </Card>

        <Card
          title={selected ? `Who paid us in ${selected.month}` : "Who paid us"}
          subtitle="Collected per client, biggest first"
        >
          <QueryState
            query={income}
            loadingRows={4}
            isEmpty={() => (selected?.clients.length ?? 0) === 0}
            empty={{
              title: selected
                ? `No money was collected in ${selected.month}.`
                : "Nothing collected in this range.",
              detail: "Pick another month above, or widen the range.",
            }}
          >
            {() => (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b border-border">
                    <tr>
                      <Th>Client</Th>
                      <Th className="w-full">Share of the month</Th>
                      <Th className="text-right">Payments</Th>
                      <Th className="text-right">Collected</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {(selected?.clients ?? []).map((row) => (
                      <tr key={row.company ?? "unknown"} className="hover:bg-secondary/50">
                        <Td className="whitespace-nowrap">
                          <div className="font-medium">
                            {row.company_name || row.company || "Unknown client"}
                          </div>
                          {row.company ? (
                            <div className="num text-[11px] text-muted-foreground">
                              {row.company}
                            </div>
                          ) : null}
                        </Td>
                        <Td>
                          <Bar value={row.total} max={clientScale} tone="ink" />
                        </Td>
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
            )}
          </QueryState>
        </Card>
      </div>
    </AppShell>
  );
}

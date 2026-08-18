import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { AppShell } from "@/components/aura/AppShell";
import { Card, Money, Pill, Stat, Td, Th } from "@/components/aura/primitives";
import { Bar, FinanceTabs } from "@/components/aura/FinanceTabs";
import { cashAccounts, forecast, monthly, sum } from "@/data/finance";

export const Route = createFileRoute("/finance/forecast")({
  head: () => ({
    meta: [
      { title: "Cash forecast — pipeline, runway and scenarios | AuraOS" },
      {
        name: "description",
        content:
          "Projected income from committed jobs and weighted pipeline, month-by-month cash balance and runway scenarios.",
      },
      { property: "og:title", content: "Cash forecast — AuraOS" },
      {
        property: "og:description",
        content: "Committed vs weighted pipeline, projected cash balance and runway.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ForecastPage,
});

const scenarios = [
  { key: "conservative", label: "Conservative", factor: 0.5, note: "Only half the weighted pipeline lands" },
  { key: "base", label: "Base case", factor: 1, note: "Pipeline lands at its current confidence" },
  { key: "upside", label: "Upside", factor: 1.35, note: "Tết season overdelivers" },
] as const;

function ForecastPage() {
  const [scenarioKey, setScenarioKey] = useState<(typeof scenarios)[number]["key"]>("base");
  const scenario = scenarios.find((s) => s.key === scenarioKey)!;

  const opening = sum(cashAccounts.map((a) => a.balance));
  let running = opening;
  const projected = forecast.map((f) => {
    const income = f.committed + Math.round(f.weighted * scenario.factor);
    const net = income - f.expense;
    running += net;
    return { ...f, income, net, balance: running };
  });

  const maxIncome = Math.max(...projected.map((p) => Math.max(p.income, p.expense)));
  const totalIncome = sum(projected.map((p) => p.income));
  const totalExpense = sum(projected.map((p) => p.expense));
  const closing = projected.at(-1)?.balance ?? opening;
  const avgBurn = Math.round(totalExpense / projected.length);
  const runway = Math.round((closing / avgBurn) * 10) / 10;
  const lowest = Math.min(...projected.map((p) => p.balance));
  const run8 = sum(monthly.map((m) => m.income));

  return (
    <AppShell
      title="Forecast"
      meta="Sep–Dec 2026 · committed jobs + weighted pipeline"
      actions={
        <div className="flex gap-1">
          {scenarios.map((s) => (
            <button
              key={s.key}
              onClick={() => setScenarioKey(s.key)}
              className={`rounded-lg border px-3 py-2 text-xs transition-colors ${
                scenarioKey === s.key
                  ? "border-transparent bg-primary text-primary-foreground"
                  : "border-border bg-card text-muted-foreground hover:text-foreground"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      }
    >
      <div className="space-y-5">
        <FinanceTabs />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Stat label="Opening cash" value={<Money value={opening} />} sub="1 Sep 2026" />
          <Stat
            label="Projected income"
            value={<Money value={totalIncome} />}
            sub={`${scenario.label} · vs ${new Intl.NumberFormat("vi-VN").format(run8)} ₫ Jan–Aug`}
          />
          <Stat label="Closing cash" value={<Money value={closing} />} sub="31 Dec 2026" />
          <Stat
            label="Runway"
            value={<span>{runway} tháng</span>}
            sub={`Avg burn ${new Intl.NumberFormat("vi-VN").format(avgBurn)} ₫/tháng`}
            alert={runway < 3}
          />
        </div>

        <Card
          title="Projected cash flow"
          subtitle={scenario.note}
          action={
            <Pill tone={lowest > 0 ? "positive" : "ember"}>
              {lowest > 0 ? "Never goes negative" : "Cash dips below zero"}
            </Pill>
          }
        >
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-border">
                <tr>
                  <Th>Month</Th>
                  <Th className="text-right">Committed</Th>
                  <Th className="text-right">Weighted pipeline</Th>
                  <Th>Confidence</Th>
                  <Th className="text-right">Expense</Th>
                  <Th className="text-right">Net</Th>
                  <Th className="text-right">Cash balance</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {projected.map((p) => (
                  <tr key={p.month} className="hover:bg-secondary/50">
                    <Td className="font-medium">{p.month} 2026</Td>
                    <Td className="text-right">
                      <Money value={p.committed} />
                    </Td>
                    <Td className="text-right text-muted-foreground">
                      <Money value={Math.round(p.weighted * scenario.factor)} />
                    </Td>
                    <Td>
                      <Pill tone={p.confidence >= 0.6 ? "positive" : "ember"}>
                        {Math.round(p.confidence * 100)}%
                      </Pill>
                    </Td>
                    <Td className="text-right text-muted-foreground">
                      <Money value={p.expense} />
                    </Td>
                    <Td className="text-right">
                      <Money value={p.net} className={p.net < 0 ? "text-ember" : ""} sign />
                    </Td>
                    <Td className="text-right font-medium">
                      <Money value={p.balance} className={p.balance < 0 ? "text-ember" : ""} />
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Income vs expense, projected" subtitle="Sep–Dec 2026">
            <div className="space-y-3 p-4">
              {projected.map((p) => (
                <div key={p.month} className="grid grid-cols-[2.5rem_1fr_auto] items-center gap-3">
                  <div className="label-caps">{p.month}</div>
                  <div className="space-y-1">
                    <Bar value={p.income} max={maxIncome} tone="ink" />
                    <Bar value={p.expense} max={maxIncome} tone="ember" />
                  </div>
                  <Money value={p.net} className="w-32 text-right text-xs" sign />
                </div>
              ))}
              <div className="flex items-center gap-4 border-t border-border pt-3 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1.5">
                  <span className="size-2 rounded-full bg-primary" /> Projected income
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span className="size-2 rounded-full bg-ember" /> Projected expense
                </span>
              </div>
            </div>
          </Card>

          <Card title="Scenarios side by side" subtitle="Closing cash on 31 Dec 2026">
            <table className="w-full">
              <thead className="border-b border-border">
                <tr>
                  <Th>Scenario</Th>
                  <Th className="text-right">Income</Th>
                  <Th className="text-right">Closing cash</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {scenarios.map((s) => {
                  const income = sum(
                    forecast.map((f) => f.committed + Math.round(f.weighted * s.factor)),
                  );
                  const bal = opening + income - totalExpense;
                  return (
                    <tr key={s.key} className={s.key === scenarioKey ? "bg-secondary/60" : ""}>
                      <Td className="font-medium">{s.label}</Td>
                      <Td className="text-right">
                        <Money value={income} />
                      </Td>
                      <Td className="text-right">
                        <Money value={bal} className={bal < 0 ? "text-ember" : ""} />
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}

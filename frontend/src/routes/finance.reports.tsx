import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Download } from "lucide-react";
import { AppShell } from "@/components/aura/AppShell";
import { Card, Money, Pill, Stat, Td, Th } from "@/components/aura/primitives";
import { Bar, FinanceTabs } from "@/components/aura/FinanceTabs";
import {
  expenseByCategory,
  jobProfitability,
  monthly,
  sum,
  taxLines,
  ytd,
  ytdMarginPct,
  ytdProfit,
} from "@/data/finance";

export const Route = createFileRoute("/finance/reports")({
  head: () => ({
    meta: [
      { title: "Finance reports — P&L, job margin and tax | AuraOS" },
      {
        name: "description",
        content:
          "Profit and loss by month, margin per job, expense structure and the VAT/TNCN/TNDN position for the period.",
      },
      { property: "og:title", content: "Finance reports — AuraOS" },
      {
        property: "og:description",
        content: "P&L by month, job margin ranking and the tax position.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ReportsPage,
});

const periods = ["Q1", "Q2", "Q3 (đang mở)", "YTD 2026"] as const;

function ReportsPage() {
  const [period, setPeriod] = useState<(typeof periods)[number]>("YTD 2026");
  const taxDue = sum(taxLines.map((t) => t.amount));
  const overhead = expenseByCategory.find((c) => c.category === "Overhead")?.amount ?? 0;
  const directCost = ytd.expense - overhead;
  const maxJob = Math.max(...jobProfitability.map((j) => j.revenue));

  return (
    <AppShell
      title="Reports"
      meta={`${period} · VND · cash basis`}
      actions={
        <button className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium transition-colors hover:bg-secondary">
          <Download className="size-3.5" /> Export XLSX
        </button>
      }
    >
      <div className="space-y-5">
        <FinanceTabs />

        <div className="flex flex-wrap gap-1">
          {periods.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`rounded-lg border px-3 py-1.5 text-xs transition-colors ${
                period === p
                  ? "border-transparent bg-primary text-primary-foreground"
                  : "border-border bg-card text-muted-foreground hover:text-foreground"
              }`}
            >
              {p}
            </button>
          ))}
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Stat label="Revenue" value={<Money value={ytd.income} />} sub="Recognised" />
          <Stat label="Direct cost" value={<Money value={directCost} />} sub="Crew, kit, art, post" />
          <Stat label="Overhead" value={<Money value={overhead} />} sub="Studio & admin" />
          <Stat label="Net profit" value={<Money value={ytdProfit} />} sub={`Margin ${ytdMarginPct}%`} />
        </div>

        <Card title="Profit & loss by month" subtitle="Income, expense and the profit left over">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-border">
                <tr>
                  <Th>Month</Th>
                  <Th className="text-right">Income</Th>
                  <Th className="text-right">Expense</Th>
                  <Th className="text-right">Profit</Th>
                  <Th className="text-right">Margin</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {monthly.map((m) => {
                  const profit = m.income - m.expense;
                  const pct = Math.round((profit / m.income) * 1000) / 10;
                  return (
                    <tr key={m.month} className="hover:bg-secondary/50">
                      <Td className="font-medium">{m.month} 2026</Td>
                      <Td className="text-right">
                        <Money value={m.income} />
                      </Td>
                      <Td className="text-right text-muted-foreground">
                        <Money value={m.expense} />
                      </Td>
                      <Td className="text-right">
                        <Money value={profit} sign />
                      </Td>
                      <Td className="text-right">
                        <Pill tone={pct >= 20 ? "positive" : "ember"}>{pct}%</Pill>
                      </Td>
                    </tr>
                  );
                })}
                <tr className="bg-secondary/60 font-semibold">
                  <Td>Total</Td>
                  <Td className="text-right">
                    <Money value={ytd.income} />
                  </Td>
                  <Td className="text-right">
                    <Money value={ytd.expense} />
                  </Td>
                  <Td className="text-right">
                    <Money value={ytdProfit} />
                  </Td>
                  <Td className="text-right">{ytdMarginPct}%</Td>
                </tr>
              </tbody>
            </table>
          </div>
        </Card>

        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2" title="Margin by job" subtitle="Revenue vs cost, closed and open jobs">
            <div className="space-y-4 p-4">
              {jobProfitability.map((j) => {
                const profit = j.revenue - j.cost;
                const pct = Math.round((profit / j.revenue) * 1000) / 10;
                return (
                  <div key={j.job} className="space-y-1.5">
                    <div className="flex flex-wrap items-baseline gap-2">
                      <span className="text-sm font-medium">{j.name}</span>
                      <span className="label-caps">{j.job}</span>
                      <span className="ml-auto">
                        <Pill tone={pct >= 20 ? "positive" : "ember"}>{pct}% margin</Pill>
                      </span>
                    </div>
                    <Bar value={j.revenue} max={maxJob} tone="ink" />
                    <Bar value={j.cost} max={maxJob} tone="ember" />
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>
                        Revenue <Money value={j.revenue} className="text-foreground" />
                      </span>
                      <span>
                        Profit <Money value={profit} className="text-foreground" />
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          <Card tone="ink" title="Tax position" subtitle="Estimate for the period">
            <div className="space-y-3 p-4">
              <dl className="space-y-2 text-sm">
                {taxLines.map((t) => (
                  <div key={t.label} className="flex justify-between gap-3">
                    <dt className="text-primary-foreground/60">{t.label}</dt>
                    <dd>
                      <Money value={t.amount} sign />
                    </dd>
                  </div>
                ))}
              </dl>
              <div className="flex justify-between gap-3 border-t border-white/10 pt-2 text-sm font-semibold">
                <span>Ước tính phải nộp</span>
                <Money value={taxDue} />
              </div>
              <p className="text-xs text-primary-foreground/50">
                Estimate only — confirm with the accountant before filing.
              </p>
            </div>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}

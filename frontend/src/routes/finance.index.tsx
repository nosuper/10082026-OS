import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowUpRight, TrendingUp } from "lucide-react";
import { AppShell } from "@/components/aura/AppShell";
import { Card, Money, Pill, Stat, Td, Th } from "@/components/aura/primitives";
import { Bar, FinanceTabs } from "@/components/aura/FinanceTabs";
import {
  cashAccounts,
  expenseByCategory,
  incomeRows,
  monthly,
  payables,
  receivables,
  sum,
  ytd,
  ytdMarginPct,
  ytdProfit,
} from "@/data/finance";

export const Route = createFileRoute("/finance/")({
  head: () => ({
    meta: [
      { title: "Finance dashboard — cash, income and margin | AuraOS" },
      {
        name: "description",
        content:
          "Cash on hand, income vs expense per month, receivables ageing and job margin for the production house.",
      },
      { property: "og:title", content: "Finance dashboard — AuraOS" },
      {
        property: "og:description",
        content: "Cash, income vs expense, receivables ageing and margin in one view.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: FinanceDashboard,
});

function FinanceDashboard() {
  const cash = sum(cashAccounts.map((a) => a.balance));
  const ar = sum(receivables.map((r) => r.amount));
  const ap = sum(payables.map((p) => p.amount));
  const maxMonth = Math.max(...monthly.map((m) => Math.max(m.income, m.expense)));
  const maxCat = Math.max(...expenseByCategory.map((c) => c.amount));
  const overdue = incomeRows.filter((r) => r.status === "Quá hạn");

  return (
    <AppShell
      title="Finance"
      meta="YTD Jan–Aug 2026 · VND · all figures exclude VAT unless noted"
      actions={
        <Link
          to="/finance/reports"
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          <TrendingUp className="size-3.5" /> Open report
        </Link>
      }
    >
      <div className="space-y-5">
        <FinanceTabs />

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Stat label="Cash on hand" value={<Money value={cash} />} sub="4 accounts incl. crew float" />
          <Stat
            label="Income YTD"
            value={<Money value={ytd.income} />}
            sub={`Expense ${new Intl.NumberFormat("vi-VN").format(ytd.expense)} ₫`}
          />
          <Stat
            label="Profit YTD"
            value={<Money value={ytdProfit} />}
            sub={`Margin ${ytdMarginPct}%`}
          />
          <Stat
            label="Overdue receivables"
            value={<Money value={sum(overdue.map((o) => o.amount))} />}
            sub={`${overdue.length} invoices past due`}
            alert
          />
        </div>

        <Card
          title="Income vs expense"
          subtitle="Monthly, realised"
          action={<Pill tone="positive">Profit every month</Pill>}
        >
          <div className="space-y-3 p-4">
            {monthly.map((m) => {
              const profit = m.income - m.expense;
              return (
                <div key={m.month} className="grid grid-cols-[2.5rem_1fr_auto] items-center gap-3">
                  <div className="label-caps">{m.month}</div>
                  <div className="space-y-1">
                    <Bar value={m.income} max={maxMonth} tone="ink" />
                    <Bar value={m.expense} max={maxMonth} tone="ember" />
                  </div>
                  <Money value={profit} className="w-32 text-right text-xs" sign />
                </div>
              );
            })}
            <div className="flex items-center gap-4 border-t border-border pt-3 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-primary" /> Income
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-ember" /> Expense
              </span>
            </div>
          </div>
        </Card>

        <div className="grid gap-4 lg:grid-cols-3">
          <Card title="Cash accounts" subtitle="Live balances" className="lg:col-span-1">
            <ul className="divide-y divide-border">
              {cashAccounts.map((a) => (
                <li key={a.name} className="flex items-center gap-3 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{a.name}</div>
                    <div className="label-caps mt-0.5">{a.kind}</div>
                  </div>
                  <Money value={a.balance} className="text-sm" />
                </li>
              ))}
            </ul>
          </Card>

          <Card title="Where the money goes" subtitle="Expense by category, YTD" className="lg:col-span-2">
            <div className="space-y-3 p-4">
              {expenseByCategory.map((c) => (
                <div key={c.category} className="grid grid-cols-[10rem_1fr_auto] items-center gap-3">
                  <div className="truncate text-sm">{c.category}</div>
                  <Bar value={c.amount} max={maxCat} tone="muted" />
                  <Money value={c.amount} className="w-32 text-right text-xs" />
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card
            title="Receivables ageing"
            subtitle={`Total ${new Intl.NumberFormat("vi-VN").format(ar)} ₫`}
            action={
              <Link
                to="/finance/income"
                className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-ember"
              >
                Income <ArrowUpRight className="size-3.5" />
              </Link>
            }
          >
            <table className="w-full">
              <thead className="border-b border-border">
                <tr>
                  <Th>Bucket</Th>
                  <Th className="text-right">Amount</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {receivables.map((r) => (
                  <tr key={r.bucket}>
                    <Td>{r.bucket}</Td>
                    <Td className="text-right">
                      <Money value={r.amount} className={r.amount > 0 && r.bucket !== "Chưa đến hạn" ? "text-ember" : ""} />
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          <Card
            title="Payables ageing"
            subtitle={`Total ${new Intl.NumberFormat("vi-VN").format(ap)} ₫`}
            action={
              <Link
                to="/finance/expenses"
                className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-ember"
              >
                Expenses <ArrowUpRight className="size-3.5" />
              </Link>
            }
          >
            <table className="w-full">
              <thead className="border-b border-border">
                <tr>
                  <Th>Bucket</Th>
                  <Th className="text-right">Amount</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {payables.map((p) => (
                  <tr key={p.bucket}>
                    <Td>{p.bucket}</Td>
                    <Td className="text-right">
                      <Money value={p.amount} />
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}

import { createFileRoute, Link } from "@tanstack/react-router";
import { AlertTriangle, ArrowUpRight, Plus } from "lucide-react";
import { useState } from "react";
import { AppShell } from "@/components/aura/AppShell";
import { Card, Money, Pill, Stat, Td, Th } from "@/components/aura/primitives";
import {
  dashboardTiles,
  expenseCategories,
  founderBlock,
  jobsInProduction,
  needsAttention,
  totals,
} from "@/data/fixture";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Home — AuraOS production ops" },
      {
        name: "description",
        content:
          "Pipeline, jobs in production, overdue payments and quiet quotes on one producer desk.",
      },
      { property: "og:title", content: "Home — AuraOS production ops" },
      {
        property: "og:description",
        content: "Pipeline, jobs in production, overdue payments and quiet quotes at a glance.",
      },
    ],
  }),
  component: HomePage,
});

const stageTone: Record<string, string> = {
  Production: "ink",
  "Post-production": "neutral",
  Delivery: "neutral",
  "Awaiting payment": "ember",
};

function HomePage() {
  const [job, setJob] = useState(jobsInProduction[0]?.job ?? "");
  const [category, setCategory] = useState(expenseCategories[0] ?? "");

  return (
    <AppShell
      title="Good morning, Bảo"
      meta="Tuesday 18 August 2026 · 6 open deals · 4 jobs in production"
      actions={
        <button className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90">
          <Plus className="size-3.5" /> New deal
        </button>
      }
    >
      <div className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {dashboardTiles.map((t) => (
            <Stat
              key={t.label}
              label={t.label}
              value={<Money value={t.value} />}
              sub={t.sub}
              alert={t.alert}
            />
          ))}
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <Card
            className="lg:col-span-2"
            title="Needs attention"
            subtitle="Money that has stopped moving"
          >
            <ul className="divide-y divide-border">
              {needsAttention.map((n) => (
                <li key={n.what} className="flex flex-wrap items-center gap-3 px-4 py-3">
                  <AlertTriangle className="size-4 shrink-0 text-ember" strokeWidth={1.75} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{n.what}</div>
                    <div className="mt-0.5 text-xs text-muted-foreground">
                      {n.kind} · <span className="text-ember">{n.age}</span>
                    </div>
                  </div>
                  <Money value={n.amount} className="text-sm font-semibold" />
                </li>
              ))}
            </ul>
          </Card>

          <Card
            tone="ink"
            title="Margin — TVC Tết 2027"
            subtitle="Founder only"
            action={<Pill tone="ember">Above floor</Pill>}
          >
            <div className="space-y-3 p-4">
              <div>
                <div className="label-caps text-primary-foreground/50">Quote total</div>
                <Money value={totals.total} className="text-2xl font-semibold" />
              </div>
              <dl className="space-y-1.5 text-sm">
                {[
                  ["Cost", totals.cost],
                  ["Margin", totals.margin],
                  [`Commission ${founderBlock.commissionRate}%`, founderBlock.commission],
                  [`TNDN ${founderBlock.tndnRate}%`, founderBlock.tndn],
                ].map(([k, v]) => (
                  <div key={k as string} className="flex justify-between gap-3">
                    <dt className="text-primary-foreground/60">{k}</dt>
                    <dd>
                      <Money value={v as number} />
                    </dd>
                  </div>
                ))}
                <div className="flex justify-between gap-3 border-t border-white/10 pt-2 font-semibold">
                  <dt>Net profit</dt>
                  <dd>
                    <Money value={founderBlock.netProfit} />
                  </dd>
                </div>
              </dl>
              <div className="text-xs text-primary-foreground/50">
                Margin {totals.marginPct}% · floor {totals.marginFloorPct}%
              </div>
            </div>
          </Card>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <Card
            className="lg:col-span-2"
            title="Jobs in production"
            subtitle="4 open jobs"
            action={
              <Link
                to="/jobs"
                className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-ember"
              >
                All jobs <ArrowUpRight className="size-3.5" />
              </Link>
            }
          >
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-border">
                  <tr>
                    <Th>Job</Th>
                    <Th>Client</Th>
                    <Th className="text-right">Quoted</Th>
                    <Th>Stage</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {jobsInProduction.map((j) => (
                    <tr key={j.job} className="hover:bg-secondary/50">
                      <Td className="font-medium">
                        <Link to="/jobs/$jobId" params={{ jobId: "JOB-0114" }}>
                          {j.job}
                        </Link>
                      </Td>
                      <Td className="text-muted-foreground">{j.client}</Td>
                      <Td className="text-right">
                        <Money value={j.quoted} />
                      </Td>
                      <Td>
                        <Pill tone={stageTone[j.stage] ?? "neutral"}>{j.stage}</Pill>
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card title="Quick expense" subtitle="Log a cost against a job">
            <form
              className="space-y-3 p-4"
              onSubmit={(e) => {
                e.preventDefault();
              }}
            >
              <label className="block">
                <span className="label-caps">Job</span>
                <select
                  value={job}
                  onChange={(e) => setJob(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-border bg-background px-2.5 py-2 text-sm"
                >
                  {jobsInProduction.map((j) => (
                    <option key={j.job}>{j.job}</option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="label-caps">Amount (VND)</span>
                <input
                  inputMode="numeric"
                  placeholder="0"
                  className="mt-1 w-full rounded-lg border border-border bg-background px-2.5 py-2 num text-sm"
                />
              </label>
              <label className="block">
                <span className="label-caps">Category</span>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-border bg-background px-2.5 py-2 text-sm"
                >
                  {expenseCategories.map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="label-caps">Note (optional)</span>
                <input className="mt-1 w-full rounded-lg border border-border bg-background px-2.5 py-2 text-sm" />
              </label>
              <button
                type="submit"
                className="w-full rounded-lg bg-ember px-3 py-2 text-sm font-medium text-ember-foreground transition-opacity hover:opacity-90"
              >
                Log expense
              </button>
            </form>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}

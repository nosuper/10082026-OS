import { createFileRoute, Link } from "@tanstack/react-router";
import { ChevronLeft, Plus, ArrowRight } from "lucide-react";
import { AppShell } from "@/components/aura/AppShell";
import { Card, Money, Pill, Td, Th } from "@/components/aura/primitives";
import { deal, totals } from "@/data/fixture";

export const Route = createFileRoute("/jobs/$jobId")({
  head: () => ({
    meta: [
      { title: "Job detail — money, milestones and float | AuraOS" },
      {
        name: "description",
        content:
          "One job: stage log, quoted vs actual money, payment milestones, crew float and revision rounds.",
      },
      { property: "og:title", content: "Job detail — money, milestones and float" },
      {
        property: "og:description",
        content: "Stage log, quoted vs actual, milestones, crew float and revision rounds.",
      },
    ],
  }),
  component: JobDetail,
});

const stages = ["Chuẩn bị", "Ghi hình", "Hậu kỳ", "Bàn giao", "Thu tiền"];
const currentStage = 2;

const money = {
  quoted: totals.total,
  actualCost: 318_400_000,
  committed: 462_000_000,
  projectedMargin: 148_900_000,
  delta: -2_500_000,
};

const milestones = [
  { label: "Đặt cọc 40%", due: "12 Aug 2026", amount: 294_624_000, status: "Đã thu" },
  { label: "Sau ghi hình 30%", due: "02 Sep 2026", amount: 220_968_000, status: "Đã xuất hoá đơn" },
  { label: "Bàn giao 30%", due: "25 Sep 2026", amount: 220_968_000, status: "Dự kiến" },
];

const floats = [
  { person: "Nguyễn Hoàng Duy", role: "Director", advance: 20_000_000, expenses: 20_000_000 },
  { person: "Vũ Đình Nam", role: "DOP", advance: 25_000_000, expenses: 12_500_000 },
  { person: "Trần Mỹ Linh", role: "Production manager", advance: 15_000_000, expenses: 18_200_000 },
];

const log = [
  {
    when: "17 Aug 09:12",
    who: "Bảo",
    what: "Stage moved Ghi hình → Hậu kỳ",
    note: "2 shoot days closed, all footage backed up",
  },
  {
    when: "16 Aug 18:40",
    who: "Mỹ Linh",
    what: "Advance issued to Vũ Đình Nam",
    note: "25,000,000 ₫ — camera team per diem",
  },
  {
    when: "15 Aug 11:05",
    who: "Thu Trang",
    what: "Revision round 2 logged",
    note: "In scope — client note on VO timing",
  },
  {
    when: "12 Aug 08:30",
    who: "System",
    what: "Milestone Đặt cọc 40% collected",
    note: "294,624,000 ₫ received",
  },
];

const revisions = [
  { round: "R1", scope: "In scope", note: "Rough cut notes", amount: 0 },
  { round: "R2", scope: "In scope", note: "VO timing", amount: 0 },
  { round: "R3", scope: "Change order", note: "Extra 15s cutdown + new endframe", amount: 18_500_000 },
];

function JobDetail() {
  const { jobId } = Route.useParams();
  return (
    <AppShell
      title={deal.name}
      meta={
        <span className="flex flex-wrap items-center gap-x-2">
          <Link to="/jobs" className="inline-flex items-center hover:text-ember">
            <ChevronLeft className="size-3.5" /> Jobs
          </Link>
          <span className="num">{jobId}</span>· {deal.client} · Producer Trần Mỹ Linh · Shoot 14–15
          Aug 2026
        </span>
      }
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <button className="rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-secondary">
            Log revision
          </button>
          <Link
            to="/expense"
            className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-secondary"
          >
            <Plus className="size-3.5" /> Add expense
          </Link>
          <button className="inline-flex items-center gap-1.5 rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90">
            Advance stage <ArrowRight className="size-3.5" />
          </button>
        </div>
      }
    >
      <div className="space-y-5">
        <div className="flex flex-wrap items-center gap-1.5 rounded-xl border border-border bg-card p-3">
          {stages.map((s, i) => (
            <div key={s} className="flex items-center gap-1.5">
              <span
                className={
                  i === currentStage
                    ? "rounded-md bg-ember px-2.5 py-1 text-xs font-medium text-ember-foreground"
                    : i < currentStage
                      ? "rounded-md bg-secondary px-2.5 py-1 text-xs text-foreground"
                      : "rounded-md px-2.5 py-1 text-xs text-muted-foreground"
                }
              >
                {s}
              </span>
              {i < stages.length - 1 ? (
                <ChevronLeft className="size-3 rotate-180 text-border-strong" />
              ) : null}
            </div>
          ))}
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2" title="Activity & stage log" subtitle="Immutable">
            <ul className="divide-y divide-border">
              {log.map((l) => (
                <li key={l.when} className="flex gap-3 px-4 py-3">
                  <div className="num w-24 shrink-0 text-[11px] text-muted-foreground">{l.when}</div>
                  <div className="min-w-0">
                    <div className="text-sm font-medium">{l.what}</div>
                    <div className="mt-0.5 text-xs text-muted-foreground">
                      {l.note} · {l.who}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </Card>

          <Card tone="ink" title="Money" subtitle="Founder only">
            <dl className="space-y-1.5 p-4 text-sm">
              {[
                ["Quoted", money.quoted],
                ["Actual cost", money.actualCost],
                ["Committed", money.committed],
                ["Projected margin", money.projectedMargin],
              ].map(([k, v]) => (
                <div key={k as string} className="flex justify-between gap-3">
                  <dt className="text-primary-foreground/60">{k}</dt>
                  <dd>
                    <Money value={v as number} />
                  </dd>
                </div>
              ))}
              <div className="flex justify-between gap-3 border-t border-white/10 pt-2">
                <dt className="text-primary-foreground/60">Delta vs quote basis</dt>
                <dd className="text-ember">
                  <Money value={money.delta} />
                </dd>
              </div>
            </dl>
            <div className="px-4 pb-4 text-xs text-primary-foreground/50">
              Cause: catering overrun on day 2 (35 → 41 pax).
            </div>
          </Card>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Payment milestones" subtitle="Collection status in Vietnamese">
            <div className="p-4">
              <div className="flex h-2 overflow-hidden rounded-full bg-secondary">
                <div className="h-full w-[40%] bg-primary" />
                <div className="h-full w-[30%] bg-ember" />
              </div>
              <div className="mt-2 text-xs text-muted-foreground">
                40% collected · 30% invoiced · 30% planned
              </div>
            </div>
            <ul className="divide-y divide-border border-t border-border">
              {milestones.map((m) => (
                <li key={m.label} className="flex items-center gap-3 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium">{m.label}</div>
                    <div className="mt-0.5 text-xs text-muted-foreground">Due {m.due}</div>
                  </div>
                  <Money value={m.amount} className="text-sm" />
                  <Pill tone={m.status === "Đã thu" ? "ink" : m.status === "Dự kiến" ? "neutral" : "ember"}>
                    {m.status}
                  </Pill>
                </li>
              ))}
            </ul>
          </Card>

          <Card title="Crew float" subtitle="Derived: advance − matched expenses">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px]">
                <thead className="border-b border-border">
                  <tr>
                    <Th>Person</Th>
                    <Th className="text-right">Advance</Th>
                    <Th className="text-right">Expenses</Th>
                    <Th className="text-right">Float</Th>
                    <Th />
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {floats.map((f) => {
                    const bal = f.advance - f.expenses;
                    return (
                      <tr key={f.person}>
                        <Td>
                          <div className="font-medium">{f.person}</div>
                          <div className="mt-0.5 text-xs text-muted-foreground">{f.role}</div>
                        </Td>
                        <Td className="text-right text-muted-foreground">
                          <Money value={f.advance} />
                        </Td>
                        <Td className="text-right text-muted-foreground">
                          <Money value={f.expenses} />
                        </Td>
                        <Td className={`text-right font-medium ${bal < 0 ? "text-ember" : ""}`}>
                          <Money value={bal} />
                        </Td>
                        <Td className="text-right">
                          <button className="rounded-md border border-border px-2 py-1 text-xs hover:bg-secondary">
                            Settle
                          </button>
                        </Td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        <Card title="Revision rounds">
          <ul className="divide-y divide-border">
            {revisions.map((r) => (
              <li key={r.round} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <span className="num w-8 text-sm font-semibold">{r.round}</span>
                <Pill tone={r.scope === "Change order" ? "ember" : "neutral"}>{r.scope}</Pill>
                <span className="min-w-0 flex-1 text-sm text-muted-foreground">{r.note}</span>
                {r.amount ? (
                  <>
                    <Money value={r.amount} className="text-sm font-medium text-ember" />
                    <Link
                      to="/deals/$dealCode"
                      params={{ dealCode: deal.code }}
                      className="rounded-md border border-border px-2 py-1 text-xs hover:bg-secondary"
                    >
                      Quote change order
                    </Link>
                  </>
                ) : (
                  <span className="text-xs text-muted-foreground">No extra charge</span>
                )}
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </AppShell>
  );
}

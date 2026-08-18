import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Filter, Plus } from "lucide-react";
import { AppShell } from "@/components/aura/AppShell";
import { Card, Money, Pill, Td, Th } from "@/components/aura/primitives";
import { KanbanBoard, ViewToggle, type KanbanColumn } from "@/components/aura/Kanban";
import { FormDialog, type FieldDef } from "@/components/aura/FormDialog";
import { deal, totals } from "@/data/fixture";

export const Route = createFileRoute("/deals/")({
  head: () => ({
    meta: [
      { title: "Deals pipeline — AuraOS" },
      {
        name: "description",
        content: "Table-first deal pipeline with stage tiles, quote state and idle-day nudges.",
      },
      { property: "og:title", content: "Deals pipeline — AuraOS" },
      {
        property: "og:description",
        content: "Stage tiles, quote state, weighted pipeline value and idle-day nudges.",
      },
    ],
  }),
  component: DealsPage,
});

const stageTiles = [
  { stage: "Lead", count: 2, value: 340_000_000 },
  { stage: "Briefed", count: 1, value: 220_000_000 },
  { stage: "Breakdown", count: 1, value: 850_000_000, focus: true },
  { stage: "Negotiating", count: 2, value: 515_000_000 },
  { stage: "Won MTD", count: 3, value: 705_000_000 },
];

const seedRows = [
  {
    code: deal.code,
    name: deal.name,
    client: `${deal.client} · Chị Thu Hà`,
    stage: "Breakdown",
    quote: "v2 published · not opened",
    quoteQuiet: true,
    tags: ["TVC", "Tết", "Tier 3"],
    value: totals.total,
    margin: totals.marginPct,
    idle: 1,
  },
  {
    code: "DEAL-0179",
    name: "Social cutdowns x12",
    client: "Nhất Minh Beverage · Chị Thu Hà",
    stage: "Negotiating",
    quote: "v1 sent · 2 opens",
    quoteQuiet: true,
    tags: ["Social"],
    value: 95_000_000,
    margin: 26.4,
    idle: 9,
  },
  {
    code: "DEAL-0176",
    name: "Corporate profile film",
    client: "Sông Hà Logistics · Anh Tuấn",
    stage: "Negotiating",
    quote: "v3 sent · 6 opens",
    tags: ["Corporate"],
    value: 420_000_000,
    margin: 24.1,
    idle: 2,
  },
  {
    code: "DEAL-0174",
    name: "Product launch KV + film",
    client: "Gốm Sứ Minh Long · Chị Ngân",
    stage: "Briefed",
    quote: "no quote yet",
    tags: ["Launch"],
    value: 220_000_000,
    margin: 21.0,
    idle: 5,
  },
  {
    code: "DEAL-0171",
    name: "Recruitment film phase 2",
    client: "Đại Việt Foods · Anh Khánh",
    stage: "Lead",
    quote: "no quote yet",
    tags: ["HR"],
    value: 140_000_000,
    margin: 19.4,
    idle: 14,
  },
  {
    code: "DEAL-0168",
    name: "Farm documentary",
    client: "Lộc Trời Agri · Chị Hạnh",
    stage: "Lead",
    quote: "no quote yet",
    tags: ["Doc"],
    value: 200_000_000,
    margin: 22.8,
    idle: 21,
  },
];

type DealRow = {
  code: string;
  name: string;
  client: string;
  stage: string;
  quote: string;
  quoteQuiet?: boolean;
  tags: string[];
  value: number;
  margin: number;
  idle: number;
};

const dealStages = ["Lead", "Briefed", "Breakdown", "Negotiating", "Won"];

const dealFields: FieldDef[] = [
  { name: "name", label: "Deal name", required: true, span: 2, placeholder: 'TVC Tết 2027 "Vị Xuân"' },
  { name: "client", label: "Client company", required: true, placeholder: "Nhất Minh Beverage" },
  { name: "contact", label: "Primary contact", placeholder: "Chị Phạm Thu Hà" },
  { name: "stage", label: "Stage", type: "select", options: dealStages },
  { name: "positioning", label: "Positioning", type: "select", options: ["Brand", "Corporate", "Social", "Retail"] },
  { name: "tier", label: "Tier", type: "select", options: ["Tier 1", "Tier 2", "Tier 3", "Tier 4"] },
  { name: "value", label: "Client budget", type: "number", suffix: "₫", placeholder: "850000000" },
  { name: "owner", label: "Owner", placeholder: "Trần Quốc Bảo", span: 2 },
];


function DealCard({ r }: { r: DealRow }) {
  return (
    <Link
      to="/deals/$dealCode"
      params={{ dealCode: r.code }}
      className="block rounded-lg border border-border bg-card p-3 transition-shadow hover:border-border-strong hover:shadow-sm"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-medium leading-snug">{r.name}</span>
        <span className="num text-[11px] text-muted-foreground">{r.code}</span>
      </div>
      <div className="mt-1 truncate text-xs text-muted-foreground">{r.client}</div>
      <div className="mt-2.5 flex items-baseline justify-between">
        <Money value={r.value} className="text-sm font-semibold" />
        <span className="num text-[11px] text-muted-foreground">{r.margin.toFixed(1)}%</span>
      </div>
      <div className="mt-2.5 flex flex-wrap items-center gap-1">
        {r.tags.map((t) => (
          <Pill key={t} tone="outline">
            {t}
          </Pill>
        ))}
        <span className="ml-auto flex items-center gap-1.5">
          <span className={`num text-[11px] ${r.idle >= 9 ? "text-ember" : "text-muted-foreground"}`}>
            {r.idle}d idle
          </span>
        </span>
      </div>
      <div
        className={`mt-2 border-t border-border pt-2 text-[11px] ${r.quoteQuiet ? "text-ember" : "text-muted-foreground"}`}
      >
        {r.quote}
      </div>
    </Link>
  );
}

export function DealsPage() {
  const weighted = 1_925_000_000;
  const [view, setView] = useState<"table" | "kanban">("table");
  const [rows, setRows] = useState<DealRow[]>(seedRows);
  const [newOpen, setNewOpen] = useState(false);
  const columns: KanbanColumn<DealRow>[] = dealStages.map((s) => ({
    key: s,
    title: s,
    items: rows.filter((r) => r.stage === s),
    focus: s === "Breakdown",
  }));

  function createDeal(v: Record<string, string>) {
    const nextCode = `DEAL-${String(183 + rows.length - seedRows.length).padStart(4, "0")}`;
    const tags = [v["positioning"], v["tier"]].filter((t): t is string => Boolean(t));
    setRows((prev) => [
      {
        code: nextCode,
        name: v["name"] ?? "Untitled deal",
        client: [v["client"], v["contact"]].filter(Boolean).join(" · "),
        stage: v["stage"] ?? "Lead",
        quote: "no quote yet",
        tags,
        value: Number(v["value"] ?? 0) || 0,
        margin: 0,
        idle: 0,
      },
      ...prev,
    ]);
    setNewOpen(false);
  }

  return (
    <AppShell
      title="Deals"
      meta={`${rows.length} open deals · 2 quotes awaiting signature`}
      actions={
        <button
          onClick={() => setNewOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:opacity-90"
        >
          <Plus className="size-3.5" /> New deal
        </button>
      }
    >
      <FormDialog
        open={newOpen}
        title="New deal"
        subtitle="Creates a deal in Lead stage — pricing happens in the breakdown."
        fields={dealFields}
        submitLabel="Create deal"
        onClose={() => setNewOpen(false)}
        onSubmit={createDeal}
      />

      <div className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-5">
          {stageTiles.map((t) => (
            <div
              key={t.stage}
              className={
                t.focus
                  ? "rounded-xl border border-ember bg-card p-4"
                  : "rounded-xl border border-border bg-card p-4"
              }
            >
              <div className="label-caps">{t.stage}</div>
              <div className="mt-1.5 flex items-baseline gap-2">
                <span className="num text-lg font-semibold">{t.count}</span>
                <span className="text-xs text-muted-foreground">deals</span>
              </div>
              <Money value={t.value} className="mt-1 block text-xs text-muted-foreground" />
            </div>
          ))}
        </div>

        <Card
          title="All deals"
          subtitle={
            <span>
              Weighted pipeline <Money value={weighted} className="text-foreground" />
            </span>
          }
          action={
            <div className="flex items-center gap-2">
              <input
                placeholder="Filter deals…"
                className="w-40 rounded-lg border border-border bg-background px-2.5 py-1.5 text-xs"
              />
              <button className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:text-foreground">
                <Filter className="size-3.5" /> Stage · Source · Owner
              </button>
              <ViewToggle view={view} onChange={setView} />
            </div>
          }
        >
          {view === "kanban" ? (
            <div className="p-3">
              <KanbanBoard
                columns={columns}
                total={(items) => items.reduce((s, r) => s + r.value, 0)}
                renderCard={(r) => <DealCard r={r} />}
              />
            </div>
          ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px]">
              <thead className="border-b border-border">
                <tr>
                  <Th>Deal</Th>
                  <Th>Client</Th>
                  <Th>Stage</Th>
                  <Th>Quote state</Th>
                  <Th>Tags</Th>
                  <Th className="text-right">Value</Th>
                  <Th className="text-right">Margin</Th>
                  <Th className="text-right">Idle</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {rows.map((r) => (
                  <tr key={r.code} className="hover:bg-secondary/50">
                    <Td>
                      <Link
                        to="/deals/$dealCode"
                        params={{ dealCode: r.code }}
                        className="font-medium hover:text-ember"
                      >
                        {r.name}
                      </Link>
                      <div className="num mt-0.5 text-[11px] text-muted-foreground">{r.code}</div>
                    </Td>
                    <Td className="text-muted-foreground">{r.client}</Td>
                    <Td>
                      <Pill tone={r.stage === "Breakdown" ? "ink" : "neutral"}>{r.stage}</Pill>
                    </Td>
                    <Td className={r.quoteQuiet ? "text-ember" : "text-muted-foreground"}>
                      {r.quote}
                    </Td>
                    <Td>
                      <div className="flex flex-wrap gap-1">
                        {r.tags.map((t) => (
                          <Pill key={t} tone="outline">
                            {t}
                          </Pill>
                        ))}
                      </div>
                    </Td>
                    <Td className="text-right">
                      <Money value={r.value} />
                    </Td>
                    <Td className="num text-right">{r.margin.toFixed(1)}%</Td>
                    <Td className={`num text-right ${r.idle >= 9 ? "text-ember" : ""}`}>
                      {r.idle}d
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )}
        </Card>
      </div>
    </AppShell>
  );
}

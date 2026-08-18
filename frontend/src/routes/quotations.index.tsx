import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Plus, Search } from "lucide-react";
import { AppShell } from "@/components/aura/AppShell";
import { Card, Money, Pill, Td, Th } from "@/components/aura/primitives";

export const Route = createFileRoute("/quotations/")({
  head: () => ({
    meta: [
      { title: "Quotations — AuraOS" },
      {
        name: "description",
        content:
          "Every quotation version across deals: status, total, detail level and client open activity.",
      },
      { property: "og:title", content: "Quotations — AuraOS" },
      {
        property: "og:description",
        content: "Quotation versions across deals with status, totals and open activity.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: QuotationsPage,
});

type QuoteRow = {
  ref: string;
  dealCode: string;
  deal: string;
  client: string;
  version: string;
  status: "Draft" | "Sent" | "Published" | "Accepted";
  total: number;
  detail: string;
  activity: string;
};

const seedRows: QuoteRow[] = [
  {
    ref: "QUO-0182-2",
    dealCode: "DEAL-0182",
    deal: 'TVC Tết 2027 "Vị Xuân"',
    client: "Nhất Minh Beverage",
    version: "v2",
    status: "Published",
    total: 736_560_000,
    detail: "Package totals",
    activity: "3 opens, last 17 Aug",
  },
  {
    ref: "QUO-0182-1",
    dealCode: "DEAL-0182",
    deal: 'TVC Tết 2027 "Vị Xuân"',
    client: "Nhất Minh Beverage",
    version: "v1",
    status: "Sent",
    total: 712_800_000,
    detail: "Package totals",
    activity: "4 opens, last 09 Aug",
  },
  {
    ref: "QUO-0179-1",
    dealCode: "DEAL-0179",
    deal: "Social cutdowns x12",
    client: "Nhất Minh Beverage",
    version: "v1",
    status: "Sent",
    total: 95_000_000,
    detail: "Full line detail",
    activity: "9 days no reply",
  },
  {
    ref: "QUO-0175-3",
    dealCode: "DEAL-0175",
    deal: 'Brand film "Hạt Gạo Quê"',
    client: "Lộc Trời Agri",
    version: "v3",
    status: "Accepted",
    total: 380_000_000,
    detail: "Package + grouped lines",
    activity: "signed 02 Aug",
  },
  {
    ref: "QUO-0186-1",
    dealCode: "DEAL-0186",
    deal: "Retail launch Nam Long",
    client: "Nam Long Group",
    version: "v1",
    status: "Draft",
    total: 168_000_000,
    detail: "Package totals",
    activity: "draft — not sent",
  },
];

const statusTone: Record<QuoteRow["status"], string> = {
  Draft: "outline",
  Sent: "neutral",
  Published: "ember",
  Accepted: "positive",
};

function QuotationsPage() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<"All" | QuoteRow["status"]>("All");
  const rows = seedRows;

  const filtered = rows.filter(
    (r) =>
      (status === "All" || r.status === status) &&
      (r.deal.toLowerCase().includes(q.toLowerCase()) ||
        r.client.toLowerCase().includes(q.toLowerCase()) ||
        r.ref.toLowerCase().includes(q.toLowerCase())),
  );

  const openValue = rows
    .filter((r) => r.status === "Sent" || r.status === "Published")
    .reduce((a, r) => a + r.total, 0);

  return (
    <AppShell
      title="Quotations"
      meta={
        <span>
          {rows.length} versions · awaiting client decision{" "}
          <Money value={openValue} className="text-foreground" />
        </span>
      }
      actions={
        <Link
          to="/quotations/$quoteRef"
          params={{ quoteRef: "new" }}
          className="inline-flex items-center gap-1.5 rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90"
        >
          <Plus className="size-3.5" /> New quotation
        </Link>
      }
    >
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex min-w-[220px] flex-1 items-center gap-2 rounded-lg border border-border bg-card px-2.5 py-2">
            <Search className="size-3.5 text-muted-foreground" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search quotations"
              className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
          </div>
          {(["All", "Draft", "Sent", "Published", "Accepted"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatus(s)}
              className={
                status === s
                  ? "rounded-lg bg-primary px-2.5 py-2 text-xs font-medium text-primary-foreground"
                  : "rounded-lg border border-border bg-card px-2.5 py-2 text-xs text-muted-foreground hover:text-foreground"
              }
            >
              {s}
            </button>
          ))}
        </div>

        <Card title="All versions" subtitle="Quotations are built from a deal breakdown">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[880px]">
              <thead className="border-b border-border">
                <tr>
                  <Th>Ref</Th>
                  <Th>Deal</Th>
                  <Th>Client</Th>
                  <Th>Status</Th>
                  <Th>Detail level</Th>
                  <Th className="text-right">Total</Th>
                  <Th>Activity</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filtered.map((r) => (
                  <tr key={r.ref} className="hover:bg-secondary/40">
                    <Td className="num">
                      <Link
                        to="/quotations/$quoteRef"
                        params={{ quoteRef: r.ref }}
                        className="font-medium hover:text-ember"
                      >
                        {r.ref}
                      </Link>
                    </Td>
                    <Td>
                      <div className="font-medium">{r.deal}</div>
                      <div className="num mt-0.5 text-xs text-muted-foreground">
                        {r.dealCode} · {r.version}
                      </div>
                    </Td>
                    <Td className="text-muted-foreground">{r.client}</Td>
                    <Td>
                      <Pill tone={statusTone[r.status]}>{r.status}</Pill>
                    </Td>
                    <Td className="text-muted-foreground">{r.detail}</Td>
                    <Td className="text-right font-semibold">
                      <Money value={r.total} />
                    </Td>
                    <Td className="text-xs text-muted-foreground">{r.activity}</Td>
                  </tr>
                ))}
                {filtered.length === 0 ? (
                  <tr>
                    <Td colSpan={7} className="py-8 text-center text-muted-foreground">
                      No quotations match this filter.
                    </Td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}

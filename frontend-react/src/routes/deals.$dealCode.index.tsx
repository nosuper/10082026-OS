import { createFileRoute, Link } from "@tanstack/react-router";
import { ChevronLeft, FileSpreadsheet } from "lucide-react";
import { AppShell } from "@/components/aura/AppShell";
import { Card, Money, Pill, Td, Th } from "@/components/aura/primitives";
import { costLines, costTotals, deal, founderBlock, totals } from "@/data/fixture";

export const Route = createFileRoute("/deals/$dealCode/")({
  head: () => ({
    meta: [
      { title: 'Breakdown — TVC Tết 2027 "Vị Xuân" | AuraOS' },
      {
        name: "description",
        content:
          "Internal cost breakdown: 17 cost lines by phase, markups, tax types and founder-only margin. Quotation is built on its own surface.",
      },
      { property: "og:title", content: 'Breakdown — TVC Tết 2027 "Vị Xuân"' },
      {
        property: "og:description",
        content: "Cost lines by phase with markup, tax type and founder-only margin check.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: BreakdownPage,
});

const phases = ["Pre-production", "Production", "Post-production"] as const;

const taxTone: Record<string, string> = {
  "Công ty": "neutral",
  "Cá nhân": "outline",
  "Không hoá đơn": "ember",
};

function BreakdownPage() {
  const { dealCode } = Route.useParams();

  return (
    <AppShell
      title={deal.name}
      meta={
        <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <Link to="/deals" className="inline-flex items-center hover:text-ember">
            <ChevronLeft className="size-3.5" /> Deals
          </Link>
          <span className="num">{dealCode}</span>· {deal.client} · {deal.contact} · Owner{" "}
          {deal.owner} · {deal.tier} · {deal.positioning}
        </span>
      }
      actions={
        <Link
          to="/quotations/$quoteRef"
          params={{ quoteRef: "new" }}
          className="inline-flex items-center gap-1.5 rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90"
        >
          <FileSpreadsheet className="size-3.5" /> Convert to quotation
        </Link>
      }
    >
      <div className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="label-caps">Client budget</div>
            <Money value={deal.clientBudget} className="mt-2 block text-lg font-semibold" />
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="label-caps">Total cost</div>
            <Money value={costTotals.totalCost} className="mt-2 block text-lg font-semibold" />
            <div className="mt-1 text-xs text-muted-foreground">
              {costLines.length} cost lines
            </div>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="label-caps">Line-level quote price</div>
            <Money value={costTotals.totalLineQuote} className="mt-2 block text-lg font-semibold" />
            <div className="mt-1 text-xs text-muted-foreground">before packaging & fees</div>
          </div>
          <div className="rounded-xl border border-ember bg-card p-4">
            <div className="label-caps">Margin</div>
            <div className="mt-2 num text-lg font-semibold text-ember">{totals.marginPct}%</div>
            <div className="mt-1 text-xs text-muted-foreground">
              floor {totals.marginFloorPct}% · above floor
            </div>
          </div>
        </div>

        <Card
          title="Cost lines"
          subtitle="Internal only — pricing shown to the client is assembled in the quotation."
          action={
            <Link
              to="/quotations/$quoteRef"
              params={{ quoteRef: "QUO-0182-2" }}
              className="rounded-lg border border-border px-2.5 py-1.5 text-xs hover:bg-secondary"
            >
              Open quotation
            </Link>
          }
        >
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1180px]">
              <thead className="border-b border-border">
                <tr>
                  <Th className="w-8">#</Th>
                  <Th>Description</Th>
                  <Th>Category</Th>
                  <Th>Source</Th>
                  <Th>Contact</Th>
                  <Th>Pkg</Th>
                  <Th className="text-right">Qty</Th>
                  <Th className="text-right">Unit price</Th>
                  <Th>Tax</Th>
                  <Th className="text-right">Markup</Th>
                  <Th className="text-right">Subtotal</Th>
                  <Th className="text-right">Quote price</Th>
                </tr>
              </thead>
              {phases.map((phase) => {
                const lines = costLines.filter((l) => l.phase === phase);
                const sub = lines.reduce((a, l) => a + l.subtotal, 0);
                const quote = lines.reduce((a, l) => a + l.quotePrice, 0);
                return (
                  <tbody key={phase} className="divide-y divide-border border-b border-border">
                    <tr className="bg-secondary/60">
                      <Td colSpan={10} className="label-caps !text-foreground">
                        {phase}
                      </Td>
                      <Td className="text-right text-xs">
                        <Money value={sub} />
                      </Td>
                      <Td className="text-right text-xs font-semibold">
                        <Money value={quote} />
                      </Td>
                    </tr>
                    {lines.map((l) => (
                      <tr key={l.id} className="hover:bg-secondary/40">
                        <Td className="num text-muted-foreground">{l.id}</Td>
                        <Td className="font-medium">{l.description}</Td>
                        <Td className="text-muted-foreground">{l.category}</Td>
                        <Td className="text-muted-foreground">{l.source}</Td>
                        <Td className="text-muted-foreground">{l.contact}</Td>
                        <Td>
                          <Pill tone="outline">{l.pkg}</Pill>
                        </Td>
                        <Td className="num text-right whitespace-nowrap">
                          {l.qty1} {l.unit1}
                          {l.qty2 ? ` × ${l.qty2} ${l.unit2}` : ""}
                        </Td>
                        <Td className="text-right">
                          <Money value={l.unitPrice} />
                        </Td>
                        <Td>
                          <Pill tone={taxTone[l.taxType]}>{l.taxType}</Pill>
                        </Td>
                        <Td className="num text-right">{l.markup}%</Td>
                        <Td className="text-right">
                          <Money value={l.subtotal} />
                        </Td>
                        <Td className="text-right font-medium">
                          <Money value={l.quotePrice} />
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                );
              })}
            </table>
          </div>
        </Card>

        <Card tone="ink" title="Founder only" subtitle="Never shown to producers">
          <dl className="grid gap-x-8 gap-y-1.5 p-4 text-sm sm:grid-cols-2">
            {[
              [`Commission (CMF) ${founderBlock.commissionRate}%`, founderBlock.commission],
              ["CM after commission", founderBlock.cmAfterCommission],
              ["Lợi nhuận trước thuế", founderBlock.profitBeforeTax],
              [`TNDN ${founderBlock.tndnRate}%`, founderBlock.tndn],
              ["VAT phải nộp", founderBlock.vatPayable],
              ["Net profit", founderBlock.netProfit],
            ].map(([k, v]) => (
              <div key={k as string} className="flex justify-between gap-3">
                <dt className="text-primary-foreground/60">{k}</dt>
                <dd>
                  <Money value={v as number} />
                </dd>
              </div>
            ))}
          </dl>
        </Card>
      </div>
    </AppShell>
  );
}

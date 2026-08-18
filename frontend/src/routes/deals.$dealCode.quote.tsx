import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { ChevronLeft, History, Send } from "lucide-react";
import { AppShell } from "@/components/aura/AppShell";
import { Card, Money, Pill, Td, Th } from "@/components/aura/primitives";
import { deal, packages, quoteVersions, totals, vnd } from "@/data/fixture";

export const Route = createFileRoute("/deals/$dealCode/quote")({
  head: () => ({
    meta: [
      { title: 'Quotation v2 — TVC Tết 2027 "Vị Xuân" | AuraOS' },
      {
        name: "description",
        content:
          "Build the client quotation from the deal breakdown: package prices, detail level, management fee, VAT and version history.",
      },
      { property: "og:title", content: 'Quotation — TVC Tết 2027 "Vị Xuân"' },
      {
        property: "og:description",
        content: "Quotation builder with package overrides, fee and VAT rates, and version history.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: QuotationPage,
});

const detailLevels = [
  "Package totals - one price per package",
  "Package + grouped lines",
  "Full line detail",
] as const;

function QuotationPage() {
  const { dealCode } = Route.useParams();
  const [detail, setDetail] = useState<string>(detailLevels[0]);
  const [feeRate, setFeeRate] = useState(totals.managementFeeRate);
  const [vatRate, setVatRate] = useState(totals.vatRate);
  const [overrides, setOverrides] = useState<Record<string, number>>(
    Object.fromEntries(packages.map((p) => [p.pkg, p.override])),
  );

  const packagesSubtotal = packages.reduce((a, p) => a + (overrides[p.pkg] ?? p.price), 0);
  const managementFee = Math.round((packagesSubtotal * feeRate) / 100);
  const beforeVat = packagesSubtotal + managementFee;
  const vat = Math.round((beforeVat * vatRate) / 100);
  const total = beforeVat + vat;
  const margin = total - vat - totals.cost;
  const marginPct = Math.round((margin / (total - vat)) * 1000) / 10;
  const belowFloor = marginPct < totals.marginFloorPct;

  return (
    <AppShell
      title="Quotation v2 (draft)"
      meta={
        <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <Link
            to="/deals/$dealCode"
            params={{ dealCode }}
            className="inline-flex items-center hover:text-ember"
          >
            <ChevronLeft className="size-3.5" /> Breakdown
          </Link>
          <span className="num">{dealCode}</span>· {deal.name} · {deal.client} · {deal.contact}
        </span>
      }
      actions={
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-secondary">
            <History className="size-3.5" /> Versions
          </button>
          <button className="inline-flex items-center gap-1.5 rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90">
            <Send className="size-3.5" /> Send to client
          </button>
        </div>
      }
    >
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card
            title="Quotation lines"
            subtitle="Prices come from the breakdown packages — override any package price here."
          >
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px]">
                <thead className="border-b border-border">
                  <tr>
                    <Th>Package</Th>
                    <Th className="text-right">From breakdown</Th>
                    <Th className="text-right">Quoted price</Th>
                    <Th className="text-right">Variance</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {packages.map((p) => {
                    const price = overrides[p.pkg] ?? p.price;
                    return (
                      <tr key={p.pkg} className="hover:bg-secondary/40">
                        <Td>
                          <div className="flex items-center gap-2">
                            <Pill tone="ink">{p.pkg}</Pill>
                            <span className="font-medium">{p.title}</span>
                          </div>
                          <div className="mt-0.5 text-xs text-muted-foreground">
                            {p.description}
                          </div>
                        </Td>
                        <Td className="text-right text-muted-foreground">
                          <Money value={p.memberSum} />
                        </Td>
                        <Td className="text-right">
                          <input
                            aria-label={`Quoted price ${p.pkg}`}
                            value={vnd(price)}
                            onChange={(e) =>
                              setOverrides((prev) => ({
                                ...prev,
                                [p.pkg]: Number(e.target.value.replace(/\D/g, "")) || 0,
                              }))
                            }
                            className="num w-36 rounded-lg border border-border bg-card px-2 py-1.5 text-right text-sm font-semibold outline-none focus:border-ember"
                          />
                        </Td>
                        <Td className="text-right text-ember">
                          <Money value={price - p.memberSum} sign />
                        </Td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="space-y-1.5 border-t border-border p-4 text-sm">
              <div className="flex justify-between gap-3">
                <span className="text-muted-foreground">Subtotal (packages)</span>
                <Money value={packagesSubtotal} />
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-2 text-muted-foreground">
                  Management fee
                  <input
                    aria-label="Management fee rate"
                    type="number"
                    value={feeRate}
                    onChange={(e) => setFeeRate(Number(e.target.value) || 0)}
                    className="num w-16 rounded-md border border-border bg-card px-1.5 py-1 text-right text-xs outline-none focus:border-ember"
                  />
                  %
                </span>
                <Money value={managementFee} />
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-muted-foreground">Total before VAT</span>
                <Money value={beforeVat} />
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-2 text-muted-foreground">
                  VAT
                  <input
                    aria-label="VAT rate"
                    type="number"
                    value={vatRate}
                    onChange={(e) => setVatRate(Number(e.target.value) || 0)}
                    className="num w-16 rounded-md border border-border bg-card px-1.5 py-1 text-right text-xs outline-none focus:border-ember"
                  />
                  %
                </span>
                <Money value={vat} />
              </div>
              <div className="flex justify-between gap-3 border-t border-border pt-2 font-display text-base font-semibold">
                <span>Total</span>
                <Money value={total} />
              </div>
            </div>
          </Card>
        </div>

        <div className="space-y-4">
          <Card title="Client detail level" subtitle="How much the client sees on the PDF">
            <div className="space-y-1.5 p-4">
              {detailLevels.map((d) => (
                <button
                  key={d}
                  onClick={() => setDetail(d)}
                  className={
                    detail === d
                      ? "flex w-full items-center gap-2 rounded-lg border border-ember bg-ember-soft px-3 py-2 text-left text-sm font-medium text-ember"
                      : "flex w-full items-center gap-2 rounded-lg border border-border px-3 py-2 text-left text-sm text-muted-foreground hover:bg-secondary"
                  }
                >
                  {d}
                </button>
              ))}
            </div>
          </Card>

          <Card
            title="Margin check"
            subtitle="Founder only — derived from breakdown cost"
            tone="ink"
          >
            <dl className="space-y-1.5 p-4 text-sm">
              <div className="flex justify-between gap-3">
                <dt className="text-primary-foreground/60">Cost (breakdown)</dt>
                <dd>
                  <Money value={totals.cost} />
                </dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-primary-foreground/60">Margin</dt>
                <dd>
                  <Money value={margin} />
                </dd>
              </div>
              <div className="flex justify-between gap-3 border-t border-white/10 pt-2 font-semibold">
                <dt>Margin %</dt>
                <dd className="num">
                  {marginPct}%{" "}
                  <span className="ml-1 text-xs font-normal opacity-60">
                    floor {totals.marginFloorPct}% · {belowFloor ? "below floor" : "above floor"}
                  </span>
                </dd>
              </div>
            </dl>
          </Card>

          <Card title="Versions">
            <ul className="divide-y divide-border">
              {quoteVersions.map((v) => (
                <li key={v.version} className="px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className="num text-sm font-semibold">{v.version}</span>
                      <Pill tone={v.status === "Published" ? "ember" : "neutral"}>{v.status}</Pill>
                    </div>
                    <Money value={v.total} className="text-sm" />
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    Published {v.published} · {v.opens}
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}

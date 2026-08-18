import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/aura/AppShell";
import { Card, Pill } from "@/components/aura/primitives";
import { totals } from "@/data/fixture";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — margin floor, fees and terms | AuraOS" },
      {
        name: "description",
        content:
          "Global defaults: margin floor, management fee, VAT, markup by source, payment terms and letterhead.",
      },
      { property: "og:title", content: "Settings — margin floor, fees and terms" },
      {
        property: "og:description",
        content: "Pricing defaults, payment terms and document letterhead for the studio.",
      },
    ],
  }),
  component: SettingsPage,
});

function Field({
  label,
  value,
  hint,
  suffix,
}: {
  label: string;
  value: string;
  hint?: string;
  suffix?: string;
}) {
  return (
    <div>
      <label className="label-caps">{label}</label>
      <div className="mt-1.5 flex items-center gap-2 rounded-lg border border-border px-3 py-2 focus-within:border-ember">
        <input
          defaultValue={value}
          className="num w-full bg-transparent text-sm outline-none"
        />
        {suffix ? <span className="text-xs text-muted-foreground">{suffix}</span> : null}
      </div>
      {hint ? <p className="mt-1 text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

const markups = [
  { source: "Internal", markup: "20", note: "Studio-delivered work" },
  { source: "Freelancer", markup: "15", note: "Crew and individual talent" },
  { source: "Vendor", markup: "20", note: "Companies issuing invoices" },
  { source: "Không hoá đơn", markup: "10", note: "No invoice — cash lines" },
];

function SettingsPage() {
  return (
    <AppShell
      title="Settings"
      meta="Studio-wide defaults — new deals inherit these values"
      actions={
        <button className="rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90">
          Save changes
        </button>
      }
    >
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Pricing floors" subtitle="Warnings fire when a quote drops below the floor">
          <div className="grid gap-4 p-4 sm:grid-cols-2">
            <Field
              label="Margin floor"
              value={String(totals.marginFloorPct)}
              suffix="%"
              hint="Current deal sits at 22.2%"
            />
            <Field label="Management fee" value={String(totals.managementFeeRate)} suffix="%" />
            <Field label="VAT rate" value={String(totals.vatRate)} suffix="%" />
            <Field label="Founder commission (CMF)" value="5" suffix="%" />
          </div>
        </Card>

        <Card title="Default markup by source">
          <ul className="divide-y divide-border">
            {markups.map((m) => (
              <li key={m.source} className="flex items-center gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium">{m.source}</div>
                  <div className="mt-0.5 text-xs text-muted-foreground">{m.note}</div>
                </div>
                <div className="flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5">
                  <input
                    defaultValue={m.markup}
                    className="num w-10 bg-transparent text-right text-sm outline-none"
                  />
                  <span className="text-xs text-muted-foreground">%</span>
                </div>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Payment terms" subtitle="Default milestone split on new deals">
          <div className="grid gap-4 p-4 sm:grid-cols-3">
            <Field label="Đặt cọc" value="40" suffix="%" />
            <Field label="Sau ghi hình" value="30" suffix="%" />
            <Field label="Bàn giao" value="30" suffix="%" />
          </div>
          <div className="grid gap-4 border-t border-border p-4 sm:grid-cols-2">
            <Field label="Net terms" value="15" suffix="days" />
            <Field
              label="Overdue nudge after"
              value="3"
              suffix="days"
              hint="Adds the deal to Attention Required on Home"
            />
          </div>
        </Card>

        <Card title="Letterhead & documents">
          <div className="space-y-4 p-4">
            <Field label="Legal entity" value="Công ty TNHH Aura Production" />
            <Field label="Tax code" value="0316 552 118" />
            <Field label="Registered address" value="19 Nguyễn Đình Chiểu, Q1, TP.HCM" />
            <Field label="Bank account" value="Vietcombank · 0071 0004 55221" />
            <div>
              <div className="label-caps">Contract number format</div>
              <div className="num mt-1.5 rounded-lg border border-border bg-secondary/50 px-3 py-2 text-sm">
                HĐ-{"{year}"}/AURA-{"{client_code}"}-{"{seq}"}
              </div>
            </div>
          </div>
        </Card>

        <Card
          className="lg:col-span-2"
          title="Roles"
          subtitle="Founder-only data stays gated on the server"
        >
          <ul className="divide-y divide-border">
            {[
              { role: "Founder", tone: "ember", can: "Everything, including margin, commission and net profit" },
              { role: "Producer", tone: "ink", can: "Deals, jobs, expenses, paperwork — no margin figures" },
              { role: "Accountant", tone: "neutral", can: "Milestones, invoices, settlements, exports" },
              { role: "Crew", tone: "outline", can: "Quick expense entry on their own float only" },
            ].map((r) => (
              <li key={r.role} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <Pill tone={r.tone}>{r.role}</Pill>
                <span className="min-w-0 flex-1 text-sm text-muted-foreground">{r.can}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </AppShell>
  );
}

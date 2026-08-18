import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { AppShell } from "@/components/aura/AppShell";
import { Card, Money, Pill, Stat, Td, Th } from "@/components/aura/primitives";
import { FinanceTabs } from "@/components/aura/FinanceTabs";
import { FormDialog, type FieldDef } from "@/components/aura/FormDialog";
import { incomeRows as seedIncome, sum, type IncomeRow } from "@/data/finance";

export const Route = createFileRoute("/finance/income")({
  head: () => ({
    meta: [
      { title: "Income & receivables — invoices and collections | AuraOS" },
      {
        name: "description",
        content:
          "Every client invoice with amount, VAT, due date and collection status, plus what is still outstanding.",
      },
      { property: "og:title", content: "Income & receivables — AuraOS" },
      {
        property: "og:description",
        content: "Invoices, VAT, due dates and collection status per deal.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: IncomePage,
});

const statusTone: Record<IncomeRow["status"], string> = {
  "Đã thu": "positive",
  "Chờ thu": "neutral",
  "Quá hạn": "ember",
};

const filters = ["All", "Đã thu", "Chờ thu", "Quá hạn"] as const;

const fields: FieldDef[] = [
  { name: "client", label: "Client", type: "text", required: true },
  { name: "deal", label: "Deal code", type: "text", placeholder: "DEAL-0182" },
  { name: "invoice", label: "Invoice no.", type: "text", placeholder: "INV-0182-2" },
  { name: "amount", label: "Amount (VND, excl. VAT)", type: "text", required: true },
  { name: "vatPct", label: "VAT %", type: "select", options: ["10", "8", "0"] },
  { name: "method", label: "Method", type: "select", options: ["Chuyển khoản", "Tiền mặt"] },
  { name: "due", label: "Due date", type: "text", placeholder: "30 Sep 2026" },
  { name: "status", label: "Status", type: "select", options: ["Chờ thu", "Đã thu", "Quá hạn"] },
];

function IncomePage() {
  const [rows, setRows] = useState<IncomeRow[]>(seedIncome);
  const [filter, setFilter] = useState<(typeof filters)[number]>("All");
  const [open, setOpen] = useState(false);

  const visible = useMemo(
    () => (filter === "All" ? rows : rows.filter((r) => r.status === filter)),
    [rows, filter],
  );

  const collected = sum(rows.filter((r) => r.status === "Đã thu").map((r) => r.amount));
  const outstanding = sum(rows.filter((r) => r.status !== "Đã thu").map((r) => r.amount));
  const overdue = sum(rows.filter((r) => r.status === "Quá hạn").map((r) => r.amount));

  function create(values: Record<string, string>) {
    const amount = Number((values["amount"] ?? "0").replace(/\D/g, "")) || 0;
    const vatPct = Number(values["vatPct"] ?? "10") || 0;
    const status = (values["status"] as IncomeRow["status"]) ?? "Chờ thu";
    setRows((prev) => [
      {
        id: `IN-${2100 + prev.length}`,
        date: status === "Đã thu" ? "18 Aug 2026" : "—",
        client: values["client"] ?? "Khách mới",
        deal: values["deal"] || "—",
        invoice: values["invoice"] || "—",
        amount,
        vat: Math.round((amount * vatPct) / 100),
        method: (values["method"] as IncomeRow["method"]) ?? "Chuyển khoản",
        status,
        due: values["due"] || "—",
      },
      ...prev,
    ]);
    setOpen(false);
  }

  return (
    <AppShell
      title="Income"
      meta={`${rows.length} invoices · Jan–Aug 2026`}
      actions={
        <button
          onClick={() => setOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          <Plus className="size-3.5" /> New invoice
        </button>
      }
    >
      <div className="space-y-5">
        <FinanceTabs />

        <div className="grid gap-3 sm:grid-cols-3">
          <Stat label="Collected" value={<Money value={collected} />} sub="Cash in the bank" />
          <Stat label="Outstanding" value={<Money value={outstanding} />} sub="Invoiced, not paid" />
          <Stat label="Overdue" value={<Money value={overdue} />} sub="Past the due date" alert />
        </div>

        <Card
          title="Invoices"
          subtitle="Client billing and collection status"
          action={
            <div className="flex gap-1">
              {filters.map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`rounded-md border px-2 py-1 text-[11px] transition-colors ${
                    filter === f
                      ? "border-transparent bg-primary text-primary-foreground"
                      : "border-border text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          }
        >
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-border">
                <tr>
                  <Th>Invoice</Th>
                  <Th>Client</Th>
                  <Th>Deal</Th>
                  <Th>Paid on</Th>
                  <Th>Due</Th>
                  <Th className="text-right">Amount</Th>
                  <Th className="text-right">VAT</Th>
                  <Th>Method</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {visible.map((r) => (
                  <tr key={r.id} className="hover:bg-secondary/50">
                    <Td className="font-medium">{r.invoice}</Td>
                    <Td>{r.client}</Td>
                    <Td className="text-muted-foreground">{r.deal}</Td>
                    <Td className="text-muted-foreground">{r.date}</Td>
                    <Td className={r.status === "Quá hạn" ? "text-ember" : "text-muted-foreground"}>
                      {r.due}
                    </Td>
                    <Td className="text-right">
                      <Money value={r.amount} />
                    </Td>
                    <Td className="text-right text-muted-foreground">
                      <Money value={r.vat} />
                    </Td>
                    <Td className="text-muted-foreground">{r.method}</Td>
                    <Td>
                      <Pill tone={statusTone[r.status]}>{r.status}</Pill>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <FormDialog
        open={open}
        onClose={() => setOpen(false)}
        title="New invoice"
        subtitle="Record a client billing and its due date"
        submitLabel="Create invoice"
        fields={fields}
        onSubmit={create}
      />
    </AppShell>
  );
}

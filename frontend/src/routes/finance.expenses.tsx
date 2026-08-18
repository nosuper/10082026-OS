import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { AppShell } from "@/components/aura/AppShell";
import { Card, Money, Pill, Stat, Td, Th } from "@/components/aura/primitives";
import { Bar, FinanceTabs } from "@/components/aura/FinanceTabs";
import { FormDialog, type FieldDef } from "@/components/aura/FormDialog";
import { expenseByCategory, expenseRows as seedExpenses, sum, type ExpenseRow } from "@/data/finance";

export const Route = createFileRoute("/finance/expenses")({
  head: () => ({
    meta: [
      { title: "Expenses & payables — crew, vendors and overhead | AuraOS" },
      {
        name: "description",
        content:
          "Every cost logged against a job with category, payee, tax type and payment status, plus spend by category.",
      },
      { property: "og:title", content: "Expenses & payables — AuraOS" },
      {
        property: "og:description",
        content: "Costs per job with payee, tax type and payment status.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ExpensesPage,
});

const statusTone: Record<ExpenseRow["status"], string> = {
  "Đã trả": "positive",
  "Chờ trả": "neutral",
  "Chờ đối chiếu": "ember",
};

const filters = ["All", "Đã trả", "Chờ trả", "Chờ đối chiếu"] as const;

const fields: FieldDef[] = [
  { name: "what", label: "Description", type: "text", required: true, span: 2 },
  {
    name: "category",
    label: "Category",
    type: "select",
    options: ["Crew", "Equipment", "Art", "Catering", "Transport", "Production", "Post-production", "Overhead"],
  },
  { name: "job", label: "Job", type: "select", options: ["JOB-0182", "JOB-0171", "JOB-0166", "—"] },
  { name: "payee", label: "Payee", type: "text" },
  {
    name: "taxType",
    label: "Tax type",
    type: "select",
    options: ["Công ty", "Cá nhân", "Không hoá đơn"],
  },
  { name: "amount", label: "Amount (VND)", type: "text", required: true },
  {
    name: "status",
    label: "Status",
    type: "select",
    options: ["Chờ trả", "Đã trả", "Chờ đối chiếu"],
  },
];

function ExpensesPage() {
  const [rows, setRows] = useState<ExpenseRow[]>(seedExpenses);
  const [filter, setFilter] = useState<(typeof filters)[number]>("All");
  const [open, setOpen] = useState(false);

  const visible = useMemo(
    () => (filter === "All" ? rows : rows.filter((r) => r.status === filter)),
    [rows, filter],
  );

  const paid = sum(rows.filter((r) => r.status === "Đã trả").map((r) => r.amount));
  const due = sum(rows.filter((r) => r.status === "Chờ trả").map((r) => r.amount));
  const unmatched = sum(rows.filter((r) => r.status === "Chờ đối chiếu").map((r) => r.amount));
  const maxCat = Math.max(...expenseByCategory.map((c) => c.amount));

  function create(values: Record<string, string>) {
    const amount = Number((values["amount"] ?? "0").replace(/\D/g, "")) || 0;
    setRows((prev) => [
      {
        id: `EX-${4500 + prev.length}`,
        date: "18 Aug 2026",
        what: values["what"] ?? "Chi phí mới",
        category: values["category"] ?? "Crew",
        job: values["job"] ?? "—",
        payee: values["payee"] || "—",
        taxType: (values["taxType"] as ExpenseRow["taxType"]) ?? "Công ty",
        amount,
        status: (values["status"] as ExpenseRow["status"]) ?? "Chờ trả",
      },
      ...prev,
    ]);
    setOpen(false);
  }

  return (
    <AppShell
      title="Expenses"
      meta={`${rows.length} entries · Jan–Aug 2026`}
      actions={
        <button
          onClick={() => setOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          <Plus className="size-3.5" /> New expense
        </button>
      }
    >
      <div className="space-y-5">
        <FinanceTabs />

        <div className="grid gap-3 sm:grid-cols-3">
          <Stat label="Paid" value={<Money value={paid} />} sub="Settled with payee" />
          <Stat label="Due to pay" value={<Money value={due} />} sub="Approved, not paid" />
          <Stat
            label="Waiting on receipts"
            value={<Money value={unmatched} />}
            sub="Float not yet matched"
            alert
          />
        </div>

        <Card
          title="Expense log"
          subtitle="Job costs and studio overhead"
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
                  <Th>Date</Th>
                  <Th>Description</Th>
                  <Th>Category</Th>
                  <Th>Job</Th>
                  <Th>Payee</Th>
                  <Th>Tax</Th>
                  <Th className="text-right">Amount</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {visible.map((r) => (
                  <tr key={r.id} className="hover:bg-secondary/50">
                    <Td className="text-muted-foreground whitespace-nowrap">{r.date}</Td>
                    <Td className="font-medium">{r.what}</Td>
                    <Td className="text-muted-foreground">{r.category}</Td>
                    <Td className="text-muted-foreground">{r.job}</Td>
                    <Td className="text-muted-foreground">{r.payee}</Td>
                    <Td>
                      <Pill tone={r.taxType === "Không hoá đơn" ? "ember" : "neutral"}>
                        {r.taxType}
                      </Pill>
                    </Td>
                    <Td className="text-right">
                      <Money value={r.amount} />
                    </Td>
                    <Td>
                      <Pill tone={statusTone[r.status]}>{r.status}</Pill>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Spend by category" subtitle="Year to date">
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

      <FormDialog
        open={open}
        onClose={() => setOpen(false)}
        title="New expense"
        subtitle="Log a cost against a job or studio overhead"
        submitLabel="Log expense"
        fields={fields}
        onSubmit={create}
      />
    </AppShell>
  );
}

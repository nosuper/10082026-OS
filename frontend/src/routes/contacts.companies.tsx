import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Plus, Search, X } from "lucide-react";
import { AppShell } from "@/components/aura/AppShell";
import { Card, Money, Pill, Td, Th } from "@/components/aura/primitives";
import { FormDialog, type FieldDef } from "@/components/aura/FormDialog";

export const Route = createFileRoute("/contacts/companies")({
  head: () => ({
    meta: [
      { title: "Companies — AuraOS contacts" },
      {
        name: "description",
        content:
          "Client, vendor, crew and partner companies with tax codes, primary contacts and linked deals.",
      },
      { property: "og:title", content: "Companies — AuraOS contacts" },
      {
        property: "og:description",
        content: "Company directory with type pills, tax codes and linked deals.",
      },
    ],
  }),
  component: CompaniesPage,
});

type Company = {
  name: string;
  type: "Client" | "Vendor" | "Crew" | "Partner";
  contact: string;
  deals: number;
  taxCode: string;
  billed: number;
  address: string;
  bank: string;
  people: { name: string; role: string }[];
  dealList: string[];
};

const seedCompanies: Company[] = [
  {
    name: "Nhất Minh Beverage",
    type: "Client",
    contact: "Chị Phạm Thu Hà",
    deals: 4,
    taxCode: "0312 456 789",
    billed: 2_140_000_000,
    address: "Lầu 8, Toà nhà Sun Wah, Q1, TP.HCM",
    bank: "Vietcombank · 0071 0007 12345",
    people: [
      { name: "Phạm Thu Hà", role: "Marketing Director" },
      { name: "Ngô Anh Tuấn", role: "Brand Manager" },
    ],
    dealList: ['TVC Tết 2027 "Vị Xuân"', "KV Summer 2026", "Digital series Q4"],
  },
  {
    name: "Hải Đăng Rental",
    type: "Vendor",
    contact: "Anh Lê Hải Đăng",
    deals: 11,
    taxCode: "0309 887 221",
    billed: 780_000_000,
    address: "45 Nguyễn Thị Thập, Q7, TP.HCM",
    bank: "Techcombank · 1903 4567 8901",
    people: [{ name: "Lê Hải Đăng", role: "Owner" }],
    dealList: ['TVC Tết 2027 "Vị Xuân"', "Brand film Sài Gòn Xanh"],
  },
  {
    name: "Sắc Màu Post",
    type: "Vendor",
    contact: "Chị Đỗ Kim Ngân",
    deals: 7,
    taxCode: "0314 220 118",
    billed: 312_000_000,
    address: "12 Trần Quốc Thảo, Q3, TP.HCM",
    bank: "ACB · 2288 1199 4455",
    people: [{ name: "Đỗ Kim Ngân", role: "Colourist / Owner" }],
    dealList: ['TVC Tết 2027 "Vị Xuân"'],
  },
  {
    name: "Xưởng Mộc Tân Phú",
    type: "Vendor",
    contact: "Anh Bùi Văn Thành",
    deals: 5,
    taxCode: "0311 004 552",
    billed: 465_000_000,
    address: "88 Lê Trọng Tấn, Tân Phú, TP.HCM",
    bank: "BIDV · 3141 5926 5358",
    people: [{ name: "Bùi Văn Thành", role: "Art fabrication lead" }],
    dealList: ['TVC Tết 2027 "Vị Xuân"', "Retail launch Nam Long"],
  },
  {
    name: "Casting Sài Gòn",
    type: "Partner",
    contact: "Chị Hồ Thanh Trúc",
    deals: 9,
    taxCode: "0313 776 090",
    billed: 198_000_000,
    address: "23 Hồ Xuân Hương, Q3, TP.HCM",
    bank: "MB Bank · 0099 8877 6655",
    people: [{ name: "Hồ Thanh Trúc", role: "Casting director" }],
    dealList: ['TVC Tết 2027 "Vị Xuân"'],
  },
];

const typeTone: Record<Company["type"], string> = {
  Client: "ink",
  Vendor: "neutral",
  Crew: "outline",
  Partner: "ember",
};

const companyFields: FieldDef[] = [
  { name: "name", label: "Company name", required: true, span: 2, placeholder: "Nhất Minh Beverage" },
  { name: "type", label: "Type", type: "select", options: ["Client", "Vendor", "Crew", "Partner"] },
  { name: "taxCode", label: "Tax code", placeholder: "0312 456 789" },
  { name: "contact", label: "Primary contact", required: true, placeholder: "Chị Phạm Thu Hà" },
  { name: "role", label: "Contact role", placeholder: "Marketing Director" },
  { name: "address", label: "Address", span: 2, placeholder: "Lầu 8, Toà nhà Sun Wah, Q1, TP.HCM" },
  { name: "bank", label: "Bank account", span: 2, placeholder: "Vietcombank · 0071 0007 12345" },
];

function CompaniesPage() {
  const [q, setQ] = useState("");
  const [type, setType] = useState<"All" | Company["type"]>("All");
  const [open, setOpen] = useState<Company | null>(null);
  const [companies, setCompanies] = useState<Company[]>(seedCompanies);
  const [newOpen, setNewOpen] = useState(false);

  const rows = companies.filter(
    (c) =>
      (type === "All" || c.type === type) &&
      (c.name.toLowerCase().includes(q.toLowerCase()) ||
        c.contact.toLowerCase().includes(q.toLowerCase())),
  );

  const counts = companies.reduce<Record<string, number>>((acc, c) => {
    acc[c.type] = (acc[c.type] ?? 0) + 1;
    return acc;
  }, {});

  function createCompany(v: Record<string, string>) {
    const company: Company = {
      name: v["name"] ?? "Untitled company",
      type: (v["type"] as Company["type"]) ?? "Client",
      contact: v["contact"] ?? "",
      deals: 0,
      taxCode: v["taxCode"] ?? "—",
      billed: 0,
      address: v["address"] ?? "—",
      bank: v["bank"] ?? "—",
      people: v["contact"]
        ? [{ name: v["contact"], role: v["role"] || "Primary contact" }]
        : [],
      dealList: [],
    };
    setCompanies((prev) => [company, ...prev]);
    setNewOpen(false);
  }

  return (
    <AppShell
      title="Companies"
      meta={`${companies.length} companies · ${(["Client", "Vendor", "Crew", "Partner"] as const)
        .filter((t) => counts[t])
        .map((t) => `${counts[t]} ${t.toLowerCase()}`)
        .join(", ")}`}
      actions={
        <button
          onClick={() => setNewOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90"
        >
          <Plus className="size-3.5" /> New company
        </button>
      }
    >
      <FormDialog
        open={newOpen}
        title="New company"
        subtitle="Companies hold tax details, bank info and their people."
        fields={companyFields}
        submitLabel="Create company"
        onClose={() => setNewOpen(false)}
        onSubmit={createCompany}
      />

      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex min-w-[220px] flex-1 items-center gap-2 rounded-lg border border-border bg-card px-2.5 py-2">
            <Search className="size-3.5 text-muted-foreground" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search companies"
              className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
          </div>
          {(["All", "Client", "Vendor", "Crew", "Partner"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setType(t)}
              className={
                type === t
                  ? "rounded-lg bg-primary px-2.5 py-2 text-xs font-medium text-primary-foreground"
                  : "rounded-lg border border-border bg-card px-2.5 py-2 text-xs text-muted-foreground hover:text-foreground"
              }
            >
              {t}
            </button>
          ))}
        </div>

        <Card title="Directory">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px]">
              <thead className="border-b border-border">
                <tr>
                  <Th>Company</Th>
                  <Th>Type</Th>
                  <Th>Primary contact</Th>
                  <Th className="text-right">Deals</Th>
                  <Th>Tax code</Th>
                  <Th className="text-right">Billed to date</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {rows.map((c) => (
                  <tr
                    key={c.name}
                    onClick={() => setOpen(c)}
                    className="cursor-pointer hover:bg-secondary/50"
                  >
                    <Td className="font-medium">{c.name}</Td>
                    <Td>
                      <Pill tone={typeTone[c.type]}>{c.type}</Pill>
                    </Td>
                    <Td className="text-muted-foreground">{c.contact}</Td>
                    <Td className="num text-right">{c.deals}</Td>
                    <Td className="num text-muted-foreground">{c.taxCode}</Td>
                    <Td className="text-right">
                      <Money value={c.billed} />
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {open ? (
        <div className="fixed inset-0 z-50 flex">
          <button
            aria-label="Close"
            onClick={() => setOpen(null)}
            className="flex-1 bg-primary/20 backdrop-blur-[1px]"
          />
          <aside className="w-full max-w-md overflow-y-auto border-l border-border bg-card p-5">
            <div className="flex items-start gap-3">
              <div className="min-w-0 flex-1">
                <h2 className="font-display text-lg font-semibold">{open.name}</h2>
                <div className="mt-1 flex items-center gap-2">
                  <Pill tone={typeTone[open.type]}>{open.type}</Pill>
                  <span className="num text-xs text-muted-foreground">{open.taxCode}</span>
                </div>
              </div>
              <button
                onClick={() => setOpen(null)}
                className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary"
              >
                <X className="size-4" />
              </button>
            </div>

            <dl className="mt-5 space-y-3 text-sm">
              <div>
                <dt className="label-caps">Address</dt>
                <dd className="mt-1">{open.address}</dd>
              </div>
              <div>
                <dt className="label-caps">Bank</dt>
                <dd className="num mt-1">{open.bank}</dd>
              </div>
              <div>
                <dt className="label-caps">Billed to date</dt>
                <dd className="mt-1">
                  <Money value={open.billed} />
                </dd>
              </div>
            </dl>

            <div className="mt-5">
              <div className="label-caps">People</div>
              <ul className="mt-2 divide-y divide-border rounded-lg border border-border">
                {open.people.map((p) => (
                  <li key={p.name} className="flex items-center justify-between gap-2 px-3 py-2.5">
                    <span className="text-sm font-medium">{p.name}</span>
                    <span className="text-xs text-muted-foreground">{p.role}</span>
                  </li>
                ))}
              </ul>
              <button className="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs hover:bg-secondary">
                <Plus className="size-3.5" /> Add person to {open.name}
              </button>
            </div>

            <div className="mt-5">
              <div className="label-caps">Linked deals</div>
              <ul className="mt-2 space-y-1.5">
                {open.dealList.map((d) => (
                  <li key={d} className="rounded-lg border border-border px-3 py-2 text-sm">
                    {d}
                  </li>
                ))}
              </ul>
            </div>
          </aside>
        </div>
      ) : null}
    </AppShell>
  );
}

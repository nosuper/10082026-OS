import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Plus, Search, X, Phone, Mail } from "lucide-react";
import { AppShell } from "@/components/aura/AppShell";
import { Card, Pill, Td, Th } from "@/components/aura/primitives";

export const Route = createFileRoute("/contacts/people")({
  head: () => ({
    meta: [
      { title: "People — AuraOS contacts" },
      {
        name: "description",
        content:
          "Individual contacts with phone, email, role tags and the company they belong to, plus roles across deals.",
      },
      { property: "og:title", content: "People — AuraOS contacts" },
      {
        property: "og:description",
        content: "Crew, clients and freelancers with their roles across deals.",
      },
    ],
  }),
  component: PeoplePage,
});

type Person = {
  name: string;
  phone: string;
  email: string;
  company: string;
  tags: string[];
  roles: { role: string; deal: string }[];
};

const people: Person[] = [
  {
    name: "Phạm Thu Hà",
    phone: "0903 118 224",
    email: "ha.pham@nhatminh.vn",
    company: "Nhất Minh Beverage",
    tags: ["Client"],
    roles: [
      { role: "Client contact", deal: 'TVC Tết 2027 "Vị Xuân"' },
      { role: "Client contact", deal: "KV Summer 2026" },
    ],
  },
  {
    name: "Nguyễn Hoàng Duy",
    phone: "0938 447 010",
    email: "duy.nguyen@gmail.com",
    company: "—",
    tags: ["Crew", "Director"],
    roles: [{ role: "Director", deal: 'TVC Tết 2027 "Vị Xuân"' }],
  },
  {
    name: "Vũ Đình Nam",
    phone: "0977 220 561",
    email: "nam.vu.dop@gmail.com",
    company: "—",
    tags: ["Crew", "DOP"],
    roles: [
      { role: "DOP", deal: 'TVC Tết 2027 "Vị Xuân"' },
      { role: "DOP", deal: "Brand film Sài Gòn Xanh" },
    ],
  },
  {
    name: "Trần Mỹ Linh",
    phone: "0912 003 887",
    email: "linh.tran@aura.vn",
    company: "Aura Production",
    tags: ["Internal", "Producer"],
    roles: [{ role: "Producer", deal: 'TVC Tết 2027 "Vị Xuân"' }],
  },
  {
    name: "Đặng Thu Trang",
    phone: "0965 771 402",
    email: "trang.dang.edit@gmail.com",
    company: "—",
    tags: ["Crew", "Editor"],
    roles: [{ role: "Offline editor", deal: 'TVC Tết 2027 "Vị Xuân"' }],
  },
  {
    name: "Lê Hải Đăng",
    phone: "0908 555 121",
    email: "dang@haidangrental.vn",
    company: "Hải Đăng Rental",
    tags: ["Vendor"],
    roles: [{ role: "Equipment vendor", deal: 'TVC Tết 2027 "Vị Xuân"' }],
  },
];

const tagTone: Record<string, string> = {
  Client: "ink",
  Crew: "outline",
  Vendor: "neutral",
  Internal: "ember",
};

function PeoplePage() {
  const [q, setQ] = useState("");
  const [tag, setTag] = useState("All");
  const [open, setOpen] = useState<Person | null>(null);

  const rows = people.filter(
    (p) =>
      (tag === "All" || p.tags.includes(tag)) &&
      (p.name.toLowerCase().includes(q.toLowerCase()) ||
        p.company.toLowerCase().includes(q.toLowerCase())),
  );

  return (
    <AppShell
      title="People"
      meta={`${people.length} contacts · roles resolved across deals`}
      actions={
        <button className="inline-flex items-center gap-1.5 rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90">
          <Plus className="size-3.5" /> New person
        </button>
      }
    >
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex min-w-[220px] flex-1 items-center gap-2 rounded-lg border border-border bg-card px-2.5 py-2">
            <Search className="size-3.5 text-muted-foreground" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search people or company"
              className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
          </div>
          {["All", "Client", "Crew", "Vendor", "Internal"].map((t) => (
            <button
              key={t}
              onClick={() => setTag(t)}
              className={
                tag === t
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
            <table className="w-full min-w-[780px]">
              <thead className="border-b border-border">
                <tr>
                  <Th>Name</Th>
                  <Th>Phone</Th>
                  <Th>Email</Th>
                  <Th>Company</Th>
                  <Th>Roles</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {rows.map((p) => (
                  <tr
                    key={p.name}
                    onClick={() => setOpen(p)}
                    className="cursor-pointer hover:bg-secondary/50"
                  >
                    <Td className="font-medium">{p.name}</Td>
                    <Td className="num text-muted-foreground">{p.phone}</Td>
                    <Td className="text-muted-foreground">{p.email}</Td>
                    <Td className="text-muted-foreground">{p.company}</Td>
                    <Td>
                      <span className="flex flex-wrap gap-1">
                        {p.tags.map((t) => (
                          <Pill key={t} tone={tagTone[t] ?? "neutral"}>
                            {t}
                          </Pill>
                        ))}
                      </span>
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
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {open.tags.map((t) => (
                    <Pill key={t} tone={tagTone[t] ?? "neutral"}>
                      {t}
                    </Pill>
                  ))}
                </div>
              </div>
              <button
                onClick={() => setOpen(null)}
                className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary"
              >
                <X className="size-4" />
              </button>
            </div>

            <div className="mt-5 space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <Phone className="size-3.5 text-muted-foreground" />
                <span className="num">{open.phone}</span>
              </div>
              <div className="flex items-center gap-2">
                <Mail className="size-3.5 text-muted-foreground" />
                <span>{open.email}</span>
              </div>
            </div>

            <div className="mt-5">
              <label className="label-caps" htmlFor="company">
                Company
              </label>
              <input
                id="company"
                defaultValue={open.company}
                className="mt-1.5 w-full rounded-lg border border-border bg-transparent px-3 py-2 text-sm outline-none focus:border-ember"
              />
            </div>

            <div className="mt-5">
              <div className="label-caps">Roles across deals</div>
              <ul className="mt-2 divide-y divide-border rounded-lg border border-border">
                {open.roles.map((r) => (
                  <li key={r.role + r.deal} className="px-3 py-2.5">
                    <div className="text-sm font-medium">{r.role}</div>
                    <div className="mt-0.5 text-xs text-muted-foreground">{r.deal}</div>
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

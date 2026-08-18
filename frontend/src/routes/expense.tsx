import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Camera, Check, ChevronDown } from "lucide-react";
import { AppShell } from "@/components/aura/AppShell";
import { Card, Money, Pill } from "@/components/aura/primitives";
import { expenseCategories } from "@/data/fixture";

export const Route = createFileRoute("/expense")({
  head: () => ({
    meta: [
      { title: "Quick expense — capture on set | AuraOS" },
      {
        name: "description",
        content:
          "One-thumb expense capture on set: amount, category, receipt photo, and the crew float balance it settles against.",
      },
      { property: "og:title", content: "Quick expense — capture on set" },
      {
        property: "og:description",
        content: "Log a spend in seconds and see the float balance update.",
      },
    ],
  }),
  component: ExpensePage,
});

const recent = [
  { what: "Catering day 2 — 41 pax", cat: "Catering", amount: 9_800_000, when: "Today 12:40", state: "Pending" },
  { what: "Grab transport — art team", cat: "Transport", amount: 640_000, when: "Today 08:15", state: "Matched" },
  { what: "Props — hoa mai giả", cat: "Art", amount: 2_150_000, when: "Yesterday", state: "Matched" },
];

function ExpensePage() {
  const [amount, setAmount] = useState("");
  const [cat, setCat] = useState(expenseCategories[3] ?? "Catering");
  const [note, setNote] = useState("");
  const [saved, setSaved] = useState(false);

  const advance = 15_000_000;
  const spent = 12_590_000;
  const float = advance - spent;

  return (
    <AppShell title="Quick expense" meta="TVC Tết 2027 “Vị Xuân” · JOB-0182 · Trần Mỹ Linh">
      <div className="mx-auto max-w-md space-y-4">
        <Card tone="ink" title="Your float" subtitle="Advance minus matched expenses">
          <div className="grid grid-cols-3 gap-2 p-4 text-sm">
            <div>
              <div className="text-[11px] tracking-wide text-primary-foreground/50 uppercase">
                Advance
              </div>
              <Money value={advance} className="mt-1 block" />
            </div>
            <div>
              <div className="text-[11px] tracking-wide text-primary-foreground/50 uppercase">
                Spent
              </div>
              <Money value={spent} className="mt-1 block" />
            </div>
            <div>
              <div className="text-[11px] tracking-wide text-primary-foreground/50 uppercase">
                Left
              </div>
              <Money value={float} className="mt-1 block font-semibold" />
            </div>
          </div>
        </Card>

        <Card title="New expense">
          <div className="space-y-4 p-4">
            <div>
              <label className="label-caps" htmlFor="amount">
                Amount
              </label>
              <div className="mt-1.5 flex items-center gap-2 rounded-xl border border-border px-3 py-3 focus-within:border-ember">
                <input
                  id="amount"
                  inputMode="numeric"
                  value={amount}
                  onChange={(e) =>
                    setAmount(
                      e.target.value
                        .replace(/[^\d]/g, "")
                        .replace(/\B(?=(\d{3})+(?!\d))/g, "."),
                    )
                  }
                  placeholder="0"
                  className="num w-full bg-transparent text-2xl font-semibold outline-none placeholder:text-muted-foreground/50"
                />
                <span className="text-lg text-muted-foreground">₫</span>
              </div>
            </div>

            <div>
              <label className="label-caps" htmlFor="cat">
                Category
              </label>
              <div className="relative mt-1.5">
                <select
                  id="cat"
                  value={cat}
                  onChange={(e) => setCat(e.target.value)}
                  className="w-full appearance-none rounded-xl border border-border bg-transparent px-3 py-3 text-sm outline-none focus:border-ember"
                >
                  {expenseCategories.map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-muted-foreground" />
              </div>
            </div>

            <div>
              <label className="label-caps" htmlFor="note">
                Note
              </label>
              <input
                id="note"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Bữa trưa ngày 2 — 41 pax"
                className="mt-1.5 w-full rounded-xl border border-border bg-transparent px-3 py-3 text-sm outline-none focus:border-ember"
              />
            </div>

            <button className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-border-strong py-6 text-sm text-muted-foreground hover:border-ember hover:text-ember">
              <Camera className="size-5" /> Attach receipt photo
            </button>

            <button
              onClick={() => setSaved(true)}
              className="w-full rounded-xl bg-ember py-4 text-sm font-semibold text-ember-foreground hover:opacity-90"
            >
              {saved ? "Saved — float updated" : "Save expense"}
            </button>
            {saved ? (
              <p className="flex items-center justify-center gap-1.5 text-xs text-muted-foreground">
                <Check className="size-3.5 text-ember" /> Awaiting producer match
              </p>
            ) : null}
          </div>
        </Card>

        <Card title="Today & yesterday">
          <ul className="divide-y divide-border">
            {recent.map((r) => (
              <li key={r.what} className="flex items-center gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium">{r.what}</div>
                  <div className="mt-0.5 text-xs text-muted-foreground">
                    {r.cat} · {r.when}
                  </div>
                </div>
                <div className="text-right">
                  <Money value={r.amount} className="block text-sm" />
                  <Pill tone={r.state === "Pending" ? "ember" : "neutral"} className="mt-1">
                    {r.state}
                  </Pill>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </AppShell>
  );
}

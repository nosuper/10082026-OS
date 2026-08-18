import { createFileRoute, Link } from "@tanstack/react-router";
import { Fragment, useState } from "react";
import {
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Copy,
  Download,
  GitCompare,
  Globe,
  GripVertical,
  Link2,
  Minus,
  Plus,
  Send,
  Trash2,
} from "lucide-react";
import { AppShell } from "@/components/aura/AppShell";
import { Card, Money, Pill, Td, Th } from "@/components/aura/primitives";
import { costLines, deal, totals, vnd } from "@/data/fixture";
import {
  clientContacts,
  isDivider,
  lineAmount,
  lineUnitPrice,
  memberSum,
  packageTemplates,
  seedOpenLog,
  seedQuoteLines,
  unitOptions,
  versionShares,
  versionSnapshots,
  type OpenEvent,
  type QuoteLine,
} from "@/data/quotations";

export const Route = createFileRoute("/quotations/$quoteRef")({
  head: () => ({
    meta: [
      { title: "Quotation builder — AuraOS" },
      {
        name: "description",
        content:
          "Build a client quotation from package templates and breakdown lines, preview the PDF, publish a shareable link and track every client open.",
      },
      { property: "og:title", content: "Quotation builder — AuraOS" },
      {
        property: "og:description",
        content:
          "Compose quotation packages from breakdown lines, override prices, preview, publish and compare options.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: QuotationDetailPage,
});

type Tab = "Editor" | "PDF preview" | "Share & tracking" | "Compare";
const tabs: Tab[] = ["Editor", "PDF preview", "Share & tracking", "Compare"];

function QuotationDetailPage() {
  const { quoteRef } = Route.useParams();
  const isNew = quoteRef === "new";

  const [tab, setTab] = useState<Tab>("Editor");
  const [name, setName] = useState(
    isNew ? 'Quotation — TVC Tết 2027 "Vị Xuân" (v3 draft)' : 'Quotation — TVC Tết 2027 "Vị Xuân"',
  );
  const [status, setStatus] = useState<"Draft" | "Published">(isNew ? "Draft" : "Published");
  const [lines, setLines] = useState<QuoteLine[]>(isNew ? [] : seedQuoteLines);
  const [expanded, setExpanded] = useState<string[]>([]);
  const [feeRate, setFeeRate] = useState(totals.managementFeeRate);
  const [vatRate, setVatRate] = useState(totals.vatRate);
  const [validDays, setValidDays] = useState(14);
  const [contact, setContact] = useState(clientContacts[0]!.name);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [compareTo, setCompareTo] = useState(versionSnapshots[0]!.version);
  const [log, setLog] = useState<OpenEvent[]>(isNew ? [] : seedOpenLog);
  const [dragId, setDragId] = useState<string | null>(null);
  const [dragOverId, setDragOverId] = useState<string | null>(null);
  const [shareVersion, setShareVersion] = useState("current");

  const contactPerson = clientContacts.find((c) => c.name === contact) ?? clientContacts[0]!;
  const contactLabel = `${contactPerson.name}, ${contactPerson.role}`;
  const shareUrl = `https://aura.studio/q/${isNew ? "quo-0182-3" : quoteRef.toLowerCase()}-x7f2`;

  const subtotal = lines.reduce((a, l) => a + lineAmount(l), 0);
  const fee = Math.round((subtotal * feeRate) / 100);
  const beforeVat = subtotal + fee;
  const vat = Math.round((beforeVat * vatRate) / 100);
  const total = beforeVat + vat;
  const cost = lines.reduce(
    (a, l) => a + costLines.filter((c) => l.lineIds.includes(c.id)).reduce((s, c) => s + c.subtotal, 0),
    0,
  );
  const margin = beforeVat - cost;
  const marginPct = beforeVat > 0 ? Math.round((margin / beforeVat) * 1000) / 10 : 0;
  const belowFloor = marginPct < totals.marginFloorPct;

  function addLine(line: Omit<QuoteLine, "id">) {
    const id = `L${lines.length + 1}-${Date.now()}`;
    setLines((prev) => [...prev, { ...line, id }]);
    setExpanded((prev) => [...prev, id]);
  }

  function patch(id: string, next: Partial<QuoteLine>) {
    setLines((prev) => prev.map((l) => (l.id === id ? { ...l, ...next } : l)));
  }

  function addDivider() {
    addLine({
      kind: "divider",
      label: "Section — type a title or note for the client",
      lineIds: [],
      qty: 0,
      unit: "package",
      overrideUnitPrice: 0,
    });
  }

  /** Move the dragged row so it lands at the target row's position */
  function reorder(fromId: string, toId: string) {
    if (fromId === toId) return;
    setLines((prev) => {
      const from = prev.findIndex((l) => l.id === fromId);
      const to = prev.findIndex((l) => l.id === toId);
      if (from < 0 || to < 0) return prev;
      const next = [...prev];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved!);
      return next;
    });
  }

  function publish() {
    setStatus("Published");
    setLog((prev) => [
      {
        when: "18 Aug 2026 · 23:11",
        who: "Trần Quốc Bảo",
        where: "Ho Chi Minh City, VN",
        device: "macOS · Chrome",
        detail: `Published ${isNew ? "v3" : "revision"} · link created`,
      },
      ...prev,
    ]);
    setTab("Share & tracking");
  }

  // Every shareable version of this quotation — the one being edited plus past ones
  const shareEntries = [
    {
      key: "current",
      version: isNew ? "v3" : "v2 (editing)",
      name,
      status,
      slug: shareUrl.split("/q/")[1]!,
      recipient: contactPerson.email,
      published: status === "Published" ? "18 Aug 2026" : "—",
      log,
    },
    ...versionShares
      .filter((v) => isNew || v.version !== "v2")
      .map((v) => ({
        key: v.version,
        version: v.version,
        name: v.name,
        status: v.status as string,
        slug: v.slug,
        recipient: v.recipient,
        published: v.published,
        log: v.log,
      })),
  ];
  const activeShare = shareEntries.find((s) => s.key === shareVersion) ?? shareEntries[0]!;
  const activeShareUrl = `https://aura.studio/q/${activeShare.slug}`;
  const opens = (l: OpenEvent[]) => l.filter((e) => e.detail.startsWith("Opened")).length;

  const other = versionSnapshots.find((v) => v.version === compareTo)!;
  const otherBeforeVat = other.subtotal + Math.round((other.subtotal * other.feeRate) / 100);
  const otherMargin = otherBeforeVat - other.cost;
  const otherMarginPct = Math.round((otherMargin / otherBeforeVat) * 1000) / 10;

  return (
    <AppShell
      title={name}
      meta={
        <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <Link to="/quotations" className="inline-flex items-center hover:text-ember">
            <ChevronLeft className="size-3.5" /> Quotations
          </Link>
          <span className="num">{isNew ? "QUO-0182-3" : quoteRef}</span>· from{" "}
          <Link to="/deals/$dealCode" params={{ dealCode: deal.code }} className="hover:text-ember">
            {deal.code} breakdown
          </Link>
          · {deal.client} · <Pill tone={status === "Published" ? "ember" : "outline"}>{status}</Pill>
        </span>
      }
      actions={
        <div className="flex items-center gap-2">
          <button
            onClick={() => window.print()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-secondary"
          >
            <Download className="size-3.5" /> Download PDF
          </button>
          <button
            onClick={publish}
            className="inline-flex items-center gap-1.5 rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90"
          >
            <Send className="size-3.5" /> {status === "Published" ? "Republish" : "Publish & share"}
          </button>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-1.5">
          {tabs.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={
                tab === t
                  ? "rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground"
                  : "rounded-lg border border-border bg-card px-3 py-2 text-xs text-muted-foreground hover:text-foreground"
              }
            >
              {t}
            </button>
          ))}
        </div>

        {tab === "Editor" ? (
          <div className="space-y-4">
            <Card title="Quotation name" subtitle="What the client sees as the document title">
              <div className="p-4">
                <input
                  aria-label="Quotation name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-lg border border-border bg-card px-3 py-2.5 font-display text-base font-semibold outline-none focus:border-ember"
                />
              </div>
            </Card>

            <Card
              title="Quotation packages"
              subtitle="Drag rows by the handle to reorder. Open a package to add, edit or remove lines."
              action={
                <div className="flex items-center gap-2">
                  <button
                    onClick={addDivider}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium hover:bg-secondary"
                  >
                    <Minus className="size-3.5" /> Add text divider
                  </button>
                  <button
                    onClick={() => setPickerOpen(true)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium hover:bg-secondary"
                  >
                    <Plus className="size-3.5" /> Add package
                  </button>
                </div>
              }
            >
              <div className="overflow-x-auto">
                <table className="w-full min-w-[980px]">
                  <thead className="border-b border-border">
                    <tr>
                      <Th className="w-8" />
                      <Th>Package</Th>
                      <Th className="text-right">Qty</Th>
                      <Th>Unit</Th>
                      <Th className="text-right">Qty 2</Th>
                      <Th>Unit 2</Th>
                      <Th className="text-right">Unit price</Th>
                      <Th className="text-right">Amount</Th>
                      <Th />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {lines.map((l) => {
                      const derived = memberSum(l.lineIds);
                      const overridden = l.overrideUnitPrice !== null;
                      const open = expanded.includes(l.id);
                      const members = costLines.filter((c) => l.lineIds.includes(c.id));
                      const available = costLines.filter((c) => !l.lineIds.includes(c.id));
                      const dragProps = {
                        draggable: true,
                        onDragStart: (e: React.DragEvent) => {
                          setDragId(l.id);
                          e.dataTransfer.effectAllowed = "move";
                        },
                        onDragEnd: () => {
                          setDragId(null);
                          setDragOverId(null);
                        },
                        onDragOver: (e: React.DragEvent) => {
                          e.preventDefault();
                          if (dragId && dragId !== l.id) setDragOverId(l.id);
                        },
                        onDragLeave: () => setDragOverId((prev) => (prev === l.id ? null : prev)),
                        onDrop: (e: React.DragEvent) => {
                          e.preventDefault();
                          if (dragId) reorder(dragId, l.id);
                          setDragId(null);
                          setDragOverId(null);
                        },
                      };
                      const dragClass = `${dragId === l.id ? "opacity-40" : ""} ${
                        dragOverId === l.id ? "border-t-2 border-t-ember" : ""
                      }`;

                      if (isDivider(l)) {
                        return (
                          <tr
                            key={l.id}
                            {...dragProps}
                            className={`bg-secondary/50 hover:bg-secondary/70 ${dragClass}`}
                          >
                            <Td className="w-8 align-middle">
                              <GripVertical className="size-3.5 cursor-grab text-muted-foreground" />
                            </Td>
                            <Td colSpan={7}>
                              <input
                                aria-label={`Divider text ${l.id}`}
                                value={l.label}
                                onChange={(e) => patch(l.id, { label: e.target.value })}
                                placeholder="Section title or free text"
                                className="label-caps w-full rounded-md border border-transparent bg-transparent px-1.5 py-1 tracking-wide outline-none hover:border-border focus:border-ember"
                              />
                            </Td>
                            <Td className="text-right">
                              <button
                                aria-label={`Remove divider ${l.id}`}
                                onClick={() => setLines((prev) => prev.filter((x) => x.id !== l.id))}
                                className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-ember"
                              >
                                <Trash2 className="size-3.5" />
                              </button>
                            </Td>
                          </tr>
                        );
                      }

                      return (
                        <Fragment key={l.id}>
                          <tr {...dragProps} className={`hover:bg-secondary/40 ${dragClass}`}>
                            <Td className="w-8 align-top">
                              <GripVertical
                                aria-label={`Drag ${l.label}`}
                                className="mt-1.5 size-3.5 cursor-grab text-muted-foreground"
                              />
                            </Td>
                            <Td>
                              <div className="flex items-start gap-1.5">
                                <button
                                  aria-label={`Toggle ${l.label} lines`}
                                  onClick={() =>
                                    setExpanded((prev) =>
                                      open ? prev.filter((x) => x !== l.id) : [...prev, l.id],
                                    )
                                  }
                                  className="mt-1 rounded-md p-0.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
                                >
                                  {open ? (
                                    <ChevronDown className="size-3.5" />
                                  ) : (
                                    <ChevronRight className="size-3.5" />
                                  )}
                                </button>
                                <div className="min-w-0 flex-1">
                                  <div className="flex items-center gap-2">
                                    {l.templatePkg ? <Pill tone="ink">{l.templatePkg}</Pill> : null}
                                    <input
                                      aria-label={`Line label ${l.id}`}
                                      value={l.label}
                                      onChange={(e) => patch(l.id, { label: e.target.value })}
                                      className="w-full rounded-md border border-transparent bg-transparent px-1.5 py-1 text-sm font-medium outline-none hover:border-border focus:border-ember"
                                    />
                                  </div>
                                  <input
                                    aria-label={`Line note ${l.id}`}
                                    value={l.note ?? ""}
                                    placeholder="Client-facing note"
                                    onChange={(e) => patch(l.id, { note: e.target.value })}
                                    className="w-full rounded-md border border-transparent bg-transparent px-1.5 py-0.5 text-xs text-muted-foreground outline-none hover:border-border focus:border-ember"
                                  />
                                  <div className="num px-1.5 text-[11px] text-muted-foreground">
                                    {l.lineIds.length} breakdown line
                                    {l.lineIds.length === 1 ? "" : "s"} · <Money value={derived} />
                                  </div>
                                </div>
                              </div>
                            </Td>
                            <Td className="text-right">
                              <input
                                aria-label={`Qty ${l.id}`}
                                type="number"
                                value={l.qty}
                                onChange={(e) => patch(l.id, { qty: Number(e.target.value) || 0 })}
                                className="num w-16 rounded-md border border-border bg-card px-1.5 py-1 text-right text-sm outline-none focus:border-ember"
                              />
                            </Td>
                            <Td>
                              <UnitSelect
                                label={`Unit ${l.id}`}
                                value={l.unit}
                                onChange={(v) => patch(l.id, { unit: v })}
                              />
                            </Td>
                            <Td className="text-right">
                              <input
                                aria-label={`Qty 2 ${l.id}`}
                                type="number"
                                value={l.qty2 ?? ""}
                                placeholder="—"
                                onChange={(e) =>
                                  patch(l.id, {
                                    qty2: e.target.value === "" ? undefined : Number(e.target.value),
                                  })
                                }
                                className="num w-16 rounded-md border border-border bg-card px-1.5 py-1 text-right text-sm outline-none focus:border-ember"
                              />
                            </Td>
                            <Td>
                              <UnitSelect
                                label={`Unit 2 ${l.id}`}
                                value={l.unit2 ?? ""}
                                onChange={(v) => patch(l.id, { unit2: v || undefined })}
                                allowEmpty
                              />
                            </Td>
                            <Td className="text-right">
                              <input
                                aria-label={`Unit price ${l.id}`}
                                value={vnd(lineUnitPrice(l))}
                                onChange={(e) =>
                                  patch(l.id, {
                                    overrideUnitPrice: Number(e.target.value.replace(/\D/g, "")) || 0,
                                  })
                                }
                                className="num w-28 rounded-lg border border-border bg-card px-2 py-1.5 text-right text-sm font-semibold outline-none focus:border-ember"
                              />
                              <div className="mt-0.5 text-[11px]">
                                {overridden ? (
                                  <button
                                    onClick={() => patch(l.id, { overrideUnitPrice: null })}
                                    className="text-ember hover:underline"
                                  >
                                    overridden · reset
                                  </button>
                                ) : (
                                  <span className="text-muted-foreground">summed from lines</span>
                                )}
                              </div>
                            </Td>
                            <Td className="text-right font-semibold">
                              <Money value={lineAmount(l)} />
                            </Td>
                            <Td className="text-right">
                              <button
                                aria-label={`Remove ${l.label}`}
                                onClick={() => setLines((prev) => prev.filter((x) => x.id !== l.id))}
                                className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-ember"
                              >
                                <Trash2 className="size-3.5" />
                              </button>
                            </Td>
                          </tr>
                          {open ? (
                            <tr className="bg-secondary/30">
                              <Td colSpan={9} className="px-4 py-3">
                                <div className="label-caps mb-2">Breakdown lines in this package</div>
                                <ul className="divide-y divide-border rounded-lg border border-border bg-card">
                                  {members.map((m) => (
                                    <li
                                      key={m.id}
                                      className="flex items-center gap-3 px-3 py-2 text-sm"
                                    >
                                      <span className="min-w-0 flex-1">
                                        <span className="block font-medium">{m.description}</span>
                                        <span className="block text-xs text-muted-foreground">
                                          {m.phase} · {m.category} · {m.source} · {m.contact} ·{" "}
                                          {m.qty1} {m.unit1}
                                          {m.qty2 ? ` × ${m.qty2} ${m.unit2}` : ""}
                                        </span>
                                      </span>
                                      <Money value={m.quotePrice} className="text-xs" />
                                      <button
                                        aria-label={`Remove ${m.description}`}
                                        onClick={() =>
                                          patch(l.id, {
                                            lineIds: l.lineIds.filter((x) => x !== m.id),
                                          })
                                        }
                                        className="rounded-md p-1 text-muted-foreground hover:bg-secondary hover:text-ember"
                                      >
                                        <Trash2 className="size-3.5" />
                                      </button>
                                    </li>
                                  ))}
                                  {members.length === 0 ? (
                                    <li className="px-3 py-3 text-xs text-muted-foreground">
                                      No breakdown lines yet — add one below or price the package
                                      manually.
                                    </li>
                                  ) : null}
                                </ul>
                                <div className="mt-2 flex flex-wrap items-center gap-2">
                                  <select
                                    aria-label={`Add breakdown line to ${l.label}`}
                                    value=""
                                    onChange={(e) => {
                                      const id = Number(e.target.value);
                                      if (id) patch(l.id, { lineIds: [...l.lineIds, id] });
                                    }}
                                    className="max-w-full rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs outline-none focus:border-ember"
                                  >
                                    <option value="">+ Add breakdown line…</option>
                                    {available.map((c) => (
                                      <option key={c.id} value={c.id}>
                                        {c.pkg} · {c.description} — {vnd(c.quotePrice)} đ
                                      </option>
                                    ))}
                                  </select>
                                  <span className="num text-xs text-muted-foreground">
                                    sum of lines <Money value={derived} />
                                  </span>
                                </div>
                              </Td>
                            </tr>
                          ) : null}
                        </Fragment>
                      );
                    })}
                    {lines.length === 0 ? (
                      <tr>
                        <Td colSpan={9} className="py-10 text-center text-muted-foreground">
                          No packages yet — add a template package or create a new one.
                        </Td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>

              <div className="border-t border-border p-4">
                <div className="ml-auto w-full max-w-sm space-y-1.5 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-muted-foreground">Subtotal</span>
                    <Money value={subtotal} />
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="flex items-center gap-2 text-muted-foreground">
                      Management fee
                      <input
                        aria-label="Management fee rate"
                        type="number"
                        value={feeRate}
                        onChange={(e) => setFeeRate(Number(e.target.value) || 0)}
                        className="num w-14 rounded-md border border-border bg-card px-1.5 py-1 text-right text-xs outline-none focus:border-ember"
                      />
                      %
                    </span>
                    <Money value={fee} />
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="flex items-center gap-2 text-muted-foreground">
                      VAT
                      <input
                        aria-label="VAT rate"
                        type="number"
                        value={vatRate}
                        onChange={(e) => setVatRate(Number(e.target.value) || 0)}
                        className="num w-14 rounded-md border border-border bg-card px-1.5 py-1 text-right text-xs outline-none focus:border-ember"
                      />
                      %
                    </span>
                    <Money value={vat} />
                  </div>
                  <div className="flex items-center justify-between gap-3 border-t border-border pt-2 font-display text-base font-semibold">
                    <span>Total</span>
                    <Money value={total} />
                  </div>
                </div>
              </div>
            </Card>

            <div className="grid gap-4 md:grid-cols-2">
              <Card title="Terms" subtitle="Printed on the quotation">
                <div className="space-y-3 p-4 text-sm">
                  <label className="flex items-center justify-between gap-3">
                    <span className="text-muted-foreground">Valid for</span>
                    <span className="flex items-center gap-1.5">
                      <input
                        type="number"
                        value={validDays}
                        onChange={(e) => setValidDays(Number(e.target.value) || 0)}
                        className="num w-16 rounded-md border border-border bg-card px-1.5 py-1 text-right outline-none focus:border-ember"
                      />
                      <span className="text-xs text-muted-foreground">days</span>
                    </span>
                  </label>
                  <label className="flex items-center justify-between gap-3">
                    <span className="text-muted-foreground">Client contact</span>
                    <select
                      value={contact}
                      onChange={(e) => setContact(e.target.value)}
                      className="max-w-[62%] rounded-md border border-border bg-card px-2 py-1.5 text-sm outline-none focus:border-ember"
                    >
                      {clientContacts.map((c) => (
                        <option key={c.name} value={c.name}>
                          {c.name} — {c.role}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="flex justify-between gap-3">
                    <span className="text-muted-foreground">Contact email</span>
                    <span className="num text-xs text-muted-foreground">{contactPerson.email}</span>
                  </div>
                  <div className="flex justify-between gap-3">
                    <span className="text-muted-foreground">Client budget</span>
                    <Money value={deal.clientBudget} />
                  </div>
                </div>
              </Card>

              <Card title="Margin check" subtitle="Compared against the breakdown cost">
                <div className="space-y-4 p-4">
                  <div className="flex items-end justify-between gap-3">
                    <div>
                      <div className="label-caps">Margin</div>
                      <div className="num font-display text-2xl font-semibold leading-tight">
                        {marginPct}%
                      </div>
                      <div className="num mt-0.5 text-xs text-muted-foreground">
                        <Money value={margin} /> on <Money value={beforeVat} /> before VAT
                      </div>
                    </div>
                    <Pill tone={belowFloor ? "ember" : "positive"}>
                      {belowFloor ? "Below floor" : "Above floor"}
                    </Pill>
                  </div>

                  <div>
                    <div className="relative h-2 overflow-hidden rounded-full bg-secondary">
                      <div
                        className={`h-full rounded-full ${belowFloor ? "bg-ember" : "bg-positive"}`}
                        style={{ width: `${Math.max(0, Math.min(100, marginPct))}%` }}
                      />
                      <div
                        className="absolute inset-y-0 w-px bg-foreground/50"
                        style={{ left: `${totals.marginFloorPct}%` }}
                      />
                    </div>
                    <div className="mt-1 flex justify-between text-[11px] text-muted-foreground">
                      <span>0%</span>
                      <span className="num">floor {totals.marginFloorPct}%</span>
                      <span>100%</span>
                    </div>
                  </div>

                  <dl className="grid grid-cols-2 gap-3 border-t border-border pt-3 text-sm">
                    <div>
                      <dt className="text-xs text-muted-foreground">Cost (breakdown)</dt>
                      <dd className="num font-medium">
                        <Money value={cost} />
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">Quoted before VAT</dt>
                      <dd className="num font-medium">
                        <Money value={beforeVat} />
                      </dd>
                    </div>
                  </dl>
                </div>
              </Card>
            </div>
          </div>
        ) : null}

        {tab === "PDF preview" ? (
          <div className="grid gap-4 lg:grid-cols-[1fr_260px]">
            <div className="flex justify-center rounded-xl border border-border bg-secondary/50 p-6">
              <article className="w-full max-w-[720px] rounded-lg border border-border bg-card p-10 shadow-sm">
                <header className="flex items-start justify-between gap-6 border-b border-border pb-6">
                  <div>
                    <div className="font-display text-lg font-bold">Aura Production House</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      12 Nguyễn Huệ, Quận 1, TP.HCM · MST 0312345678
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="label-caps">Quotation</div>
                    <div className="num mt-1 text-sm font-semibold">
                      {isNew ? "QUO-0182-3" : quoteRef}
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      18 Aug 2026 · valid {validDays} days
                    </div>
                  </div>
                </header>

                <h1 className="mt-6 font-display text-xl font-semibold tracking-tight">{name}</h1>
                <div className="mt-1 text-sm text-muted-foreground">
                  {deal.client} · {contactLabel}
                </div>

                <table className="mt-6 w-full">
                  <thead className="border-b border-border">
                    <tr>
                      <Th>Description</Th>
                      <Th className="text-right">Qty</Th>
                      <Th className="text-right">Unit price</Th>
                      <Th className="text-right">Amount</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {lines.map((l) =>
                      isDivider(l) ? (
                        <tr key={l.id} className="bg-secondary/50">
                          <Td colSpan={4} className="label-caps tracking-wide">
                            {l.label}
                          </Td>
                        </tr>
                      ) : (
                      <tr key={l.id}>
                        <Td>
                          <div className="font-medium">{l.label}</div>
                          {l.note ? (
                            <div className="mt-0.5 text-xs text-muted-foreground">{l.note}</div>
                          ) : null}
                        </Td>
                        <Td className="num text-right">
                          {l.qty} {l.unit}
                          {l.qty2 ? ` × ${l.qty2} ${l.unit2 ?? ""}` : ""}
                        </Td>
                        <Td className="text-right">
                          <Money value={lineUnitPrice(l)} />
                        </Td>
                        <Td className="text-right font-semibold">
                          <Money value={lineAmount(l)} />
                        </Td>
                       </tr>
                      ),
                    )}
                  </tbody>
                </table>

                <div className="mt-6 ml-auto max-w-xs space-y-1.5 text-sm">
                  <div className="flex justify-between gap-3">
                    <span className="text-muted-foreground">Subtotal</span>
                    <Money value={subtotal} />
                  </div>
                  <div className="flex justify-between gap-3">
                    <span className="text-muted-foreground">Management fee {feeRate}%</span>
                    <Money value={fee} />
                  </div>
                  <div className="flex justify-between gap-3">
                    <span className="text-muted-foreground">VAT {vatRate}%</span>
                    <Money value={vat} />
                  </div>
                  <div className="flex justify-between gap-3 border-t border-border pt-2 font-display text-base font-semibold">
                    <span>Total</span>
                    <Money value={total} />
                  </div>
                </div>

                <footer className="mt-10 border-t border-border pt-4 text-xs text-muted-foreground">
                  Payment terms 50% on signing, 50% on delivery. Quotation valid {validDays} days
                  from issue date.
                </footer>
              </article>
            </div>
            <Card title="Export">
              <div className="space-y-2 p-4 text-sm">
                <button
                  onClick={() => window.print()}
                  className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90"
                >
                  <Download className="size-3.5" /> Download PDF
                </button>
                <p className="text-xs text-muted-foreground">
                  The client sees exactly this page — internal cost, markups and margin never
                  appear.
                </p>
              </div>
            </Card>
          </div>
        ) : null}

        {tab === "Share & tracking" ? (
          <div className="space-y-4">
            <Card
              title="Shared versions"
              subtitle="Every version of this quotation, its link and its client activity"
            >
              <div className="overflow-x-auto">
                <table className="w-full min-w-[820px]">
                  <thead className="border-b border-border">
                    <tr>
                      <Th>Version</Th>
                      <Th>Status</Th>
                      <Th>Sent to</Th>
                      <Th>Published</Th>
                      <Th className="text-right">Opens</Th>
                      <Th>Last activity</Th>
                      <Th />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {shareEntries.map((s) => {
                      const active = s.key === activeShare.key;
                      return (
                        <tr
                          key={s.key}
                          onClick={() => setShareVersion(s.key)}
                          className={`cursor-pointer ${active ? "bg-ember-soft/40" : "hover:bg-secondary/40"}`}
                        >
                          <Td>
                            <span className="num font-semibold">{s.version}</span>
                            <div className="max-w-[280px] truncate text-xs text-muted-foreground">
                              {s.name}
                            </div>
                          </Td>
                          <Td>
                            <Pill tone={s.status === "Published" ? "ember" : "neutral"}>
                              {s.status}
                            </Pill>
                          </Td>
                          <Td className="text-xs text-muted-foreground">{s.recipient}</Td>
                          <Td className="num text-xs text-muted-foreground">{s.published}</Td>
                          <Td className="num text-right">{opens(s.log)}</Td>
                          <Td className="num text-xs text-muted-foreground">
                            {s.log[0]?.when ?? "No activity"}
                          </Td>
                          <Td className="text-right">
                            <button
                              aria-label={`Copy link for ${s.version}`}
                              onClick={(e) => {
                                e.stopPropagation();
                                void navigator.clipboard?.writeText(
                                  `https://aura.studio/q/${s.slug}`,
                                );
                                setShareVersion(s.key);
                                setCopied(true);
                                window.setTimeout(() => setCopied(false), 1600);
                              }}
                              className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-ember"
                            >
                              <Copy className="size-3.5" />
                            </button>
                          </Td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>

            <div className="grid gap-4 lg:grid-cols-3">
              <Card
                title={`Link — ${activeShare.version}`}
                subtitle="Read-only client view"
                className="lg:col-span-1"
              >
                <div className="space-y-3 p-4">
                  <div className="flex items-center gap-2 rounded-lg border border-border bg-secondary/60 px-2.5 py-2">
                    <Link2 className="size-3.5 shrink-0 text-muted-foreground" />
                    <span className="num truncate text-xs">{activeShareUrl}</span>
                  </div>
                  <button
                    onClick={() => {
                      void navigator.clipboard?.writeText(activeShareUrl);
                      setCopied(true);
                      window.setTimeout(() => setCopied(false), 1600);
                    }}
                    className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-secondary"
                  >
                    {copied ? (
                      <Check className="size-3.5 text-positive" />
                    ) : (
                      <Copy className="size-3.5" />
                    )}
                    {copied ? "Copied" : "Copy link"}
                  </button>
                  <dl className="space-y-1.5 border-t border-border pt-3 text-sm">
                    <div className="flex justify-between gap-3">
                      <dt className="text-muted-foreground">Status</dt>
                      <dd>
                        <Pill tone={activeShare.status === "Published" ? "ember" : "outline"}>
                          {activeShare.status}
                        </Pill>
                      </dd>
                    </div>
                    <div className="flex justify-between gap-3">
                      <dt className="text-muted-foreground">Sent to</dt>
                      <dd className="text-right text-xs">{activeShare.recipient}</dd>
                    </div>
                    <div className="flex justify-between gap-3">
                      <dt className="text-muted-foreground">Opens</dt>
                      <dd className="num">{opens(activeShare.log)}</dd>
                    </div>
                    <div className="flex justify-between gap-3">
                      <dt className="text-muted-foreground">Link expiry</dt>
                      <dd>{validDays} days</dd>
                    </div>
                  </dl>
                </div>
              </Card>

              <Card
                title="Tracking log"
                subtitle={`Where, when and what the client did with ${activeShare.version}`}
                className="lg:col-span-2"
              >
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[620px]">
                    <thead className="border-b border-border">
                      <tr>
                        <Th>When</Th>
                        <Th>Who</Th>
                        <Th>Where</Th>
                        <Th>Device</Th>
                        <Th>Event</Th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {activeShare.log.map((e, i) => (
                        <tr key={`${e.when}-${i}`} className="hover:bg-secondary/40">
                          <Td className="num whitespace-nowrap text-xs">{e.when}</Td>
                          <Td className="text-sm">{e.who}</Td>
                          <Td className="text-xs text-muted-foreground">
                            <span className="inline-flex items-center gap-1">
                              <Globe className="size-3" />
                              {e.where}
                            </span>
                          </Td>
                          <Td className="text-xs text-muted-foreground">{e.device}</Td>
                          <Td className="text-sm">{e.detail}</Td>
                        </tr>
                      ))}
                      {activeShare.log.length === 0 ? (
                        <tr>
                          <Td colSpan={5} className="py-10 text-center text-muted-foreground">
                            Nothing yet — publish this version to create a link and start tracking.
                          </Td>
                        </tr>
                      ) : null}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          </div>
        ) : null}

        {tab === "Compare" ? (
          <div className="space-y-4">
            <Card
              title="Compare versions"
              subtitle="This quotation vs another version or option for the same deal"
              action={
                <select
                  aria-label="Compare against"
                  value={compareTo}
                  onChange={(e) => setCompareTo(e.target.value)}
                  className="max-w-[280px] rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs outline-none focus:border-ember"
                >
                  {versionSnapshots.map((v) => (
                    <option key={v.version} value={v.version}>
                      {v.version} — {v.name}
                    </option>
                  ))}
                </select>
              }
            >
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px]">
                  <thead className="border-b border-border">
                    <tr>
                      <Th>Line</Th>
                      <Th className="text-right">This quotation</Th>
                      <Th className="text-right">{other.version}</Th>
                      <Th className="text-right">Difference</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {mergeLines(
                      lines.map((l) => ({ label: l.label, amount: lineAmount(l) })),
                      other.lines,
                    ).map((r) => (
                      <tr key={r.label} className="hover:bg-secondary/40">
                        <Td className="font-medium">{r.label}</Td>
                        <Td className="text-right">
                          {r.a === null ? (
                            <span className="text-xs text-muted-foreground">not included</span>
                          ) : (
                            <Money value={r.a} />
                          )}
                        </Td>
                        <Td className="text-right text-muted-foreground">
                          {r.b === null ? (
                            <span className="text-xs">not included</span>
                          ) : (
                            <Money value={r.b} />
                          )}
                        </Td>
                        <Td
                          className={
                            r.diff === 0 ? "text-right text-muted-foreground" : "text-right text-ember"
                          }
                        >
                          <Money value={r.diff} sign />
                        </Td>
                      </tr>
                    ))}
                    <tr className="bg-secondary/50 font-semibold">
                      <Td>Total (incl. VAT)</Td>
                      <Td className="text-right">
                        <Money value={total} />
                      </Td>
                      <Td className="text-right">
                        <Money value={other.total} />
                      </Td>
                      <Td className="text-right text-ember">
                        <Money value={total - other.total} sign />
                      </Td>
                    </tr>
                    <tr>
                      <Td className="text-muted-foreground">Margin %</Td>
                      <Td className="num text-right">{marginPct}%</Td>
                      <Td className="num text-right text-muted-foreground">{otherMarginPct}%</Td>
                      <Td className="num text-right text-ember">
                        {Math.round((marginPct - otherMarginPct) * 10) / 10} pts
                      </Td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="flex items-center gap-2 border-t border-border p-4 text-xs text-muted-foreground">
                <GitCompare className="size-3.5" />
                {other.version} was {other.status.toLowerCase()} on {other.published} · fee{" "}
                {other.feeRate}% · VAT {other.vatRate}%
              </div>
            </Card>

            <Card title="All options for this deal" subtitle="Demo data — versions and priced options">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px]">
                  <thead className="border-b border-border">
                    <tr>
                      <Th>Version</Th>
                      <Th>Status</Th>
                      <Th>Date</Th>
                      <Th className="text-right">Subtotal</Th>
                      <Th className="text-right">Total</Th>
                      <Th className="text-right">Margin %</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {versionSnapshots.map((v) => {
                      const bv = v.subtotal + Math.round((v.subtotal * v.feeRate) / 100);
                      const pct = Math.round(((bv - v.cost) / bv) * 1000) / 10;
                      return (
                        <tr
                          key={v.version}
                          onClick={() => setCompareTo(v.version)}
                          className="cursor-pointer hover:bg-secondary/40"
                        >
                          <Td>
                            <span className="num font-semibold">{v.version}</span>
                            <div className="text-xs text-muted-foreground">{v.name}</div>
                          </Td>
                          <Td>
                            <Pill tone={v.status === "Published" ? "ember" : "neutral"}>
                              {v.status}
                            </Pill>
                          </Td>
                          <Td className="num text-xs text-muted-foreground">{v.published}</Td>
                          <Td className="text-right">
                            <Money value={v.subtotal} />
                          </Td>
                          <Td className="text-right font-semibold">
                            <Money value={v.total} />
                          </Td>
                          <Td className="num text-right">{pct}%</Td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        ) : null}
      </div>

      {pickerOpen ? (
        <PackagePicker
          onClose={() => setPickerOpen(false)}
          onAdd={(line) => {
            addLine(line);
            setPickerOpen(false);
          }}
        />
      ) : null}
    </AppShell>
  );
}

function UnitSelect({
  label,
  value,
  onChange,
  allowEmpty,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  allowEmpty?: boolean;
}) {
  return (
    <select
      aria-label={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-24 rounded-md border border-border bg-card px-1.5 py-1 text-xs outline-none focus:border-ember"
    >
      {allowEmpty ? <option value="">—</option> : null}
      {unitOptions.map((u) => (
        <option key={u} value={u}>
          {u}
        </option>
      ))}
    </select>
  );
}

function mergeLines(
  a: { label: string; amount: number }[],
  b: { label: string; amount: number }[],
) {
  const labels = Array.from(new Set([...a.map((x) => x.label), ...b.map((x) => x.label)]));
  return labels.map((label) => {
    const av = a.find((x) => x.label === label)?.amount ?? null;
    const bv = b.find((x) => x.label === label)?.amount ?? null;
    return { label, a: av, b: bv, diff: (av ?? 0) - (bv ?? 0) };
  });
}

function PackagePicker({
  onClose,
  onAdd,
}: {
  onClose: () => void;
  onAdd: (line: Omit<QuoteLine, "id">) => void;
}) {
  const [newName, setNewName] = useState("");

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-primary/40 p-4 backdrop-blur-sm sm:p-8">
      <div className="w-full max-w-2xl rounded-xl border border-border bg-card shadow-xl">
        <header className="flex items-start gap-3 border-b border-border px-5 py-4">
          <div className="min-w-0 flex-1">
            <h2 className="font-display text-sm font-semibold">Add package</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Pick a template package from the breakdown, or create an empty package. You can add,
              edit and remove its breakdown lines afterwards.
            </p>
          </div>
          <button onClick={onClose} className="text-xs text-muted-foreground hover:text-foreground">
            Close
          </button>
        </header>

        <div className="max-h-[52vh] space-y-4 overflow-y-auto p-5">
          <div>
            <div className="label-caps mb-2">Template packages</div>
            <div className="space-y-2">
              {packageTemplates.map((p) => (
                <button
                  key={p.pkg}
                  onClick={() =>
                    onAdd({
                      label: p.title,
                      note: p.description,
                      templatePkg: p.pkg,
                      lineIds: p.lineIds,
                      qty: 1,
                      unit: "package",
                      overrideUnitPrice: null,
                    })
                  }
                  className="flex w-full items-center gap-3 rounded-lg border border-border px-3 py-2.5 text-left hover:border-ember hover:bg-ember-soft/40"
                >
                  <Pill tone="ink">{p.pkg}</Pill>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-medium">{p.title}</span>
                    <span className="block text-xs text-muted-foreground">
                      {p.description} · {p.lineIds.length} breakdown lines
                    </span>
                  </span>
                  <Money value={p.sum} className="text-sm font-semibold" />
                </button>
              ))}
            </div>
          </div>

          <div className="border-t border-border pt-4">
            <div className="label-caps mb-2">Create new package</div>
            <div className="flex flex-wrap items-center gap-2">
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Package name, e.g. Social cutdowns x12"
                className="min-w-0 flex-1 rounded-lg border border-border bg-card px-3 py-2 text-sm outline-none focus:border-ember"
              />
              <button
                disabled={!newName.trim()}
                onClick={() =>
                  onAdd({
                    label: newName.trim(),
                    lineIds: [],
                    qty: 1,
                    unit: "package",
                    overrideUnitPrice: 0,
                  })
                }
                className="rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90 disabled:opacity-40"
              >
                Create package
              </button>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              An empty package starts at 0 đ — open it to pull in breakdown lines or type your own
              price.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

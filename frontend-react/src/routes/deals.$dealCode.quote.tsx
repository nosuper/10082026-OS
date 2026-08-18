// The deal breakdown, on real data.
//
// A producer prices a deal line by line against the record itself: quantities,
// units, unit price, tax type, vendor management fee and markup, with the three
// money columns - subtotal, quote price, margin - coming back from the server's
// pricing engine on every edit. Nothing here multiplies money.
//
// The Vue screen this replaces is frontend/src/pages/DealBreakdownPage.vue: same
// doctype, same field list, the same auraos.api.compute_breakdown recompute and
// the same frappe.client.save write.
//
// Packages, the fee and VAT dials, the detail level and publishing are the quote
// surface (#88) and are deliberately not edited here; this screen passes the
// deal's stored packages and rates through to the engine untouched, because the
// client-facing prices are what the margin and the floor warning are measured
// against.

import { useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { AlertTriangle, ChevronDown, ChevronLeft, ChevronUp, Plus, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { AppShell } from "@/components/aura/AppShell";
import { useSession } from "@/components/aura/SessionProvider";
import { Card, Money, Pill, Td, Th } from "@/components/aura/primitives";
import { Empty, ErrorState, QueryStates } from "@/components/aura/states";
import { countLabel, parseVnd, vnd } from "@/lib/format";
import { listsOf, useDoc, useList, useMethod, useMethodMutation } from "@/lib/queries";

export const Route = createFileRoute("/deals/$dealCode/quote")({
  head: () => ({
    meta: [
      { title: "Deal breakdown - AuraOS" },
      {
        name: "description",
        content:
          "Price a deal line by line: quantities, unit prices, tax type and markup, with subtotal, quote price and margin computed by the server.",
      },
      { property: "og:title", content: "Deal breakdown - AuraOS" },
      {
        property: "og:description",
        content: "Cost lines with server-computed subtotal, quote price and margin.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: BreakdownPage,
});

// -- the vocabulary the backend enforces -------------------------------------

// Deal Cost Line.tax_type, exactly as the doctype spells them. Internal work
// carries no invoice: Không hoá đơn.
const TAX_TYPES = ["Công ty", "Cá nhân", "Không hoá đơn"];

const COST_PHASES = ["Pre-production", "Production", "Post-production", "Appendix"];

const SOURCE_TYPES = ["Internal", "Freelancer", "Vendor"];

// A new row carries the doctype's own defaults, so an untouched line saves.
const NEW_LINE: LineFields = {
  description: "",
  item_category: "",
  cost_phase: "",
  source_type: "Internal",
  source_contact: "",
  package: "",
  qty1: 1,
  qty1_unit: "",
  qty2: 1,
  qty2_unit: "",
  unit_price: 0,
  tax_type: "Không hoá đơn",
  vendor_mf_pct: 0,
  markup_pct: 0,
};

// The quiet pause after the last keystroke before the page saves itself. Long
// enough to type a description into, short enough that a closed laptop has not
// lost anything.
const AUTOSAVE_MS = 2500;

// The pause before asking the engine again. Money on screen has to keep up with
// typing without a request per character.
const RECOMPUTE_MS = 400;

// -- what this screen sends and reads ----------------------------------------

type LineFields = {
  description: string;
  item_category: string;
  cost_phase: string;
  source_type: string;
  source_contact: string;
  package: string;
  qty1: number;
  qty1_unit: string;
  qty2: number;
  qty2_unit: string;
  unit_price: number;
  tax_type: string;
  vendor_mf_pct: number;
  markup_pct: number;
};

/** A row on screen. `key` is React's, never the server's, and never sent. */
type Line = LineFields & { key: string };

type PackageRow = {
  title: string | null;
  description: string | null;
  price_override: number | null;
  has_price_override: number | null;
};

type DealDoc = {
  name: string;
  title: string | null;
  stage: string;
  company: string | null;
  quote_mf_pct: number | null;
  vat_pct: number | null;
  quote_detail_level: string | null;
  commission_pct: number | null;
  cost_lines: Partial<LineFields>[] | null;
  packages: PackageRow[] | null;
};

/** What auraos.api.compute_breakdown returns for one line. */
type LineView = {
  subtotal: number;
  cost_basis: number;
  input_vat: number;
  quote_price: number;
  margin: number;
};

/** Founder-only. Absent from a producer's payload, not blanked in it. */
type FounderView = {
  commission_pct: number;
  total_commission: number;
  cm: number;
  profit_before_tax: number;
  tndn: number;
  net_profit: number;
  total_input_vat: number;
  vat_payable: number;
  margin_floor_pct: number;
};

type BreakdownView = {
  lines: LineView[];
  subtotal: number;
  management_fee: number;
  vat: number;
  total: number;
  margin: number;
  margin_pct: number | null;
  floor_breached: boolean;
  founder?: FounderView;
};

type NamedRow = { name: string };
type ContactRow = { name: string; full_name: string | null };

// -- the detail columns ------------------------------------------------------
//
// Real fields, but not what pricing a job needs on screen. Off by default so the
// table fits a laptop; the choice sticks per user, in the browser, because it is
// a habit rather than data.

const META_COLUMNS = [
  { key: "item_category", label: "Item Category", width: 150 },
  { key: "cost_phase", label: "Cost Phase", width: 150 },
  { key: "source_type", label: "Source Type", width: 130 },
  { key: "source_contact", label: "Source Contact", width: 160 },
] as const;

// The columns after the detail block, in order: package, the two quantity
// pairs, unit price, tax type, the two rates, then the frozen band - subtotal,
// quote price, margin, row controls. The table is laid out fixed from these, so
// the frozen band's right offsets below are arithmetic rather than a guess.
const TAIL_WIDTHS = [150, 72, 90, 72, 90, 150, 150, 78, 78, 132, 132, 132, 84];
const DESCRIPTION_WIDTH = 180;

type MetaKey = (typeof META_COLUMNS)[number]["key"];

const META_KEYS = META_COLUMNS.map((column) => column.key);

function columnsKey(user: string): string {
  return `auraos.next.breakdown.columns.${user || "anon"}`;
}

function loadColumns(user: string): MetaKey[] {
  try {
    const raw = window.localStorage.getItem(columnsKey(user));
    if (!raw) return [];
    const saved = JSON.parse(raw) as unknown;
    if (!Array.isArray(saved)) return [];
    return saved.filter((key): key is MetaKey => META_KEYS.includes(key as MetaKey));
  } catch {
    // A blocked storage API must never make the editor unusable.
    return [];
  }
}

function saveColumns(user: string, keys: MetaKey[]): void {
  try {
    window.localStorage.setItem(columnsKey(user), JSON.stringify(keys));
  } catch {
    // Preferences are an enhancement, never a dependency.
  }
}

// -- small local helpers -----------------------------------------------------

/** Wait for the typing to stop before asking the server. */
function useDebounced<T>(value: T, delay: number): T {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setSettled(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);
  return settled;
}

let counter = 0;
function nextKey(): string {
  counter += 1;
  return `line-${counter}`;
}

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function num(value: unknown): number {
  return typeof value === "number" && !Number.isNaN(value) ? value : 0;
}

/** A stored child row as an editable row. */
function toLine(row: Partial<LineFields>): Line {
  return {
    key: nextKey(),
    description: text(row.description),
    item_category: text(row.item_category),
    cost_phase: text(row.cost_phase),
    source_type: text(row.source_type),
    source_contact: text(row.source_contact),
    package: text(row.package),
    qty1: num(row.qty1),
    qty2: num(row.qty2),
    qty1_unit: text(row.qty1_unit),
    qty2_unit: text(row.qty2_unit),
    unit_price: num(row.unit_price),
    tax_type: text(row.tax_type) || "Không hoá đơn",
    vendor_mf_pct: num(row.vendor_mf_pct),
    markup_pct: num(row.markup_pct),
  };
}

/** What "unsaved" is measured against: the editable state, and nothing else. */
function snapshotOf(lines: Line[], commission: number | null): string {
  return JSON.stringify({ lines: lines.map(wireLine), commission });
}

/** An untouched optional field goes back as it came: empty, not "". */
function blank(value: string): string | null {
  return value.trim() ? value.trim() : null;
}

/** The fields the server owns, in the order the doctype declares them. */
function wireLine(line: Line): Record<string, string | number | null> {
  return {
    description: line.description.trim(),
    item_category: blank(line.item_category),
    cost_phase: blank(line.cost_phase),
    source_type: blank(line.source_type),
    source_contact: blank(line.source_contact),
    package: blank(line.package),
    qty1: line.qty1,
    qty1_unit: blank(line.qty1_unit),
    qty2: line.qty2,
    qty2_unit: blank(line.qty2_unit),
    unit_price: line.unit_price,
    tax_type: line.tax_type,
    vendor_mf_pct: line.vendor_mf_pct,
    markup_pct: line.markup_pct,
  };
}

const cellInput =
  "rounded-lg border border-border bg-background px-2 py-1 text-sm outline-none focus:border-border-strong";
// Numerals read as a ledger. Vietnamese units and tax types stay in the sans
// face: the mono face has no business rendering "Không hoá đơn".
const cellNum = `num ${cellInput} text-right`;
const cellSelect = `${cellInput} max-w-40`;
const ghostButton =
  "inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium transition-colors hover:border-border-strong";
const rowIcon =
  "rounded-md p-1 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground disabled:opacity-30 disabled:hover:bg-transparent";
const headCell = "px-2 py-2";
const bodyCell = "px-2 py-1.5";
// This is the widest table in the app and it scrolls sideways. Two things must
// never scroll away: the row's name and what it costs the client. The
// description freezes to the left, the three computed money columns and the row
// controls freeze to the right, and the inputs move between them. The offsets
// are the widths of the frozen columns to their right, so they have to agree
// with the w-[...] on the cells themselves.
const stickyLeft = "sticky left-0 z-10 border-r border-border";
const stickyMoney = ["sticky right-[348px]", "sticky right-[216px]", "sticky right-[84px]"];
const moneyWidth = "w-[132px]";
// Opaque, because scrolled cells pass underneath these.
const computedCell = `bg-secondary ${moneyWidth} z-10 px-2 py-1.5 text-right`;
const actionsCell = "sticky right-0 z-10 w-[84px] bg-card px-2 py-1.5 text-right whitespace-nowrap";

const STAGE_TONE: Record<string, string> = {
  Breakdown: "ink",
  "Quote Sent": "outline",
  Negotiation: "ember",
  Won: "positive",
  Lost: "ember",
};

// -- the screen --------------------------------------------------------------

function BreakdownPage() {
  const { dealCode } = Route.useParams();
  const session = useSession();
  const client = useQueryClient();

  // -- reads ----------------------------------------------------------------

  const deal = useDoc<DealDoc>("Deal", dealCode);

  const categories = useList<NamedRow>({
    doctype: "Cost Item Category",
    fields: ["name"],
    orderBy: "name asc",
  });

  const contacts = useList<ContactRow>({
    doctype: "Party Contact",
    fields: ["name", "full_name"],
    orderBy: "full_name asc",
  });

  // -- what is being edited -------------------------------------------------

  const [serverDoc, setServerDoc] = useState<DealDoc | null>(null);
  const [lines, setLines] = useState<Line[]>([]);
  const [commission, setCommission] = useState<number | null>(null);
  const [visibleMeta, setVisibleMeta] = useState<MetaKey[]>(() => loadColumns(session.userId));
  const [failure, setFailure] = useState<unknown>(null);

  // Dirty is a snapshot comparison, not a flag: loading the deal must not count
  // as an edit, and an edit typed while a save is in flight must stay dirty.
  const [baseline, setBaseline] = useState("");

  // Seed once per deal. A later refetch of the same record must not overwrite
  // what the producer has typed since.
  const seeded = useRef("");
  useEffect(() => {
    const data = deal.data;
    if (!data || seeded.current === data.name) return;
    seeded.current = data.name;
    const seededLines = (data.cost_lines ?? []).map(toLine);
    setServerDoc(data);
    setLines(seededLines);
    setCommission(data.commission_pct ?? null);
    setBaseline(snapshotOf(seededLines, data.commission_pct ?? null));
  }, [deal.data]);

  const wireLines = useMemo(() => JSON.stringify(lines.map(wireLine)), [lines]);
  const snapshot = useMemo(() => snapshotOf(lines, commission), [lines, commission]);

  const dirty = Boolean(baseline) && snapshot !== baseline;
  // Autosave holds off while a line has no description: the save would only
  // bounce off the server's own validation, and the row says why in the border.
  const complete = lines.every((line) => line.description.trim());

  // -- the engine -----------------------------------------------------------
  //
  // Subtotal, quote price and margin are pricing decisions, so they are asked
  // for rather than worked out here. The deal's stored packages and rates ride
  // along untouched: the margin is measured against the prices a client reads,
  // and a line inside a package is priced through that package.

  const packagesJson = useMemo(
    () =>
      JSON.stringify(
        (serverDoc?.packages ?? []).map((row) => ({
          title: row.title,
          description: row.description,
          price_override: row.price_override,
          has_price_override: row.has_price_override,
        })),
      ),
    [serverDoc],
  );

  const settledLines = useDebounced(wireLines, RECOMPUTE_MS);
  const settledCommission = useDebounced(commission, RECOMPUTE_MS);

  const live = useMethod<BreakdownView>(
    "auraos.api.compute_breakdown",
    {
      lines: settledLines,
      packages: packagesJson,
      quote_mf_pct: serverDoc?.quote_mf_pct ?? 0,
      vat_pct: serverDoc?.vat_pct ?? 0,
      commission_pct: settledCommission,
    },
    { enabled: Boolean(serverDoc), staleTime: Number.POSITIVE_INFINITY },
  );

  // The previous answer stays on screen while the next one is in flight, so the
  // money columns dim rather than empty out under an edit.
  const lastView = useRef<BreakdownView | null>(null);
  useEffect(() => {
    if (live.data) lastView.current = live.data;
  }, [live.data]);
  const view = live.data ?? lastView.current;
  const settling =
    settledLines !== wireLines || settledCommission !== commission || live.isFetching;

  // -- writes ---------------------------------------------------------------

  const sent = useRef("");

  const saveDeal = useMethodMutation<DealDoc, { doc: Record<string, unknown> }>(
    "frappe.client.save",
    {
      invalidate: [listsOf("Deal")],
      onSuccess: (saved) => {
        setFailure(null);
        setServerDoc(saved);
        setBaseline(sent.current);
        // The save already returned the whole document, so hand it to the cache
        // rather than invalidating and refetching: a refetch would re-seed the
        // rows under the cursor and take the focus out of the cell being typed
        // in. ["doc", doctype, name] is the key useDoc builds; lib/queries has
        // listsOf and resultOf but no docOf to say it in one word.
        client.setQueryData(["doc", "Deal", dealCode], saved);
      },
    },
  );

  // Typing a category that does not exist yet creates it, as the Vue editor
  // does: the line's Link field would otherwise fail on save.
  const createCategory = useMethodMutation<NamedRow, { doc: Record<string, unknown> }>(
    "frappe.client.insert",
    { invalidate: [listsOf("Cost Item Category")] },
  );

  async function save(): Promise<void> {
    const base = serverDoc;
    if (!base || saveDeal.isPending) return;

    const known = new Set((categories.data ?? []).map((row) => row.name));
    const missing = [
      ...new Set(lines.map((line) => line.item_category.trim()).filter(Boolean)),
    ].filter((value) => !known.has(value));
    for (const value of missing) {
      try {
        await createCategory.mutateAsync({
          doc: { doctype: "Cost Item Category", category_name: value },
        });
      } catch (error) {
        setFailure(error);
        return;
      }
    }

    sent.current = snapshot;
    const doc: Record<string, unknown> = {
      ...base,
      doctype: "Deal",
      cost_lines: lines.map((line) => ({ ...wireLine(line), doctype: "Deal Cost Line" })),
    };
    // Producers never receive this field and the server ignores it from them.
    if (view?.founder && commission !== null) doc["commission_pct"] = commission;
    setFailure(null);
    saveDeal.mutate({ doc });
  }

  // The handlers below fire from timers and from a window listener, both of
  // which outlive the render that created them.
  const saveNow = useRef(save);
  useEffect(() => {
    saveNow.current = save;
  });

  useEffect(() => {
    if (!dirty || !complete || saveDeal.isPending) return;
    const timer = window.setTimeout(() => void saveNow.current(), AUTOSAVE_MS);
    return () => window.clearTimeout(timer);
  }, [snapshot, dirty, complete, saveDeal.isPending]);

  // The founder sits on this page for hours; muscle memory has to work.
  useEffect(() => {
    function onKeydown(event: KeyboardEvent) {
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "s") return;
      event.preventDefault();
      void saveNow.current();
    }
    window.addEventListener("keydown", onKeydown);
    return () => window.removeEventListener("keydown", onKeydown);
  }, []);

  // -- editing --------------------------------------------------------------

  function update(index: number, patch: Partial<LineFields>) {
    setLines((current) => current.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  }

  function addLine() {
    setLines((current) => [...current, { ...NEW_LINE, key: nextKey() }]);
  }

  function removeLine(index: number) {
    setLines((current) => current.filter((_, i) => i !== index));
  }

  function moveLine(index: number, delta: number) {
    setLines((current) => {
      const target = index + delta;
      if (target < 0 || target >= current.length) return current;
      const next = [...current];
      const [row] = next.splice(index, 1);
      if (!row) return current;
      next.splice(target, 0, row);
      return next;
    });
  }

  function toggleMeta(key: MetaKey) {
    const next = visibleMeta.includes(key)
      ? visibleMeta.filter((item) => item !== key)
      : META_KEYS.filter((item) => item === key || visibleMeta.includes(item));
    setVisibleMeta(next);
    saveColumns(session.userId, next);
  }

  const showing = (key: MetaKey) => visibleMeta.includes(key);

  // -- chrome ---------------------------------------------------------------

  const packageTitles = (serverDoc?.packages ?? [])
    .map((row) => row.title)
    .filter((title): title is string => Boolean(title));

  const columnCount = 14 + visibleMeta.length;

  const columnWidths = [
    DESCRIPTION_WIDTH,
    ...META_COLUMNS.filter((column) => visibleMeta.includes(column.key)).map((c) => c.width),
    ...TAIL_WIDTHS,
  ];
  const tableWidth = columnWidths.reduce((total, width) => total + width, 0);

  const marginPct = view?.margin_pct ?? null;

  const status = saveDeal.isPending
    ? "Saving..."
    : dirty && !complete
      ? "A line is missing its description - autosave is waiting"
      : dirty
        ? "Unsaved changes - autosaves in a moment, Ctrl+S saves now"
        : baseline
          ? "All changes saved"
          : "";

  const error = failure ?? (saveDeal.isError ? saveDeal.error : null);

  return (
    <AppShell
      title={serverDoc?.title || deal.data?.title || dealCode}
      meta={
        <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <Link to="/deals" className="inline-flex items-center hover:text-ember">
            <ChevronLeft className="size-3.5" /> Deals
          </Link>
          <span className="num">{dealCode}</span>
          {deal.data ? (
            <Pill tone={STAGE_TONE[deal.data.stage] ?? "neutral"}>{deal.data.stage}</Pill>
          ) : null}
          {lines.length ? <span>{countLabel(lines.length, "cost line")}</span> : null}
        </span>
      }
      actions={
        <div className="flex items-center gap-3">
          {status ? (
            <span
              className={
                dirty && !complete
                  ? "hidden text-xs text-ember sm:inline"
                  : "hidden text-xs text-muted-foreground sm:inline"
              }
            >
              {status}
            </span>
          ) : null}
          <button
            type="button"
            onClick={() => void save()}
            disabled={saveDeal.isPending || !serverDoc}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-40"
          >
            {saveDeal.isPending ? "Saving..." : "Save"}
          </button>
        </div>
      }
    >
      <div className="space-y-4">
        {view?.floor_breached ? (
          <div className="flex items-center gap-2 rounded-xl border border-ember/40 bg-ember-soft px-3 py-2.5 text-sm text-ember">
            <AlertTriangle className="size-4 shrink-0" strokeWidth={1.75} />
            <span>
              Margin is below the company floor
              {view.founder ? (
                <>
                  {" of "}
                  <span className="num">{view.founder.margin_floor_pct}%</span>
                </>
              ) : null}
              {" - this quote is flagged as unprofitable."}
            </span>
          </div>
        ) : null}

        <Card
          title="Cost lines"
          subtitle="Subtotal, quote price and margin are computed by the pricing engine, not in this browser."
          action={
            <div className="flex flex-wrap items-center gap-2">
              <details className="relative">
                <summary
                  className={`${ghostButton} cursor-pointer list-none text-muted-foreground select-none hover:text-foreground`}
                >
                  Detail columns <ChevronDown className="size-3" />
                </summary>
                <div className="absolute right-0 z-30 mt-1 w-56 rounded-xl border border-border bg-card p-2 shadow-lg">
                  {META_COLUMNS.map((column) => (
                    <label
                      key={column.key}
                      className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1 text-sm hover:bg-secondary"
                    >
                      <input
                        type="checkbox"
                        checked={showing(column.key)}
                        onChange={() => toggleMeta(column.key)}
                      />
                      {column.label}
                    </label>
                  ))}
                  <p className="mt-1 border-t border-border px-2 pt-1.5 text-[11px] text-muted-foreground">
                    Money columns are always shown.
                  </p>
                </div>
              </details>
              <button type="button" onClick={addLine} disabled={!serverDoc} className={ghostButton}>
                <Plus className="size-3" /> Add line
              </button>
            </div>
          }
        >
          <QueryStates queries={[deal]} loadingRows={6}>
            {() => (
              <div className="overflow-x-auto">
                <table className="table-fixed border-collapse" style={{ width: `${tableWidth}px` }}>
                  <colgroup>
                    {columnWidths.map((width, index) => (
                      <col key={index} style={{ width: `${width}px` }} />
                    ))}
                  </colgroup>
                  <thead className="border-b border-border">
                    <tr>
                      <Th className={`${headCell} ${stickyLeft} bg-card`}>Description</Th>
                      {showing("item_category") ? (
                        <Th className={headCell}>Item Category</Th>
                      ) : null}
                      {showing("cost_phase") ? <Th className={headCell}>Cost Phase</Th> : null}
                      {showing("source_type") ? <Th className={headCell}>Source Type</Th> : null}
                      {showing("source_contact") ? (
                        <Th className={headCell}>Source Contact</Th>
                      ) : null}
                      <Th className={headCell}>Package</Th>
                      <Th className={`${headCell} text-right`}>Qty 1</Th>
                      <Th className={headCell}>Unit 1</Th>
                      <Th className={`${headCell} text-right`}>Qty 2</Th>
                      <Th className={headCell}>Unit 2</Th>
                      <Th className={`${headCell} text-right`}>Unit price</Th>
                      <Th className={headCell}>Tax type</Th>
                      <Th className={`${headCell} text-right`}>Vendor MF %</Th>
                      <Th className={`${headCell} text-right`}>Markup %</Th>
                      <Th
                        className={`${headCell} ${stickyMoney[0]} ${moneyWidth} z-10 border-l border-border bg-card text-right`}
                      >
                        Subtotal
                      </Th>
                      <Th
                        className={`${headCell} ${stickyMoney[1]} ${moneyWidth} z-10 bg-card text-right`}
                      >
                        Quote price
                      </Th>
                      <Th
                        className={`${headCell} ${stickyMoney[2]} ${moneyWidth} z-10 bg-card text-right`}
                      >
                        Margin
                      </Th>
                      <Th className={`${headCell} sticky right-0 z-10 w-[84px] bg-card`} />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {lines.map((line, index) => {
                      const computed = view?.lines[index];
                      return (
                        <tr key={line.key} className="group hover:bg-secondary/50">
                          <Td
                            className={`${bodyCell} ${stickyLeft} bg-card group-hover:bg-secondary`}
                          >
                            <input
                              value={line.description}
                              onChange={(event) =>
                                update(index, { description: event.target.value })
                              }
                              placeholder="Description"
                              aria-label={`Description, line ${index + 1}`}
                              title="A line needs a description before it can save"
                              className={`w-full ${cellInput} ${
                                line.description.trim() ? "" : "border-ember bg-ember-soft"
                              }`}
                            />
                          </Td>

                          {showing("item_category") ? (
                            <Td className={bodyCell}>
                              <input
                                list="aura-cost-categories"
                                value={line.item_category}
                                onChange={(event) =>
                                  update(index, { item_category: event.target.value })
                                }
                                placeholder="Select or add"
                                aria-label={`Item category, line ${index + 1}`}
                                className={`w-full ${cellInput}`}
                              />
                            </Td>
                          ) : null}

                          {showing("cost_phase") ? (
                            <Td className={bodyCell}>
                              <select
                                value={line.cost_phase}
                                onChange={(event) =>
                                  update(index, { cost_phase: event.target.value })
                                }
                                aria-label={`Cost phase, line ${index + 1}`}
                                className={`w-full ${cellSelect}`}
                              >
                                <option value="" />
                                {COST_PHASES.map((phase) => (
                                  <option key={phase} value={phase}>
                                    {phase}
                                  </option>
                                ))}
                              </select>
                            </Td>
                          ) : null}

                          {showing("source_type") ? (
                            <Td className={bodyCell}>
                              <select
                                value={line.source_type}
                                onChange={(event) =>
                                  update(index, { source_type: event.target.value })
                                }
                                aria-label={`Source type, line ${index + 1}`}
                                className={`w-full ${cellSelect}`}
                              >
                                <option value="" />
                                {SOURCE_TYPES.map((type) => (
                                  <option key={type} value={type}>
                                    {type}
                                  </option>
                                ))}
                              </select>
                            </Td>
                          ) : null}

                          {showing("source_contact") ? (
                            <Td className={bodyCell}>
                              <select
                                value={line.source_contact}
                                onChange={(event) =>
                                  update(index, { source_contact: event.target.value })
                                }
                                aria-label={`Source contact, line ${index + 1}`}
                                className={`w-full ${cellSelect}`}
                              >
                                <option value="" />
                                {(contacts.data ?? []).map((contact) => (
                                  <option key={contact.name} value={contact.name}>
                                    {contact.full_name || contact.name}
                                  </option>
                                ))}
                              </select>
                            </Td>
                          ) : null}

                          <Td className={bodyCell}>
                            <select
                              value={line.package}
                              onChange={(event) => update(index, { package: event.target.value })}
                              aria-label={`Package, line ${index + 1}`}
                              className={`w-full ${cellSelect}`}
                              title="Packages are created on the quote surface"
                            >
                              <option value="">No package</option>
                              {packageTitles.map((title) => (
                                <option key={title} value={title}>
                                  {title}
                                </option>
                              ))}
                            </select>
                          </Td>

                          <Td className={bodyCell}>
                            <input
                              type="number"
                              min={0}
                              value={line.qty1}
                              onChange={(event) =>
                                update(index, { qty1: Number(event.target.value) || 0 })
                              }
                              aria-label={`Quantity 1, line ${index + 1}`}
                              className={`w-full ${cellNum}`}
                            />
                          </Td>
                          <Td className={bodyCell}>
                            <input
                              value={line.qty1_unit}
                              onChange={(event) => update(index, { qty1_unit: event.target.value })}
                              placeholder="người"
                              aria-label={`Unit 1, line ${index + 1}`}
                              className={`w-full ${cellInput}`}
                            />
                          </Td>
                          <Td className={bodyCell}>
                            <input
                              type="number"
                              min={0}
                              value={line.qty2}
                              onChange={(event) =>
                                update(index, { qty2: Number(event.target.value) || 0 })
                              }
                              aria-label={`Quantity 2, line ${index + 1}`}
                              className={`w-full ${cellNum}`}
                            />
                          </Td>
                          <Td className={bodyCell}>
                            <input
                              value={line.qty2_unit}
                              onChange={(event) => update(index, { qty2_unit: event.target.value })}
                              placeholder="ngày"
                              aria-label={`Unit 2, line ${index + 1}`}
                              className={`w-full ${cellInput}`}
                            />
                          </Td>

                          <Td className={bodyCell}>
                            <input
                              inputMode="numeric"
                              value={line.unit_price ? vnd(line.unit_price) : ""}
                              onChange={(event) =>
                                update(index, { unit_price: parseVnd(event.target.value) })
                              }
                              placeholder="0"
                              aria-label={`Unit price, line ${index + 1}`}
                              className={`w-full font-medium ${cellNum}`}
                            />
                          </Td>

                          <Td className={bodyCell}>
                            <select
                              value={line.tax_type}
                              onChange={(event) => update(index, { tax_type: event.target.value })}
                              aria-label={`Tax type, line ${index + 1}`}
                              className={`w-full ${cellSelect}`}
                            >
                              {TAX_TYPES.map((type) => (
                                <option key={type} value={type}>
                                  {type}
                                </option>
                              ))}
                            </select>
                          </Td>

                          <Td className={bodyCell}>
                            <input
                              type="number"
                              min={0}
                              value={line.vendor_mf_pct}
                              onChange={(event) =>
                                update(index, { vendor_mf_pct: Number(event.target.value) || 0 })
                              }
                              aria-label={`Vendor management fee percent, line ${index + 1}`}
                              className={`w-full ${cellNum}`}
                            />
                          </Td>
                          <Td className={bodyCell}>
                            <input
                              type="number"
                              min={0}
                              value={line.markup_pct}
                              onChange={(event) =>
                                update(index, { markup_pct: Number(event.target.value) || 0 })
                              }
                              aria-label={`Markup percent, line ${index + 1}`}
                              className={`w-full ${cellNum}`}
                            />
                          </Td>

                          <Td
                            className={`${computedCell} ${stickyMoney[0]} border-l border-border ${settling ? "opacity-50" : ""}`}
                          >
                            {computed ? (
                              <Money value={computed.subtotal} className="text-muted-foreground" />
                            ) : (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </Td>
                          <Td
                            className={`${computedCell} ${stickyMoney[1]} ${settling ? "opacity-50" : ""}`}
                          >
                            {computed ? (
                              <Money value={computed.quote_price} className="font-medium" />
                            ) : (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </Td>
                          <Td
                            className={`${computedCell} ${stickyMoney[2]} ${settling ? "opacity-50" : ""}`}
                          >
                            {computed ? (
                              <Money value={computed.margin} className="text-muted-foreground" />
                            ) : (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </Td>

                          <Td className={`${actionsCell} group-hover:bg-secondary`}>
                            <button
                              type="button"
                              className={rowIcon}
                              disabled={index === 0}
                              title="Move up"
                              aria-label={`Move line ${index + 1} up`}
                              onClick={() => moveLine(index, -1)}
                            >
                              <ChevronUp className="size-3.5" />
                            </button>
                            <button
                              type="button"
                              className={rowIcon}
                              disabled={index === lines.length - 1}
                              title="Move down"
                              aria-label={`Move line ${index + 1} down`}
                              onClick={() => moveLine(index, 1)}
                            >
                              <ChevronDown className="size-3.5" />
                            </button>
                            <button
                              type="button"
                              className={rowIcon}
                              title="Remove line"
                              aria-label={`Remove line ${index + 1}`}
                              onClick={() => removeLine(index)}
                            >
                              <X className="size-3.5" />
                            </button>
                          </Td>
                        </tr>
                      );
                    })}

                    {lines.length === 0 ? (
                      <tr>
                        <Td colSpan={columnCount}>
                          <Empty
                            title="No cost lines yet."
                            detail="Add the first one - the engine prices it as you type."
                            action={
                              <button type="button" onClick={addLine} className={ghostButton}>
                                <Plus className="size-3" /> Add line
                              </button>
                            }
                          />
                        </Td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>

                <datalist id="aura-cost-categories">
                  {(categories.data ?? []).map((row) => (
                    <option key={row.name} value={row.name} />
                  ))}
                </datalist>
              </div>
            )}
          </QueryStates>

          {error ? <ErrorState error={error} className="border-t border-border py-6" /> : null}

          <div className="border-t border-border px-4 py-2 text-xs text-muted-foreground">
            Edits save themselves a moment after you stop typing. Ctrl or Cmd plus S saves now.
          </div>
        </Card>

        <div className="grid gap-4 lg:grid-cols-3">
          <Card
            title="What it adds up to"
            subtitle="From the pricing engine, against the packages this deal already carries."
          >
            <dl className="space-y-1.5 p-4 text-sm">
              <Row label="Subtotal" value={view?.subtotal} settling={settling} />
              <Row label="Quote total" value={view?.total} settling={settling} strong />
              <div className="flex items-baseline justify-between gap-3 border-t border-border pt-2">
                <dt className="flex items-baseline gap-1.5 text-muted-foreground">
                  Margin
                  {marginPct === null ? null : (
                    <span
                      className={`num text-xs font-medium ${view?.floor_breached ? "text-ember" : "text-positive"}`}
                    >
                      {marginPct.toFixed(1)}%
                    </span>
                  )}
                </dt>
                <dd className={settling ? "opacity-50" : ""}>
                  {view ? (
                    <Money
                      value={view.margin}
                      className={view.floor_breached ? "font-medium text-ember" : "font-medium"}
                    />
                  ) : (
                    "-"
                  )}
                </dd>
              </div>
              {view?.floor_breached ? (
                <div className="pt-1">
                  <Pill tone="ember">Below floor</Pill>
                </div>
              ) : null}
            </dl>
          </Card>

          {/* Founder only, and the server decides: the block is absent from a
              producer's payload rather than hidden from their screen. */}
          {view?.founder ? (
            <Card
              title="Founder only"
              subtitle="Commission and profit, on the inverted surface so they never sit in the producer-safe register."
              tone="ink"
              className="lg:col-span-2"
            >
              <div className="p-4">
                <label className="block text-xs text-primary-foreground/60">
                  Commission %
                  <input
                    type="number"
                    min={0}
                    value={commission ?? view.founder.commission_pct}
                    onChange={(event) => setCommission(Number(event.target.value) || 0)}
                    className="num mt-1 block w-20 rounded-lg border border-white/15 bg-white/10 px-2 py-1 text-right text-sm text-primary-foreground outline-none focus:border-white/40"
                  />
                </label>
                <dl className="mt-3 grid gap-x-6 gap-y-1.5 text-sm sm:grid-cols-2">
                  <InkRow label="Commission (CMF)" value={view.founder.total_commission} />
                  <InkRow label="CM (after commission)" value={view.founder.cm} />
                  <InkRow label="Lợi nhuận trước thuế" value={view.founder.profit_before_tax} />
                  <InkRow label="TNDN" value={view.founder.tndn} />
                  <InkRow label="Net profit" value={view.founder.net_profit} strong />
                  <InkRow label="VAT phải nộp" value={view.founder.vat_payable} />
                </dl>
                <div className="mt-3 border-t border-white/10 pt-2 text-xs text-primary-foreground/60">
                  Margin floor:{" "}
                  {view.founder.margin_floor_pct ? (
                    <span className="num">{view.founder.margin_floor_pct}%</span>
                  ) : (
                    "off"
                  )}
                </div>
              </div>
            </Card>
          ) : null}
        </div>
      </div>
    </AppShell>
  );
}

function Row({
  label,
  value,
  settling,
  strong,
}: {
  label: string;
  value: number | undefined;
  settling: boolean;
  strong?: boolean | undefined;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className={settling ? "opacity-50" : ""}>
        {value === undefined ? (
          <span className="text-muted-foreground">-</span>
        ) : (
          <Money value={value} className={strong ? "font-semibold" : ""} />
        )}
      </dd>
    </div>
  );
}

function InkRow({
  label,
  value,
  strong,
}: {
  label: string;
  value: number;
  strong?: boolean | undefined;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-primary-foreground/60">{label}</dt>
      <dd>
        <Money value={value} className={strong ? "font-semibold" : ""} />
      </dd>
    </div>
  );
}

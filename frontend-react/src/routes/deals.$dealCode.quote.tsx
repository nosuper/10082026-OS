// The deal breakdown and the client-facing quote built on top of it.
//
// The top half is internal: a producer prices a deal line by line against the
// record itself - quantities, units, unit price, tax type, vendor management fee
// and markup - with the three money columns (subtotal, quote price, margin)
// coming back from the server's pricing engine on every edit. Nothing here
// multiplies money.
//
// The bottom half is what a client reads: packages that gather those lines and
// may override their price, the management fee and VAT rates, how much of the
// build to show, and publishing, which freezes all of it into the next version
// at its own link. The engine prices packages too, so an override's variance
// against the member sum is a server figure like every other one.
//
// The Vue screens this replaces are frontend/src/pages/DealBreakdownPage.vue and
// frontend/src/components/QuotePanel.vue: same doctype, same field list, the
// same auraos.api.compute_breakdown recompute, the same frappe.client.save
// write, and the same publish / mark / open-log endpoints.

import { useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import {
  AlertTriangle,
  ChevronDown,
  ChevronLeft,
  ChevronUp,
  ExternalLink,
  FileDown,
  MousePointerClick,
  Plus,
  Send,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { AppShell } from "@/components/aura/AppShell";
import { useSession } from "@/components/aura/SessionProvider";
import { Card, Modal, Money, Pill, Td, Th } from "@/components/aura/primitives";
import {
  activityLabel,
  statusTone,
  versionActivity,
  isAmendable,
  type QuoteVersion,
} from "@/components/aura/QuoteVersions";
import { Empty, ErrorState, QueryState, QueryStates } from "@/components/aura/states";
import { countLabel, formatDate, formatDateTime, parseVnd, vnd } from "@/lib/format";
import { listsOf, resultOf, useDoc, useList, useMethod, useMethodMutation } from "@/lib/queries";

export const Route = createFileRoute("/deals/$dealCode/quote")({
  head: () => ({
    meta: [
      { title: "Deal breakdown and quote - AuraOS" },
      {
        name: "description",
        content:
          "Price a deal line by line, gather the lines into packages, set the management fee, VAT and detail level, then publish a version with its own client link.",
      },
      { property: "og:title", content: "Deal breakdown and quote - AuraOS" },
      {
        property: "og:description",
        content:
          "Cost lines with server-computed subtotal, quote price and margin, then packages and published quote versions.",
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

// Deal.quote_detail_level, exactly as the doctype spells them, with what each
// one puts in front of a client (playbook 3.3). The wording matters: choosing
// this is choosing how much of the build the client gets to argue with.
const DETAIL_LEVELS = [
  {
    value: "Package totals",
    label: "Package totals",
    detail: "One row per package, at the package price. Cost lines stay internal.",
  },
  {
    value: "Line by line",
    label: "Line by line",
    detail:
      "Every line with its quantities and sell price, AICP style. Cost and markup never leave.",
  },
  {
    value: "Lump sum",
    label: "Lump sum",
    detail: "One figure for the whole job, under the deal's own title.",
  },
] as const;

const DEFAULT_DETAIL_LEVEL = "Package totals";

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

/** A Deal Package as the document stores it. */
type PackageRow = {
  title: string | null;
  description: string | null;
  phase: string | null;
  price_override: number | null;
  has_price_override: number | null;
};

/**
 * A package being edited.
 *
 * `override` is the whole reason this is not just `price_override`: the column
 * is NOT NULL, so the document carries a flag beside it saying whether the
 * number means anything. Blank here is null and quotes the member sum; 0 is a
 * real price and quotes the package free of charge. Collapsing the two would
 * silently give away work.
 */
type PackageFields = {
  title: string;
  description: string;
  override: number | null;
  /** Which phase this package is quoted under. "" is quoted on its own. */
  phase: string;
};

/**
 * A phase: an ordered, named group of packages with its own blurb and its own
 * subtotal (#43). Not a Package - that is what it groups - and not a
 * production stage, which is where a job sits once we are making it.
 * CONTEXT.md keeps the three apart.
 */
type PhaseFields = { title: string; blurb: string };
type Phase = PhaseFields & { key: string };
type PhaseRow = { title: string | null; blurb: string | null };

type Package = PackageFields & { key: string };

type DealDoc = {
  name: string;
  title: string | null;
  stage: string;
  company: string | null;
  quote_mf_pct: number | null;
  vat_pct: number | null;
  contingency_pct: number | null;
  assumptions: string | null;
  exclusions: string | null;
  included_revision_rounds: number | null;
  quote_detail_level: string | null;
  commission_pct: number | null;
  cost_lines: Partial<LineFields>[] | null;
  packages: PackageRow[] | null;
  phases: PhaseRow[] | null;
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

/** What the engine makes of one package: the sum of its members, then the
 *  price the client is quoted, and the gap between them. */
type PackageView = {
  title: string | null;
  default_price: number;
  price: number;
  variance: number;
  overridden: boolean;
};

type BreakdownView = {
  lines: LineView[];
  packages: PackageView[];
  subtotal: number;
  management_fee: number;
  vat: number;
  total: number;
  margin: number;
  margin_pct: number | null;
  /** The reserve, already inside every cost figure above. Reported as one
   *  number so the screen can name it - it is not a line the client is
   *  charged separately for. */
  contingency: number;
  contingency_pct: number;
  floor_breached: boolean;
  founder?: FounderView;
};

type NamedRow = { name: string };
type ContactRow = { name: string; full_name: string | null };

/** One row of auraos.api.quote_opens: when the client looked, and how. */
type OpenEvent = {
  opened_on: string | null;
  via: string | null;
  ip_address: string | null;
};

/** The three rates and dials a client's copy is built from. */
/** The protective half of a quote (playbook 3.1.7) and the promise it makes.
 *  Edited on the deal, frozen onto each published version, printed on the
 *  client's page. Grouped with the rates because they are the same kind of
 *  thing: what a version says, fixed at the moment it is sent. */
type QuoteTerms = { assumptions: string; exclusions: string; revisionRounds: number };

type Terms = {
  mfPct: number;
  vatPct: number;
  /** Playbook 3.1.4. Inside the cost and before the markup, so it moves the
   *  cost basis and the price together and leaves margin % where it was. */
  contingencyPct: number;
  detailLevel: string;
};

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

/** A stored package row as an editable row. */
function toPackage(row: PackageRow): Package {
  return {
    key: nextKey(),
    title: text(row.title),
    description: text(row.description),
    override: row.has_price_override ? num(row.price_override) : null,
    phase: text(row.phase),
  };
}

function toPhase(row: PhaseRow): Phase {
  return { key: nextKey(), title: text(row.title), blurb: text(row.blurb) };
}

function wirePhase(phase: Phase): Record<string, string | null> {
  return { title: phase.title.trim(), blurb: blank(phase.blurb) };
}

/** What "unsaved" is measured against: the editable state, and nothing else. */
function snapshotOf(
  lines: Line[],
  packages: Package[],
  phases: Phase[],
  terms: Terms,
  quoteTerms: QuoteTerms,
  commission: number | null,
): string {
  return JSON.stringify({
    lines: lines.map(wireLine),
    packages: packages.map(wirePackage),
    // In the snapshot for the reason the assumptions below are: without it,
    // renaming a phase or reordering two of them would never mark the form
    // dirty, and the change would be lost on the next reload with nothing
    // saying so.
    phases: phases.map(wirePhase),
    terms,
    // In the snapshot because `dirty` is what enables Save. Left out, an
    // assumption typed into the box would never mark the form dirty and
    // would be lost on the next reload without anything saying so.
    quoteTerms,
    commission,
  });
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

/**
 * A package as the engine and the document both want it: the override split
 * back into the flag that says "this is set" and the number itself.
 */
function wirePackage(pkg: Package): Record<string, string | number | null> {
  return {
    title: pkg.title.trim(),
    description: blank(pkg.description),
    has_price_override: pkg.override === null ? 0 : 1,
    price_override: pkg.override ?? 0,
    // Trimmed, and blank rather than null: the server matches a package to a
    // phase by this name, so " Tiền kỳ" and "Tiền kỳ" must not be two phases.
    phase: pkg.phase.trim(),
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
// Quiet chrome for the delivery actions - the ember belongs to Publish alone.
const chip =
  "inline-flex shrink-0 items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-muted-foreground transition-colors hover:border-border-strong hover:text-foreground disabled:opacity-40";
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
  const [packages, setPackages] = useState<Package[]>([]);
  const [phases, setPhases] = useState<Phase[]>([]);
  const [terms, setTerms] = useState<Terms>({
    mfPct: 0,
    vatPct: 0,
    contingencyPct: 0,
    detailLevel: DEFAULT_DETAIL_LEVEL,
  });
  const [quoteTerms, setQuoteTerms] = useState<QuoteTerms>({
    assumptions: "",
    exclusions: "",
    revisionRounds: 0,
  });
  const [commission, setCommission] = useState<number | null>(null);
  const [visibleMeta, setVisibleMeta] = useState<MetaKey[]>(() => loadColumns(session.userId));
  const [failure, setFailure] = useState<unknown>(null);
  const [notes, setNotes] = useState("");
  // Which version's open log is expanded. The counts are on every row already;
  // this is the "when", which is what decides the timing of a follow-up.
  const [openLogFor, setOpenLogFor] = useState<string | null>(null);
  const [copied, setCopied] = useState("");

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
    const seededPackages = (data.packages ?? []).map(toPackage);
    const seededPhases = (data.phases ?? []).map(toPhase);
    setPhases(seededPhases);
    const seededTerms: Terms = {
      mfPct: data.quote_mf_pct ?? 0,
      vatPct: data.vat_pct ?? 0,
      // Zero for every deal quoted before #69: Frappe does not backfill a new
      // field's default onto existing rows, and repricing a deal that has
      // already gone out is not something an editor should do by opening it.
      contingencyPct: data.contingency_pct ?? 0,
      detailLevel: data.quote_detail_level || DEFAULT_DETAIL_LEVEL,
    };
    setServerDoc(data);
    setLines(seededLines);
    setPackages(seededPackages);
    setTerms(seededTerms);
    setQuoteTerms({
      assumptions: data.assumptions ?? "",
      exclusions: data.exclusions ?? "",
      revisionRounds: data.included_revision_rounds ?? 0,
    });
    setCommission(data.commission_pct ?? null);
    setBaseline(
      snapshotOf(
        seededLines,
        seededPackages,
        seededPhases,
        seededTerms,
        {
          assumptions: data.assumptions ?? "",
          exclusions: data.exclusions ?? "",
          revisionRounds: data.included_revision_rounds ?? 0,
        },
        data.commission_pct ?? null,
      ),
    );
  }, [deal.data]);

  const wireLines = useMemo(() => JSON.stringify(lines.map(wireLine)), [lines]);
  const wirePackages = useMemo(() => JSON.stringify(packages.map(wirePackage)), [packages]);
  const snapshot = useMemo(
    () => snapshotOf(lines, packages, phases, terms, quoteTerms, commission),
    [lines, packages, phases, terms, quoteTerms, commission],
  );

  const dirty = Boolean(baseline) && snapshot !== baseline;
  // Autosave holds off while a line has no description or a package has no
  // title: the save would only bounce off the server's own validation, and the
  // row says why in the border.
  const complete =
    lines.every((line) => line.description.trim()) &&
    packages.every((pkg) => pkg.title.trim()) &&
    phases.every((phase) => phase.title.trim());

  // -- the engine -----------------------------------------------------------
  //
  // Subtotal, quote price, package prices, the management fee, the VAT and the
  // margin are all pricing decisions, so they are asked for rather than worked
  // out here. The packages and rates being edited below ride along on every
  // call: the margin is measured against the prices a client reads, and a line
  // inside a package is priced through that package.

  const settledLines = useDebounced(wireLines, RECOMPUTE_MS);
  const settledPackages = useDebounced(wirePackages, RECOMPUTE_MS);
  const settledTerms = useDebounced(terms, RECOMPUTE_MS);
  const settledCommission = useDebounced(commission, RECOMPUTE_MS);

  const live = useMethod<BreakdownView>(
    "auraos.api.compute_breakdown",
    {
      lines: settledLines,
      packages: settledPackages,
      quote_mf_pct: settledTerms.mfPct,
      vat_pct: settledTerms.vatPct,
      contingency_pct: settledTerms.contingencyPct,
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
    settledLines !== wireLines ||
    settledPackages !== wirePackages ||
    settledTerms !== terms ||
    settledCommission !== commission ||
    live.isFetching;

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

  /**
   * Write the document. Answers whether the server now holds what is on screen,
   * which is what publishing has to know: a version freezes the *saved* deal, so
   * an unsaved override would be published at its old price.
   */
  async function save(): Promise<boolean> {
    const base = serverDoc;
    if (!base || saveDeal.isPending) return false;

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
        return false;
      }
    }

    sent.current = snapshot;
    const doc: Record<string, unknown> = {
      ...base,
      doctype: "Deal",
      cost_lines: lines.map((line) => ({ ...wireLine(line), doctype: "Deal Cost Line" })),
      packages: packages.map((pkg) => ({ ...wirePackage(pkg), doctype: "Deal Package" })),
      phases: phases.map((phase) => ({ ...wirePhase(phase), doctype: "Deal Phase" })),
      quote_mf_pct: terms.mfPct,
      vat_pct: terms.vatPct,
      contingency_pct: terms.contingencyPct,
      quote_detail_level: terms.detailLevel,
      assumptions: blank(quoteTerms.assumptions),
      exclusions: blank(quoteTerms.exclusions),
      included_revision_rounds: quoteTerms.revisionRounds,
    };
    // Producers never receive this field and the server ignores it from them.
    if (view?.founder && commission !== null) doc["commission_pct"] = commission;
    setFailure(null);
    // Awaited rather than fired and forgotten, because publish waits on it. The
    // catch is what keeps that from becoming an unhandled rejection.
    try {
      await saveDeal.mutateAsync({ doc });
      return true;
    } catch (error) {
      setFailure(error);
      return false;
    }
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

  function updatePackage(index: number, patch: Partial<PackageFields>) {
    setPackages((current) => current.map((pkg, i) => (i === index ? { ...pkg, ...patch } : pkg)));
  }

  function addPackage() {
    setPackages((current) => [
      ...current,
      { key: nextKey(), title: "", description: "", override: null, phase: "" },
    ]);
  }

  // -- phases (#43) ---------------------------------------------------------

  function updatePhase(index: number, patch: Partial<PhaseFields>) {
    setPhases((current) =>
      current.map((phase, i) => (i === index ? { ...phase, ...patch } : phase)),
    );
  }

  function addPhase() {
    setPhases((current) => [...current, { key: nextKey(), title: "", blurb: "" }]);
  }

  /**
   * Drop a phase, and let go of the packages that named it.
   *
   * The same rule `removePackage` follows for its lines: a package whose phase
   * has gone falls back out of every phase and is quoted on its own, which is
   * what the server does with a phase name it cannot match. Leaving the name
   * on the package would keep it out of every printed group but still adrift -
   * visible, but under a heading that no longer exists.
   */
  function removePhase(index: number) {
    const gone = phases[index]?.title.trim();
    setPhases((current) => current.filter((_, i) => i !== index));
    if (gone) {
      setPackages((current) =>
        current.map((pkg) => (pkg.phase.trim() === gone ? { ...pkg, phase: "" } : pkg)),
      );
    }
  }

  /**
   * Move a phase up or down. Order is the whole point of a phase - the client
   * reads pre-production before post because the founder put it there - so it
   * is editable rather than alphabetical or by creation.
   */
  function movePhase(index: number, delta: number) {
    setPhases((current) => {
      const target = index + delta;
      if (target < 0 || target >= current.length) return current;
      const next = [...current];
      const [row] = next.splice(index, 1);
      if (!row) return current;
      next.splice(target, 0, row);
      return next;
    });
  }

  /**
   * Renaming a phase carries its packages across.
   *
   * Without this a rename would orphan every package that named the old title:
   * they would still print, at the bottom, under a heading the founder thought
   * they had just edited. The same shape of decision as the vocabulary rename
   * in T3.5 - the rename migrates rather than stranding what pointed at it.
   */
  function renamePhase(index: number, title: string) {
    const before = phases[index]?.title.trim() ?? "";
    updatePhase(index, { title });
    const after = title.trim();
    if (before && before !== after) {
      setPackages((current) =>
        current.map((pkg) => (pkg.phase.trim() === before ? { ...pkg, phase: after } : pkg)),
      );
    }
  }

  /**
   * Drop a package. The cost lines that pointed at it keep their own text and
   * fall back out of any package, which is what the engine does with a member
   * whose package no longer exists - so the money on screen does not move under
   * a rename either.
   */
  function removePackage(index: number) {
    const gone = packages[index]?.title.trim();
    setPackages((current) => current.filter((_, i) => i !== index));
    if (gone) {
      setLines((current) =>
        current.map((line) => (line.package === gone ? { ...line, package: "" } : line)),
      );
    }
  }

  // -- publishing -----------------------------------------------------------
  //
  // Every version of this deal, newest first. Publishing appends the next
  // integer to that list: there is no branch, no variant and no way to edit a
  // version that a client may already have opened.

  const versions = useMethod<QuoteVersion[]>("auraos.api.deal_quotes", { deal: dealCode });

  const history = versions.data ?? [];
  const nextVersion = (history[0]?.version ?? 0) + 1;

  const quoteKeys = [
    resultOf("auraos.api.deal_quotes"),
    resultOf("auraos.api.quotation_list"),
    listsOf("Deal Quote"),
    listsOf("Deal"),
    // Marking sent can move the deal's own stage, which the header pill reads.
    ["doc", "Deal", dealCode],
  ];

  const publishQuote = useMethodMutation<QuoteVersion, { deal: string; notes: string }>(
    "auraos.api.publish_quote",
    { invalidate: quoteKeys, onSuccess: () => setNotes("") },
  );

  // #35: fixing a typo on a version nobody can be holding, rather than
  // publishing a v2 that says nothing new. The server refuses once the
  // version has hardened - Sent, Confirmed, or simply opened - so this is an
  // affordance over a rule rather than the rule itself.
  const [amending, setAmending] = useState<QuoteVersion | null>(null);
  const amendQuote = useMethodMutation<
    QuoteVersion,
    { quote: string; values: Record<string, unknown> }
  >("auraos.api.amend_quote", {
    invalidate: quoteKeys,
    onSuccess: () => setAmending(null),
  });

  const markSent = useMethodMutation<QuoteVersion, { quote: string }>(
    "auraos.api.mark_quote_sent",
    { invalidate: quoteKeys },
  );

  const markConfirmed = useMethodMutation<QuoteVersion, { quote: string }>(
    "auraos.api.mark_quote_confirmed",
    { invalidate: quoteKeys },
  );

  const opens = useMethod<OpenEvent[]>(
    "auraos.api.quote_opens",
    { quote: openLogFor },
    { enabled: Boolean(openLogFor) },
  );

  async function publish(): Promise<void> {
    // The version freezes the saved document, so what is on screen has to be
    // the saved document first. This is the Vue panel's beforePublish, awaited.
    if (dirty && !(await save())) return;
    publishQuote.mutate({ deal: dealCode, notes: notes.trim() });
  }

  function copyLink(url: string) {
    void navigator.clipboard?.writeText(url);
    setCopied(url);
  }

  // -- chrome ---------------------------------------------------------------

  // Straight off the editable packages, so a package added below is selectable
  // on a cost line above it without a round trip.
  const packageTitles = [...new Set(packages.map((pkg) => pkg.title.trim()).filter(Boolean))];
  // Straight off the editable phases, so a phase added below is selectable on
  // a package immediately - the same rule the package picker above follows.
  const phaseTitles = [...new Set(phases.map((phase) => phase.title.trim()).filter(Boolean))];

  // A line may still name a package that is no longer in the table. Keep it in
  // the dropdown rather than showing the row as unassigned, which would be a
  // silent reassignment the producer never asked for.
  const strayPackages = [
    ...new Set(
      lines
        .map((line) => line.package.trim())
        .filter((title) => title && !packageTitles.includes(title)),
    ),
  ];

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
      ? "A line needs a description, or a package needs a title - autosave is waiting"
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
                              title="Packages are created in the packages table below"
                            >
                              <option value="">No package</option>
                              {[...packageTitles, ...strayPackages].map((title) => (
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
              {terms.contingencyPct ? (
                <Row
                  label={`Contingency ${terms.contingencyPct}% (in cost)`}
                  value={view?.contingency}
                  settling={settling}
                  muted
                />
              ) : null}
              <Row label="Subtotal" value={view?.subtotal} settling={settling} />
              <Row
                label={`Management fee ${terms.mfPct}%`}
                value={view?.management_fee}
                settling={settling}
              />
              <Row label={`VAT ${terms.vatPct}%`} value={view?.vat} settling={settling} />
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

        {/* -- the client-facing half ------------------------------------- */}

        {/* Phases (#43), above the packages they group - the reading order
            on the quote, and the order the founder builds in: name the parts
            of the job, then say which part each package sits in. */}
        <Card
          title="Phases"
          subtitle="How the client reads the job split into parts. Optional - a deal with no phases quotes exactly as it always has, and a package naming none is quoted on its own, ahead of the first phase."
          action={
            <button type="button" onClick={addPhase} disabled={!serverDoc} className={ghostButton}>
              <Plus className="size-3" /> Add phase
            </button>
          }
        >
          <QueryStates queries={[deal]} loadingRows={2}>
            {() =>
              phases.length === 0 ? (
                <p className="p-4 text-xs leading-relaxed text-muted-foreground">
                  No phases. Every package is quoted on its own, in the order below - which is how
                  this quote reads today and how it read before phases existed.
                </p>
              ) : (
                <div className="divide-y divide-border">
                  {phases.map((phase, index) => {
                    // Counted off the packages being edited, not off the server:
                    // the founder needs to see a phase is empty *before* saving,
                    // because an empty phase is dropped from the client's quote.
                    const held = packages.filter(
                      (pkg) => pkg.phase.trim() === phase.title.trim() && phase.title.trim(),
                    ).length;
                    return (
                      <div key={phase.key} className="flex flex-wrap items-start gap-2 p-3">
                        <div className="flex shrink-0 flex-col gap-0.5">
                          <button
                            type="button"
                            aria-label={`Move phase ${index + 1} up`}
                            disabled={index === 0}
                            onClick={() => movePhase(index, -1)}
                            className="rounded border border-border px-1 text-xs disabled:opacity-30"
                          >
                            ↑
                          </button>
                          <button
                            type="button"
                            aria-label={`Move phase ${index + 1} down`}
                            disabled={index === phases.length - 1}
                            onClick={() => movePhase(index, 1)}
                            className="rounded border border-border px-1 text-xs disabled:opacity-30"
                          >
                            ↓
                          </button>
                        </div>
                        <input
                          value={phase.title}
                          onChange={(event) => renamePhase(index, event.target.value)}
                          placeholder="Tiền kỳ"
                          aria-label={`Phase title, phase ${index + 1}`}
                          title="Renaming a phase carries its packages across."
                          className={`w-44 ${cellInput} ${
                            phase.title.trim() ? "" : "border-ember bg-ember-soft"
                          }`}
                        />
                        <input
                          value={phase.blurb}
                          onChange={(event) => updatePhase(index, { blurb: event.target.value })}
                          placeholder="The sentence under the heading (optional)"
                          aria-label={`Phase blurb, phase ${index + 1}`}
                          className={`min-w-48 flex-1 ${cellInput}`}
                        />
                        <span
                          className="label-caps shrink-0 self-center"
                          title={
                            held === 0
                              ? "An empty phase is not printed on the client's quote."
                              : undefined
                          }
                        >
                          {held === 0
                            ? "empty · not printed"
                            : `${held} package${held === 1 ? "" : "s"}`}
                        </span>
                        <button
                          type="button"
                          aria-label={`Remove phase ${index + 1}`}
                          onClick={() => removePhase(index)}
                          className="shrink-0 self-center rounded-lg border border-border p-1.5 text-muted-foreground hover:bg-secondary hover:text-ember"
                        >
                          <X className="size-3.5" strokeWidth={1.75} />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )
            }
          </QueryStates>
        </Card>

        <Card
          title="Packages"
          subtitle="What the client is offered. A package is priced at the sum of its lines unless it carries an override, and the variance is the engine's, not this browser's."
          action={
            <button
              type="button"
              onClick={addPackage}
              disabled={!serverDoc}
              className={ghostButton}
            >
              <Plus className="size-3" /> Add package
            </button>
          }
        >
          <QueryStates queries={[deal]} loadingRows={3}>
            {() =>
              packages.length === 0 ? (
                <Empty
                  title="No packages yet."
                  detail="A quote is published from packages - add one and put cost lines in it."
                  action={
                    <button type="button" onClick={addPackage} className={ghostButton}>
                      <Plus className="size-3" /> Add package
                    </button>
                  }
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[900px]">
                    <thead className="border-b border-border">
                      <tr>
                        <Th>Package</Th>
                        <Th>Phase</Th>
                        <Th>What the client reads</Th>
                        <Th className="text-right">Member sum</Th>
                        <Th className="text-right">Override</Th>
                        <Th className="text-right">Quoted</Th>
                        <Th className="text-right">Variance</Th>
                        <Th />
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {packages.map((pkg, index) => {
                        const priced = view?.packages?.[index];
                        return (
                          <tr key={pkg.key} className="hover:bg-secondary/40">
                            <Td>
                              <input
                                value={pkg.title}
                                onChange={(event) =>
                                  updatePackage(index, { title: event.target.value })
                                }
                                placeholder="Tên gói"
                                aria-label={`Package title, package ${index + 1}`}
                                title="A package needs a title before it can save"
                                className={`w-full ${cellInput} ${
                                  pkg.title.trim() ? "" : "border-ember bg-ember-soft"
                                }`}
                              />
                            </Td>
                            <Td>
                              {/* Chosen from the declared phases, never typed:
                                  a free-text phase would make a new one out of
                                  a spelling mistake, and the client would read
                                  two headings for one part of the job. Blank
                                  is a real answer - quoted on its own, ahead
                                  of the first phase. */}
                              <select
                                value={pkg.phase}
                                onChange={(event) =>
                                  updatePackage(index, { phase: event.target.value })
                                }
                                aria-label={`Phase, package ${index + 1}`}
                                title="Which part of the job this package is quoted under. Leave blank to quote it on its own, ahead of the first phase."
                                className={`w-full ${cellInput}`}
                              >
                                <option value="">On its own</option>
                                {phaseTitles.map((title) => (
                                  <option key={title} value={title}>
                                    {title}
                                  </option>
                                ))}
                                {/* A package still naming a phase that has gone
                                    keeps its own option, so opening the deal
                                    does not silently reassign it. */}
                                {pkg.phase.trim() && !phaseTitles.includes(pkg.phase.trim()) ? (
                                  <option value={pkg.phase}>{pkg.phase} (missing)</option>
                                ) : null}
                              </select>
                            </Td>
                            <Td>
                              <textarea
                                rows={2}
                                value={pkg.description}
                                onChange={(event) =>
                                  updatePackage(index, { description: event.target.value })
                                }
                                placeholder="Client-facing wording"
                                aria-label={`Package description, package ${index + 1}`}
                                className={`w-full resize-y ${cellInput}`}
                              />
                            </Td>
                            <Td
                              className={`num text-right text-muted-foreground ${
                                settling ? "opacity-50" : ""
                              }`}
                            >
                              {priced ? <Money value={priced.default_price} /> : "-"}
                            </Td>
                            <Td>
                              <input
                                inputMode="numeric"
                                value={pkg.override === null ? "" : vnd(pkg.override)}
                                onChange={(event) => {
                                  const typed = event.target.value;
                                  // Blank is "no override" and quotes the member
                                  // sum; a typed 0 is a real price and quotes the
                                  // package free of charge.
                                  updatePackage(index, {
                                    override: typed.trim() ? parseVnd(typed) : null,
                                  });
                                }}
                                placeholder="Auto"
                                aria-label={`Price override, package ${index + 1}`}
                                title="Leave blank to quote the member sum. Type 0 to quote it free of charge."
                                className={`w-full font-medium ${cellNum}`}
                              />
                            </Td>
                            <Td className={`text-right ${settling ? "opacity-50" : ""}`}>
                              {priced ? (
                                <Money value={priced.price} className="font-semibold" />
                              ) : (
                                <span className="num text-muted-foreground">-</span>
                              )}
                            </Td>
                            <Td className={`text-right ${settling ? "opacity-50" : ""}`}>
                              {!priced ? (
                                <span className="num text-muted-foreground">-</span>
                              ) : priced.overridden ? (
                                <Money
                                  value={priced.variance}
                                  sign
                                  className={
                                    priced.variance < 0
                                      ? "text-ember"
                                      : priced.variance > 0
                                        ? "text-positive"
                                        : "text-muted-foreground"
                                  }
                                />
                              ) : (
                                // No override, so there is nothing to vary from.
                                <span className="num text-muted-foreground">-</span>
                              )}
                            </Td>
                            <Td className="text-right">
                              <button
                                type="button"
                                className={rowIcon}
                                title="Remove package"
                                aria-label={`Remove package ${index + 1}`}
                                onClick={() => removePackage(index)}
                              >
                                <X className="size-3.5" />
                              </button>
                            </Td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )
            }
          </QueryStates>
          <div className="border-t border-border px-4 py-2 text-xs text-muted-foreground">
            Blank quotes the member sum. A typed <span className="num">0</span> quotes the package
            free of charge - the two are different offers and the record keeps them apart.
          </div>
        </Card>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card
            title="Client terms"
            subtitle="The rates the engine applies above, and how much of the build a published version puts in front of the client."
          >
            <div className="grid gap-4 p-4 sm:grid-cols-2">
              <label className="block text-xs text-muted-foreground">
                Management fee %
                <input
                  type="number"
                  min={0}
                  step={0.5}
                  value={terms.mfPct}
                  disabled={!serverDoc}
                  onChange={(event) =>
                    setTerms((current) => ({
                      ...current,
                      mfPct: Number(event.target.value) || 0,
                    }))
                  }
                  className={`num mt-1 block w-24 ${cellInput} text-right`}
                />
              </label>
              <label className="block text-xs text-muted-foreground">
                Contingency %
                <input
                  type="number"
                  min={0}
                  step={0.5}
                  value={terms.contingencyPct}
                  disabled={!serverDoc}
                  onChange={(event) =>
                    setTerms((current) => ({
                      ...current,
                      contingencyPct: Number(event.target.value) || 0,
                    }))
                  }
                  className={`num mt-1 block w-24 ${cellInput} text-right`}
                />
                <span className="mt-1 block text-[11px] text-muted-foreground">
                  Dự phòng, trong cost và trước markup. Nâng cả chi phí lẫn giá bán, nên margin %
                  không đổi.
                </span>
              </label>
              <label className="block text-xs text-muted-foreground">
                VAT %
                <input
                  type="number"
                  min={0}
                  step={0.5}
                  value={terms.vatPct}
                  disabled={!serverDoc}
                  onChange={(event) =>
                    setTerms((current) => ({
                      ...current,
                      vatPct: Number(event.target.value) || 0,
                    }))
                  }
                  className={`num mt-1 block w-24 ${cellInput} text-right`}
                />
              </label>
            </div>

            <fieldset className="border-t border-border p-4">
              <legend className="label-caps px-0">Detail level</legend>
              <div className="mt-2 space-y-2">
                {DETAIL_LEVELS.map((level) => (
                  <label
                    key={level.value}
                    className={`flex cursor-pointer gap-2.5 rounded-lg border p-2.5 transition-colors ${
                      terms.detailLevel === level.value
                        ? "border-border-strong bg-secondary"
                        : "border-border hover:bg-secondary/50"
                    }`}
                  >
                    <input
                      type="radio"
                      name="quote-detail-level"
                      value={level.value}
                      checked={terms.detailLevel === level.value}
                      disabled={!serverDoc}
                      onChange={() =>
                        setTerms((current) => ({ ...current, detailLevel: level.value }))
                      }
                      className="mt-0.5"
                    />
                    <span className="min-w-0">
                      <span className="block text-sm font-medium">{level.label}</span>
                      <span className="block text-xs text-muted-foreground">{level.detail}</span>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          </Card>

          <Card
            title="Assumptions and exclusions"
            subtitle="What this price assumes, and what it does not cover. Frozen into every version you publish, and printed on the client's page."
          >
            <div className="grid gap-4 p-4">
              <label className="block text-xs text-muted-foreground">
                Assumptions
                <textarea
                  aria-label="Assumptions"
                  rows={4}
                  value={quoteTerms.assumptions}
                  disabled={!serverDoc}
                  onChange={(event) =>
                    setQuoteTerms((current) => ({ ...current, assumptions: event.target.value }))
                  }
                  placeholder={"2 ngày quay\n1 location\nUsage: digital 12 tháng"}
                  className={`mt-1 w-full resize-y ${cellInput}`}
                />
                <span className="mt-1 block text-[11px] text-muted-foreground">
                  Mỗi dòng một ý. Client đổi scope thì chỉ vào đây.
                </span>
              </label>

              <label className="block text-xs text-muted-foreground">
                Not included
                <textarea
                  aria-label="Not included"
                  rows={4}
                  value={quoteTerms.exclusions}
                  disabled={!serverDoc}
                  onChange={(event) =>
                    setQuoteTerms((current) => ({ ...current, exclusions: event.target.value }))
                  }
                  placeholder={"Ngày quay thêm\nKOL fee\nMusic license mở rộng"}
                  className={`mt-1 w-full resize-y ${cellInput}`}
                />
              </label>

              <label className="block text-xs text-muted-foreground">
                Revision rounds included
                <input
                  aria-label="Revision rounds included"
                  type="number"
                  min={0}
                  step={1}
                  value={quoteTerms.revisionRounds}
                  disabled={!serverDoc}
                  onChange={(event) =>
                    setQuoteTerms((current) => ({
                      ...current,
                      revisionRounds: Number(event.target.value) || 0,
                    }))
                  }
                  className={`num mt-1 block w-24 ${cellInput} text-right`}
                />
                <span className="mt-1 block text-[11px] text-muted-foreground">
                  In lên báo giá, và job kế thừa đúng con số này khi deal thắng - nên cái đã hứa và
                  cái hệ thống tính tiền là một.
                </span>
              </label>
            </div>
          </Card>

          <Card
            title="Publish a version"
            subtitle="Publishing freezes the packages, the rates, the detail level and the assumptions into the next version at its own link. A published version never changes - send a new one instead."
          >
            <div className="p-4">
              <label className="block text-xs text-muted-foreground">
                Note for the client
                <textarea
                  rows={3}
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  placeholder="Hiệu lực báo giá, điều khoản thanh toán..."
                  className={`mt-1 w-full resize-y ${cellInput}`}
                />
              </label>

              <button
                type="button"
                onClick={() => void publish()}
                disabled={publishQuote.isPending || saveDeal.isPending || !serverDoc || !complete}
                className="mt-3 inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-ember px-3 py-2 text-sm font-medium text-ember-foreground transition-opacity hover:opacity-90 disabled:opacity-40"
              >
                <Send className="size-3.5" strokeWidth={1.75} />
                {publishQuote.isPending || saveDeal.isPending
                  ? "Publishing..."
                  : `Publish version ${nextVersion}`}
              </button>

              <p className="mt-2 text-xs text-muted-foreground">
                {dirty
                  ? "Unsaved edits are saved first, so the version freezes what is on screen."
                  : "Versions are numbered in sequence and publishing cannot be undone."}
              </p>

              {publishQuote.isError ? (
                <ErrorState error={publishQuote.error} className="py-6" />
              ) : null}
              {markSent.isError ? <ErrorState error={markSent.error} className="py-6" /> : null}
              {markConfirmed.isError ? (
                <ErrorState error={markConfirmed.error} className="py-6" />
              ) : null}
            </div>
          </Card>
        </div>

        <Card
          title="Published versions"
          subtitle="Newest first. Opens and PDF downloads are counted apart by the server, so the page's own download button is not scored twice."
        >
          <QueryState
            query={versions}
            loadingRows={3}
            empty={{
              title: "No version published yet.",
              detail: "Publish one and the link to send the client appears here.",
            }}
          >
            {(rows) => (
              <ul className="divide-y divide-border">
                {rows.map((version) => {
                  const activity = versionActivity(version);
                  const url = version.url;
                  const pdf = version.pdf_url;
                  const expanded = openLogFor === version.name;
                  return (
                    <li key={version.name} className="px-4 py-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <Link
                          to="/quotations/$quoteRef"
                          params={{ quoteRef: version.name }}
                          className="num text-sm font-semibold hover:text-ember"
                        >
                          v{version.version}
                        </Link>
                        <Pill tone={statusTone[version.status] ?? "neutral"}>{version.status}</Pill>
                        <span className="num text-xs text-muted-foreground">
                          published {formatDate(version.published_on)}
                        </span>
                        {version.sent_on ? (
                          <span className="num text-xs text-muted-foreground">
                            sent {formatDate(version.sent_on)}
                          </span>
                        ) : null}
                        {version.confirmed_on ? (
                          <span className="num text-xs text-muted-foreground">
                            signed {formatDate(version.confirmed_on)}
                          </span>
                        ) : null}
                        <span className="ml-auto">
                          <Money value={version.total} className="font-semibold" />
                        </span>
                      </div>

                      <div className="mt-2 flex flex-wrap items-center gap-1.5">
                        {url ? (
                          <>
                            <a
                              href={url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className={chip}
                            >
                              Public link <ExternalLink className="size-3" strokeWidth={1.75} />
                            </a>
                            <button type="button" className={chip} onClick={() => copyLink(url)}>
                              {copied === url ? "Copied" : "Copy"}
                            </button>
                          </>
                        ) : null}
                        {pdf ? (
                          <a href={pdf} target="_blank" rel="noopener noreferrer" className={chip}>
                            PDF <FileDown className="size-3" strokeWidth={1.75} />
                          </a>
                        ) : null}
                        <button
                          type="button"
                          className={chip}
                          aria-expanded={expanded}
                          onClick={() => setOpenLogFor(expanded ? null : version.name)}
                        >
                          <MousePointerClick className="size-3" strokeWidth={1.75} />
                          {activityLabel(activity)}
                        </button>

                        <span className="ml-auto flex flex-wrap gap-1.5">
                          {isAmendable(version) ? (
                            <button
                              type="button"
                              className={chip}
                              onClick={() => setAmending(version)}
                            >
                              Fix wording
                            </button>
                          ) : null}
                          {version.status === "Sent" ? null : (
                            <button
                              type="button"
                              className={chip}
                              disabled={markSent.isPending}
                              onClick={() => markSent.mutate({ quote: version.name })}
                            >
                              {version.status === "Confirmed" ? "Undo confirm" : "Mark sent"}
                            </button>
                          )}
                          {version.status === "Confirmed" ? null : (
                            <button
                              type="button"
                              className={chip}
                              disabled={markConfirmed.isPending}
                              onClick={() => markConfirmed.mutate({ quote: version.name })}
                            >
                              Mark confirmed
                            </button>
                          )}
                        </span>
                      </div>

                      {expanded ? (
                        <div className="mt-2 border-t border-border pt-2">
                          <QueryState
                            query={opens}
                            loadingRows={2}
                            empty={{
                              title: "Not opened yet.",
                              detail:
                                "Nothing has reached the client's screen from this version's link.",
                              icon: <MousePointerClick className="size-6" strokeWidth={1.5} />,
                            }}
                          >
                            {(events) => (
                              <ul className="space-y-1 text-xs">
                                {events.map((event, i) => (
                                  <li
                                    key={`${event.opened_on}-${i}`}
                                    className="flex items-center gap-2"
                                  >
                                    <span className="num text-muted-foreground">
                                      {formatDateTime(event.opened_on)}
                                    </span>
                                    <Pill tone={event.via === "PDF" ? "ink" : "neutral"}>
                                      {event.via === "PDF" ? "PDF download" : "Page open"}
                                    </Pill>
                                    <span className="num text-muted-foreground/70">
                                      {event.ip_address || ""}
                                    </span>
                                  </li>
                                ))}
                              </ul>
                            )}
                          </QueryState>
                        </div>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            )}
          </QueryState>
          {versions.data?.length ? (
            <div className="border-t border-border px-4 py-2 text-xs text-muted-foreground">
              {countLabel(versions.data.length, "version")} published. The next one is{" "}
              <span className="num">v{nextVersion}</span>.
            </div>
          ) : null}
        </Card>
      </div>
      {amending ? (
        <AmendDialog
          version={amending}
          pending={amendQuote.isPending}
          error={amendQuote.error}
          onClose={() => setAmending(null)}
          onSave={(values) => amendQuote.mutate({ quote: amending.name, values })}
        />
      ) : null}
    </AppShell>
  );
}

function Row({
  label,
  value,
  settling,
  strong,
  muted,
}: {
  label: string;
  value: number | undefined;
  settling: boolean;
  strong?: boolean | undefined;
  /** For a figure that is *inside* one of the others rather than added to
   *  them. The contingency is the only one: printing it flush with Subtotal
   *  and VAT would read as a separate charge, which is exactly what the
   *  playbook says it is not. */
  muted?: boolean | undefined;
}) {
  return (
    <div className={`flex items-baseline justify-between gap-3${muted ? " text-xs" : ""}`}>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className={settling ? "opacity-50" : ""}>
        {value === undefined ? (
          <span className="text-muted-foreground">-</span>
        ) : (
          <Money
            value={value}
            className={strong ? "font-semibold" : muted ? "text-muted-foreground" : ""}
          />
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

/**
 * Correcting the wording on a version that has not gone out (#35).
 *
 * **Text only, and the omission is the design.** Package prices and line
 * figures come from the deal, so editing them here would put a number on the
 * client's page that the deal cannot reproduce - worse than the typo this
 * exists to fix. Money still moves by publishing a new version, and the
 * subtitle says so rather than leaving someone hunting for the field.
 */
function AmendDialog({
  version,
  pending,
  error,
  onClose,
  onSave,
}: {
  version: QuoteVersion;
  pending: boolean;
  error: unknown;
  onClose: () => void;
  onSave: (values: Record<string, unknown>) => void;
}) {
  const [draft, setDraft] = useState({
    title: version.title ?? "",
    client_name: version.client_name ?? "",
    client_address: version.client_address ?? "",
    client_tax_code: version.client_tax_code ?? "",
    client_contact: version.client_contact ?? "",
    notes: version.notes ?? "",
    assumptions: version.assumptions ?? "",
    exclusions: version.exclusions ?? "",
    included_revision_rounds: version.included_revision_rounds ?? 0,
  });

  const field = (key: keyof typeof draft, label: string, rows = 0) => (
    <label className="block text-xs text-muted-foreground">
      {label}
      {rows ? (
        <textarea
          aria-label={label}
          rows={rows}
          value={String(draft[key])}
          onChange={(event) => setDraft((d) => ({ ...d, [key]: event.target.value }))}
          className={`mt-1 w-full resize-y ${cellInput}`}
        />
      ) : (
        <input
          aria-label={label}
          value={String(draft[key])}
          onChange={(event) => setDraft((d) => ({ ...d, [key]: event.target.value }))}
          className={`mt-1 w-full ${cellInput}`}
        />
      )}
    </label>
  );

  return (
    <Modal
      title={`Fix the wording on v${version.version}`}
      subtitle="Only the words. Figures come from the deal - to change those, publish a new version. This stops being possible the moment the version is sent or the client opens it."
      onClose={onClose}
      footer={
        <>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-border px-3 py-2 text-xs text-muted-foreground hover:text-foreground"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={pending}
            onClick={() => onSave(draft)}
            className="rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90 disabled:opacity-50"
          >
            {pending ? "Saving..." : "Save wording"}
          </button>
        </>
      }
    >
      <div className="grid gap-3 p-4">
        {field("title", "Quote title")}
        {field("client_name", "Client name")}
        {field("client_address", "Client address", 2)}
        {field("client_tax_code", "Client tax code")}
        {field("client_contact", "Client contact")}
        {field("notes", "Note for the client", 3)}
        {field("assumptions", "Assumptions", 4)}
        {field("exclusions", "Not included", 4)}
        <label className="block text-xs text-muted-foreground">
          Revision rounds included
          <input
            aria-label="Revision rounds included"
            type="number"
            min={0}
            step={1}
            value={draft.included_revision_rounds}
            onChange={(event) =>
              setDraft((d) => ({
                ...d,
                included_revision_rounds: Number(event.target.value) || 0,
              }))
            }
            className={`num mt-1 block w-24 ${cellInput} text-right`}
          />
        </label>
        {error ? <ErrorState error={error} className="py-4" /> : null}
      </div>
    </Modal>
  );
}

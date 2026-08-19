// The deals pipeline, on real data.
//
// Seven stages, one card per deal, dragged between columns; the same rows in a
// table that creates, edits and deletes in place. Every read and write goes
// through lib/queries.ts and every figure through lib/format.ts, so this screen
// owns no transport and no formatting of its own.
//
// The Vue screen this replaces is frontend/src/pages/DealsPage.vue: same
// doctype, same field list, same endpoints, same stage vocabulary.

import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { ArrowUpRight, Clock, DollarSign, Link2, Plus, Search, Trash2, X } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";

import { AppShell } from "@/components/aura/AppShell";
import { RichText } from "@/components/aura/RichText";
import { ViewToggle } from "@/components/aura/Kanban";
import { useSession } from "@/components/aura/SessionProvider";
import { Card, Money, Pill, Td, Th } from "@/components/aura/primitives";
import { ErrorState, QueryStates } from "@/components/aura/states";
import { countLabel, daysSince, formatDate, formatDateTime, parseVnd, vnd } from "@/lib/format";
import { listsOf, resultOf, useList, useMethod, useMethodMutation } from "@/lib/queries";

export const Route = createFileRoute("/deals/")({
  head: () => ({
    meta: [
      { title: "Deals pipeline - AuraOS" },
      {
        name: "description",
        content:
          "The seven-stage deal pipeline: drag a card between stages, edit the table in place, win the deal and open the job.",
      },
      { property: "og:title", content: "Deals pipeline - AuraOS" },
      {
        property: "og:description",
        content: "Drag deals between stages, edit inline, and turn a won deal into a job.",
      },
    ],
  }),
  component: DealsPage,
});

// -- what the server sends ---------------------------------------------------

type DealRow = {
  name: string;
  title: string | null;
  stage: string;
  deal_owner: string | null;
  company: string | null;
  lost_reason: string | null;
  estimated_budget: number | null;
  source: string | null;
  project_type: string | null;
  quote_status: string | null;
  quote_sent_on: string | null;
  tier: string | null;
  positioning: string | null;
  modified: string | null;
  creation: string | null;
};

type CompanyRow = { name: string; company_name: string | null };
type OwnerRow = { name: string; full_name: string | null };
type NamedRow = { name: string };

type SilentPayload = {
  silence_days: number;
  deals: { name: string; title: string | null; quote_sent_on: string | null }[];
};

type QuoteLink = { name: string; version: number; status: string; url: string };

type TableRow = { name: string; title: string | null; stage: string };

type JobResult = { name: string; title: string; stage: string };

// -- the vocabulary the backend enforces -------------------------------------

// Deal.stage, in board order. The seven the doctype accepts, nothing else.
const STAGES = [
  "Brief Received",
  "De-brief",
  "Breakdown",
  "Quote Sent",
  "Negotiation",
  "Won",
  "Lost",
] as const;

const RESOLVED = new Set(["Won", "Lost"]);
const OPEN_STAGES = STAGES.filter((stage) => !RESOLVED.has(stage));

// Deal.lost_reason is a Select with exactly these options.
const LOST_REASONS = ["Price", "Timing", "Silence", "Competitor", "Scope"];

const TIERS = ["Tier 1", "Tier 2", "Tier 3"];
const POSITIONINGS = ["Cash", "Bridge", "Brand"];

// Past a week in one stage the age badge turns ember: the founder's weekly
// question is which deal has stopped moving.
const STALE_DAYS = 7;

// The pipeline reads quiet until a stage asks for a human.
const STAGE_TONE: Record<string, string> = {
  Breakdown: "ink",
  "Quote Sent": "outline",
  Negotiation: "ember",
  Won: "positive",
};

// -- table columns -----------------------------------------------------------
//
// `editable` mirrors auraos.api DEAL_TABLE_EDITABLE_FIELDS exactly. Tier and
// positioning are shown but not editable here: the server refuses them in the
// table endpoint (tier is derived from positioning and budget).

type ColumnKey =
  | "title"
  | "company"
  | "stage"
  | "deal_owner"
  | "estimated_budget"
  | "source"
  | "project_type"
  | "tier"
  | "positioning"
  | "quote_status"
  | "tags"
  | "modified";

type Column = {
  key: ColumnKey;
  label: string;
  editable?: boolean;
  required?: boolean;
  type?: "text" | "select" | "number";
  align?: "right";
};

const COLUMNS: Column[] = [
  { key: "title", label: "Deal", editable: true, required: true, type: "text" },
  { key: "company", label: "Client", editable: true, required: true, type: "select" },
  { key: "stage", label: "Stage", editable: true, type: "select" },
  { key: "deal_owner", label: "Owner", editable: true, type: "select" },
  {
    key: "estimated_budget",
    label: "Budget",
    editable: true,
    type: "number",
    align: "right",
  },
  { key: "source", label: "Source", editable: true, type: "select" },
  { key: "project_type", label: "Project type", editable: true, type: "select" },
  { key: "tier", label: "Tier" },
  { key: "positioning", label: "Positioning" },
  { key: "quote_status", label: "Quote" },
  { key: "tags", label: "Tags", editable: true, type: "text" },
  { key: "modified", label: "Updated" },
];

const ALL_COLUMN_KEYS = COLUMNS.map((column) => column.key);
const REQUIRED_COLUMN_KEYS = COLUMNS.filter((column) => column.required).map((c) => c.key);

// -- per-user preferences ----------------------------------------------------
//
// View and visible columns are a habit, not data: they live in the browser,
// keyed by the signed-in account so two people sharing a machine do not inherit
// each other's table. A blocked storage API must never break the screen.

type View = "table" | "kanban";
type Prefs = { view: View; columns: ColumnKey[] };

function prefsKey(user: string): string {
  return `auraos.next.deals.${user || "anon"}`;
}

function loadPrefs(user: string): Prefs {
  const fallback: Prefs = { view: "kanban", columns: ALL_COLUMN_KEYS };
  try {
    const raw = window.localStorage.getItem(prefsKey(user));
    if (!raw) return fallback;
    const saved = JSON.parse(raw) as Partial<Prefs>;
    const columns = Array.isArray(saved.columns)
      ? saved.columns.filter((key): key is ColumnKey => ALL_COLUMN_KEYS.includes(key as ColumnKey))
      : [];
    return {
      view: saved.view === "table" ? "table" : "kanban",
      columns: columns.length
        ? [...new Set([...REQUIRED_COLUMN_KEYS, ...columns])]
        : ALL_COLUMN_KEYS,
    };
  } catch {
    return fallback;
  }
}

function savePrefs(user: string, prefs: Prefs): void {
  try {
    window.localStorage.setItem(prefsKey(user), JSON.stringify(prefs));
  } catch {
    // Preferences are an enhancement, never a dependency.
  }
}

// -- small local helpers -----------------------------------------------------

function sum(values: Array<number | null | undefined>): number {
  return values.reduce<number>((total, value) => total + (value ?? 0), 0);
}

/** Wait for the typing to stop before asking the server. */
function useDebounced<T>(value: T, delay = 300): T {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setSettled(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);
  return settled;
}

/**
 * A money field that reads the way money is written: digits go in, grouped
 * đồng shows, the caller keeps the raw digits.
 */
function MoneyInput({
  digits,
  onDigits,
  onEnter,
  onEscape,
  onBlur,
  autoFocus,
  placeholder,
  className,
}: {
  digits: string;
  onDigits: (digits: string) => void;
  onEnter?: (() => void) | undefined;
  onEscape?: (() => void) | undefined;
  onBlur?: (() => void) | undefined;
  autoFocus?: boolean | undefined;
  placeholder?: string | undefined;
  className?: string | undefined;
}) {
  return (
    <input
      type="text"
      inputMode="numeric"
      autoComplete="off"
      autoFocus={autoFocus}
      placeholder={placeholder}
      value={digits === "" ? "" : vnd(parseVnd(digits))}
      onChange={(event) => onDigits(event.target.value.replace(/\D/g, ""))}
      onBlur={onBlur}
      onClick={(event) => event.stopPropagation()}
      onKeyDown={(event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          onEnter?.();
        }
        if (event.key === "Escape") onEscape?.();
      }}
      className={className}
    />
  );
}

const inputClass =
  "w-full rounded-lg border border-border bg-background px-2 py-1.5 text-sm outline-none focus:border-border-strong";

const editClass =
  "w-full rounded-lg border border-ember bg-background px-2 py-1 text-sm outline-none";

/** The dialog chrome the three deal dialogs share. Same shape as FormDialog. */
function Modal({
  title,
  subtitle,
  onClose,
  children,
  footer,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  onClose: () => void;
  children: ReactNode;
  footer: ReactNode;
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 sm:p-8">
      <button
        aria-label="Close"
        onClick={onClose}
        className="fixed inset-0 bg-primary/25 backdrop-blur-[1px]"
      />
      <div
        role="dialog"
        aria-modal="true"
        className="relative z-10 w-full max-w-xl rounded-xl border border-border bg-card shadow-lg"
      >
        <header className="flex items-start gap-3 border-b border-border px-5 py-4">
          <div className="min-w-0 flex-1">
            <h2 className="font-display text-base font-semibold tracking-tight">{title}</h2>
            {subtitle ? (
              <div className="mt-0.5 text-xs text-muted-foreground">{subtitle}</div>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary"
          >
            <X className="size-4" />
          </button>
        </header>
        {children}
        <footer className="flex items-center justify-end gap-2 border-t border-border px-5 py-4">
          {footer}
        </footer>
      </div>
    </div>
  );
}

// -- the screen --------------------------------------------------------------

function DealsPage() {
  const session = useSession();
  const navigate = useNavigate();

  const [prefs, setPrefs] = useState<Prefs>(() => loadPrefs(session.userId));
  const [search, setSearch] = useState("");
  const [owner, setOwner] = useState("");
  const needle = useDebounced(search.trim(), 300).toLowerCase();

  // -- reads ----------------------------------------------------------------

  const companies = useList<CompanyRow>({
    doctype: "Party Company",
    fields: ["name", "company_name"],
    orderBy: "company_name asc",
  });

  const companyName = useMemo(() => {
    const map = new Map<string, string>();
    for (const row of companies.data ?? []) map.set(row.name, row.company_name ?? row.name);
    return map;
  }, [companies.data]);

  // A company is a link field, so a search for "Nhất Minh" is a search for the
  // ids whose name matches. Resolved here, then asked of the server with the
  // rest of the needle rather than filtered in the browser.
  const companyMatches = useMemo(() => {
    if (!needle) return [];
    return (companies.data ?? [])
      .filter((row) => (row.company_name ?? row.name).toLowerCase().includes(needle))
      .map((row) => row.name);
  }, [companies.data, needle]);

  const filters: Record<string, unknown> = {};
  if (owner) filters["deal_owner"] = owner;

  const orFilters = needle
    ? {
        title: ["like", `%${needle}%`],
        name: ["like", `%${needle}%`],
        project_type: ["like", `%${needle}%`],
        // An empty "in" is not valid SQL; a sentinel keeps the clause honest.
        company: ["in", companyMatches.length ? companyMatches : ["-none-"]],
      }
    : undefined;

  const deals = useList<DealRow>({
    doctype: "Deal",
    fields: [
      "name",
      "title",
      "stage",
      "deal_owner",
      "company",
      "lost_reason",
      "estimated_budget",
      "source",
      "project_type",
      "quote_status",
      "quote_sent_on",
      "tier",
      "positioning",
      "modified",
      "creation",
    ],
    filters,
    ...(orFilters ? { orFilters } : {}),
    orderBy: "modified desc",
  });

  const owners = useMethod<OwnerRow[]>("auraos.api.operating_users");
  const sources = useList<NamedRow>({
    doctype: "Deal Source",
    fields: ["name"],
    orderBy: "name asc",
  });
  const projectTypes = useList<NamedRow>({
    doctype: "Project Type",
    fields: ["name"],
    orderBy: "name asc",
  });

  // Child rows are not reachable through the list API; one call maps them all.
  const tagsMap = useMethod<Record<string, string[]>>("auraos.api.deal_tags_map");
  const stageEntries = useMethod<Record<string, string>>("auraos.api.deal_stage_entries");
  const quoteLinks = useMethod<Record<string, QuoteLink>>("auraos.api.deal_quote_links");
  const jobsByDeal = useMethod<Record<string, string>>("auraos.api.jobs_by_deal");
  // Same query key as the Home dashboard, so this is a cache read there.
  const silence = useMethod<SilentPayload>("auraos.api.silent_quote_deals");

  const silentDeals = useMemo(() => {
    const map = new Map<string, string | null>();
    for (const row of silence.data?.deals ?? []) map.set(row.name, row.quote_sent_on);
    return map;
  }, [silence.data]);

  function ownerLabel(user: string | null): string {
    if (!user) return "Unassigned";
    return (owners.data ?? []).find((row) => row.name === user)?.full_name || user;
  }

  function tagsFor(deal: string): string[] {
    return tagsMap.data?.[deal] ?? [];
  }

  function jobFor(deal: string): string | undefined {
    return jobsByDeal.data?.[deal];
  }

  function stageAge(deal: DealRow): number {
    return daysSince(stageEntries.data?.[deal.name] ?? deal.creation) ?? 0;
  }

  // -- writes ---------------------------------------------------------------

  const [failure, setFailure] = useState<unknown>(null);
  // A card lands where it was dropped before the server answers; the refetch is
  // the correction if the server disagrees.
  const [moved, setMoved] = useState<Record<string, string>>({});
  const [pendingLost, setPendingLost] = useState<DealRow | null>(null);
  const [pendingJob, setPendingJob] = useState<{ name: string; title: string } | null>(null);
  const [newOpen, setNewOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState("");

  const dealWrites = [
    listsOf("Deal"),
    resultOf("auraos.api.deal_tags_map"),
    resultOf("auraos.api.deal_stage_entries"),
    resultOf("auraos.api.jobs_by_deal"),
    resultOf("auraos.api.deal_quote_links"),
  ];

  function offerJob(name: string, title: string | null) {
    if (jobFor(name)) return;
    setPendingJob({ name, title: title ?? name });
  }

  const setStage = useMethodMutation<
    unknown,
    { doctype: string; name: string; fieldname: Record<string, unknown> }
  >("frappe.client.set_value", {
    invalidate: dealWrites,
    onSuccess: (_result, args) => {
      setFailure(null);
      const stage = args.fieldname["stage"];
      // Winning a deal is where the job is created; ask right here rather than
      // leaving it to be remembered later.
      if (stage === "Won") {
        const row = (deals.data ?? []).find((deal) => deal.name === args.name);
        offerJob(args.name, row?.title ?? args.name);
      }
    },
  });

  useEffect(() => {
    if (!setStage.isError) return;
    setFailure(setStage.error);
    setMoved({});
  }, [setStage.isError, setStage.error]);

  // Drop an optimistic stage as soon as the server's own answer agrees.
  useEffect(() => {
    const rows = deals.data;
    if (!rows) return;
    setMoved((previous) => {
      let changed = false;
      const next = { ...previous };
      for (const row of rows) {
        if (next[row.name] === row.stage) {
          delete next[row.name];
          changed = true;
        }
      }
      return changed ? next : previous;
    });
  }, [deals.data]);

  function moveTo(deal: DealRow, stage: string) {
    if (deal.stage === stage) return;
    if (stage === "Lost") {
      // The server refuses Lost without a reason; collect it first.
      setPendingLost(deal);
      return;
    }
    setFailure(null);
    setMoved((previous) => ({ ...previous, [deal.name]: stage }));
    setStage.mutate({ doctype: "Deal", name: deal.name, fieldname: { stage } });
  }

  function markLost(reason: string, note: string) {
    const deal = pendingLost;
    setPendingLost(null);
    if (!deal) return;
    setFailure(null);
    setMoved((previous) => ({ ...previous, [deal.name]: "Lost" }));
    setStage.mutate({
      doctype: "Deal",
      name: deal.name,
      fieldname: { stage: "Lost", lost_reason: reason, lost_note: note },
    });
  }

  const updateRow = useMethodMutation<TableRow, { deal: string; values: Record<string, unknown> }>(
    "auraos.api.update_deal_table_row",
    {
      invalidate: dealWrites,
      onSuccess: (row) => {
        setFailure(null);
        if (row.stage === "Won") offerJob(row.name, row.title);
      },
    },
  );

  const createRow = useMethodMutation<TableRow, { values: Record<string, unknown> }>(
    "auraos.api.create_deal_table_row",
    { invalidate: dealWrites, onSuccess: () => setFailure(null) },
  );

  const insertDeal = useMethodMutation<DealRow, { doc: Record<string, unknown> }>(
    "frappe.client.insert",
    {
      invalidate: dealWrites,
      onSuccess: (doc) => {
        setFailure(null);
        setNewOpen(false);
        if (doc.stage === "Won") offerJob(doc.name, doc.title);
      },
    },
  );

  const deleteDeal = useMethodMutation<unknown, { doctype: string; name: string }>(
    "frappe.client.delete",
    {
      invalidate: dealWrites,
      onSuccess: () => {
        setFailure(null);
        setConfirmDelete("");
      },
    },
  );

  const createJob = useMethodMutation<JobResult, { deal: string }>(
    "auraos.api.create_job_from_deal",
    {
      invalidate: [...dealWrites, listsOf("Job")],
      onSuccess: (job) => {
        setPendingJob(null);
        void navigate({ to: "/jobs/$jobId", params: { jobId: job.name } });
      },
    },
  );

  useEffect(() => {
    for (const write of [updateRow, createRow, insertDeal, deleteDeal, createJob]) {
      if (write.isError) {
        setFailure(write.error);
        return;
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    updateRow.isError,
    createRow.isError,
    insertDeal.isError,
    deleteDeal.isError,
    createJob.isError,
  ]);

  // -- what the screen shows ------------------------------------------------

  const rows = useMemo(() => {
    return (deals.data ?? []).map((row) => {
      const stage = moved[row.name];
      return stage ? { ...row, stage } : row;
    });
  }, [deals.data, moved]);

  const openRows = rows.filter((row) => !RESOLVED.has(row.stage));
  const pipeline = sum(openRows.map((row) => row.estimated_budget));

  const byStage = useMemo(() => {
    const map = new Map<string, DealRow[]>();
    for (const stage of STAGES) map.set(stage, []);
    for (const row of rows) {
      const bucket = map.get(row.stage);
      if (bucket) bucket.push(row);
      else map.set(row.stage, [row]);
    }
    return map;
  }, [rows]);

  const visibleColumns = COLUMNS.filter((column) => prefs.columns.includes(column.key));

  function setView(view: View) {
    const next: Prefs = { ...prefs, view };
    setPrefs(next);
    savePrefs(session.userId, next);
  }

  function toggleColumn(key: ColumnKey) {
    if (REQUIRED_COLUMN_KEYS.includes(key)) return;
    const columns = prefs.columns.includes(key)
      ? prefs.columns.filter((item) => item !== key)
      : ALL_COLUMN_KEYS.filter((item) => item === key || prefs.columns.includes(item));
    if (!columns.length) return;
    const next: Prefs = { ...prefs, columns };
    setPrefs(next);
    savePrefs(session.userId, next);
  }

  const meta = [
    deals.isSuccess ? countLabel(rows.length, "deal") + " in view" : null,
    silence.isSuccess && silence.data?.deals.length
      ? `${countLabel(silence.data.deals.length, "quote")} gone quiet`
      : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <AppShell
      title="Deals"
      meta={meta}
      actions={
        <button
          onClick={() => setNewOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          <Plus className="size-3.5" /> New deal
        </button>
      }
    >
      <div className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-5">
          {OPEN_STAGES.map((stage) => {
            const items = byStage.get(stage) ?? [];
            return (
              <div key={stage} className="rounded-xl border border-border bg-card p-4">
                <div className="label-caps">{stage}</div>
                <div className="mt-1.5 flex items-baseline gap-2">
                  <span className="num text-lg font-semibold">{items.length}</span>
                  <span className="text-xs text-muted-foreground">
                    {items.length === 1 ? "deal" : "deals"}
                  </span>
                </div>
                <Money
                  value={sum(items.map((item) => item.estimated_budget))}
                  className="mt-1 block text-xs text-muted-foreground"
                />
              </div>
            );
          })}
        </div>

        <Card
          title="All deals"
          subtitle={
            <span>
              Pipeline value <Money value={pipeline} className="text-foreground" /> ·{" "}
              {countLabel(openRows.length, "open deal")}
            </span>
          }
          action={
            <div className="flex flex-wrap items-center gap-2">
              <span className="relative">
                <Search className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" />
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search deals"
                  aria-label="Search deals"
                  className="w-44 rounded-lg border border-border bg-background py-1.5 pr-2.5 pl-8 text-xs outline-none focus:border-border-strong"
                />
              </span>

              <select
                value={owner}
                onChange={(event) => setOwner(event.target.value)}
                aria-label="Filter by owner"
                className="rounded-lg border border-border bg-background px-2 py-1.5 text-xs text-muted-foreground outline-none focus:border-border-strong"
              >
                <option value="">All owners</option>
                {(owners.data ?? []).map((row) => (
                  <option key={row.name} value={row.name}>
                    {row.full_name || row.name}
                  </option>
                ))}
              </select>

              {prefs.view === "table" ? (
                <details className="relative">
                  <summary className="cursor-pointer list-none rounded-lg border border-border px-2.5 py-1.5 text-xs text-muted-foreground select-none hover:text-foreground">
                    Columns
                  </summary>
                  <div className="absolute right-0 z-20 mt-1 w-52 rounded-xl border border-border bg-card p-2 shadow-lg">
                    {COLUMNS.map((column) => (
                      <label
                        key={column.key}
                        className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1 text-sm hover:bg-secondary"
                      >
                        <input
                          type="checkbox"
                          checked={prefs.columns.includes(column.key)}
                          disabled={column.required}
                          onChange={() => toggleColumn(column.key)}
                        />
                        {column.label}
                      </label>
                    ))}
                  </div>
                </details>
              ) : null}

              <ViewToggle view={prefs.view} onChange={setView} />
            </div>
          }
        >
          <QueryStates
            queries={[deals, companies]}
            isEmpty={() => rows.length === 0 && prefs.view === "kanban"}
            empty={{
              title: needle || owner ? "No deals match that." : "No deals yet.",
              detail:
                needle || owner
                  ? "Clear the search or the owner filter to see the whole pipeline."
                  : "Start one with New deal, or type a row into the table.",
            }}
            loadingRows={6}
          >
            {() =>
              prefs.view === "kanban" ? (
                <div className="p-3">
                  <Board
                    byStage={byStage}
                    onMove={moveTo}
                    companyName={companyName}
                    ownerLabel={ownerLabel}
                    stageAge={stageAge}
                    silentDeals={silentDeals}
                    silenceDays={silence.data?.silence_days ?? 0}
                    quoteLinks={quoteLinks.data ?? {}}
                    jobFor={jobFor}
                    onWin={(deal) => offerJob(deal.name, deal.title)}
                  />
                </div>
              ) : (
                <DealTable
                  rows={rows}
                  columns={visibleColumns}
                  companies={companies.data ?? []}
                  companyName={companyName}
                  owners={owners.data ?? []}
                  ownerLabel={ownerLabel}
                  sources={sources.data ?? []}
                  projectTypes={projectTypes.data ?? []}
                  tagsFor={tagsFor}
                  silentDeals={silentDeals}
                  defaultOwner={
                    (owners.data ?? []).some((row) => row.name === session.userId)
                      ? session.userId
                      : ""
                  }
                  onSave={(deal, key, value) => {
                    setFailure(null);
                    updateRow.mutate({ deal, values: { [key]: value } });
                  }}
                  onLose={(deal) => setPendingLost(deal)}
                  onCreate={(values) => {
                    setFailure(null);
                    createRow.mutate({ values });
                  }}
                  onDelete={(name) => {
                    setFailure(null);
                    deleteDeal.mutate({ doctype: "Deal", name });
                  }}
                  confirmDelete={confirmDelete}
                  setConfirmDelete={setConfirmDelete}
                  saving={updateRow.isPending}
                  creating={createRow.isPending}
                  searching={Boolean(needle || owner)}
                />
              )
            }
          </QueryStates>

          {failure ? <ErrorState error={failure} className="border-t border-border py-6" /> : null}
        </Card>
      </div>

      {newOpen ? (
        <NewDealDialog
          companies={companies.data ?? []}
          owners={owners.data ?? []}
          sources={sources.data ?? []}
          projectTypes={projectTypes.data ?? []}
          defaultOwner={
            (owners.data ?? []).some((row) => row.name === session.userId) ? session.userId : ""
          }
          saving={insertDeal.isPending}
          onClose={() => setNewOpen(false)}
          onCreate={(doc) => {
            setFailure(null);
            insertDeal.mutate({ doc });
          }}
        />
      ) : null}

      {pendingLost ? (
        <LostReasonDialog
          title={pendingLost.title || pendingLost.name}
          onClose={() => setPendingLost(null)}
          onConfirm={markLost}
        />
      ) : null}

      {pendingJob ? (
        <Modal
          title={`"${pendingJob.title}" is won`}
          onClose={() => setPendingJob(null)}
          footer={
            <>
              <button
                type="button"
                onClick={() => setPendingJob(null)}
                className="rounded-lg border border-border px-3 py-2 text-xs text-muted-foreground hover:text-foreground"
              >
                Not yet
              </button>
              <button
                type="button"
                disabled={createJob.isPending}
                onClick={() => createJob.mutate({ deal: pendingJob.name })}
                className="rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90 disabled:opacity-40"
              >
                {createJob.isPending ? "Creating..." : "Create job"}
              </button>
            </>
          }
        >
          <p className="px-5 py-5 text-sm text-muted-foreground">
            Create the job now? It carries the breakdown, packages and links across, so nothing is
            re-entered.
          </p>
        </Modal>
      ) : null}
    </AppShell>
  );
}

// -- the board ---------------------------------------------------------------

function Board({
  byStage,
  onMove,
  companyName,
  ownerLabel,
  stageAge,
  silentDeals,
  silenceDays,
  quoteLinks,
  jobFor,
  onWin,
}: {
  byStage: Map<string, DealRow[]>;
  onMove: (deal: DealRow, stage: string) => void;
  companyName: Map<string, string>;
  ownerLabel: (user: string | null) => string;
  stageAge: (deal: DealRow) => number;
  silentDeals: Map<string, string | null>;
  silenceDays: number;
  quoteLinks: Record<string, QuoteLink>;
  jobFor: (deal: string) => string | undefined;
  onWin: (deal: DealRow) => void;
}) {
  const [dragged, setDragged] = useState<DealRow | null>(null);
  const [over, setOver] = useState<string | null>(null);

  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex min-w-max items-stretch gap-3">
        {STAGES.map((stage) => {
          const items = byStage.get(stage) ?? [];
          const active = over === stage;
          return (
            <div
              key={stage}
              className="flex w-[292px] shrink-0 flex-col"
              onDragOver={(event) => {
                event.preventDefault();
                setOver(stage);
              }}
              onDragLeave={(event) => {
                if (event.currentTarget.contains(event.relatedTarget as Node | null)) return;
                setOver((current) => (current === stage ? null : current));
              }}
              onDrop={(event) => {
                event.preventDefault();
                const deal = dragged;
                setDragged(null);
                setOver(null);
                if (deal) onMove(deal, stage);
              }}
            >
              <div
                className={`flex items-baseline justify-between rounded-t-xl border border-b-0 px-3 py-2.5 transition-colors ${
                  active ? "border-ember bg-ember-soft" : "border-border bg-card"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="label-caps">{stage}</span>
                  <span className="num rounded-md bg-secondary px-1.5 py-0.5 text-[11px] text-muted-foreground">
                    {items.length}
                  </span>
                </div>
                <Money
                  value={items.reduce((total, item) => total + (item.estimated_budget ?? 0), 0)}
                  className="text-[11px] text-muted-foreground"
                />
              </div>
              <div
                className={`dot-grid min-h-24 flex-1 space-y-2 overflow-y-auto rounded-b-xl border p-2 transition-colors ${
                  active ? "border-ember" : "border-border"
                }`}
              >
                {items.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-border px-3 py-6 text-center text-[11px] text-muted-foreground">
                    Nothing here
                  </div>
                ) : (
                  items.map((deal) => (
                    <DealCard
                      key={deal.name}
                      deal={deal}
                      dragging={dragged?.name === deal.name}
                      onDragStart={() => setDragged(deal)}
                      onDragEnd={() => {
                        setDragged(null);
                        setOver(null);
                      }}
                      company={deal.company ? (companyName.get(deal.company) ?? deal.company) : ""}
                      owner={ownerLabel(deal.deal_owner)}
                      age={stageAge(deal)}
                      silentSince={silentDeals.get(deal.name)}
                      silenceDays={silenceDays}
                      quote={quoteLinks[deal.name]}
                      job={jobFor(deal.name)}
                      onWin={() => onWin(deal)}
                    />
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DealCard({
  deal,
  dragging,
  onDragStart,
  onDragEnd,
  company,
  owner,
  age,
  silentSince,
  silenceDays,
  quote,
  job,
  onWin,
}: {
  deal: DealRow;
  dragging: boolean;
  onDragStart: () => void;
  onDragEnd: () => void;
  company: string;
  owner: string;
  age: number;
  silentSince: string | null | undefined;
  silenceDays: number;
  quote: QuoteLink | undefined;
  job: string | undefined;
  onWin: () => void;
}) {
  const open = !RESOLVED.has(deal.stage);

  return (
    <div
      draggable
      onDragStart={(event) => {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", deal.name);
        onDragStart();
      }}
      onDragEnd={onDragEnd}
      className={`group cursor-grab rounded-lg border border-border bg-card p-3 transition-shadow hover:border-border-strong hover:shadow-sm ${
        dragging ? "opacity-50" : ""
      }`}
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <Link
            to="/deals/$dealCode"
            params={{ dealCode: deal.name }}
            className="block truncate text-sm leading-snug font-medium hover:text-ember"
            title={deal.title ?? deal.name}
          >
            {deal.title || deal.name}
          </Link>
          <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
            {company ? <span className="truncate">{company}</span> : null}
            <span className="num ml-auto shrink-0 text-[10px]">{deal.name}</span>
          </div>
        </div>
        <Link
          to="/deals/$dealCode/quote"
          params={{ dealCode: deal.name }}
          title="Breakdown and quote"
          className="shrink-0 rounded-md p-1 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 hover:bg-secondary hover:text-foreground"
        >
          <DollarSign className="size-3.5" />
        </Link>
      </div>

      {deal.estimated_budget || deal.project_type || deal.tier ? (
        <div className="mt-2.5 flex flex-wrap items-baseline gap-2">
          {deal.estimated_budget ? (
            <Money value={deal.estimated_budget} className="text-sm font-semibold" />
          ) : null}
          {deal.project_type ? <Pill tone="outline">{deal.project_type}</Pill> : null}
          {deal.tier ? (
            <Pill tone={deal.tier === "Tier 3" ? "ink" : "neutral"} className="num">
              {deal.tier.replace("Tier ", "T")}
            </Pill>
          ) : null}
        </div>
      ) : null}

      <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
        <Pill tone="outline">{owner}</Pill>
        {deal.stage === "Lost" && deal.lost_reason ? (
          <Pill tone="ember">{deal.lost_reason}</Pill>
        ) : null}
        {silentSince !== undefined ? (
          <Pill tone="ember" className="gap-1">
            <Clock className="size-3" /> Silent {silenceDays}d
          </Pill>
        ) : null}
        {quote ? (
          <a
            href={quote.url}
            target="_blank"
            rel="noopener noreferrer"
            title="Open the client's quote page"
            className="inline-flex items-center gap-1 rounded-md border border-border-strong px-2 py-0.5 text-[11px] font-medium hover:text-ember"
          >
            <Link2 className="size-3" />
            <span className="num">v{quote.version}</span>
          </a>
        ) : null}
        {deal.stage === "Won" ? (
          job ? (
            <Link
              to="/jobs/$jobId"
              params={{ jobId: job }}
              className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-0.5 text-[11px] font-medium text-positive hover:opacity-80"
            >
              Job <ArrowUpRight className="size-3" />
            </Link>
          ) : (
            <button
              type="button"
              onClick={onWin}
              className="rounded-md border border-border px-2 py-0.5 text-[11px] font-medium text-positive hover:opacity-80"
            >
              + Job
            </button>
          )
        ) : null}
        {open && age >= 1 ? (
          <span
            className={`num ml-auto shrink-0 text-[11px] ${age > STALE_DAYS ? "text-ember" : "text-muted-foreground"}`}
            title={`In ${deal.stage} for ${countLabel(age, "day")}`}
          >
            {age}d
          </span>
        ) : null}
      </div>
    </div>
  );
}

// -- the table ---------------------------------------------------------------

type NewRowDraft = Record<string, string>;

function emptyDraft(owner: string): NewRowDraft {
  return {
    title: "",
    company: "",
    stage: "Brief Received",
    deal_owner: owner,
    estimated_budget: "",
    source: "",
    project_type: "",
    tags: "",
  };
}

function DealTable({
  rows,
  columns,
  companies,
  companyName,
  owners,
  ownerLabel,
  sources,
  projectTypes,
  tagsFor,
  silentDeals,
  defaultOwner,
  onSave,
  onLose,
  onCreate,
  onDelete,
  confirmDelete,
  setConfirmDelete,
  saving,
  creating,
  searching,
}: {
  rows: DealRow[];
  columns: Column[];
  companies: CompanyRow[];
  companyName: Map<string, string>;
  owners: OwnerRow[];
  ownerLabel: (user: string | null) => string;
  sources: NamedRow[];
  projectTypes: NamedRow[];
  tagsFor: (deal: string) => string[];
  silentDeals: Map<string, string | null>;
  defaultOwner: string;
  onSave: (deal: string, key: string, value: unknown) => void;
  onLose: (deal: DealRow) => void;
  onCreate: (values: Record<string, unknown>) => void;
  onDelete: (name: string) => void;
  confirmDelete: string;
  setConfirmDelete: (name: string) => void;
  saving: boolean;
  creating: boolean;
  searching: boolean;
}) {
  const [sortKey, setSortKey] = useState<ColumnKey>("modified");
  const [ascending, setAscending] = useState(false);
  const [editing, setEditing] = useState<{ deal: string; key: ColumnKey; original: string } | null>(
    null,
  );
  const [draft, setDraft] = useState("");
  const [newRow, setNewRow] = useState<NewRowDraft>(() => emptyDraft(defaultOwner));

  useEffect(() => {
    setNewRow((current) =>
      current["deal_owner"] ? current : { ...current, deal_owner: defaultOwner },
    );
  }, [defaultOwner]);

  function optionsFor(key: ColumnKey): { value: string; label: string }[] {
    const blank = { value: "", label: "" };
    if (key === "company") {
      return [
        blank,
        ...companies.map((row) => ({ value: row.name, label: row.company_name ?? row.name })),
      ];
    }
    if (key === "stage") return STAGES.map((stage) => ({ value: stage, label: stage }));
    if (key === "deal_owner") {
      return [
        blank,
        ...owners.map((row) => ({ value: row.name, label: row.full_name || row.name })),
      ];
    }
    if (key === "source")
      return [blank, ...sources.map((row) => ({ value: row.name, label: row.name }))];
    if (key === "project_type") {
      return [blank, ...projectTypes.map((row) => ({ value: row.name, label: row.name }))];
    }
    return [];
  }

  function cellText(deal: DealRow, key: ColumnKey): string {
    if (key === "tags") return tagsFor(deal.name).join(", ");
    if (key === "estimated_budget") {
      return deal.estimated_budget ? String(Math.round(deal.estimated_budget)) : "";
    }
    const value = deal[key];
    return value === null || value === undefined ? "" : String(value);
  }

  // Sort by what the reader sees, not by the ids underneath.
  function sortValue(deal: DealRow, key: ColumnKey): string | number {
    if (key === "company")
      return deal.company ? (companyName.get(deal.company) ?? deal.company) : "";
    if (key === "deal_owner") return ownerLabel(deal.deal_owner);
    if (key === "tags") return tagsFor(deal.name).join(", ");
    if (key === "estimated_budget") return deal.estimated_budget ?? 0;
    return cellText(deal, key);
  }

  const sorted = useMemo(() => {
    const direction = ascending ? 1 : -1;
    return [...rows].sort((a, b) => {
      const left = sortValue(a, sortKey);
      const right = sortValue(b, sortKey);
      if (typeof left === "number" || typeof right === "number") {
        return ((Number(left) || 0) - (Number(right) || 0)) * direction;
      }
      return String(left).localeCompare(String(right), "vi") * direction;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, sortKey, ascending, companyName, owners, tagsFor]);

  function startEditing(deal: DealRow, column: Column) {
    if (!column.editable) return;
    const original = cellText(deal, column.key);
    setEditing({ deal: deal.name, key: column.key, original });
    setDraft(original);
  }

  function commit(deal: DealRow, key: ColumnKey, value: string) {
    setEditing(null);
    if (!editing || value === editing.original) return;
    if (key === "stage" && value === "Lost") {
      // The reason comes first; the dialog does the save.
      onLose(deal);
      return;
    }
    if (key === "tags") {
      const tags = [
        ...new Set(
          value
            .split(",")
            .map((tag) => tag.trim())
            .filter(Boolean),
        ),
      ];
      onSave(deal.name, "deal_tags", tags);
      return;
    }
    if (key === "estimated_budget") {
      onSave(deal.name, key, value === "" ? null : parseVnd(value));
      return;
    }
    onSave(deal.name, key, value);
  }

  function createFromRow() {
    const title = (newRow["title"] ?? "").trim();
    if (!title) return;
    const values: Record<string, unknown> = {
      title,
      company: newRow["company"] ?? "",
      stage: newRow["stage"] ?? "Brief Received",
    };
    for (const key of ["deal_owner", "source", "project_type"]) {
      const value = newRow[key];
      if (value) values[key] = value;
    }
    if (newRow["estimated_budget"])
      values["estimated_budget"] = parseVnd(newRow["estimated_budget"]);
    const tags = [
      ...new Set(
        (newRow["tags"] ?? "")
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean),
      ),
    ];
    if (tags.length) values["deal_tags"] = tags;
    onCreate(values);
    setNewRow(emptyDraft(defaultOwner));
  }

  function header(column: Column) {
    return (
      <Th
        key={column.key}
        className={`cursor-pointer select-none hover:text-foreground ${column.align === "right" ? "text-right" : ""}`}
      >
        <button
          type="button"
          onClick={() => {
            if (sortKey === column.key) setAscending((value) => !value);
            else {
              setSortKey(column.key);
              setAscending(true);
            }
          }}
        >
          {column.label}
          {sortKey === column.key ? (
            <span className="text-ember"> {ascending ? "↑" : "↓"}</span>
          ) : null}
        </button>
      </Th>
    );
  }

  function renderValue(deal: DealRow, column: Column): ReactNode {
    switch (column.key) {
      case "title":
        return (
          <span className="flex items-center gap-1.5">
            <Link
              to="/deals/$dealCode"
              params={{ dealCode: deal.name }}
              className="font-medium hover:text-ember"
            >
              {deal.title || deal.name}
            </Link>
            <span className="num shrink-0 text-[10px] text-muted-foreground">{deal.name}</span>
          </span>
        );
      case "stage":
        return <Pill tone={STAGE_TONE[deal.stage] ?? "neutral"}>{deal.stage}</Pill>;
      case "company":
        return deal.company ? (companyName.get(deal.company) ?? deal.company) : "-";
      case "deal_owner":
        return <span className="text-muted-foreground">{ownerLabel(deal.deal_owner)}</span>;
      case "estimated_budget":
        return deal.estimated_budget ? <Money value={deal.estimated_budget} /> : "-";
      case "tags": {
        const tags = tagsFor(deal.name);
        return tags.length ? (
          <span className="flex flex-wrap gap-1">
            {tags.map((tag) => (
              <Pill key={tag} tone="outline">
                {tag}
              </Pill>
            ))}
          </span>
        ) : (
          "-"
        );
      }
      case "quote_status":
        return (
          <span className="flex items-center gap-1.5">
            <span className="text-muted-foreground">
              {deal.quote_status && deal.quote_status !== "Not Sent" ? deal.quote_status : "-"}
            </span>
            {silentDeals.has(deal.name) ? (
              <Pill tone="ember" className="gap-1">
                <Clock className="size-3" /> Silent
              </Pill>
            ) : null}
          </span>
        );
      case "modified":
        return (
          <span
            className="num whitespace-nowrap text-muted-foreground"
            title={formatDateTime(deal.modified)}
          >
            {formatDate(deal.modified)}
          </span>
        );
      case "tier":
      case "positioning":
      case "source":
      case "project_type": {
        const value = deal[column.key];
        return <span className="text-muted-foreground">{value || "-"}</span>;
      }
      default:
        return "-";
    }
  }

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px]">
          <thead className="border-b border-border">
            <tr>
              {columns.map(header)}
              <Th className="text-right">Row</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {/* The blank row: a deal starts by being typed, not by opening a form. */}
            <tr className="bg-secondary/40 align-top">
              {columns.map((column) => (
                <Td key={column.key} className="px-2 py-1.5">
                  {!column.editable ? (
                    <span className="text-muted-foreground">-</span>
                  ) : column.type === "select" ? (
                    <select
                      value={newRow[column.key] ?? ""}
                      onChange={(event) =>
                        setNewRow((current) => ({ ...current, [column.key]: event.target.value }))
                      }
                      aria-label={`New deal ${column.label}`}
                      className={inputClass}
                    >
                      {optionsFor(column.key).map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  ) : column.type === "number" ? (
                    <MoneyInput
                      digits={newRow[column.key] ?? ""}
                      onDigits={(digits) =>
                        setNewRow((current) => ({ ...current, [column.key]: digits }))
                      }
                      onEnter={createFromRow}
                      placeholder={column.label}
                      className={`num ${inputClass} text-right`}
                    />
                  ) : (
                    <input
                      type="text"
                      value={newRow[column.key] ?? ""}
                      placeholder={column.key === "tags" ? "tag, tag" : column.label}
                      aria-label={`New deal ${column.label}`}
                      onChange={(event) =>
                        setNewRow((current) => ({ ...current, [column.key]: event.target.value }))
                      }
                      onKeyDown={(event) => {
                        if (event.key === "Enter") createFromRow();
                      }}
                      className={inputClass}
                    />
                  )}
                </Td>
              ))}
              <Td className="px-2 py-1.5 text-right">
                <button
                  type="button"
                  onClick={createFromRow}
                  disabled={creating || !(newRow["title"] ?? "").trim()}
                  className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-40"
                >
                  {creating ? "Adding..." : "Add"}
                </button>
              </Td>
            </tr>

            {sorted.map((deal) => (
              <tr key={deal.name} className="group hover:bg-secondary/50">
                {columns.map((column) => {
                  const isEditing = editing?.deal === deal.name && editing.key === column.key;
                  return (
                    <Td
                      key={column.key}
                      className={[
                        column.align === "right" ? "text-right" : "",
                        column.editable && !isEditing ? "cursor-text" : "",
                      ]
                        .filter(Boolean)
                        .join(" ")}
                    >
                      {isEditing ? (
                        column.type === "select" ? (
                          <select
                            autoFocus
                            value={draft}
                            onChange={(event) => {
                              setDraft(event.target.value);
                              commit(deal, column.key, event.target.value);
                            }}
                            onKeyDown={(event) => {
                              if (event.key === "Escape") setEditing(null);
                            }}
                            className={editClass}
                          >
                            {optionsFor(column.key).map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        ) : column.type === "number" ? (
                          <MoneyInput
                            autoFocus
                            digits={draft}
                            onDigits={setDraft}
                            onEnter={() => commit(deal, column.key, draft)}
                            onEscape={() => setEditing(null)}
                            onBlur={() => commit(deal, column.key, draft)}
                            className={`num ${editClass} text-right`}
                          />
                        ) : (
                          <input
                            autoFocus
                            type="text"
                            value={draft}
                            onChange={(event) => setDraft(event.target.value)}
                            onBlur={() => commit(deal, column.key, draft)}
                            onKeyDown={(event) => {
                              if (event.key === "Enter") event.currentTarget.blur();
                              if (event.key === "Escape") setEditing(null);
                            }}
                            className={editClass}
                          />
                        )
                      ) : (
                        <span
                          className="block"
                          onClick={() => startEditing(deal, column)}
                          title={column.editable ? "Click to edit" : undefined}
                        >
                          {renderValue(deal, column)}
                        </span>
                      )}
                    </Td>
                  );
                })}
                <Td className="text-right whitespace-nowrap">
                  {confirmDelete === deal.name ? (
                    <span className="inline-flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => onDelete(deal.name)}
                        className="rounded-md bg-ember px-2 py-1 text-[11px] font-medium text-ember-foreground hover:opacity-90"
                      >
                        Delete
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmDelete("")}
                        className="rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground hover:text-foreground"
                      >
                        Keep
                      </button>
                    </span>
                  ) : (
                    <button
                      type="button"
                      title={`Delete ${deal.name}`}
                      aria-label={`Delete ${deal.name}`}
                      onClick={() => setConfirmDelete(deal.name)}
                      className="rounded-md p-1 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 hover:bg-secondary hover:text-ember"
                    >
                      <Trash2 className="size-3.5" />
                    </button>
                  )}
                </Td>
              </tr>
            ))}

            {sorted.length === 0 ? (
              <tr>
                <Td colSpan={columns.length + 1} className="py-8 text-center text-muted-foreground">
                  {searching
                    ? "No deals match that."
                    : "No deals yet - type one into the row above."}
                </Td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
      <div className="border-t border-border px-4 py-2 text-xs text-muted-foreground">
        Click a cell to edit it in place - Enter saves, Esc cancels.
        {saving ? <span className="ml-2 text-ember">Saving...</span> : null}
      </div>
    </>
  );
}

// -- dialogs -----------------------------------------------------------------

function NewDealDialog({
  companies,
  owners,
  sources,
  projectTypes,
  defaultOwner,
  saving,
  onClose,
  onCreate,
}: {
  companies: CompanyRow[];
  owners: OwnerRow[];
  sources: NamedRow[];
  projectTypes: NamedRow[];
  defaultOwner: string;
  saving: boolean;
  onClose: () => void;
  onCreate: (doc: Record<string, unknown>) => void;
}) {
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [dealOwner, setDealOwner] = useState(defaultOwner);
  const [stage, setStage] = useState<string>("Brief Received");
  const [budget, setBudget] = useState("");
  const [source, setSource] = useState("");
  const [projectType, setProjectType] = useState("");
  const [positioning, setPositioning] = useState("");
  const [brief, setBrief] = useState("");

  const ready = Boolean(title.trim() && company && dealOwner);

  function submit() {
    if (!ready || saving) return;
    onCreate({
      doctype: "Deal",
      title: title.trim(),
      company,
      deal_owner: dealOwner,
      stage,
      estimated_budget: budget ? parseVnd(budget) : null,
      source: source || null,
      project_type: projectType || null,
      positioning: positioning || null,
      brief: brief || null,
    });
  }

  return (
    <Modal
      title="New deal"
      subtitle="The deal record. Pricing happens in the breakdown."
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
            onClick={submit}
            disabled={!ready || saving}
            className="rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90 disabled:opacity-40"
          >
            {saving ? "Creating..." : "Create deal"}
          </button>
        </>
      }
    >
      <div className="grid gap-4 px-5 py-5 sm:grid-cols-2">
        <label className="block sm:col-span-2">
          <span className="label-caps">
            Deal name<span className="text-ember"> *</span>
          </span>
          <input
            autoFocus
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="TVC Tết 2027"
            className={`mt-1.5 ${inputClass}`}
          />
        </label>

        <label className="block">
          <span className="label-caps">
            Client company<span className="text-ember"> *</span>
          </span>
          <select
            value={company}
            onChange={(event) => setCompany(event.target.value)}
            className={`mt-1.5 ${inputClass}`}
          >
            <option value="">Which company...</option>
            {companies.map((row) => (
              <option key={row.name} value={row.name}>
                {row.company_name ?? row.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="label-caps">
            Owner<span className="text-ember"> *</span>
          </span>
          <select
            value={dealOwner}
            onChange={(event) => setDealOwner(event.target.value)}
            className={`mt-1.5 ${inputClass}`}
          >
            <option value="">Who owns it...</option>
            {owners.map((row) => (
              <option key={row.name} value={row.name}>
                {row.full_name || row.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="label-caps">Stage</span>
          <select
            value={stage}
            onChange={(event) => setStage(event.target.value)}
            className={`mt-1.5 ${inputClass}`}
          >
            {STAGES.filter((item) => item !== "Lost").map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="label-caps">Client budget (VND)</span>
          <MoneyInput
            digits={budget}
            onDigits={setBudget}
            placeholder="0"
            className={`num mt-1.5 ${inputClass} text-right`}
          />
        </label>

        <label className="block">
          <span className="label-caps">Source</span>
          <select
            value={source}
            onChange={(event) => setSource(event.target.value)}
            className={`mt-1.5 ${inputClass}`}
          >
            <option value="">Unknown</option>
            {sources.map((row) => (
              <option key={row.name} value={row.name}>
                {row.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="label-caps">Project type</span>
          <select
            value={projectType}
            onChange={(event) => setProjectType(event.target.value)}
            className={`mt-1.5 ${inputClass}`}
          >
            <option value="">Not set</option>
            {projectTypes.map((row) => (
              <option key={row.name} value={row.name}>
                {row.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="label-caps">Positioning</span>
          <select
            value={positioning}
            onChange={(event) => setPositioning(event.target.value)}
            className={`mt-1.5 ${inputClass}`}
          >
            <option value="">Not set</option>
            {POSITIONINGS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
          <span className="mt-1 block text-[11px] text-muted-foreground">
            Tier follows positioning and budget: {TIERS.join(", ")}.
          </span>
        </label>

        <label className="block sm:col-span-2">
          <span className="label-caps">Brief</span>
          {/* The same editor the deal screen uses, because this writes the
              same field. `brief` is a Text Editor field now, so a plain
              textarea here would put unescaped text into a column the rest of
              the app renders as HTML - and the first deal briefed with
              "budget < 200tr" would come back with half its sentence missing.
              One editor also means one answer to what a line break is. */}
          <div className="mt-1.5">
            <RichText
              defaultValue=""
              onChange={setBrief}
              placeholder="What the client asked for"
              ariaLabel="Brief"
              className="min-h-[5rem]"
            />
          </div>
        </label>
      </div>
    </Modal>
  );
}

function LostReasonDialog({
  title,
  onClose,
  onConfirm,
}: {
  title: string;
  onClose: () => void;
  onConfirm: (reason: string, note: string) => void;
}) {
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");

  return (
    <Modal
      title={`Mark "${title}" as Lost`}
      subtitle="A reason is required. The note is for anything the list cannot say."
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
            disabled={!reason}
            onClick={() => onConfirm(reason, note)}
            className="rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90 disabled:opacity-40"
          >
            Mark Lost
          </button>
        </>
      }
    >
      <div className="space-y-4 px-5 py-5">
        <label className="block">
          <span className="label-caps">
            Why was it lost?<span className="text-ember"> *</span>
          </span>
          <select
            autoFocus
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            className={`mt-1.5 ${inputClass}`}
          >
            <option value="">Pick a reason...</option>
            {LOST_REASONS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="label-caps">Note (optional)</span>
          <textarea
            rows={3}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            className={`mt-1.5 ${inputClass}`}
          />
        </label>
      </div>
    </Modal>
  );
}

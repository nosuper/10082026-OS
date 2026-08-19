// One deal, on real data.
//
// The record itself: who it is for, who owns it, what it is worth, what it is
// tagged and linked with, what has been said about it and how it moved through
// the stages. Pricing is the next screen along, at /deals/<code>/quote.
//
// The Vue surface this replaces is frontend/src/components/DealFormDialog.vue.
// Same doctype, same field list, same endpoints - deal_comments,
// add_deal_comment, deal_attachments, classification_hints, preview_tier - and
// the same frappe.client.save write, with the edits overlaid on the server's
// own copy so the breakdown, the packages and the stage history survive the
// round trip. The backend is unchanged.
//
// The one deliberate change is where it lives. The dialog was reached from the
// board and vanished on save; the design puts the deal on its own route, so a
// deal is a place you can link to, keep open and come back to.
//
// The stage is shown here and moved on the board: Lost needs a reason before
// the server will take it, and that conversation belongs where the card is
// dragged. Comments and attachments write themselves the moment you add them,
// because they are their own records; everything else waits for Save.

import { useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import {
  ChevronLeft,
  ExternalLink,
  FileSpreadsheet,
  Paperclip,
  Plus,
  RotateCcw,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { AppShell } from "@/components/aura/AppShell";
import { RichText } from "@/components/aura/RichText";
import { Card, Money, Pill } from "@/components/aura/primitives";
import { STAGE_TONE, StageSelect, useDealStageChange } from "@/components/aura/DealStage";
import { Empty, ErrorState, Loading } from "@/components/aura/states";
import { FrappeError, uploadFile } from "@/lib/frappe";
import { countLabel, formatDateTime, parseVnd, vnd } from "@/lib/format";
import { listsOf, resultOf, useDoc, useList, useMethod, useMethodMutation } from "@/lib/queries";

export const Route = createFileRoute("/deals/$dealCode/")({
  head: () => ({
    meta: [
      { title: "Deal - AuraOS" },
      {
        name: "description",
        content:
          "One deal: client, contact, owner, budget, positioning and tier, with its tags, links, files, comments and stage history.",
      },
      { property: "og:title", content: "Deal - AuraOS" },
      {
        property: "og:description",
        content: "The deal record, with its tags, links, files, comments and stage history.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: DealPage,
});

// -- the vocabulary the backend enforces -------------------------------------

// Deal.positioning is a Select with exactly these three, and the tier follows
// from it. The percentages beside them are the founder's live mix targets, not
// a hardcoded 70/20/10.
const POSITIONINGS = ["Cash", "Bridge", "Brand"] as const;

const POSITIONING_HINTS: Record<string, string> = {
  Cash: "nuôi bộ máy",
  Bridge: "gần định vị",
  Brand: "đúng định vị",
};

// What each tier means in the playbook (§2.2). Prose, so it stays in the sans
// face; the pill beside it carries the tier itself.
const TIER_HINTS: Record<string, string> = {
  "Tier 1": "cơm áo",
  "Tier 2": "trung bình",
  "Tier 3": "đúng định vị",
};

// The pause after the last keystroke before the tier chip is asked for again.
// The budget field fires per character.
const PREVIEW_MS = 300;

// -- what the server sends ---------------------------------------------------

type TagRow = { deal_tag: string | null };
type LinkRow = { label: string | null; url: string | null };

type StageLogRow = {
  name: string;
  from_stage: string | null;
  to_stage: string | null;
  changed_on: string | null;
  changed_by: string | null;
};

type DealDoc = {
  name: string;
  title: string | null;
  stage: string;
  deal_owner: string | null;
  company: string | null;
  contact: string | null;
  brief: string | null;
  estimated_budget: number | null;
  source: string | null;
  project_type: string | null;
  tier: string | null;
  tier_is_manual: number | null;
  positioning: string | null;
  quote_status: string | null;
  modified: string | null;
  deal_tags: TagRow[] | null;
  deal_links: LinkRow[] | null;
  stage_history: StageLogRow[] | null;
};

type CompanyRow = { name: string; company_name: string | null };
type ContactRow = { name: string; full_name: string | null; company: string | null };
type OwnerRow = { name: string; full_name: string | null };
type NamedRow = { name: string };

/** auraos.api.classification_hints: the founder's mix targets, in percent. */
type Mix = { cash: number; bridge: number; brand: number };

/** One row of auraos.api.deal_comments. */
type CommentRow = {
  name: string;
  content: string | null;
  comment_by: string | null;
  comment_email: string | null;
  creation: string | null;
};

/** One row of auraos.api.deal_attachments. */
type FileRow = {
  name: string;
  file_name: string | null;
  file_url: string | null;
  file_size: number | null;
  creation: string | null;
};

// -- what is being edited ----------------------------------------------------

type Draft = {
  title: string;
  deal_owner: string;
  company: string;
  contact: string;
  brief: string;
  /** Digits only, so the field can be empty and mean "not known". */
  budget: string;
  source: string;
  project_type: string;
  positioning: string;
  tags: string[];
  links: { label: string; url: string }[];
};

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function toDraft(doc: DealDoc): Draft {
  return {
    title: text(doc.title),
    deal_owner: text(doc.deal_owner),
    company: text(doc.company),
    contact: text(doc.contact),
    brief: text(doc.brief),
    budget: doc.estimated_budget ? String(Math.round(doc.estimated_budget)) : "",
    source: text(doc.source),
    project_type: text(doc.project_type),
    positioning: text(doc.positioning),
    tags: (doc.deal_tags ?? []).map((row) => text(row.deal_tag)).filter(Boolean),
    links: (doc.deal_links ?? [])
      .map((row) => ({ label: text(row.label), url: text(row.url) }))
      .filter((row) => row.url),
  };
}

/** An untouched optional field goes back as it came: empty, not "". */
function blank(value: string): string | null {
  return value.trim() ? value.trim() : null;
}

/** The fields this screen owns, as the doctype spells them. */
function wire(draft: Draft): Record<string, unknown> {
  return {
    title: draft.title.trim(),
    deal_owner: blank(draft.deal_owner),
    company: blank(draft.company),
    contact: blank(draft.contact),
    brief: blank(draft.brief),
    estimated_budget: draft.budget ? parseVnd(draft.budget) : null,
    source: blank(draft.source),
    project_type: blank(draft.project_type),
    positioning: blank(draft.positioning),
    deal_tags: draft.tags.map((tag) => ({ deal_tag: tag })),
    deal_links: draft.links.map((row) => ({ label: row.label, url: row.url })),
  };
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

function isMissing(error: unknown): boolean {
  return error instanceof FrappeError && error.kind === "notfound";
}

/**
 * A comment as text. The server stores sanitized HTML; parsing it out of the
 * document rather than assigning innerHTML keeps it out of the live tree.
 */
function stripHtml(html: string | null): string {
  if (!html) return "";
  return new DOMParser().parseFromString(html, "text/html").body.textContent ?? "";
}

/** How big a file is. Not money and not a date, so format.ts does not own it. */
function fileSize(bytes: number | null): string {
  if (!bytes) return "";
  // A real file is never 0 KB, so a small one rounds up rather than down.
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const inputClass =
  "w-full rounded-lg border border-border bg-background px-2.5 py-1.5 text-sm outline-none focus:border-border-strong";

const ghostButton =
  "inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium transition-colors hover:border-border-strong";

/**
 * One labelled control.
 *
 * The label sits *beside* the control from `sm` up rather than above it. This
 * panel is a list of facts about one deal, and a stacked label costs a whole
 * line per fact to say something a column heading says once - which on a wide
 * screen is most of why the section read as loose. Below `sm` it stacks,
 * because a 8.5rem label column on a phone leaves no room for the control.
 *
 * The hint stays under the control rather than under the label: it explains
 * the value, and a hint sitting under a label reads as part of the label.
 */
const FIELD_ROW = "block sm:grid sm:grid-cols-[8.5rem_minmax(0,1fr)] sm:items-start sm:gap-x-3";

function Field({
  label,
  hint,
  required,
  span,
  children,
}: {
  label: string;
  hint?: ReactNode;
  required?: boolean | undefined;
  span?: boolean | undefined;
  children: ReactNode;
}) {
  return (
    <label className={`${FIELD_ROW} ${span ? "sm:col-span-2" : ""}`}>
      <span className="label-caps mt-0 sm:mt-2">
        {label}
        {required ? <span className="text-ember"> *</span> : null}
      </span>
      <div className="mt-1 sm:mt-0">
        {children}
        {hint ? <div className="mt-1 text-[11px] text-muted-foreground">{hint}</div> : null}
      </div>
    </label>
  );
}

/** The same block for something the server decides, so it has no control. */
function Readout({
  label,
  hint,
  span,
  children,
}: {
  label: string;
  hint?: ReactNode;
  span?: boolean | undefined;
  children: ReactNode;
}) {
  return (
    <div className={`${FIELD_ROW} ${span ? "sm:col-span-2" : ""}`}>
      <div className="label-caps mt-0 sm:mt-2">{label}</div>
      <div className="mt-1 sm:mt-0">
        {children}
        {hint ? <div className="mt-1 text-[11px] text-muted-foreground">{hint}</div> : null}
      </div>
    </div>
  );
}

// -- the screen --------------------------------------------------------------

function DealPage() {
  const { dealCode } = Route.useParams();
  const client = useQueryClient();

  // -- reads ----------------------------------------------------------------

  const deal = useDoc<DealDoc>("Deal", dealCode);

  const companies = useList<CompanyRow>({
    doctype: "Party Company",
    fields: ["name", "company_name"],
    orderBy: "company_name asc",
  });

  const contacts = useList<ContactRow>({
    doctype: "Party Contact",
    fields: ["name", "full_name", "company"],
    orderBy: "full_name asc",
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

  const tagOptions = useList<NamedRow>({
    doctype: "Deal Tag",
    fields: ["name"],
    orderBy: "name asc",
  });

  const mix = useMethod<Mix>("auraos.api.classification_hints");

  const comments = useMethod<CommentRow[]>(
    "auraos.api.deal_comments",
    { deal: dealCode },
    { enabled: deal.isSuccess },
  );

  const attachments = useMethod<FileRow[]>(
    "auraos.api.deal_attachments",
    { deal: dealCode },
    { enabled: deal.isSuccess },
  );

  // -- what is being edited -------------------------------------------------

  const [serverDoc, setServerDoc] = useState<DealDoc | null>(null);
  const [typed, setDraft] = useState<Draft | null>(null);
  const [baseline, setBaseline] = useState("");
  const [failure, setFailure] = useState<unknown>(null);

  // The route component survives a change of :dealCode - clicking through from
  // one deal to another does not remount it - so whatever is in state may still
  // belong to the deal just left. Nothing is used until it says it is this
  // one's, which is the whole bug this screen was filed for.
  const onThisDeal = serverDoc?.name === dealCode;
  const draft = onThisDeal ? typed : null;
  const doc = onThisDeal ? serverDoc : deal.data?.name === dealCode ? deal.data : null;

  // The half-typed additions: a tag, a link, a comment, a file in flight. None
  // of them is part of the deal until it is added.
  const [tagInput, setTagInput] = useState("");
  const [linkLabel, setLinkLabel] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const [linkError, setLinkError] = useState("");
  const [commentDraft, setCommentDraft] = useState("");
  const [uploading, setUploading] = useState(false);
  const picker = useRef<HTMLInputElement>(null);

  // Bumped on every seed so the brief editor remounts with the server's
  // copy. It is a token rather than the deal code because reload() re-seeds
  // the same deal, and that has to reload the editor too.
  const [seedToken, setSeedToken] = useState(0);

  function seed(data: DealDoc) {
    seeded.current = data.name;
    const fresh = toDraft(data);
    setServerDoc(data);
    setDraft(fresh);
    setBaseline(JSON.stringify(wire(fresh)));
    setSeedToken((token) => token + 1);
  }

  // Seed once per deal. A later refetch of the same record must not overwrite
  // what has been typed since.
  const seeded = useRef("");
  useEffect(() => {
    const data = deal.data;
    if (!data || seeded.current === data.name) return;
    seed(data);
  }, [deal.data]);

  /**
   * Start again from the server's copy, losing what is on screen.
   *
   * Frappe refuses a save whose `modified` is stale - somebody else has edited
   * the deal since this page loaded it - and says so. There is no sane way to
   * merge two people's edits, so the offer is the honest one: take theirs and
   * retype yours.
   */
  async function reload() {
    setFailure(null);
    // Clear the refused save too, or its message would outlive the record it
    // was complaining about. saveDeal is declared below and this only ever runs
    // from a click, long after the render body has.
    saveDeal.reset();
    const fresh = await deal.refetch();
    if (fresh.data) seed(fresh.data);
  }

  const snapshot = useMemo(() => (draft ? JSON.stringify(wire(draft)) : ""), [draft]);
  const dirty = onThisDeal && Boolean(baseline) && snapshot !== baseline;

  function edit(patch: Partial<Draft>) {
    setDraft((current) => (current ? { ...current, ...patch } : current));
  }

  // -- the tier chip --------------------------------------------------------
  //
  // Tier is derived, not chosen: positioning and budget in, tier out. Previewed
  // on the server so a producer session sees the outcome without ever learning
  // the thresholds.

  const manualTier = Boolean(doc?.tier_is_manual);

  // Three primitives rather than one object: a fresh object every render would
  // restart the timer on every render and never settle.
  const settledBudget = useDebounced(draft?.budget ?? "", PREVIEW_MS);
  const settledType = useDebounced(draft?.project_type ?? "", PREVIEW_MS);
  const settledPositioning = useDebounced(draft?.positioning ?? "", PREVIEW_MS);

  const previewed = useMethod<string>(
    "auraos.api.preview_tier",
    {
      estimated_budget: settledBudget ? parseVnd(settledBudget) : 0,
      project_type: settledType,
      positioning: settledPositioning,
    },
    { enabled: Boolean(draft) && !manualTier },
  );

  const tier = manualTier ? (doc?.tier ?? "") : (previewed.data ?? doc?.tier ?? "");

  // -- writes ---------------------------------------------------------------

  const dealWrites = [
    listsOf("Deal"),
    resultOf("auraos.api.deal_tags_map"),
    resultOf("auraos.api.deal_stage_entries"),
  ];

  // Whether this deal already has a job, so reaching Won does not offer a
  // second one. Same source the board reads, because the prompt has to appear
  // in the same cases from either screen.
  const jobs = useMethod<Record<string, string>>("auraos.api.jobs_by_deal");

  // The one way a stage moves (#117). The write is a set_value on Deal.stage,
  // which loads and saves the document - so before_save runs and
  // append_stage_change writes the history row. Setting the field directly
  // would move the stage and leave the deal's history with a hole in it.
  const stageChange = useDealStageChange({
    invalidate: [...dealWrites, resultOf("auraos.api.jobs_by_deal")],
    hasJob: (deal) => Boolean(jobs.data?.[deal]),
    onWrite: () => setFailure(null),
  });

  useEffect(() => {
    if (stageChange.error) setFailure(stageChange.error);
  }, [stageChange.error]);

  const sent = useRef("");

  const saveDeal = useMethodMutation<DealDoc, { doc: Record<string, unknown> }>(
    "frappe.client.save",
    {
      invalidate: dealWrites,
      onSuccess: (saved) => {
        setFailure(null);
        // The server's copy replaces the old one - it carries the derived tier
        // and the new stage history row - but what is on screen is left alone:
        // anything typed while the save was in flight is still an edit.
        setServerDoc(saved);
        setBaseline(sent.current);
        // The save returned the whole document, so hand it to the cache rather
        // than invalidating and refetching. ["doc", doctype, name] is the key
        // useDoc builds; lib/queries has listsOf and resultOf but no docOf.
        client.setQueryData(["doc", "Deal", dealCode], saved);
      },
    },
  );

  // Typing a tag that does not exist yet creates it, as the Vue form does: the
  // child row's Link field would otherwise fail on save.
  const createTag = useMethodMutation<NamedRow, { doc: Record<string, unknown> }>(
    "frappe.client.insert",
    { invalidate: [listsOf("Deal Tag")] },
  );

  const postComment = useMethodMutation<CommentRow, { deal: string; content: string }>(
    "auraos.api.add_deal_comment",
    {
      invalidate: [resultOf("auraos.api.deal_comments")],
      onSuccess: () => setCommentDraft(""),
    },
  );

  function save() {
    const base = doc;
    if (!base || !draft || !onThisDeal || saveDeal.isPending) return;
    sent.current = snapshot;
    setFailure(null);
    saveDeal.mutate({ doc: { ...base, doctype: "Deal", ...wire(draft) } });
  }

  // The shortcut fires from a window listener, which outlives the render that
  // created it.
  const saveNow = useRef(save);
  useEffect(() => {
    saveNow.current = save;
  });

  useEffect(() => {
    function onKeydown(event: KeyboardEvent) {
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "s") return;
      event.preventDefault();
      saveNow.current();
    }
    window.addEventListener("keydown", onKeydown);
    return () => window.removeEventListener("keydown", onKeydown);
  }, []);

  // -- tags, links, files, comments -----------------------------------------

  async function addTag() {
    const value = tagInput.trim();
    if (!value || !draft) return;
    setTagInput("");
    if (draft.tags.includes(value)) return;
    const known = (tagOptions.data ?? []).some((row) => row.name === value);
    if (!known) {
      try {
        await createTag.mutateAsync({ doc: { doctype: "Deal Tag", tag_name: value } });
      } catch (error) {
        setFailure(error);
        return;
      }
    }
    setFailure(null);
    edit({ tags: [...draft.tags, value] });
  }

  function addLink() {
    const label = linkLabel.trim();
    const url = linkUrl.trim();
    if (!draft) return;
    // The row renders as a clickable link before the server's own URL
    // validation runs on save - keep javascript: and data: out of href.
    if (!label || !url) {
      setLinkError("A link needs both a label and a URL");
      return;
    }
    if (!/^https?:\/\//i.test(url)) {
      setLinkError("URL must start with http:// or https://");
      return;
    }
    setLinkError("");
    setLinkLabel("");
    setLinkUrl("");
    edit({ links: [...draft.links, { label, url }] });
  }

  function attach(file: File | undefined) {
    if (!file) return;
    setFailure(null);
    setUploading(true);
    uploadFile(file, { doctype: "Deal", docname: dealCode, isPrivate: true })
      .then(() => client.invalidateQueries({ queryKey: resultOf("auraos.api.deal_attachments") }))
      .catch((error: unknown) => setFailure(error))
      .finally(() => setUploading(false));
  }

  function comment() {
    const content = commentDraft.trim();
    if (!content || postComment.isPending) return;
    setFailure(null);
    postComment.mutate({ deal: dealCode, content });
  }

  // -- chrome ---------------------------------------------------------------

  const companyLabel = doc?.company
    ? ((companies.data ?? []).find((row) => row.name === doc.company)?.company_name ?? doc.company)
    : "";

  // Only people of the selected company, as the Vue form decided; nothing
  // chosen yet means everybody.
  const contactOptions = (contacts.data ?? []).filter(
    (row) => !draft?.company || row.company === draft.company,
  );
  // A contact saved before the company changed must still be reachable, or
  // opening the deal would silently drop it.
  const savedContact = (contacts.data ?? []).find((row) => row.name === draft?.contact);
  if (savedContact && !contactOptions.some((row) => row.name === savedContact.name)) {
    contactOptions.unshift(savedContact);
  }

  const ownerOptions = (owners.data ?? []).slice();
  if (draft?.deal_owner && !ownerOptions.some((row) => row.name === draft.deal_owner)) {
    ownerOptions.unshift({ name: draft.deal_owner, full_name: draft.deal_owner });
  }

  const percent: Record<string, number | undefined> = {
    Cash: mix.data?.cash,
    Bridge: mix.data?.bridge,
    Brand: mix.data?.brand,
  };

  const status = saveDeal.isPending
    ? "Saving..."
    : dirty
      ? "Unsaved changes - Ctrl or Cmd plus S saves"
      : onThisDeal && baseline
        ? "All changes saved"
        : "";

  const error = failure ?? (saveDeal.isError ? saveDeal.error : null);

  return (
    <AppShell
      title={doc?.title || dealCode}
      meta={
        <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <Link to="/deals" className="inline-flex items-center hover:text-ember">
            <ChevronLeft className="size-3.5" /> Deals
          </Link>
          <span className="num">{dealCode}</span>
          {companyLabel ? <span>· {companyLabel}</span> : null}
          {doc ? (
            <StageSelect
              value={doc.stage}
              disabled={stageChange.pending}
              onChange={(stage) => stageChange.request(doc, stage)}
            />
          ) : null}
          {tier ? <Pill tone={tier === "Tier 3" ? "ink" : "neutral"}>{tier}</Pill> : null}
        </span>
      }
      actions={
        doc ? (
          <div className="flex items-center gap-3">
            {status ? (
              <span className="hidden text-xs text-muted-foreground sm:inline">{status}</span>
            ) : null}
            <Link
              to="/deals/$dealCode/quote"
              params={{ dealCode }}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-secondary"
            >
              <FileSpreadsheet className="size-3.5" strokeWidth={1.75} /> Breakdown and quote
            </Link>
            <button
              type="button"
              onClick={save}
              disabled={saveDeal.isPending || !dirty}
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-40"
            >
              {saveDeal.isPending ? "Saving..." : "Save"}
            </button>
          </div>
        ) : null
      }
    >
      {deal.isPending ? (
        <Loading rows={6} />
      ) : deal.isError ? (
        isMissing(deal.error) ? (
          <Empty
            title="No such deal."
            detail={`Nothing on this site is filed under ${dealCode}. It may have been deleted, or the code may be a typo.`}
            action={
              <Link to="/deals" className={ghostButton}>
                <ChevronLeft className="size-3.5" /> Back to the pipeline
              </Link>
            }
          />
        ) : (
          <ErrorState error={deal.error} onRetry={() => void deal.refetch()} />
        )
      ) : !draft ? (
        <Loading rows={6} />
      ) : (
        <div className="grid gap-4 xl:grid-cols-3">
          <div className="space-y-4 xl:col-span-2">
            <Card
              title="The deal"
              subtitle="The record itself. Pricing lives in the breakdown and the quote."
            >
              {/* Rows are one line tall now that the label is beside the
                  control, so the vertical gap is the thing that decides how
                  dense this reads. The horizontal gap stays wide: two
                  label-and-control pairs side by side need a gutter between
                  them or they read as one four-column table. */}
              <div className="grid gap-x-8 gap-y-2 p-4 sm:grid-cols-2">
                <Field label="Title" required span>
                  <input
                    value={draft.title}
                    onChange={(event) => edit({ title: event.target.value })}
                    placeholder="TVC Tết 2027"
                    className={inputClass}
                  />
                </Field>

                <Field label="Client company" required>
                  <select
                    value={draft.company}
                    onChange={(event) => edit({ company: event.target.value })}
                    className={inputClass}
                  >
                    <option value="">Which company...</option>
                    {(companies.data ?? []).map((row) => (
                      <option key={row.name} value={row.name}>
                        {row.company_name ?? row.name}
                      </option>
                    ))}
                  </select>
                </Field>

                <Field
                  label="Contact"
                  hint={draft.company ? "People at the selected company." : undefined}
                >
                  <select
                    value={draft.contact}
                    onChange={(event) => edit({ contact: event.target.value })}
                    className={inputClass}
                  >
                    <option value="">No contact</option>
                    {contactOptions.map((row) => (
                      <option key={row.name} value={row.name}>
                        {row.full_name || row.name}
                      </option>
                    ))}
                  </select>
                </Field>

                <Field label="Owner" required>
                  <select
                    value={draft.deal_owner}
                    onChange={(event) => edit({ deal_owner: event.target.value })}
                    className={inputClass}
                  >
                    <option value="">Who owns it...</option>
                    {ownerOptions.map((row) => (
                      <option key={row.name} value={row.name}>
                        {row.full_name || row.name}
                      </option>
                    ))}
                  </select>
                </Field>

                <Readout
                  label="Stage"
                  hint="Change it in the header. Lost asks why; Won offers the job."
                >
                  <div className="flex items-center gap-2 sm:py-1.5">
                    <Pill tone={STAGE_TONE[doc?.stage ?? ""] ?? "neutral"}>{doc?.stage}</Pill>
                    <Link to="/deals" className="text-xs text-muted-foreground hover:text-ember">
                      Open the pipeline
                    </Link>
                  </div>
                </Readout>

                {/* Keyed on the seed, not on the draft. RichText writes its
                    body once and never again while somebody types - see its
                    docblock - so a new deal, or a reload that throws away what
                    is on screen, has to remount it. Anything else either loses
                    the reload or moves the caret on every keystroke. */}
                <Field label="Brief" span>
                  <RichText
                    key={seedToken}
                    defaultValue={draft.brief}
                    onChange={(html) => edit({ brief: html })}
                    placeholder="What the client asked for"
                    ariaLabel="Brief"
                  />
                </Field>

                <Field label="Est. client budget">
                  <input
                    inputMode="numeric"
                    value={draft.budget ? vnd(parseVnd(draft.budget)) : ""}
                    onChange={(event) => edit({ budget: event.target.value.replace(/\D/g, "") })}
                    placeholder="0"
                    aria-label="Estimated client budget in đồng"
                    className={`num ${inputClass} text-right`}
                  />
                </Field>

                <Field label="Source">
                  <select
                    value={draft.source}
                    onChange={(event) => edit({ source: event.target.value })}
                    className={inputClass}
                  >
                    <option value="">Unknown</option>
                    {(sources.data ?? []).map((row) => (
                      <option key={row.name} value={row.name}>
                        {row.name}
                      </option>
                    ))}
                  </select>
                </Field>

                <Field label="Project type">
                  <select
                    value={draft.project_type}
                    onChange={(event) => edit({ project_type: event.target.value })}
                    className={inputClass}
                  >
                    <option value="">Not set</option>
                    {(projectTypes.data ?? []).map((row) => (
                      <option key={row.name} value={row.name}>
                        {row.name}
                      </option>
                    ))}
                  </select>
                </Field>

                <Field
                  label="Positioning"
                  hint={
                    // New tab on purpose: the half-edited deal stays behind.
                    // The SOP is a Library document since #66, not a page.
                    <a
                      href="/aura-next/documents/library"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 underline decoration-border underline-offset-2 hover:text-ember"
                    >
                      SOP: cách đánh giá và phân loại deal
                      <ExternalLink className="size-3" />
                    </a>
                  }
                >
                  <select
                    value={draft.positioning}
                    onChange={(event) => edit({ positioning: event.target.value })}
                    className={inputClass}
                  >
                    <option value="">Not set</option>
                    {POSITIONINGS.map((item) => (
                      <option key={item} value={item}>
                        {item} - {POSITIONING_HINTS[item]}
                        {percent[item] === undefined ? "" : ` (~${percent[item]}%)`}
                      </option>
                    ))}
                  </select>
                </Field>

                <Readout
                  label="Tier (auto)"
                  hint={
                    manualTier
                      ? "Pinned by hand - clear the tier in the deals table to hand it back to the rules."
                      : "Follows positioning and budget, decided on the server."
                  }
                >
                  <div className="flex flex-wrap items-center gap-2 sm:py-1.5">
                    {tier ? (
                      <>
                        <Pill tone={tier === "Tier 3" ? "ink" : "neutral"}>{tier}</Pill>
                        <span className="text-xs text-muted-foreground">{TIER_HINTS[tier]}</span>
                      </>
                    ) : (
                      <span className="text-xs text-muted-foreground">
                        No tier yet - it follows positioning and budget.
                      </span>
                    )}
                  </div>
                </Readout>

                {/* The tags a deal carries, and the way to add one, on a
                    single row. The add control used to be a full-width boxed
                    input with its own button on a line of its own, which is
                    why it read as a dialog dropped into the panel rather than
                    as part of it: it was the widest control on the screen for
                    the shortest value on it. Now it is a chip the same size as
                    the tags it makes, so typing a tag looks like what it
                    produces. Enter still commits; the + is for whoever does
                    not know that. */}
                <Field label="Tags" span>
                  <div className="flex flex-wrap items-center gap-1.5">
                    {draft.tags.map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center gap-1 rounded-md border border-border bg-secondary px-2 py-0.5 text-[11px] font-medium text-muted-foreground"
                      >
                        {tag}
                        <button
                          type="button"
                          title={`Remove ${tag}`}
                          aria-label={`Remove tag ${tag}`}
                          onClick={() => edit({ tags: draft.tags.filter((item) => item !== tag) })}
                          className="text-muted-foreground hover:text-ember"
                        >
                          <X className="size-3" />
                        </button>
                      </span>
                    ))}

                    <span className="inline-flex items-center gap-1 rounded-md border border-dashed border-border px-2 py-0.5 focus-within:border-border-strong">
                      <input
                        list="aura-deal-tags"
                        value={tagInput}
                        onChange={(event) => setTagInput(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key !== "Enter") return;
                          event.preventDefault();
                          void addTag();
                        }}
                        placeholder="Add tag"
                        aria-label="Add tag"
                        // Grows with what is typed rather than sitting at a
                        // fixed width. A tag like "cần báo giá gấp" is longer
                        // than the box a fixed width can justify for an empty
                        // one, and an input you cannot read what you typed into
                        // is worse than the wide box this replaced.
                        size={Math.max(8, tagInput.length + 1)}
                        className="max-w-[14rem] bg-transparent text-[11px] font-medium outline-none placeholder:text-muted-foreground"
                      />
                      <datalist id="aura-deal-tags">
                        {(tagOptions.data ?? [])
                          .filter((row) => !draft.tags.includes(row.name))
                          .map((row) => (
                            <option key={row.name} value={row.name} />
                          ))}
                      </datalist>
                      <button
                        type="button"
                        onClick={() => void addTag()}
                        disabled={createTag.isPending || !tagInput.trim()}
                        title="Add this tag"
                        aria-label="Add this tag"
                        className="text-muted-foreground hover:text-ember disabled:opacity-40"
                      >
                        <Plus className="size-3" />
                      </button>
                    </span>
                  </div>
                </Field>
              </div>

              {/* Both sentences stay. They are not decoration: one says the
                  fields and the tags save together and by which key, the other
                  says comments and files do not. Someone who loses a comment
                  because they assumed Save covered it has been failed by a
                  compact screen. Density is the goal here, silence is not - so
                  this drops to the hint size the rest of the panel uses rather
                  than dropping a clause. */}
              <div className="border-t border-border px-4 py-2 text-[11px] leading-relaxed text-muted-foreground">
                Tags, links and the fields above save together - Save, or Ctrl or Cmd plus S.
                Comments and files are their own records and save themselves.
              </div>
            </Card>

            <Card title="Links" subtitle="The brief, the folder, the reference board.">
              <div className="space-y-1 p-4">
                {draft.links.map((row, index) => (
                  <div key={`${row.url}-${index}`} className="flex items-center gap-2 text-sm">
                    <a
                      href={row.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-medium hover:text-ember"
                    >
                      {row.label || row.url}
                    </a>
                    <span className="truncate text-xs text-muted-foreground">{row.url}</span>
                    <button
                      type="button"
                      title="Remove link"
                      aria-label={`Remove link ${row.label || row.url}`}
                      onClick={() =>
                        edit({ links: draft.links.filter((_, item) => item !== index) })
                      }
                      className="ml-auto rounded-md p-1 text-muted-foreground hover:bg-secondary hover:text-ember"
                    >
                      <X className="size-3.5" />
                    </button>
                  </div>
                ))}
                {draft.links.length === 0 ? (
                  <div className="text-xs text-muted-foreground">No links yet.</div>
                ) : null}

                <div className="flex flex-wrap gap-1.5 pt-2">
                  <input
                    value={linkLabel}
                    onChange={(event) => setLinkLabel(event.target.value)}
                    placeholder="Label, e.g. Drive folder"
                    aria-label="Link label"
                    className={`${inputClass} sm:w-2/5`}
                  />
                  <input
                    value={linkUrl}
                    onChange={(event) => setLinkUrl(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key !== "Enter") return;
                      event.preventDefault();
                      addLink();
                    }}
                    placeholder="https://"
                    aria-label="Link URL"
                    className={`${inputClass} sm:flex-1`}
                  />
                  <button type="button" onClick={addLink} className={ghostButton}>
                    <Plus className="size-3" /> Add
                  </button>
                </div>
                {linkError ? <div className="text-xs text-ember">{linkError}</div> : null}
              </div>
            </Card>

            <Card
              title="Comments"
              subtitle={
                comments.data?.length
                  ? countLabel(comments.data.length, "comment")
                  : "Anything the fields cannot say."
              }
            >
              <div className="space-y-2 p-4">
                {(comments.data ?? []).map((row) => (
                  <div
                    key={row.name}
                    className="rounded-lg border border-border bg-secondary/40 px-3 py-2"
                  >
                    <div className="flex flex-wrap items-baseline gap-2 text-xs">
                      <span className="font-medium">{row.comment_by || row.comment_email}</span>
                      <span className="num text-muted-foreground">
                        {formatDateTime(row.creation)}
                      </span>
                    </div>
                    <div className="mt-0.5 text-sm whitespace-pre-line">
                      {stripHtml(row.content)}
                    </div>
                  </div>
                ))}
                {comments.isError ? (
                  <ErrorState error={comments.error} onRetry={() => void comments.refetch()} />
                ) : null}
                {comments.isSuccess && comments.data.length === 0 ? (
                  <div className="text-xs text-muted-foreground">Nothing said yet.</div>
                ) : null}

                <div className="flex gap-1.5 pt-1">
                  <input
                    value={commentDraft}
                    onChange={(event) => setCommentDraft(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key !== "Enter") return;
                      event.preventDefault();
                      comment();
                    }}
                    placeholder="Write a comment"
                    aria-label="Write a comment"
                    className={inputClass}
                  />
                  <button
                    type="button"
                    onClick={comment}
                    disabled={postComment.isPending || !commentDraft.trim()}
                    className={`${ghostButton} disabled:opacity-40`}
                  >
                    {postComment.isPending ? "Posting..." : "Comment"}
                  </button>
                </div>
                {postComment.isError ? (
                  <div className="text-xs text-ember">{postComment.error.messages.join(" ")}</div>
                ) : null}
              </div>
            </Card>
          </div>

          <div className="space-y-4">
            <Card title="At a glance">
              <dl className="space-y-2 p-4 text-sm">
                <div className="flex items-baseline justify-between gap-3">
                  <dt className="text-muted-foreground">Client budget</dt>
                  <dd>
                    {doc?.estimated_budget ? (
                      <Money value={doc.estimated_budget} className="font-medium" />
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </dd>
                </div>
                <div className="flex items-baseline justify-between gap-3">
                  <dt className="text-muted-foreground">Quote</dt>
                  <dd className="text-right">
                    {doc?.quote_status && doc.quote_status !== "Not Sent" ? (
                      doc.quote_status
                    ) : (
                      <span className="text-muted-foreground">Not sent</span>
                    )}
                  </dd>
                </div>
                <div className="flex items-baseline justify-between gap-3">
                  <dt className="text-muted-foreground">Last touched</dt>
                  <dd className="num text-right text-xs text-muted-foreground">
                    {formatDateTime(doc?.modified)}
                  </dd>
                </div>
              </dl>
              <div className="border-t border-border p-4">
                <Link
                  to="/deals/$dealCode/quote"
                  params={{ dealCode }}
                  className="inline-flex items-center gap-1.5 text-xs font-medium hover:text-ember"
                >
                  <FileSpreadsheet className="size-3.5" strokeWidth={1.75} /> Cost lines, margin and
                  the client quote
                </Link>
              </div>
            </Card>

            <Card
              title="Attachments"
              subtitle="Private files, on the deal itself."
              action={
                <>
                  <input
                    ref={picker}
                    type="file"
                    className="hidden"
                    onChange={(event) => {
                      attach(event.target.files?.[0]);
                      event.target.value = "";
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => picker.current?.click()}
                    disabled={uploading}
                    className={`${ghostButton} disabled:opacity-40`}
                  >
                    <Paperclip className="size-3" /> {uploading ? "Uploading..." : "Attach file"}
                  </button>
                </>
              }
            >
              <div className="space-y-1 p-4">
                {(attachments.data ?? []).map((file) => (
                  <div key={file.name} className="flex items-baseline gap-2 text-sm">
                    <a
                      href={file.file_url ?? "#"}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="truncate hover:text-ember"
                    >
                      {file.file_name || file.file_url}
                    </a>
                    <span className="num ml-auto shrink-0 text-xs text-muted-foreground">
                      {fileSize(file.file_size)}
                    </span>
                  </div>
                ))}
                {attachments.isError ? (
                  <ErrorState
                    error={attachments.error}
                    onRetry={() => void attachments.refetch()}
                  />
                ) : null}
                {attachments.isSuccess && attachments.data.length === 0 ? (
                  <div className="text-xs text-muted-foreground">No files yet.</div>
                ) : null}
              </div>
            </Card>

            <Card title="Stage history" subtitle="As stored on the deal, not reconstructed.">
              <div className="space-y-1.5 p-4">
                {(doc?.stage_history ?? []).map((entry) => (
                  <div key={entry.name} className="flex gap-2 text-xs">
                    <span className="num w-32 shrink-0 text-muted-foreground">
                      {formatDateTime(entry.changed_on)}
                    </span>
                    <span className="min-w-0">
                      {entry.from_stage ? (
                        <span className="text-muted-foreground">{entry.from_stage} → </span>
                      ) : null}
                      <span className="font-medium">{entry.to_stage}</span>
                      <span className="text-muted-foreground"> · {entry.changed_by}</span>
                    </span>
                  </div>
                ))}
                {(doc?.stage_history ?? []).length === 0 ? (
                  <div className="text-xs text-muted-foreground">Nothing logged yet.</div>
                ) : null}
              </div>
            </Card>
          </div>

          {error ? (
            <div className="xl:col-span-3">
              <Card>
                <ErrorState error={error} />
                <div className="flex justify-center pb-6">
                  <button type="button" onClick={() => void reload()} className={ghostButton}>
                    <RotateCcw className="size-3" /> Start again from the server's copy
                  </button>
                </div>
              </Card>
            </div>
          ) : null}
        </div>
      )}
      {stageChange.dialogs}
    </AppShell>
  );
}

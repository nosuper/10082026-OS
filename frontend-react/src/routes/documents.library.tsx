// The Library: knowledge the company keeps, as opposed to paperwork it
// generates. An SOP, a checklist, a way of doing something - written once,
// read often, edited in place.
//
// The distinction from the tab next door is the whole design. A generated
// paper is made from a job's records and belongs to that job; it has a
// lifecycle - unsigned, signed, filed. A Library document is made from
// somebody's head and belongs to nobody; it has versions and nothing else.
// Merging the two lists would mean one table answering both questions with
// one set of columns, which is why the founder asked for two tabs.
//
// **No placeholders here, deliberately.** Filling a template from a job is
// Paperwork's job and it is a hard one - see lib/paperwork.py. A document
// that generated nothing needs none of that machinery, and adding it would
// blur the line the two tabs exist to draw.
//
// The first document in here is the deal-classification SOP, which was a Vue
// page until #66 and needed a deploy to change a sentence. Its migration
// dropped two live values on purpose; auraos/patches/seed_sop_deals_library_document.py
// records why.

import { Outlet, createFileRoute, useNavigate, useParams } from "@tanstack/react-router";
import { useState } from "react";
import { BookOpen, LayoutGrid, LockKeyhole, Paperclip, Plus, Rows3, Search } from "lucide-react";

import { AppShell } from "@/components/aura/AppShell";
import { DocumentsTabs } from "@/components/aura/DocumentsTabs";
import { DIALOG_BUTTON, Modal } from "@/components/aura/Modal";
import { RichText } from "@/components/aura/RichText";
import { Card, Pill, Td, Th } from "@/components/aura/primitives";
import { ErrorState, QueryState } from "@/components/aura/states";
import { countLabel, formatDateTime } from "@/lib/format";
import { resultOf, useMethod, useMethodMutation } from "@/lib/queries";

export const Route = createFileRoute("/documents/library")({
  head: () => ({
    meta: [
      { title: "Library - the SOPs and notes the company keeps | AuraOS" },
      {
        name: "description",
        content:
          "Standard operating procedures, checklists and reference notes, editable in the app rather than in a deploy.",
      },
      { property: "og:title", content: "Library - the SOPs and notes the company keeps" },
      {
        property: "og:description",
        content: "Knowledge documents, written once and read often.",
      },
    ],
  }),
  component: LibraryPage,
});

// -- what the server sends --

type LibraryRow = {
  name: string;
  title: string;
  category: string | null;
  /** First line of the prose, from lib/library.py. Not the HTML. */
  snippet: string;
  modified: string;
  attachment_count: number;
};

type LibraryIndex = {
  /** The founder gate, decided by the server, like the Paperwork tab's. */
  can_manage: boolean;
  categories: string[];
  documents: LibraryRow[];
};

type LibraryDoc = {
  name: string;
  title: string;
  category: string | null;
  body: string;
  modified: string;
  attachments: { name: string; file_name: string; file_url: string }[];
};

const DOCUMENTS = "auraos.api.library_documents";
// `_detail` rather than the singular of the line above: two endpoints that
// differ by one trailing letter are a typo away from returning a list where
// a record was expected, which fails somewhere other than the mistake.
const DOCUMENT_DETAIL = "auraos.api.library_document_detail";
const SAVE = "auraos.api.save_library_document";

const ALL = "All";

type View = "cards" | "table";

/** A draft is a document being written, which a saved one is not: it has no
 *  name until the server gives it one. `null` name means "new". */
type Draft = { key: number; name: string | null; title: string; category: string; body: string };

function LibraryPage() {
  const index = useMethod<LibraryIndex>(DOCUMENTS);

  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<string>(ALL);
  const [view, setView] = useState<View>("cards");
  // **Which document is open is a fact about the URL, not about this
  // component** (#124). It used to be `useState`, which is why a link to a
  // document landed the recipient on the tab: the address bar never learned
  // anything. `strict: false` because this route matches with and without the
  // child - `/documents/library` has no `docName` and that is not an error,
  // it is the list.
  const { docName } = useParams({ strict: false }) as { docName?: string };
  const navigate = useNavigate();
  const openName = docName ?? null;
  const openDocument = (name: string) =>
    void navigate({ to: "/documents/library/$docName", params: { docName: name } });
  const closeDocument = () => void navigate({ to: "/documents/library" });
  const [draft, setDraft] = useState<Draft | null>(null);

  const canManage = index.data?.can_manage ?? false;
  const documents = index.data?.documents ?? [];
  const categories = index.data?.categories ?? [];

  const needle = search.trim().toLowerCase();
  const shown = documents.filter(
    (row) =>
      (category === ALL || row.category === category) &&
      // Searching the snippet as well as the title, because a library is for
      // the document you half remember: you know a phrase in it, not its name.
      (needle
        ? [row.title, row.category, row.snippet]
            .filter(Boolean)
            .some((text) => String(text).toLowerCase().includes(needle))
        : true),
  );

  const meta = index.isSuccess ? countLabel(documents.length, "document") : undefined;

  return (
    <AppShell title="Documents" meta={meta}>
      <div className="space-y-5">
        <DocumentsTabs />

        <p className="max-w-3xl text-sm text-muted-foreground">
          How the company does things: SOPs, checklists, the reasoning behind a rule. Edited here
          rather than in a deploy, so the version on screen is the version in force.
        </p>

        {index.isSuccess && !canManage ? (
          <div className="flex items-start gap-2 rounded-xl border border-border bg-card px-4 py-3 text-sm text-muted-foreground">
            <LockKeyhole className="mt-0.5 size-3.5 shrink-0" strokeWidth={1.75} />
            <span>Only the founder can add or change these. You can read all of them.</span>
          </div>
        ) : null}

        <Card
          title="Library"
          subtitle={
            index.isSuccess && shown.length !== documents.length
              ? `${countLabel(shown.length, "document")} of ${documents.length}`
              : undefined
          }
          action={
            <div className="flex flex-wrap items-center gap-1.5">
              <div className="flex items-center gap-1.5 rounded-lg border border-border px-2 py-1">
                <Search className="size-3.5 shrink-0 text-muted-foreground" />
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search"
                  aria-label="Search the library"
                  className="w-32 bg-transparent text-sm outline-none placeholder:text-muted-foreground sm:w-44"
                />
              </div>
              <ViewToggle view={view} onChange={setView} />
              {canManage ? (
                <button
                  type="button"
                  onClick={() =>
                    setDraft({ key: Date.now(), name: null, title: "", category: "", body: "" })
                  }
                  className="flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium hover:bg-secondary"
                >
                  <Plus className="size-3.5" strokeWidth={2} />
                  New document
                </button>
              ) : null}
            </div>
          }
        >
          <QueryState
            query={index}
            isEmpty={() => documents.length === 0}
            empty={{
              title: "Nothing in the library yet.",
              detail: canManage
                ? "Write the first one - an SOP, a checklist, a way of working."
                : "The founder has not added any documents yet.",
              icon: <BookOpen className="size-6" strokeWidth={1.5} />,
            }}
          >
            {() => (
              <>
                {categories.length > 0 ? (
                  <CategoryFilters
                    categories={categories}
                    current={category}
                    onChange={setCategory}
                    countOf={(value) =>
                      value === ALL
                        ? documents.length
                        : documents.filter((row) => row.category === value).length
                    }
                  />
                ) : null}

                {shown.length === 0 ? (
                  <p className="px-4 py-8 text-center text-sm text-muted-foreground">
                    Nothing matches that.
                  </p>
                ) : view === "cards" ? (
                  <DocumentCards rows={shown} onOpen={openDocument} />
                ) : (
                  <DocumentTable rows={shown} onOpen={openDocument} />
                )}
              </>
            )}
          </QueryState>
        </Card>
      </div>

      {/* The child route renders nothing; it exists so the router will match
          and restore `/documents/library/$docName`. The window stays here,
          where `canManage` and the edit draft already live - a ticket about
          addressability is not a reason to move state ownership. */}
      <Outlet />

      {openName ? (
        <DocumentWindow
          name={openName}
          canManage={canManage}
          onClose={closeDocument}
          onEdit={(doc) =>
            setDraft({
              key: Date.now(),
              name: doc.name,
              title: doc.title,
              category: doc.category ?? "",
              body: doc.body,
            })
          }
        />
      ) : null}

      {draft ? (
        <DocumentEditor
          draft={draft}
          categories={categories}
          onChange={setDraft}
          onClose={() => setDraft(null)}
          onSaved={(name) => {
            setDraft(null);
            openDocument(name);
          }}
        />
      ) : null}
    </AppShell>
  );
}

// -- the two views the founder asked for --

function ViewToggle({ view, onChange }: { view: View; onChange: (view: View) => void }) {
  const options = [
    { value: "cards" as const, label: "Cards", icon: LayoutGrid },
    { value: "table" as const, label: "Table", icon: Rows3 },
  ];
  return (
    <div
      role="group"
      aria-label="View"
      className="flex items-center rounded-lg border border-border"
    >
      {options.map((option) => {
        const Icon = option.icon;
        const active = view === option.value;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            title={option.label}
            aria-label={option.label}
            onClick={() => onChange(option.value)}
            className={
              "flex items-center gap-1.5 px-2.5 py-1.5 text-xs first:rounded-l-lg last:rounded-r-lg " +
              (active
                ? "bg-secondary font-medium text-foreground"
                : "text-muted-foreground hover:text-foreground")
            }
          >
            <Icon className="size-3.5" strokeWidth={1.75} />
          </button>
        );
      })}
    </div>
  );
}

function CategoryFilters({
  categories,
  current,
  onChange,
  countOf,
}: {
  categories: string[];
  current: string;
  onChange: (value: string) => void;
  countOf: (value: string) => number;
}) {
  return (
    <div className="flex flex-wrap gap-1.5 border-b border-border px-4 py-3">
      {[ALL, ...categories].map((value) => {
        const active = current === value;
        return (
          <button
            key={value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(value)}
            className={
              "rounded-md border px-2 py-0.5 text-[11px] font-medium whitespace-nowrap " +
              (active
                ? "border-border-strong bg-secondary text-foreground"
                : "border-border text-muted-foreground hover:text-foreground")
            }
          >
            {value} <span className="num opacity-60">{countOf(value)}</span>
          </button>
        );
      })}
    </div>
  );
}

function DocumentCards({ rows, onOpen }: { rows: LibraryRow[]; onOpen: (name: string) => void }) {
  return (
    <ul className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-3">
      {rows.map((row) => (
        <li key={row.name}>
          <button
            type="button"
            onClick={() => onOpen(row.name)}
            className="flex h-full w-full flex-col gap-2 rounded-xl border border-border bg-background p-4 text-left transition-colors hover:border-border-strong"
          >
            <div className="flex items-start gap-2">
              <BookOpen
                className="mt-0.5 size-4 shrink-0 text-muted-foreground"
                strokeWidth={1.5}
                aria-hidden="true"
              />
              <span className="min-w-0 flex-1 font-medium">{row.title}</span>
            </div>
            {/* The snippet is prose, not markup: lib/library.py strips the
                tags server-side, so nothing here renders raw HTML. */}
            <p className="line-clamp-3 text-xs text-muted-foreground">{row.snippet}</p>
            <div className="mt-auto flex flex-wrap items-center gap-2 pt-1">
              {row.category ? <Pill>{row.category}</Pill> : null}
              {row.attachment_count > 0 ? (
                <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                  <Paperclip className="size-3" strokeWidth={1.75} />
                  {row.attachment_count}
                </span>
              ) : null}
              <span className="ml-auto text-[11px] text-muted-foreground">
                {formatDateTime(row.modified)}
              </span>
            </div>
          </button>
        </li>
      ))}
    </ul>
  );
}

function DocumentTable({ rows, onOpen }: { rows: LibraryRow[]; onOpen: (name: string) => void }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="border-b border-border">
          <tr>
            <Th>Title</Th>
            <Th>Category</Th>
            <Th className="text-right">Files</Th>
            <Th>Updated</Th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((row) => (
            <tr key={row.name} className="hover:bg-secondary/40">
              <Td>
                <button
                  type="button"
                  onClick={() => onOpen(row.name)}
                  className="text-left font-medium hover:underline"
                >
                  {row.title}
                </button>
                <p className="truncate text-xs text-muted-foreground">{row.snippet}</p>
              </Td>
              <Td>{row.category ? <Pill>{row.category}</Pill> : "-"}</Td>
              <Td className="num text-right text-muted-foreground">
                {row.attachment_count || "-"}
              </Td>
              <Td className="whitespace-nowrap text-muted-foreground">
                {formatDateTime(row.modified)}
              </Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// -- reading one, and writing one --

function DocumentWindow({
  name,
  canManage,
  onClose,
  onEdit,
}: {
  name: string;
  canManage: boolean;
  onClose: () => void;
  onEdit: (doc: LibraryDoc) => void;
}) {
  const doc = useMethod<LibraryDoc>(DOCUMENT_DETAIL, { name });
  // Captured rather than read through `doc.data` inside the handler, so the
  // narrowing survives into the closure.
  const data = doc.data;

  return (
    <Modal
      title={data?.title ?? "Document"}
      onClose={onClose}
      footer={
        <>
          {data && canManage ? (
            <button type="button" className={DIALOG_BUTTON} onClick={() => onEdit(data)}>
              Edit
            </button>
          ) : null}
          <button type="button" className={DIALOG_BUTTON} onClick={onClose}>
            Close
          </button>
        </>
      }
    >
      <QueryState query={doc} isEmpty={() => false}>
        {(loaded) => (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              {loaded.category ? <Pill>{loaded.category}</Pill> : null}
              <span>Updated {formatDateTime(loaded.modified)}</span>
            </div>

            {/* The body is the founder's own HTML, written through the app's
                one editor and stored in a Frappe Text Editor field, which
                sanitises on save. Rendering it is the point of the screen.
                overflow-x-auto because a seeded document can carry a table
                wider than this dialog - the SOP's tier matrix does. */}
            <div
              className="aura-rich overflow-x-auto text-sm"
              dangerouslySetInnerHTML={{ __html: loaded.body || "<p></p>" }}
            />

            {loaded.attachments.length > 0 ? (
              <div className="border-t border-border pt-3">
                <p className="label-caps mb-2">Attachments</p>
                <ul className="space-y-1">
                  {loaded.attachments.map((file) => (
                    <li key={file.name}>
                      <a
                        href={file.file_url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground hover:underline"
                      >
                        <Paperclip className="size-3.5 shrink-0" strokeWidth={1.75} />
                        {file.file_name}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        )}
      </QueryState>
    </Modal>
  );
}

function DocumentEditor({
  draft,
  categories,
  onChange,
  onClose,
  onSaved,
}: {
  draft: Draft;
  categories: string[];
  onChange: (draft: Draft) => void;
  onClose: () => void;
  onSaved: (name: string) => void;
}) {
  const save = useMethodMutation<{ name: string }, Record<string, unknown>>(SAVE, {
    invalidate: [resultOf(DOCUMENTS), resultOf(DOCUMENT_DETAIL)],
    onSuccess: (result) => onSaved(result.name),
  });

  const titled = draft.title.trim().length > 0;

  return (
    <Modal
      title={draft.name ? "Edit document" : "New document"}
      onClose={onClose}
      footer={
        <>
          {save.isError ? (
            <div className="mr-auto max-w-md">
              <ErrorState error={save.error} />
            </div>
          ) : null}
          <button type="button" className={DIALOG_BUTTON} onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            disabled={!titled || save.isPending}
            onClick={() =>
              save.mutate({
                name: draft.name,
                title: draft.title.trim(),
                category: draft.category.trim(),
                body: draft.body,
              })
            }
            className="rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {save.isPending ? "Saving..." : "Save"}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="label-caps">Title</span>
            <input
              value={draft.title}
              onChange={(event) => onChange({ ...draft, title: event.target.value })}
              placeholder="SOP - how we do the thing"
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-border-strong"
            />
          </label>
          <label className="block">
            <span className="label-caps">Category</span>
            {/* A free-text field with suggestions rather than a fixed list:
                adding a category is the founder typing one, not a deploy. */}
            <input
              value={draft.category}
              list="library-categories"
              onChange={(event) => onChange({ ...draft, category: event.target.value })}
              placeholder="SOP"
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-border-strong"
            />
            <datalist id="library-categories">
              {categories.map((value) => (
                <option key={value} value={value} />
              ))}
            </datalist>
          </label>
        </div>

        <div>
          <span className="label-caps">Body</span>
          <div className="mt-1">
            {/* Keyed on the draft, because RichText writes its body once on
                mount by design - see RichText.tsx. Opening a different
                document has to remount it or the caret fights the state. */}
            <RichText
              key={draft.key}
              defaultValue={draft.body}
              onChange={(html) => onChange({ ...draft, body: html })}
              ariaLabel="Document body"
              className="min-h-[22rem]"
            />
          </div>
        </div>
      </div>
    </Modal>
  );
}

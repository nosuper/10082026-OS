// Paperwork, on real data: the template library, the registry of every paper
// ever generated, and the reading window both of them open into.
//
// The screen is the React half of frontend/src/pages/PaperworkPage.vue, which
// is still the running implementation. Same four endpoints, same founder gate,
// same placeholder vocabulary - nothing new was asked of the backend.
//
// Generating a paper is not here: it happens on a job, against that job's
// records (auraos.api.generate_job_paperwork). This screen owns what a paper is
// made *from*, and what has been made.

import { createFileRoute, Link } from "@tanstack/react-router";
import type { UseQueryResult } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  Bold,
  Download,
  FileText,
  Italic,
  List,
  LockKeyhole,
  Pencil,
  Printer,
  Search,
  X,
} from "lucide-react";

import { AppShell } from "@/components/aura/AppShell";
import { Card, Pill, Td, Th } from "@/components/aura/primitives";
import { Empty, ErrorState, QueryState } from "@/components/aura/states";
import { countLabel, formatDateTime } from "@/lib/format";
import { FrappeError, uploadFile, type UploadedFile } from "@/lib/frappe";
import { resultOf, useMethod, useMethodMutation } from "@/lib/queries";

export const Route = createFileRoute("/paperwork")({
  head: () => ({
    meta: [
      { title: "Paperwork - template library and generated papers | AuraOS" },
      {
        name: "description",
        content:
          "The contract templates a job can be papered from, every document generated so far, and the gaps still unfilled in each one.",
      },
      { property: "og:title", content: "Paperwork - template library and generated papers" },
      {
        property: "og:description",
        content: "Templates, placeholders and the registry of generated documents in one place.",
      },
    ],
  }),
  component: PaperworkPage,
});

// -- what the server sends --

type TemplateRow = {
  name: string;
  template_name: string;
  template_file: string | null;
  template_source: string | null;
  notes: string | null;
  disabled: number;
  /** Placeholder names read back out of the file on every save. */
  placeholders: string[];
  /** The ones the fill pipeline cannot answer: a typo in the docx. */
  unknown_placeholders: string[];
  needs_vendor: boolean;
  needs_freelancer: boolean;
};

type Library = {
  /** The founder gate, decided by the server. Never inferred in the browser. */
  can_manage: boolean;
  placeholders: string[];
  templates: TemplateRow[];
};

type PaperRow = {
  name: string;
  job: string;
  template: string | null;
  template_name: string | null;
  vendor: string | null;
  freelancer: string | null;
  file_name: string;
  file_url: string;
  owner: string;
  creation: string;
  vendor_label: string | null;
  freelancer_label: string | null;
};

type Preview = { html: string | null; web?: boolean; file_url?: string | null };


const LIBRARY = "auraos.api.paperwork_library";
const PAPERS = "auraos.api.generated_papers";
const PREVIEW_TEMPLATE = "auraos.api.preview_template";
const PREVIEW_PAPER = "auraos.api.preview_paper";

/** The MIME type Word writes. A .doc renamed, or a PDF, is refused on save. */
const DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

// Shown, never interpolated: this is the syntax a template is written in.
function braced(field: string): string {
  return `{{${field}}}`;
}

const ROW_BUTTON =
  "rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:border-border-strong hover:text-foreground";

// -- the one thing the shared transport cannot do --
//
// lib/frappe.ts posts JSON, which is the right call for every other request in
// the app; an upload is multipart. Rather than widen the shared layer for one
// screen, the upload lives here and hands back the same FrappeError everything
// else throws, so <ErrorState> reads it the way it reads the rest.

const PLACEHOLDER = /\{\{\s*([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*)\s*\}\}/g;

function chipHtml(field: string): string {
  return (
    `<span class="mention" data-type="mention" data-id="${field}" ` +
    `data-label="${field}" contenteditable="false">@${field}</span>`
  );
}

function sourceToEditor(source: string): string {
  return source.replace(PLACEHOLDER, (_match, field: string) => chipHtml(field));
}

function editorToSource(html: string): string {
  const parsed = new DOMParser().parseFromString(html, "text/html");
  for (const chip of parsed.querySelectorAll('[data-type="mention"]')) {
    const field = chip.getAttribute("data-id");
    chip.replaceWith(parsed.createTextNode(field ? braced(field) : ""));
  }
  return parsed.body.innerHTML;
}

/** Legacy sources were plain paragraph lines; both stay editable. */
function asHtml(source: string): string {
  const trimmed = source.trimStart();
  if (!trimmed) return "";
  if (trimmed.startsWith("<")) return source;
  return source
    .split("\n")
    .map((line) => `<p>${line}</p>`)
    .join("");
}

function gapCount(html: string): number {
  return (html.match(/data-gap/g) ?? []).length;
}

/**
 * The printed paper. Its stylesheet is the contract look the founder signs off
 * on, carried over from PaperWindow.vue unchanged - screen tokens deliberately
 * do not reach in here.
 */
function printPaper(html: string): void {
  const printWindow = window.open("", "_blank");
  if (!printWindow) return;
  printWindow.document.write(`<!doctype html><html><head><meta charset="utf-8">
    <title>Print</title>
    <style>
      body { font-family: "Times New Roman", serif; font-size: 13pt;
             line-height: 1.6; max-width: 17cm; margin: 1cm auto; }
      mark[data-gap] { background: #fde68a; }
      h1, h2, h3 { line-height: 1.3; }
      span.mention { font-family: ui-monospace, monospace; background: #f3f4f6;
             padding: 0 2px; border-radius: 2px; }
      table { border-collapse: collapse; width: 100%; margin: 0.4cm 0; }
      td, th { border: 1px solid #6b7280; padding: 0.15cm 0.25cm;
             vertical-align: top; }
      table.borderless td, table.borderless th { border: none; }
      td p { margin: 0; }
    </style></head><body>${html}</body></html>`);
  printWindow.document.close();
  printWindow.focus();
  printWindow.print();
}

// The reading view and the editor share one look for document text. Written
// here rather than in styles.css because only this screen renders a paper.
// Vietnamese belongs to the text face: the gap marker says "thiếu", and the
// mono face has no diacritics to say it with.
const PAPER_CSS = `
.aura-paper { font-family: var(--font-sans); font-size: 13px; line-height: 1.75; }
.aura-paper p { margin: 0 0 0.65rem; }
.aura-paper h1 { font-size: 1.15rem; font-weight: 600; margin: 1.1rem 0 0.6rem; }
.aura-paper h2 { font-size: 1.02rem; font-weight: 600; margin: 1rem 0 0.5rem; }
.aura-paper h3 { font-size: 0.95rem; font-weight: 600; margin: 0.9rem 0 0.45rem; }
.aura-paper ul { list-style: disc; margin: 0 0 0.65rem 1.25rem; }
.aura-paper ol { list-style: decimal; margin: 0 0 0.65rem 1.25rem; }
.aura-paper li { margin: 0.15rem 0; }
.aura-paper strong { font-weight: 600; }
.aura-paper em { font-style: italic; }
.aura-paper table { border-collapse: collapse; width: 100%; margin: 0.5rem 0; }
.aura-paper td, .aura-paper th { border: 1px solid var(--border-strong);
  padding: 0.35rem 0.6rem; vertical-align: top; }
.aura-paper td p { margin: 0; }
.aura-paper table.borderless td, .aura-paper table.borderless th { border: none; }
.aura-paper mark[data-gap] { background-color: var(--ember-soft); color: var(--ember);
  padding: 0 3px; border-radius: 4px;
  box-shadow: inset 0 0 0 1px color-mix(in oklab, var(--ember) 30%, transparent); }
.aura-paper span.mention { font-family: var(--font-mono); font-size: 0.85em;
  background: var(--ember-soft); color: var(--ember); padding: 0 4px;
  border-radius: 4px; white-space: nowrap; }
`;

// -- the screen --

type EditorDraft = { key: number; name: string | null; templateName: string; source: string };

type WindowState = { kind: "template"; row: TemplateRow } | { kind: "paper"; row: PaperRow } | null;

function PaperworkPage() {
  const library = useMethod<Library>(LIBRARY);
  const papers = useMethod<PaperRow[]>(PAPERS);

  const [paperWindow, setPaperWindow] = useState<WindowState>(null);
  const [editor, setEditor] = useState<EditorDraft | null>(null);
  const [search, setSearch] = useState("");

  const templates = library.data?.templates ?? [];
  const canManage = library.data?.can_manage ?? false;
  const fields = library.data?.placeholders ?? [];

  // Both windows are ordinary reads, so they cache, retry and show their own
  // failure. Neither runs until something is open.
  const templatePreview = useMethod<Preview>(
    PREVIEW_TEMPLATE,
    { template: paperWindow?.kind === "template" ? paperWindow.row.name : "" },
    { enabled: paperWindow?.kind === "template" },
  );
  const paperPreview = useMethod<Preview>(
    PREVIEW_PAPER,
    { file_url: paperWindow?.kind === "paper" ? paperWindow.row.file_url : "" },
    { enabled: paperWindow?.kind === "paper" },
  );

  function openEditor(row: TemplateRow | null, source?: string) {
    setEditor({
      key: Date.now(),
      name: row?.name ?? null,
      templateName: row?.template_name ?? "",
      source: asHtml(source ?? row?.template_source ?? ""),
    });
  }

  const meta = [
    library.isSuccess ? countLabel(templates.length, "template") : null,
    papers.isSuccess ? `${countLabel(papers.data?.length ?? 0, "paper")} generated` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  const needle = search.trim().toLowerCase();
  const shownPapers = (papers.data ?? []).filter((row) =>
    needle
      ? [row.template_name, row.file_name, row.job, row.vendor_label, row.freelancer_label]
          .filter(Boolean)
          .some((text) => String(text).toLowerCase().includes(needle))
      : true,
  );

  return (
    <AppShell title="Paperwork" meta={meta}>
      <style>{PAPER_CSS}</style>

      <div className="space-y-5">
        <p className="max-w-3xl text-sm text-muted-foreground">
          Design each paper once in Word - letterhead, clauses, signature block - and type{" "}
          <code className="num rounded border border-border bg-secondary px-1 py-0.5 text-[11px] text-foreground">
            {braced("client.tax_code")}
          </code>{" "}
          where a value belongs. Generating on a job fills those in and attaches the result to it.
        </p>

        {/* The founder gate is the server's answer, not a guess about the
            signed-in user. A producer is told why, rather than shown less. */}
        {library.isSuccess && !canManage ? (
          <div className="flex items-start gap-2 rounded-xl border border-border bg-card px-4 py-3 text-sm text-muted-foreground">
            <LockKeyhole className="mt-0.5 size-3.5 shrink-0" strokeWidth={1.75} />
            <span>
              Only the founder can add or change templates. You can generate paperwork from these on
              any job.
            </span>
          </div>
        ) : null}

        <div className="grid gap-4 lg:grid-cols-3">
          <Card
            className="h-fit lg:col-span-2"
            title="Template library"
            subtitle="Open one to read it; edit, print and download live inside."
          >
            <QueryState
              query={library}
              isEmpty={() => templates.length === 0}
              empty={{
                title: "The library is empty.",
                detail: canManage ? "Upload a .docx, or write one here." : undefined,
                icon: <FileText className="size-6" strokeWidth={1.5} />,
              }}
            >
              {() => (
                <ul className="divide-y divide-border">
                  {templates.map((row) => (
                    <TemplateItem
                      key={row.name}
                      row={row}
                      canManage={canManage}
                      onOpen={() => setPaperWindow({ kind: "template", row })}
                      onEdit={() => openEditor(row)}
                    />
                  ))}
                </ul>
              )}
            </QueryState>
          </Card>

          <div className="space-y-4">
            {canManage ? <NewTemplateCard onWriteOne={() => openEditor(null)} /> : null}

            {library.isSuccess ? (
              <Card title={`Placeholders a template can use (${fields.length})`}>
                <div className="grid grid-cols-2 gap-x-3 gap-y-1 px-4 py-3">
                  {fields.map((field) => (
                    <code
                      key={field}
                      title={braced(field)}
                      className="num truncate text-[11px] text-muted-foreground"
                    >
                      {braced(field)}
                    </code>
                  ))}
                </div>
                <p className="border-t border-border px-4 py-3 text-xs text-muted-foreground">
                  Our own company name, tax code and address are not on this list - they are the
                  same on every paper, so type them into the template.
                </p>
              </Card>
            ) : null}
          </div>
        </div>

        <Card
          title="Generated papers"
          subtitle={papers.isSuccess ? countLabel(papers.data?.length ?? 0, "document") : undefined}
          action={
            <div className="flex items-center gap-1.5 rounded-lg border border-border px-2 py-1">
              <Search className="size-3.5 shrink-0 text-muted-foreground" />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search"
                className="w-32 bg-transparent text-sm outline-none placeholder:text-muted-foreground sm:w-44"
              />
            </div>
          }
        >
          <QueryState
            query={papers}
            isEmpty={() => (papers.data ?? []).length === 0}
            empty={{
              title: "Nothing generated yet.",
              detail: "Papers made on a job appear here.",
              icon: <FileText className="size-6" strokeWidth={1.5} />,
            }}
          >
            {() =>
              shownPapers.length === 0 ? (
                <Empty title="No paper matches that." detail="Clear the search to see them all." />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="border-b border-border">
                      <tr>
                        <Th>Paper</Th>
                        <Th>For</Th>
                        <Th>Job</Th>
                        <Th>Generated</Th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {shownPapers.map((row) => (
                        <tr key={row.name} className="hover:bg-secondary/50">
                          <Td className="font-medium">
                            <button
                              type="button"
                              onClick={() => setPaperWindow({ kind: "paper", row })}
                              className="max-w-[22rem] truncate text-left hover:text-ember"
                            >
                              {row.template_name || row.file_name}
                            </button>
                          </Td>
                          <Td className="text-muted-foreground">
                            {row.freelancer_label || row.vendor_label || "Client"}
                          </Td>
                          <Td>
                            <Link
                              to="/jobs/$jobId"
                              params={{ jobId: row.job }}
                              className="num text-xs text-muted-foreground hover:text-ember"
                            >
                              {row.job}
                            </Link>
                          </Td>
                          <Td className="num text-xs whitespace-nowrap text-muted-foreground">
                            {formatDateTime(row.creation)}
                          </Td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
            }
          </QueryState>
        </Card>
      </div>

      {paperWindow?.kind === "template" ? (
        <PaperWindowDialog
          title={paperWindow.row.template_name}
          query={templatePreview}
          fallback="(Không đọc được nội dung file)"
          downloadUrl={paperWindow.row.template_file ?? ""}
          editLabel={canManage ? "Edit template" : undefined}
          onEdit={(html) => {
            const row = paperWindow.row;
            setPaperWindow(null);
            // An uploaded template edited here becomes a web one: the window's
            // extracted text, placeholders included, is the new source.
            openEditor(row, row.template_source || html);
          }}
          onClose={() => setPaperWindow(null)}
        />
      ) : null}

      {paperWindow?.kind === "paper" ? (
        <PaperWindowDialog
          title={paperWindow.row.template_name || paperWindow.row.file_name}
          query={paperPreview}
          fallback="(File này không phải văn bản .docx)"
          downloadUrl={paperWindow.row.file_url}
          editLabel="Edit"
          editInline
          onClose={() => setPaperWindow(null)}
        />
      ) : null}

      {editor ? (
        <TemplateEditorDialog
          key={editor.key}
          draft={editor}
          fields={fields}
          onClose={() => setEditor(null)}
          onSaved={() => setEditor(null)}
        />
      ) : null}
    </AppShell>
  );
}

// -- the library row --

function TemplateItem({
  row,
  canManage,
  onOpen,
  onEdit,
}: {
  row: TemplateRow;
  canManage: boolean;
  onOpen: () => void;
  onEdit: () => void;
}) {
  const retire = useMethodMutation<unknown, Record<string, unknown>>("frappe.client.set_value", {
    invalidate: [resultOf(LIBRARY)],
  });
  const remove = useMethodMutation<unknown, Record<string, unknown>>("frappe.client.delete", {
    invalidate: [resultOf(LIBRARY)],
  });

  const busy = retire.isPending || remove.isPending;

  return (
    <li className={row.disabled ? "px-4 py-3 opacity-60" : "px-4 py-3"}>
      <div className="flex flex-wrap items-center gap-2">
        <FileText className="size-4 shrink-0 text-muted-foreground" strokeWidth={1.75} />
        <button
          type="button"
          onClick={onOpen}
          className="min-w-0 truncate text-sm font-medium hover:text-ember"
        >
          {row.template_name}
        </button>
        {row.template_source ? (
          <Pill tone="neutral" className="shrink-0">
            Web
          </Pill>
        ) : null}
        {row.disabled ? (
          <Pill tone="outline" className="shrink-0">
            Retired
          </Pill>
        ) : null}

        <span className="ml-auto flex shrink-0 items-center gap-1">
          {row.template_file ? (
            <a
              href={row.template_file}
              title="Download the .docx"
              className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
            >
              <Download className="size-3.5" />
            </a>
          ) : null}
          {/* Offered only where the server would accept them. The refusal is
              still the server's: hiding a button is not a permission. */}
          {canManage ? (
            <>
              {row.template_source ? (
                <button type="button" className={ROW_BUTTON} onClick={onEdit}>
                  Edit
                </button>
              ) : null}
              <button
                type="button"
                className={ROW_BUTTON}
                disabled={busy}
                onClick={() =>
                  retire.mutate({
                    doctype: "Paperwork Template",
                    name: row.name,
                    fieldname: { disabled: row.disabled ? 0 : 1 },
                  })
                }
              >
                {row.disabled ? "Bring back" : "Retire"}
              </button>
              <button
                type="button"
                disabled={busy}
                className="rounded-md border border-ember/40 px-2 py-1 text-xs text-ember hover:bg-ember-soft"
                onClick={() => {
                  // Papers already generated hang off their jobs and survive
                  // this; deleting only stops new ones being made from it.
                  if (!window.confirm(`Delete the template "${row.template_name}"?`)) return;
                  remove.mutate({ doctype: "Paperwork Template", name: row.name });
                }}
              >
                Delete
              </button>
            </>
          ) : null}
        </span>
      </div>

      {row.unknown_placeholders.length ? (
        <p className="mt-2 flex items-start gap-1.5 rounded-lg border border-ember/25 bg-ember-soft px-2 py-1.5 text-xs text-ember">
          <AlertTriangle className="mt-0.5 size-3 shrink-0" />
          <span>
            Asks for {row.unknown_placeholders.join(", ")} - no such placeholder, so it prints as a
            gap marker. Fix the docx and upload it again.
          </span>
        </p>
      ) : null}

      {row.placeholders.length ? (
        <div className="mt-2 flex flex-wrap items-center gap-1">
          <span className="label-caps mr-0.5">Fills</span>
          {row.placeholders.map((field) => (
            <code
              key={field}
              className={
                row.unknown_placeholders.includes(field)
                  ? "num rounded border border-ember/25 bg-ember-soft px-1.5 py-0.5 text-[11px] text-ember"
                  : "num rounded border border-border bg-secondary px-1.5 py-0.5 text-[11px] text-muted-foreground"
              }
            >
              {field}
            </code>
          ))}
        </div>
      ) : (
        <p className="mt-2 text-xs text-muted-foreground">
          No placeholders - this prints exactly as designed.
        </p>
      )}

      {retire.isError ? <ErrorState error={retire.error} className="px-0 py-2" /> : null}
      {remove.isError ? <ErrorState error={remove.error} className="px-0 py-2" /> : null}
    </li>
  );
}

// -- adding one from Word --

function NewTemplateCard({ onWriteOne }: { onWriteOne: () => void }) {
  const [name, setName] = useState("");
  const [uploaded, setUploaded] = useState<UploadedFile | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<unknown>(null);
  const picker = useRef<HTMLInputElement>(null);

  const add = useMethodMutation<unknown, Record<string, unknown>>("frappe.client.insert", {
    invalidate: [resultOf(LIBRARY)],
    onSuccess: () => {
      setName("");
      setUploaded(null);
    },
  });

  function choose(file: File | undefined) {
    if (!file) return;
    setUploadError(null);
    setUploading(true);
    uploadFile(file, { isPrivate: true })
      .then((result) => setUploaded(result))
      .catch((error: unknown) => setUploadError(error))
      .finally(() => setUploading(false));
  }

  return (
    <Card title="New template" subtitle="Upload the Word file, or write one in the app.">
      <div className="grid gap-2 p-4">
        <label className="block">
          <span className="label-caps">Name</span>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Hợp đồng dịch vụ"
            className="mt-1 w-full rounded-lg border border-border bg-background px-2.5 py-2 text-sm"
          />
        </label>

        <input
          ref={picker}
          type="file"
          accept={`.docx,${DOCX}`}
          className="hidden"
          onChange={(event) => {
            choose(event.target.files?.[0]);
            event.target.value = "";
          }}
        />
        <button
          type="button"
          disabled={uploading}
          onClick={() => picker.current?.click()}
          className="rounded-lg border border-border px-3 py-2 text-sm hover:bg-secondary disabled:opacity-40"
        >
          {uploading ? "Uploading..." : uploaded ? "Choose another .docx" : "Choose .docx"}
        </button>
        {uploaded ? (
          <p className="truncate text-xs text-muted-foreground">{uploaded.file_name}</p>
        ) : null}

        <button
          type="button"
          disabled={!name.trim() || !uploaded || add.isPending}
          onClick={() =>
            add.mutate({
              doc: {
                doctype: "Paperwork Template",
                template_name: name.trim(),
                template_file: uploaded?.file_url,
              },
            })
          }
          className="rounded-lg bg-ember px-3 py-2 text-sm font-medium text-ember-foreground hover:opacity-90 disabled:opacity-40"
        >
          {add.isPending ? "Adding..." : "Add to library"}
        </button>

        <button
          type="button"
          onClick={onWriteOne}
          className="rounded-lg border border-border px-3 py-2 text-sm hover:bg-secondary"
        >
          Write one here
        </button>

        {uploadError ? <ErrorState error={uploadError} className="px-0 py-2" /> : null}
        {add.isError ? <ErrorState error={add.error} className="px-0 py-2" /> : null}
      </div>
      <p className="border-t border-border px-4 py-3 text-xs text-muted-foreground">
        Only .docx - a .doc renamed, or a PDF, is refused by the server when saved.
      </p>
    </Card>
  );
}

// -- the modal shell both windows sit in --

function Modal({
  title,
  onClose,
  children,
  footer,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  footer: React.ReactNode;
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
        type="button"
        aria-label="Close"
        onClick={onClose}
        className="fixed inset-0 bg-primary/25 backdrop-blur-[1px]"
      />
      <div
        role="dialog"
        aria-label={title}
        className="relative z-10 w-full max-w-4xl rounded-xl border border-border bg-card shadow-lg"
      >
        <header className="flex items-start gap-3 border-b border-border px-5 py-4">
          <h2 className="min-w-0 flex-1 truncate font-display text-base font-semibold tracking-tight">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary"
          >
            <X className="size-4" />
          </button>
        </header>
        <div className="px-5 py-5">{children}</div>
        <footer className="flex flex-wrap items-center justify-end gap-2 border-t border-border px-5 py-4">
          {footer}
        </footer>
      </div>
    </div>
  );
}

const DIALOG_BUTTON =
  "rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-secondary";

/**
 * One window for every paper-shaped thing: a template, or a document already
 * generated. It opens reading, edits on request, prints what is on screen and
 * downloads the stored file. The gap counter is the point of it: what is still
 * unfilled is said in words before anybody sends the thing.
 */
function PaperWindowDialog({
  title,
  query,
  fallback,
  downloadUrl,
  editLabel,
  editInline,
  onEdit,
  onClose,
}: {
  title: string;
  query: UseQueryResult<Preview, FrappeError>;
  fallback: string;
  downloadUrl: string;
  editLabel?: string | undefined;
  editInline?: boolean | undefined;
  onEdit?: ((html: string) => void) | undefined;
  onClose: () => void;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);

  // The unreadable-file fallback is a Vietnamese sentence, so it is a <p> in
  // the text face rather than anything the mono face has to spell.
  const served = query.data ? (query.data.html ?? `<p>${fallback}</p>`) : "";
  const html = draft ?? served;
  const gaps = gapCount(html);

  return (
    <Modal
      title={title}
      onClose={onClose}
      footer={
        <>
          {editLabel && query.isSuccess ? (
            <button
              type="button"
              className={DIALOG_BUTTON}
              onClick={() => (editInline ? setEditing(true) : onEdit?.(html))}
            >
              <Pencil className="mr-1 inline size-3.5" />
              {editLabel}
            </button>
          ) : null}
          <button
            type="button"
            disabled={!query.isSuccess}
            className={`${DIALOG_BUTTON} disabled:opacity-40`}
            onClick={() => printPaper(html)}
          >
            <Printer className="mr-1 inline size-3.5" />
            Print
          </button>
          {downloadUrl ? (
            <a href={downloadUrl} className={DIALOG_BUTTON}>
              <Download className="mr-1 inline size-3.5" />
              Download
            </a>
          ) : null}
          <button type="button" className={DIALOG_BUTTON} onClick={onClose}>
            Close
          </button>
        </>
      }
    >
      <QueryState query={query} isEmpty={() => false} loadingRows={6}>
        {() => (
          <>
            {gaps ? (
              <p className="mb-3 flex items-center gap-1.5 rounded-lg border border-ember/30 bg-ember-soft px-3 py-2 text-xs text-ember">
                <AlertTriangle className="size-3.5 shrink-0" />
                <span>
                  {countLabel(gaps, "gap")} highlighted - fill the record, or type over them here.
                </span>
              </p>
            ) : null}

            {editing ? (
              <div
                contentEditable
                suppressContentEditableWarning
                onInput={(event) => setDraft(event.currentTarget.innerHTML)}
                dangerouslySetInnerHTML={{ __html: html }}
                className="aura-paper max-h-[55vh] min-h-[16rem] overflow-y-auto rounded-lg border border-border bg-card px-6 py-4 outline-none"
              />
            ) : (
              <div className="max-h-[55vh] min-h-[16rem] overflow-y-auto rounded-lg border border-border bg-secondary/50 p-3 sm:p-5">
                <article
                  className="aura-paper mx-auto max-w-[46rem] rounded-lg border border-border bg-card px-8 py-9 shadow-sm"
                  dangerouslySetInnerHTML={{ __html: html }}
                />
              </div>
            )}
          </>
        )}
      </QueryState>
    </Modal>
  );
}

// -- writing a template in the app --

type Mention = { node: Text; start: number; end: number; query: string };

/** The @-token being typed at the caret, if there is one. */
function caretMention(host: HTMLElement | null): Mention | null {
  const selection = window.getSelection();
  if (!host || !selection || !selection.isCollapsed) return null;
  const node = selection.anchorNode;
  if (!node || node.nodeType !== Node.TEXT_NODE || !host.contains(node)) return null;
  const offset = selection.anchorOffset;
  const before = (node.textContent ?? "").slice(0, offset);
  const match = /@([A-Za-z0-9_.]*)$/.exec(before);
  if (!match) return null;
  return {
    node: node as Text,
    start: offset - match[0].length,
    end: offset,
    query: match[1] ?? "",
  };
}

function TemplateEditorDialog({
  draft,
  fields,
  onClose,
  onSaved,
}: {
  draft: EditorDraft;
  fields: string[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [templateName, setTemplateName] = useState(draft.templateName);
  const [suggest, setSuggest] = useState<{ query: string; left: number; top: number } | null>(null);
  const [active, setActive] = useState(0);
  const body = useRef<HTMLDivElement>(null);
  const frame = useRef<HTMLDivElement>(null);

  // Uncontrolled on purpose: re-rendering the HTML under a live caret moves it.
  useEffect(() => {
    if (body.current) body.current.innerHTML = sourceToEditor(draft.source) || "<p><br></p>";
  }, [draft.source]);

  // set_value, not client.save: a partial doc through save would blank every
  // field it does not carry - the notes, the retired flag, the file.
  // The reading window is a cached read of the same template, so a save has to
  // drop it too or the founder reopens what they just rewrote.
  const written = [resultOf(LIBRARY), resultOf(PREVIEW_TEMPLATE)];

  const update = useMethodMutation<unknown, Record<string, unknown>>("frappe.client.set_value", {
    invalidate: written,
    onSuccess: onSaved,
  });
  const create = useMethodMutation<unknown, Record<string, unknown>>("frappe.client.insert", {
    invalidate: written,
    onSuccess: onSaved,
  });

  const saving = update.isPending || create.isPending;
  const failure = update.error ?? create.error;

  const matches = suggest
    ? fields
        .filter((field) => field.toLowerCase().includes(suggest.query.toLowerCase()))
        .slice(0, 8)
    : [];

  function refreshSuggestions() {
    const mention = caretMention(body.current);
    if (!mention) {
      setSuggest(null);
      return;
    }
    const range = document.createRange();
    range.setStart(mention.node, mention.start);
    range.setEnd(mention.node, mention.end);
    const caret = range.getBoundingClientRect();
    const box = frame.current?.getBoundingClientRect();
    setSuggest({
      query: mention.query,
      left: caret.left - (box?.left ?? 0),
      top: caret.bottom - (box?.top ?? 0) + 6,
    });
    setActive(0);
  }

  function insert(html: string) {
    const host = body.current;
    if (!host) return;
    host.focus();
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0 || !host.contains(selection.anchorNode)) {
      const end = document.createRange();
      end.selectNodeContents(host);
      end.collapse(false);
      selection?.removeAllRanges();
      selection?.addRange(end);
    }
    document.execCommand("insertHTML", false, html);
  }

  function pick(field: string) {
    const mention = caretMention(body.current);
    setSuggest(null);
    if (mention) {
      const range = document.createRange();
      range.setStart(mention.node, mention.start);
      range.setEnd(mention.node, mention.end);
      const selection = window.getSelection();
      selection?.removeAllRanges();
      selection?.addRange(range);
    }
    insert(`${chipHtml(field)}&nbsp;`);
  }

  function save() {
    const source = editorToSource(body.current?.innerHTML ?? "");
    const name = templateName.trim();
    if (!name || !source.trim()) return;
    if (draft.name) {
      update.mutate({
        doctype: "Paperwork Template",
        name: draft.name,
        fieldname: { template_name: name, template_source: source },
      });
    } else {
      create.mutate({
        doc: { doctype: "Paperwork Template", template_name: name, template_source: source },
      });
    }
  }

  return (
    <Modal
      title={draft.name ? "Edit template" : "Write a template"}
      onClose={onClose}
      footer={
        <>
          <button type="button" className={DIALOG_BUTTON} onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            disabled={saving || !templateName.trim()}
            onClick={save}
            className="rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90 disabled:opacity-40"
          >
            {saving ? "Saving..." : "Save template"}
          </button>
        </>
      }
    >
      <div className="space-y-3">
        <input
          value={templateName}
          onChange={(event) => setTemplateName(event.target.value)}
          placeholder="Template name - e.g. Hợp đồng cộng tác viên"
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm sm:w-96"
        />

        <div ref={frame} className="relative">
          <div className="flex flex-wrap items-center gap-1 rounded-t-lg border border-border bg-secondary/60 px-2 py-1.5">
            <ToolButton label="Bold" onPress={() => document.execCommand("bold")}>
              <Bold className="size-3.5" />
            </ToolButton>
            <ToolButton label="Italic" onPress={() => document.execCommand("italic")}>
              <Italic className="size-3.5" />
            </ToolButton>
            <ToolButton
              label="Bulleted list"
              onPress={() => document.execCommand("insertUnorderedList")}
            >
              <List className="size-3.5" />
            </ToolButton>
            <span className="mx-1 h-4 w-px bg-border" />
            <select
              defaultValue="p"
              onMouseDown={(event) => event.stopPropagation()}
              onChange={(event) => {
                document.execCommand("formatBlock", false, event.target.value);
                event.target.value = "p";
              }}
              className="rounded-md border border-border bg-background px-2 py-1 text-xs"
            >
              <option value="p">Body text</option>
              <option value="h1">Heading 1</option>
              <option value="h2">Heading 2</option>
              <option value="h3">Heading 3</option>
            </select>
          </div>

          <div
            ref={body}
            contentEditable
            suppressContentEditableWarning
            onInput={refreshSuggestions}
            onKeyUp={refreshSuggestions}
            onMouseUp={refreshSuggestions}
            onBlur={() => setSuggest(null)}
            onKeyDown={(event) => {
              if (!suggest || matches.length === 0) return;
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setActive((i) => (i + 1) % matches.length);
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setActive((i) => (i - 1 + matches.length) % matches.length);
              } else if (event.key === "Enter" || event.key === "Tab") {
                event.preventDefault();
                pick(matches[active] ?? matches[0] ?? "");
              } else if (event.key === "Escape") {
                event.preventDefault();
                event.stopPropagation();
                setSuggest(null);
              }
            }}
            className="aura-paper max-h-[45vh] min-h-[22rem] overflow-y-auto rounded-b-lg border border-t-0 border-border bg-card px-6 py-4 outline-none"
          />

          {suggest && matches.length ? (
            <div
              className="absolute z-[60] max-h-56 w-72 overflow-y-auto rounded-lg border border-border bg-card py-1 shadow-lg"
              style={{ left: `${suggest.left}px`, top: `${suggest.top}px` }}
            >
              {matches.map((field, index) => (
                <button
                  key={field}
                  type="button"
                  onMouseDown={(event) => {
                    event.preventDefault();
                    pick(field);
                  }}
                  className={`num block w-full truncate px-3 py-1.5 text-left text-xs ${
                    index === active ? "bg-ember-soft text-ember" : "hover:bg-secondary"
                  }`}
                >
                  {field}
                </button>
              ))}
            </div>
          ) : null}
        </div>

        <div>
          <p className="mb-1.5 text-xs text-muted-foreground">
            Type <code className="num rounded border border-border bg-secondary px-1">@</code> to
            insert a field, or click one:
          </p>
          <div className="flex max-h-24 flex-wrap gap-1 overflow-y-auto">
            {fields.map((field) => (
              <button
                key={field}
                type="button"
                onMouseDown={(event) => {
                  event.preventDefault();
                  insert(`${chipHtml(field)}&nbsp;`);
                }}
                className="num rounded border border-border bg-secondary px-1.5 py-0.5 text-[11px] text-muted-foreground hover:border-ember/40 hover:text-ember"
              >
                {field}
              </button>
            ))}
          </div>
        </div>

        {failure ? <ErrorState error={failure} className="px-0 py-2" /> : null}
      </div>
    </Modal>
  );
}

function ToolButton({
  label,
  onPress,
  children,
}: {
  label: string;
  onPress: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      onMouseDown={(event) => {
        event.preventDefault();
        onPress();
      }}
      className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
    >
      {children}
    </button>
  );
}

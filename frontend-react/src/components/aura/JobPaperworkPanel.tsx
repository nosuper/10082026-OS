// The job's paperwork: what has been printed off this job, and one door for
// making the next one. Replaces frontend/src/components/PaperworkPanel.vue.
//
// Every paper is read before it exists: Preview fills the template from the
// job and opens it in the reading window, and Generate lives inside that
// window. An untouched draft generates from the original file, so an uploaded
// Word template keeps its exact formatting; an edited draft is what the founder
// approved, so the edit wins.

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, FileText, X } from "lucide-react";

import {
  PaperStatusSelect,
  PaperStatusStamp,
  statusOf,
  useSetPaperStatus,
  type PaperStatusFields,
} from "@/components/aura/PaperStatus";
import { Card } from "@/components/aura/primitives";
import { ErrorState, Loading, QueryState } from "@/components/aura/states";
import { formatDateTime } from "@/lib/format";
import { resultOf, useList, useMethod, useMethodMutation } from "@/lib/queries";

// -- what the server sends --

type TemplateRow = {
  name: string;
  template_name: string | null;
  needs_vendor: boolean;
  needs_freelancer: boolean;
  unknown_placeholders: string[];
};

type PaperRow = Partial<PaperStatusFields> & {
  name: string;
  file_name: string | null;
  file_url: string | null;
  owner: string | null;
  creation: string | null;
  /** The registry row behind this file, where there is one. */
  paper?: string | null;
};

type Preview = { html: string; missing: string[]; unknown: string[] };

type Generated = {
  name: string;
  file_name: string | null;
  file_url: string | null;
  missing: string[];
  unknown: string[];
};

type PartiesPayload = { freelancers: { name: string; full_name: string | null }[] };

type ContactRow = { name: string; full_name: string | null };
type CompanyRow = { name: string; company_name: string | null };

/** The gap markers the server highlights are outside Tailwind's reach. */
const GAP_STYLE = `
.job-paper mark[data-gap] { background-color: var(--ember-soft); color: var(--ember);
  padding: 0 2px; border-radius: 2px; }
.job-paper h1, .job-paper h2, .job-paper h3 { font-weight: 600; margin: 0.8em 0 0.4em; }
.job-paper p, .job-paper li { margin: 0.4em 0; line-height: 1.6; }
.job-paper ul, .job-paper ol { padding-left: 1.2em; list-style: disc; }
.job-paper table { width: 100%; border-collapse: collapse; }
.job-paper td, .job-paper th { border: 1px solid var(--border); padding: 4px 6px; }
`;

export function JobPaperworkPanel({ job }: { job: string }) {
  const templates = useMethod<TemplateRow[]>("auraos.api.paperwork_templates");
  const documents = useMethod<PaperRow[]>("auraos.api.job_paperwork", { job });

  const [chosen, setChosen] = useState("");
  const [vendor, setVendor] = useState("");
  const [freelancer, setFreelancer] = useState("");
  const [generated, setGenerated] = useState<Generated | null>(null);
  const [draft, setDraft] = useState<Preview | null>(null);
  const [reading, setReading] = useState<{ title: string; html: string; url: string } | null>(null);

  useEffect(() => {
    const rows = templates.data;
    if (!chosen && rows && rows.length) setChosen(rows[0]?.name ?? "");
  }, [templates.data, chosen]);

  const template = (templates.data ?? []).find((row) => row.name === chosen);

  // The party lists are only fetched for templates that name one: most papers
  // are between us and the client, who is already on the job.
  const parties = useMethod<PartiesPayload>(
    "auraos.api.job_parties",
    { job },
    { enabled: Boolean(template?.needs_freelancer) },
  );
  const contacts = useList<ContactRow>(
    { doctype: "Party Contact", fields: ["name", "full_name"], orderBy: "full_name asc" },
    { enabled: Boolean(template?.needs_freelancer) },
  );
  const companies = useList<CompanyRow>(
    { doctype: "Party Company", fields: ["name", "company_name"], orderBy: "company_name asc" },
    { enabled: Boolean(template?.needs_vendor) },
  );

  const crew = parties.data?.freelancers ?? [];
  const onJob = new Set(crew.map((row) => row.name));
  const offJob = (contacts.data ?? []).filter((row) => !onJob.has(row.name));

  const previewer = useMethodMutation<Preview, Record<string, unknown>>(
    "auraos.api.preview_job_paperwork",
    { onSuccess: (result) => setDraft(result) },
  );

  const generator = useMethodMutation<Generated, Record<string, unknown>>(
    "auraos.api.generate_job_paperwork",
    {
      invalidate: [resultOf("auraos.api.job_paperwork")],
      onSuccess: (result) => {
        setDraft(null);
        setGenerated(result);
      },
    },
  );

  const draftSaver = useMethodMutation<Generated, Record<string, unknown>>(
    "auraos.api.save_job_paperwork_draft",
    {
      invalidate: [resultOf("auraos.api.job_paperwork")],
      onSuccess: (result) => {
        setDraft(null);
        setGenerated({ ...result, missing: [], unknown: [] });
      },
    },
  );

  const paperReader = useMethodMutation<{ html: string | null }, Record<string, unknown>>(
    "auraos.api.preview_paper",
  );

  // Sent out, come back signed, or back to Draft because it has to be redone.
  // The server records who moved it and when; nothing here is founder-only.
  const move = useSetPaperStatus();

  function openDocument(row: PaperRow) {
    paperReader.mutate(
      { file_url: row.file_url },
      {
        onSuccess: (result) =>
          setReading({
            title: row.file_name || "Paper",
            html: result.html || "<p>File này không phải văn bản .docx</p>",
            url: row.file_url ?? "",
          }),
      },
    );
  }

  const forParties = { vendor: vendor || null, freelancer: freelancer || null };
  const gaps = [...(generated?.missing ?? []), ...(generated?.unknown ?? [])];
  const failure =
    previewer.error ??
    generator.error ??
    draftSaver.error ??
    paperReader.error ??
    move.error ??
    templates.error;

  return (
    <Card title="Paperwork" subtitle="Filled from this job and printed for wet-ink signature.">
      <style>{GAP_STYLE}</style>

      <QueryState
        query={templates}
        empty={{
          title: "No templates in the library yet.",
          detail: "Upload one on the Paperwork screen to generate papers from it.",
          icon: <FileText className="size-6" strokeWidth={1.5} />,
        }}
      >
        {() => (
          <div className="space-y-3 border-b border-border px-4 py-3">
            <div className="flex flex-wrap items-end gap-3">
              <label className="block">
                <span className="label-caps">Template</span>
                <select
                  value={chosen}
                  onChange={(event) => setChosen(event.target.value)}
                  className="mt-1 block w-64 rounded-lg border border-border bg-background px-2 py-1.5 text-sm outline-none focus:border-border-strong"
                >
                  {(templates.data ?? []).map((row) => (
                    <option key={row.name} value={row.name}>
                      {row.template_name || row.name}
                    </option>
                  ))}
                </select>
              </label>

              {/* Only the parties this paper actually mentions are asked for. */}
              {template?.needs_freelancer ? (
                <label className="block">
                  <span className="label-caps">Freelancer</span>
                  <select
                    value={freelancer}
                    onChange={(event) => setFreelancer(event.target.value)}
                    className="mt-1 block w-52 rounded-lg border border-border bg-background px-2 py-1.5 text-sm outline-none focus:border-border-strong"
                  >
                    <option value="">- pick a person -</option>
                    {crew.length ? (
                      <optgroup label="On this job">
                        {crew.map((row) => (
                          <option key={row.name} value={row.name}>
                            {row.full_name || row.name}
                          </option>
                        ))}
                      </optgroup>
                    ) : null}
                    <optgroup label={crew.length ? "Everyone" : "Contacts"}>
                      {offJob.map((row) => (
                        <option key={row.name} value={row.name}>
                          {row.full_name || row.name}
                        </option>
                      ))}
                    </optgroup>
                  </select>
                </label>
              ) : null}

              {template?.needs_vendor ? (
                <label className="block">
                  <span className="label-caps">Vendor</span>
                  <select
                    value={vendor}
                    onChange={(event) => setVendor(event.target.value)}
                    className="mt-1 block w-52 rounded-lg border border-border bg-background px-2 py-1.5 text-sm outline-none focus:border-border-strong"
                  >
                    <option value="">- pick a company -</option>
                    {(companies.data ?? []).map((row) => (
                      <option key={row.name} value={row.name}>
                        {row.company_name || row.name}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}

              <button
                type="button"
                disabled={!chosen || previewer.isPending}
                onClick={() => previewer.mutate({ job, template: chosen, ...forParties })}
                className="rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90 disabled:opacity-40"
              >
                {previewer.isPending ? "Filling..." : "Preview"}
              </button>
            </div>

            {template?.unknown_placeholders?.length ? (
              <p className="flex items-start gap-1.5 text-xs text-ember">
                <AlertTriangle className="mt-0.5 size-3 shrink-0" />
                <span>
                  This template asks for {template.unknown_placeholders.join(", ")} - no such
                  placeholder exists, so it will print as a gap marker. Fix the docx in the library.
                </span>
              </p>
            ) : null}

            {/* The whole point of the paperwork ticket: what did not get
                filled, said out loud, beside the document it is missing from. */}
            {generated ? (
              <div
                className={`rounded-xl border p-3 text-sm ${
                  gaps.length ? "border-ember/30 bg-ember-soft/60" : "border-border bg-secondary/50"
                }`}
              >
                <button
                  type="button"
                  onClick={() =>
                    openDocument({
                      name: generated.name,
                      file_name: generated.file_name,
                      file_url: generated.file_url,
                      owner: null,
                      creation: null,
                    })
                  }
                  className="text-left font-medium text-ember hover:underline"
                >
                  {generated.file_name}
                </button>
                {gaps.length === 0 ? (
                  <p className="mt-1 text-xs text-positive">
                    Every placeholder filled - ready to print.
                  </p>
                ) : (
                  <>
                    <p className="mt-1 text-xs text-ember">
                      Printed with {gaps.length === 1 ? "one gap" : `${gaps.length} gaps`} marked on
                      the page - fill these in and generate again:
                    </p>
                    <ul className="mt-1 space-y-0.5 text-xs text-ember">
                      {generated.missing.map((name) => (
                        <li key={`missing-${name}`}>
                          <span className="num">{name}</span> - no data on the record
                        </li>
                      ))}
                      {generated.unknown.map((name) => (
                        <li key={`unknown-${name}`}>
                          <span className="num">{name}</span> - not a placeholder this system has
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            ) : null}
          </div>
        )}
      </QueryState>

      <QueryState query={documents} empty={{ title: "No paper on this job yet." }} loadingRows={2}>
        {(rows) => (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-border">
                <tr>
                  <th className="label-caps px-4 py-2 text-left font-normal">
                    Document on this job
                  </th>
                  <th className="label-caps px-2 py-2 text-left font-normal">Added</th>
                  <th className="label-caps px-4 py-2 text-left font-normal">By</th>
                  <th className="label-caps px-2 py-2 text-left font-normal">Signing</th>
                  <th className="label-caps px-4 py-2 text-left font-normal">Last change</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {rows.map((row) => (
                  <tr key={row.name}>
                    <td className="px-4 py-2">
                      <button
                        type="button"
                        onClick={() => openDocument(row)}
                        className="text-left text-sm font-medium text-ember hover:underline"
                      >
                        {row.file_name}
                      </button>
                    </td>
                    <td className="num px-2 py-2 text-xs whitespace-nowrap text-muted-foreground">
                      {formatDateTime(row.creation)}
                    </td>
                    <td className="px-4 py-2 text-xs whitespace-nowrap text-muted-foreground">
                      {row.owner}
                    </td>
                    {/* A file that reached this job some other way has no
                        registry row, so there is nothing to move. */}
                    <td className="px-2 py-2">
                      {row.paper ? (
                        <PaperStatusSelect
                          status={statusOf({ status: row.status ?? null })}
                          disabled={move.isPending}
                          onChange={(status) => move.mutate({ paper: row.paper as string, status })}
                        />
                      ) : (
                        <span className="text-xs text-muted-foreground">-</span>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      {row.paper ? (
                        <PaperStatusStamp
                          by={row.status_changed_by ?? null}
                          byLabel={row.status_changed_by_label ?? null}
                          on={row.status_changed_on ?? null}
                        />
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </QueryState>

      {paperReader.isPending ? <Loading rows={1} label="Opening the paper" /> : null}
      {failure ? <ErrorState error={failure} className="border-t border-border py-4" /> : null}

      {draft ? (
        <PaperWindow
          title={`Draft - ${template?.template_name || "paper"}`}
          html={draft.html}
          saveLabel="Generate .docx"
          saving={generator.isPending || draftSaver.isPending}
          onSave={(html, edited) => {
            if (edited) draftSaver.mutate({ job, template: chosen, html, ...forParties });
            else generator.mutate({ job, template: chosen, ...forParties });
          }}
          onClose={() => setDraft(null)}
        />
      ) : null}

      {reading ? (
        <PaperWindow
          title={reading.title}
          html={reading.html}
          downloadUrl={reading.url}
          onClose={() => setReading(null)}
        />
      ) : null}
    </Card>
  );
}

/**
 * One window for every paper-shaped thing: a filled draft, a generated
 * document. It opens reading, edits on request, prints what is on screen, and
 * downloads the stored file when there is one.
 */
function PaperWindow({
  title,
  html,
  downloadUrl,
  saveLabel,
  saving,
  onSave,
  onClose,
}: {
  title: string;
  html: string;
  downloadUrl?: string | undefined;
  saveLabel?: string | undefined;
  saving?: boolean | undefined;
  onSave?: ((html: string, edited: boolean) => void) | undefined;
  onClose: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const paper = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  function current(): string {
    return paper.current?.innerHTML ?? html;
  }

  const gapCount = (html.match(/data-gap/g) ?? []).length;

  function print() {
    const sheet = window.open("", "_blank");
    if (!sheet) return;
    sheet.document.write(
      `<!doctype html><html><head><meta charset="utf-8"><title>${title}</title><style>
        body { font-family: "Times New Roman", serif; font-size: 13pt; line-height: 1.6;
               max-width: 17cm; margin: 1cm auto; }
        mark[data-gap] { background: #fde68a; }
        h1, h2, h3 { line-height: 1.3; }
      </style></head><body>${current()}</body></html>`,
    );
    sheet.document.close();
    sheet.focus();
    sheet.print();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 sm:p-8">
      <button aria-label="Close" onClick={onClose} className="fixed inset-0 bg-primary/25" />
      <div className="relative z-10 w-full max-w-4xl rounded-xl border border-border bg-card shadow-lg">
        <header className="flex items-start gap-3 border-b border-border px-5 py-4">
          <h2 className="min-w-0 flex-1 truncate font-display text-base font-semibold">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary"
          >
            <X className="size-4" />
          </button>
        </header>

        <div className="px-5 py-4">
          {gapCount ? (
            <p className="mb-3 flex items-center gap-1.5 rounded-lg border border-ember/30 bg-ember-soft px-3 py-2 text-xs text-ember">
              <AlertTriangle className="size-3.5 shrink-0" />
              <span>
                {gapCount === 1 ? "One gap" : `${gapCount} gaps`} highlighted - fill the record, or
                type over them here.
              </span>
            </p>
          ) : null}

          <div className="max-h-[55vh] min-h-64 overflow-y-auto rounded-xl border border-border bg-background p-3 sm:p-5">
            <article
              ref={paper}
              contentEditable={editing}
              suppressContentEditableWarning
              className={`job-paper mx-auto max-w-[46rem] rounded-lg border bg-card px-8 py-9 text-sm ${
                editing ? "border-ember outline-none" : "border-border"
              }`}
              dangerouslySetInnerHTML={{ __html: html }}
            />
          </div>
        </div>

        <footer className="flex flex-wrap items-center justify-end gap-2 border-t border-border px-5 py-4">
          {!editing && onSave ? (
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-secondary"
            >
              Edit
            </button>
          ) : null}
          <button
            type="button"
            onClick={print}
            className="rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-secondary"
          >
            Print
          </button>
          {downloadUrl ? (
            <a
              href={downloadUrl}
              download
              className="rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-secondary"
            >
              Download
            </a>
          ) : null}
          {onSave && saveLabel ? (
            <button
              type="button"
              disabled={saving}
              onClick={() => onSave(current(), current() !== html)}
              className="rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90 disabled:opacity-40"
            >
              {saving ? "Generating..." : saveLabel}
            </button>
          ) : null}
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-secondary"
          >
            Close
          </button>
        </footer>
      </div>
    </div>
  );
}

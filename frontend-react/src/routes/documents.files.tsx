// Every attachment across every deal, with the deal each one hangs on
// (#28 / T3.4, ported to React at #162's request).
//
// One read, `auraos.api.deal_files(deal, file_type, uploader)`. It answers the
// filtered rows **and the choices the filters offer**, both built from the same
// unfiltered set — so narrowing to one deal never empties the dropdown that got
// you there, which is the way a filter bar usually breaks.
//
// **The question this screen exists for is the one a deal card cannot answer:**
// "we have that brief somewhere, which deal was it on?" So the deal is a column
// rather than a heading, and the list is flat rather than grouped.
//
// **Scoped by the server to the deals this session may list.** `deal_files`
// reads with `get_all`, which skips row-level permissions, so it filters
// against `frappe.get_list("Deal")` first. Nothing here re-checks that, and
// nothing here could: the browser is handed rows it is allowed to see.
//
// **A pasted screenshot is here too.** It is an ordinary deal attachment — that
// is what makes it readable by exactly the seats that may read the deal — so it
// appears in this list like any other file rather than hiding inside a comment.
//
// Renaming and removing are gated on **write on the deal**, not on who
// uploaded. Unlike a comment, a file is shared material rather than authored
// speech: a badly named brief is everyone's problem.

import { createFileRoute } from "@tanstack/react-router";
import { Check, FolderOpen, Pencil, Trash2, X } from "lucide-react";
import { useState } from "react";

import { AppShell } from "@/components/aura/AppShell";
import { DocumentsTabs } from "@/components/aura/DocumentsTabs";
import { Card, Pill, Td, Th, inputClass } from "@/components/aura/primitives";
import { ErrorState, QueryState } from "@/components/aura/states";
import { countLabel, formatDateTime } from "@/lib/format";
import { resultOf, useMethod, useMethodMutation } from "@/lib/queries";
import { cn } from "@/lib/utils";

/** Pinned by auraos/auraos/doctype/deal/test_deal_collab.py. */
type FileRow = {
  name: string;
  file_name: string | null;
  file_url: string | null;
  file_size: number | null;
  file_type: string | null;
  is_private: 0 | 1;
  owner: string | null;
  creation: string | null;
  /** The deal it hangs on - `attached_to_name`, renamed on the way out. */
  deal: string;
  deal_title: string | null;
};

type FilesPayload = {
  files: FileRow[];
  deals: { name: string; title: string }[];
  file_types: string[];
  uploaders: { name: string; full_name: string }[];
};

const FILES = resultOf("auraos.api.deal_files");

/** Bytes as a person reads them. Nothing depends on the exact rounding. */
function fileSize(bytes: number | null): string {
  if (!bytes) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export const Route = createFileRoute("/documents/files")({
  head: () => ({
    meta: [
      { title: "Files - every attachment, and the deal it is on | AuraOS" },
      {
        name: "description",
        content:
          "Every file attached to a deal, filterable by deal, type and who uploaded it. Where a brief is found when nobody remembers which deal it was on.",
      },
      { property: "og:title", content: "Files - AuraOS" },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: FilesPage,
});

function FilesPage() {
  const [deal, setDeal] = useState("");
  const [fileType, setFileType] = useState("");
  const [uploader, setUploader] = useState("");
  const [renaming, setRenaming] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [confirming, setConfirming] = useState<string | null>(null);

  const files = useMethod<FilesPayload>("auraos.api.deal_files", {
    deal: deal || undefined,
    file_type: fileType || undefined,
    uploader: uploader || undefined,
  });

  const rename = useMethodMutation<FileRow, Record<string, unknown>>(
    "auraos.api.rename_deal_file",
    { invalidate: [FILES], onSuccess: () => setRenaming(null) },
  );
  const drop = useMethodMutation<unknown, Record<string, unknown>>("auraos.api.delete_deal_file", {
    invalidate: [FILES],
    onSuccess: () => setConfirming(null),
  });

  const data = files.data;
  const rows = data?.files ?? [];
  const filtered = Boolean(deal || fileType || uploader);
  const error = rename.error || drop.error;

  return (
    <AppShell
      title="Files"
      meta="Every attachment, and the deal it is on"
      actions={files.isSuccess ? <Pill tone="ink">{countLabel(rows.length, "file")}</Pill> : null}
    >
      <div className="space-y-5">
        <DocumentsTabs />

        {/* The choices come from the unfiltered set, so narrowing by deal
            never empties the type dropdown that got you here. */}
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border bg-card p-3">
          <select
            aria-label="Filter by deal"
            value={deal}
            onChange={(event) => setDeal(event.target.value)}
            className={cn(inputClass, "w-auto min-w-44")}
          >
            <option value="">Every deal</option>
            {(data?.deals ?? []).map((one) => (
              <option key={one.name} value={one.name}>
                {one.title}
              </option>
            ))}
          </select>
          <select
            aria-label="Filter by file type"
            value={fileType}
            onChange={(event) => setFileType(event.target.value)}
            className={cn(inputClass, "w-auto min-w-32")}
          >
            <option value="">Every type</option>
            {(data?.file_types ?? []).map((one) => (
              <option key={one} value={one}>
                {one}
              </option>
            ))}
          </select>
          <select
            aria-label="Filter by uploader"
            value={uploader}
            onChange={(event) => setUploader(event.target.value)}
            className={cn(inputClass, "w-auto min-w-40")}
          >
            <option value="">Anyone</option>
            {(data?.uploaders ?? []).map((one) => (
              <option key={one.name} value={one.name}>
                {one.full_name}
              </option>
            ))}
          </select>
          {filtered ? (
            <button
              type="button"
              onClick={() => {
                setDeal("");
                setFileType("");
                setUploader("");
              }}
              className="rounded-lg border border-border px-2.5 py-1.5 text-xs hover:bg-secondary"
            >
              Clear
            </button>
          ) : null}
        </div>

        {error ? <ErrorState error={error} /> : null}

        <Card>
          <QueryState
            query={files}
            loadingRows={5}
            isEmpty={() => rows.length === 0}
            empty={{
              title: filtered ? "Nothing matches those filters." : "No files on any deal yet.",
              detail: filtered
                ? "Clear a filter and look again."
                : "A file lands here when somebody attaches it to a deal - including a screenshot pasted into a comment, which is an attachment like any other.",
              icon: <FolderOpen className="size-6" strokeWidth={1.5} />,
            }}
          >
            {() => (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[52rem]">
                  <thead className="border-b border-border">
                    <tr>
                      <Th className="w-full">File</Th>
                      <Th>Deal</Th>
                      <Th>Uploaded by</Th>
                      <Th>When</Th>
                      <Th className="text-right">Size</Th>
                      <Th />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {rows.map((row) => (
                      <tr key={row.name} className="hover:bg-secondary/40">
                        <Td>
                          {renaming === row.name ? (
                            <div className="flex items-center gap-1.5">
                              <input
                                value={newName}
                                autoFocus
                                aria-label={`Rename ${row.file_name ?? row.name}`}
                                onChange={(event) => setNewName(event.target.value)}
                                onKeyDown={(event) => {
                                  if (event.key === "Enter" && newName.trim()) {
                                    rename.mutate({ file: row.name, file_name: newName.trim() });
                                  }
                                  if (event.key === "Escape") setRenaming(null);
                                }}
                                className={inputClass}
                              />
                              <button
                                type="button"
                                aria-label="Save name"
                                disabled={!newName.trim() || rename.isPending}
                                onClick={() =>
                                  rename.mutate({ file: row.name, file_name: newName.trim() })
                                }
                                className="rounded-md border border-border p-1 disabled:opacity-50"
                              >
                                <Check className="size-3" strokeWidth={2} />
                              </button>
                              <button
                                type="button"
                                aria-label="Cancel rename"
                                onClick={() => setRenaming(null)}
                                className="rounded-md border border-border p-1"
                              >
                                <X className="size-3" strokeWidth={2} />
                              </button>
                            </div>
                          ) : (
                            <a
                              href={row.file_url ?? "#"}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sm font-medium underline underline-offset-2 hover:text-ember"
                            >
                              {row.file_name || row.name}
                            </a>
                          )}
                          <div className="mt-0.5 flex flex-wrap items-center gap-1.5">
                            {row.file_type ? (
                              <span className="label-caps">{row.file_type}</span>
                            ) : null}
                            {/* Said out loud, because it is the whole reason a
                                pasted screenshot is safe to keep here. */}
                            {row.is_private ? <Pill tone="outline">private</Pill> : null}
                          </div>
                        </Td>
                        <Td className="text-xs">{row.deal_title || row.deal}</Td>
                        <Td className="text-xs text-muted-foreground">{row.owner}</Td>
                        <Td className="num text-xs whitespace-nowrap text-muted-foreground">
                          {formatDateTime(row.creation)}
                        </Td>
                        <Td className="num text-right text-xs text-muted-foreground">
                          {fileSize(row.file_size)}
                        </Td>
                        <Td className="whitespace-nowrap text-right">
                          {confirming === row.name ? (
                            <span className="inline-flex items-center gap-1.5">
                              <span className="text-xs">Delete?</span>
                              <button
                                type="button"
                                disabled={drop.isPending}
                                onClick={() => drop.mutate({ file: row.name })}
                                className="rounded-lg bg-ember px-2 py-1 text-xs font-medium text-white disabled:opacity-50"
                              >
                                Yes
                              </button>
                              <button
                                type="button"
                                onClick={() => setConfirming(null)}
                                className="rounded-lg border border-border px-2 py-1 text-xs"
                              >
                                No
                              </button>
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1">
                              <button
                                type="button"
                                aria-label={`Rename ${row.file_name ?? row.name}`}
                                onClick={() => {
                                  setRenaming(row.name);
                                  setNewName(row.file_name ?? "");
                                  setConfirming(null);
                                }}
                                className="rounded-md border border-border p-1 text-muted-foreground hover:bg-secondary hover:text-foreground"
                              >
                                <Pencil className="size-3" strokeWidth={1.75} />
                              </button>
                              <button
                                type="button"
                                aria-label={`Delete ${row.file_name ?? row.name}`}
                                onClick={() => setConfirming(row.name)}
                                className="rounded-md border border-border p-1 text-muted-foreground hover:bg-secondary hover:text-ember"
                              >
                                <Trash2 className="size-3" strokeWidth={1.75} />
                              </button>
                            </span>
                          )}
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </QueryState>
        </Card>
      </div>
    </AppShell>
  );
}

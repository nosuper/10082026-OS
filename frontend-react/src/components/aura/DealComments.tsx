// The comment thread on a deal: mentions, editing, deleting, pasted pictures
// (#28 / T3.4, ported to React at #162's request).
//
// **No second editor.** `RichText` already owns the one rich-text surface this
// app has, and its own docblock declines TipTap for a reason that applies here
// twice over: the mention picker below is built on the caret of that editor
// rather than on a framework's suggestion plugin, so there is still one editor
// to keep in step. `RichText` gained a `bodyRef` and three event hooks for
// this; nothing else about it moved.
//
// **The mention markup is a contract with the server, not a styling choice.**
// `auraos.lib.comments.mentioned_users` reads `data-id` out of a
// `<span class="mention">`, so that is exactly what gets inserted. Checked
// against the running site rather than assumed: `sanitize_html` keeps the
// span, its class and its data attributes intact, so a mention survives being
// stored and reads as a mention when the thread is loaded again - not only at
// the moment it was typed.
//
// **A pasted picture is an ordinary deal attachment.** It uploads private and
// attached to the deal, which is what makes it readable by exactly the seats
// that may read the deal and by nobody else. The file manager lists it beside
// every other attachment, because it is one.
//
// **Whose comment it is comes from the server.** `mine` is decided by
// `_comment_row`, and it is the same answer that gates the edit and delete
// endpoints - a thread offering a button the server will refuse is worse than
// a thread with no button.

import { useEffect, useRef, useState } from "react";
import { Image as ImageIcon, Pencil, Send, Trash2, X } from "lucide-react";

import { RichText } from "@/components/aura/RichText";
import { Pill } from "@/components/aura/primitives";
import { useSession } from "@/components/aura/SessionProvider";
import { ErrorState, QueryState } from "@/components/aura/states";
import { formatDateTime } from "@/lib/format";
import { errorMessage, uploadFile } from "@/lib/frappe";
import { resultOf, useMethod, useMethodMutation } from "@/lib/queries";
import { cn } from "@/lib/utils";

/** One row of auraos.api.deal_comments. Pinned by test_deal_collab.py. */
export type CommentRow = {
  name: string;
  content: string | null;
  comment_by: string | null;
  comment_email: string | null;
  creation: string | null;
  modified: string | null;
  /** Decided by the server, and the same answer that gates edit and delete. */
  mine: boolean;
  /** Written and modified came from one clock read, so a later stamp is a rewrite. */
  edited: boolean;
};

type Seat = { name: string; full_name: string | null };

const THREAD = resultOf("auraos.api.deal_comments");

/**
 * An empty editor still sends `<p><br></p>`, and a comment that is nothing but
 * a pasted picture has no text at all. The same rule the server holds in
 * `auraos.lib.comments.is_blank`, so the button and the endpoint agree about
 * what counts as saying something.
 */
function isBlank(html: string): boolean {
  if (/<img\b/i.test(html)) return false;
  return !html
    .replace(/<[^>]*>/g, " ")
    .replace(/&nbsp;|\u00a0/g, " ")
    .trim();
}

/** The mention span the server reads. Escaped, because a name is user input. */
function mentionHtml(seat: Seat): string {
  const label = (seat.full_name || seat.name).replace(
    /[<>&"]/g,
    (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;" })[c] as string,
  );
  const id = seat.name.replace(/"/g, "&quot;");
  return `<span class="mention" data-type="mention" data-id="${id}" data-label="${label}">@${label}</span>&nbsp;`;
}

export function DealComments({ deal }: { deal: string }) {
  const session = useSession();
  const thread = useMethod<CommentRow[]>("auraos.api.deal_comments", { deal });
  // Naming yourself notifies nobody, so the server does not offer you.
  const seats = useMethod<Seat[]>("auraos.api.operating_users");

  const [draft, setDraft] = useState("");
  // Remounts the composer after a post: clearing the string alone leaves the
  // editor's own undo history, and an undo back to the sent comment.
  const [composerKey, setComposerKey] = useState(0);
  const [editing, setEditing] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState("");
  const [confirming, setConfirming] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const invalidate = [
    THREAD,
    resultOf("auraos.api.deal_attachments"),
    resultOf("auraos.api.deal_files"),
  ];
  const post = useMethodMutation<CommentRow, Record<string, unknown>>(
    "auraos.api.add_deal_comment",
    {
      invalidate,
      onSuccess: () => {
        setDraft("");
        setComposerKey((key) => key + 1);
      },
    },
  );
  const edit = useMethodMutation<CommentRow, Record<string, unknown>>(
    "auraos.api.edit_deal_comment",
    { invalidate, onSuccess: () => setEditing(null) },
  );
  const drop = useMethodMutation<unknown, Record<string, unknown>>(
    "auraos.api.delete_deal_comment",
    { invalidate, onSuccess: () => setConfirming(null) },
  );

  const mentionable = (seats.data ?? []).filter((seat) => seat.name !== session.userId);
  const error = post.error || edit.error || drop.error;

  return (
    <div className="space-y-3">
      <QueryState
        query={thread}
        loadingRows={2}
        isEmpty={() => (thread.data ?? []).length === 0}
        empty={{
          title: "No comments yet.",
          detail: "Say what happened on the call, or name someone to pull them in.",
        }}
      >
        {(rows) => (
          // Named, so a test can look at the thread rather than at the page:
          // the composer holds a copy of whatever was just typed, and a
          // page-wide text assertion is satisfied by that copy whether the
          // comment posted or not.
          <ul aria-label="Comment thread" className="space-y-3">
            {rows.map((row) => (
              <li key={row.name} className="rounded-xl border border-border bg-card p-3">
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="text-sm font-medium">
                    {row.comment_by || row.comment_email || "Someone"}
                  </span>
                  <span className="label-caps">{formatDateTime(row.creation)}</span>
                  {row.edited ? <Pill tone="outline">edited</Pill> : null}
                  {row.mine ? (
                    <span className="ml-auto flex items-center gap-1">
                      <button
                        type="button"
                        aria-label="Edit comment"
                        onClick={() => {
                          setEditing(row.name);
                          setEditDraft(row.content ?? "");
                          setConfirming(null);
                        }}
                        className="rounded-md border border-border p-1 text-muted-foreground hover:bg-secondary hover:text-foreground"
                      >
                        <Pencil className="size-3" strokeWidth={1.75} />
                      </button>
                      <button
                        type="button"
                        aria-label="Delete comment"
                        onClick={() => setConfirming(row.name)}
                        className="rounded-md border border-border p-1 text-muted-foreground hover:bg-secondary hover:text-ember"
                      >
                        <Trash2 className="size-3" strokeWidth={1.75} />
                      </button>
                    </span>
                  ) : null}
                </div>

                {editing === row.name ? (
                  <div className="mt-2 space-y-2">
                    <Composer
                      key={`edit-${row.name}`}
                      value={editDraft}
                      onChange={setEditDraft}
                      seats={mentionable}
                      deal={deal}
                      onUploadError={setUploadError}
                      ariaLabel="Edit comment"
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={isBlank(editDraft) || edit.isPending}
                        onClick={() => edit.mutate({ comment: row.name, content: editDraft })}
                        className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground disabled:opacity-50"
                      >
                        {edit.isPending ? "Saving..." : "Save"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditing(null)}
                        className="rounded-lg border border-border px-3 py-1.5 text-xs"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  // The stored HTML, which the server sanitised on the way in -
                  // twice, in fact: `_clean_comment` and Frappe's own save.
                  <div
                    className="aura-rich mt-1.5 text-sm"
                    dangerouslySetInnerHTML={{ __html: row.content ?? "" }}
                  />
                )}

                {confirming === row.name ? (
                  <div className="mt-2 flex flex-wrap items-center gap-2 rounded-lg border border-ember bg-ember-soft px-3 py-2">
                    <span className="text-xs">Delete this comment? It does not come back.</span>
                    <button
                      type="button"
                      disabled={drop.isPending}
                      onClick={() => drop.mutate({ comment: row.name })}
                      className="rounded-lg bg-ember px-2.5 py-1 text-xs font-medium text-white disabled:opacity-50"
                    >
                      {drop.isPending ? "Deleting..." : "Delete"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setConfirming(null)}
                      className="rounded-lg border border-border px-2.5 py-1 text-xs"
                    >
                      Keep
                    </button>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </QueryState>

      <div className="space-y-2">
        <Composer
          key={`new-${composerKey}`}
          value={draft}
          onChange={setDraft}
          seats={mentionable}
          deal={deal}
          onUploadError={setUploadError}
          ariaLabel="New comment"
          placeholder="Type @ to name someone. Paste a screenshot straight in."
        />
        <button
          type="button"
          disabled={isBlank(draft) || post.isPending}
          onClick={() => post.mutate({ deal, content: draft })}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
        >
          <Send className="size-3.5" strokeWidth={1.75} />
          {post.isPending ? "Posting..." : "Comment"}
        </button>
      </div>

      {uploadError ? <ErrorState error={new Error(uploadError)} /> : null}
      {error ? <ErrorState error={error} /> : null}
    </div>
  );
}

/**
 * The editor, plus the two things a comment can do that a brief cannot: name
 * somebody, and carry a pasted picture.
 *
 * The mention picker watches the caret rather than the text. A query is only
 * live while the caret sits at the end of an unbroken `@word` - so an email
 * address typed mid-sentence does not open a menu, and moving away closes it
 * without needing an explicit dismiss.
 */
function Composer({
  value,
  onChange,
  seats,
  deal,
  onUploadError,
  ariaLabel,
  placeholder,
}: {
  value: string;
  onChange: (html: string) => void;
  seats: Seat[];
  deal: string;
  onUploadError: (message: string | null) => void;
  ariaLabel: string;
  placeholder?: string;
}) {
  const body = useRef<HTMLDivElement | null>(null);
  const [query, setQuery] = useState<string | null>(null);
  const [highlight, setHighlight] = useState(0);
  const [uploading, setUploading] = useState(false);

  const matches =
    query === null
      ? []
      : seats
          .filter((seat) =>
            `${seat.full_name ?? ""} ${seat.name}`.toLowerCase().includes(query.toLowerCase()),
          )
          .slice(0, 6);

  useEffect(() => setHighlight(0), [query]);

  /** The `@word` the caret is sitting at the end of, or null. */
  function queryAtCaret(): string | null {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0 || !selection.isCollapsed) return null;
    const node = selection.anchorNode;
    if (!node || node.nodeType !== Node.TEXT_NODE) return null;
    const before = (node.textContent ?? "").slice(0, selection.anchorOffset);
    const match = /(?:^|\s)@([^\s@]*)$/.exec(before);
    return match ? (match[1] ?? "") : null;
  }

  /** Replace the `@word` under the caret with a mention span. */
  function insertMention(seat: Seat) {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;
    const node = selection.anchorNode;
    if (!node || node.nodeType !== Node.TEXT_NODE) return;
    const before = (node.textContent ?? "").slice(0, selection.anchorOffset);
    const match = /(?:^|\s)@([^\s@]*)$/.exec(before);
    if (!match) return;

    const range = document.createRange();
    range.setStart(node, selection.anchorOffset - (match[1] ?? "").length - 1);
    range.setEnd(node, selection.anchorOffset);
    range.deleteContents();

    const fragment = range.createContextualFragment(mentionHtml(seat));
    range.insertNode(fragment);
    // Caret after what was just inserted, so typing carries on normally.
    selection.collapseToEnd();
    setQuery(null);
    if (body.current) onChange(body.current.innerHTML);
  }

  /** A pasted picture becomes a private attachment on this deal. */
  async function onPaste(event: React.ClipboardEvent<HTMLDivElement>) {
    const file = Array.from(event.clipboardData.files).find((one) => one.type.startsWith("image/"));
    if (!file) return;
    // Kept out of the DOM: the browser would otherwise drop in a base64 blob
    // that no attachment list can see and no permission gates.
    event.preventDefault();
    setUploading(true);
    onUploadError(null);
    try {
      const uploaded = await uploadFile(file, {
        isPrivate: true,
        doctype: "Deal",
        docname: deal,
      });
      const selection = window.getSelection();
      const html = `<img src="${uploaded.file_url}" alt="${file.name.replace(/"/g, "")}" />`;
      if (selection && selection.rangeCount > 0) {
        const range = selection.getRangeAt(0);
        range.deleteContents();
        range.insertNode(range.createContextualFragment(html));
        selection.collapseToEnd();
      } else if (body.current) {
        body.current.insertAdjacentHTML("beforeend", html);
      }
      if (body.current) onChange(body.current.innerHTML);
    } catch (failure) {
      onUploadError(errorMessage(failure));
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="relative">
      <RichText
        defaultValue={value}
        onChange={onChange}
        ariaLabel={ariaLabel}
        {...(placeholder ? { placeholder } : {})}
        className="min-h-[5rem]"
        bodyRef={(node) => {
          body.current = node;
        }}
        extras={
          uploading ? (
            <span className="label-caps flex items-center gap-1 px-2">
              <ImageIcon className="size-3" strokeWidth={1.75} />
              uploading
            </span>
          ) : null
        }
        onKeyDown={(event) => {
          if (query === null || matches.length === 0) return;
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setHighlight((at) => (at + 1) % matches.length);
          } else if (event.key === "ArrowUp") {
            event.preventDefault();
            setHighlight((at) => (at - 1 + matches.length) % matches.length);
          } else if (event.key === "Enter" || event.key === "Tab") {
            event.preventDefault();
            const seat = matches[highlight];
            if (seat) insertMention(seat);
          } else if (event.key === "Escape") {
            event.preventDefault();
            setQuery(null);
          }
        }}
        onKeyUp={(event) => {
          // Not on the keys the menu itself handles, or moving through it
          // would rewrite the query from under the highlight.
          if (["ArrowDown", "ArrowUp", "Enter", "Tab", "Escape"].includes(event.key)) return;
          setQuery(queryAtCaret());
        }}
        onPaste={(event) => void onPaste(event)}
      />

      {query !== null && matches.length > 0 ? (
        <ul
          role="listbox"
          aria-label="Mention someone"
          className="absolute right-2 bottom-2 z-20 w-56 overflow-hidden rounded-lg border border-border-strong bg-card shadow-lg"
        >
          {matches.map((seat, index) => (
            <li key={seat.name}>
              <button
                type="button"
                role="option"
                aria-selected={index === highlight}
                // mousedown, not click: click fires after the editor has lost
                // the caret, and the caret is what says where the span goes.
                onMouseDown={(event) => {
                  event.preventDefault();
                  insertMention(seat);
                }}
                onMouseEnter={() => setHighlight(index)}
                className={cn(
                  "block w-full px-3 py-1.5 text-left text-sm",
                  index === highlight ? "bg-secondary text-foreground" : "text-muted-foreground",
                )}
              >
                {seat.full_name || seat.name}
                <span className="label-caps ml-2">{seat.name}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

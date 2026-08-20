// Same-origin talk to Frappe. The app is served by Frappe itself (see
// auraos/www/aura_next.py), so the session cookie rides along automatically and
// there is no token auth, no CORS and no second backend.
//
// This file is the only place in the app that calls fetch. Screens never build
// a request; they call useMethod / useList / useDoc from lib/queries.ts, which
// call the three functions at the bottom of this file. One transport means one
// CSRF rule and one error shape, which is the whole point of the layer.

declare global {
  interface Window {
    csrf_token?: string;
  }
}

/**
 * The token the page shell injects (`window.csrf_token = '{{ csrf_token }}'`).
 *
 * Frappe rejects an authenticated POST without it. Every request this file
 * makes is a POST, so the header is attached unconditionally rather than being
 * something a caller can forget.
 */
export function csrfToken(): string {
  const token = typeof window === "undefined" ? undefined : window.csrf_token;
  // The vite dev server serves index.html untouched, so the Jinja tag is still
  // literal there and must not be sent as if it were a token.
  return token && !token.startsWith("{{") ? token : "";
}

/**
 * What went wrong, in the only five flavours a screen has to care about.
 *
 * - `session`  the session is gone or was never there. Sign in again.
 * - `permission` signed in, not allowed. The server refused on purpose.
 * - `validation` the server rejected the input and said why, in `messages`.
 * - `notfound` the record is not there.
 * - `network`  the request never reached the server.
 * - `server`   anything else, including a 500.
 */
export type FrappeErrorKind =
  "session" | "permission" | "validation" | "notfound" | "network" | "server";

/**
 * Every failure out of this file is a FrappeError. Nothing else escapes, so a
 * screen never has to guess whether it caught a TypeError from fetch, a string
 * from JSON.parse or an error shape Frappe invented.
 */
export class FrappeError extends Error {
  readonly kind: FrappeErrorKind;
  readonly status: number;
  /** Human sentences the server sent, already unwrapped. May be empty. */
  readonly messages: string[];
  /** Frappe's own class name, e.g. "PermissionError", when it sent one. */
  readonly excType: string;
  /** The method or doctype that failed, for the console and for logs. */
  readonly endpoint: string;

  constructor(init: {
    kind: FrappeErrorKind;
    status: number;
    messages: string[];
    excType?: string;
    endpoint: string;
  }) {
    super(init.messages[0] || defaultMessage(init.kind));
    this.name = "FrappeError";
    this.kind = init.kind;
    this.status = init.status;
    this.messages = init.messages;
    this.excType = init.excType ?? "";
    this.endpoint = init.endpoint;
  }
}

function defaultMessage(kind: FrappeErrorKind): string {
  switch (kind) {
    case "session":
      return "Your session has ended. Sign in again.";
    case "permission":
      return "You do not have access to this.";
    case "validation":
      return "The server rejected that.";
    case "notfound":
      return "That record no longer exists.";
    case "network":
      return "Could not reach the server.";
    default:
      return "Something went wrong on the server.";
  }
}

/**
 * One sentence for any thrown thing, so a catch block never renders "[object
 * Object]". Screens should prefer <ErrorState error={...} /> over calling this
 * directly; it exists for toasts and inline field errors.
 */
export function errorMessage(error: unknown): string {
  if (error instanceof FrappeError) return error.messages.join("\n") || error.message;
  if (error instanceof Error) return error.message;
  return String(error ?? "Something went wrong.");
}

const TAG = /<[^>]*>/g;

/**
 * Frappe wraps its human messages twice: `_server_messages` is a JSON string
 * holding an array of JSON strings, each of which is an object with a
 * `message` key that may contain HTML. This is what frontend/src/utils
 * relied on frappe-ui to do, kept here because there is no frappe-ui now.
 */
function unwrapMessages(body: Record<string, unknown> | undefined): string[] {
  if (!body) return [];
  const found: string[] = [];

  const packed = body["_server_messages"];
  if (typeof packed === "string") {
    try {
      const outer = JSON.parse(packed) as unknown[];
      for (const entry of outer) {
        if (typeof entry !== "string") continue;
        try {
          const inner = JSON.parse(entry) as { message?: unknown };
          found.push(String(inner.message ?? entry));
        } catch {
          found.push(entry);
        }
      }
    } catch {
      found.push(packed);
    }
  }

  for (const key of ["_error_message", "message", "exception"]) {
    const value = body[key];
    if (typeof value === "string" && value) found.push(value);
  }

  const cleaned = found
    .map((text) =>
      text
        .replace(/<br\s*\/?>/gi, "\n")
        .replace(TAG, "")
        .trim(),
    )
    .filter(Boolean);

  return [...new Set(cleaned)];
}

function kindFor(status: number, excType: string): FrappeErrorKind {
  if (status === 401) return "session";
  if (status === 403) return excType === "CSRFTokenError" ? "session" : "permission";
  if (status === 404) return "notfound";
  // Frappe answers frappe.throw with 417 and names the exception class.
  if (status === 417 || status === 400 || excType.includes("ValidationError")) {
    return "validation";
  }
  if (excType === "DoesNotExistError") return "notfound";
  if (excType === "PermissionError") return "permission";
  return "server";
}

/**
 * The single request. Everything is a POST: reads too, because a POST carries
 * the CSRF token that a mutation needs anyway, and one code path cannot drift
 * from the other. Frappe treats a whitelisted method the same either way.
 */
async function post(path: string, args: unknown, endpoint: string): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-Frappe-CSRF-Token": csrfToken(),
      },
      body: JSON.stringify(args ?? {}),
    });
  } catch {
    // fetch only rejects when the request never happened: offline, DNS, CORS.
    throw new FrappeError({ kind: "network", status: 0, messages: [], endpoint });
  }

  const text = await response.text();
  let body: Record<string, unknown> | undefined;
  try {
    body = text ? (JSON.parse(text) as Record<string, unknown>) : undefined;
  } catch {
    body = undefined;
  }

  if (!response.ok) {
    const excType = typeof body?.["exc_type"] === "string" ? (body["exc_type"] as string) : "";
    throw new FrappeError({
      kind: kindFor(response.status, excType),
      status: response.status,
      messages: unwrapMessages(body),
      excType,
      endpoint,
    });
  }

  // A whitelisted method's return value lives under `message`. Frappe puts
  // nothing there for a method that returns None, which is a legitimate answer.
  return body?.["message"];
}

/**
 * Call a whitelisted method: `callMethod("auraos.api.overdue_milestones")`.
 *
 * The type parameter is the endpoint's return shape and is not checked at
 * runtime; declare it next to the screen that reads it, or in lib/api-types.ts
 * once two screens need the same one.
 */
export async function callMethod<T>(method: string, args: unknown = {}): Promise<T> {
  return (await post(`/api/method/${method}`, args, method)) as T;
}

/** Frappe filter syntax: `{stage: ["not in", ["Won", "Lost"]], title: "x"}`. */
export type ListFilters = Record<string, unknown> | unknown[][];

export type ListQuery = {
  doctype: string;
  /** Always ask for what you use. Omitted means `name` only. */
  fields?: string[];
  filters?: ListFilters;
  orFilters?: ListFilters;
  orderBy?: string;
  groupBy?: string;
  /** Rows to return. 0 means every row this session may read, and is the default. */
  limit?: number;
  start?: number;
  /** Required when reading a child table directly. */
  parent?: string;
};

/**
 * Read a doctype list through Frappe's own permitted list endpoint, so row and
 * field permissions apply exactly as they do in the desk. This is the same
 * endpoint the Vue app's createListResource used.
 *
 * The limit defaults to 0 (everything) rather than to Frappe's own default of
 * 20, which silently truncates a board to its first twenty cards and shows no
 * sign of having done so.
 */
export async function getList<T>(query: ListQuery): Promise<T[]> {
  const rows = await callMethod<T[]>("frappe.client.get_list", {
    doctype: query.doctype,
    fields: query.fields ?? ["name"],
    filters: query.filters,
    or_filters: query.orFilters,
    order_by: query.orderBy,
    group_by: query.groupBy,
    limit_start: query.start,
    limit_page_length: query.limit ?? 0,
    parent: query.parent,
  });
  return rows ?? [];
}

/** One whole document, permissions applied. For detail screens. */
export async function getDoc<T>(doctype: string, name: string): Promise<T> {
  return await callMethod<T>("frappe.client.get", { doctype, name });
}

/** What Frappe returns for an accepted upload. */
export type UploadedFile = {
  file_url?: string;
  file_name?: string;
  name?: string;
};

export type UploadOptions = {
  /** Attach the file to this doctype and record, rather than leaving it loose. */
  doctype?: string;
  docname?: string;
  fieldname?: string;
  /** Private files need a session to read; public ones are served to anyone. */
  isPrivate?: boolean;
  /** Where Frappe files it, e.g. "Home/Attachments". */
  folder?: string;
};

/**
 * Upload a file.
 *
 * Separate from `request` because this one alone sends multipart rather than
 * JSON, so the body cannot go through the same encoder. Everything else is
 * shared deliberately: the same CSRF token, the same error classification, the
 * same FrappeError, so a failed upload reaches a screen looking exactly like
 * any other failure and `ErrorState` renders it without special cases.
 *
 * It lives here because two screens wrote this by hand independently before it
 * did, which is how one shared client quietly becomes several.
 */
export async function uploadFile(file: File, options: UploadOptions = {}): Promise<UploadedFile> {
  const form = new FormData();
  form.append("file", file, file.name);
  if (options.isPrivate) form.append("is_private", "1");
  if (options.folder) form.append("folder", options.folder);
  if (options.doctype) form.append("doctype", options.doctype);
  if (options.docname) form.append("docname", options.docname);
  if (options.fieldname) form.append("fieldname", options.fieldname);

  const endpoint = "upload_file";
  let response: Response;
  try {
    response = await fetch("/api/method/upload_file", {
      method: "POST",
      credentials: "same-origin",
      // No Content-Type: the browser must set the multipart boundary itself.
      headers: { Accept: "application/json", "X-Frappe-CSRF-Token": csrfToken() },
      body: form,
    });
  } catch {
    throw new FrappeError({ kind: "network", status: 0, messages: [], endpoint });
  }

  const text = await response.text();
  let payload: Record<string, unknown> | undefined;
  try {
    payload = text ? (JSON.parse(text) as Record<string, unknown>) : undefined;
  } catch {
    payload = undefined;
  }

  if (!response.ok) {
    const excType = String(payload?.["exc_type"] ?? "");
    throw new FrappeError({
      kind: kindFor(response.status, excType),
      status: response.status,
      messages: unwrapMessages(payload),
      endpoint,
    });
  }

  return (payload?.["message"] ?? {}) as UploadedFile;
}

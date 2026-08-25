// The three things a screen shows when it does not have data: loading, empty,
// broken. One representation each, reused everywhere, so the app does not grow
// five spinners and five ways of saying "nothing here yet".
//
// Screens should reach for <QueryState> first. It takes a query from
// lib/queries.ts and resolves all three cases, so the happy path is the only
// branch a screen writes by hand.

import type { ReactNode } from "react";
import { AlertTriangle, Inbox, LockKeyhole, WifiOff } from "lucide-react";
import type { UseQueryResult } from "@tanstack/react-query";

import { FrappeError } from "@/lib/frappe";
import { loginUrl } from "@/lib/session";
import { cn } from "@/lib/utils";

/**
 * Waiting for the server. A skeleton, not a spinner: it holds the shape of what
 * is coming, so the layout does not jump when it arrives.
 */
export function Loading({
  rows = 3,
  className,
  label = "Loading",
}: {
  rows?: number | undefined;
  className?: string | undefined;
  label?: string | undefined;
}) {
  return (
    <div
      className={cn("space-y-2 p-4", className)}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-4 animate-pulse rounded bg-secondary"
          style={{ width: `${100 - i * 12}%` }}
        />
      ))}
    </div>
  );
}

/**
 * There is genuinely nothing. Not a failure: a new company with no data has to
 * read as calm, so this is quiet and never uses an alarm colour.
 */
export function Empty({
  title,
  detail,
  icon,
  action,
  className,
}: {
  title: string;
  detail?: string | undefined;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string | undefined;
}) {
  return (
    <div className={cn("flex flex-col items-center gap-2 px-4 py-10 text-center", className)}>
      <span className="text-muted-foreground/60">
        {icon ?? <Inbox className="size-6" strokeWidth={1.5} />}
      </span>
      <div className="text-sm font-medium text-foreground">{title}</div>
      {detail ? <div className="max-w-sm text-xs text-muted-foreground">{detail}</div> : null}
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  );
}

function errorFace(error: unknown) {
  const kind = error instanceof FrappeError ? error.kind : "server";
  switch (kind) {
    case "session":
      return {
        icon: <LockKeyhole className="size-6" strokeWidth={1.5} />,
        title: "Your session has ended.",
        detail: "Sign in again to carry on.",
      };
    case "permission":
      return {
        icon: <LockKeyhole className="size-6" strokeWidth={1.5} />,
        title: "You do not have access to this.",
        detail: "Ask the founder if you think you should.",
      };
    case "network":
      return {
        icon: <WifiOff className="size-6" strokeWidth={1.5} />,
        title: "Could not reach the server.",
        detail: "Check the connection and try again.",
      };
    case "validation":
    case "notfound":
      return {
        icon: <AlertTriangle className="size-6" strokeWidth={1.5} />,
        title: "That did not work.",
        detail: undefined,
      };
    default:
      return {
        icon: <AlertTriangle className="size-6" strokeWidth={1.5} />,
        title: "This did not load.",
        detail: undefined,
      };
  }
}

/**
 * A failure a person can act on. The server's own sentences are shown when it
 * sent any, because a validation message is usually the most useful thing on
 * the screen; the generic line is the fallback, never a replacement.
 */
export function ErrorState({
  error,
  onRetry,
  className,
}: {
  error: unknown;
  onRetry?: (() => void) | undefined;
  className?: string | undefined;
}) {
  const face = errorFace(error);
  const kind = error instanceof FrappeError ? error.kind : "server";
  const messages = error instanceof FrappeError ? error.messages : [];
  const detail = messages.join("\n") || face.detail;

  return (
    <div
      className={cn("flex flex-col items-center gap-2 px-4 py-10 text-center", className)}
      role="alert"
    >
      <span className="text-ember">{face.icon}</span>
      <div className="text-sm font-medium text-foreground">{face.title}</div>
      {detail ? (
        <div className="max-w-sm text-xs whitespace-pre-line text-muted-foreground">{detail}</div>
      ) : null}
      {kind === "session" ? (
        <a
          href={loginUrl(window.location.pathname)}
          className="mt-1 rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-secondary"
        >
          Sign in
        </a>
      ) : onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1 rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-secondary"
        >
          Try again
        </button>
      ) : null}
    </div>
  );
}

/**
 * A single figure that is still on its way: a headline number in a stat tile, a
 * total in a header. The bar holds the number's width so the tile does not
 * resize under the reader.
 */
export function Figure({
  query,
  children,
  width = "6rem",
}: {
  query: UseQueryResult<unknown, unknown>;
  children: ReactNode;
  width?: string | undefined;
}) {
  if (query.isPending) {
    return (
      <span
        className="inline-block h-6 animate-pulse rounded bg-secondary align-middle"
        style={{ width }}
        role="status"
        aria-label="Loading"
      />
    );
  }
  if (query.isError) {
    return (
      <span className="text-muted-foreground" title={String((query.error as Error)?.message ?? "")}>
        -
      </span>
    );
  }
  return <>{children}</>;
}

/**
 * The whole non-happy path in one component.
 *
 *   <QueryState query={jobs} empty={{ title: "No jobs in production." }}>
 *     {(rows) => <JobsTable rows={rows} />}
 *   </QueryState>
 *
 * A query that fails renders <ErrorState> with a retry, so a permission error
 * or a dropped connection is a card that explains itself instead of a blank
 * page or an unhandled rejection.
 */
export function QueryState<T>({
  query,
  children,
  empty,
  isEmpty,
  loadingRows,
}: {
  query: UseQueryResult<T, unknown>;
  children: (data: T) => ReactNode;
  empty?: { title: string; detail?: string | undefined; icon?: ReactNode; action?: ReactNode };
  /** Defaults to "the array came back with no rows". */
  isEmpty?: ((data: T) => boolean) | undefined;
  loadingRows?: number | undefined;
}) {
  if (query.isPending) return <Loading rows={loadingRows ?? 3} />;
  if (query.isError) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;

  const data = query.data as T;
  const blank = isEmpty ? isEmpty(data) : Array.isArray(data) && data.length === 0;
  if (blank && empty) return <Empty {...empty} />;

  return <>{children(data)}</>;
}

/**
 * The same contract when one card is fed by several queries, which is common:
 * a table of jobs plus the companies they belong to.
 *
 *   <QueryStates queries={[jobs, companies]} isEmpty={() => rows.length === 0}
 *                empty={{ title: "No jobs in production." }}>
 *     {() => <JobsTable rows={rows} />}
 *   </QueryStates>
 *
 * The first query still loading wins, then the first that failed, so the reader
 * sees one state rather than a card half full of skeletons.
 */
export function QueryStates({
  queries,
  children,
  empty,
  isEmpty,
  loadingRows,
}: {
  queries: UseQueryResult<unknown, unknown>[];
  children: () => ReactNode;
  empty?: { title: string; detail?: string | undefined; icon?: ReactNode; action?: ReactNode };
  isEmpty?: (() => boolean) | undefined;
  loadingRows?: number | undefined;
}) {
  if (queries.some((q) => q.isPending)) return <Loading rows={loadingRows ?? 3} />;

  const failed = queries.find((q) => q.isError);
  if (failed) return <ErrorState error={failed.error} onRetry={() => void failed.refetch()} />;

  if (empty && isEmpty?.()) return <Empty {...empty} />;

  return <>{children()}</>;
}

// Whether a generated paper has been signed - the one control, shared by the
// two screens that show it (issue #106).
//
// The registry on /paperwork and the paperwork tab on a job both answer "has
// the client actually signed it?", so the vocabulary, the wording and the
// endpoint live here rather than twice over. The server sends the status as a
// field and the two stamps beside it; this file is where those become words.
//
// Nothing enforces an order: every state is offered from every state, because a
// paper sometimes has to be redone and a status set by mistake must not be a
// one-way door.

import { cn } from "@/lib/utils";
import { formatDateTime } from "@/lib/format";
import { resultOf, useMethodMutation } from "@/lib/queries";

/** The three states, in the order a paper usually travels. */
export const PAPER_STATUSES = ["Draft", "Awaiting signature", "Signed"] as const;

export type PaperStatus = (typeof PAPER_STATUSES)[number];

/** What every read path sends alongside a paper. */
export type PaperStatusFields = {
  status: PaperStatus | null;
  status_changed_by: string | null;
  /** The person's name, resolved by the server - never derived here. */
  status_changed_by_label: string | null;
  status_changed_on: string | null;
};

export type PaperStatusResult = PaperStatusFields & { name: string; paper: string | null };

const SET_STATUS = "auraos.api.set_paper_status";

/**
 * The mutation both screens use. Either screen's change refreshes the other's
 * list, so a paper marked signed on a job is signed in the registry too.
 */
export function useSetPaperStatus(onDone?: () => void) {
  return useMethodMutation<PaperStatusResult, { paper: string; status: PaperStatus }>(SET_STATUS, {
    invalidate: [resultOf("auraos.api.generated_papers"), resultOf("auraos.api.job_paperwork")],
    ...(onDone ? { onSuccess: onDone } : {}),
  });
}

const TONES: Record<PaperStatus, string> = {
  Draft: "border-border bg-secondary text-muted-foreground",
  "Awaiting signature": "border-transparent bg-ember-soft text-ember",
  Signed: "border-border bg-secondary text-positive",
};

/**
 * The status as a control: what it is now, and the other two beside it.
 *
 * A plain select on purpose - three states and no order is exactly what a
 * select is for, and it is the same control the rest of the app changes a
 * stage with.
 */
export function PaperStatusSelect({
  status,
  onChange,
  disabled,
  className,
}: {
  status: PaperStatus;
  onChange: (next: PaperStatus) => void;
  disabled?: boolean | undefined;
  className?: string | undefined;
}) {
  return (
    <select
      value={status}
      disabled={disabled}
      aria-label="Signing status"
      onChange={(event) => onChange(event.target.value as PaperStatus)}
      className={cn(
        "rounded-md border px-2 py-1 text-xs font-medium outline-none",
        "focus:border-border-strong disabled:opacity-50",
        TONES[status] ?? TONES.Draft,
        className,
      )}
    >
      {PAPER_STATUSES.map((option) => (
        <option key={option} value={option} className="bg-card text-foreground">
          {option}
        </option>
      ))}
    </select>
  );
}

/**
 * Who moved it and when - the question asked when a contract turns out to be
 * missing. A name, never a login, and never in the mono face: these are
 * Vietnamese names.
 */
export function PaperStatusStamp({
  by,
  byLabel,
  on,
}: {
  by: string | null;
  byLabel: string | null;
  on: string | null;
}) {
  if (!on && !by) return <span className="text-xs text-muted-foreground">-</span>;
  return (
    <span className="text-xs text-muted-foreground">
      {by ? <span>{byLabel || by}</span> : null}
      {by && on ? " · " : null}
      {on ? <span className="num whitespace-nowrap">{formatDateTime(on)}</span> : null}
    </span>
  );
}

/** Draft for a row the server sent without one, which is what a blank means. */
export function statusOf(row: { status: string | null }): PaperStatus {
  const status = row.status as PaperStatus | null;
  return status && PAPER_STATUSES.includes(status) ? status : "Draft";
}

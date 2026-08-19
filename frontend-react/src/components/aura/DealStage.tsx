// Moving a deal to another stage, in one place.
//
// The move itself is a `frappe.client.set_value` on Deal.stage, which is not an
// arbitrary choice: set_value loads the document and saves it, so Deal's
// before_save runs and append_stage_change writes the stage_history row. A
// direct db write would change the stage and leave no history, and the payment
// milestone triggers read stage - so a second way into that field is a second
// set of rules about what a stage change means.
//
// Two stages carry a question with them. Lost needs a reason before the server
// will accept it, and Won is where a job gets created. Both are part of moving
// a deal, not of any one screen, which is why they live here rather than on the
// board that happened to implement them first.

import { useEffect, useRef, useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";

import { Modal, inputClass, pillToneClass } from "@/components/aura/primitives";
import { cn } from "@/lib/utils";
import { useQueryClient } from "@tanstack/react-query";

import { docOf, listsOf, resultOf, useMethodMutation } from "@/lib/queries";

export const DEAL_STAGES = [
  "Brief Received",
  "De-brief",
  "Breakdown",
  "Quote Sent",
  "Negotiation",
  "Won",
  "Lost",
] as const;

export const RESOLVED_STAGES = new Set<string>(["Won", "Lost"]);

// Deal.lost_reason is a Select with exactly these options.
export const LOST_REASONS = ["Price", "Timing", "Silence", "Competitor", "Scope"];

// Only tones primitives actually defines. An unknown tone falls back to
// neutral without complaining, so an invented name here would look like a
// styling choice rather than the mistake it is.
export const STAGE_TONE: Record<string, string> = {
  Breakdown: "ink",
  "Quote Sent": "outline",
  Negotiation: "ember",
  Won: "positive",
  Lost: "ember",
};

type JobResult = { name: string };

export type StageChange = {
  /** Ask for a stage. Lost and Won open their dialog instead of writing. */
  request: (deal: { name: string; title?: string | null; stage: string }, stage: string) => void;
  /** Ask for the Lost reason without naming a stage - the row control's shape. */
  requestLost: (deal: { name: string; title?: string | null }) => void;
  /**
   * Offer the job for a deal that reached Won by some other write - a table
   * edit, an insert. The prompt belongs to reaching Won, not to this control.
   */
  offerJob: (name: string, title: string | null) => void;
  /** Render this somewhere in the screen: it is the two dialogs. */
  dialogs: ReactNode;
  pending: boolean;
  error: unknown;
};

export function useDealStageChange({
  invalidate,
  hasJob,
  onWrite,
  onSaved,
}: {
  invalidate: (readonly unknown[])[];
  /** True when this deal already has a job, so Won does not offer a second. */
  hasJob?: (deal: string) => boolean;
  /** Fires the moment the write is sent, for optimistic screens. */
  onWrite?: (deal: string, stage: string) => void;
  /**
   * The saved document, for a screen holding its own copy of it. The deal
   * detail seeds a snapshot once per deal and renders from that, so a refetch
   * behind it changes nothing on screen - it has to be handed the new copy.
   */
  onSaved?: (doc: unknown, deal: string) => void;
}): StageChange {
  const navigate = useNavigate();
  const client = useQueryClient();

  // The title of each in-flight move, so the Won prompt can name the deal
  // without the title riding along in the write. It used to be sent as a
  // `_title` key inside the set_value payload, which Frappe drops on the floor
  // because Deal has no such field - a fake field on the wire, working only by
  // the server's good manners.
  const titles = useRef(new Map<string, string>());
  const [pendingLost, setPendingLost] = useState<{ name: string; title: string } | null>(null);
  const [pendingJob, setPendingJob] = useState<{ name: string; title: string } | null>(null);

  const setStage = useMethodMutation<
    unknown,
    { doctype: string; name: string; fieldname: Record<string, unknown> }
  >("frappe.client.set_value", {
    invalidate,
    onSuccess: (result, args) => {
      const title = titles.current.get(args.name) ?? args.name;
      titles.current.delete(args.name);

      // set_value returns the whole saved document. Hand it to the doc cache
      // and to any screen rendering its own copy, then invalidate so a reader
      // that has neither still refetches.
      client.setQueryData(docOf("Deal", args.name), result);
      onSaved?.(result, args.name);
      void client.invalidateQueries({ queryKey: docOf("Deal", args.name) });

      if (args.fieldname["stage"] !== "Won") return;
      if (hasJob?.(args.name)) return;
      // Winning a deal is where the job is created; ask right here rather than
      // leaving it to be remembered later.
      setPendingJob({ name: args.name, title });
    },
  });

  const createJob = useMethodMutation<JobResult, { deal: string }>(
    "auraos.api.create_job_from_deal",
    {
      invalidate: [...invalidate, listsOf("Job")],
      onSuccess: (job) => {
        setPendingJob(null);
        void navigate({ to: "/jobs/$jobId", params: { jobId: job.name } });
      },
    },
  );

  function write(name: string, title: string, fieldname: Record<string, unknown>) {
    titles.current.set(name, title);
    onWrite?.(name, String(fieldname["stage"]));
    setStage.mutate({ doctype: "Deal", name, fieldname });
  }

  function request(deal: { name: string; title?: string | null; stage: string }, stage: string) {
    if (deal.stage === stage) return;
    const title = deal.title || deal.name;
    if (stage === "Lost") {
      // The server refuses Lost without a reason; collect it first.
      setPendingLost({ name: deal.name, title });
      return;
    }
    write(deal.name, title, { stage });
  }

  const dialogs = (
    <>
      {pendingLost ? (
        <LostReasonDialog
          title={pendingLost.title}
          onClose={() => setPendingLost(null)}
          onConfirm={(reason, note) => {
            const deal = pendingLost;
            setPendingLost(null);
            if (!deal) return;
            write(deal.name, deal.title, {
              stage: "Lost",
              lost_reason: reason,
              lost_note: note,
            });
          }}
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
    </>
  );

  return {
    request,
    requestLost: (deal) => setPendingLost({ name: deal.name, title: deal.title || deal.name }),
    offerJob: (name, title) => {
      if (hasJob?.(name)) return;
      setPendingJob({ name, title: title ?? name });
    },
    dialogs,
    pending: setStage.isPending || createJob.isPending,
    error: setStage.isError ? setStage.error : createJob.isError ? createJob.error : null,
  };
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

/**
 * The stage control itself: a select that looks like the Pill it replaces.
 * Shared so the header on the detail screen and any future caller cannot drift
 * into offering different stages.
 */
export function StageSelect({
  value,
  onChange,
  disabled,
}: {
  value: string;
  onChange: (stage: string) => void;
  disabled?: boolean | undefined;
}) {
  return (
    <span className="relative inline-flex items-center">
      <select
        aria-label="Stage"
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className={cn(
          "cursor-pointer appearance-none rounded-md border py-0.5 pr-6 pl-2",
          "text-[11px] font-medium whitespace-nowrap",
          "disabled:cursor-not-allowed disabled:opacity-60",
          pillToneClass(STAGE_TONE[value]),
        )}
      >
        {DEAL_STAGES.map((stage) => (
          <option key={stage} value={stage}>
            {stage}
          </option>
        ))}
      </select>
      {/* A real element rather than a background-image caret. An inline SVG
          data URI in an arbitrary Tailwind value contains spaces, and Tailwind
          splits classes on spaces - the rule would never be generated and the
          caret would be silently absent, which reads as a design choice. */}
      <ChevronDown
        aria-hidden="true"
        className="pointer-events-none absolute right-1.5 size-3 opacity-70"
      />
    </span>
  );
}

// Money in: what the client owes on this job, and how far along each part of it
// has got. Replaces frontend/src/components/MilestonesPanel.vue, running in
// production - same four endpoints, same rules, same words.
//
// The plan is edited as a whole and saved as a whole: percentages rebalance to
// 100 as one is typed, and the amounts are never sent, because the server
// derives them from the quoted total on save.

import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";

import { Card, Money, Pill } from "@/components/aura/primitives";
import { ErrorState, QueryState } from "@/components/aura/states";
import {
  COLLECTION_STATUSES,
  LOCKED_STATUSES,
  PAID,
  STAGES,
  type Milestone,
  type MilestonesPayload,
  docKey,
} from "@/components/aura/job";
import { countLabel, formatDate, overdueLabel } from "@/lib/format";
import { resultOf, useMethod, useMethodMutation } from "@/lib/queries";

/** A milestone as the panel edits it: the stored row plus a stable row key. */
type PlanRow = Milestone & { key: string };

type InvoiceText = { text: string };

function isLocked(row: PlanRow): boolean {
  return LOCKED_STATUSES.includes(row.status);
}

function pctOf(row: { pct: number | null }): number {
  return Number(row.pct) || 0;
}

/**
 * Editing one milestone's share rebalances the others, so the plan lands back
 * on 100% by itself. Invoiced and paid rows never move: their share is already
 * on an invoice the client holds. Whole percents, with the remainder on the
 * last movable row, so the plan closes on exactly 100.
 */
function rebalanced(rows: PlanRow[], index: number, pct: number): PlanRow[] {
  const next = rows.map((row, i) => (i === index ? { ...row, pct } : { ...row }));
  const edited = next[index];
  if (!edited) return next;

  const movable = next.filter((row) => row !== edited && !isLocked(row));
  if (movable.length === 0) return next;

  const fixed = next
    .filter((row) => row !== edited && !movable.includes(row))
    .reduce((total, row) => total + pctOf(row), 0);
  const target = Math.max(0, 100 - pctOf(edited) - fixed);
  const current = movable.reduce((total, row) => total + pctOf(row), 0);

  let running = 0;
  movable.forEach((row, order) => {
    let share: number;
    if (order === movable.length - 1) share = Math.max(0, target - running);
    else if (current > 0) share = Math.round((pctOf(row) / current) * target);
    else share = Math.round(target / movable.length);
    row.pct = share;
    running += share;
  });

  return next;
}

/** Which step of the flow this milestone last took, and when. */
function stampFor(row: PlanRow): string {
  const stamp = row.paid_on || row.invoiced_on || row.requested_on;
  return stamp ? formatDate(stamp) : "";
}

/** The four planning fields, as the comparison for "unsaved". */
function planOf(row: {
  name: string | null;
  title: string | null;
  pct: number | null;
  trigger_stage: string | null;
}) {
  return [row.name ?? "", row.title ?? "", Number(row.pct) || 0, row.trigger_stage ?? ""];
}

export function JobMilestonesPanel({ job }: { job: string }) {
  const milestones = useMethod<MilestonesPayload>("auraos.api.job_milestones", { job });

  const [rows, setRows] = useState<PlanRow[]>([]);
  const [invoiceText, setInvoiceText] = useState("");
  const [copied, setCopied] = useState(false);
  const nextKey = useRef(0);
  const seeded = useRef<MilestonesPayload | null>(null);

  const stored = milestones.data?.milestones ?? [];
  const dirty = JSON.stringify(rows.map(planOf)) !== JSON.stringify(stored.map(planOf));

  // Seed the editable plan from the server, and re-seed whenever the server
  // answers differently - except while there are unsaved edits, which is the
  // one thing a background refetch must not throw away.
  useEffect(() => {
    const data = milestones.data;
    if (!data || data === seeded.current) return;
    if (seeded.current !== null && dirty) return;
    seeded.current = data;
    setRows(
      data.milestones.map((row) => ({ ...row, key: row.name ?? `new-${nextKey.current++}` })),
    );
  }, [milestones.data, dirty]);

  const plannedPct = rows.reduce((total, row) => total + pctOf(row), 0);
  const lockedPct = rows.filter(isLocked).reduce((total, row) => total + pctOf(row), 0);
  const overdueCount = rows.filter((row) => row.overdue).length;
  const termsDays = milestones.data?.payment_terms_days ?? 0;

  const invalidate = [resultOf("auraos.api.job_milestones"), docKey("Job", job)];

  const saver = useMethodMutation<MilestonesPayload, Record<string, unknown>>(
    "auraos.api.save_job_milestones",
    { invalidate },
  );

  // The typed plan is deliberately left alone when a save is refused: a refusal
  // is usually one number to correct, and throwing the plan away makes the
  // founder retype it to find out they were nearly right.
  const statusSetter = useMethodMutation<Milestone, Record<string, unknown>>(
    "auraos.api.set_milestone_status",
    { invalidate },
  );

  const invoiceRequest = useMethodMutation<InvoiceText, Record<string, unknown>>(
    "auraos.api.milestone_invoice_request",
    {
      onSuccess: (result) => {
        setInvoiceText(result.text);
        copyText(result.text);
      },
    },
  );

  function copyText(text: string) {
    const clipboard = navigator.clipboard;
    if (!clipboard) {
      setCopied(false);
      return;
    }
    clipboard.writeText(text).then(
      () => setCopied(true),
      () => setCopied(false),
    );
  }

  function addRow() {
    setRows((current) => [
      ...current,
      {
        key: `new-${nextKey.current++}`,
        name: null,
        idx: null,
        title: "",
        pct: Math.max(0, 100 - plannedPct),
        trigger_stage: STAGES[0] ?? "",
        amount: null,
        status: "Not requested",
        due_on: null,
        requested_on: null,
        invoiced_on: null,
        paid_on: null,
        overdue: false,
        days_overdue: 0,
      },
    ]);
  }

  function setStatus(row: PlanRow, status: string) {
    setRows((current) => current.map((one) => (one.key === row.key ? { ...one, status } : one)));
    statusSetter.mutate({ job, milestone: row.name, status });
  }

  function savePlan() {
    saver.mutate({
      job,
      milestones: rows.map((row) => ({
        name: row.name,
        title: row.title,
        pct: row.pct,
        trigger_stage: row.trigger_stage,
      })),
    });
  }

  const failure = saver.error ?? statusSetter.error ?? invoiceRequest.error;

  return (
    <Card
      title="Payment milestones"
      subtitle={
        <span className="flex flex-wrap items-center gap-2">
          {overdueCount ? (
            <span title={`Uncollected more than ${termsDays} days after falling due`}>
              <Pill tone="ember">{countLabel(overdueCount, "milestone")} overdue</Pill>
            </span>
          ) : null}
          <span className={plannedPct === 100 ? undefined : "text-ember"}>
            {plannedPct}% of the quote planned
          </span>
        </span>
      }
    >
      <QueryState
        query={milestones}
        isEmpty={() => rows.length === 0}
        empty={{
          title: "No payment milestones.",
          detail: "This job has nothing chasing the client.",
        }}
      >
        {() => (
          <div className="overflow-x-auto">
            {/* Fixed columns: the collection control carries the longest text on
                the row and an auto layout gave the width to the amounts, which
                clipped it mid-word. */}
            <table className="w-full min-w-[56rem] table-fixed">
              <thead className="border-b border-border">
                <tr>
                  <th className="label-caps w-1/5 px-4 py-2 text-left font-normal">Milestone</th>
                  <th className="label-caps w-20 px-2 py-2 text-left font-normal">% of quote</th>
                  <th className="label-caps w-1/6 px-2 py-2 text-left font-normal">
                    Trigger stage
                  </th>
                  <th className="label-caps w-1/6 px-2 py-2 text-right font-normal">Amount</th>
                  <th className="label-caps px-2 py-2 text-left font-normal">Collection</th>
                  <th className="w-44 px-4 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {rows.map((row, index) => (
                  <tr
                    key={row.key}
                    className={row.overdue ? "bg-ember-soft/50 align-top" : "align-top"}
                  >
                    <td className="px-4 py-2">
                      <input
                        value={row.title ?? ""}
                        placeholder="Deposit"
                        aria-label="Milestone name"
                        onChange={(event) =>
                          setRows((current) =>
                            current.map((one) =>
                              one.key === row.key ? { ...one, title: event.target.value } : one,
                            ),
                          )
                        }
                        className="w-full rounded-lg border border-border bg-background px-2 py-1 text-sm outline-none focus:border-border-strong"
                      />
                    </td>
                    <td className="px-2 py-2">
                      <input
                        type="number"
                        min={0}
                        step={5}
                        value={row.pct ?? 0}
                        aria-label="Percent of the quote"
                        onChange={(event) =>
                          setRows((current) =>
                            rebalanced(current, index, event.target.valueAsNumber || 0),
                          )
                        }
                        className="num w-16 rounded-lg border border-border bg-background px-2 py-1 text-right text-sm outline-none focus:border-border-strong"
                      />
                    </td>
                    <td className="px-2 py-2">
                      <select
                        value={row.trigger_stage ?? ""}
                        aria-label="Trigger stage"
                        onChange={(event) =>
                          setRows((current) =>
                            current.map((one) =>
                              one.key === row.key
                                ? { ...one, trigger_stage: event.target.value }
                                : one,
                            ),
                          )
                        }
                        className="w-full rounded-lg border border-border bg-background px-2 py-1 text-sm outline-none focus:border-border-strong"
                      >
                        {STAGES.map((stage) => (
                          <option key={stage} value={stage}>
                            {stage}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-2 py-2 text-right">
                      <Money value={row.amount ?? 0} className="text-sm" />
                      {row.overdue ? (
                        <div className="text-xs whitespace-nowrap text-ember">
                          {overdueLabel(row.days_overdue)}
                        </div>
                      ) : row.due_on ? (
                        <div className="text-xs whitespace-nowrap text-muted-foreground">
                          due since {formatDate(row.due_on)}
                        </div>
                      ) : (
                        <div className="text-xs text-muted-foreground">not due yet</div>
                      )}
                    </td>
                    <td className="px-2 py-2">
                      {/* Sans, never the ledger face: the second half of every
                          option is Vietnamese and the mono face has no
                          diacritics. */}
                      <select
                        value={row.status}
                        disabled={!row.name}
                        aria-label="Collection status"
                        onChange={(event) => setStatus(row, event.target.value)}
                        className={`w-full rounded-lg border border-border bg-background px-2 py-1 font-sans text-sm outline-none focus:border-border-strong disabled:text-muted-foreground ${
                          row.status === PAID ? "text-positive" : "text-foreground"
                        }`}
                      >
                        {COLLECTION_STATUSES.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.value} - {option.vi}
                          </option>
                        ))}
                      </select>
                      {row.name && stampFor(row) ? (
                        <div className="num mt-1 text-xs text-muted-foreground">
                          {stampFor(row)}
                        </div>
                      ) : null}
                    </td>
                    <td className="px-4 py-2 text-right whitespace-nowrap">
                      {row.name ? (
                        <button
                          type="button"
                          title="Copy the invoice request for the accountant, ready to paste into Zalo"
                          onClick={() => {
                            setCopied(false);
                            invoiceRequest.mutate({ job, milestone: row.name });
                          }}
                          className="rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:border-border-strong hover:text-foreground"
                        >
                          Invoice request
                        </button>
                      ) : null}
                      <button
                        type="button"
                        title="Remove this milestone"
                        aria-label="Remove this milestone"
                        onClick={() =>
                          setRows((current) => current.filter((one) => one.key !== row.key))
                        }
                        className="ml-1 rounded-md border border-border p-1 text-muted-foreground hover:border-border-strong hover:text-ember"
                      >
                        <X className="size-3" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </QueryState>

      <div className="space-y-2 border-t border-border px-4 py-3">
        {plannedPct !== 100 && lockedPct ? (
          <p className="text-xs text-ember">
            {lockedPct}% of the plan is already invoiced or paid and cannot rebalance itself -
            adjust the open rows to bring the total to 100%.
          </p>
        ) : null}

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={addRow}
            className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-secondary"
          >
            Add milestone
          </button>
          <button
            type="button"
            disabled={!dirty || saver.isPending}
            onClick={savePlan}
            className="rounded-lg bg-ember px-3 py-1.5 text-xs font-medium text-ember-foreground hover:opacity-90 disabled:opacity-40"
          >
            {saver.isPending ? "Saving..." : "Save plan"}
          </button>
          {dirty ? (
            <span className="text-xs text-ember">
              Unsaved changes - amounts refresh from the quote on save.
            </span>
          ) : null}
        </div>

        {failure ? <ErrorState error={failure} className="px-0 py-2" /> : null}

        {/* The invoice request is shown as well as copied, both so the founder
            can read what they are pasting and so a browser that refuses the
            clipboard still leaves them something to select. */}
        {invoiceText ? (
          <div className="rounded-xl border border-border bg-secondary/60 p-3">
            <div className="mb-2 flex items-center gap-2">
              <span className="label-caps">
                {copied ? "Copied - paste into Zalo" : "Invoice request for the accountant"}
              </span>
              <button
                type="button"
                onClick={() => copyText(invoiceText)}
                className="ml-auto rounded-md border border-border bg-card px-2 py-0.5 text-xs text-muted-foreground hover:text-foreground"
              >
                {copied ? "Copy again" : "Copy"}
              </button>
              <button
                type="button"
                onClick={() => setInvoiceText("")}
                className="rounded-md border border-border bg-card px-2 py-0.5 text-xs text-muted-foreground hover:text-foreground"
              >
                Close
              </button>
            </div>
            {/* Sans: the request is Vietnamese prose, not a ledger column. */}
            <pre className="font-sans text-sm whitespace-pre-wrap text-foreground">
              {invoiceText}
            </pre>
            <p className="mt-2 text-xs text-muted-foreground">
              Copying does not change the milestone - mark it Requested once you have actually sent
              it.
            </p>
          </div>
        ) : null}
      </div>
    </Card>
  );
}

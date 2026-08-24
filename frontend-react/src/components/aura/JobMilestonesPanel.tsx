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
  INVOICED,
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

/**
 * Whether a status still holds an invoice: đã xuất HĐ and everything past it.
 * Anything short of it has walked back before the invoice was issued, and the
 * server clears the number, the issue date and the rate together.
 */
function keepsInvoice(status: string): boolean {
  return LOCKED_STATUSES.includes(status);
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

/**
 * The VAT rate the invoice beside it was written at. Shown from the issue date,
 * because the issue date is what says an invoice exists: a milestone with no
 * date has no invoice to describe, and a rate of 0 is a real export invoice
 * rather than a way of saying nothing was issued.
 *
 * Shown and never edited. The rate is captured once, at issue, from the job -
 * today's rate must not restate an invoice the client is already holding - so
 * there is no control for it anywhere on this screen.
 */
function vatNote(row: PlanRow): string | null {
  if (!row.invoiced_on) return null;
  const rate = row.invoice_vat_pct;
  if (rate === null || rate === undefined) return null;
  return `VAT ${Number(rate)}%`;
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

/**
 * Everything on a row a person types, plan or not.
 *
 * Deliberately a second function rather than four more fields inside planOf.
 * `planOf` answers "does Save plan have anything to send", which is what
 * lights the button; this answers "would a refetch overwrite something
 * somebody typed", which is a wider question and always will be - the invoice
 * number is saved through set_milestone_status, not through the plan.
 *
 * #137: the two used to be one, and a milestone's invoice number was thrown
 * away by the refetch the status change itself triggers. Marking a milestone
 * invoiced is what opens the field, so the refetch was always racing the
 * typing it had just invited, and it won often enough to be the normal case.
 *
 * #140: the row is the right thing to read *here* - this asks what is on the
 * screen - and the wrong thing to read when deciding what to save. What was
 * typed lives in `typedInvoiceNos`, out of reach of the payload that replaces
 * the row.
 */
function typedOf(row: { invoice_no: string | null }) {
  return row.invoice_no ?? "";
}

/**
 * What the saver did the last time an invoice field was blurred, per milestone.
 * Rendered onto the field as `data-invoice-save` and read by nothing else.
 *
 * #140: the saver is allowed to decide not to send - the same number typed
 * twice is a write that changes nothing - but the only evidence of that
 * decision used to be the absence of a request, which is also what a lost edit
 * looks like. A named outcome makes "it had nothing to send" and "it had
 * something and dropped it" tellable apart from the outside.
 *
 *   closed    - the field is not open for typing: no server row, or a status
 *               that holds no invoice.
 *   untouched - nothing has been typed since the server last took a number.
 *   unchanged - what was typed is already what is stored. Nothing sent, and
 *               nothing lost.
 *   sent      - a write went out carrying the typed number.
 */
type InvoiceSave = "idle" | "closed" | "untouched" | "unchanged" | "sent";

export function JobMilestonesPanel({ job }: { job: string }) {
  const milestones = useMethod<MilestonesPayload>("auraos.api.job_milestones", { job });

  const [rows, setRows] = useState<PlanRow[]>([]);
  const [invoiceText, setInvoiceText] = useState("");
  const [copied, setCopied] = useState(false);
  const nextKey = useRef(0);
  const seeded = useRef<MilestonesPayload | null>(null);
  const [invoiceSaves, setInvoiceSaves] = useState<Record<string, InvoiceSave>>({});

  /**
   * Invoice numbers that have been typed and that the server has not confirmed
   * yet, keyed by milestone name. Emptied for a milestone the moment a write
   * carrying its number comes back.
   *
   * Kept here rather than read back off the row, because the row is the one
   * thing a refetch replaces. #140: the saver compared `row.invoice_no` against
   * the server's copy, so a re-seed landing between the typing and the blur
   * emptied both sides at once - they matched, the no-op guard fired, and the
   * number went nowhere without a request, an error or a word. A ref is a value
   * no payload can reach, which is what keeps "empty because nobody typed" and
   * "empty because it was overwritten" two different answers.
   */
  const typedInvoiceNos = useRef(new Map<string, string>());

  const stored = milestones.data?.milestones ?? [];
  const dirty = JSON.stringify(rows.map(planOf)) !== JSON.stringify(stored.map(planOf));
  // What Save plan would send, plus what it would not. See typedOf.
  const edited = dirty || JSON.stringify(rows.map(typedOf)) !== JSON.stringify(stored.map(typedOf));

  // Seed the editable plan from the server, and re-seed whenever the server
  // answers differently - except while there are unsaved edits, which is the
  // one thing a background refetch must not throw away.
  useEffect(() => {
    const data = milestones.data;
    if (!data || data === seeded.current) return;
    if (seeded.current !== null && edited) return;
    seeded.current = data;
    setRows(
      data.milestones.map((row) => {
        // A number typed and not yet taken by the server outlives the payload
        // that would otherwise wipe it off the screen. See typedInvoiceNos.
        const pending = row.name ? typedInvoiceNos.current.get(row.name) : undefined;
        return {
          ...row,
          key: row.name ?? `new-${nextKey.current++}`,
          invoice_no: pending ?? row.invoice_no,
        };
      }),
    );
  }, [milestones.data, edited]);

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
    {
      invalidate,
      // A typed number stops being pending only once the server has taken it.
      // Until then it is what the field shows, whatever a refetch says - and a
      // refused write leaves it pending on purpose, so the founder still has
      // what they typed in front of them.
      onSuccess: (_result, args) => {
        if (args["invoice_no"] === undefined) return;
        const name = args["milestone"];
        if (typeof name === "string") typedInvoiceNos.current.delete(name);
      },
    },
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
        invoice_no: null,
        invoice_vat_pct: null,
        overdue: false,
        days_overdue: 0,
      },
    ]);
  }

  function setStatus(row: PlanRow, status: string) {
    // Walking back before đã xuất HĐ clears the invoice on the server - number,
    // issue date and rate in one go, because a number with no issue date is a
    // number nobody issued. The row drops all three in the same breath, so the
    // screen never shows a number the server has already forgotten.
    const invoice = keepsInvoice(status)
      ? {}
      : { invoice_no: null, invoice_vat_pct: null, invoiced_on: null };
    // Including anything typed and not yet sent: the row is dropping the
    // number, so a later blur must not post it back.
    if (!keepsInvoice(status) && row.name) typedInvoiceNos.current.delete(row.name);
    setRows((current) =>
      current.map((one) => (one.key === row.key ? { ...one, status, ...invoice } : one)),
    );
    statusSetter.mutate({ job, milestone: row.name, status });
  }

  /**
   * The number the accountant sent back, saved through the same door as the
   * status: đã xuất HĐ stamps the issue date and carries the number beside it.
   * Sent again while the milestone is still invoiced it corrects a mistyped
   * number and leaves the issue date alone, which is what the accountant's
   * corrections need.
   *
   * Only sent while the milestone is marked đã xuất HĐ. The server refuses a
   * number at any other status, and the only way to obey it from a paid
   * milestone would be to send đã xuất HĐ too - walking a collected payment
   * back behind the founder. A text field must not do that, so the field waits
   * for the status instead.
   */
  function saveInvoiceNo(row: PlanRow) {
    const name = row.name;
    if (!name) return;
    const record = (outcome: InvoiceSave) =>
      setInvoiceSaves((current) => ({ ...current, [name]: outcome }));

    if (row.status !== INVOICED) return record("closed");

    // What was typed, not what the row is holding: the same value until a
    // refetch replaces the row, and the whole defect lived in that gap.
    const pending = typedInvoiceNos.current.get(name);
    if (pending === undefined) return record("untouched");

    const typed = pending.trim();
    const savedRow = stored.find((one) => one.name === name);
    if (savedRow && (savedRow.invoice_no ?? "") === typed) {
      // A real no-op: the server already holds this number. Say so, rather
      // than just not sending, which is what a lost edit also looks like.
      typedInvoiceNos.current.delete(name);
      return record("unchanged");
    }

    record("sent");
    statusSetter.mutate({ job, milestone: name, status: INVOICED, invoice_no: typed });
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
                      {/* The invoice, beside the status that issues it. The
                          number is the only part anyone types: the rate is the
                          job's on the day the invoice went out, captured once
                          and never restated, so it is shown and not offered. */}
                      {row.name ? (
                        <div className="mt-1 flex items-center gap-2">
                          <input
                            value={row.invoice_no ?? ""}
                            disabled={row.status !== INVOICED}
                            placeholder="Invoice number"
                            aria-label="Invoice number"
                            title={
                              row.status === INVOICED
                                ? "The number the accountant sent back. Retyping it corrects the number without moving the issue date."
                                : `An invoice number belongs to a milestone marked ${INVOICED} - set the status first.`
                            }
                            data-invoice-save={(row.name && invoiceSaves[row.name]) || "idle"}
                            onChange={(event) => {
                              const value = event.target.value;
                              if (row.name) typedInvoiceNos.current.set(row.name, value);
                              setRows((current) =>
                                current.map((one) =>
                                  one.key === row.key ? { ...one, invoice_no: value } : one,
                                ),
                              );
                            }}
                            onBlur={() => saveInvoiceNo(row)}
                            onKeyDown={(event) => {
                              if (event.key === "Enter") event.currentTarget.blur();
                            }}
                            className="num w-32 rounded-lg border border-border bg-background px-2 py-0.5 text-xs outline-none focus:border-border-strong disabled:border-transparent disabled:bg-transparent disabled:px-0 disabled:text-muted-foreground"
                          />
                          {vatNote(row) ? (
                            <span
                              className="num text-xs text-muted-foreground"
                              title="The VAT rate this invoice was written at, recorded when it was issued"
                            >
                              {vatNote(row)}
                            </span>
                          ) : null}
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

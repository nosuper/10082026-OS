// Money out on a job: the cash handed to people, what each of them is still
// holding, every đồng logged against the job, and actual against quoted per
// category. Replaces frontend/src/components/JobMoneyPanel.vue - one read
// (auraos.api.job_money) answers all four, because they are computed from the
// same rows.

import { useState } from "react";
import { Paperclip } from "lucide-react";

import { Card, Money, Pill, Td, Th } from "@/components/aura/primitives";
import { ErrorState, QueryState } from "@/components/aura/states";
import {
  EVEN,
  FROM_ADVANCE,
  FROM_COMPANY,
  RETURN,
  type FloatRow,
  type MoneyPayload,
  type OperatingUser,
  personName,
} from "@/components/aura/job";
import { countLabel, formatDate, parseVnd, vnd } from "@/lib/format";
import { listsOf, resultOf, useMethod, useMethodMutation } from "@/lib/queries";

type SettlementResult = { recipient: string; amount: number; direction: string };

/** Budget bars fill toward the quoted cost; spending past it turns the bar. */
function barWidth(row: { quoted: number; actual: number }): number {
  if (!row.quoted) return row.actual ? 100 : 0;
  return Math.min(100, Math.round((row.actual / row.quoted) * 100));
}

/** One quoted line, as auraos.api.job_cost_lines sends it. */
type CostLineOption = {
  name: string;
  description: string | null;
  package: string | null;
  tax_type: string | null;
  quoted: number;
};

/**
 * The tax type that carries exposure, spelled as the pricing engine spells it.
 * The screen uses it only to mark which lines mean the company will be taxed
 * on this spend. The decision itself stays the server's.
 */
const NO_INVOICE_TAX = "Không hoá đơn";

export function JobMoneyPanel({ job }: { job: string }) {
  const money = useMethod<MoneyPayload>("auraos.api.job_money", { job });
  const users = useMethod<OperatingUser[]>("auraos.api.operating_users");
  const categories = useMethod<string[]>("auraos.api.job_expense_categories", { job });
  // The quoted lines this spend can answer to. Naming one is what carries
  // Không hoá đơn from the quote onto the money, which is the whole reason
  // the founder's exposure can be a fact rather than an estimate (#123).
  const costLines = useMethod<CostLineOption[]>("auraos.api.job_cost_lines", { job });

  // Entry forms stay collapsed until asked for: the page reads first and
  // writes second.
  const [showAdvance, setShowAdvance] = useState(false);
  const [showExpense, setShowExpense] = useState(false);
  const [confirming, setConfirming] = useState<string | null>(null);
  const [settled, setSettled] = useState("");

  const [advanceTo, setAdvanceTo] = useState("");
  const [advanceAmount, setAdvanceAmount] = useState("");
  const [advanceNote, setAdvanceNote] = useState("");

  const [expenseAmount, setExpenseAmount] = useState("");
  const [expenseCategory, setExpenseCategory] = useState("");
  const [expenseLine, setExpenseLine] = useState("");
  const [expenseWhat, setExpenseWhat] = useState("");
  const [expensePaidBy, setExpensePaidBy] = useState("");
  // paid_from is deliberately unset: it is the one field that decides who owes
  // whom afterwards, and a founder logging a company transfer under somebody
  // else's default would open a float in his own name.
  const [expenseFrom, setExpenseFrom] = useState("");

  const invalidate = [
    resultOf("auraos.api.job_money"),
    listsOf("Job Expense"),
    listsOf("Job Advance"),
    listsOf("Job Settlement"),
  ];

  const advance = useMethodMutation<unknown, Record<string, unknown>>(
    "auraos.api.record_job_advance",
    {
      invalidate,
      onSuccess: () => {
        setAdvanceAmount("");
        setAdvanceNote("");
      },
    },
  );

  const expense = useMethodMutation<unknown, Record<string, unknown>>(
    "auraos.api.log_job_expense",
    {
      invalidate,
      onSuccess: () => {
        setExpenseAmount("");
        setExpenseWhat("");
        // The quoted line is deliberately left as it was. Several
        // receipts in a row usually answer to the same line, and a form
        // that makes you re-pick it each time is a form people stop
        // using - which would put the spending back in unattributed.
      },
    },
  );

  const settle = useMethodMutation<SettlementResult, Record<string, unknown>>(
    "auraos.api.settle_job",
    {
      invalidate,
      onSuccess: (result) => {
        setConfirming(null);
        const who = personName(users.data, result.recipient);
        setSettled(
          result.direction === RETURN
            ? `${who} returned ${vnd(result.amount)} ₫ - float closed.`
            : `Paid ${who} ${vnd(-result.amount)} ₫ - float closed.`,
        );
      },
    },
  );

  const rows = money.data;
  const advances = [...(rows?.advances ?? [])].sort((a, b) =>
    String(b.transferred_on ?? "").localeCompare(String(a.transferred_on ?? "")),
  );
  const expenses = rows?.expenses ?? [];
  const floats = rows?.floats ?? [];

  function settleWording(held: FloatRow): string {
    const who = personName(users.data, held.holder);
    return held.direction === RETURN
      ? `${who} returns ${vnd(held.amount)} ₫`
      : `Pay ${who} ${vnd(-held.amount)} ₫`;
  }

  const advanceValue = parseVnd(advanceAmount);
  const expenseValue = parseVnd(expenseAmount);
  const failure = advance.error ?? expense.error ?? settle.error;

  return (
    <div className="space-y-4">
      <Card
        title="Cash advanced"
        subtitle={
          rows
            ? `${vnd(rows.spent_total)} ₫ spent of ${vnd(rows.quoted_total)} ₫ quoted · ${vnd(
                rows.advanced_total,
              )} ₫ advanced`
            : undefined
        }
        action={
          rows?.may_advance && !showAdvance ? (
            <button
              type="button"
              onClick={() => setShowAdvance(true)}
              className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-secondary"
            >
              Record advance
            </button>
          ) : null
        }
      >
        {/* Every advance on its own line: a history, not a per-person sum. The
            per-holder float below stays, because settlement closes a person's
            float and not a single line. */}
        <QueryState
          query={money}
          isEmpty={() => advances.length === 0}
          empty={{ title: "No cash advanced on this job yet." }}
        >
          {() => (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[32rem]">
                <thead className="border-b border-border">
                  <tr>
                    <Th>Date</Th>
                    <Th>To</Th>
                    <Th className="text-right">Amount</Th>
                    <Th>Note</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {advances.map((row) => (
                    <tr key={row.name}>
                      <Td className="num text-xs whitespace-nowrap text-muted-foreground">
                        {formatDate(row.transferred_on)}
                      </Td>
                      <Td>{personName(users.data, row.recipient)}</Td>
                      <Td className="text-right">
                        <Money value={row.amount ?? 0} />
                      </Td>
                      <Td className="text-muted-foreground">{row.note}</Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </QueryState>

        {floats.length ? (
          <>
            <div className="border-t border-border px-4 pt-3 pb-1">
              <span className="label-caps">Currently holding</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[38rem]">
                <thead className="border-b border-border">
                  <tr>
                    <Th>Holding</Th>
                    <Th className="text-right">Advanced</Th>
                    <Th className="text-right">Spent</Th>
                    <Th className="text-right">Float</Th>
                    <Th>Settle</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {floats.map((held) => (
                    <tr key={held.holder}>
                      <Td>{personName(users.data, held.holder)}</Td>
                      <Td className="text-right text-muted-foreground">
                        <Money value={held.advanced} />
                      </Td>
                      <Td className="text-right text-muted-foreground">
                        <Money value={held.spent} />
                      </Td>
                      <Td className="text-right font-medium">
                        <Money value={Math.abs(held.amount)} />
                      </Td>
                      <Td>
                        {held.direction === EVEN ? (
                          <span className="text-xs text-muted-foreground">Settled</span>
                        ) : confirming === held.holder ? (
                          <span className="flex flex-wrap items-center gap-1.5">
                            <span className="text-xs">{settleWording(held)}?</span>
                            <button
                              type="button"
                              disabled={settle.isPending}
                              onClick={() => {
                                setSettled("");
                                settle.mutate({ job, holder: held.holder });
                              }}
                              className="rounded-md bg-ember px-2 py-1 text-xs font-medium text-ember-foreground hover:opacity-90 disabled:opacity-40"
                            >
                              Confirm
                            </button>
                            <button
                              type="button"
                              onClick={() => setConfirming(null)}
                              className="rounded-md border border-border px-2 py-1 text-xs hover:bg-secondary"
                            >
                              Cancel
                            </button>
                          </span>
                        ) : (
                          <span className="flex flex-wrap items-center gap-2">
                            <span className="text-xs text-muted-foreground">
                              {settleWording(held)}
                            </span>
                            {rows?.may_settle ? (
                              <button
                                type="button"
                                onClick={() => setConfirming(held.holder)}
                                className="rounded-md border border-border px-2 py-1 text-xs hover:bg-secondary"
                              >
                                Settle
                              </button>
                            ) : null}
                          </span>
                        )}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : null}

        {settled ? (
          <p className="border-t border-border px-4 py-2 text-xs text-positive">{settled}</p>
        ) : null}

        {rows?.may_advance && showAdvance ? (
          <div className="flex flex-wrap items-center gap-2 border-t border-border bg-secondary/50 px-4 py-3">
            <span className="label-caps">Advance</span>
            <select
              value={advanceTo}
              aria-label="Who receives the advance"
              onChange={(event) => setAdvanceTo(event.target.value)}
              className="rounded-lg border border-border bg-background px-2 py-1.5 text-sm outline-none focus:border-border-strong"
            >
              <option value="">Who receives it...</option>
              {(users.data ?? []).map((user) => (
                <option key={user.name} value={user.name}>
                  {user.full_name || user.name}
                </option>
              ))}
            </select>
            <input
              inputMode="numeric"
              aria-label="Advance amount"
              placeholder="Amount"
              value={advanceValue ? vnd(advanceValue) : ""}
              onChange={(event) => setAdvanceAmount(event.target.value)}
              className="num w-36 rounded-lg border border-border bg-background px-2 py-1.5 text-right text-sm outline-none focus:border-border-strong"
            />
            <input
              aria-label="Advance note"
              placeholder="Note (optional)"
              value={advanceNote}
              onChange={(event) => setAdvanceNote(event.target.value)}
              className="min-w-0 flex-1 rounded-lg border border-border bg-background px-2.5 py-1.5 text-sm outline-none focus:border-border-strong"
            />
            <button
              type="button"
              disabled={!advanceTo || !advanceValue || advance.isPending}
              onClick={() =>
                advance.mutate({
                  job,
                  recipient: advanceTo,
                  amount: advanceValue,
                  note: advanceNote || null,
                })
              }
              className="rounded-lg bg-ember px-3 py-1.5 text-xs font-medium text-ember-foreground hover:opacity-90 disabled:opacity-40"
            >
              {advance.isPending ? "Recording..." : "Record"}
            </button>
          </div>
        ) : null}
      </Card>

      <Card
        title="Expenses"
        subtitle={
          rows
            ? `${countLabel(expenses.length, "expense")} · ${vnd(rows.spent_total)} ₫`
            : undefined
        }
        action={
          !showExpense ? (
            <button
              type="button"
              onClick={() => setShowExpense(true)}
              className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-secondary"
            >
              Log expense
            </button>
          ) : null
        }
      >
        <QueryState
          query={money}
          isEmpty={() => expenses.length === 0}
          empty={{ title: "Nothing logged yet." }}
        >
          {() => (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[38rem]">
                <thead className="border-b border-border">
                  <tr>
                    <Th>Date</Th>
                    <Th>Category</Th>
                    <Th>What</Th>
                    <Th>Paid by</Th>
                    <Th className="text-right">Amount</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {expenses.map((row) => (
                    <tr key={row.name}>
                      <Td className="num text-xs whitespace-nowrap text-muted-foreground">
                        {formatDate(row.spent_on)}
                      </Td>
                      <Td>{row.category || "-"}</Td>
                      <Td className="text-muted-foreground">
                        {row.description}
                        {row.photo ? (
                          <a
                            href={row.photo}
                            target="_blank"
                            rel="noopener"
                            className="ml-1.5 inline-flex items-center gap-1 text-ember hover:underline"
                          >
                            <Paperclip className="size-3" />
                            receipt
                          </a>
                        ) : null}
                      </Td>
                      <Td className="whitespace-nowrap text-muted-foreground">
                        {personName(users.data, row.paid_by)}
                        {row.paid_from === FROM_COMPANY ? (
                          <span
                            className="ml-1.5"
                            title="Paid by the company directly - settles no float"
                          >
                            <Pill>company</Pill>
                          </span>
                        ) : null}
                      </Td>
                      <Td className="text-right">
                        <Money value={row.amount ?? 0} />
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </QueryState>

        {showExpense ? (
          <div className="flex flex-wrap items-center gap-2 border-t border-border bg-secondary/50 px-4 py-3">
            <input
              inputMode="numeric"
              aria-label="Expense amount"
              placeholder="Amount"
              value={expenseValue ? vnd(expenseValue) : ""}
              onChange={(event) => setExpenseAmount(event.target.value)}
              className="num w-32 rounded-lg border border-border bg-background px-2 py-1.5 text-right text-sm outline-none focus:border-border-strong"
            />
            <select
              value={expenseCategory}
              aria-label="Expense category"
              onChange={(event) => setExpenseCategory(event.target.value)}
              className="rounded-lg border border-border bg-background px-2 py-1.5 text-sm outline-none focus:border-border-strong"
            >
              <option value="">Uncategorised</option>
              {(categories.data ?? []).map((title) => (
                <option key={title} value={title}>
                  {title}
                </option>
              ))}
            </select>
            <select
              value={expenseLine}
              aria-label="Quoted line this spend answers to"
              title="Which quoted line is this spending against? Leave it unattributed if nobody quoted it."
              onChange={(event) => setExpenseLine(event.target.value)}
              className="max-w-[13rem] rounded-lg border border-border bg-background px-2 py-1.5 text-sm outline-none focus:border-border-strong"
            >
              <option value="">no quoted line</option>
              {(costLines.data ?? []).map((line) => (
                <option key={line.name} value={line.name}>
                  {line.description || line.name}
                  {line.tax_type === NO_INVOICE_TAX ? " (no invoice)" : ""}
                </option>
              ))}
            </select>
            <input
              aria-label="What the money was for"
              placeholder="What was it for?"
              value={expenseWhat}
              onChange={(event) => setExpenseWhat(event.target.value)}
              className="min-w-0 flex-1 rounded-lg border border-border bg-background px-2.5 py-1.5 text-sm outline-none focus:border-border-strong"
            />
            <select
              value={expensePaidBy}
              aria-label="Who paid"
              onChange={(event) => setExpensePaidBy(event.target.value)}
              className="rounded-lg border border-border bg-background px-2 py-1.5 text-sm outline-none focus:border-border-strong"
            >
              <option value="">paid by me</option>
              {(users.data ?? []).map((user) => (
                <option key={user.name} value={user.name}>
                  {user.full_name || user.name}
                </option>
              ))}
            </select>
            <select
              value={expenseFrom}
              aria-label="Whose money it was"
              title="Whose money was it? An advance settles with the person holding it; the company's settles with nobody."
              onChange={(event) => setExpenseFrom(event.target.value)}
              className={`rounded-lg border bg-background px-2 py-1.5 text-sm outline-none focus:border-border-strong ${
                expenseFrom ? "border-border" : "border-ember/60"
              }`}
            >
              <option value="">whose money?</option>
              <option value={FROM_ADVANCE}>from advance</option>
              <option value={FROM_COMPANY}>company paid</option>
            </select>
            <button
              type="button"
              disabled={!expenseValue || !expenseFrom || expense.isPending}
              onClick={() =>
                expense.mutate({
                  job,
                  amount: expenseValue,
                  category: expenseCategory || null,
                  cost_line: expenseLine || null,
                  description: expenseWhat || null,
                  paid_by: expensePaidBy || null,
                  paid_from: expenseFrom,
                })
              }
              className="rounded-lg bg-ember px-3 py-1.5 text-xs font-medium text-ember-foreground hover:opacity-90 disabled:opacity-40"
            >
              {expense.isPending ? "Logging..." : "Log"}
            </button>
          </div>
        ) : null}
      </Card>

      {/* Actual against quoted, per category. The categories are the quote's own
          entries, so this costs nothing extra to know. */}
      <Card title="Where the money went" subtitle="Actual against the quoted cost, per category.">
        <QueryState
          query={money}
          isEmpty={() => (rows?.categories.length ?? 0) === 0}
          empty={{ title: "The quote named no cost categories." }}
        >
          {() => (
            <div className="space-y-3 p-4">
              {(rows?.categories ?? []).map((row) => (
                <div key={row.title}>
                  <div className="flex items-baseline gap-2 text-sm">
                    <span className="font-medium">{row.title}</span>
                    <span className="num ml-auto">
                      {vnd(row.actual)}
                      <span className="text-muted-foreground"> / {vnd(row.quoted)}</span>
                    </span>
                    <span
                      className={`num w-28 text-right text-xs ${
                        row.variance > 0 ? "font-medium text-ember" : "text-muted-foreground"
                      }`}
                    >
                      {row.variance > 0 ? "+" : ""}
                      {vnd(row.variance)}
                    </span>
                  </div>
                  <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-secondary">
                    <div
                      className={`h-full rounded-full ${
                        !row.actual ? "bg-border" : row.variance > 0 ? "bg-ember" : "bg-positive"
                      }`}
                      style={{ width: `${barWidth(row)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </QueryState>
        <p className="border-t border-border px-4 py-2 text-xs text-muted-foreground">
          Quoted cost is what the job expected to pay out for that category - not what the client is
          charged for it.
        </p>
      </Card>

      {failure ? (
        <Card>
          <ErrorState error={failure} />
        </Card>
      ) : null}
    </div>
  );
}

// The bank's statement beside our own ledger, and the difference between them
// (#150).
//
// **The two unmatched lists are the product.** A reconciliation screen that
// showed only what lined up would be a screen agreeing with itself: the reason
// to import a statement at all is that the bank saw something we have no
// record of, or we recorded something the bank never saw. Both lists are on
// this page, both named, and neither is hidden behind a filter.
//
// **Matching suggests; a person confirms.** Nothing on this screen writes a
// ledger entry, and no suggestion applies itself. The server ranks candidates
// on exact amount, agreeing direction and a shared reference; where two
// candidates are indistinguishable it offers none rather than the nearer one,
// and this screen shows that as a choice rather than as an answer.
//
// **Some lines can never match, and the screen says why.** Tax paid to the
// treasury, bank interest and cash moved into the company's own box are
// movements AuraOS keeps no record of at all. They read as an explanation
// rather than as a failure, because somebody hunting for a record nobody made
// is the cost of the alternative.
//
// Founder-only, decided by the server: every endpoint behind this page refuses
// anyone else, and the screen renders that refusal rather than hiding itself.

import { createFileRoute } from "@tanstack/react-router";
import { Landmark, Link2, Unlink } from "lucide-react";
import { useState } from "react";

import { AppShell } from "@/components/aura/AppShell";
import { FinanceTabs } from "@/components/aura/FinanceTabs";
import { Card, Money, Pill, Stat, Td, Th } from "@/components/aura/primitives";
import { ErrorState, QueryState } from "@/components/aura/states";
import { countLabel, formatDate } from "@/lib/format";
import { uploadFile } from "@/lib/frappe";
import { resultOf, useMethod, useMethodMutation } from "@/lib/queries";

// -- what the server sends --
//
// Pinned by auraos/auraos/doctype/bank_statement/test_bank_statement.py.

type StatementRow = {
  name: string;
  account: string;
  period_from: string;
  period_to: string;
  opening: number;
  closing: number;
  withdrawn: number;
  deposited: number;
};

type Candidate = {
  entry: string;
  confidence: "strong" | "weak";
  shared_references: string[];
  days_apart: number;
};

type StatementLine = {
  name: string;
  effective_on: string;
  sequence: string;
  description: string;
  /** Signed: positive arrived, negative left. */
  amount: number;
  running_balance: number;
  matched_entry: string | null;
  matched_on: string | null;
  matched_by: string | null;
  /** Why this line can never match, when it never can. */
  unmodelled: string | null;
  candidates: Candidate[];
  suggestion: Candidate | null;
};

type LedgerEntry = {
  name: string;
  entry_date: string;
  amount: number;
  flow: string;
  job: string | null;
  description: string | null;
};

type Reconciliation = {
  statement: StatementRow;
  lines: StatementLine[];
  unmatched_entries: LedgerEntry[];
};

type CashAccountRow = { name: string; account_name: string };
type CashAccountsReport = { accounts: CashAccountRow[] };

const STATEMENTS = "auraos.api.bank_statements";
const RECONCILE = "auraos.api.bank_reconciliation";

export const Route = createFileRoute("/finance/bank")({
  head: () => ({
    meta: [
      { title: "Bank - the statement beside the ledger | AuraOS" },
      {
        name: "description",
        content:
          "Bank statements imported as they arrived, lined up against the cash ledger, with both sides' unmatched movements named.",
      },
    ],
  }),
  component: BankPage,
});

function BankPage() {
  const statements = useMethod<StatementRow[]>(STATEMENTS);
  const [open, setOpen] = useState<string | null>(null);
  const chosen = open ?? statements.data?.[0]?.name ?? null;

  return (
    <AppShell title="Finance" meta={<FinanceTabs />}>
      <div className="space-y-4">
        <Card
          title="Statements"
          subtitle="As the bank sent them. A statement is recorded, never edited."
        >
          <QueryState
            query={statements}
            isEmpty={() => (statements.data ?? []).length === 0}
            empty={{
              title: "No statement has been imported yet.",
              detail:
                "Import one and this screen will show it beside the ledger, with what neither side can account for.",
              icon: <Landmark className="size-6" strokeWidth={1.5} />,
            }}
            loadingRows={2}
          >
            {(rows) => (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b border-border">
                    <tr>
                      <Th>Account</Th>
                      <Th>Period</Th>
                      <Th className="text-right">Opening</Th>
                      <Th className="text-right">Out</Th>
                      <Th className="text-right">In</Th>
                      <Th className="text-right">Closing</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {rows.map((row) => (
                      <tr
                        key={row.name}
                        className={row.name === chosen ? "bg-secondary/40" : undefined}
                      >
                        <Td>
                          <button
                            type="button"
                            onClick={() => setOpen(row.name)}
                            className="text-left font-medium hover:underline"
                          >
                            {row.account}
                          </button>
                        </Td>
                        <Td className="whitespace-nowrap text-muted-foreground">
                          {formatDate(row.period_from)} - {formatDate(row.period_to)}
                        </Td>
                        <Td className="text-right">
                          <Money value={row.opening} />
                        </Td>
                        <Td className="text-right">
                          <Money value={row.withdrawn} />
                        </Td>
                        <Td className="text-right">
                          <Money value={row.deposited} />
                        </Td>
                        <Td className="text-right">
                          <Money value={row.closing} />
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </QueryState>
        </Card>

        <Import />

        {chosen ? <Reconcile statement={chosen} /> : null}
      </div>
    </AppShell>
  );
}

/**
 * The front door. Two answers are needed and neither can be guessed: which
 * file, and which of the company's accounts it belongs to - a bank prints an
 * account *number* and AuraOS keeps accounts by name, so the import hands the
 * number back and the founder sees the two agree rather than being told they
 * do.
 *
 * The upload and the import are two steps on purpose, and the file survives a
 * failed parse rather than being cleaned up. Two reasons, and **neither is a
 * founder ruling - this was decided here**:
 *
 *   - **A rejected file is evidence.** "What did the bank actually send" is
 *     the first question after a parse fails, and deleting the file would
 *     throw away the only artefact that answers it.
 *   - **A second attempt should not start further back** than the first.
 *
 * Consistent with how template uploads already behave, which is where the
 * shape comes from rather than from any decision about this screen.
 */
function Import() {
  const accounts = useMethod<CashAccountsReport>("auraos.api.cash_accounts");
  const [account, setAccount] = useState("");
  const [busy, setBusy] = useState(false);
  const [said, setSaid] = useState<string | null>(null);
  const [failed, setFailed] = useState<unknown>(null);
  const importing = useMethodMutation<
    { name: string; account_number: string | null; lines: number },
    Record<string, unknown>
  >("auraos.api.import_bank_statement", {
    invalidate: [resultOf(STATEMENTS), resultOf(RECONCILE)],
  });

  async function chose(file: File | undefined) {
    if (!file || !account) return;
    setBusy(true);
    setSaid(null);
    setFailed(null);
    try {
      const uploaded = await uploadFile(file, { isPrivate: true });
      const out = await importing.mutateAsync({
        file_url: uploaded.file_url,
        account,
      });
      setSaid(
        `${out.name}: ${countLabel(out.lines, "line")}` +
          (out.account_number ? `, from account ${out.account_number}` : ""),
      );
    } catch (wrong) {
      setFailed(wrong);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Import a statement" subtitle="The bank's own file, as it arrived.">
      <div className="flex flex-wrap items-center gap-2 p-4">
        <select
          aria-label="Account this statement belongs to"
          value={account}
          onChange={(event) => setAccount(event.target.value)}
          className="rounded-lg border border-border bg-background px-2 py-1.5 text-sm outline-none focus:border-border-strong"
        >
          <option value="">Which account?</option>
          {(accounts.data?.accounts ?? []).map((one) => (
            <option key={one.name} value={one.name}>
              {one.account_name}
            </option>
          ))}
        </select>
        <input
          type="file"
          accept=".xlsx"
          aria-label="Statement file"
          disabled={!account || busy}
          onChange={(event) => void chose(event.target.files?.[0])}
          className="text-xs text-muted-foreground file:mr-2 file:rounded-lg file:border file:border-border file:bg-background file:px-2.5 file:py-1.5 file:text-xs disabled:opacity-50"
        />
        {busy ? <span className="text-xs text-muted-foreground">Reading...</span> : null}
        {said ? <span className="text-xs text-positive">{said}</span> : null}
      </div>
      {failed ? <ErrorState error={failed} /> : null}
    </Card>
  );
}

function Reconcile({ statement }: { statement: string }) {
  const view = useMethod<Reconciliation>(RECONCILE, { statement_name: statement });
  const invalidate = [resultOf(RECONCILE), resultOf(STATEMENTS)];
  const confirm = useMethodMutation<unknown, Record<string, unknown>>(
    "auraos.api.match_statement_line",
    { invalidate },
  );
  const undo = useMethodMutation<unknown, Record<string, unknown>>(
    "auraos.api.unmatch_statement_line",
    { invalidate },
  );

  const lines = view.data?.lines ?? [];
  const entries = view.data?.unmatched_entries ?? [];
  // Counted here because they are counts of what is on screen, not money:
  // no figure on this page is added up in the browser.
  const confirmed = lines.filter((line) => line.matched_entry).length;
  const unexplained = lines.filter((line) => !line.matched_entry && !line.unmodelled).length;

  return (
    <>
      {confirm.error ? <ErrorState error={confirm.error} /> : null}
      {undo.error ? <ErrorState error={undo.error} /> : null}

      <Card
        title="What the bank saw"
        subtitle="Every line on the statement, and what AuraOS can account for."
        action={
          <div className="flex items-center gap-3">
            <Stat label="Matched" value={String(confirmed)} />
            <Stat label="Unaccounted" value={String(unexplained)} />
          </div>
        }
      >
        <QueryState query={view} isEmpty={() => lines.length === 0} loadingRows={4}>
          {() => (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-border">
                  <tr>
                    <Th>Date</Th>
                    <Th>Bank ref</Th>
                    <Th>Description</Th>
                    <Th className="text-right">Amount</Th>
                    <Th>Reconciliation</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {lines.map((line) => (
                    <tr key={line.name}>
                      <Td className="num whitespace-nowrap text-xs text-muted-foreground">
                        {formatDate(line.effective_on)}
                      </Td>
                      <Td className="num text-xs text-muted-foreground">{line.sequence}</Td>
                      <Td className="max-w-md text-xs text-muted-foreground">{line.description}</Td>
                      <Td className="text-right">
                        <Money value={line.amount} />
                      </Td>
                      <Td>
                        {line.matched_entry ? (
                          <div className="flex items-center gap-2">
                            <Pill>{line.matched_entry}</Pill>
                            <button
                              type="button"
                              onClick={() =>
                                undo.mutate({
                                  statement_name: statement,
                                  line: line.name,
                                })
                              }
                              className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-secondary hover:text-foreground"
                            >
                              <Unlink className="size-3" strokeWidth={1.75} />
                              Unmatch
                            </button>
                          </div>
                        ) : line.unmodelled ? (
                          /* Not a failure to match: a movement this app keeps
                             no record of. The sentence is the server's. */
                          <span className="text-xs text-muted-foreground">{line.unmodelled}</span>
                        ) : line.suggestion ? (
                          <button
                            type="button"
                            disabled={confirm.isPending}
                            onClick={() =>
                              confirm.mutate({
                                statement_name: statement,
                                line: line.name,
                                entry: line.suggestion?.entry,
                              })
                            }
                            className="flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium hover:bg-secondary disabled:opacity-50"
                          >
                            <Link2 className="size-3.5" strokeWidth={1.75} />
                            {line.suggestion.confidence === "strong"
                              ? `Match ${line.suggestion.entry}`
                              : `Probably ${line.suggestion.entry}`}
                          </button>
                        ) : line.candidates.length > 1 ? (
                          /* Two candidates the server cannot tell apart. It
                             declines to pick, and so does this screen. */
                          <span className="text-xs text-muted-foreground">
                            {countLabel(line.candidates.length, "possible entry")} - open the ledger
                            to tell them apart
                          </span>
                        ) : (
                          <span className="text-xs text-ember">Nothing on file matches this</span>
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

      {/* The other half of the difference, and the half a screen like this
          usually omits: what we recorded that the bank never showed. */}
      <Card
        title="What AuraOS recorded and this statement does not show"
        subtitle="Ledger entries on this account and period that no line claims."
      >
        <QueryState
          query={view}
          isEmpty={() => entries.length === 0}
          empty={{
            title: "Every entry on this account is accounted for.",
            detail: "Nothing AuraOS recorded in this period is missing from the statement.",
          }}
          loadingRows={2}
        >
          {() => (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-border">
                  <tr>
                    <Th>Date</Th>
                    <Th>Entry</Th>
                    <Th>Flow</Th>
                    <Th>What</Th>
                    <Th className="text-right">Amount</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {entries.map((entry) => (
                    <tr key={entry.name}>
                      <Td className="num whitespace-nowrap text-xs text-muted-foreground">
                        {formatDate(entry.entry_date)}
                      </Td>
                      <Td className="num text-xs text-muted-foreground">{entry.name}</Td>
                      <Td className="text-xs">
                        <Pill>{entry.flow}</Pill>
                      </Td>
                      <Td className="text-xs text-muted-foreground">{entry.description}</Td>
                      <Td className="text-right">
                        <Money value={entry.amount} />
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </QueryState>
      </Card>
    </>
  );
}

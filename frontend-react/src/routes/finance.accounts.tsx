// What the company actually has, per account - the first screen the cash
// ledger is visible on (#101).
//
// Two reads, both derived and both already computed:
// auraos.api.cash_accounts() answers every account's balance and the total
// across them, auraos.api.cash_account_entries(account) answers one account's
// movements. Nothing on this screen adds money up, because a balance is the
// server's sum of a column it owns - a browser adding up a page of rows would
// be a second opinion about the same đồng, and the point of the ledger is that
// there is only one.
//
// Nothing on this screen writes, either. There is no field, no form and no
// endpoint behind it that could set a balance: the figure moves when a
// milestone is collected, a vendor is paid, an advance is handed over or a
// float is settled, and in no other way.
//
// Founder-only, decided by the server. The read asks for the Cash Ledger
// Entry doctype, which grants read to the founder and to no operating role, so
// a producer opening this URL gets the permission card that every refusal in
// this app renders. Nothing is hidden here to bring that about.

import { createFileRoute } from "@tanstack/react-router";
import { Landmark, Scale, Wallet } from "lucide-react";
import { useState } from "react";

import { AppShell } from "@/components/aura/AppShell";
import { FinanceTabs } from "@/components/aura/FinanceTabs";
import { Card, Money, Pill, Stat, Td, Th } from "@/components/aura/primitives";
import { ErrorState, Figure, QueryState } from "@/components/aura/states";
import { countLabel, formatDate, parseVnd, vnd } from "@/lib/format";
import { resultOf, useMethod, useMethodMutation } from "@/lib/queries";

// -- what the server sends --
//
// Pinned by the contract tests in
// auraos/auraos/doctype/cash_account/test_cash_accounts.py. Money is whole
// integer đồng, dates are ISO days, and nothing here is prose.

type CashAccount = {
  name: string;
  account_name: string;
  note: string | null;
  /** The sum of this account's ledger entries. Derived, never stored. */
  balance: number;
  count: number;
  is_default: boolean;
};

type CashAccountsReport = {
  accounts: CashAccount[];
  total: number;
  count: number;
};

type CashEntry = {
  name: string;
  entry_date: string;
  /** Signed: positive came in, negative went out. */
  amount: number;
  direction: "In" | "Out";
  flow: string;
  /** What the origin calls itself, resolved by the server from its pair. */
  source: string;
  source_doctype: string;
  source_name: string;
  job: string | null;
  job_title: string | null;
};

type CashAccountEntries = {
  account: string;
  account_name: string;
  balance: number;
  count: number;
  entries: CashEntry[];
};

export const Route = createFileRoute("/finance/accounts")({
  head: () => ({
    meta: [
      { title: "Accounts - what the company holds | AuraOS" },
      {
        name: "description",
        content:
          "Every cash account with its balance, summed from the ledger rather than typed in, and the movements behind each figure.",
      },
      { property: "og:title", content: "Accounts - AuraOS" },
      {
        property: "og:description",
        content: "Balances derived from the cash ledger, per account and in total.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: CashAccountsPage,
});

/** Money in reads calm, money out reads warm. The sign decides, nothing else. */
function toneOf(amount: number): string {
  if (amount > 0) return "text-positive";
  if (amount < 0) return "text-ember";
  return "text-muted-foreground";
}

function CashAccountsPage() {
  const [picked, setPicked] = useState<string | null>(null);

  const held = useMethod<CashAccountsReport>("auraos.api.cash_accounts");

  const accounts = held.data?.accounts ?? [];
  const selected = accounts.find((row) => row.name === picked) ?? accounts[0] ?? null;

  const movements = useMethod<CashAccountEntries>(
    "auraos.api.cash_account_entries",
    { account: selected?.name },
    { enabled: Boolean(selected) },
  );

  return (
    <AppShell
      title="Accounts"
      meta="What the company holds, summed from the ledger"
      actions={<Pill tone="ink">Derived</Pill>}
    >
      <div className="space-y-5">
        <FinanceTabs />

        <p className="flex items-start gap-2 rounded-xl border border-border bg-secondary/40 px-4 py-3 text-xs leading-relaxed text-muted-foreground">
          <Scale className="mt-0.5 size-4 shrink-0" strokeWidth={1.75} />
          <span>
            <strong className="font-medium text-foreground">Nothing here is typed in.</strong> Every
            balance is the sum of the ledger entries against that account, and an entry exists
            because money moved on a record that says so - a milestone collected, a vendor paid, an
            advance handed over, a float settled. There is no field anywhere that holds a balance.
          </span>
        </p>

        <div className="grid gap-3 sm:grid-cols-3">
          <Stat
            label="Cash on hand"
            value={
              <Figure query={held}>
                <Money value={held.data?.total ?? 0} />
              </Figure>
            }
            sub={held.isSuccess ? "Every account added up" : undefined}
          />
          <Stat
            label="Accounts"
            value={
              <Figure query={held} width="3rem">
                <span className="num">{accounts.length}</span>
              </Figure>
            }
            sub={
              held.isSuccess
                ? accounts.length === 0
                  ? "No account named yet"
                  : `${countLabel(accounts.filter((row) => row.count > 0).length, "account")} with movements`
                : undefined
            }
          />
          <Stat
            label="Movements"
            value={
              <Figure query={held} width="3rem">
                <span className="num">{held.data?.count ?? 0}</span>
              </Figure>
            }
            sub={held.isSuccess ? "Entries in the ledger" : undefined}
          />
        </div>

        <Card
          title="What each account holds"
          subtitle="A balance is the sum of the account's entries, computed on every read"
          action={
            selected ? <span className="label-caps">Showing {selected.account_name}</span> : null
          }
        >
          <QueryState
            query={held}
            loadingRows={4}
            isEmpty={() => accounts.length === 0}
            empty={{
              title: "No cash account yet.",
              detail:
                "Name where the company keeps its money - a bank account, the cash box, a wallet - and collections start landing in it. Until then there is nothing to hold and the total is zero.",
              icon: <Landmark className="size-6" strokeWidth={1.5} />,
            }}
          >
            {() => (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b border-border">
                    <tr>
                      <Th>Account</Th>
                      <Th className="text-right">Movements</Th>
                      <Th className="text-right">Balance</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {accounts.map((account) => (
                      <tr
                        key={account.name}
                        onClick={() => setPicked(account.name)}
                        className={`cursor-pointer transition-colors hover:bg-secondary/50 ${
                          selected?.name === account.name ? "bg-secondary/60" : ""
                        }`}
                      >
                        <Td>
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-medium">{account.account_name}</span>
                            {account.is_default ? <Pill>Default</Pill> : null}
                          </div>
                          {account.note ? (
                            <div className="mt-0.5 text-xs text-muted-foreground">
                              {account.note}
                            </div>
                          ) : null}
                        </Td>
                        <Td className="num text-right text-xs text-muted-foreground">
                          {account.count}
                        </Td>
                        <Td className="text-right">
                          <Money value={account.balance} className={toneOf(account.balance)} />
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="border-t border-border">
                    <tr>
                      <Td className="label-caps">Total held</Td>
                      <Td className="num text-right text-xs text-muted-foreground">
                        {held.data?.count ?? 0}
                      </Td>
                      <Td className="text-right font-semibold">
                        <Money value={held.data?.total ?? 0} />
                      </Td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </QueryState>
        </Card>

        <MoveMoney accounts={held.data?.accounts ?? []} />

        <Card
          title={selected ? `Movements in ${selected.account_name}` : "Movements"}
          subtitle="Newest first, each one showing what it came from"
          action={
            selected ? (
              <span className="text-sm">
                <Money
                  value={movements.data?.balance ?? selected.balance}
                  className={toneOf(movements.data?.balance ?? selected.balance)}
                />
              </span>
            ) : null
          }
        >
          {selected ? (
            <QueryState
              query={movements}
              loadingRows={5}
              isEmpty={(data) => data.entries.length === 0}
              empty={{
                title: "No money has moved through this account yet.",
                detail:
                  "It holds zero, which is a fact about the account rather than a problem with it. Collect a milestone, pay a vendor or hand over an advance and the movement shows up here.",
                icon: <Wallet className="size-6" strokeWidth={1.5} />,
              }}
            >
              {(data) => (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="border-b border-border">
                      <tr>
                        <Th>Date</Th>
                        <Th className="w-full">Source</Th>
                        <Th>Flow</Th>
                        <Th className="text-right">Amount</Th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {data.entries.map((entry) => (
                        <tr key={entry.name} className="hover:bg-secondary/50">
                          <Td className="num text-xs whitespace-nowrap">
                            {formatDate(entry.entry_date)}
                          </Td>
                          <Td>
                            <div className="font-medium">{entry.source}</div>
                            {entry.job ? (
                              <div className="mt-0.5 text-xs text-muted-foreground">
                                {entry.job_title ? `${entry.job_title} · ` : ""}
                                <span className="num">{entry.job}</span>
                              </div>
                            ) : null}
                          </Td>
                          <Td>
                            <Pill tone={entry.direction === "In" ? "positive" : "neutral"}>
                              {entry.flow}
                            </Pill>
                          </Td>
                          <Td className="text-right">
                            <Money value={entry.amount} sign className={toneOf(entry.amount)} />
                          </Td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="border-t border-border">
                      <tr>
                        <Td className="label-caps">Balance</Td>
                        <Td />
                        <Td className="num text-right text-xs text-muted-foreground">
                          {countLabel(data.count, "movement")}
                        </Td>
                        <Td className="text-right font-semibold">
                          <Money value={data.balance} className={toneOf(data.balance)} />
                        </Td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              )}
            </QueryState>
          ) : (
            // No account to select yet, which is only the case while the
            // accounts read is still pending, has failed, or came back empty.
            // Deferring to it keeps all three answers in one place.
            <QueryState
              query={held}
              loadingRows={5}
              isEmpty={() => true}
              empty={{
                title: "Nothing to show yet.",
                detail: "Movements appear here once the company has an account to post them to.",
                icon: <Wallet className="size-6" strokeWidth={1.5} />,
              }}
            >
              {() => null}
            </QueryState>
          )}
        </Card>
      </div>
    </AppShell>
  );
}

/**
 * Recording money that moved between two of the company's own accounts (#151).
 *
 * **The only write on this screen, and it is not a balance.** Every figure here
 * is the server's sum of a column it owns; this records the movement and the
 * sums follow. A control that set a balance would be a second opinion about
 * the same đồng.
 *
 * Both ends are named because a transfer has two, and neither defaults: the
 * server refuses a blank end as an unfinished record rather than posting to
 * the company's usual account, which would put money somewhere nobody said.
 *
 * The two balances come back with the answer, because the reason to record a
 * withdrawal is to make two figures right and the person doing it wants to see
 * them rather than be told it worked.
 */
function MoveMoney({ accounts }: { accounts: CashAccount[] }) {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const move = useMethodMutation<
    { name: string; balances: Record<string, number> },
    Record<string, unknown>
  >("auraos.api.record_cash_transfer", {
    invalidate: [
      resultOf("auraos.api.cash_accounts"),
      resultOf("auraos.api.cash_account_entries"),
      resultOf("auraos.api.cash_transfers"),
    ],
    onSuccess: () => {
      setAmount("");
      setNote("");
    },
  });

  const value = parseVnd(amount);
  // Refused by the server too - this only keeps the screen from offering a
  // button that would be rejected.
  const sound = Boolean(from && to && from !== to && value);

  return (
    <Card
      title="Move money between accounts"
      subtitle="A withdrawal to the cash box, or a top-up from it. The company holds the same total either way."
    >
      <div className="flex flex-wrap items-end gap-2 p-4">
        <select
          aria-label="Move money from"
          value={from}
          onChange={(event) => setFrom(event.target.value)}
          className="rounded-lg border border-border bg-background px-2 py-1.5 text-sm outline-none focus:border-border-strong"
        >
          <option value="">From</option>
          {accounts.map((one) => (
            <option key={one.name} value={one.name}>
              {one.account_name}
            </option>
          ))}
        </select>
        <select
          aria-label="Move money to"
          value={to}
          onChange={(event) => setTo(event.target.value)}
          className="rounded-lg border border-border bg-background px-2 py-1.5 text-sm outline-none focus:border-border-strong"
        >
          <option value="">To</option>
          {accounts
            .filter((one) => one.name !== from)
            .map((one) => (
              <option key={one.name} value={one.name}>
                {one.account_name}
              </option>
            ))}
        </select>
        <input
          aria-label="Amount to move"
          inputMode="numeric"
          placeholder="Amount"
          value={value ? vnd(value) : amount}
          onChange={(event) => setAmount(event.target.value)}
          className="num w-36 rounded-lg border border-border bg-background px-2 py-1.5 text-sm outline-none focus:border-border-strong"
        />
        <input
          aria-label="What the transfer was for"
          placeholder="What for (optional)"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          className="min-w-40 flex-1 rounded-lg border border-border bg-background px-2 py-1.5 text-sm outline-none focus:border-border-strong"
        />
        <button
          type="button"
          disabled={!sound || move.isPending}
          onClick={() =>
            move.mutate({
              from_account: from,
              to_account: to,
              amount: value,
              note: note || null,
            })
          }
          className="rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
        >
          {move.isPending ? "Moving..." : "Move"}
        </button>
      </div>
      {move.error ? <ErrorState error={move.error} /> : null}
    </Card>
  );
}

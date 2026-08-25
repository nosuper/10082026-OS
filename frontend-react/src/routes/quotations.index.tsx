// Every quote version across every deal, on real data.
//
// The app could not show this before: a quote was only reachable from inside
// the deal that produced it, so "what is out with clients right now" had to be
// assembled one deal at a time. auraos.api.quotation_list answers it in one
// call, scoped to the deals the session may list.
//
// The endpoint returns structured fields and never prose - open_count,
// download_count, last_opened_at, ISO dates - so every word on this screen is
// built here from lib/format.ts, and the status filter and the search box are
// arguments to the call rather than a filter over rows already fetched.

import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowUpRight, ExternalLink, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/aura/AppShell";
import { Card, Money, Pill, Stat, Td, Th } from "@/components/aura/primitives";
import {
  AWAITING_CLIENT,
  QUOTE_STATUSES,
  activityLabel,
  statusTone,
} from "@/components/aura/QuoteVersions";
import { Figure, QueryState } from "@/components/aura/states";
import { countLabel, formatDate } from "@/lib/format";
import { useMethod } from "@/lib/queries";

export const Route = createFileRoute("/quotations/")({
  head: () => ({
    meta: [
      { title: "Quotations - AuraOS" },
      {
        name: "description",
        content:
          "Every quote version across every deal: client, status, total and how the client engaged with it.",
      },
      { property: "og:title", content: "Quotations - AuraOS" },
      {
        property: "og:description",
        content: "Quote versions across all deals with status, totals and client open activity.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: QuotationsPage,
});

// -- what the server sends ---------------------------------------------------
//
// auraos.api.quotation_list, one row per published version. The key set is
// pinned by auraos/auraos/doctype/deal_quote/test_quotation_list.py.

export type QuotationRow = {
  name: string;
  deal: string;
  deal_title: string | null;
  company: string | null;
  client: string | null;
  version: number;
  status: string;
  total: number;
  published_on: string | null;
  sent_on: string | null;
  confirmed_on: string | null;
  url: string | null;
  open_count: number;
  download_count: number;
  last_opened_at: string | null;
};

/** The three tracking fields as the shared label reads them. */
function rowActivity(row: QuotationRow) {
  return {
    opens: row.open_count ?? 0,
    downloads: row.download_count ?? 0,
    lastOpenedAt: row.last_opened_at,
  };
}

/** The delivery dates a row carries, in the order they happen. */
function deliveryLabel(row: QuotationRow): string {
  const parts: string[] = [];
  if (row.published_on) parts.push(`published ${formatDate(row.published_on)}`);
  if (row.sent_on) parts.push(`sent ${formatDate(row.sent_on)}`);
  if (row.confirmed_on) parts.push(`signed ${formatDate(row.confirmed_on)}`);
  return parts.join(" · ") || "-";
}

function sum(rows: QuotationRow[]): number {
  return rows.reduce((total, row) => total + (row.total ?? 0), 0);
}

/** Typing should not be one request per keystroke. */
function useDebounced<T>(value: T, delay = 300): T {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setSettled(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);
  return settled;
}

function QuotationsPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const needle = useDebounced(search.trim(), 300);

  // Both controls are arguments to the call, not a filter over rows already
  // in the browser: the search looks through the client's name, which lives on
  // a third document the list never fetches. `args` are part of the cache key,
  // so going back to a filter already seen is a cache read.
  const quotes = useMethod<QuotationRow[]>("auraos.api.quotation_list", {
    status,
    search: needle,
  });

  const rows = useMemo(() => quotes.data ?? [], [quotes.data]);
  const deals = new Set(rows.map((row) => row.deal));
  const awaiting = rows.filter((row) => AWAITING_CLIENT.has(row.status));
  const signed = rows.filter((row) => row.status === "Confirmed");
  const filtering = Boolean(status || needle);

  const meta = quotes.isSuccess
    ? `${countLabel(rows.length, "version")} across ${countLabel(deals.size, "deal")}`
    : "Every quote version across every deal";

  return (
    <AppShell
      title="Quotations"
      meta={meta}
      actions={
        <Link
          to="/deals"
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          Quote from a deal <ArrowUpRight className="size-3.5" />
        </Link>
      }
    >
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <Stat
            label="Awaiting the client"
            value={
              <Figure query={quotes}>
                <Money value={sum(awaiting)} />
              </Figure>
            }
            sub={quotes.isSuccess ? countLabel(awaiting.length, "version") : undefined}
          />
          <Stat
            label="Signed"
            value={
              <Figure query={quotes}>
                <Money value={sum(signed)} />
              </Figure>
            }
            sub={quotes.isSuccess ? countLabel(signed.length, "version") : undefined}
          />
          <Stat
            label="Never opened"
            value={
              <Figure query={quotes} width="3rem">
                <span className="num">
                  {rows.filter((row) => !row.open_count && !row.download_count).length}
                </span>
              </Figure>
            }
            sub={quotes.isSuccess ? "of the versions listed" : undefined}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex min-w-[220px] flex-1 items-center gap-2 rounded-lg border border-border bg-card px-2.5 py-2">
            <Search className="size-3.5 text-muted-foreground" strokeWidth={1.75} />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search by deal or client"
              aria-label="Search quotations by deal or client"
              className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
          </div>
          {[{ key: "", label: "All" }, ...QUOTE_STATUSES.map((s) => ({ key: s, label: s }))].map(
            (option) => (
              <button
                key={option.key || "all"}
                type="button"
                onClick={() => setStatus(option.key)}
                aria-pressed={status === option.key}
                className={
                  status === option.key
                    ? "rounded-lg bg-primary px-2.5 py-2 text-xs font-medium text-primary-foreground"
                    : "rounded-lg border border-border bg-card px-2.5 py-2 text-xs text-muted-foreground hover:text-foreground"
                }
              >
                {option.label}
              </button>
            ),
          )}
        </div>

        <Card
          title="All versions"
          subtitle="Newest first, by the date it was published. A quotation is built from a deal breakdown."
        >
          <QueryState
            query={quotes}
            loadingRows={6}
            empty={{
              title: filtering ? "No quotation matches this." : "No quotation published yet.",
              detail: filtering
                ? "Try another status, or search for a different deal or client."
                : "Publishing a deal's breakdown freezes it as version 1 and it lands here.",
            }}
          >
            {(list) => (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[980px]">
                  <thead className="border-b border-border">
                    <tr>
                      <Th>Quote</Th>
                      <Th>Deal</Th>
                      <Th>Client</Th>
                      <Th>Status</Th>
                      <Th className="text-right">Total</Th>
                      <Th>Delivery</Th>
                      <Th>Client activity</Th>
                      <Th className="text-right">Link</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {list.map((row) => (
                      <tr key={row.name} className="hover:bg-secondary/40">
                        <Td className="whitespace-nowrap">
                          <Link
                            to="/quotations/$quoteRef"
                            params={{ quoteRef: row.name }}
                            className="num font-medium hover:text-ember"
                          >
                            {row.name}
                          </Link>
                          <div className="num mt-0.5 text-[11px] text-muted-foreground">
                            v{row.version}
                          </div>
                        </Td>
                        <Td>
                          <Link
                            to="/deals/$dealCode"
                            params={{ dealCode: row.deal }}
                            className="font-medium hover:text-ember"
                          >
                            {row.deal_title || row.deal}
                          </Link>
                          <div className="num mt-0.5 text-[11px] text-muted-foreground">
                            {row.deal}
                          </div>
                        </Td>
                        <Td className="text-muted-foreground">{row.client || "-"}</Td>
                        <Td>
                          <Pill tone={statusTone[row.status] ?? "neutral"}>{row.status}</Pill>
                        </Td>
                        <Td className="text-right font-semibold">
                          <Money value={row.total} />
                        </Td>
                        <Td className="text-xs text-muted-foreground">{deliveryLabel(row)}</Td>
                        <Td
                          className={
                            row.open_count || row.download_count
                              ? "text-xs text-foreground"
                              : "text-xs text-muted-foreground"
                          }
                        >
                          {activityLabel(rowActivity(row))}
                        </Td>
                        <Td className="text-right">
                          {row.url ? (
                            <a
                              href={row.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 rounded-lg border border-border px-2 py-1 text-xs text-muted-foreground hover:text-ember"
                            >
                              Open <ExternalLink className="size-3" strokeWidth={1.75} />
                            </a>
                          ) : (
                            <span className="text-xs text-muted-foreground">-</span>
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
      </div>
    </AppShell>
  );
}

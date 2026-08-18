// What the quotations screens share: how a quote's status is coloured, how the
// client's engagement reads, and the version history table itself.
//
// Two screens ask the server two different questions about the same versions -
// auraos.api.quotation_list across every deal, auraos.api.deal_quotes inside
// one - and both send counts and timestamps rather than prose. The wording of
// "3 opens · last 17/08/2026" is decided once here so the list and the detail
// view cannot phrase the same activity differently.

import { Link } from "@tanstack/react-router";
import { ExternalLink, FileDown } from "lucide-react";

import { Money, Pill, Td, Th } from "@/components/aura/primitives";
import { countLabel, formatDate } from "@/lib/format";

/** Deal Quote.status is a Select with exactly these three options. */
export const QUOTE_STATUSES = ["Published", "Sent", "Confirmed"] as const;

/** Published is a fact, Sent is in flight, Confirmed is settled. */
export const statusTone: Record<string, string> = {
  Published: "outline",
  Sent: "ember",
  Confirmed: "positive",
};

/** Published or sent, not yet signed: the client still owes an answer. */
export const AWAITING_CLIENT = new Set(["Published", "Sent"]);

/** The three tracking fields, whichever endpoint they arrived from. */
export type QuoteActivity = {
  opens: number;
  downloads: number;
  lastOpenedAt: string | null;
};

/**
 * How engagement reads. Page opens and PDF downloads are counted apart by the
 * server, because the public page's own download button would otherwise score
 * one visit as two.
 */
export function activityLabel(activity: QuoteActivity): string {
  if (!activity.opens && !activity.downloads) return "Not opened yet";
  const parts = [countLabel(activity.opens, "open")];
  if (activity.downloads) parts.push(`${countLabel(activity.downloads, "download")} of the PDF`);
  if (activity.lastOpenedAt) parts.push(`last ${formatDate(activity.lastOpenedAt)}`);
  return parts.join(" · ");
}

/** One version as auraos.api.deal_quotes sends it. */
export type QuoteVersion = {
  name: string;
  version: number;
  status: string;
  total: number;
  published_on: string | null;
  sent_on: string | null;
  confirmed_on: string | null;
  url: string | null;
  pdf_url: string | null;
  opens: number;
  downloads: number;
  last_open: string | null;
};

export function versionActivity(version: QuoteVersion): QuoteActivity {
  return {
    opens: version.opens ?? 0,
    downloads: version.downloads ?? 0,
    lastOpenedAt: version.last_open,
  };
}

/**
 * Every version of one deal's quote, newest first. Published versions never
 * change - a revision is a new version - so this is the negotiation, in order.
 */
export function VersionHistory({
  versions,
  current,
}: {
  versions: QuoteVersion[];
  current: string;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[860px]">
        <thead className="border-b border-border">
          <tr>
            <Th>Version</Th>
            <Th>Status</Th>
            <Th className="text-right">Total</Th>
            <Th>Published</Th>
            <Th>Sent</Th>
            <Th>Signed</Th>
            <Th>Client activity</Th>
            <Th className="text-right">Links</Th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {versions.map((version) => {
            const activity = versionActivity(version);
            return (
              <tr
                key={version.name}
                className={version.name === current ? "bg-secondary/60" : "hover:bg-secondary/40"}
              >
                <Td>
                  <Link
                    to="/quotations/$quoteRef"
                    params={{ quoteRef: version.name }}
                    className="num font-medium hover:text-ember"
                  >
                    v{version.version}
                  </Link>
                  <div className="num mt-0.5 text-[11px] text-muted-foreground">{version.name}</div>
                </Td>
                <Td>
                  <Pill tone={statusTone[version.status] ?? "neutral"}>{version.status}</Pill>
                </Td>
                <Td className="text-right font-semibold">
                  <Money value={version.total} />
                </Td>
                <Td className="num text-xs text-muted-foreground">
                  {formatDate(version.published_on)}
                </Td>
                <Td className="num text-xs text-muted-foreground">{formatDate(version.sent_on)}</Td>
                <Td className="num text-xs text-muted-foreground">
                  {formatDate(version.confirmed_on)}
                </Td>
                <Td
                  className={
                    activity.opens || activity.downloads
                      ? "text-xs text-foreground"
                      : "text-xs text-muted-foreground"
                  }
                >
                  {activityLabel(activity)}
                </Td>
                <Td>
                  <div className="flex items-center justify-end gap-1.5">
                    {version.url ? (
                      <a
                        href={version.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 rounded-lg border border-border px-2 py-1 text-xs text-muted-foreground hover:text-ember"
                      >
                        Link <ExternalLink className="size-3" strokeWidth={1.75} />
                      </a>
                    ) : null}
                    {version.pdf_url ? (
                      <a
                        href={version.pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 rounded-lg border border-border px-2 py-1 text-xs text-muted-foreground hover:text-ember"
                      >
                        PDF <FileDown className="size-3" strokeWidth={1.75} />
                      </a>
                    ) : null}
                  </div>
                </Td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

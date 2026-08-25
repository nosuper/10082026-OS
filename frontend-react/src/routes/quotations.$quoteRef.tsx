// One quotation: its versions and how the client engaged with it.
//
// A published version never changes - a revision is a new version - so this
// screen is a history, not an editor. The quote itself is read as a document
// (auraos Deal Quote), the sibling versions come from auraos.api.deal_quotes
// and the open log from auraos.api.quote_opens, which is the same trio the Vue
// QuotePanel has been running.
//
// Every figure and every date arrives structured and is worded here through
// lib/format.ts. Nothing on this screen computes money: the subtotal, the
// management fee, the VAT and the total are all fields the server froze into
// the version when it was published.

import { createFileRoute, Link } from "@tanstack/react-router";
import { ChevronLeft, ExternalLink, FileDown, MousePointerClick } from "lucide-react";

import { AppShell } from "@/components/aura/AppShell";
import { Card, Money, Pill, Stat, Td, Th } from "@/components/aura/primitives";
import {
  activityLabel,
  statusTone,
  versionActivity,
  VersionHistory,
  type QuoteVersion,
} from "@/components/aura/QuoteVersions";
import { Empty, ErrorState, Figure, Loading, QueryState } from "@/components/aura/states";
import { countLabel, formatDate, formatDateTime } from "@/lib/format";
import { FrappeError } from "@/lib/frappe";
import { useDoc, useMethod } from "@/lib/queries";

export const Route = createFileRoute("/quotations/$quoteRef")({
  head: () => ({
    meta: [
      { title: "Quotation - AuraOS" },
      {
        name: "description",
        content:
          "One quotation: every version with its own status and total, the public link, the PDF and every time the client opened it.",
      },
      { property: "og:title", content: "Quotation - AuraOS" },
      {
        property: "og:description",
        content: "Version history, public link, PDF and client open tracking for one quotation.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: QuotationDetailPage,
});

// -- what the server sends ---------------------------------------------------

/** The Deal Quote document, as frappe.client.get returns it. */
type QuoteDoc = {
  name: string;
  deal: string;
  version: number;
  status: string;
  title: string | null;
  client_name: string | null;
  client_contact: string | null;
  detail_level: string | null;
  notes: string | null;
  quote_mf_pct: number | null;
  vat_pct: number | null;
  subtotal: number | null;
  mf_amount: number | null;
  vat_amount: number | null;
  total: number | null;
  published_on: string | null;
  sent_on: string | null;
  confirmed_on: string | null;
};

/** One row of auraos.api.quote_opens: when the client looked, and how. */
type OpenEvent = {
  opened_on: string | null;
  via: string | null;
  ip_address: string | null;
};

function isMissing(error: unknown): boolean {
  return error instanceof FrappeError && error.kind === "notfound";
}

function QuotationDetailPage() {
  const { quoteRef } = Route.useParams();

  const quote = useDoc<QuoteDoc>("Deal Quote", quoteRef);
  const deal = quote.data?.deal;

  // The sibling versions, which is also where the public link and the PDF come
  // from: the cross-deal list carries the page URL but not the PDF one.
  const versions = useMethod<QuoteVersion[]>(
    "auraos.api.deal_quotes",
    { deal },
    { enabled: Boolean(deal) },
  );

  // Counts say how much the client looked; the log says when, which is what
  // decides the timing of the follow-up.
  const opens = useMethod<OpenEvent[]>(
    "auraos.api.quote_opens",
    { quote: quoteRef },
    { enabled: quote.isSuccess },
  );

  const doc = quote.data;
  const history = versions.data ?? [];
  const thisVersion = history.find((row) => row.name === quoteRef);
  const activity = thisVersion
    ? versionActivity(thisVersion)
    : { opens: 0, downloads: 0, lastOpenedAt: null };

  const meta = (
    <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
      <Link to="/quotations" className="inline-flex items-center hover:text-ember">
        <ChevronLeft className="size-3.5" /> Quotations
      </Link>
      <span className="num">{quoteRef}</span>
      {doc ? (
        <>
          <span aria-hidden="true">·</span>
          <Link to="/deals/$dealCode" params={{ dealCode: doc.deal }} className="hover:text-ember">
            <span className="num">{doc.deal}</span> breakdown
          </Link>
          {doc.client_name ? (
            <>
              <span aria-hidden="true">·</span>
              <span>{doc.client_name}</span>
            </>
          ) : null}
          <span aria-hidden="true">·</span>
          <span className="num">v{doc.version}</span>
          <Pill tone={statusTone[doc.status] ?? "neutral"}>{doc.status}</Pill>
        </>
      ) : null}
    </span>
  );

  return (
    <AppShell
      title={doc?.title || quoteRef}
      meta={meta}
      actions={
        thisVersion ? (
          <div className="flex items-center gap-2">
            {thisVersion.url ? (
              <a
                href={thisVersion.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-secondary"
              >
                <ExternalLink className="size-3.5" strokeWidth={1.75} /> Public link
              </a>
            ) : null}
            {thisVersion.pdf_url ? (
              <a
                href={thisVersion.pdf_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90"
              >
                <FileDown className="size-3.5" strokeWidth={1.75} /> PDF
              </a>
            ) : null}
          </div>
        ) : null
      }
    >
      {quote.isPending ? (
        <Loading rows={6} />
      ) : quote.isError ? (
        isMissing(quote.error) ? (
          <Empty
            title="No such quotation."
            detail="A quotation is published from a deal's breakdown, and it appears here once it exists."
            action={
              <Link
                to="/quotations"
                className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-secondary"
              >
                Back to quotations
              </Link>
            }
          />
        ) : (
          <ErrorState error={quote.error} onRetry={() => void quote.refetch()} />
        )
      ) : (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Stat
              label="Quoted total"
              value={<Money value={doc?.total ?? 0} />}
              sub="VAT included"
            />
            <Stat
              label="Subtotal"
              value={<Money value={doc?.subtotal ?? 0} />}
              sub="packages before fee"
            />
            <Stat
              label="Management fee"
              value={<Money value={doc?.mf_amount ?? 0} />}
              sub={doc?.quote_mf_pct ? `${doc.quote_mf_pct}% of the subtotal` : undefined}
            />
            <Stat
              label="VAT"
              value={<Money value={doc?.vat_amount ?? 0} />}
              sub={doc?.vat_pct ? `${doc.vat_pct}% output VAT` : undefined}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <Card
              className="lg:col-span-2"
              title="Client engagement"
              subtitle="Page opens and PDF downloads are counted apart, so the page's own download button is not scored twice."
            >
              <div className="grid gap-3 border-b border-border p-4 sm:grid-cols-3">
                <div>
                  <div className="label-caps">Opens</div>
                  <div className="num mt-1 text-xl font-semibold">
                    <Figure query={versions} width="3rem">
                      {activity.opens}
                    </Figure>
                  </div>
                </div>
                <div>
                  <div className="label-caps">PDF downloads</div>
                  <div className="num mt-1 text-xl font-semibold">
                    <Figure query={versions} width="3rem">
                      {activity.downloads}
                    </Figure>
                  </div>
                </div>
                <div>
                  <div className="label-caps">Last opened</div>
                  <div className="num mt-1 text-sm font-medium">
                    <Figure query={versions} width="7rem">
                      {formatDateTime(activity.lastOpenedAt)}
                    </Figure>
                  </div>
                </div>
              </div>

              <QueryState
                query={opens}
                loadingRows={3}
                empty={{
                  title: "Not opened yet.",
                  detail: "Nothing has reached the client's screen from this version's link.",
                  icon: <MousePointerClick className="size-6" strokeWidth={1.5} />,
                }}
              >
                {(events) => (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[420px]">
                      <thead className="border-b border-border">
                        <tr>
                          <Th>When</Th>
                          <Th>How</Th>
                          <Th>From</Th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {events.map((event, index) => (
                          <tr key={`${event.opened_on}-${index}`}>
                            <Td className="num">{formatDateTime(event.opened_on)}</Td>
                            <Td>
                              <Pill tone={event.via === "PDF" ? "ink" : "neutral"}>
                                {event.via === "PDF" ? "PDF download" : "Page open"}
                              </Pill>
                            </Td>
                            <Td className="num text-xs text-muted-foreground">
                              {event.ip_address || "-"}
                            </Td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </QueryState>
            </Card>

            <Card title="This version" subtitle="Frozen when it was published">
              <dl className="divide-y divide-border text-sm">
                <Field label="Detail level" value={doc?.detail_level || "-"} />
                <Field label="Client" value={doc?.client_name || "-"} />
                <Field label="Contact" value={doc?.client_contact || "-"} />
                <Field label="Published" value={formatDate(doc?.published_on)} mono />
                <Field label="Sent" value={formatDate(doc?.sent_on)} mono />
                <Field label="Signed" value={formatDate(doc?.confirmed_on)} mono />
                <Field label="Activity" value={activityLabel(activity)} />
              </dl>
              {doc?.notes ? (
                <div className="border-t border-border p-4">
                  <div className="label-caps">Note to the client</div>
                  <p className="mt-1 text-sm whitespace-pre-line">{doc.notes}</p>
                </div>
              ) : null}
            </Card>
          </div>

          <Card
            title="Every version"
            subtitle="Newest first. A published version never changes - a revision is the next version at its own link."
          >
            <QueryState
              query={versions}
              loadingRows={4}
              empty={{ title: "No version published for this deal." }}
            >
              {(rows) => (
                <>
                  <VersionHistory versions={rows} current={quoteRef} />
                  <div className="border-t border-border px-4 py-3 text-xs text-muted-foreground">
                    {countLabel(rows.length, "version")} of{" "}
                    <Link
                      to="/deals/$dealCode"
                      params={{ dealCode: doc?.deal ?? "" }}
                      className="hover:text-ember"
                    >
                      {doc?.title || doc?.deal}
                    </Link>
                  </div>
                </>
              )}
            </QueryState>
          </Card>
        </div>
      )}
    </AppShell>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-3 px-4 py-2.5">
      <dt className="label-caps shrink-0">{label}</dt>
      <dd className={mono ? "num text-right text-sm" : "text-right text-sm"}>{value}</dd>
    </div>
  );
}

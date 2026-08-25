// What the open pipeline is expected to be worth in the months ahead (#102).
//
// One read: auraos.api.weighted_pipeline_forecast(). Every figure on this page
// arrives computed - the headline, each month, each stage, each deal's own
// contribution - because the weighted total is the server's sum and not a list
// this browser multiplies out. There is nothing here that could be turned into
// a `reduce` over money, and the scenario multipliers this screen carried while
// it was a mockup are gone for exactly that reason: a browser scaling a
// projection by 1.35 is a browser inventing money.
//
// The whole screen turns on one distinction. Beside this tab sit Accounts and
// Receivables, which are facts - a balance is the ledger's own sum. This is an
// estimate multiplied by a guess. So the payload never calls anything here a
// total, a balance or an income: the weighted figure arrives as
// `weighted_projection` and the unweighted contrast as `open_pipeline`, and
// auraos.lib.forecast refuses to emit a cash-shaped name at all. That is what
// stops the next screen rendering a projection as money the studio can spend,
// and it survives somebody restyling this file, because the guarantee is in
// what the server calls the number rather than in how this page colours it.
//
// Nothing here writes a forecast. The dials that move it - a win probability
// and a lead time per stage - live in company settings, are read live on every
// call, and are shown on this page beside the figures they produce so that a
// founder reading a number can see the assumption that made it.
//
// Founder-only, decided by the server. The read asks for AuraOS Settings,
// which grants read to the founder and to no operating role, so a producer
// opening this URL gets the permission card every refusal in this app renders.
// Nothing is hidden here to bring that about.

import { createFileRoute } from "@tanstack/react-router";
import { CircleSlash, Scale, TrendingUp } from "lucide-react";
import { useState } from "react";

import { AppShell } from "@/components/aura/AppShell";
import { Bar, FinanceTabs } from "@/components/aura/FinanceTabs";
import { MonthLabel, scaleOf } from "@/components/aura/FinanceRange";
import { Card, Money, Pill, Stat, Td, Th } from "@/components/aura/primitives";
import { Figure, QueryState } from "@/components/aura/states";
import { countLabel, formatDate } from "@/lib/format";
import { useMethod } from "@/lib/queries";

// -- what the server sends --
//
// Pinned by tests/test_forecast.py (the arithmetic) and by
// auraos/auraos/doctype/auraos_settings/test_stage_forecast.py (the payload).
// Money is whole integer đồng. Note what is deliberately absent from every
// shape below: no `total`, no `balance`, no `amount`. A projection does not get
// to be called any of those, and the server will not send one that is.

/** Which number was weighted: the quote the client holds, the deal's own
 *  pricing, the client's stated budget, or nothing at all. */
export type ValueBasis = "quoted" | "priced" | "estimated" | "unvalued";

export type ForecastDeal = {
  deal: string;
  title: string | null;
  stage: string;
  /** What the deal is worth if it lands. Not weighted, not cash. */
  deal_value: number;
  value_basis: ValueBasis;
  win_probability_pct: number;
  lead_days: number;
  /** deal_value times the stage probability, rounded by the server. */
  weighted_projection: number;
  month: string;
};

export type ForecastMonth = {
  month: string;
  weighted_projection: number;
  open_pipeline: number;
  deal_count: number;
  deals: ForecastDeal[];
};

export type ForecastStage = {
  stage: string;
  win_probability_pct: number;
  lead_days: number;
  /** False means no row is stored and the house default is governing. */
  configured: boolean;
  /** Won and Lost never contribute; a won deal is already a job. */
  contributes: boolean;
  deal_count: number;
  open_pipeline: number;
  weighted_projection: number;
  month: string | null;
};

export type UnruledDeal = {
  deal: string;
  title: string | null;
  stage: string | null;
  deal_value: number;
  value_basis: ValueBasis;
};

export type ForecastReport = {
  /** What was measured, printed rather than asserted by the screen. */
  basis: string;
  as_of: string;
  /** The projection. Never money the studio has. */
  weighted_projection: number;
  /** The same deals unweighted - what lands if every one of them lands. */
  open_pipeline: number;
  deal_count: number;
  months: ForecastMonth[];
  stages: ForecastStage[];
  unruled: UnruledDeal[];
  unruled_pipeline: number;
};

export const Route = createFileRoute("/finance/forecast")({
  head: () => ({
    meta: [
      { title: "Cash forecast - weighted pipeline by stage | AuraOS" },
      {
        name: "description",
        content:
          "Each open deal weighted by the win probability of its stage, landing in the month that stage's lead time reaches. A projection, labelled apart from cash.",
      },
      { property: "og:title", content: "Cash forecast - AuraOS" },
      {
        property: "og:description",
        content: "Weighted pipeline by month and by stage, derived on every read.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ForecastPage,
});

/** How far ahead the screen asks. A choice of horizon, not of arithmetic. */
const HORIZONS = [3, 6, 12] as const;

/** What each rung of the value ladder is called where a founder reads it. */
const BASIS_LABEL: Record<ValueBasis, string> = {
  quoted: "Quoted",
  priced: "Priced",
  estimated: "Budget",
  unvalued: "No value yet",
};

const BASIS_TONE: Record<ValueBasis, string> = {
  quoted: "positive",
  priced: "ink",
  estimated: "neutral",
  unvalued: "ember",
};

function ForecastPage() {
  // The horizon the founder is looking at. A view choice and nothing more:
  // the months come back computed either way.
  const [months, setMonths] = useState<number>(6);

  const forecast = useMethod<ForecastReport>(
    "auraos.api.weighted_pipeline_forecast",
    { months },
    { retry: false },
  );

  const report = forecast.data;
  const monthRows = report?.months ?? [];
  const stageRows = report?.stages ?? [];
  const contributing = stageRows.filter((row) => row.contributes);
  // A shared scale for the bars, taken from the figures already on the page.
  // A bar width is a proportion, not a sum: no money is worked out here.
  const scale = scaleOf(monthRows.map((row) => row.open_pipeline));

  return (
    <AppShell
      title="Cash forecast"
      meta={
        report
          ? `Weighted pipeline · as of ${formatDate(report.as_of)}`
          : "Weighted pipeline by stage probability"
      }
      actions={
        <div className="flex items-center gap-2">
          <Pill tone="ember">Projection</Pill>
          <div className="flex gap-1">
            {HORIZONS.map((count) => (
              <button
                key={count}
                onClick={() => setMonths(count)}
                className={`rounded-lg border px-3 py-2 text-xs transition-colors ${
                  months === count
                    ? "border-transparent bg-primary text-primary-foreground"
                    : "border-border bg-card text-muted-foreground hover:text-foreground"
                }`}
              >
                {count} tháng
              </button>
            ))}
          </div>
        </div>
      }
    >
      <div className="space-y-5">
        <FinanceTabs />

        <p className="flex items-start gap-2 rounded-xl border border-ember/30 bg-ember-soft/40 px-4 py-3 text-xs leading-relaxed text-muted-foreground">
          <Scale className="mt-0.5 size-4 shrink-0 text-ember" strokeWidth={1.75} />
          <span>
            <strong className="font-medium text-foreground">
              This is not money the studio has.
            </strong>{" "}
            Every figure below is{" "}
            {report?.basis ??
              "open deal value weighted by the win probability of its stage - a projection, not money held"}
            . Accounts and Receivables next door are facts, provable against the ledger; this one is
            an estimate multiplied by a probability, and it moves the moment a deal moves stage or
            the founder moves a dial.
          </span>
        </p>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Stat
            label="Weighted projection"
            value={
              <Figure query={forecast}>
                <Money value={report?.weighted_projection ?? 0} />
              </Figure>
            }
            sub={forecast.isSuccess ? `Across the next ${countLabel(months, "month")}` : undefined}
          />
          <Stat
            label="Open pipeline · unweighted"
            value={
              <Figure query={forecast}>
                <Money value={report?.open_pipeline ?? 0} />
              </Figure>
            }
            sub={forecast.isSuccess ? "If every open deal landed in full" : undefined}
          />
          <Stat
            label="Open deals"
            value={
              <Figure query={forecast} width="3rem">
                <span className="num">{report?.deal_count ?? 0}</span>
              </Figure>
            }
            sub={
              forecast.isSuccess
                ? `${countLabel(contributing.filter((row) => row.deal_count > 0).length, "stage")} with deals in it`
                : undefined
            }
          />
          <Stat
            label="Best month ahead"
            value={
              <Figure query={forecast}>
                <Money value={bestMonth(monthRows)?.weighted_projection ?? 0} />
              </Figure>
            }
            sub={
              forecast.isSuccess
                ? bestMonth(monthRows)
                  ? bestMonth(monthRows)?.month
                  : "Nothing projected yet"
                : undefined
            }
          />
        </div>

        <Card
          title="Expected by month"
          subtitle="Lead time is counted from today, so the spread is the shape of the stage mix - two deals at the same stage always land in the same month, whatever their own timing"
          action={<span className="label-caps">Weighted, not committed</span>}
        >
          <QueryState
            query={forecast}
            loadingRows={6}
            isEmpty={(data) => data.months.length === 0}
            empty={{
              title: "No months to project.",
              detail: "Ask for a longer horizon and the months appear.",
              icon: <TrendingUp className="size-6" strokeWidth={1.5} />,
            }}
          >
            {(data) => (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b border-border">
                    <tr>
                      <Th>Month</Th>
                      <Th className="w-full">Share of the horizon</Th>
                      <Th className="text-right">Deals</Th>
                      <Th className="text-right">Open pipeline</Th>
                      <Th className="text-right">Weighted projection</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data.months.map((row) => (
                      <tr key={row.month} className="hover:bg-secondary/50">
                        <Td className="font-medium">
                          <MonthLabel month={row.month} />
                        </Td>
                        <Td>
                          <div className="space-y-1">
                            <Bar value={row.open_pipeline} max={scale} tone="muted" />
                            <Bar value={row.weighted_projection} max={scale} tone="ink" />
                          </div>
                        </Td>
                        <Td className="num text-right text-xs text-muted-foreground">
                          {row.deal_count}
                        </Td>
                        <Td className="text-right text-muted-foreground">
                          <Money value={row.open_pipeline} />
                        </Td>
                        <Td className="text-right font-medium">
                          <Money value={row.weighted_projection} />
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="border-t border-border">
                    <tr>
                      <Td className="label-caps">Horizon</Td>
                      <Td>
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          <span className="inline-flex items-center gap-1.5">
                            <span className="size-2 rounded-full bg-border-strong" /> Open pipeline
                          </span>
                          <span className="inline-flex items-center gap-1.5">
                            <span className="size-2 rounded-full bg-primary" /> Weighted projection
                          </span>
                        </div>
                      </Td>
                      <Td className="num text-right text-xs text-muted-foreground">
                        {data.deal_count}
                      </Td>
                      <Td className="text-right text-muted-foreground">
                        <Money value={data.open_pipeline} />
                      </Td>
                      <Td className="text-right font-semibold">
                        <Money value={data.weighted_projection} />
                      </Td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </QueryState>
        </Card>

        <Card
          title="The dials behind the figure"
          subtitle="Win probability and lead time per stage, read live from company settings on every load"
          action={
            <a
              href="/aura-next/settings"
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Edit in settings
            </a>
          }
        >
          <QueryState query={forecast} loadingRows={7}>
            {(data) => (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b border-border">
                    <tr>
                      <Th>Stage</Th>
                      <Th className="text-right">Win probability</Th>
                      <Th className="text-right">Lead time</Th>
                      <Th>Bills in</Th>
                      <Th className="text-right">Deals</Th>
                      <Th className="text-right">Open pipeline</Th>
                      <Th className="text-right">Weighted projection</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data.stages.map((row) => (
                      <tr
                        key={row.stage}
                        className={row.contributes ? "hover:bg-secondary/50" : "opacity-55"}
                      >
                        <Td>
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-medium">{row.stage}</span>
                            {row.configured ? null : <Pill>House default</Pill>}
                            {row.contributes ? null : <Pill tone="outline">Not pipeline</Pill>}
                          </div>
                        </Td>
                        <Td className="num text-right">{row.win_probability_pct}%</Td>
                        <Td className="num text-right text-muted-foreground">
                          {countLabel(row.lead_days, "day")}
                        </Td>
                        <Td className="text-muted-foreground">
                          {row.month ? <MonthLabel month={row.month} /> : "-"}
                        </Td>
                        <Td className="num text-right text-xs text-muted-foreground">
                          {row.deal_count}
                        </Td>
                        <Td className="text-right text-muted-foreground">
                          <Money value={row.open_pipeline} />
                        </Td>
                        <Td className="text-right font-medium">
                          <Money value={row.weighted_projection} />
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </QueryState>
        </Card>

        <Card
          title="Every deal in the figure"
          subtitle="The value weighted is the best number written down for the deal, and the row says which one"
        >
          <QueryState
            query={forecast}
            loadingRows={5}
            isEmpty={(data) => data.deal_count === 0}
            empty={{
              title: "No open deals to project.",
              detail:
                "The forecast is zero, which is a fact about the pipeline rather than a problem with the screen. Open a deal and it appears here weighted by whatever stage it sits at.",
              icon: <CircleSlash className="size-6" strokeWidth={1.5} />,
            }}
          >
            {(data) => (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b border-border">
                    <tr>
                      <Th className="w-full">Deal</Th>
                      <Th>Stage</Th>
                      <Th>Value from</Th>
                      <Th className="text-right">Deal value</Th>
                      <Th className="text-right">Win %</Th>
                      <Th>Bills in</Th>
                      <Th className="text-right">Weighted projection</Th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data.months.flatMap((month) =>
                      month.deals.map((row) => (
                        <tr key={row.deal} className="hover:bg-secondary/50">
                          <Td>
                            <div className="font-medium">{row.title || row.deal}</div>
                            <div className="num text-[11px] text-muted-foreground">{row.deal}</div>
                          </Td>
                          <Td className="text-muted-foreground">{row.stage}</Td>
                          <Td>
                            <Pill tone={BASIS_TONE[row.value_basis]}>
                              {BASIS_LABEL[row.value_basis]}
                            </Pill>
                          </Td>
                          <Td className="text-right text-muted-foreground">
                            <Money value={row.deal_value} />
                          </Td>
                          <Td className="num text-right">{row.win_probability_pct}%</Td>
                          <Td className="text-muted-foreground">
                            <MonthLabel month={row.month} />
                          </Td>
                          <Td className="text-right font-medium">
                            <Money value={row.weighted_projection} />
                          </Td>
                        </tr>
                      )),
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </QueryState>
        </Card>

        {/* Deals no stage rule reaches. Carried by the server rather than
            dropped: money the projection cannot speak for is still money, and
            a founder is owed the fact that it is missing from the figure
            above. Absent entirely on a healthy site. */}
        {report && report.unruled.length > 0 ? (
          <Card
            title="Outside the forecast"
            subtitle="These deals sit at a stage with no rule, so nothing above counts them"
            action={
              <span className="text-sm">
                <Money value={report.unruled_pipeline} className="text-ember" />
              </span>
            }
          >
            <ul className="divide-y divide-border">
              {report.unruled.map((row) => (
                <li key={row.deal} className="flex flex-wrap items-center gap-3 px-4 py-3 text-sm">
                  <span className="min-w-0 flex-1 truncate font-medium">
                    {row.title || row.deal}
                  </span>
                  <Pill tone="ember">{row.stage || "No stage"}</Pill>
                  <Money value={row.deal_value} className="text-xs" />
                </li>
              ))}
            </ul>
          </Card>
        ) : null}
      </div>
    </AppShell>
  );
}

/**
 * The fattest month ahead. A pick out of the server's own rows, never a
 * calculation: nothing here adds, multiplies or scales money.
 */
function bestMonth(months: ForecastMonth[]): ForecastMonth | null {
  let best: ForecastMonth | null = null;
  for (const month of months) {
    if (
      month.weighted_projection > 0 &&
      (!best || month.weighted_projection > best.weighted_projection)
    ) {
      best = month;
    }
  }
  return best;
}

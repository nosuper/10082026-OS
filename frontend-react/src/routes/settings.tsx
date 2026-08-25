// Company settings, on real data.
//
// The numbers the app enforces - margin floor, the two nudges, the tier
// boundaries, the positioning dials and the company block printed on every
// quote - edited by the founder and by nobody else. The endpoints and the
// per-section saves are the ones the Vue screen has been running in production
// (frontend/src/pages/SettingsPage.vue); nothing new is asked of the backend.
//
// Two rules shape this file:
//
//  1. The founder gate is load-bearing. Any settings read refused by the server
//     replaces the whole body with one sentence, so a producer session never
//     sees a settings field - not even an empty or a disabled one. The server
//     refuses the data anyway; this is the last line of defence, not the only
//     one.
//  2. Each section saves on its own and confirms on its own. There is
//     deliberately no page-level "Save changes": a founder fixing the silence
//     nudge should not also be writing the letterhead they happened to click in.

import { createFileRoute } from "@tanstack/react-router";
import type { QueryKey } from "@tanstack/react-query";
import { LockKeyhole, Upload } from "lucide-react";
import { useState, type ChangeEvent, type ReactNode } from "react";

import { AppShell } from "@/components/aura/AppShell";
import { VocabularyLists } from "@/components/aura/VocabularyLists";
import { Card, Pill, Td, Th } from "@/components/aura/primitives";
import { ErrorState, QueryStates } from "@/components/aura/states";
import { FrappeError, uploadFile } from "@/lib/frappe";
import { parseVnd, vnd } from "@/lib/format";
import { listsOf, resultOf, useMethod, useMethodMutation } from "@/lib/queries";
import { FOUNDER_PROBE } from "@/lib/session";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings - company defaults | AuraOS" },
      {
        name: "description",
        content:
          "Founder-only defaults: margin floor, quote and payment nudges, tier thresholds, positioning targets and the company identity printed on quotes.",
      },
      { property: "og:title", content: "Settings - company defaults" },
      {
        property: "og:description",
        content: "The numbers AuraOS enforces, editable by the founder alone.",
      },
    ],
  }),
  component: SettingsPage,
});

// -- what the server sends --

type TierThresholds = { tier2: number; tier3: number };

type MixKey = "cash" | "bridge" | "brand";

type ProjectTypeRow = { name: string; is_positioning: number };

type PositioningRules = {
  mix: Record<MixKey, number>;
  project_types: ProjectTypeRow[];
};

/**
 * One deal stage's forecast dials (#102). `configured` is the load-bearing
 * field: AuraOS Settings is a Single, so a row nobody has written reads back as
 * 0 rather than as nothing - and Lost is legitimately 0. Only whether a row
 * exists can tell the founder's decision from silence, so the server sends that
 * fact rather than leaving this screen to guess it from a zero.
 */
type StageForecastRule = {
  stage: string;
  win_probability_pct: number;
  lead_days: number;
  configured: boolean;
  /** Won and Lost carry dials but never contribute: a won deal is a job. */
  contributes: boolean;
};

type StageForecastRules = { stages: StageForecastRule[] };

/** The company block, keyed by the field names auraos.lib.quote.COMPANY_FIELDS
 *  accepts. Anything not on that list is refused by name on save. */
type CompanyIdentity = Record<string, string | null>;

const MIX_KEYS: MixKey[] = ["cash", "bridge", "brand"];

const MIX_LABEL: Record<MixKey, string> = {
  cash: "Cash",
  bridge: "Bridge",
  brand: "Brand",
};

/**
 * Mirrors auraos.lib.quote.COMPANY_FIELDS minus the logo, which has its own
 * uploader. Drift is caught in one direction only: a field named here and not
 * there is refused by name on save, but a field added there and not here is
 * simply not editable from this screen.
 *
 * `numeric` is presentation only - digit fields read in the ledger face. The
 * Vietnamese fields (company name, address, bank, signatory) deliberately stay
 * in the text face, which is the only one with the diacritics.
 */
const IDENTITY_FIELDS: Array<{
  name: string;
  label: string;
  numeric?: boolean;
  placeholder?: string;
}> = [
  { name: "company_name", label: "Company name" },
  { name: "tax_code", label: "Tax code", numeric: true },
  { name: "address", label: "Address" },
  { name: "phone", label: "Phone", numeric: true },
  { name: "email", label: "Email" },
  { name: "website", label: "Website" },
  { name: "bank_name", label: "Bank" },
  { name: "bank_account_number", label: "Bank account number", numeric: true },
  { name: "bank_account_name", label: "Bank account holder" },
  {
    name: "signatory_name",
    label: "Signatory name",
    placeholder: "Printed on the PDF signature block",
  },
  { name: "signatory_title", label: "Signatory title" },
];

const inputShell =
  "flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 focus-within:border-ember";

const inputField =
  "w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground/60";

function SettingsPage() {
  // Six founder-only reads. `retry: false` on every one of them: a refusal is
  // the answer, and asking three times only delays the denied state.
  const probe = { retry: false } as const;

  // Same query key as the founder probe in SessionProvider, so the floor is a
  // cache read rather than a seventh request.
  const floor = useMethod<number>(FOUNDER_PROBE, undefined, {
    retry: false,
    staleTime: Number.POSITIVE_INFINITY,
  });
  const silence = useMethod<number>("auraos.api.get_quote_silence_days", undefined, probe);
  const terms = useMethod<number>("auraos.api.get_payment_terms_days", undefined, probe);
  const tiers = useMethod<TierThresholds>("auraos.api.get_tier_thresholds", undefined, probe);
  const positioning = useMethod<PositioningRules>(
    "auraos.api.get_positioning_rules",
    undefined,
    probe,
  );
  const company = useMethod<CompanyIdentity>("auraos.api.get_company_identity", undefined, probe);
  const forecast = useMethod<StageForecastRules>(
    "auraos.api.stage_forecast_rules",
    undefined,
    probe,
  );

  const queries = [floor, silence, terms, tiers, positioning, company, forecast];

  // The gate. One refused read is enough: the settings single is readable as a
  // whole or not at all, so a partial screen would be a lie.
  const refused = queries.some((query) => query.error?.kind === "permission");

  return (
    <AppShell
      title="Company settings"
      meta="Studio-wide defaults - deals, quotes and the jobs board read these live"
    >
      {/* Outside the founder gate, deliberately. T3.5 stopped Settings being a
          founder-only door: a producer manages deal sources here while the
          margin floor below stays out of reach. Putting this inside the gate
          would send a producer to a page that refuses them wholesale, which is
          the screen T3.5 exists to replace. Each list decides for itself
          whether this session may edit it. */}
      <div className="mb-4">
        <VocabularyLists />
      </div>

      {refused ? (
        <Card>
          <div className="flex items-start gap-2 p-4 text-sm text-muted-foreground">
            <LockKeyhole className="mt-0.5 size-4 shrink-0" strokeWidth={1.75} aria-hidden="true" />
            <span>
              The lists above are yours to manage. The rest of company settings - the margin floor,
              tiers, positioning and the company identity - is the founder's.
            </span>
          </div>
        </Card>
      ) : (
        <QueryStates queries={queries} loadingRows={6}>
          {() => (
            <div className="space-y-4">
              <div className="grid gap-4 lg:grid-cols-3">
                <NumberSetting
                  title="Global margin floor"
                  unit="%"
                  step="0.5"
                  initial={floor.data ?? 0}
                  method="auraos.api.set_margin_floor"
                  argName="pct"
                  invalidate={[resultOf(FOUNDER_PROBE)]}
                  hint="Quotes whose margin falls below this warn every role, without revealing where the number comes from. 0 turns the warning off."
                />
                <NumberSetting
                  title="Quote silence nudge"
                  unit="days"
                  step="1"
                  initial={silence.data ?? 0}
                  method="auraos.api.set_quote_silence_days"
                  argName="days"
                  invalidate={[
                    resultOf("auraos.api.get_quote_silence_days"),
                    resultOf("auraos.api.silent_quote_deals"),
                  ]}
                  hint="A sent quote with no reply after this many days is flagged on the deal board. 0 turns the nudge off."
                />
                <NumberSetting
                  title="Payment terms"
                  unit="days"
                  step="1"
                  initial={terms.data ?? 0}
                  method="auraos.api.set_payment_terms_days"
                  argName="days"
                  invalidate={[
                    resultOf("auraos.api.get_payment_terms_days"),
                    resultOf("auraos.api.overdue_milestones"),
                  ]}
                  hint="A payment milestone still uncollected this many days after it falls due is flagged on the jobs board. 0 turns the nudge off."
                />
              </div>

              <div className="grid gap-4 lg:grid-cols-3">
                <TierCard initial={tiers.data ?? { tier2: 0, tier3: 0 }} />
                <PositioningCard
                  initial={
                    positioning.data ?? { mix: { cash: 0, bridge: 0, brand: 0 }, project_types: [] }
                  }
                />
              </div>

              <StageForecastCard rules={forecast.data?.stages ?? []} />

              <CompanyCard initial={company.data ?? {}} />
            </div>
          )}
        </QueryStates>
      )}
    </AppShell>
  );
}

/**
 * The save row every section ends with: its own button, its own confirmation,
 * its own failure. Nothing here knows about any other section.
 */
function SaveRow({
  pending,
  saved,
  error,
  label = "Save",
}: {
  pending: boolean;
  saved: boolean;
  error: unknown;
  label?: string | undefined;
}) {
  return (
    <div className="mt-3 border-t border-border pt-3">
      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={pending}
          className="rounded-lg bg-ember px-3 py-1.5 text-xs font-medium text-ember-foreground transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          {pending ? "Saving..." : label}
        </button>
        {saved ? <span className="text-xs text-positive">Saved.</span> : null}
      </div>
      {error ? <ErrorState error={error} className="px-0 py-2" /> : null}
    </div>
  );
}

function Eyebrow({ children }: { children: ReactNode }) {
  return <div className="label-caps">{children}</div>;
}

/**
 * One number, one endpoint, one save: the margin floor and the two nudges are
 * the same card three times over, differing only in the argument name and the
 * unit. A stored 0 is a deliberate off switch, so the card says so rather than
 * leaving the reader to interpret a zero.
 */
function NumberSetting({
  title,
  unit,
  hint,
  step,
  initial,
  method,
  argName,
  invalidate,
}: {
  title: string;
  unit: string;
  hint: string;
  step: string;
  initial: number;
  method: string;
  argName: "pct" | "days";
  invalidate: QueryKey[];
}) {
  const [draft, setDraft] = useState(String(initial ?? 0));
  const [saved, setSaved] = useState(false);

  const save = useMethodMutation<number, Record<string, number>>(method, {
    invalidate,
    onSuccess: (stored) => {
      setDraft(String(stored ?? 0));
      setSaved(true);
    },
  });

  const value = Number(draft) || 0;

  return (
    <Card title={title} action={value ? null : <Pill tone="ember">currently off</Pill>}>
      <form
        className="p-4"
        onSubmit={(event) => {
          event.preventDefault();
          setSaved(false);
          save.mutate({ [argName]: value });
        }}
      >
        <div className={inputShell}>
          <input
            type="number"
            min="0"
            step={step}
            value={draft}
            onChange={(event) => {
              setDraft(event.target.value);
              setSaved(false);
            }}
            className={`num ${inputField}`}
          />
          <span className="shrink-0 text-xs text-muted-foreground">{unit}</span>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{hint}</p>
        <SaveRow pending={save.isPending} saved={saved} error={save.isError ? save.error : null} />
      </form>
    </Card>
  );
}

/** The two tier boundaries, as money. Saved together because the server writes
 *  them in one call and a half-applied pair would misclassify deals. */
function TierCard({ initial }: { initial: TierThresholds }) {
  const [tier2, setTier2] = useState(initial.tier2 ?? 0);
  const [tier3, setTier3] = useState(initial.tier3 ?? 0);
  const [saved, setSaved] = useState(false);

  const save = useMethodMutation<TierThresholds, { tier2: number; tier3: number }>(
    "auraos.api.set_tier_thresholds",
    {
      invalidate: [resultOf("auraos.api.get_tier_thresholds"), resultOf("auraos.api.preview_tier")],
      onSuccess: (stored) => {
        setTier2(stored.tier2);
        setTier3(stored.tier3);
        setSaved(true);
      },
    },
  );

  return (
    <Card title="Tier thresholds" subtitle="Playbook §2.2">
      <form
        className="p-4"
        onSubmit={(event) => {
          event.preventDefault();
          setSaved(false);
          save.mutate({ tier2, tier3 });
        }}
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
          <MoneyField
            label="Tier 2 from"
            value={tier2}
            onChange={(next) => {
              setTier2(next);
              setSaved(false);
            }}
          />
          <MoneyField
            label="Tier 3 from"
            value={tier3}
            onChange={(next) => {
              setTier3(next);
              setSaved(false);
            }}
          />
        </div>
        <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
          Every deal&apos;s tier is derived: Brand positioning, or a positioning-segment job type,
          means Tier 3 whatever it pays; otherwise Tier 2 from the first number, Tier 3 from the
          second. Hand-setting a tier on a deal pins it against the rules.
        </p>
        <SaveRow pending={save.isPending} saved={saved} error={save.isError ? save.error : null} />
      </form>
    </Card>
  );
}

function MoneyField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (next: number) => void;
}) {
  return (
    <label className="block">
      <Eyebrow>{label}</Eyebrow>
      <div className={`mt-1.5 ${inputShell}`}>
        <input
          inputMode="numeric"
          value={value ? vnd(value) : ""}
          placeholder="0"
          onChange={(event) => onChange(parseVnd(event.target.value))}
          className={`num text-right ${inputField}`}
        />
        <span className="shrink-0 text-xs text-muted-foreground">VND</span>
      </div>
    </label>
  );
}

/**
 * The mix targets and the positioning-segment job types share one save, because
 * the server writes them in a single call. The sum is shown live and warns
 * whenever it is not 100: the targets are an allocation lens, so 105% is not a
 * rounding quirk, it is a mistake worth seeing before saving.
 */
function PositioningCard({ initial }: { initial: PositioningRules }) {
  const [mix, setMix] = useState<Record<MixKey, string>>({
    cash: String(initial.mix.cash ?? 0),
    bridge: String(initial.mix.bridge ?? 0),
    brand: String(initial.mix.brand ?? 0),
  });
  const [flags, setFlags] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(initial.project_types.map((row) => [row.name, Boolean(row.is_positioning)])),
  );
  const [saved, setSaved] = useState(false);

  const apply = (stored: PositioningRules) => {
    setMix({
      cash: String(stored.mix.cash ?? 0),
      bridge: String(stored.mix.bridge ?? 0),
      brand: String(stored.mix.brand ?? 0),
    });
    setFlags(
      Object.fromEntries(
        stored.project_types.map((row) => [row.name, Boolean(row.is_positioning)]),
      ),
    );
  };

  const save = useMethodMutation<
    PositioningRules,
    { cash: number; bridge: number; brand: number; positioning_types: string[] }
  >("auraos.api.set_positioning_rules", {
    invalidate: [
      resultOf("auraos.api.get_positioning_rules"),
      resultOf("auraos.api.classification_hints"),
      resultOf("auraos.api.preview_tier"),
      listsOf("Project Type"),
    ],
    onSuccess: (stored) => {
      apply(stored);
      setSaved(true);
    },
  });

  const numeric = (key: MixKey) => Number(mix[key]) || 0;
  const sum = MIX_KEYS.reduce((total, key) => total + numeric(key), 0);
  const balanced = sum === 100;
  const types = initial.project_types;

  return (
    <Card className="lg:col-span-2" title="Positioning mix targets" subtitle="Playbook §6.1">
      <form
        className="p-4"
        onSubmit={(event) => {
          event.preventDefault();
          setSaved(false);
          save.mutate({
            cash: numeric("cash"),
            bridge: numeric("bridge"),
            brand: numeric("brand"),
            positioning_types: types.filter((row) => flags[row.name]).map((row) => row.name),
          });
        }}
      >
        <div className="grid gap-3 sm:grid-cols-3">
          {MIX_KEYS.map((key) => (
            <label key={key} className="block">
              <Eyebrow>{MIX_LABEL[key]}</Eyebrow>
              <div className={`mt-1.5 ${inputShell}`}>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="5"
                  value={mix[key]}
                  onChange={(event) => {
                    const next = event.target.value;
                    setMix((current) => ({ ...current, [key]: next }));
                    setSaved(false);
                  }}
                  className={`num text-right ${inputField}`}
                />
                <span className="shrink-0 text-xs text-muted-foreground">%</span>
              </div>
            </label>
          ))}
        </div>

        <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span
            className={`text-xs ${balanced ? "text-muted-foreground" : "font-medium text-ember"}`}
            role={balanced ? undefined : "status"}
          >
            sums to <span className="num">{sum}%</span>
            {balanced ? null : ", not 100"}
          </span>
          <p className="min-w-0 flex-1 text-xs leading-relaxed text-muted-foreground">
            The cash / bridge / brand allocation lens - tune it as the company moves phases. The
            deal form reads these live. The{" "}
            <a
              href="/aura-next/documents/library"
              target="_blank"
              rel="noopener noreferrer"
              className="text-ember underline underline-offset-2"
            >
              classification SOP
            </a>{" "}
            points here for the numbers rather than repeating them, so it cannot fall out of date
            with this screen.
          </p>
        </div>

        <div className="mt-3 border-t border-border pt-3">
          <Eyebrow>Positioning-segment job types</Eyebrow>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            Deals of these types derive Tier 3 whatever they pay, even when their positioning is
            left empty.
          </p>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2">
            {types.map((row) => (
              <label key={row.name} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={Boolean(flags[row.name])}
                  onChange={(event) => {
                    const next = event.target.checked;
                    setFlags((current) => ({ ...current, [row.name]: next }));
                    setSaved(false);
                  }}
                  className="size-3.5 rounded border-border accent-ember"
                />
                {row.name}
              </label>
            ))}
            {types.length === 0 ? (
              <span className="text-xs text-muted-foreground">No project types yet.</span>
            ) : null}
          </div>
        </div>

        <SaveRow pending={save.isPending} saved={saved} error={save.isError ? save.error : null} />
      </form>
    </Card>
  );
}

/**
 * The logo, uploaded public on purpose: a client with no account has to load it
 * off the quote page, and a private file would 404 there.
 *
 * This is the one request on the screen that lib/frappe.ts cannot make - it is
 * multipart, not JSON - so it is written out here rather than widening the
 * shared transport for a single caller. It still carries the CSRF token from
 * the same place and still fails as a FrappeError, so <ErrorState> reads it
 * exactly like any other failure.
 */
async function uploadLogoFile(file: File): Promise<string> {
  // Public: the logo is printed on quotes a client opens without a session.
  const uploaded = await uploadFile(file, { isPrivate: false });
  return uploaded.file_url ?? "";
}

function CompanyCard({ initial }: { initial: CompanyIdentity }) {
  const [values, setValues] = useState<CompanyIdentity>(() => ({ ...initial }));
  const [saved, setSaved] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<unknown>(null);

  const save = useMethodMutation<CompanyIdentity, { values: CompanyIdentity }>(
    "auraos.api.set_company_identity",
    {
      invalidate: [resultOf("auraos.api.get_company_identity")],
      onSuccess: (stored) => {
        setValues({ ...stored });
        setSaved(true);
      },
    },
  );

  const logo = values["logo"] ?? "";

  const set = (field: string, next: string | null) => {
    setValues((current) => ({ ...current, [field]: next }));
    setSaved(false);
  };

  async function pickLogo(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    // Cleared so picking the same file twice still fires a change.
    event.target.value = "";
    if (!file) return;
    setUploadError(null);
    setUploading(true);
    try {
      set("logo", await uploadLogoFile(file));
    } catch (error) {
      setUploadError(error);
    } finally {
      setUploading(false);
    }
  }

  return (
    <Card title="Company identity" subtitle="Printed on every quote page and PDF">
      <form
        className="p-4"
        onSubmit={(event) => {
          event.preventDefault();
          setSaved(false);
          save.mutate({ values });
        }}
      >
        <p className="text-xs leading-relaxed text-muted-foreground">
          These render live - changing one updates quotes already sent, without making a new
          version. An empty field prints nothing at all.
        </p>

        <div className="mt-3 flex flex-wrap items-center gap-3">
          {logo ? (
            <img
              src={logo}
              alt="Company logo"
              className="max-h-12 max-w-40 rounded-lg border border-border bg-background p-1"
            />
          ) : null}

          <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-secondary">
            <Upload className="size-3.5" strokeWidth={1.75} aria-hidden="true" />
            {uploading ? "Uploading..." : logo ? "Replace logo" : "Upload logo"}
            <input
              type="file"
              accept="image/*"
              className="sr-only"
              disabled={uploading}
              onChange={(event) => void pickLogo(event)}
            />
          </label>

          {logo ? (
            <button
              type="button"
              onClick={() => set("logo", null)}
              className="text-xs text-muted-foreground underline underline-offset-2 hover:text-ember"
            >
              Remove
            </button>
          ) : null}

          <p className="min-w-0 flex-1 text-xs leading-relaxed text-muted-foreground">
            Uploaded public, because a client with no account has to be able to load it. The logo is
            stored with the fields below when you save.
          </p>
        </div>

        {uploadError ? <ErrorState error={uploadError} className="px-0 py-2" /> : null}

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {IDENTITY_FIELDS.map((field) => (
            <label key={field.name} className="block">
              <Eyebrow>{field.label}</Eyebrow>
              <div className={`mt-1.5 ${inputShell}`}>
                <input
                  value={values[field.name] ?? ""}
                  placeholder={field.placeholder ?? ""}
                  onChange={(event) => set(field.name, event.target.value)}
                  className={field.numeric ? `num ${inputField}` : inputField}
                />
              </div>
            </label>
          ))}
        </div>

        <SaveRow pending={save.isPending} saved={saved} error={save.isError ? save.error : null} />
      </form>
    </Card>
  );
}

/**
 * The cash forecast dials (#102): a win probability and a lead time per deal
 * stage, the two numbers that turn an open pipeline into an expected month.
 *
 * Saved as one table in one call. The founder reads the seven stages together
 * and reasons about them together - Quote Sent has to be worth more than
 * Breakdown - and a half-applied table would forecast with one stage's old
 * probability and another's new one.
 *
 * A stage with no stored row is governed by the house default in
 * auraos/lib/forecast.py and is marked as such, rather than showing the 0 an
 * unwritten field on a Single actually reads back as. Saving writes every row,
 * including a probability of 0, which is how a deliberate zero (Lost) stops
 * being indistinguishable from silence.
 *
 * Nothing here stores a forecast figure. The projection is derived from these
 * dials on every read, so moving one moves the number on the Forecast tab
 * immediately - there is no cached total in between to go stale.
 */
function StageForecastCard({ rules }: { rules: StageForecastRule[] }) {
  const [draft, setDraft] = useState<StageForecastRule[]>(rules);
  const [saved, setSaved] = useState(false);

  const save = useMethodMutation<StageForecastRules, { rules: StageForecastRule[] }>(
    "auraos.api.set_stage_forecast_rules",
    {
      invalidate: [
        resultOf("auraos.api.stage_forecast_rules"),
        resultOf("auraos.api.weighted_pipeline_forecast"),
      ],
      onSuccess: (stored) => {
        setDraft(stored.stages);
        setSaved(true);
      },
    },
  );

  const set = (stage: string, field: "win_probability_pct" | "lead_days", next: number) => {
    setDraft((rows) => rows.map((row) => (row.stage === stage ? { ...row, [field]: next } : row)));
    setSaved(false);
  };

  const unconfigured = draft.filter((row) => !row.configured).length;

  return (
    <Card
      title="Cash forecast dials"
      subtitle="What each stage is worth, and how far ahead it bills"
      action={unconfigured ? <Pill tone="ember">{unconfigured} on house defaults</Pill> : null}
    >
      <form
        className="p-4"
        onSubmit={(event) => {
          event.preventDefault();
          setSaved(false);
          save.mutate({
            rules: draft.map((row) => ({
              ...row,
              win_probability_pct: Number(row.win_probability_pct) || 0,
              lead_days: Number(row.lead_days) || 0,
            })),
          });
        }}
      >
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-border">
              <tr>
                <Th>Stage</Th>
                <Th className="text-right">Win probability %</Th>
                <Th className="text-right">Lead time (days)</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {draft.map((row) => (
                <tr key={row.stage} className={row.contributes ? "" : "opacity-60"}>
                  <Td>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{row.stage}</span>
                      {row.configured ? null : <Pill>House default</Pill>}
                      {row.contributes ? null : <Pill tone="outline">Not pipeline</Pill>}
                    </div>
                  </Td>
                  <Td className="text-right">
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="1"
                      value={row.win_probability_pct}
                      onChange={(event) =>
                        set(row.stage, "win_probability_pct", Number(event.target.value))
                      }
                      className="num w-24 rounded-lg border border-border bg-background px-2.5 py-1.5 text-right text-sm focus:border-ember focus:outline-none"
                    />
                  </Td>
                  <Td className="text-right">
                    <input
                      type="number"
                      min="0"
                      step="1"
                      value={row.lead_days}
                      onChange={(event) => set(row.stage, "lead_days", Number(event.target.value))}
                      className="num w-24 rounded-lg border border-border bg-background px-2.5 py-1.5 text-right text-sm focus:border-ember focus:outline-none"
                    />
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
          Every open deal contributes its value times the probability of the stage it sits at,
          landing in the month that stage&apos;s lead time reaches counted from today. Won and Lost
          keep their dials for the record but never contribute - a won deal is already a job, and
          counting it here would have the same money arriving twice. Nothing is stored as a
          forecast: change a number and the Forecast tab changes on its next read.
        </p>
        <SaveRow
          pending={save.isPending}
          saved={saved}
          error={save.isError ? save.error : null}
          label="Save the dials"
        />
      </form>
    </Card>
  );
}

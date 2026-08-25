// The reporting window the money screens are read through, plus the two
// payload shapes they share.
//
// Both finance reports are range reports: auraos.api.finance_income and
// auraos.api.finance_expenses refuse to guess a range, so the range is a
// control on the screen rather than a default hidden in the backend. It lives
// here because three screens (dashboard, income, expenses) ask the same
// question of the same two endpoints, and a range that reset every time the
// founder changed tab would be its own small lie.
//
// The types are here for the same reason: the dashboard reads both payloads,
// so neither shape belongs beside a single screen any more.

import { useCallback, useState } from "react";

import { formatDate } from "@/lib/format";

// -- what the server sends --
//
// Pinned by the contract tests in
// auraos/auraos/doctype/job_payment_milestone/test_finance_income.py and
// auraos/auraos/doctype/job_expense/test_finance_expenses.py. Money is whole
// integer đồng at every level; nothing here is prose.

export type IncomeClient = {
  company: string | null;
  company_name: string | null;
  total: number;
  count: number;
};

export type IncomeMonth = {
  month: string;
  month_start: string;
  total: number;
  count: number;
  clients: IncomeClient[];
};

export type IncomeReport = {
  date_from: string | null;
  date_to: string | null;
  /** "cash". The screen prints the basis it is told, not one it believes. */
  basis: string;
  months: IncomeMonth[];
  total: number;
  count: number;
};

/** Whose money paid the vendor. Keys, not labels: auraos.lib.settlement. */
export const FROM_COMPANY = "Company";
export const FROM_ADVANCE = "Advance";

/** Both sources on every payload, so a column never drops out of a chart. */
export type PaidFromSplit = { Company: number; Advance: number };

export type ExpenseCategory = { category: string; total: number };

export type ExpenseMonth = {
  month: string;
  month_start: string;
  total: number;
  count: number;
  categories: ExpenseCategory[];
  paid_from: PaidFromSplit;
};

export type ExpenseReport = {
  date_from: string | null;
  date_to: string | null;
  months: ExpenseMonth[];
  categories: ExpenseCategory[];
  paid_from: PaidFromSplit;
  total: number;
  count: number;
};

// -- the range itself --

export type FinanceRange = { from: string; to: string };

const STORE_KEY = "auraos.finance.range";

/** `2026-08-18` out of a local Date, without a UTC round trip moving the day. */
function iso(date: Date): string {
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

type Preset = { label: string; of: (now: Date) => FinanceRange };

/**
 * The four windows a founder actually asks for. Every one of them starts on
 * the first of a month, because the report buckets by calendar month and a
 * range starting mid-month would print a half month next to whole ones.
 */
export const PRESETS: Preset[] = [
  {
    label: "This month",
    of: (now) => ({ from: iso(new Date(now.getFullYear(), now.getMonth(), 1)), to: iso(now) }),
  },
  {
    label: "Last 3 months",
    of: (now) => ({ from: iso(new Date(now.getFullYear(), now.getMonth() - 2, 1)), to: iso(now) }),
  },
  {
    label: "This year",
    of: (now) => ({ from: iso(new Date(now.getFullYear(), 0, 1)), to: iso(now) }),
  },
  {
    label: "Last year",
    of: (now) => ({
      from: iso(new Date(now.getFullYear() - 1, 0, 1)),
      to: iso(new Date(now.getFullYear() - 1, 11, 31)),
    }),
  },
];

function defaultRange(): FinanceRange {
  return PRESETS[2]!.of(new Date());
}

function remembered(): FinanceRange | null {
  try {
    const raw = window.sessionStorage.getItem(STORE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<FinanceRange>;
    if (typeof parsed.from === "string" && typeof parsed.to === "string") {
      return { from: parsed.from, to: parsed.to };
    }
  } catch {
    // Storage can be refused outright; a forgotten range is not an error.
  }
  return null;
}

/**
 * The range, kept for the session so moving between Dashboard, Income and
 * Expenses keeps asking about the same months.
 */
export function useFinanceRange(): [FinanceRange, (next: FinanceRange) => void] {
  const [range, setRange] = useState<FinanceRange>(() => remembered() ?? defaultRange());

  const update = useCallback((next: FinanceRange) => {
    setRange(next);
    try {
      window.sessionStorage.setItem(STORE_KEY, JSON.stringify(next));
    } catch {
      // As above: the screen still works, it just forgets.
    }
  }, []);

  return [range, update];
}

/** The range in words, for a page header. */
export function rangeLabel(range: FinanceRange): string {
  return `${formatDate(range.from)} to ${formatDate(range.to)}`;
}

/** True when the window is inside out, which the server reports as no months. */
export function isBackwards(range: FinanceRange): boolean {
  return range.to < range.from;
}

/**
 * Two dates and four shortcuts. Deliberately plain inputs: the browser's own
 * date picker is localised, keyboard reachable and needs no dependency.
 */
export function FinanceRangeBar({
  range,
  onChange,
}: {
  range: FinanceRange;
  onChange: (next: FinanceRange) => void;
}) {
  const now = new Date();

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-xl border border-border bg-card p-3">
      <label className="block">
        <span className="label-caps">From</span>
        <input
          type="date"
          value={range.from}
          max={range.to}
          onChange={(event) => onChange({ ...range, from: event.target.value })}
          className="num mt-1 block rounded-lg border border-border bg-background px-2.5 py-1.5 text-sm"
        />
      </label>
      <label className="block">
        <span className="label-caps">To</span>
        <input
          type="date"
          value={range.to}
          min={range.from}
          onChange={(event) => onChange({ ...range, to: event.target.value })}
          className="num mt-1 block rounded-lg border border-border bg-background px-2.5 py-1.5 text-sm"
        />
      </label>

      <div className="flex flex-wrap gap-1 pb-0.5">
        {PRESETS.map((preset) => {
          const value = preset.of(now);
          const active = value.from === range.from && value.to === range.to;
          return (
            <button
              key={preset.label}
              type="button"
              onClick={() => onChange(value)}
              className={`rounded-md border px-2 py-1 text-[11px] transition-colors ${
                active
                  ? "border-transparent bg-primary text-primary-foreground"
                  : "border-border text-muted-foreground hover:text-foreground"
              }`}
            >
              {preset.label}
            </button>
          );
        })}
      </div>

      {isBackwards(range) ? (
        <p className="w-full text-xs text-ember">
          The range ends before it starts, so it covers no months.
        </p>
      ) : null}
    </div>
  );
}

/**
 * A month label. The server sends `2026-08`; nothing turns that into "Aug"
 * because month names are not in lib/format.ts and this file has no business
 * being the second place the app formats a date.
 */
export function MonthLabel({ month }: { month: string }) {
  return <span className="num text-xs whitespace-nowrap">{month}</span>;
}

/** Biggest figure in a set, so a row of bars shares one scale. Never printed. */
export function scaleOf(values: number[]): number {
  return values.reduce((top, value) => (value > top ? value : top), 0);
}

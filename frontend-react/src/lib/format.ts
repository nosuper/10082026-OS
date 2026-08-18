// Every number and date the server sends is formatted here and nowhere else.
//
// The API deliberately returns structured values and never formatted prose:
// `amount: 47500000`, not "47,5 triệu"; `days_overdue: 12`, not "Quá hạn 12
// ngày". Turning those into words is the frontend's job, and it is one job, in
// one file, so two screens cannot write the same money two ways.

const GROUPED = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 });

/**
 * Money, as grouped whole đồng: `1.925.000.000`.
 *
 * Never abbreviated. "1,9 tỷ" was rejected by the founder and the design uses
 * full digits everywhere, so there is deliberately no short variant to reach
 * for. Whole đồng only: it is the only denomination anybody pays in.
 *
 * The blank for a missing figure is a short dash, never an em dash.
 */
export function vnd(amount: number | null | undefined, blank = "-"): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) return blank;
  return GROUPED.format(Math.round(amount));
}

/** `1.925.000.000 ₫`, for a string context. In JSX prefer <Money value={...} />. */
export function vndWithSign(amount: number | null | undefined, blank = "-"): string {
  const digits = vnd(amount, blank);
  return digits === blank ? blank : `${digits} ₫`;
}

/**
 * Digits back out of whatever a human typed: a phone keypad, a grouped
 * "12.500.000", a figure pasted out of Zalo. Returns 0 for nothing usable.
 */
export function parseVnd(text: string | number | null | undefined): number {
  const digits = String(text ?? "").replace(/\D/g, "");
  return digits ? Number(digits) : 0;
}

/**
 * Frappe sends "YYYY-MM-DD" or "YYYY-MM-DD HH:mm:ss(.ffffff)" in server local
 * time (Asia/Ho_Chi_Minh). Read as browser local time, which matches for a team
 * working in one timezone.
 */
export function parseServerDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const parsed = new Date(String(value).replace(" ", "T"));
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

/** A date in a row or a field: `18/08/2026`. */
export function formatDate(value: string | Date | null | undefined, blank = "-"): string {
  const date = value instanceof Date ? value : parseServerDate(value);
  if (!date) return blank;
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date);
}

/** A date and time, for anything with a clock on it: `18/08/2026 14:30`. */
export function formatDateTime(value: string | Date | null | undefined, blank = "-"): string {
  const date = value instanceof Date ? value : parseServerDate(value);
  if (!date) return blank;
  return `${formatDate(date)} ${new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date)}`;
}

/** A date spelled out, for a page header: `Tuesday 18 August 2026`. */
export function formatDateLong(value: string | Date | null | undefined, blank = "-"): string {
  const date = value instanceof Date ? value : parseServerDate(value);
  if (!date) return blank;
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);
}

/** Whole days since a server datetime, or null. */
export function daysSince(value: string | null | undefined, now = new Date()): number | null {
  const then = parseServerDate(value);
  if (!then) return null;
  return Math.max(0, Math.floor((now.getTime() - then.getTime()) / 86_400_000));
}

/**
 * How lateness reads wherever a milestone is chased. The server sends
 * `days_overdue` as a number; this is the only place it becomes a sentence, so
 * the jobs board and the dashboard cannot phrase it differently.
 */
export function overdueLabel(days: number | null | undefined): string {
  const count = days ?? 0;
  return `${count} day${count === 1 ? "" : "s"} overdue`;
}

/** "6 deals", "1 deal". English plurals only; the data itself stays Vietnamese. */
export function countLabel(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

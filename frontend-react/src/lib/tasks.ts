// The task vocabulary, and the two date questions a plan asks.
//
// **The statuses are the doctype's, and they arrive with the plan.**
// `auraos.api.job_tasks` sends `statuses` in every payload precisely so the
// columns of a board are the server's list rather than a copy of it.
// `FALLBACK_STATUSES` exists only for the render before the first payload
// lands, and it mirrors `auraos.auraos.doctype.job_task.job_task.STATUSES`,
// which the doctype names as the authority.
//
// The Vue panel this replaces kept its statuses in `frontend/src/data/jobTasks.js`
// alongside a palette of frappe-ui class names - `bg-gray-100`, `bg-blue-50`.
// That file was deliberately not carried across when the React line was
// integrated (#164): this app has its own tokens, and importing colours from a
// preset it does not load would have resolved to nothing, silently. So the
// tones below are named in this app's vocabulary and go through `Pill`, which
// owns what each tone looks like.

/** Mirrors job_task.STATUSES. Used only until the server's list arrives. */
export const FALLBACK_STATUSES = ["To do", "In progress", "Blocked", "In review", "Done"] as const;

/** Mirrors job_task.DONE - the status that stops a task being late. */
export const DONE = "Done";

/**
 * How a status reads. Deliberately the app's own tones rather than a colour
 * per status: `Pill` decides what "ember" looks like, so a card, a column
 * header and a list row cannot drift apart.
 *
 * Blocked is the only one that gets the alarming tone. In review is outlined
 * rather than filled because it is a waiting state, not a working one, and a
 * board where four of five columns shout has no emphasis left for the one
 * that should.
 */
export function statusTone(status: string): string {
  switch (status) {
    case "In progress":
      return "ink";
    case "Blocked":
      return "ember";
    case "In review":
      return "outline";
    case DONE:
      return "positive";
    default:
      return "neutral";
  }
}

export const DAY_MS = 86_400_000;

/**
 * A server date (`2026-08-25`) as a local midnight.
 *
 * Sliced to ten characters and given an explicit `T00:00:00` so a value that
 * arrives as a full timestamp still lands on its own day. Parsing
 * `"2026-08-25"` bare would be read as UTC and could fall on the 24th for
 * anyone west of Greenwich - which for a deadline is the difference between
 * late and not.
 */
export function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const parsed = new Date(`${String(value).slice(0, 10)}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

/** `25/8` - the short form a bar label and a ruler tick both use. */
export function shortDate(value: string | null | undefined): string {
  const parsed = parseDate(value);
  if (!parsed) return "";
  return `${parsed.getDate()}/${parsed.getMonth() + 1}`;
}

export type TaskLike = { end_date?: string | null; status?: string };

/**
 * How many whole days past its due date a task is, or null.
 *
 * Null rather than 0 for a task that is not late, so "late" is a question with
 * one answer rather than two. A finished task is never late however long it
 * sat: the deadline stopped mattering when the work landed, and a board full
 * of red Done cards teaches people to ignore red.
 *
 * Measured midnight to midnight so a task due today is not late at 9am.
 */
export function daysLate(task: TaskLike, now: Date = new Date()): number | null {
  if (!task.end_date || task.status === DONE) return null;
  const due = parseDate(task.end_date);
  if (!due) return null;
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const days = Math.floor((today.getTime() - due.getTime()) / DAY_MS);
  return days > 0 ? days : null;
}

/**
 * A person as a card should read them: "Minh", not an email address.
 *
 * `people` is served with the plan rather than looked up, because a crew
 * session cannot list the User doctype - and who else is on the job is not a
 * number. An email with no name falls back to its local part, which is still
 * more readable than the whole address; no email at all is unassigned work,
 * which is a real state and says so.
 */
export function personLabel(
  email: string | null | undefined,
  people: Record<string, string>,
): string {
  if (!email) return "Unassigned";
  // Both fallbacks are guarded because the app compiles with
  // noUncheckedIndexedAccess: an unknown email is not in `people`, and an
  // address with no "@" in it has no local part to take. Neither is a state
  // worth crashing a board over.
  return people[email] || email.split("@")[0] || email;
}

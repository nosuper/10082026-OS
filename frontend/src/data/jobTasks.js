// The task board, in column order - mirrors STATUSES in
// auraos.auraos.doctype.job_task.job_task, which is the authority.
// A kanban's columns are its whole shape, so this list is fixed rather
// than typed in per job.
export const STATUSES = [
  "To do",
  "In progress",
  "Blocked",
  "In review",
  "Done",
]

export const DONE = "Done"

// One color per status, used by all three views - the list pill, the
// board column dot and the timeline bar must never disagree.
// Palette note: frappe-ui's Tailwind preset ships amber, blue, cyan,
// gray, green, orange, pink, red, teal, violet, yellow - nothing else.
const STATUS_STYLES = {
  "To do": {
    dot: "bg-gray-400",
    pill: "bg-gray-100 text-gray-700",
    bar: "bg-gray-300",
  },
  "In progress": {
    dot: "bg-blue-500",
    pill: "bg-blue-50 text-blue-700",
    bar: "bg-blue-500",
  },
  Blocked: {
    dot: "bg-red-500",
    pill: "bg-red-50 text-red-700",
    bar: "bg-red-400",
  },
  "In review": {
    dot: "bg-amber-500",
    pill: "bg-amber-50 text-amber-800",
    bar: "bg-amber-400",
  },
  Done: {
    dot: "bg-green-500",
    pill: "bg-green-50 text-green-700",
    bar: "bg-green-500",
  },
}

const FALLBACK = {
  dot: "bg-gray-400",
  pill: "bg-gray-100 text-gray-700",
  bar: "bg-gray-300",
}

export function statusDot(status) {
  return (STATUS_STYLES[status] || FALLBACK).dot
}

export function statusPill(status) {
  return (STATUS_STYLES[status] || FALLBACK).pill
}

export function statusBar(status) {
  return (STATUS_STYLES[status] || FALLBACK).bar
}

// A Frappe Date arrives as "YYYY-MM-DD". Parsed at local midnight so a
// bar's left edge lands on the day the task starts rather than the
// evening before, which is what UTC parsing would do east of Greenwich.
export function parseDate(value) {
  if (!value) return null
  const parsed = new Date(`${String(value).slice(0, 10)}T00:00:00`)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

export const DAY_MS = 86_400_000

// "1 Thg 9" - short enough for a timeline tick, unambiguous in a team
// that reads both languages.
export function shortDate(value) {
  const date = parseDate(value)
  if (!date) return ""
  return `${date.getDate()}/${date.getMonth() + 1}`
}

// How late a task is, in whole days, or null when it is not late.
// Done work is never late, whenever it finished.
export function daysLate(task, now = new Date()) {
  if (!task.end_date || task.status === DONE) return null
  const due = parseDate(task.end_date)
  if (!due) return null
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const days = Math.floor((today - due) / DAY_MS)
  return days > 0 ? days : null
}

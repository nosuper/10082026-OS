// Short relative time for scanning columns - "5m", "3h", "6d", "2w".
// Frappe datetimes arrive as "YYYY-MM-DD HH:mm:ss(.ffffff)" in server
// (Asia/Ho_Chi_Minh) local time; Date.parse reads that shape as browser
// local time, which matches for a team working in one timezone.
export function parseFrappeDatetime(value) {
  if (!value) return null
  const parsed = new Date(String(value).replace(" ", "T"))
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

export function ago(value, now = new Date()) {
  const then = parseFrappeDatetime(value)
  if (!then) return ""
  const minutes = Math.floor((now - then) / 60_000)
  if (minutes < 1) return "now"
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h`
  const days = Math.floor(hours / 24)
  if (days < 14) return `${days}d`
  return `${Math.floor(days / 7)}w`
}

// Whole days since a datetime - the board's "how long has this deal
// sat in its stage" number.
export function daysSince(value, now = new Date()) {
  const then = parseFrappeDatetime(value)
  if (!then) return null
  return Math.max(0, Math.floor((now - then) / 86_400_000))
}

// Whole đồng with Vietnamese thousands separators — the way every
// number in the app is written. Mirrors auraos.lib.money.format_vnd.
export function vnd(amount, blank = "—") {
  if (amount == null || amount === "") return blank
  return new Intl.NumberFormat("vi-VN").format(amount)
}

// Compact VND the way the founder says it out loud — "1,2 tỷ",
// "450tr" — for board column totals where the full figure is noise.
// Below a million the full figure is already short enough.
export function vndShort(amount) {
  if (!amount) return ""
  const sign = amount < 0 ? "-" : ""
  const abs = Math.abs(amount)
  if (abs >= 1e9) {
    const billions = abs / 1e9
    const rendered = billions >= 10 ? Math.round(billions) : Math.round(billions * 10) / 10
    return `${sign}${String(rendered).replace(".", ",")} tỷ`
  }
  if (abs >= 1e6) return `${sign}${Math.round(abs / 1e6)}tr`
  return sign + vnd(abs)
}

// Digits back out of whatever a human typed — a phone keypad, a
// grouped "12.500.000", a figure pasted out of Zalo. Whole đồng only,
// because that is the only denomination anybody pays in.
export function parseVnd(text) {
  const digits = String(text ?? "").replace(/\D/g, "")
  return digits ? Number(digits) : 0
}

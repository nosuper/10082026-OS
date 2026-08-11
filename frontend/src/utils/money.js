// Whole đồng with Vietnamese thousands separators — the way every
// number in the app is written. Mirrors auraos.lib.money.format_vnd.
export function vnd(amount, blank = "—") {
  if (amount == null || amount === "") return blank
  return new Intl.NumberFormat("vi-VN").format(amount)
}

// Digits back out of whatever a human typed — a phone keypad, a
// grouped "12.500.000", a figure pasted out of Zalo. Whole đồng only,
// because that is the only denomination anybody pays in.
export function parseVnd(text) {
  const digits = String(text ?? "").replace(/\D/g, "")
  return digits ? Number(digits) : 0
}

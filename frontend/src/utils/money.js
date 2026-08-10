// Whole đồng with Vietnamese thousands separators — the way every
// number in the app is written. Mirrors auraos.lib.money.format_vnd.
export function vnd(amount, blank = "—") {
  if (amount == null || amount === "") return blank
  return new Intl.NumberFormat("vi-VN").format(amount)
}

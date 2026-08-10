// One place to render a VND amount for the screens.
export function vnd(amount) {
  if (amount == null) return "—"
  return new Intl.NumberFormat("vi-VN").format(amount)
}

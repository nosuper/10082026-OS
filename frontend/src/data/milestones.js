// The collection flow, in order — mirrors STATUS_FLOW in
// auraos.lib.milestones, which is the authority.
//
// The stored value is English like every other status in the app; the
// Vietnamese beside it is what the founder and the accountant actually
// say, so the screen shows both.
export const COLLECTION_STATUSES = [
  { value: "Not requested", vi: "chưa yêu cầu" },
  { value: "Requested", vi: "đã yêu cầu KT" },
  { value: "Invoiced", vi: "đã xuất HĐ" },
  { value: "Paid", vi: "đã thanh toán" },
]

export const PAID = "Paid"

// How far along the flow a status sits — drives the progress colouring.
export function statusIndex(status) {
  return COLLECTION_STATUSES.findIndex((row) => row.value === status)
}

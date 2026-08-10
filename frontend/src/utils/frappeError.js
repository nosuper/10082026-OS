// One place to turn a frappe-ui request error into display text.
export function frappeErrorMessage(err) {
  return err.messages?.join("\n") || err.message
}

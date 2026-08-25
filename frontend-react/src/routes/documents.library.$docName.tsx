import { createFileRoute } from "@tanstack/react-router";

// One Library document, addressable (#124).
//
// **The founder's complaint was "gửi link sẽ ra tab, không ra tài liệu"** -
// sending someone a link landed them on the tab, not on the document. The SOP
// is the thing people actually send each other, and it had no address.
//
// **This route renders nothing, and that is the design rather than a stub.**
// The document opens in a window over the list, the way the Paperwork tab
// opens a paper - that parity is deliberate, and making the Library navigate
// differently would be a bigger product change than giving it a URL. So the
// list route stays mounted, reads `docName` out of the match, and drives the
// window it already owned. What lives here is the *path*: this file is what
// makes `/documents/library/$docName` a real location the router will match,
// restore on refresh, and put in the address bar.
//
// The alternative was a standalone page, and it was rejected for a concrete
// reason rather than taste: Edit opens an editor owned by the list route's
// state. Moving the window into a child means routing the editor too, and a
// ticket about addressability would have become one about state ownership.
//
// **The URL is the contract either way.** If the window turns out to be
// cramped, a later change to render this as a full page changes presentation
// and leaves every saved link working.
//
// **A URL is not a bypass, and the reason is worth knowing precisely because
// it is load-bearing and invisible.** `api.library_document_detail` opens with
// `frappe.has_permission("Library Document", "read", throw=True)`, so the
// server is asked on every request whatever route reached it - a deep link
// cannot see more than the tab can. A throw renders through `QueryState`'s
// error branch inside the window rather than as a blank, which is the same
// path a broken tab load takes.
//
// **The caution: that check is doctype-level, not per-record.** It answers
// "may this person read Library Documents", not "may they read *this* one".
// Today that is correct - any reader may read any of them. The day somebody
// adds a document not everyone should see, this is the assumption that fails,
// **and a shared link is the surface it fails on**: the list would filter and
// the address would not. Whoever adds that will be editing the doctype, not
// this file, so the note lives here where the exposure is.
export const Route = createFileRoute("/documents/library/$docName")({
  component: () => null,
});

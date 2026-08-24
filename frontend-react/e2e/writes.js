// Waiting for a write to land, rather than for a length of time.
//
// **No panel in this app awaits its own write.** A control's handler calls
// `mutate(...)` and returns; the response lands later and invalidates a query.
// So the statement after an interaction runs while the POST is still in
// flight, and `page.reload()` or the end of a test aborts it.
//
// **The measurement that made this concrete**, taken by the ledger lane rather
// than reasoned: `set_milestone_status` with an invoice number takes **~26ms
// warm** server-side - a Job save with its milestone stamps and ledger
// reconciliation - and **1780ms cold**. Run 18's trace had a spec blurring at
// 527ms and reloading at 541ms: **14ms**. The request was always in flight;
// whether it survived was a race between the browser dispatching it and the
// navigation cancelling it. That is why one file was green on one run and red
// on the next from the same commit.
//
// **A fixed wait is the wrong fix** for the same reason it looks like the
// right one: 26ms is the warm floor, not a budget, and the cold path is
// seventy times it.
//
// **What makes this hard to see is that the assertions after a write look like
// synchronisation points.** Two ways they are not:
//
//   - `JobMilestonesPanel.setStatus` updates its rows **optimistically** before
//     mutating, so `toBeEnabled()` and `toHaveValue()` pass on the browser's
//     own optimism with nothing on the server yet.
//   - A `<select>` the test just changed already holds the new value in the
//     DOM, whatever the server thinks. Even where the control is *controlled*
//     by server state - `PaperStatusSelect` is - `toHaveValue` can match that
//     transient before React re-renders.
//
// **The end of a test is the worst place for this**, because a restore is
// usually the last statement and there is nothing after it to force a wait. A
// restore that never lands leaves the next test reading a fixture nobody
// seeded, and every spec here restores what it moves.

/**
 * Run an interaction that writes, and wait for that write to come back.
 *
 * `method` is the whitelisted endpoint the panel calls, matched against the
 * request URL. Registered *before* the action, so a fast response cannot land
 * between the two.
 *
 * **This helper's failure mode is a timeout, not a failure, and that is worth
 * knowing before you meet one.** Every way it goes wrong looks identical from
 * the outside: the test sits there and then Playwright gives up. **A hang here
 * is a bug in the wait, not a slow box** - check these in order, because the
 * list is roughly most-likely-first for someone who has just written a call:
 *
 *   1. **`method` does not match the URL the panel calls.** A typo, or the
 *      panel calls a different endpoint than you assumed. `waitForResponse`
 *      cannot tell "no such response yet" from "no such response ever".
 *   2. **The handler returned early without mutating.** Several here do when
 *      the value has not changed - `saveInvoiceNo` compares what was typed
 *      against the stored row - so saving the same value twice waits for a
 *      request nobody sent. That one at least says so: it writes its decision
 *      to the field's `data-invoice-save`, so read the attribute before
 *      concluding the write was lost (#140).
 *   3. **The action did not trigger the write at all** - a blur that did not
 *      fire because focus was already elsewhere, a select set to the value it
 *      already had.
 *
 * Only after those three is a slow server worth considering, and the cold path
 * above is what that looks like: slow, then finished.
 */
export async function saving(page, method, action) {
  const landed = page.waitForResponse(
    (response) => response.url().includes(method) && response.request().method() === "POST",
  );
  await action();
  await landed;
}

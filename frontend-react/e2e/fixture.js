// What the E2E fixture is called.
//
// `scripts/e2e-seed.py` is the single statement of what the disposable site
// contains. This file exists because a spec cannot import a Python constant,
// and the alternative - each spec spelling the names out itself - is how
// cash-accounts.spec.js came to assert on `Tài khoản VCB` and `Quỹ tiền mặt`,
// which are the *dev walkthrough* seed's accounts (auraos/setup/seed.py). The
// E2E stack has never run that file. Four tests could not have passed, and
// they would have come back as four reds belonging to nobody.
//
// The lesson underneath is worth more than the names: **stating in a header
// that you depend on the fixture is not depending on it.** That spec said so,
// in prose, correctly, and still read from the wrong file. Only a run proves
// the dependency, and until one has happened the claim is an intention.
//
// So the mirror is guarded rather than trusted - fixture.spec.js reads the
// seed and fails loudly if a name here has drifted from it. One legible red
// at the rename, instead of four obscure ones a run later.
//
// Names only. Amounts and dates deliberately live in the seed alone: a spec
// that hardcodes a figure asserts the seed's arithmetic rather than the
// screen's, and the derivation tests here work on differences for that reason.

/** Where the seeded company keeps its money. The first is the default, so
 *  every posting flow lands there and the second stays empty on purpose. */
export const BANK = "Playwright Bank";
export const PETTY = "Playwright Petty Cash";

/** The deal that becomes the open job. Not `Playwright Existing Deal`, which
 *  the deals specs hold at Brief Received. */
export const JOB_DEAL = "Playwright Job Deal";

/** The deal behind the closed job. Named here so a spec can say which job it
 *  means: #123 refuses spending against a job at its closing stage, and the
 *  seed converts this one last, so "the most recently modified job" is the one
 *  the product forbids writing to. */
export const CLOSED_DEAL = "Playwright Closed Deal";

/** Every name above, for the guard in fixture.spec.js. */
export const FIXTURE_NAMES = { BANK, PETTY, JOB_DEAL, CLOSED_DEAL };

# Company branding on a quote renders live, never freezes

A quote version is otherwise an immutable snapshot: packages, totals, phase
names and validity date are all frozen at publish, because what a client was
offered must not change under them. Company identity is the deliberate
exception — the logo, company name, tax code, contact and bank block are read
from AuraOS Settings at render time, so every quote page and PDF shows today's
details rather than the ones that happened to be on file the day it was sent.

The reason is that branding is not part of the offer. When the company moves
office, changes bank or replaces the logo, a client re-opening a quote from
last month should see the letterhead that will still be true when they call
the number on it. Freezing it would mean an old link quietly printing a dead
address, and re-publishing a frozen quote purely to correct a phone number
would change its version and its token — a new document, for a change that
was never about price.

## Consequences

- The company block reaches the template through its own named whitelist,
  the same doctrine as `CLIENT_QUOTE_FIELDS`. AuraOS Settings also holds
  `margin_floor_pct`; handing the whole Settings doc to a guest render
  context would put an internal number one typo away from a client's page.
- A PDF downloaded by a client and the same quote re-rendered a year later
  can differ in their letterhead while agreeing on every number. That is
  intended, and is why this file exists — the mismatch reads as a bug
  otherwise.
- Emptying a Settings field blanks that line on every existing quote. There
  is no per-version fallback to the old value, by design.

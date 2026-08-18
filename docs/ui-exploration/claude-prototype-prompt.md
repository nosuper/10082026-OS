# Prompting Claude to prototype AuraOS UI directions

Asset of wayfinder ticket [#77 - Direction panel](https://github.com/nosuper/10082026-OS/issues/77), child of map [#76](https://github.com/nosuper/10082026-OS/issues/76).

This is a paste-ready guide for generating the direction-panel prototypes with Claude - in claude.ai (artifacts), the Claude desktop app, or a fresh Claude Code session. The rules it encodes: prototypes are static, self-contained HTML; the current UI in `frontend/` is never touched; the same fixture data appears in every direction so only the design varies; the founder picks by reacting to rendered pages.

## How to use it

1. Start one fresh conversation per direction (three conversations). A fresh context keeps each direction from bleeding into the next.
2. Paste the **master prompt** below, then paste **one** direction brief under it.
3. Let Claude produce the page, then iterate with the follow-up prompts.
4. Save each result as `pipeline-<direction>.html` on the `prototype/ui-directions` branch, and view them side by side.
5. React in front of the pages, not from memory: which one would you want to open every morning?

## Master prompt (paste first, always)

```text
You are designing a screen for AuraOS, the internal operations system of a small
Vietnamese video production house (a "production house"). The founder lives in this
tool daily. It covers the deal pipeline, quoting, jobs and money tracking.

Build ONE static, self-contained HTML page: the DEAL PIPELINE screen, as a kanban
board. No external fonts, scripts, or images - inline all CSS, use system font
stacks or embedded styles only. Responsive down to mobile. Build exactly one
mode: light by default, or dark if the direction brief calls for it - no
direction owes a second variant.

Use EXACTLY this data, unchanged (it mirrors the real system):

Pipeline stages, in order:
Brief Received | De-brief | Breakdown | Quote Sent | Negotiation | Won | Lost

Deal cards (name - client - value - tier - type - days in stage):
- TVC Tết 2027 "Vị Xuân" - Nhất Minh Beverage - 850,000,000 VND - Tier 3 - Brand - 4d (Brief Received)
- Recruitment film - Sông Hà Logistics - 120,000,000 VND - Tier 1 - Cash - 2d (Brief Received)
- Product launch livestream - An Khang Pharma - 260,000,000 VND - Tier 2 - Bridge - 6d (De-brief)
- Corporate profile 2026 - Kiến Vàng Construction - 180,000,000 VND - Tier 1 - Cash - 1d (Breakdown)
- Social cutdowns x12 - Nhất Minh Beverage - 95,000,000 VND - Tier 1 - Bridge - 9d (Quote Sent, stalled)
- Brand film "Người Giữ Lửa" - Gốm Sứ Minh Long - 420,000,000 VND - Tier 2 - Brand - 3d (Negotiation)
- Factory safety series - Sông Hà Logistics - 210,000,000 VND - Tier 2 - Cash - 12d (Won)
- Event aftermovie - Deja Vu Weddings - 60,000,000 VND - Tier 1 - Cash - 5d (Lost)

Rules the design must express:
- Money is the loudest fact on a card. Format VND as 850,000,000 VND (or the
  double-struck dong sign) - never abbreviate to 850M.
- A "stalled" deal (Quote Sent, unanswered too long) must be visibly flagged.
- Won and Lost are terminal columns and should read as an ending, not just two
  more columns.
- Each card carries its tier (Tier 1-3) and type (Cash / Bridge / Brand) as
  compact marks, not sentences.
- The board must survive density: imagine 3x the cards before calling it done.
- Every typeface must fully support Vietnamese diacritics - judge each face
  against the data above (Tết, Vị Xuân, Gốm Sứ, Người Giữ Lửa) before keeping it.
- Never use em dashes anywhere in copy - use "-".

Before writing code, present a compact design plan: palette as 4-6 named hex
values, typefaces for display / body / data roles, a one-paragraph layout
concept, and the single signature element this page will be remembered by.
Critique your own plan once - if any part is the generic default you would
produce for any kanban board, revise it - then build.
```

## Direction briefs (paste one per conversation)

The three directions are deliberately divergent, and each is grounded in the production house's own world - not in generic dashboard fashion. Claude may refine them, but the aesthetic risk named in each brief must survive.

### Direction 1 - Call sheet

```text
DIRECTION BRIEF: "Call sheet".
The aesthetic of working production paper: call sheets, shooting schedules,
camera reports. Utilitarian print vernacular translated to screen - strong
tabular bones, ruled lines that mean something, stamped/overprinted status
marks for stalled/Won/Lost, a monospaced data face for money and codes, ink-on-
paper contrast. Feels like a document the 1st AD taped to the wall, but alive.
The risk to take: commit to print-grade typographic discipline - no card
shadows, no rounded-everything - and let rules, weight and spacing do all the
hierarchy work.
```

### Direction 2 - Grading suite

```text
DIRECTION BRIEF: "Grading suite".
The calm of a color-grading room: a deep neutral charcoal environment (not pure
black), low-glare surfaces, precise instrument-panel accents borrowed from
scopes and waveforms, money rendered like timecode - tabular, exact, luminous.
Color is used sparingly and diagnostically: one hue for money, one for state,
nothing decorative. The risk to take: an interface that is genuinely dark-first
and quiet, where the cards feel like clips on a timeline and the stalled flag
glows like a warning on a monitor.
```

### Direction 3 - Studio brand

```text
DIRECTION BRIEF: "Studio brand".
The production house's outward confidence turned inward: big assured display
type, generous air, one saturated brand color doing structural work (stage
columns, totals, the stalled flag), photography-adjacent warmth without using
any images. The board should feel like the opening slide of a great pitch deck
that happens to be operable. The risk to take: oversize the stage headers and
per-stage totals until they become the visual architecture of the page, and
keep the cards almost austere underneath them.
```

## Iterating

Useful follow-ups once the first render exists:

- "Triple the cards in Quote Sent and Negotiation. Does the design still hold? Fix what breaks."
- "Show the same page at 390px wide."
- "The founder scans for two things: total value per stage, and anything stalled. Make both findable in under a second without adding elements."
- "Remove one accessory: find the least necessary decorative choice on this page and delete it."

## After the pick

When a front-runner exists, the next tickets apply it where it is hardest:
[#79 - dense screens](https://github.com/nosuper/10082026-OS/issues/79) (quote builder, breakdown, dashboard) and
[#80 - client quote page](https://github.com/nosuper/10082026-OS/issues/80).
Reuse this master-prompt structure, swapping the screen spec and fixture data;
carry the winning direction brief verbatim so the direction stays stable.

Expressibility in the real frontend (Vue + frappe-ui) was researched in
[#78 - theming constraints](https://github.com/nosuper/10082026-OS/issues/78)
and is mostly a non-issue: new color families, typefaces, spacing/radius
extensions and dark mode are all cheap via Tailwind `theme.extend` and
CSS-variable overrides on frappe-ui's token layer. Directions may therefore use
any palette, typeface or radius language. The one priced item: Button, Badge
and Alert hard-code a gray/blue/green/red theme enum in JS, so a winning accent
outside those four families needs a thin app-level wrapper component - small
new code, not a fork. If a direction's accent leaves gray/blue/green/red, note
that on the direction so the restyle spec budgets the wrapper. Full findings:
`docs/research/frappe-ui-theming.md` on branch `research/frappe-ui-theming`.

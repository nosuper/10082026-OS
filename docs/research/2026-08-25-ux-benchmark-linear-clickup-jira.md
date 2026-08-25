---
date: 2026-08-25
question: >
  The founder says the app's UX is "rất rối" - very confusing, very cluttered -
  and names three specifics: too much information on one screen, horizontal
  space distributed wrongly, and no intuitive scanning order. What exactly is
  confusing about AuraOS, screen by screen, and what would Linear, ClickUp and
  Jira do instead?

  Then, having read that: "bên cạnh những yếu tố thiết kế thì cái tôi quan tâm
  hơn nữa là user flow và vị trí các con số, screen có hợp lý chưa. có nên gộp
  / tách screen hay gì không" - are these the right screens at all, is each
  number where the person who needs it is standing, and what should be merged
  or split? That is §9.
status: complete
---

# UX benchmark: AuraOS against Linear, ClickUp and Jira

## 0. How to read this

Every claim about another product is followed back to that product's own
documentation - `linear.app/method`, `atlassian.design`, `help.clickup.com`,
Atlassian's product docs. Every claim about **this** app is a file and a line
number, measured rather than remembered. Where a number is arithmetic on the
source (a table's width, a contrast ratio), the arithmetic is shown so it can
be checked.

Nielsen Norman Group is cited only for NN/g's own research. W3C is cited for
WCAG success criteria and the ARIA Authoring Practices patterns. Nothing here
comes from a blog roundup; where a claim is mine and has no source behind it,
it says **judgement** in as many words.

**One thing this document will not do is call a deliberate decision a defect.**
§7 lists the decisions that look like flaws and are not, with the docstring
that argues each one. Read §7 before acting on §6.

**§9 is the information-architecture half and was written second**, after the
founder asked the harder question underneath the design one: *user flow và vị
trí các con số, screen có hợp lý chưa — có nên gộp / tách screen hay gì không.*
§1-§8 ask where the eye goes *within* a screen. §9 asks where the screen
boundaries should be, traces the five real task flows route by route, and
tabulates every significant figure against who needs it and where they are
standing when they do. It contains one correction to §7.5. **If you only read
one section, read §9.3 and §9.4.**

## 1. TL;DR

The founder's three complaints are all real, and they have three different
causes. Ranked by how much of the "rối" each one explains:

1. **No page has a maximum width, and the widest thing on most pages is a
   table that cannot fit anyway.** `AppShell`'s `<main>` is
   `min-w-0 flex-1 px-4 py-5 sm:px-6 sm:py-6` - no `max-w-*` anywhere
   (`frontend-react/src/components/aura/AppShell.tsx:214`). On a 2560px
   monitor the content column is 2256px wide, so a `text-xs` card subtitle
   runs to roughly 375 characters per line where WCAG 1.4.8 asks for 80. In
   the same app, the cost-line editor's table is 1590px at its narrowest and
   2180px with all four optional columns on, so on a 1440px laptop it scrolls
   sideways by 450-1050px. **Prose has too much width and money has too
   little, on the same screen, at the same time.**
2. **The screens that matter most print the same number twice and open with
   tiles of equal weight.** `routes/deals.index.tsx` renders five stat tiles -
   one per open stage, each showing a count and a money total - and then,
   directly beneath, a board whose seven column headers show *the same count
   and the same money total*. The Home dashboard opens on five equally
   weighted `<Stat>` tiles for a founder. Nothing on either screen says which
   number to act on first.
3. **Sub-navigation contradicts itself.** Under one sidebar item, "Finance",
   sit nine route tabs. Two of them disagree with the `<h1>` of the page they
   open ("Accounts" opens "Cash accounts", "Forecast" opens "Cash forecast"),
   one of them shows `<h1>Finance</h1>` where the other eight show their own
   name, and one of them - `routes/finance.bank.tsx:117` - renders the tab
   strip in `AppShell`'s `meta` slot while the other eight render it in the
   page body, so **the tab strip physically moves when you click Bank**.

Underneath those sit three findings that are not about clutter but will bite:

4. **`outline-none` appears 63 times across 23 files, and no rule anywhere
   restores a focus ring for any of them.** A keyboard user cannot see where
   they are. This is a WCAG 2.4.7 (Level A) failure and it is the single
   cheapest thing on this list to fix.

   > **Corrected 2026-08-25.** This item first read "there is not one
   > `focus-visible` rule in the entire application", which is false.
   > `focus-visible` appears **44 times across 11 files** — all of them in
   > `components/ui/`, the shadcn primitives. The claim that survives is the
   > narrower one **§5.1 made all along**: zero occurrences in `routes/` or
   > `components/aura/`, and none in `styles.css` — which is every file the
   > app actually renders, because nothing imports `components/ui/`. The app
   > ships the styling for a focus ring it never mounts. Nothing in §5.1 or §6
   > changes, and the fix gets *better* supported: `--ring` is not only
   > defined, it is already written against.
5. **Below 1024px there is no navigation at all.** The sidebar is
   `hidden ... lg:flex` with no drawer, no hamburger and no fallback. A
   producer holding a phone on set can reach `/expense` only by typing the URL.
6. **In light mode, the alert colour fails contrast.** `text-ember` on a card
   is 3.45:1 and the ember `<Pill>` is 2.99:1, against the 4.5:1 that WCAG
   1.4.3 asks for text. Dark mode passes comfortably. The colour the app uses
   to mean "this is the urgent one" is the colour hardest to read.

### And on the architecture question (§9, written second)

The screens are mostly the right screens. **What is wrong is the wiring between
them and where two numbers live.**

7. **Six of the nine Finance tabs have no outbound link, and Home does not link
   to Finance at all.** Overhead prints a job that lost money, Reports prints
   its margin, Forecast prints a deal's weighted value, and Files prints the
   deal a brief hangs on — **none of them as a link**. You read the answer,
   memorise it, and go and search for it again. There is no global search
   either. This, not the tab count, is why Finance reads as a separate app.
8. **The Quotations section is read-only.** Both its routes contain **zero
   mutations**. `Mark sent` and `Mark confirmed` exist only at
   `deals.$dealCode.quote.tsx:2222` and `:2230` — the ninth card of a 2464-line
   file. The screen built to answer "what is out with clients" cannot act on
   its own answer.
9. **The margin-floor warning is silent where it matters.** `floor_breached`
   appears in exactly one file. The banner is the first element on the quote
   page; the Publish button is eight cards below it and mentions no margin. The
   flag never reaches `/deals`, `/quotations`, or the job. A below-floor quote
   can be published, sent, confirmed and won without any screen saying so again.
10. **"Are we all right?" costs seven screens.** Cash on hand is on
    `/finance/accounts` and nowhere else; the break-even surplus is on
    `/finance/overhead` and nowhere else — the ninth tab of the seventh nav
    item. `CONTEXT.md` made the break-even line "one signed number rather than
    two fields" precisely so it could be shown as one. It is the hardest number
    in the app to reach, and it is not on Home.
11. **A job's own margin is served to the founder's reports and not to the
    producer running the job.** `job_profitability(job=…)` exists, is
    producer-permitted, and its docstring says it exists "so they can act on
    it". The frontend calls it twice, both times without a `job` argument.

Items 19-23 in §9.6 close all of that and are roughly **one afternoon's work**
between them. They touch no pricing logic, add no endpoint and rename nothing.

**The benchmark answer, in one line.** Linear's discipline is the right one for
a one-founder studio and ClickUp's is not - but this app has already made
Linear's bet (opinionated, permission-shaped, no configuration surface) and is
losing on the part Linear is actually famous for, which is *restraint about
what goes on a screen at once*, plus the keyboard and speed affordances it
advertises but has not built. Jira is the useful reference for exactly one
thing: what to do with a record page carrying more fields than fit.
## 2. The app as it actually is, in numbers

Measured on `origin/main` at `05607de`, in `frontend-react/src`.

### 2.1 Surface count

| Surface | Count |
|---|---|
| Route files | 33 (27 real screens; 6 are 5-9 line layout shells) |
| Sidebar links, founder session | 11 - 7 primary, 2 under "Contacts", 2 under "Studio" |
| Finance tabs | 9 (`components/aura/FinanceTabs.tsx:740-750`) |
| Documents tabs | 3 (`components/aura/DocumentsTabs.tsx:820-826`) |
| Job detail tabs | 4, in React state, not in the URL (`routes/jobs.$jobId.tsx:76,100`) |
| Distinct tab mechanisms | **3** - route tabs, `useState` tabs, `ViewToggle` (`aria-pressed`) |
| Destinations reachable without opening a record | **21** (11 links, of which Finance expands to 9 and Documents to 3) |

Nine tabs behind one sidebar word is the outlier. It is more first-level
choices than Linear puts in its entire sidebar (§3.1).

### 2.2 Density, per screen

Counted as literal component occurrences in the route file, plus what its
imported panels render.

| Screen | `<Card>` | Stat tiles | `<table>` | Notes |
|---|---|---|---|---|
| `routes/jobs.$jobId.tsx` | 9 | 4 | 2 | plus `JobMoneyPanel` (4 cards / 3 tables), `JobMilestonesPanel` (1 table, 7 columns), `JobPaperworkPanel`, `JobTasks` (2 cards / 1 table). **Two stage controls on screen at once**: an 8-option `<select>` in the header (line 170) *and* an 8-button chip trail in the body (line 190). |
| `routes/deals.$dealCode.quote.tsx` | 9 | 0 | 2 | 2464 lines. Tables are 14-18 columns and 9 columns. |
| `routes/deals.$dealCode.index.tsx` | 7 | 0 | 0 | 12 `<Field>`s inside the first card, in an `xl:grid-cols-3` page. |
| `routes/finance.overhead.tsx` | 5 | 4 | 5 | 26 `<Th>` across five tables, founder-only. |
| `routes/index.tsx` (Home) | 5 | 5 | 1 | `xl:grid-cols-5` stat row for a founder, 4 for a producer. |
| `routes/deals.index.tsx` | - | 5 | 1 | the five tiles duplicate the board's own column headers. |
| `routes/settings.tsx` | 6 | 0 | 1 | - |

The worst offender is not the one with the most cards. It is
`routes/deals.index.tsx`, because its density is **redundant**: lines 554-573
render one tile per open stage carrying `items.length` and
`sum(estimated_budget)`, and lines 764-800 render one board column per stage
carrying `items.length` and the same sum again. The reader pays twice for one
fact.

### 2.3 Width, in pixels

`AppShell` gives the sidebar `w-64` (256px) and gives `<main>` no maximum.
Content column = viewport - 256 - 48px padding:

| Viewport | Content column |
|---|---|
| 1280 | 976px |
| 1440 | 1136px |
| 1920 | 1616px |
| 2560 | 2256px |

Against that, the widest things the app draws:

| Thing | Width | Source |
|---|---|---|
| Cost-line table, no optional columns | **1590px** | `180 + sum(TAIL_WIDTHS)` = `180 + 1410`, `routes/deals.$dealCode.quote.tsx:322-323,1024-1029` |
| Cost-line table, all four optional columns | **2180px** | `+150+150+130+160` from `META_COLUMNS` (line 311) |
| Jobs board, 8 production stages | **2284px** | `8 x 272 + 7 x 12 + 24`, `routes/jobs.index.tsx:314` |
| Deals board, 7 stages | **2116px** | `7 x 292 + 6 x 12`, `routes/deals.index.tsx:770` |
| Quotations table | 980px | `routes/quotations.index.tsx:221` |
| Package table | 900px | `routes/deals.$dealCode.quote.tsx:1710` |
| Files table | 832px (`52rem`) | `routes/documents.files.tsx:198` |
| Milestones table | 896px (`56rem`) | `components/aura/JobMilestonesPanel.tsx:385` |

**Both boards scroll horizontally on every monitor anyone in this studio
owns.** The jobs board needs 2284px; a 1920px monitor gives it 1616px, so four
of the eight production stages are off-screen at rest, with no visual signifier
that they exist beyond the scroll container's edge.

Fifteen containers carry a hard `min-w-[...]`; 37 regions carry
`overflow-x-auto`.

### 2.4 The width is distributed backwards

Inside the cost-line editor, the fixed column widths are
(`routes/deals.$dealCode.quote.tsx:322-323`):

```
DESCRIPTION_WIDTH = 180
TAIL_WIDTHS       = [150, 72, 90, 72, 90, 150, 150, 78, 78, 132, 132, 132, 84]
                     pkg  q1  u1  q2  u2  price tax  mf% mk% sub  quote margin ⋯
```

- **Description - the one column a human reads as prose, and the one that
  carries the Vietnamese - gets 180px.** At 14px that is roughly 24 characters
  before wrapping.
- The three derived money columns get 132px each, **396px between them**, and
  are `sticky` so they never scroll away.
- Four of the five quantity/unit columns are 72-90px for values that are
  usually one or two characters.

So the founder's second complaint is exactly right and can be stated as
arithmetic: **the money columns hold 2.2x the width of the prose column, and
they are the columns that never move.** Elsewhere the same page runs a
185-character card subtitle across 2256px of unconstrained width.

The app already knows the better pattern. `routes/finance.overhead.tsx` puts
`className="w-full"` on the *prose* `<Th>` and lets the money columns
shrink-to-fit (lines 349, 492, 623, 760, 990). That table is fluid, has no
`min-w`, and reads correctly at every width. It is the only family of tables in
the app that does.

### 2.5 Type scale

| Class | Occurrences in `routes/` + `components/aura/` |
|---|---|
| `text-xs` (12px) | 386 |
| `text-[11px]` | 59 |
| `text-[10px]` | 3 |
| `label-caps` (10px, uppercase, `styles.css:174`) | 71 files-worth of uses |

`<Td>` is `text-sm` (14px). **Nothing in this application is 16px.** Table
column headers are 10px uppercase. The default browser body size is 16px; this
app runs its entire chrome at 12px and its densest content at 10-11px. That is
a deliberate-looking choice with no docstring defending it, and it multiplies
every other density problem: shrinking type is how you fit too much on a
screen without admitting that you did.

### 2.6 Heading structure

The whole application contains **three `<h1>` and seven `<h2>`. There is no
`<h3>` anywhere.** `Card` renders its title as `<h2>`
(`components/aura/primitives.tsx:261`); every sub-heading below that is
`label-caps`, which is a `<div>`. On `routes/finance.overhead.tsx` that means
one `<h1>`, five `<h2>`, and eight visually-obvious section labels with no
programmatic existence at all.

## 3. What the three products actually do

Three sourcing notes before the content, because they change what can honestly
be claimed:

- **Several famous Linear quotes are no longer primary sources.** There is no
  page titled "Opinionated software" on linear.app; the nearest real principle
  is **"Purpose-built."** The line *"no spinners, no waiting, no problems"* is
  not on the current site. There is **no Linear page stating a ⌘K philosophy**
  and no `linear.app/docs/keyboard-shortcuts` page at all — only per-feature
  shortcut lists. Anything cited below is quoted from a page that exists today.
- **Atlassian publishes fewer numbers than its reputation suggests.** ADS gives
  no maximum tab count, no table column limit, no horizontal-scroll rule and no
  characters-per-line measure. Where it *does* give a number it is quoted
  exactly.
- **`atlassian.design`'s Side navigation and Page layout components are
  deprecated.** The current one is **Navigation system**, and its numbers are
  the ones used here.

### 3.1 Where they genuinely disagree

This matters more than any consensus, because AuraOS has to pick one.

**On configurability, Linear and ClickUp are opposites, and both say so in
their own words.**

Linear, [linear.app/method/introduction](https://linear.app/method/introduction):

> "**Purpose-built** — Productivity software needs to be designed for purpose.
> It's the only way the product can truly do the heavy lifting. **Flexible
> software lets everyone invent their own workflows, which eventually creates
> chaos as teams scale.**"

> "**Say no to busy work** — Your tools should not make you the designer and
> maintainer of them."

ClickUp, [clickup.com/about](https://clickup.com/about):

> "Teams juggle dozens of disconnected tools... **So we built one platform to
> replace them all.**"

and, [help.clickup.com](https://help.clickup.com/hc/en-us/articles/9559764679831-Customizable-ClickUp-features):

> "**ClickUp is an incredibly customizable platform.**" — with **17 view
> types**, per-Space **ClickApps** toggling fifteen named features on and off,
> and five-level Custom Field permissions.

Jira sits in the middle and is closest to ClickUp: three view types per queue
([support.atlassian.com](https://support.atlassian.com/jira-service-management-cloud/docs/switch-between-views-for-different-ways-to-visualize-your-work-items/)),
per-space field layouts, per-user board view settings, and a dashboard anyone
can build.

**Which fits a one-founder studio: Linear, decisively.** ClickUp's model
requires a person whose job is configuring ClickUp. Its own docs say only
Workspace owners and admins can toggle ClickApps, and that "Members can view,
but not activate or deactivate" them
([help.clickup.com](https://help.clickup.com/hc/en-us/articles/6304327753111-Intro-to-ClickApps)).
In a studio of one founder, some producers, and crew, that administrator is the
founder — the same person who is currently unhappy that the app is confusing.
Handing them a settings surface is handing them more work, which is the exact
failure mode Linear names as "busy work."

**AuraOS has already made Linear's bet.** It has one settings screen, no view
builder, no custom fields, no per-user feature toggles, and a navigation that
is decided by `auraos.api.session_scope` on the server rather than configured.
That is the right bet and §7 defends it. The problem is that the app is not yet
collecting Linear's *payoff* — restraint about what appears on one screen, the
keyboard affordances, and speed you can feel — while it has already paid
Linear's price, which is that when a screen is wrong there is no setting the
user can reach to fix it.

**Where Linear and AuraOS actually disagree, and AuraOS is right.** Linear's
principles include:

> "**Aim for clarity** — **Don't invent terms if possible**, as these can
> confuse and have different meanings in different teams. **Projects should be
> called projects.**"
> — [linear.app/method/introduction](https://linear.app/method/introduction)

`CONTEXT.md` does the opposite and does it deliberately, down to an `_Avoid_`
list that forbids "project" for **Job**. This is a real disagreement, not a
misreading. **Judgement: AuraOS wins it**, for two reasons. First, Linear's
rule is about not inventing synonyms for *universal* concepts, and most of this
glossary is not invented — Advance, Float, Overhead, Contribution and
Receivables are ordinary Vietnamese-business accounting words rendered in
English, not neologisms. Second, where the glossary does deviate it argues the
semantic difference rather than asserting a preference: a **Job** is "a won
deal in production, carrying that deal's breakdown, packages and client
unchanged... the numbers it carries are a snapshot", which is a narrower and
more load-bearing thing than a project. Linear's principle would be right if
these were synonyms. They are not.

### 3.2 Layout width — the one question with published numbers

This is the strongest source in the whole document, and it is Atlassian's.

[atlassian.design/foundations/grid](https://atlassian.design/foundations/grid):

> "**Fixed-wide has a maximum width of 1296px (including margins). Use this as
> the default for most experiences.**"

> "**Fixed-narrow has a maximum width of 864px (including margins). Use this
> for long-form content such as blogs and articles, to limit line length and
> increase readability.**"

> "Fluid grids fill the available space... **Use sparingly, because at very
> large viewports, text lines can become too long and visual relationships
> between elements may break down.**"

And a table naming exactly which is which:

| ADS grid | Max width | Use for |
|---|---|---|
| Fixed-wide | **1296px** | "Dashboards, directories, search results" |
| Fixed-narrow | **864px** | "Blogs, articles, documentation" |
| Fluid | none | "**Kanban boards, whiteboards**" |

> "**Don't use fixed-wide grids for long-form content like blogs and articles.
> Long line lengths impair readability.**"

**AuraOS is fluid everywhere** (§2.3): `<main>` carries no maximum, and its
Home dashboard, its Finance reports and its Settings screen — all "dashboards,
directories" by ADS's own classification — stretch to 2256px on a large
monitor. Atlassian says fluid is for kanban boards. AuraOS has two kanban
boards, and they are the only two screens where fluid is correct.

That is §6.5's entire argument, from a primary source, with a number.
W3C supplies the only citable measure figure — SC 1.4.8 (AAA): *"Width is no
more than 80 characters or glyphs (40 if CJK)"*
([w3.org](https://www.w3.org/WAI/WCAG22/Understanding/visual-presentation.html)).
NN/g publishes **no** characters-per-line number; its legibility article is
qualitative
([nngroup.com](https://www.nngroup.com/articles/legibility-readability-comprehension/)).
Neither does ADS. Do not let anyone tell you otherwise.

### 3.3 Sidebar width and what happens on a phone

[atlassian.design/components/navigation-system/layout](https://atlassian.design/components/navigation-system/layout):

> "**The default width of the side nav is 320px.**"
> "**The side nav can be resized to a minimum width of 240px and a maximum
> width equal to 50% of the viewport width.**"
> "At **s, xs, and xxs** breakpoints (i.e. viewports **smaller than 1024px**),
> **the side nav automatically collapses** to make room for the content."
> "At xs and xxs (smaller than 768px), the max width of the overlay side nav is
> **either 320px or 90% of the screen width — whichever value is smaller**."

AuraOS's sidebar is a fixed 256px — inside Atlassian's 240-320px range, so the
width is fine — and it **disappears** below 1024px rather than collapsing to an
overlay. **AuraOS picked Atlassian's exact breakpoint and skipped Atlassian's
overlay.** That is §5.3 and §6.14, stated as precisely as it can be stated.

Atlassian also publishes a rule AuraOS should adopt while it is in there:

> "**Always include the skip link menu if a substantial number of tab presses
> are required to reach the main content.**"
> "**Make sure there are no more than 4 or 5 elements in the skip link menu.**"
> — [atlassian.design/components/page-layout/usage](https://atlassian.design/components/page-layout/usage)

There is no skip link in AuraOS. With 11 sidebar links plus a logout button,
reaching `<main>` costs 12 tab presses on every page — and per §5.1, invisibly.

### 3.4 How many things belong in a sidebar

Linear's sidebar, from
[linear.app/docs/layout](https://linear.app/docs/layout) and the product shot
on [linear.app](https://linear.app/): four personal items — **Inbox, My issues,
Reviews, Pulse** — then a **Workspace** group (Initiatives, Projects, More),
then **Favorites**, then **Teams**. Team pages expand to *"Triage, Issues,
Cycles, Projects, and Views"*, and crucially:

> "Some items depend on team settings and features — for example, **Triage only
> appears when it's enabled.**"
> — [linear.app/docs/default-team-pages](https://linear.app/docs/default-team-pages)

**That is exactly AuraOS's doctrine**, arrived at independently and written into
`AppShell.tsx:38-42`: *"a nav full of links that answer 403 is worse than a
shorter nav."* Credit where it is due — this is the part of Linear AuraOS
already has.

What AuraOS does not have is Linear's *count*. Linear puts roughly six things
at the top level and pushes everything else into teams and saved views. AuraOS
offers **21 destinations without opening a record** (§2.1), nine of them behind
one word.

Atlassian's rule for the same problem:

> "**Keep nested navigation levels to a minimum. If you need to use a nested
> navigation, always provide a 'go back' button to help people get out of the
> menu.**"
> — [atlassian.design/components/side-navigation/usage](https://atlassian.design/components/side-navigation/usage)

### 3.5 Tabs — and where Atlassian would tell AuraOS it is wrong

[atlassian.design/components/tabs/usage](https://atlassian.design/components/tabs/usage):

> "**Surface important information outside of tabs, and keep the number of tabs
> low wherever possible** in order to increase the visibility of content."
> "**Use tabs to switch between views within the same context.**"
> "**Don't use tabs to navigate to different pages, or states.**"
> "**Use headings or information related to all tabs above the tab line.**"
> "**Prioritize tabs by importance or most frequently used.**"
> "Write clear and concise tab labels (**usually 1-2 words**)."
> "**Keyboard users can navigate between tabs using the left and right arrow
> keys. The tab key is used to navigate to the tab content, not to the next
> tab.**"

NN/g adds the same conclusion from a different direction —
*"**The fewer tabs, the better**"*, and tabs are appropriate *"When there are
few content groupings"*
([nngroup.com](https://www.nngroup.com/articles/tabs-used-right/)).

**Neither publishes a maximum number.** I checked; ADS's machine summary says
only "Limit the number of tabs to avoid overcrowding". So "nine is too many" is
a judgement, not a citation. What *is* citable is the shape of the failure:
nine flat peers with 1-2 word labels, two of which do not match the heading
they lead to (§6.3), fail ADS's "prioritize tabs by importance" and NN/g's
information-scent test at once.

**The genuine disagreement**: ADS says *don't use tabs to navigate to different
pages* — and AuraOS's Finance and Documents strips are exactly that. They are
`<Link>`s to routes, styled as tabs. `DocumentsTabs.tsx`'s docstring defends
the choice explicitly: *"Route tabs rather than in-page state, which is what
ContactsTabs and FinanceTabs already do here."*

By ADS's rule those nine Finance destinations should be **second-level side
navigation**, not a tab strip. **Judgement: I would not do that**, and the
reason is Linear's, not Atlassian's — moving nine items into the sidebar takes
a sidebar of eleven to a sidebar of nineteen, which is worse. §6.9's grouping
is the compromise: keep them as route tabs, keep them in the header, but stop
presenting nine unrelated things as nine equal peers. Say plainly that this
deviates from ADS.

Where AuraOS is unambiguously right: `FinanceTabs` and `DocumentsTabs` are real
links in a `<nav>` and therefore do **not** claim `role="tablist"`. The two
places that *do* claim it (§5.4) are the two that fail ADS's arrow-key rule and
the [APG pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/) with it.

### 3.6 Density and hierarchy — what each product says goes on a screen

**Atlassian is the most directly useful, and it contradicts AuraOS twice.**

[atlassian.design/foundations/spacing](https://atlassian.design/foundations/spacing):

> "**Create order and hierarchy** — Users look for order in visual information
> to reduce the mental effort required to scan and process data... varying the
> amount of whitespace around an element can be used to group elements together
> or separate them to impart greater importance."
> Do: "Use scale and whitespace to rank elements."
> **Don't: "Don't give every element the same visual importance."**

That last line is the founder's third complaint, written by Atlassian. Home's
five identical `<Stat>` tiles (§4.1) and Deals' five identical stage tiles
(§4.2) are precisely "every element the same visual importance."

[atlassian.design/foundations/typography](https://atlassian.design/foundations/typography):

> `font.body` is **14px/20px** — "**Body M (Default) is the default size in
> components or where space is limited**"
> `font.body.small` is **12px/16px** — "**should be used sparingly**... fine
> print"

AuraOS uses 12px **386 times** as its default (§2.5). Atlassian calls 12px fine
print. That is the citation behind §6.15.

Same page, two more rules AuraOS breaks:

> "**Headings should be used to introduce a new section of content. Use heading
> styles, rather than bold or a change of font size, as they're important for
> accessibility.**"
> "**Heading levels (`<h1>` to `<h6>`) should be used in a descending sequence.
> Only use one h1 per page... and don't skip a level.**"

AuraOS has three `<h1>`, seven `<h2>`, no `<h3>`, and 71 uses of `label-caps` —
a 10px uppercase `<div>` — doing the job of a heading (§2.6).

And on capitalisation, from
[atlassian.design/foundations/content/language-and-grammar](https://atlassian.design/foundations/content/language-and-grammar):

> "**Use sentence case in all titles, headings, menu items, labels, and
> buttons.**"

with the Lozenge page repeating it —
*"Don't use title case capitalization or all caps"*
([atlassian.design](https://atlassian.design/components/lozenge/usage)).
`label-caps` is `text-transform: uppercase` at 10px, on every stat label, every
table header and every sidebar section title. **Judgement: I am not
recommending changing this.** It is a coherent typographic voice, it is used
consistently, and ADS's rule is a house style rather than a usability finding.
Noted so that nobody reads its absence from §6 as an oversight.

**Linear's density position** is narrower than folklore suggests. There is no
Linear page against dashboards — Linear ships Dashboards, and their docs even
describe hiding filters *"to reduce visual clutter"*
([linear.app/docs/dashboards](https://linear.app/docs/dashboards)). What Linear
does say, from its own redesign write-up:

> "We've adjusted the **sidebar, tabs, headers, and panels to reduce visual
> noise, maintain visual alignment, and increase the hierarchy and density of
> navigation elements.**"
> "It was definitely a challenge given the amount of UI elements we have on
> this tiny surface. This part of the redesign isn't something you'll
> immediately see but rather something that you'll **feel** after a few minutes
> of using the app."
> — [linear.app/now/how-we-redesigned-the-linear-ui](https://linear.app/now/how-we-redesigned-the-linear-ui)

Note that Linear *increased* density of navigation while reducing noise. Those
are not the same axis, and conflating them is how "declutter" turns into
"delete features."

Linear on scoping what goes in front of a person at all:

> "**Scope issues to be as small as possible** — It's hard to see visible
> progress when working on large tasks."
> "**Write project specs** — Aim for brevity. **Short specs are more likely to
> be read.**"
> "**Keep a manageable backlog** — You don't need to save every feature request
> or piece of feedback indefinitely."
> — [linear.app/method/introduction](https://linear.app/method/introduction)

**ClickUp's density position is the honest opposite and it is worth taking
seriously**, because ClickUp serves teams whose screens really are dense. Its
answer is not less information; it is per-view, per-user controls over
information:

> "**Table view lets you choose the information to display.**" and a documented
> **Customize → Layout options → Row height** control
> ([help.clickup.com](https://help.clickup.com/hc/en-us/articles/6329880717719-Intro-to-views))
> — see also
> [Create and share a Table view](https://help.clickup.com/hc/en-us/articles/6329890854935-Create-and-share-a-Table-view)
> and the List-view toggles at
> [Customize List view](https://help.clickup.com/hc/en-us/articles/7255389296919-Customize-List-view):
> "Show empty statuses", "Wrap text", "Hide tags from task name", "Show closed
> tasks", "Show task properties", **"You can save space in your view by
> collapsing the Lists you're not using"**, **"You can click Hide to
> temporarily remove the header in List view"**, and **Me Mode**.

**Jira's answer is the most directly transplantable**, and it is the one thing
in this document Jira is genuinely best at
([support.atlassian.com](https://support.atlassian.com/jira-software-cloud/docs/configure-field-layout-in-the-work-item/)):

> "**Description fields** — This section usually appears on the left side of
> the work item... **Since this is the first place users look when they open a
> work item, put your most important fields here.**"
> "**Context fields** — This section normally appears down the right side...
> Context fields usually contain **secondary information**."
> "**Hide when empty** — The context fields section has a **divider**... Fields
> above the hide when empty are shown in the **Details** group and those below
> the line are **hidden under the More fields group when they don't have a
> value. When a field in the More fields group has a value, it moves to the
> Details group.**"

That is progressive disclosure with a rule instead of a preference: **empty
means collapsed, populated means promoted.** It is the right answer for
`deals.$dealCode.index.tsx`'s twelve-field card, and it needs no settings
screen — which is why it fits a Linear-shaped app.

Jira also caps card density with an actual number:

> "You can also configure cards on a board to display **up to three additional
> fields**." and "**Note that view settings are applied per user**."
> — [support.atlassian.com](https://support.atlassian.com/jira-software-cloud/docs/customize-your-view-of-the-board-and-backlog/)

And NN/g supplies the principle all three are circling:

> "**Every extra unit of information in an interface competes with the relevant
> units of information and diminishes their relative visibility.**"
> — [nngroup.com](https://www.nngroup.com/articles/ten-usability-heuristics/)

with the necessary corrective, from the full article: minimalist is **not**
sparse — *"too few elements inhibit utility through absence"*
([nngroup.com](https://www.nngroup.com/articles/aesthetic-minimalist-design/)).
That corrective is why §7 exists.

### 3.7 Keyboard, speed and URLs

**Linear's docs are structured keyboard-first** — most pages carry a
**Keyboard | Mouse | Command menu** tab block, in that order. Verified
shortcuts include `/` for search, `Cmd/Ctrl F` to search within the current
view, `G then I` / `G then M` for Inbox and My Issues, `F` for the filter menu,
`Shift V` for display options, `Cmd/Ctrl B` to swap list and board, and
`Alt V` to save a view
([linear.app/docs/search](https://linear.app/docs/search),
[/docs/display-options](https://linear.app/docs/display-options),
[/docs/custom-views](https://linear.app/docs/custom-views)).

**AuraOS has two keyboard shortcuts** — `Ctrl+S` on two deal screens — and a
non-functional `⌘K` chip on all 27 (§6.12).

**On speed**, the citable Linear source is its engineering blog, not marketing:

> "**Linear is a local-first application. Each client maintains a local
> database so that creating an issue, changing its status, or navigating a
> workspace doesn't require a network round trip. That makes the app feel
> immediate**, but the tradeoff is that a client returning online needs a way
> to catch up, fast."
> — [linear.app/now/rebuilding-delta-sync-read-path](https://linear.app/now/rebuilding-delta-sync-read-path)

**AuraOS should not attempt this**, and it is not on the recommendation list.
It is a Frappe SPA with a `@tanstack/react-query` cache and a documented
30-second stale time (`lib/queries.ts`), and every money figure is computed
server-side on purpose (§7.2). Local-first would put the arithmetic back in the
browser, which is the one thing the codebase most consistently refuses. What is
worth borrowing is the *perceptual* half, which AuraOS already largely has —
see §3.8.

**On URLs**, Linear:

> "The applied filters are also **reflected in the browser URL. You can copy the
> browser address to share the filtered view**; opening the link applies the
> same filters."
> — [linear.app/docs/filters](https://linear.app/docs/filters)

AuraOS puts state in the URL in exactly one route — `expense.tsx`'s
`validateSearch`. Every finance date range, every table's column selection,
every job detail tab and every board/table toggle is either component state or
`localStorage`. Nobody in this studio can send a colleague a link to what they
are looking at. §6.11 starts on this; the general fix is larger.

Linear's model for *defaults* rather than settings is the one to copy:

> "Display options can be saved as personal preferences **or as the default
> display options on that page for your workspace**... It will be the view they
> see when they first open it, **but they can always apply their own
> preferences on top of it**."
> — [linear.app/docs/display-options](https://linear.app/docs/display-options)

That is the shape of §6.13: a good default, overridable per user, with no
settings screen involved.

### 3.8 Where AuraOS already matches or beats the benchmark

Saying this is not politeness; a document that only accuses is easy to
dismiss.

- **Loading states.** `components/aura/states.tsx` uses skeletons, not
  spinners, and its docstring says *"A skeleton, not a spinner: it holds the
  shape of what is coming, so the layout does not jump when it arrives."*
  Atlassian: *"**Use skeletons to reserve space for content while data is
  loading. Match the size and shape of the expected content so the page does
  not jump when loading completes.**"*
  ([atlassian.design](https://atlassian.design/components/skeleton/usage)) and
  *"We should be striving for UI that feels stable, which means it doesn't jump
  around when content loads"*
  ([atlassian.design](https://atlassian.design/components/side-navigation/usage)).
  Near-verbatim agreement, independently arrived at. `<Figure>` even holds a
  number's width so a stat tile cannot resize under the reader.
- **One representation each of loading, empty and error**, with `<QueryState>`
  resolving all three so *"the happy path is the only branch a screen writes by
  hand"*. This is stronger than anything ADS mandates.
- **Empty states are calm and never alarm-coloured** — *"a new company with no
  data has to read as calm"*. ADS: an empty state *"can be a chance to
  celebrate, educate, and inform people of what they can do next"*, and for a
  blank slate the tone should be *"inspirational, motivating, or educational"*
  ([atlassian.design](https://atlassian.design/components/empty-state/usage)).
  AuraOS's `Empty` takes an optional `action`, which is ADS's *"Include an
  action or link to help people understand what to do next."*
- **Error states show the server's own sentences** rather than a generic line,
  and distinguish session / permission / network / validation. NN/g heuristic
  #9: *"Error messages should be expressed in plain language (no error codes),
  precisely indicate the problem, and constructively suggest a solution"*
  ([nngroup.com](https://www.nngroup.com/articles/ten-usability-heuristics/)).
  *"You do not have access to this. Ask the founder if you think you should."*
  is better than most enterprise software manages.
- **Permission-shaped navigation** matches Linear's feature-gated nav items and
  ClickUp's role-limited sidebar (§3.4, §7.4), with a stronger backend
  guarantee than either.
- **Sticky first column and sticky money band** on the cost-line table is
  exactly NN/g's data-table recommendation and ClickUp's pinned-column feature
  (§4.3).
- **The detail-columns picker defaults to off** — progressive disclosure done
  correctly, in the app's most complex screen.

One number that cuts the other way, and belongs here for honesty: Atlassian's
Progress indicator usage page says *"**Use a maximum of seven steps in your
journey so that people aren't overwhelmed**"*
([atlassian.design](https://atlassian.design/components/progress-indicator/usage)).
The job stage chip trail is **eight**. The eight production stages are a domain
fact (`components/aura/job.ts:15-24`), not a design choice, so this is an
observation rather than a recommendation — but it is one more reason the job
detail header does not need a second control saying the same thing (§4.4).

## 4. Screen by screen: where the eye goes, and where it should

The founder's third complaint — that the scanning flow is not intuitive — is
downstream of the first two, but it is testable on its own. NN/g's eye-tracking
work gives two patterns to check against. The **layer-cake** pattern is what
you want: *"fixations made mostly on the page's headings and subheadings, with
deliberate occasional fixations on the (body) text in between"*, which lets
people *"quickly identify the content that is most relevant to their task"*
([nngroup.com](https://www.nngroup.com/articles/layer-cake-pattern-scanning/)).
The **F-shaped** pattern is the failure mode: it happens when there are no
strong cues, users *"choose the path of minimum effort"*, and they *"miss big
chunks of content based merely on how text flows in a column"*
([nngroup.com](https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content/)).

And the budget for getting it right is small. NN/g measured **57% of
page-viewing time above the fold** and **74% in the first two screenfuls**,
with **42% of viewing time in the top 20% of the page**; their recommendation
is to *"reserve the top of the page for high-priority content"*
([nngroup.com](https://www.nngroup.com/articles/scrolling-and-attention/)).

Here is what the top 20% of each major screen actually contains.

### 4.1 Home (`routes/index.tsx`) — five things of equal weight

**Top of page:** an `<h1>` greeting, a meta line, and then
`grid gap-3 sm:grid-cols-2 xl:grid-cols-5` of five identical `<Stat>` tiles
(four for a producer): Pipeline, Weighted projection, In production, Overdue
payments, Quotes gone quiet.

The tiles are visually identical — same border, same padding, same
`text-xl font-semibold` number, same `label-caps` label. Two of them carry an
`alert` flag that turns the number ember, but §5.2 shows ember at 3.45:1 is the
*least* legible colour on the palette, so the one signal that distinguishes
urgency is the one hardest to see.

**The screen already knows the answer and buries it.** Below the tiles sits a
card titled **"Needs attention"** with the subtitle *"Money that has stopped
moving, worst first"* (line 389) — which is exactly the right idea, exactly the right
name, and is the second thing on the page rather than the first.

Two smaller notes on that card:
- The claim "worst first" is only partly kept. `overdue_milestones` arrives
  ordered `due_on asc` from the server
  (`job_payment_milestone.py:234`), so the milestones are worst-first among
  themselves; but `routes/index.tsx:265-281` then **concatenates** the silent
  quotes after them with no sort across the two groups. A quote silent for
  ninety days sorts below a milestone one day late.
- For a producer, four tiles of pipeline/production/overdue/silence sit above
  a card of things to chase. Their actual work is on `/my-work`.

**Judgement:** lead with "Needs attention". Demote the tiles to a single row of
small figures, or move them under it. The founder's complaint that "a screen
that opens with four equal-weight stat tiles has said nothing about which of
the four the reader should act on" is a precise description of this screen.

### 4.2 Deals board (`routes/deals.index.tsx`) — every number printed twice

Covered in §2.2 and §6.4. Top 20% of the page: five stage tiles with counts and
money. Immediately below: a seven-column board whose headers carry the same
counts and the same money. Then, off the right edge on every monitor (2116px of
board in ≤1616px of column), the Won and Lost columns.

The table view is the more interesting half and is well built — a live blank
row at the top so *"a deal starts by being typed, not by opening a form"*
(line 1275), a persisted per-user column picker, server-side search. It is not
the default; kanban is (`loadPrefs`, line 180). **Judgement:** that default is
defensible and I would not change it, but the duplicated tile row is only
visible in the kanban default, which is why deleting it there is worth doing.

### 4.3 Quote / breakdown editor (`routes/deals.$dealCode.quote.tsx`) — the worst screen, and the most important one

2464 lines. Nine `<Card>`s, stacked vertically: Cost lines, What it adds up to,
Founder only, Phases, Packages, Client terms, Assumptions and exclusions,
Publish a version, plus the versions list. Two tables — one of 14-18 columns at
1590-2180px, one of 9 columns at 900px minimum — both full of editable inputs.

Where the eye goes first: the Cost lines table, which is correct. What it hits
there: a 180px Description column against a 396px frozen money band (§2.4).

What is genuinely good and should be said plainly:
- The **detail-columns picker** (line 1105) with its four optional columns
  defaulting to *off*, persisted per user, with the printed rule *"Money
  columns are always shown."* That is textbook progressive disclosure — *"show
  users only a few of the most important options"*, then *"offer a larger set
  of specialized options upon request"*
  ([nngroup.com](https://www.nngroup.com/articles/progressive-disclosure/)).
- The **sticky first column and sticky money band**, which is NN/g's explicit
  recommendation for tables wider than the screen
  ([nngroup.com](https://www.nngroup.com/articles/data-tables/)).
- The **autosave status line** (line 1033-1041) naming four distinct states in
  plain sentences, including *"A line needs a description, or a package needs a
  title - autosave is waiting"* — heuristic #1 done properly.
- Every card subtitle explains **who computed the number**: *"Subtotal, quote
  price and margin are computed by the pricing engine, not in this browser."*

What is wrong is width and stacking, not information. **Judgement:** the nine
cards are nine genuinely different things and merging them would be worse. But
Cost lines / Packages / Phases is one task, and Client terms / Assumptions /
Publish is another, and the screen makes no distinction between them — it is
nine equal cards in one column. Splitting the page at that seam is a bigger
change than anything in §6 and I have not costed it; §6.6's width rebalance is
the cheap 80%.

### 4.4 Job detail (`routes/jobs.$jobId.tsx`) — two controls for one action

The densest single route: 9 cards, a 4-tile stat row, 2 tables, four tabs, plus
four imported panels that bring another 7 cards and 5 tables between them.

The specific confusion is at the top. Within the first 20% of the page a
reader meets **two different controls that do the same thing**:

1. `actions` slot, line 170: a `<select aria-label="Production stage">` with all
   eight stages.
2. body, line 190: a chip trail of eight `<button>`s, styled as a progress
   indicator, each of which also moves the job.

One is a form control, one looks like a status display. Both write. NN/g
heuristic #4: *"Users should not have to wonder whether different words,
situations, or actions mean the same thing"*
([nngroup.com](https://www.nngroup.com/articles/ten-usability-heuristics/)).

**Judgement:** keep the chip trail — it shows position *and* affords the move,
which the select cannot — and drop the select, or reduce it to a read-only
badge. This is an XS change I did not put in §6's table only because it is a
product decision rather than a defect.

The tabs are the right structure for this page and meet four of NN/g's five
conditions for tabs — clear groupings, few of them, unequal importance,
one-word labels, no need to see two at once
([nngroup.com](https://www.nngroup.com/articles/tabs-used-right/)). They fail
only on keyboard (§5.4) and on not being in the URL (§6.11).

### 4.5 Finance (nine tabs) — the H1 does not match the door you came through

Covered in §2.1, §6.3 and §7.5. The individual screens are among the best in
the app: `finance.overhead.tsx` has the most careful docstring in the codebase
and the only correctly-fluid tables; `finance.bank.tsx` argues its own density
(*"The two unmatched lists are the product"*); `finance.forecast.tsx` refuses
to call an estimate a total.

The confusion is entirely at the seam between them: a nine-item flat strip, two
tab labels that disagree with the page's `<h1>`, one page that shows the
section name instead of its own, and one page that renders the strip in a
different place so it jumps.

### 4.6 My work (`routes/my-work.index.tsx`) — the least confusing screen in the app

One card, one list, one `<Pill>` per row, no money by construction. It is worth
naming as the counter-example: when a screen answers one question, this app is
already good at it. Nothing to change here.

### 4.7 Quick expense (`routes/expense.tsx`) — right design, wrong reachability

Single narrow column, amount focused on arrival, thumb-sized full-width save.
The docstring is explicit that it is for *"a producer on set, holding a receipt,
one hand on the phone."* It is also the only route in the app that puts state
in the URL (`validateSearch`, line 28).

And it is unreachable on a phone, because the sidebar that links to it is
`hidden ... lg:flex` (§5.3). The best mobile screen in the app cannot be
reached on mobile.

## 5. Accessibility, measured

These are not style opinions. Each is a named WCAG 2.2 success criterion with the app's measured value beside it.

### 5.1 Focus is invisible — SC 2.4.7 Focus Visible (Level A)

> "Any keyboard operable user interface has a mode of operation where the keyboard focus indicator is visible."
> — [WCAG 2.2 SC 2.4.7](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html)

Measured:

- `outline-none` appears **63 times across 23 files** in `routes/` and `components/aura/`.
- `focus-visible` appears **zero times** in `routes/` or `components/aura/`.
- `styles.css` contains no `:focus`, `:focus-visible` or `outline` rule.
- The `--ring` token *is* defined (`styles.css:93`, the ember orange) and is used only by `components/ui/`, which nothing in the app imports.
- What replaces the outline is `focus:border-border-strong` on `inputClass` (`components/aura/primitives.tsx:401`): the border moves from `oklch(0.925)` to `oklch(0.88)`. The contrast of that change against itself is **1.15:1**; the resulting border against a white card is **1.44:1**.

SC 1.4.11 Non-text Contrast asks 3:1 for the visual information needed to identify component state. 1.44:1 is not a focus indicator; it is a rumour of one. **This is the highest value-per-hour item in the whole document** — one rule in `styles.css`, using the `--ring` token that already exists.

### 5.2 The alert colour fails contrast in light mode — SC 1.4.3 (Level AA)

> "The visual presentation of text and images of text has a contrast ratio of at least 4.5:1", with an exception for large text at 3:1.
> — [WCAG 2.2 SC 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)

Computed from the OKLCH tokens in `styles.css`, converted through OKLab to linear sRGB and then to WCAG relative luminance:

| Pair | Light | Dark |
|---|---|---|
| `--foreground` on `--card` | 17.91:1 | 15.29:1 |
| `--muted-foreground` on `--card` | 5.51:1 | 6.72:1 |
| `--positive` on `--card` | 4.58:1 | — |
| **`--ember` on `--card`** | **3.45:1 — fails** | 5.82:1 |
| **`--ember` on `--ember-soft`** (`<Pill tone="ember">`) | **2.99:1 — fails** | 4.51:1 |
| `--border` on `--card` | 1.25:1 | — |

Ember is the app's urgency colour: the `alert` state of `<Stat>`, the overdue dot on the job Money tab, `<Pill tone="ember">Founder only</Pill>`, the active nav icon, the active tab underline. It is used at `text-[11px]` inside pills and `text-xs` in prose — both well under the 18.66px-bold / 24px large-text threshold, so 4.5:1 applies and both values fail.

The stat *number* is `text-xl font-semibold` (20px bold), which does qualify as large text, so at 3.45:1 that one usage passes. Everything smaller does not.

Dark mode passes on every pair. Fixing light mode is a token change, not a redesign.

### 5.3 Below 1024px there is no navigation — SC 1.4.10 Reflow (Level AA)

> "Content can be presented without loss of information or functionality, and without requiring scrolling in two dimensions for: Vertical scrolling content at a width equivalent to 320 CSS pixels..."
> — [WCAG 2.2 SC 1.4.10](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html)

`AppShell.tsx:136` is `<aside className="sticky top-0 hidden h-screen w-64 ... lg:flex">`. There is no `lg:hidden` counterpart anywhere in the file — no drawer, no sheet, no hamburger. Below Tailwind's `lg` (1024px) the navigation is simply gone. Loss of functionality is loss of functionality; this is a Reflow failure, and more to the point it is why nobody uses this app on a phone.

The one screen built for a phone — `routes/expense.tsx`, whose docstring says it is "used standing up: a producer on set, holding a receipt, one hand on the phone" — is reachable only from the sidebar link that does not exist at that width, or from a job page whose nav is also gone.

The horizontal scrolling in §2.3 is largely *compliant*, and deliberately so: the Reflow Understanding document exempts data tables provided they are "rendered within a scrollable container" so that surrounding content still reflows. The app does exactly that — 37 `overflow-x-auto` wrappers. The problem with the boards and the cost-line table is usability, not conformance.

### 5.4 The tab lists do not implement the tabs pattern

The [WAI-ARIA APG Tabs pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/) requires, for anything using `role="tablist"`:

- **Left/Right Arrow** move focus between tabs, wrapping at the ends
- a **roving tabindex** — only the active tab sits in the page tab sequence
- `aria-label` or `aria-labelledby` on the tablist
- `tabindex="0"` on a tabpanel containing no focusable elements

`routes/jobs.$jobId.tsx:271-300` and `components/aura/JobTasks.tsx:146-155` both declare `role="tablist"` / `role="tab"` / `role="tabpanel"`, and both wire `aria-selected`, `aria-controls` and `aria-labelledby` correctly. Neither has an `onKeyDown` handler, neither manages `tabIndex`, and neither tablist carries a label. So they announce themselves as tabs and then behave as a row of buttons — the worst of both, because a screen-reader user is told to press arrow keys that do nothing.

`FinanceTabs` and `DocumentsTabs` sidestep this correctly by being real links inside a `<nav>` rather than ARIA tabs. That is the right call and should not change. But neither `<nav>` has an `aria-label`, and the app renders three unlabelled `<nav>` landmarks at once (sidebar, finance strip, documents strip).

### 5.5 Language — SC 3.1.1 (A) and SC 3.1.2 (AA)

`frontend-react/index.html:2` is `<html lang="en">`. The attribute `lang` appears nowhere else in the frontend.

> SC 3.1.2 Language of Parts: "The human language of each passage or phrase in the content can be programmatically determined except for proper names, technical terms, words of indeterminate language, and words or phrases that have become part of the vernacular of the immediately surrounding text."
> — [WCAG 2.2 SC 3.1.2](https://www.w3.org/WAI/WCAG22/Understanding/language-of-parts.html)

The app hard-codes Vietnamese passages that are neither proper nouns nor technical terms and are not marked: `"SOP: cách đánh giá và phân loại deal"` (`routes/deals.$dealCode.index.tsx:945`), `"(Không đọc được nội dung file)"` and `"(File này không phải văn bản .docx)"` (`routes/documents.paperwork.tsx:503,521`), the positioning and tier glosses `"nuôi bộ máy" / "gần định vị" / "đúng định vị" / "cơm áo" / "trung bình"` (`deals.$dealCode.index.tsx:73-87`), and the whole `AcceptanceFigures` label set. Plus every row of user-entered Vietnamese in every table on every screen.

The fix is two-part and cheap: set `lang="vi"` on `<html>` — the *content* is predominantly Vietnamese even where the chrome is English — then mark the English chrome strings. Which direction is correct is a judgement the founder should make; what is not a judgement is that the current value is wrong either way.

### 5.6 Drag-only boards

Both boards move records by HTML5 drag-and-drop (`draggable`, `onDragStart`, `onDrop` at `routes/jobs.index.tsx:307,466` and `routes/deals.index.tsx:779,874`) with no keyboard handler on the card. A non-dragging path does exist — the deals table view has an editable stage `<select>`, and the job detail page has both a `<select>` and a chip trail — so SC 2.5.7 Dragging Movements is arguably satisfied, and SC 2.1.1 Keyboard with it.

But the board's own subtitle says only *"Drag a card to move the job."* (`routes/jobs.index.tsx:269`). The alternative is real and undiscoverable. **Judgement:** say it in the subtitle, or make the card's own stage chip a control.

## 6. Recommendations, ordered by value ÷ effort

Effort is in the usual currency: **XS** ≈ under an hour, **S** ≈ half a day,
**M** ≈ one to three days, **L** ≈ a week or more. "Value" is against the
founder's three stated complaints plus the accessibility findings, not against
a general notion of polish.

| # | Change | Value | Effort | Files |
|---|---|---|---|---|
| 1 | One global focus ring | ★★★★★ | XS | `styles.css` |
| 2 | Fix `--ember` in light mode | ★★★★ | XS | `styles.css` |
| 3 | Make Finance's nine tabs tell the truth | ★★★★ | XS | 9 `finance.*.tsx` |
| 4 | Delete the duplicated stat row on Deals | ★★★★ | XS | `deals.index.tsx` |
| 5 | Give `<main>` a max width, with a `wide` escape hatch | ★★★★★ | S | `AppShell.tsx` + ~27 routes (one prop) |
| 6 | Rebalance the cost-line column widths | ★★★★ | S | `deals.$dealCode.quote.tsx` |
| 7 | Vietnamese glosses on the money vocabulary | ★★★★ | S | ~6 screens |
| 8 | `lang` attributes | ★★★ | S | `index.html` + ~8 strings |
| 9 | Group the Finance strip into three named clusters | ★★★ | S | `FinanceTabs.tsx` |
| 10 | Keyboard support on the two ARIA tablists | ★★★ | S | `jobs.$jobId.tsx`, `JobTasks.tsx` |
| 11 | Job detail tab into the URL | ★★★ | S | `jobs.$jobId.tsx` |
| 12 | Decide about ⌘K: build it or delete the chip | ★★★ | XS or L | `AppShell.tsx` |
| 13 | Lean column defaults + extend the column picker | ★★★ | M | `deals.index.tsx`, 4 table screens |
| 14 | A navigation drawer below `lg` | ★★★★ | M | `AppShell.tsx` |
| 15 | Raise the base type scale | ★★★★ | M | `styles.css` + sweep |
| 16 | Delete the dead UI layer | ★ | S | `components/ui/`, `Kanban.tsx`, `primitives.tsx` |
| 17 | Jira's hide-when-empty rule on the deal record | ★★★ | S | `deals.$dealCode.index.tsx` |
| 18 | Two stage controls become one, on the job page | ★★★ | XS | `jobs.$jobId.tsx` |

---

### 6.1 One global focus ring — XS

Add to `styles.css`, using the `--ring` token that is already defined and
currently unused by the app:

```css
:where(a, button, input, select, textarea, summary, [tabindex]):focus-visible {
  outline: 2px solid var(--ring);
  outline-offset: 2px;
}
```

`:where()` keeps specificity at zero so nothing has to be un-styled, and
`:focus-visible` means a mouse click on a button still shows nothing. The 63
`outline-none` occurrences can then be swept, or left — `outline-none` sets
`outline-style: none`, which the rule above overrides on focus because it is
declared later and matches the same element. **Verify by tabbing, not by
grepping.**

Closes the SC 2.4.7 (Level A) failure in §5.1. This is the single highest
value-per-hour item in the document.

### 6.2 Fix `--ember` in light mode — XS

Two tokens in `styles.css`. Darkening `--ember` from `oklch(0.653 0.183 39)`
to roughly `oklch(0.56 0.17 39)` brings it to ≈4.6:1 on `--card` and keeps the
hue; `--ember-soft` needs to lift to hold ≈4.5:1 against it. Check the pair
with a real contrast tool rather than trusting these figures — they are my
arithmetic, not a measurement of a rendered pixel.

Do **not** change the dark palette: §5.2 shows it already passes.

### 6.3 Make Finance's nine tabs tell the truth — XS

Three separate bugs, all in the same family:

1. `routes/finance.bank.tsx:117` renders `<FinanceTabs />` inside `AppShell`'s
   `meta` slot. The other eight render it as the first child of the page body.
   **The tab strip jumps when you click Bank.** Move it into the body.
2. `routes/finance.accounts.tsx:122` has `<h1>Cash accounts</h1>` under a tab
   labelled "Accounts"; `routes/finance.forecast.tsx:174` has
   `<h1>Cash forecast</h1>` under "Forecast". Make the tab label and the `<h1>`
   the same string, in both directions of your choosing.
3. `routes/finance.index.tsx:98` has `<h1>Finance</h1>` under a tab labelled
   "Dashboard", while its eight siblings show their own name. Pick one rule.

NN/g's tabs guidance is directly on point: *"Users should be able to predict
what they'll find when selecting a tab... labels with strong information scent
are crucial"*, and *"Tab labels should usually be 1-2 words"*
([nngroup.com](https://www.nngroup.com/articles/tabs-used-right/)). A tab that
opens a page with a different name has negative information scent — it teaches
the reader that the labels cannot be trusted.

### 6.4 Delete the duplicated stat row on Deals — XS

`routes/deals.index.tsx:554-573` renders a tile per open stage carrying
`items.length` and `sum(estimated_budget)`. Lines 764-800 render the board,
whose column headers carry `items.length` and the same sum. In kanban view —
the default (`loadPrefs`, line 180) — the reader sees every number twice,
sixty pixels apart.

Delete the tile row in kanban view. Keep it in table view, where the board's
column headers are not on screen. This is heuristic #8 in its literal form:
*"Every extra unit of information in an interface competes with the relevant
units of information and diminishes their relative visibility"*
([nngroup.com](https://www.nngroup.com/articles/aesthetic-minimalist-design/)).

### 6.5 Give `<main>` a max width, with a `wide` escape hatch — S

The founder's second complaint, at its root. `AppShell.tsx:213` currently:

```tsx
<main className="min-w-0 flex-1 px-4 py-5 sm:px-6 sm:py-6">{children}</main>
```

Proposal: an inner wrapper with a maximum, plus a `wide` prop on `AppShell` for
the handful of screens that genuinely need every pixel:

```tsx
<main className="min-w-0 flex-1 px-4 py-5 sm:px-6 sm:py-6">
  <div className={cn("mx-auto w-full", wide ? "max-w-none" : "max-w-[1296px]")}>
    {children}
  </div>
</main>
```

**1296px is not a guess.** It is Atlassian's published fixed-wide maximum:
*"Fixed-wide has a maximum width of 1296px (including margins). **Use this as
the default for most experiences**"*, against fluid, which ADS reserves for
*"Kanban boards, whiteboards"* and warns to *"use sparingly, because at very
large viewports, text lines can become too long"*
([atlassian.design/foundations/grid](https://atlassian.design/foundations/grid)).

Which screens get `wide`: **the two boards and the quote editor**, plus bank
reconciliation. That is ADS's own list — kanban is the fluid case. Everything
else — Home, My work, Documents, Settings, Contacts, seven of the nine Finance
tabs — is a "dashboard, directory, search result" in ADS's classification and
belongs at 1296px.

At the app's 12px chrome, a 1296px column is ~210 characters per line, down
from ~375. Still well over WCAG SC 1.4.8's *"no more than 80 characters or
glyphs (40 if CJK)"*
([w3.org](https://www.w3.org/WAI/WCAG22/Understanding/visual-presentation.html)),
which is a AAA criterion nothing here is chasing — but the long card subtitles
in §2.3 would benefit from an additional `max-w-[70ch]` on `Card`'s subtitle
slot, which is a one-line change in `primitives.tsx:264`.

**Judgement, and the honest caveat:** capping the page will make the two boards
and the quote editor feel *tighter*, not looser, which is why they get the
escape hatch. Do not apply this globally and call it done.

### 6.6 Rebalance the cost-line column widths — S

`routes/deals.$dealCode.quote.tsx:322-323`. Today: prose 180px, three derived
money columns 396px between them, four quantity/unit columns 72-90px each for
one-to-two-character values.

Concrete proposal, holding the total roughly flat so nothing else has to move:

- `DESCRIPTION_WIDTH` **180 → 280**
- the three money columns **132 → 116** each (`1.925.000.000` fits at 116px in
  the `num` face; check it)
- `Qty 1` / `Qty 2` **72 → 60**, `Unit 1` / `Unit 2` **90 → 76**

Net table width: 1590px → ≈1610px, i.e. unchanged, with the prose column 55%
wider. That is the whole fix — it is a constant array, not a refactor.

Keeping the money band `sticky` is correct and matches NN/g's data-table
guidance: *"Freeze header rows and header columns (if the table is larger than
the screen)"*
([nngroup.com](https://www.nngroup.com/articles/data-tables/)). ClickUp ships
the same affordance — *"You can pin a column so it stays visible as you scroll
across your Table view"*
([help.clickup.com](https://help.clickup.com/hc/en-us/articles/6329890854935-Create-and-share-a-Table-view)).

**Where the fluid pattern belongs instead:** `routes/finance.overhead.tsx`
already puts `className="w-full"` on the prose `<Th>` and lets the money
columns shrink-to-fit, with no `min-w` at all. Every read-only table in the app
should follow that file rather than the quote editor's fixed layout. The quote
editor is fixed-width for a real reason — the sticky offsets are computed from
the widths (`TAIL_WIDTHS` comment, line 318-322) — so it stays fixed and just
gets better numbers.

### 6.7 Vietnamese glosses on the money vocabulary — S

Copy the Positioning/Tier pattern from `deals.$dealCode.index.tsx:73-86` (see
§8.3) onto the terms that currently appear as bare English labels with no
explanation anywhere on screen: **Contribution**, **Break-even line**,
**Float**, **Advance**, **Quoted cost**, **Profit cost basis**, and the four
**Collection status** values.

`CONTEXT.md` already ships the Vietnamese for the last of these — "Not
requested (chưa yêu cầu) → Requested (đã yêu cầu KT) → Invoiced (đã xuất HĐ) →
Paid (đã thanh toán)" — and `JobMilestonesPanel.tsx` repeats them in *code
comments* (lines 37, 287, 305, 310) while rendering only the English to the
screen. The translation exists; it just never reaches a user.

This renames nothing, touches no `_Avoid_` list, and is a `sub` string on a
`<Stat>` or a second line in an `<option>`. **Judgement: this is the highest
value item in the document that is not an accessibility fix**, because "rối"
for a producer is at least partly not knowing what a word means.

### 6.8 `lang` attributes — S

`index.html:2` → `lang="vi"`, then `lang="en"` on the English chrome that a
Vietnamese screen reader would mispronounce. Or the reverse, marking the
Vietnamese. §5.5 has the criterion; the direction is the founder's call. Do it
in one pass so the two halves cannot disagree.

### 6.9 Group the Finance strip into three named clusters — S

Nine peers at one level, in one flat wrapping row, with no signal about which
are facts and which are estimates and which are founder-only. NN/g: *"When the
number of tabs overflows the tab list, the tab bar often becomes a carousel...
The fewer tabs, the better"*
([nngroup.com](https://www.nngroup.com/articles/tabs-used-right/)).

But §7.5 shows the nine are each a distinct server question, so **do not
merge them**. Group them, the way the sidebar already groups "Contacts" and
"Studio":

- **Now** — Dashboard, Accounts, Bank
- **Record** — Income, Expenses, Receivables
- **Judgement** — Reports, Forecast, Overhead

That split is not arbitrary: it is the one `finance.forecast.tsx`'s own
docstring draws — *"Beside this tab sit Accounts and Receivables, which are
facts — a balance is the ledger's own sum. This is an estimate multiplied by a
guess."* Putting a fact and a guess in visibly different groups is the screen
keeping a promise the docstring already made.

Effort is one component; `FinanceTabs.tsx` is 66 lines.

### 6.10 Keyboard support on the two ARIA tablists — S

`jobs.$jobId.tsx:271` and `JobTasks.tsx:146`. Add Left/Right arrow handling
with wrap, a roving `tabIndex` (`0` on the active tab, `-1` on the rest), and
an `aria-label` on each `tablist`. The
[APG Tabs pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/) has the full
keyboard table; §5.4 has the short version.

Everything else on those two components is already correct, which is why this
is small.

### 6.11 Job detail tab into the URL — S

`jobs.$jobId.tsx:100` holds the tab in `useState`, so `/jobs/JOB-0009` on the
Money tab is not a link anybody can send, and browser Back does not step
between tabs. `expense.tsx:28` is the only route in the app that uses
`validateSearch`; the pattern exists and is used once.

Move the tab to a search param. **Preserve the `hidden`-not-unmounted
behaviour** documented at line 302 — an unsaved plan surviving a tab switch is
deliberate and a route-level swap would destroy it. Keeping all four panels
mounted and driving `hidden` off the search param does both.

Do the same for `documents.library.tsx`'s view toggle if it is cheap; leave
`deals.index`'s alone, since `loadPrefs` deliberately treats view choice as
*"a habit, not data"* and persists it per user.

### 6.12 Decide about ⌘K — XS to delete, L to build

`AppShell.tsx:202-209` renders a `<div>` reading **"Quick actions ⌘K"** with a
keycap badge. It is not a `<button>`, it has no `onClick`, and there is no
global key handler anywhere in the app — `metaKey`/`ctrlKey` appears in exactly
two places, both `Ctrl+S` on deal screens. `cmdk` is installed and
`components/ui/command.tsx` exists; nothing imports it.

So the app advertises a command palette it does not have, in the header of
every screen. That is a promise broken 27 times. Either build it or delete the
chip — **deleting it is XS and is the right call unless a palette is actually
next up.** A visible affordance that does nothing is worse than no affordance:
NN/g measured 22% slower task performance and 25% more fixations on interfaces
with weak signifiers, because *"even when they do see the weak element, they
don't feel confident that it is what they want, so they keep looking around the
page"*
([nngroup.com](https://www.nngroup.com/articles/flat-ui-less-attention-cause-uncertainty/)).

### 6.13 Lean column defaults, and extend the column picker — M

The mechanism already exists and is good. `deals.index.tsx:163-204` persists a
per-user, per-account column selection in `localStorage`, degrades safely when
storage is blocked, and pins required columns. `deals.$dealCode.quote.tsx:329-352`
does the same for the four optional cost-line columns.

Two changes:

1. **The quote editor already defaults correctly** — `loadColumns` returns `[]`,
   so a new user sees 14 columns rather than 18. **`deals.index` does not**:
   `loadPrefs` falls back to `ALL_COLUMN_KEYS`, all eleven. Change the default
   to a lean five (Deal, Client, Stage, Owner, Quote) and let people add back.
2. **Extend the picker** to the four other wide tables — quotations (980px),
   files (832px), milestones (896px), receivables.

This is ClickUp's answer to density, and ClickUp is unusually explicit about
it: *"Table view lets you choose the information to display"*, plus a documented
row-height control under **Customize → Layout options → Row height**
([help.clickup.com](https://help.clickup.com/hc/en-us/articles/6329890854935-Create-and-share-a-Table-view)),
and a long list of List-view show/hide toggles
([help.clickup.com](https://help.clickup.com/hc/en-us/articles/7255389296919-Customize-List-view)).
NN/g agrees for data tables generally: *"Hiding and reordering columns must be
easy to accomplish"*
([nngroup.com](https://www.nngroup.com/articles/data-tables/)).

**The caveat that keeps this at M and not S:** every column you let a user hide
is a column somebody will hide and then not understand why their number moved.
Pin the required ones the way `REQUIRED_COLUMN_KEYS` already does, and never
make a money column hideable — which is exactly the rule the quote editor
already prints on its own picker: *"Money columns are always shown."*

### 6.14 A navigation drawer below `lg` — M

§5.3. A hamburger in the header and the existing `primaryNav`/`contactsNav`/
`footNav` arrays rendered into a slide-over. The nav data structure and the
`reachable()` filter already exist and are unchanged; this is a second
presentation of the same list.

Atlassian's Navigation system does exactly this at exactly this breakpoint:
*"At s, xs, and xxs breakpoints (i.e. viewports smaller than 1024px), **the
side nav automatically collapses** to make room for the content"*, and below
768px the overlay is *"either 320px or 90% of the screen width — whichever
value is smaller"*
([atlassian.design](https://atlassian.design/components/navigation-system/layout)).
AuraOS already chose 1024px as its breakpoint; it just stops there instead of
collapsing.

While in `AppShell`, add a skip link. ADS: *"Always include the skip link menu
if a substantial number of tab presses are required to reach the main
content"*, capped at *"no more than 4 or 5 elements"*
([atlassian.design](https://atlassian.design/components/page-layout/usage)).
Reaching `<main>` currently costs twelve tab presses, and per §5.1 the focus is
invisible the whole way. Also give each of the three `<nav>` landmarks an
`aria-label` — ADS: *"Provide a unique label for every different navigation...
Make sure that the navigation label is meaningful and not direction-based"*
([atlassian.design](https://atlassian.design/components/side-navigation/usage)).

Worth doing properly because `routes/expense.tsx` — the one screen whose
docstring is explicitly about a producer on set with a phone — is currently
unreachable on that phone except by typing a URL.

### 6.15 Raise the base type scale — M

386 uses of `text-xs` (12px), 59 of `text-[11px]`, table headers at 10px
uppercase, and nothing anywhere at 16px.

Atlassian's typography foundation sets `font.body` — *"the default size in
components or where space is limited"* — at **14px/20px**, and reserves 12px
for `font.body.small`, which *"**should be used sparingly**... fine print"*
([atlassian.design](https://atlassian.design/foundations/typography)). AuraOS
uses Atlassian's fine-print size as its default, 386 times. NN/g agrees
qualitatively: *"Use a reasonably large default font size and allow users to
change the font size"*
([nngroup.com](https://www.nngroup.com/articles/legibility-readability-comprehension/)).
ADS also notes its type tokens use **rem, not px**, precisely so browser text
scaling works — AuraOS's `text-[10px]` / `text-[11px]` arbitrary values are px.

**Judgement, and I am less sure of this one than of anything above it.** A
uniform bump — `text-xs` → `text-sm`, `text-[11px]` → `text-xs`, `label-caps`
10px → 11px — will make several screens overflow that currently just fit, and
§6.5's width cap will already have moved things. Do this **after** 6.5 and 6.6,
measure the boards and the quote editor, and be prepared to leave the two
densest tables at the current scale. It is on the list because 12px chrome is a
real part of why the app reads as busy, not because it is safe.

### 6.16 Delete the dead UI layer — S

Not a UX fix; a "why does this app feel like two apps" fix.

- **Two `Modal` components, both live.** `components/aura/primitives.tsx:188`
  and `components/aura/Modal.tsx` both export `Modal`, with different max
  widths (`max-w-xl` vs `max-w-4xl`), different ARIA wiring (`aria-modal` +
  `role="dialog"` vs `role="dialog"` + `aria-label`) and different subtitle
  support. Three files import the first (`deals.index.tsx`,
  `deals.$dealCode.quote.tsx`, `DealStage.tsx`); five import the second
  (`deals.$dealCode.index.tsx`, `documents.library.tsx`,
  `documents.paperwork.tsx`, `AcceptanceFigures.tsx`, `ContractDetails.tsx`).
  **So the two tabs of one deal open differently-shaped dialogs** — this is a
  live consistency defect (heuristic #4), not just dead weight. `Modal.tsx`'s
  own docstring argues that a copied dialog is "two sets of escape handling and
  two answers about what a backdrop click does", which is exactly the situation
  it is now in. Keep one.
- **Two `ViewToggle`s.** One exported from `components/aura/Kanban.tsx:6`, one
  redefined locally at `routes/documents.library.tsx:270`.
- **`KanbanBoard` is exported from `components/aura/Kanban.tsx:43` and imported
  nowhere.** Both boards hand-roll their own, at `w-[292px]` and `w-[272px]`
  respectively — the shared component's own width, copied and then diverged.
- **`components/ui/` holds 45 shadcn components** and the app imports
  essentially none of them, including `command.tsx` and `sidebar.tsx` — the two
  that would have built §6.12.

Delete or adopt. Leaving both is how the next contributor writes a third
kanban.


### 6.17 Jira's hide-when-empty rule on the deal record — S

`routes/deals.$dealCode.index.tsx:797` renders twelve `<Field>`s in a
`sm:grid-cols-2` block: Title, Client company, Contact, Owner, Stage, Brief,
Est. client budget, Source, Project type, Positioning, Tier (auto), Tags. All
twelve are always present, at equal weight, whether or not they hold anything.

Jira's issue view solves exactly this without a settings screen, by rule rather
than by preference
([support.atlassian.com](https://support.atlassian.com/jira-software-cloud/docs/configure-field-layout-in-the-work-item/)):

> "**Description fields**... **Since this is the first place users look when
> they open a work item, put your most important fields here.**"
> "**Context fields**... usually contain **secondary information**."
> "**Hide when empty** — ...Fields above the hide when empty are shown in the
> **Details** group and those below the line are **hidden under the More fields
> group when they don't have a value. When a field in the More fields group has
> a value, it moves to the Details group.**"

Applied here: Title, Client company, Owner, Stage and Brief stay always-visible.
Contact, Est. client budget, Source, Project type, Positioning, Tier and Tags go
below a divider and appear only when populated, with a "More fields" disclosure
for the empty ones.

This is a static rule in the component, not a per-user setting, which is what
makes it fit a Linear-shaped app (§3.1) rather than a ClickUp-shaped one. It is
also NN/g's progressive disclosure applied properly — *"Initially, show users
only a few of the most important options"*, then *"Offer a larger set of
specialized options upon request"*, with the warning that more than two levels
of disclosure hurts
([nngroup.com](https://www.nngroup.com/articles/progressive-disclosure/)). One
level is what this needs.

**Do not extend this to the quote editor's money columns.** That screen already
prints its own rule — *"Money columns are always shown"* — and it is correct.

### 6.18 Two stage controls become one, on the job page — XS

`routes/jobs.$jobId.tsx` puts an 8-option `<select aria-label="Production
stage">` in the header (line 170) *and* an 8-button chip trail in the body
(line 190). Both write. One looks like a control, one looks like a progress
display, and the one that looks like a display is also a control.

Keep the chip trail — it shows position and affords the move, which the select
cannot — and reduce the header control to a read-only status indicator, or
remove it. NN/g heuristic #4: *"Users should not have to wonder whether
different words, situations, or actions mean the same thing"*
([nngroup.com](https://www.nngroup.com/articles/ten-usability-heuristics/)).

Listed as a product decision rather than a defect, which is why it sits at the
bottom of the table despite being XS: somebody chose to add the second one, and
they may have had a reason this document cannot see.

---

### What is deliberately not on this list

- **Anything that moves a computation into the browser.** §7.2.
- **Any rename.** §7.1.
- **Local-first sync**, Linear-style. §3.7 explains why it is the wrong
  borrowing for a Frappe SPA whose whole doctrine is server-computed money.
- **A view builder, custom fields, or per-Space feature toggles**, ClickUp-style.
  §3.1: the only person who could configure them is the founder, and the founder
  is the person asking for less work, not more.
- **Merging Finance tabs.** §7.5.
- **Sentence-casing `label-caps`.** §3.6 — noted, deliberately declined.

## 7. What NOT to change

A benchmark document is dangerous in exactly one way: it arrives holding three
other products' answers and starts pattern-matching this app's deliberate
decisions into defects. Every item below **looks** like something Linear,
ClickUp or Jira would fix, and every one of them is right as it stands. The
argument is in the codebase already; this section only points at it.

### 7.1 Do not rename a single domain term

`CONTEXT.md` is binding, and its `_Avoid_` lists rule out — by name — almost
every word the three benchmark products use:

| Benchmark word | AuraOS term | Ruled out by |
|---|---|---|
| Project (Linear, Jira, ClickUp) | **Job** | Job `_Avoid_`: "project, production, gig, booking" |
| Issue / Task / Ticket (Linear, Jira) | **Job task** | Job task `_Avoid_`: "todo, ticket, item, activity" |
| Status (all three) | **Production stage** | Production stage `_Avoid_`: "status, phase, step" |
| Group / Section (ClickUp Folders, Jira components) | **Package**, **Phase** | Package `_Avoid_`: "bundle, group, section, item"; Phase `_Avoid_`: "section, group, block, stage" |
| Balance / Outstanding | **Float** | Float `_Avoid_`: "balance, outstanding, petty cash, running total" |
| Gross profit / Gross margin | **Contribution** | Contribution `_Avoid_`: "profit, gross profit, earnings, gross margin" |
| Fixed cost / Opex | **Overhead** | Overhead `_Avoid_`: "cost, expense (unqualified), fixed cost, opex" |
| Recurring expense / Subscription | **Standing cost** | Standing cost `_Avoid_`: "recurring expense, subscription, schedule, template (unqualified)" |

There is no vocabulary recommendation anywhere in §6, and that is not an
oversight. NN/g's second heuristic — *"The design should speak the users'
language. Use words, phrases, and concepts familiar to the user, rather than
internal jargon"*
([nngroup.com](https://www.nngroup.com/articles/ten-usability-heuristics/)) —
argues **for** this glossary, not against it. "Contribution" *is* this studio's
word; "gross margin" is the internal jargon of an accounting package they do
not use. `CONTEXT.md`'s Contribution entry makes the distinction explicit:
contribution is not profit, "which is what remains after the upkeep and has the
founder's commission chain in it". A rename would collapse two facts into one
word.

One observation only, offered as a note rather than a change: the deal form
carries a field labelled **"Project type"** (`deals.$dealCode.index.tsx:919`),
using the word the Job entry forbids. It is a different sense — the kind of
work, not the unit of work — and renaming it would cost more than it buys.
Worth knowing it is there; not worth touching.

### 7.2 Server-computed figures are the architecture, not laziness

Four screens carry an explicit docstring promise that nothing is computed in
the browser: `finance.overhead.tsx` ("**Nothing here is computed in the
browser** — not a month's overhead, not a contribution, not a surplus, not the
run rate"), `finance.reports.tsx` ("**nothing here is computed in the browser
from a list of rows**"), `finance.accounts.tsx` ("a browser adding up a page of
rows would be a second opinion about the same đồng"), and `finance.forecast.tsx`
("a browser scaling a projection by 1.35 is a browser inventing money").

Anything in §6 that would require a client-side total, a client-side filter
over already-fetched rows, or a "quick calculator" widget is out of scope by
construction. §6.3's grouping proposal is deliberately a *navigation* change,
not a data change, for this reason.

### 7.3 Do not add a second rich-text editor

`components/aura/RichText.tsx`'s docstring rejects TipTap by name and explains
that pulling it in "would create the exact second editor the constraint exists
to prevent", and defends `execCommand` on the grounds that the sanitiser on the
Frappe side accepts exactly the tags the four buttons emit. A recommendation to
"modernise the editor" would be a recommendation to break a documented seam. It
is not here.

### 7.4 Permission-shaped navigation is the correct answer, and it beats Jira's

`AppShell.tsx:38-42`: "a nav full of links that answer 403 is worse than a
shorter nav — and My work is the door they do have. Decided by
`auraos.api.session_scope` rather than by a role name read in the browser."
`FinanceTabs.tsx:736-739` says the same for the Overhead tab: "Hiding it keeps
the nav honest rather than keeping anything secret: every endpoint behind
Overhead throws for a producer."

`routes/my-work.index.tsx` goes further and is the strongest piece of design in
the codebase: crew see no money because the `my_jobs` endpoint's payload
**cannot carry money**, not because a screen hides it — "A payload that cannot
hold those numbers cannot leak them, which is a stronger guarantee than a screen
that fetches a job and hides the money."

ClickUp's documented model is the same shape — *"Depending on your user role and
permissions, you may see a limited version of the Spaces Sidebar"*
([ClickUp 4.0](https://help.clickup.com/hc/en-us/articles/31142608907543-Intro-to-ClickUp-4-0))
— and ClickUp's private Custom Fields are "hidden from everyone else"
([Custom Field permissions](https://help.clickup.com/hc/en-us/articles/26025804975895-Custom-Field-permissions)).
AuraOS is doing the industry-standard thing, arrived at independently, and with
a stronger backend guarantee than either. Leave it alone.

### 7.5 The Finance tabs are not redundant

> **Partly withdrawn — see §9.6.** The *argument* below (each tab has its own
> endpoint, therefore each tab should exist) does not hold, and §9.6 says why.
> The endpoint table is still accurate and still shows these tabs are not
> displaying the same data twice. The conclusion survives for seven of the nine
> on better evidence in §9.5 B; `finance.overhead.tsx` should split.

It is tempting to read "nine tabs" as "nine tabs too many" and merge them. Each
one is backed by a distinct server endpoint answering a distinct question:

| Tab | Endpoint(s) |
|---|---|
| Dashboard | `finance_income` + `finance_expenses` |
| Accounts | `cash_accounts`, `cash_account_entries`, `cash_transfers` |
| Bank | `bank_statements`, `bank_reconciliation`, `match_statement_line` |
| Income | `finance_income` |
| Expenses | `finance_expenses` |
| Receivables | `finance_receivables`, `job_profitability` |
| Reports | `finance_profit_and_loss`, `job_profitability`, `period_tax_position` |
| Forecast | `weighted_pipeline_forecast` |
| Overhead | `break_even`, `overhead_log`, `overheads_due`, `recurring_overheads` |

`finance.reports.tsx` argues the separation directly: the P&L "is not two
payloads zipped together on the client. It could have been... But then the
browser would own two rules it has no business owning." `finance.forecast.tsx`
argues the Forecast/Accounts split: "Beside this tab sit Accounts and
Receivables, which are facts... This is an estimate multiplied by a guess."

So §6.3 recommends **grouping** the strip, not shortening it. The count is
justified; the flatness is not.

### 7.6 Deliberate absences that are correct

- **No "New job" button** on the jobs board — "A job exists because a deal was
  won, never because a button was pressed" (`jobs.index.tsx:9-10`). Linear,
  ClickUp and Jira would all put a create button there. They would be wrong
  here.
- **No range control on Receivables or Forecast** — "what is owed is owed
  today... putting a copy of it here would be a control that changed nothing"
  (`finance.receivables.tsx`). This is exactly the discipline Linear preaches.
- **No abbreviated money.** `lib/format.ts`: "Never abbreviated. '1,9 tỷ' was
  rejected by the founder and the design uses full digits everywhere, so there
  is deliberately no short variant to reach for." Any width recommendation that
  works by shortening numbers is off the table — which is why §6.2 works by
  reallocating column width instead.
- **No recommendation engine on Overhead.** "**Show, don't suggest.** #14 says
  it in as many words... The payload carries no key a screen could render as
  advice, and the contract test... fails if one appears." A "suggested margin
  floor" is the obvious dashboard feature and it is banned on purpose.
- **Both unmatched lists on the Bank screen** — "**The two unmatched lists are
  the product.** A reconciliation screen that showed only what lined up would be
  a screen agreeing with itself." That screen's density is its point.
- **Settings sits outside the founder gate** (T3.5, ADR-0005) so a producer can
  manage deal sources while the margin floor stays out of reach. Do not
  re-gate it.
- **Job detail tabs keep unmounted panels alive** — "Hidden, not unmounted: an
  unsaved plan or a half-filled expense form survives a trip to another tab"
  (`jobs.$jobId.tsx:302`). §6.11 proposes putting the tab in the URL; that
  proposal must preserve this, and it can.

### 7.7 Against the ADRs

Nothing in §6 contradicts an ADR. For the record:

- **ADR-0002** (quote branding renders live) — untouched; no recommendation
  here reaches the quote render path.
- **ADR-0003** (any producer may write any job's money) — §6 proposes no
  per-job boundary and no new permission. The nav filtering in §7.4 stays as
  it is.
- **ADR-0005** (vocabulary rename migrates, removal refuses) — §7.1 proposes no
  rename at all, so the migrating-rename machinery is not engaged.
- **ADR-0001 / ADR-0004** are about where code and CI run and have no UI
  surface.

## 8. Vietnamese and English in one interface

The app's split is consistent and, mostly, deliberate: **chrome in English,
content in Vietnamese**. `lib/format.ts` states the rule outright — *"English
plurals only; the data itself stays Vietnamese"* — and the typeface choice
backs it up: `index.html` loads **Be Vietnam Pro**, a family designed for
Vietnamese diacritics, rather than leaning on a Latin face that mangles
stacked tone marks. That is a good decision nobody wrote a docstring for.

Three concrete problems sit on top of it.

### 8.1 Two date locales in one app

`lib/format.ts` uses `vi-VN` for `vnd`, `formatDate`, `formatDateTime` and
`percent` — so money is `1.925.000.000`, dates are `18/08/2026`, percentages
are `68,7%`. But `formatDateLong` uses **`en-GB`**, producing
`Tuesday 18 August 2026`, and that is what the Home page prints in its header
line (`routes/index.tsx:285`).

So the founder opens Home, reads an English long-form date at the top, and then
reads `18/08/2026` in every table below it. Same app, same session, two
locales, no rule that explains the difference. NN/g's fourth heuristic —
*"Users should not have to wonder whether different words, situations, or
actions mean the same thing"*
([nngroup.com](https://www.nngroup.com/articles/ten-usability-heuristics/)) —
covers this exactly. **One-line fix**, and the only question is which locale
wins.

### 8.2 English sentences describing Vietnamese rows

`overdueLabel` renders `"12 days overdue"` (English) and is used on the jobs
board and the Home dashboard, in rows whose job titles are `TVC Tết 2027` and
whose clients are Vietnamese company names. The `<Empty>` states are English
prose — *"Write the plan: what has to happen, who is doing it and by when."*
— shown to crew whose entire working vocabulary in this app is Vietnamese.

This is the one place the English-chrome rule genuinely costs something,
because empty states and overdue warnings are the moments the app is *teaching*
rather than *labelling*. NN/g's guidance on international users is blunt about
the asymmetry: *"users in all countries prefer concise sites"*, and non-native
readers are slower and less confident with foreign-language prose
([nngroup.com](https://www.nngroup.com/articles/international-usability-details-differ/)).
A one-word label in English is fine. A three-clause instruction is not.

### 8.3 The app already contains the right pattern, on one screen

`routes/deals.$dealCode.index.tsx:73-87, 934-985` does the best bilingual work
in the codebase, and it is worth copying rather than describing:

- The **Positioning** select renders each option as
  `Cash - nuôi bộ máy (~50%)` — the English term the backend enforces, a
  Vietnamese gloss of what it *means*, and the founder's live mix target,
  in one line.
- **Tier** renders as a `<Pill>` plus a Vietnamese gloss (`Tier 1 - cơm áo`).
- The field's `hint` is a link to the Vietnamese SOP in the Library:
  *"SOP: cách đánh giá và phân loại deal"*, opening in a new tab so the
  half-edited deal survives.

That is: English token + Vietnamese meaning + a route to the long explanation,
without a second language toggle and without translating the schema. NN/g's own
recommendation for international B2B is to name languages *as text, not flags*
([nngroup.com](https://www.nngroup.com/articles/international-b2b/)) — this
pattern sidesteps the question entirely by not having a language switch at all.

**Recommendation (§6.7):** extend this pattern to the terms that currently have
no gloss anywhere — `Contribution`, `Break-even line`, `Float`, `Advance`,
`Quoted cost`, `Profit cost basis`. These are the words `CONTEXT.md` defines
most carefully and the app explains least. A one-line Vietnamese gloss beside
each does not rename anything, does not touch the glossary, and does more for
"rất rối" than any layout change on this list.

### 8.4 What to leave alone

- **The English/Vietnamese split itself.** Do not translate the schema or add
  an i18n layer. `lib/format.ts` states the rule; the rule is coherent; a
  half-translated app is worse than a consistently split one.
- **Full-digit money.** `1.925.000.000` reads long and is meant to. See §7.6.
- **Vietnamese collection-status glosses** — `CONTEXT.md` already ships them
  ("Not requested (chưa yêu cầu) → Requested (đã yêu cầu KT) → Invoiced
  (đã xuất HĐ) → Paid (đã thanh toán)"). That is §8.3's pattern in the
  glossary; it should reach the screen.

## 9. Information architecture: are these the right screens at all?

§4 asked where the eye goes *within* a screen. This section asks the different
and harder question the founder put next: **where should the screen boundaries
be**, is every number in the place the person who needs it is standing, and what
should be merged or split.

It is organised as: the navigation graph the code actually builds (§9.2), the
five real task flows traced route by route with the seams marked (§9.3), a
table of every significant figure against who needs it and where it is (§9.4),
and then — only then — merge/split proposals with their counter-arguments
(§9.5). §9.6 collects the actions and marks one correction to §7.5.

Two constraints hold throughout, as before: **no domain term is renamed to make
a screen tidier**, and every proposal is argued on its own evidence rather than
against a general preference for fewer screens or more.

### 9.1 What "the right number of screens" looks like elsewhere

The three benchmark products disagree about this more sharply than they disagree
about anything in §3, which makes the comparison useful rather than decorative.

**ClickUp puts six levels between you and a task**, and documents them as the
product's spine:

> "The Hierarchy is how your Workspace is organized... **Workspace → Spaces →
> Folders → Lists → Tasks → Subtasks.**"
> — [help.clickup.com, Intro to the Hierarchy](https://help.clickup.com/hc/en-us/articles/13856392825367-Intro-to-the-Hierarchy)

with **Folders optional** and **17 view types** available at several of those
levels ([Intro to views](https://help.clickup.com/hc/en-us/articles/6329880717719-Intro-to-views)).
ClickUp's answer to "should this be its own screen?" is *"make a view, at
whichever level of the hierarchy it belongs to."*

**Linear's object model is deliberately small**, and its sidebar is smaller
still: four personal items, a Workspace group, Favorites, then Teams
([linear.app/docs/layout](https://linear.app/docs/layout)). Everything else is a
**view** — a saved filter that lives in the sidebar rather than a page that had
to be built:

> "The applied filters are also reflected in the browser URL. **You can copy the
> browser address to share the filtered view**; opening the link applies the same
> filters."
> — [linear.app/docs/filters](https://linear.app/docs/filters)

And Linear's stated reason for keeping the model small is the one that matters
for a studio of this size:

> "**Purpose-built** — Productivity software needs to be designed for purpose...
> **Flexible software lets everyone invent their own workflows, which eventually
> creates chaos as teams scale.**"
> — [linear.app/method/introduction](https://linear.app/method/introduction)

**Jira sits between them and is the most instructive for AuraOS**, because it
answers the "should this be its own screen?" question in writing, more than once.

*A terminology note before the quotes:* current Jira Cloud docs have renamed
**project → space** and **issue → work item**. Data Center docs still say
project and issue. Quotes below keep whichever word the cited page uses.

The container-versus-view distinction, stated three times on one page
([atlassian.com/software/jira/guides/boards/overview](https://www.atlassian.com/software/jira/guides/boards/overview)):

> "A Jira space houses all work items needed to achieve a particular goal. A Jira
> board, on the other hand, is the tool used to manage those work items as they
> move from creation to completion."
> "In short, the space holds the work, and the board is how you visualize and
> move it."
> **"The space is the container; the board is the view."**

And the single most useful sentence in this whole document for §9's question,
from the same page:

> "**Because every view draws on the same underlying work items, you can move
> between them without duplicating anything and pick the one that best answers
> the question in front of you.**"

That page enumerates five surfaces over one set of work items — board ("a
shared, at-a-glance view of what is being worked on and where it stands"),
backlog ("holds and prioritizes upcoming work"), list ("a spreadsheet-style view
of work items and their fields"), timeline, calendar — plus dashboards
elsewhere, which aggregate the same items again through saved filters: a filter
can *"Display the search results in a dashboard gadget"*
([support.atlassian.com](https://support.atlassian.com/jira-software-cloud/docs/save-your-search-as-a-filter/)).

**Atlassian's answer to "make a new page?" is documented and it is "no — make a
view."** The boards guide lists three cases where a team wants more separation —
*"Different work streams within a single space"*, *"Multiple teams working on a
single project"*, *"Lengthy processes with various stakeholders"* — and the
prescribed answer to every one of them is **another board over a filter, not
another project**. Cross-space boards handle the rest: *"A cross-space board can
surface the right work items while keeping other spaces private."*

Jira also names its navigation levels, which ADS does not do publicly
([atlassian.com/software/jira/guides/navigation/overview](https://www.atlassian.com/software/jira/guides/navigation/overview)):

> "**The top navigation or top bar**: ...actions that affect your entire site."
> "**The side navigation or sidebar**: Navigation in Jira starts from the
> sidebar, where you can work across multiple projects..."
> "**The horizontal project navigation** in Jira offers different views... While
> the sidebar lets you seamlessly navigate between different Jira projects, the
> project navigation allows you to change between different views..."

— which is exactly AuraOS's shape: a sidebar for objects, a horizontal strip
for views of one object. And Atlassian's advice about that strip is the same as
§6.3's and §9.5 B's:

> "If you're a project admin, you can customize the project navigation to suit
> your team's needs and **reduce clutter**." / "**prioritize the views your team
> uses the most for a cleaner, focused tab layout** that helps reduce confusion
> and keeps everyone aligned."

Jira's record-page rule is the transplantable one already quoted in §6.17:
description fields where people look first, context fields to the side, and
**hide-when-empty** below a divider
([support.atlassian.com](https://support.atlassian.com/jira-software-cloud/docs/configure-field-layout-in-the-work-item/)).

**Two things Atlassian does *not* publish**, checked and worth knowing so nobody
goes looking: there is no first-party page giving criteria for *when to create a
new project versus a component or a label* — the widely-quoted line about
"different project-specific settings" is from `community.atlassian.com`, a user
forum, and is not cited here. And there is no public ADS page enumerating the
navigation levels; `atlassian.design/components/navigation-system` says the
fuller guidance is *"(Atlassians only)"*. The closest first-party structural
advice is the honest one:

> "**There is no one-size fits all approach to structuring a project in Jira.**
> However, it may be helpful to recognize that **Jira projects are not intended
> to be bespoke or unique to a single outcome. Rather, they capture ongoing
> efforts.**"
> — [atlassian.com/software/jira/guides/projects/tutorials](https://www.atlassian.com/software/jira/guides/projects/tutorials)

Atlassian's own navigation guidance points the same direction as Linear's
count — *"**Keep nested navigation levels to a minimum. If you need to use a
nested navigation, always provide a 'go back' button to help people get out of
the menu.**"*
([atlassian.design](https://atlassian.design/components/side-navigation/usage)).

**Where AuraOS sits.** Its object model is already small and already correct —
Deal → Quote version → Job → Job task, with Package and Phase inside the quote
and Advance / Expense / Milestone hanging off the job. That is a Linear-shaped
model, not a ClickUp-shaped one, and §7.1 explains why none of it should be
renamed. The problem §9 finds is not the model. **It is that the model's
lifecycle is spread across surfaces that do not link to each other**, and that
the two figures the founder most needs are the two furthest from where they
stand.

### 9.2 The navigation graph the code builds

Every `<Link to="/...">` in `routes/` and `components/aura/`, deduplicated:

```
                    ┌──────────────► /my-work ───► /my-work/$jobId
                    │
   Home ────────────┼──► /deals ─────► /deals/$dealCode ──► /deals/$dealCode/quote
    │               │        ▲               │  ▲                 │
    │               │        │               │  └─────────────────┘
    │               └──► /jobs ──► /jobs/$jobId ◄── /documents/paperwork
    │                                   │  ▲
    │                                   │  └─── /finance/receivables
    │                                   └─────► /deals/$dealCode
    │
    └──► /settings                /quotations ──► /quotations/$quoteRef
                                       └──► /deals, /deals/$dealCode

   /finance ──► /finance/income, /finance/expenses          (and nothing else)

   DEAD ENDS (zero outbound links):
     finance.accounts   finance.bank      finance.expenses
     finance.forecast   finance.income    finance.overhead
     finance.reports    contacts.companies  contacts.people
     documents.files    documents.library   settings
```

Three facts fall straight out of that picture:

1. **Home does not link to Finance.** Not to the Dashboard, not to Accounts, not
   to Overhead. The sidebar is the only route in.
2. **Six of the nine Finance tabs have no way out.** Only the Dashboard (→
   Income, Expenses) and Receivables (→ a job) link anywhere.
3. **The job page does not link to `/expense`**, though `/expense` links to it.

There is also no global search: `/deals`, `/jobs` and `/quotations` each have
their own server-side search box, and the one affordance that would cross
objects — the `⌘K` chip in the header — does nothing (§6.12). So when a screen
prints a record's name without linking it, the recovery is: read it, remember
it, go to the right list, search it again.

There are also no breadcrumbs anywhere in the app. The detail screens partly
substitute with a back-link in `AppShell`'s `meta` slot — `jobs.$jobId.tsx:153`
renders `‹ Jobs`, and the quote and deal pages do the same — which is the right
instinct. Atlassian's rule is that breadcrumbs *"are a useful addition to, but
shouldn't replace, the main navigation on a page"*, and are for *"large websites
and complex apps that have hierarchically arranged pages, so that users who land
on the page can quickly know where they are"*
([atlassian.design](https://atlassian.design/components/breadcrumbs/usage)).
**Judgement: AuraOS is not deep enough to need breadcrumbs** — two levels at
most — and the existing back-links do the job. This is listed so that
"add breadcrumbs" does not get proposed as the fix for §9.3's dead ends. It is
not; the fix is making the names into links.

### 9.3 The five flows, traced from the code

Each flow below is what the routes actually force. A **seam** is marked where
the app makes somebody carry a fact in their head from one screen to another —
that is the measurable cost of a screen boundary in the wrong place.

#### Flow A — Win work

```
/deals ──► /deals/$dealCode ──► /deals/$dealCode/quote ──► [Zalo] ──► ⤶ same page
 create        the record            price + publish        send        Mark sent
   │                                                                    (card 9 of 9,
   │                                                                     line 2222/2464)
   └─ two ways to create: a typed blank row (table view, line 1275)
      and a "New deal" dialog (kanban view)

  …client replies…

/quotations ──► /quotations/$quoteRef ──► /deals/$dealCode ──► /deals/$dealCode/quote
  "what's out"     read-only, 0 mutations     the record          scroll to card 9,
                        ▲                                          Mark confirmed
                        └── SEAM 1 ─────────────────────────────────────┘
```

**Seam 1 is the worst screen boundary in the app.** `/quotations` and
`/quotations/$quoteRef` contain **zero mutations** — verified by grep, both
files. Every action on a quote version lives at
`deals.$dealCode.quote.tsx:2222` (`Mark sent`) and `:2230` (`Mark confirmed`),
which is the bottom of a 2464-line file, in the ninth card down.

So the section built to answer *"what is out with clients right now"* — a nav
item and two routes — cannot act on the answer. Reading it costs two more
navigations and a long scroll into the pricing editor, which is the one screen
you did **not** want to open, because it is where prices get changed by
accident.

**Also missing across the whole flow:** `floor_breached` appears in exactly one
file. The margin-floor warning is `deals.$dealCode.quote.tsx:1085` — the first
element in the page body — and the Publish button is at ~2097, eight cards
below, in a card that mentions no margin at all. `/deals` has a `quote_status`
column but no margin; `/quotations` has eight columns and none of them is
margin or floor.

> `CONTEXT.md` — **Margin floor**: "The single global margin percentage below
> which any quote warns, without revealing where the number comes from."

It warns while you type. It is silent where you commit, and silent forever
after. A below-floor quote can be published, sent, confirmed and won without
any screen after the editor ever saying so.

*Credit where due:* a producer **does** see the banner, without the percentage
(`view.founder` gates the number). That is the glossary's "without revealing
where the number comes from", implemented exactly.

#### Flow B — Run a shoot

```
/jobs ──► /jobs/$jobId ──┬─ Production (7 cards: Files, Revisions, Packages,
 board      4 stat tiles  │              Client, Links, Quoted, Stage log)
            + stage trail ├─ Tasks      (JobTasks: board / timeline / list)
            + 4 tabs      ├─ Money      (JobMoneyPanel + JobMilestonesPanel)
                          └─ Paperwork  (JobPaperworkPanel)
```

**This flow is cohesive and is the app's best decomposition.** One job, one
route, four tabs, and the four money figures (Quoted, Collected, Uncollected,
Spent) sit **above** the tabs so they persist across all four. Revisions and
the redo round-trip are on Production where the stage is. Paperwork generation
is here, against the job's own records, while the template library lives at
`/documents/paperwork` — and that split is right and its docstring says why:
*"This screen owns what a paper is made from, and what has been made."* The
registry rows link back to `/jobs/$jobId`.

Two seams, both small:

- **The job page does not link to `/expense`.** `expense.tsx` links to
  `/jobs/$jobId`; nothing links back. The one-handed on-set screen is reachable
  only from a sidebar that does not exist below 1024px (§5.3).
- **The tab is `useState`, not the URL** (line 100), so no tab is linkable —
  which becomes an IA problem in Flow C.

#### Flow C — Get paid

```
/jobs/$jobId ► Money tab ► JobMilestonesPanel ► set status ► generate invoice
                                              (Not requested → Requested →
                                               Invoiced → Paid)
                                                     │
        the money then appears in ────────────────────┼──► /finance/income
                                                     └──► /finance/receivables

chasing it back the other way:
/finance/receivables ──► /jobs/$jobId ──► click "Money" ──► scroll to milestones
                            ▲ opens on Production
                            └── SEAM 2
```

**Seam 2:** Receivables is the *only* Finance tab besides the Dashboard with an
outbound link, and it links to a job page that opens on the wrong tab, because
the tab is component state. You arrive one click away from the thing the link
was for. This is §6.11 with an IA consequence attached: the fix is a search
param and a `?tab=money` on that link.

#### Flow D — Pay out

```
advance ──► expenses ──► settlement        all inside JobMoneyPanel, one endpoint
   (record_job_advance, log_job_expense, settle_job, job_money)
   + /expense?job=… as the standing-up shortcut
```

**No seam.** This is the tightest flow in the app: one read (`job_money`)
answers the ledger, the floats, and actual-against-quoted per category, because
*"they are computed from the same rows."* Nothing to change.

#### Flow E — the founder's Monday morning

The question is "are we all right?" Here is what answering it costs today:

| # | Screen | What it answers |
|---|---|---|
| 1 | `/` Home | pipeline, weighted projection, in production, overdue, silent quotes, margin floor, no-invoice exposure |
| 2 | `/finance` Dashboard | money in vs money out by month |
| 3 | `/finance/accounts` | **cash on hand** |
| 4 | `/finance/receivables` | who owes, ageing |
| 5 | `/finance/overhead` | **the break-even line: surplus or shortfall** |
| 6 | `/finance/reports` | P&L, margin by job |
| 7 | `/finance/forecast` | weighted pipeline ahead |

**Seven screens, and Home links to none of them.** `index.tsx`'s outbound links
are `/deals`, `/jobs`, `/jobs/$jobId`, `/my-work` and `/settings` — there is no
link from Home to Finance at all. The sidebar is the only way in.

And the two figures that most directly answer "are we all right?" are the two
that are furthest away:

- **Cash on hand** — `finance.accounts.tsx:141`, one screen, nowhere else.
- **The break-even surplus/shortfall** — `finance.overhead.tsx`, one screen,
  nowhere else, behind the ninth tab of the seventh nav item, founder-gated.

`CONTEXT.md` defines the break-even line as *"A month's contribution against
its overhead. Positive is a surplus, negative a shortfall, **and it is one
signed number rather than two fields**."* The glossary went to the trouble of
making it one number precisely so it could be shown as one. It is currently the
hardest number in the app to reach.

**This is the finding of §9.** Not "too many screens" — the founder's most
important question is spread across seven of them, and the app's own home page
does not carry the answer or a route to it.

#### Flows that end in a wall

Four screens print a record's name and do not link to it. Each one forces a
memorise-and-re-search:

| Screen | Prints | Link? | The seam |
|---|---|---|---|
| `finance.overhead.tsx:503` | per-job contribution, "Final" or "Still spending" | **no** | founder sees a job that lost money and must go find it |
| `finance.reports.tsx` | margin by job | **no** | same |
| `finance.forecast.tsx` | per-deal weighted contribution | **no** | same, for deals |
| `documents.files.tsx:267` | `{row.deal_title \|\| row.deal}` | **no** | worst of the four — see below |
| `contacts.companies.tsx` | Company, Tax code, Phone, Email, Paperwork | **no** | no deals, no jobs, no ageing |

`documents.files.tsx` is the sharpest because its own docstring states the
purpose: *"The question this screen exists for is the one a deal card cannot
answer: 'we have that brief somewhere, which deal was it on?' So the deal is a
column rather than a heading."* The reasoning is right and the column is dead
text. The screen answers the question and then makes you carry the answer to
the sidebar by hand.

And one more, on Home: a **silent-quote row links to `/deals`** — the whole
board — not to the deal it names, because `index.tsx:279` sets `job: null` for
silent deals and the fallback link is generic. The row says *"TVC Tết 2027 ·
Silent quote · quote sent, no reply for 14 days"*, you click it, and you land
on a board of every deal. `SilentDeal` carries `name` (line 117). The link is
one field away from working.

**Six dead ends of nine Finance tabs.** Routes with zero outbound `<Link>`:
`finance.accounts`, `finance.bank`, `finance.expenses`, `finance.forecast`,
`finance.income`, `finance.overhead`, plus `contacts.companies`,
`contacts.people`, `documents.files`, `documents.library`, `settings`.

**This, not the tab count, is why Finance feels like a separate application.**
It is a reporting annexe you enter from the sidebar and leave the same way.

### 9.4 Every significant number: who needs it, when, and is it where they are standing

Screens are from `grep` across `routes/` and `components/aura/`. "Verdict" is my
judgement against the flows in §9.3.

| Figure | Printed on | Who needs it | At what moment | Where they are standing | Verdict |
|---|---|---|---|---|---|
| **Quote total** | Home, `jobs.index`, `jobs.$jobId`, `quotations.index`, quote editor | producer + founder | pricing; and on every job all through the shoot | it is on all of them | ✅ correct duplication |
| **Margin %** (`margin_pct`) | quote editor, `finance.reports`, `finance.receivables`, `finance.overhead` | producer while spending; founder afterwards | when a shoot starts costing more than quoted | producer is on `/jobs/$jobId`, which does not have it | ⚠️ see below |
| **Floor breached** (`floor_breached`) | **quote editor only** | whoever decides to send, and the founder reviewing what is out | at publish; at send; while reviewing `/quotations` | banner is 1000 lines above the Publish button; absent from `/deals`, `/quotations`, the job | ❌ **wrong place** |
| **Days overdue** | Home, `jobs.index`, `finance.receivables`, `JobMilestonesPanel` | founder chasing; producer on the job | Monday; and when opening the job | all four | ✅ useful reminder, not noise |
| **Uncollected** | `jobs.$jobId`, `jobs.index`, `finance.receivables`, `finance.reports` | founder + producer | on the job, and when chasing | both | ✅ |
| **Collected** | 9 screens incl. `finance.accounts`, `finance.income`, `finance.index`, `finance.reports`, `AcceptanceFigures` | founder | reporting | everywhere | ⚠️ nine is more than the fact needs, but each is a different aggregate of it (cash basis, per-client, per-month, per-job) — not duplication |
| **Spent / Advanced total** | `jobs.$jobId`, `JobMoneyPanel` | producer | while spending | exactly there | ✅ |
| **Float** (per person) | `JobMoneyPanel` only | producer + the person holding it | at settlement | exactly there | ✅ |
| **Actual vs quoted cost, per category** | `JobMoneyPanel` "Where the money went" | producer | every time they spend | exactly there | ✅ **the best-placed number in the app** |
| **Contribution** | `finance.overhead`, `finance.forecast` | founder | month end | founder-only screens | ✅ |
| **Break-even surplus / shortfall** | **`finance.overhead` only** | founder | Monday morning; "are we all right?" | Home | ❌ **wrong place** |
| **Cash on hand** | **`finance.accounts` only** | founder | same moment | Home | ❌ **wrong place** |
| **Open task count** | **`my-work.index` only** | crew and producer | daily | correct for crew; a producer's own tasks are not on Home | ⚠️ minor |
| **Revision rounds / change order** | `jobs.$jobId` (Production), quote editor, `quotations.$quoteRef` | producer at the moment a client asks again | on the job | there | ✅ |
| **Margin floor % itself** | Home ("Margin floor" card, founder), Settings, quote editor | founder | when setting it, and when pricing | there | ✅ |
| **No-invoice tax exposure** | Home (founder) | founder | Monday | there | ✅ |
| **Weighted projection** | Home (founder), `finance.forecast` | founder | Monday | both, and Home names it *"not cash"* | ✅ well handled |

#### The three ❌s, in order of how much they cost

**1. `floor_breached` never leaves the pricing editor.** Covered in §9.3 Flow A.
The fix is small and does not touch the pricing engine: put the flag on the
Publish card, on the `/quotations` row, and on the deals table's `quote_status`
cell. The server already sends it in the same payload the editor reads.

**2. The break-even line and cash on hand are not on Home.** §9.3 Flow E. Both
are single-endpoint reads (`break_even`, `cash_accounts`), both already
founder-gated server-side, and Home already renders two founder-only cards
behind `session.isFounder`, so the pattern is in the file. This is the change
that would most directly answer *"are we all right?"* in one screen instead of
seven.

**3. A job's own margin is served to the founder's reports and not to the
producer running the job.** This one deserves its own paragraph, because the
codebase already argued for it:

> `auraos/api.py:2008` — `def job_profitability(job=None, include_closed=0)`
> "Margin, deliberately, and not the founder profit chain. **A producer already
> sees the quoted total, the milestone plan and every đồng spent; the difference
> between what was quoted and what the shoot is costing is the number that tells
> them it is going wrong, and story 32 exists so they can act on it.**"

The endpoint takes a single `job`. It is producer-permitted. Its docstring says
it exists so a producer can act. And the frontend calls it from exactly two
places — `finance.receivables.tsx:379` and `finance.reports.tsx:278` — **both
with no `job` argument.** `jobs.$jobId.tsx` never calls it at all; its endpoint
list is `job_milestones`, `job_money`, `log_job_revision`, `overdue_milestones`.

**The single-job branch of that endpoint is unreached from the browser.** The
number was built for the person running the shoot and is currently served only
to the two screens they have no reason to open.

**The honest counter-argument, which I accept in part:** the producer is not
flying blind. `JobMoneyPanel`'s "Where the money went" card gives actual against
**quoted cost** per category, with bars, which is the right *control* for
someone deciding whether to approve one more rental. Margin is the right
*verdict*, and a verdict belongs where the decision was made — which is the
quote — not necessarily on the job. So this is a ⚠️ dressed as an ❌: adding a
fifth stat tile is cheap and the endpoint is waiting, but the existing
budget-bar framing is not wrong, and if only one thing gets built, build #1.

#### On duplication, since not all of it is noise

The brief asked when repetition helps. From the table above:

- **Helpful:** *days overdue* on four screens. Each is a different standing
  point — the founder's Monday list, the jobs board, the receivables ledger, the
  milestone row itself — and the fact is short, urgent, and identical in all
  four. `lib/format.ts`'s `overdueLabel` makes sure they cannot phrase it
  differently, which is what makes the repetition safe.
- **Helpful:** *quote total* everywhere a job appears. It is the job's size; it
  is context, not a claim.
- **Not duplication at all:** *collected* on nine screens. Each is a different
  cut — cash-basis month, per client, per job, per account. The word is the
  same; the number is not.
- **Noise:** the Deals stat row against the board's own column headers (§6.4).
  Same grain, same aggregate, sixty pixels apart.
- **Noise:** the job page's header `<select>` against its chip trail (§6.18).
  Not a number, but the same category of error.

### 9.5 Merge or split: five proposals, each with its counter-argument

#### A. Deals and Quotations — keep both lists, move the actions, retire the version page

**Are they two screens or one with a filter?** They are two *grains*, and the
backend says so:

> `auraos/api.py:1013` — `quotation_list(status=None, search=None)`: "Every quote
> version across every deal, newest first. A deal has always been able to list
> its own versions (`deal_quotes`); this is **the same rows without a deal in
> front of them**, because 'what is out with clients right now' cannot be
> assembled one deal at a time."

A deal has many versions. `/deals` is one row per deal; `/quotations` is one row
per version. You cannot filter one into the other. **Keep both.**

In Atlassian's vocabulary the Deal is the container and both lists are views of
it — *"The space is the container; the board is the view"*, and *"because every
view draws on the same underlying work items, you can move between them without
duplicating anything and pick the one that best answers the question in front of
you"*
([atlassian.com](https://www.atlassian.com/software/jira/guides/boards/overview)).
`/quotations` is a filtered, searchable view over one doctype with three summary
tiles. That is a view, not a section, and having it is right; Linear's sidebar is
largely views and Jira's documented answer to "should this be a new page?" is
"make another board over a filter."

What is not fine is that **this view is read-only** (§9.3 Flow A). Every other
product's views act on the objects they show — that is what makes them views
rather than reports. AuraOS's Quotations view is a report.

**Proposal.**
1. Put `Mark sent` and `Mark confirmed` on the `/quotations` row, behind the
   same confirm-dialog pattern `DealStage.tsx` already uses for Lost. **S.**
2. Add a **margin / below-floor** column to `/quotations`. The payload behind
   the editor already carries `floor_breached`. **S.**
3. **Retire `/quotations/$quoteRef` as a separate destination**, or reduce it to
   what only it has. Today it is 348 lines showing a status pill, client
   engagement, "This version", and "Every version" — and every one of those
   except the engagement timeline is already rendered by
   `components/aura/QuoteVersions.tsx` at the bottom of the quote editor, *with*
   the actions. It is a strictly weaker copy.

**Counter-argument.** Row-level "Mark confirmed" on a list is a misclick that
freezes the wrong version's status. Real, and the mitigation is the confirm
dialog that already exists. Second counter: the engagement timeline (opens, PDF
downloads, timestamps) genuinely has nowhere else to live and is the best reason
to open a version. So retire the *route* only if that timeline moves into a
drawer on the list; otherwise keep the route and just give it the two buttons.
**My preference: keep the route, add the buttons to both.** Cheaper, and it
does not delete a working screen to prove a point.

#### B. Finance's nine tabs — a correction to §7.5, and one split

**I am changing my position, and §7.5's argument was wrong.**

§7.5 defended all nine tabs on the grounds that each backs a distinct server
endpoint. That reasoning does not hold: **endpoint-distinctness proves the data
is distinct, not that the screens should be.** By that argument the Home
dashboard should be six screens. I was reading each file's docstring and letting
it justify its own existence, which is exactly the failure the coordinator
warned about — a tab can be individually justified and collectively wrong.

What the flows change, and what they do not:

**What survives.** Seven of the nine are still right as separate destinations.
Bank reconciliation, Accounts, Receivables, Reports and Forecast each answer a
question you go looking for deliberately, and `finance.forecast.tsx`'s
fact-versus-estimate line is a real reason to keep the estimate away from the
ledger.

**What does not survive: `finance.overhead.tsx` should split.** It is 1148 lines
holding **five cards and five tables**: the break-even line by month, per-job
contributions, standing costs due, the standing-cost register, and the overhead
payment log. That is two different jobs — *"are we all right?"* and
*"bookkeeping for the company's own costs"* — and the first is buried inside the
second, behind the ninth tab of the seventh nav item.

> `CONTEXT.md` — **Break-even line**: "A month's contribution against its
> overhead. Positive is a surplus, negative a shortfall, **and it is one signed
> number rather than two fields.**"

The glossary made it one signed number so it could be *shown* as one. Split it
out: the break-even line goes up (to Home, or to a Finance overview); the
standing-cost register, the due list and the payment log stay as **Overhead**,
which is then honestly named — it becomes the screen for the thing the glossary
calls an Overhead, rather than a dashboard with a register attached.

**What I still will not do: merge Dashboard / Income / Expenses.** These are the
closest to genuinely redundant — `finance.index` calls exactly the two endpoints
that Income and Expenses each call alone, and shares one range control with both
via `FinanceRange`. But Income carries a per-client breakdown inside each month
and Expenses carries the category split and the company-money-versus-float
split, and neither fits on a summary. This is ordinary hub-and-spoke: a summary
and its two drill-downs. `finance.index` already links to both, which is the
right relationship. **Leave it.**

**The bigger fix is not the count — it is that Finance is terminal.** Six of the
nine have no outbound link (§9.3). Make every job name and deal name in
Overhead, Reports and Forecast a `<Link>`. That is **XS per screen**, it is the
single change that would most reduce the "Finance is a different app" feeling,
and it does not move a single tab.

#### C. The quote editor — do not split it yet, and here is exactly what breaks

I called it the worst and most important screen (§4.3) and named a seam:
Cost lines / Phases / Packages is one task; Client terms / Assumptions /
Publish is another.

**What breaks if you split it.** The screen is backed by **one
`frappe.client.save` writing the entire Deal document**
(`deals.$dealCode.quote.tsx:743-757`):

```
const doc = { ...base, doctype: "Deal",
  cost_lines, packages, phases,
  quote_mf_pct, vat_pct, contingency_pct, quote_detail_level,
  assumptions, exclusions, included_revision_rounds, quote_valid_until }
```

Every field on both halves of the proposed split is in that one payload, and it
is written by spreading `...base`. Two routes each autosaving that object is
**last-write-wins clobbering**: screen A's 2.5-second autosave would write its
stale copy of `assumptions` over what you just typed on screen B.

And publishing depends on the save having happened:

> "Answers whether the server now holds what is on screen, which is what
> publishing has to know: **a version freezes the *saved* deal, so an unsaved
> override would be published at its old price.**"

So `publish` `await`s `save()`. Split the screen and that await now has to reach
across a route boundary.

**The safe split exists and the seam is already in the tree.**
`routes/deals.$dealCode.tsx` is a nine-line passthrough `<Outlet />`. Hoisting
the draft state, the dirty flag, the autosave timer and the status line into that
layout route, with `index` / `quote` / a new `offer` as children, is the correct
architecture. It is **M-to-L**, it touches the most dangerous code in the app,
and it would be done for readability rather than for a bug.

**Verdict: not now.** Do §6.6 (rebalance the column widths, S) and the XS fix
below first, then re-measure.

**The XS fix that solves the actual harm.** The reason the seam hurts is not
that the page is long — it is that the **margin floor banner is 1000 lines above
the Publish button** (§9.3 Flow A). Put `floor_breached` *inside* the Publish
card, next to the button that commits. The flag is already in the same payload
the card renders from. That is one conditional, and it removes most of the
argument for splitting.

**Counter-argument to my own verdict:** the founder "sits on this page for
hours" (line 786) and the page is 2464 lines. If the width fix does not land it,
the split is the real answer and putting it off twice would be cowardice. Revisit
after §6.6 ships.

#### D. Job tabs versus Deal long column — the job pattern is right, and fixing it is change C

Two records, two patterns, in one app:

| | Deal | Job |
|---|---|---|
| Routes | **2** (`/deals/$dealCode`, `/deals/$dealCode/quote`) | **1** |
| Split by | route | four `useState` tabs |
| Persistent summary | none — "At a glance" is card 4 of 7 and scrolls away | **4 money tiles above the tab strip**, visible on all four tabs |
| Depth of one page | 7 cards, 12 fields in the first | Production tab = 7 cards |

**The job pattern is right**, and specifically because of the summary strip:
Quoted / Collected / Uncollected / Spent stay on screen whichever tab you are
on, so switching tabs never costs you the context you switched with. The deal's
equivalent numbers are inside a card that scrolls away, and its pricing is on a
different route entirely.

**Proposal:** converge the deal onto the job's shape — one route, a persistent
summary strip (client, stage, estimated budget, quote status, margin), and tabs
for Record / Pricing / Offer / Activity.

**But notice this is the same change as C.** Both need the draft state hoisted
into `routes/deals.$dealCode.tsx`. They are one piece of work, not two, and that
is a point in favour of eventually doing it.

**Counter-argument.** A deal is *a form plus a pricing tool* — two things. A job
is *four unrelated workstreams*. Four tabs earn their tab strip; two do not, and
two tabs is usually worse than two routes. So the converged deal might be one
route with a summary strip and **no** tabs, keeping `quote` as a sibling route.
That is a smaller change and probably the right one. **Decide when C is
scheduled, not before.**

**Do not converge the other way.** Do not split the job into routes. Its tabs
are correct, they keep unsaved work alive (`jobs.$jobId.tsx:302`), and the only
thing wrong with them is that they are not in the URL (§6.11).

#### E. My work as the model — yes, but for the rule, not the shape

`my-work.index.tsx` is one card, one list, one `<Pill>` per row, money-free by
construction. I called it the least confusing screen in the app (§4.6).

**The transferable rule is "a screen answers one question and says which" — not
"every screen should be one card."** `finance.bank.tsx` argues its own density
convincingly (*"The two unmatched lists are the product"*) and would be worse
with less on it. Reading My work as a density target rather than a clarity
target would damage the app.

Applied concretely, the rule produces exactly two things, both already proposed:

1. **A Finance overview that answers one question** — cash on hand, the
   break-even line, what is owed, money in against money out — instead of a
   Dashboard that answers half of it and four sibling tabs that hold the rest
   (§9.4, and B above).
2. **Home leading with "Needs attention"** rather than with five tiles of equal
   weight (§4.1). Home's job is *"what should I do now"*; the tiles answer
   *"how big is everything"*, which is a different question and belongs under it.

**Should Home and My work merge?** No. They answer *"how is the company"* and
*"what is on my plate"*, which are different questions. Linear does keep the
equivalent surfaces separate — **Inbox** and **My issues** are two of the four
personal items in its sidebar
([linear.app/docs/layout](https://linear.app/docs/layout)) — though Linear does
not publish a rationale for the split, so the reason above is mine, not theirs.
Home already links to `/my-work`, which is the right relationship.

### 9.6 What to do, ordered — and one correction

These are IA changes. They are additional to §6, not a replacement for it, and
the numbering continues from it so the two lists can be scheduled together.

| # | Change | Value | Effort | Files |
|---|---|---|---|---|
| 19 | Make every record name in Finance a link | ★★★★★ | XS ×4 | `finance.overhead`, `finance.reports`, `finance.forecast`, `documents.files` |
| 20 | `floor_breached` into the Publish card | ★★★★★ | XS | `deals.$dealCode.quote.tsx` |
| 21 | Silent-quote rows link to their deal | ★★★★ | XS | `index.tsx:265-281` |
| 22 | `Mark sent` / `Mark confirmed` on `/quotations` | ★★★★★ | S | `quotations.index`, `quotations.$quoteRef` |
| 23 | Break-even line + cash on hand onto Home | ★★★★★ | S | `index.tsx` |
| 24 | Receivables links carry `?tab=money` | ★★★ | S | with §6.11 |
| 25 | Margin / below-floor column on `/quotations` and `/deals` | ★★★ | S | `quotations.index`, `deals.index` |
| 26 | Job margin tile from `job_profitability(job=…)` | ★★★ | S | `jobs.$jobId.tsx` |
| 27 | Split the break-even line out of Overhead | ★★★★ | M | `finance.overhead.tsx`, new overview |
| 28 | Companies link to their deals, jobs and ageing | ★★ | M | `contacts.companies.tsx` |
| 29 | Job page links to `/expense?job=…` | ★★ | XS | `jobs.$jobId.tsx` |
| 30 | Hoist deal draft state into the layout route | ★★ | L | `deals.$dealCode.tsx` + 2 routes |

**The first five are one afternoon and they are the whole point of this
section.** Nineteen through twenty-three cost roughly a day between them, touch
no pricing logic, add no endpoint, rename nothing, and between them they close
every ❌ in §9.4 and three of the four seams in §9.3.

Number 30 is the one to *not* do yet (§9.5 C).

#### Correction to §7.5

§7.5 defended all nine Finance tabs on the grounds that each is backed by a
distinct server endpoint, with a table of endpoints as the evidence.

**That argument is wrong and I withdraw it.** Endpoint-distinctness shows the
*data* is distinct; it says nothing about whether the *screens* should be. By
that reasoning Home would be six screens, since it reads six endpoints. What I
was actually doing was reading each file's docstring and allowing it to justify
its own existence — which cannot discover a boundary that is collectively wrong,
because no file's docstring is written from outside itself.

The conclusion survives for seven of the nine tabs, on the different and better
evidence in §9.5 B: they answer questions somebody goes looking for
deliberately. It does **not** survive for `finance.overhead.tsx`, which holds two
jobs in one route and should split, and it never addressed the finding that
matters more than the count — that six of the nine are navigational dead ends.

§7.5's table of endpoints is still accurate and still useful. Its heading should
be read as "these tabs are not showing the same data twice", which is true,
rather than "therefore nine tabs is right", which does not follow.

#### What §9 does *not* propose

- **No renaming.** §7.1 stands unchanged. None of items 19-30 touches a term in
  `CONTEXT.md`, and the Overhead split in item 27 makes the Overhead screen a
  *better* match for its glossary entry, not a worse one.
- **No new permission surface.** Items 23 and 26 use endpoints that are already
  gated server-side (`break_even`, `cash_accounts`, `job_profitability`); Home
  already renders two founder-only cards behind `session.isFounder`.
- **No client-side arithmetic.** Every figure moved by items 19-27 is one the
  server already computes. §7.2 stands.
- **No merged Finance tabs.** §9.5 B argues the Dashboard / Income / Expenses
  trio is ordinary hub-and-spoke and should be left alone.
- **No split of the job's four tabs**, and no split of the quote editor yet.

## 10. Sources, and what could not be sourced

### 10.1 Primary sources used

**Linear** — [method/introduction](https://linear.app/method/introduction),
[method/product-direction](https://linear.app/method/product-direction),
[method/building-with-momentum](https://linear.app/method/building-with-momentum),
[method/write-issues-not-user-stories](https://linear.app/method/write-issues-not-user-stories),
[docs/conceptual-model](https://linear.app/docs/conceptual-model),
[docs/layout](https://linear.app/docs/layout),
[docs/default-team-pages](https://linear.app/docs/default-team-pages),
[docs/custom-views](https://linear.app/docs/custom-views),
[docs/filters](https://linear.app/docs/filters),
[docs/display-options](https://linear.app/docs/display-options),
[docs/search](https://linear.app/docs/search),
[docs/favorites](https://linear.app/docs/favorites),
[docs/dashboards](https://linear.app/docs/dashboards),
[now/how-we-redesigned-the-linear-ui](https://linear.app/now/how-we-redesigned-the-linear-ui),
[now/rebuilding-delta-sync-read-path](https://linear.app/now/rebuilding-delta-sync-read-path),
[method/scope-projects](https://linear.app/method/scope-projects),
[docs/projects](https://linear.app/docs/projects),
[docs/initiatives](https://linear.app/docs/initiatives),
[docs/use-cycles](https://linear.app/docs/use-cycles),
[docs/inbox](https://linear.app/docs/inbox),
[docs/my-issues](https://linear.app/docs/my-issues),
[docs/triage](https://linear.app/docs/triage),
[docs/parent-and-sub-issues](https://linear.app/docs/parent-and-sub-issues).

**Atlassian Design System** —
[foundations/grid](https://atlassian.design/foundations/grid),
[foundations/spacing](https://atlassian.design/foundations/spacing),
[foundations/typography](https://atlassian.design/foundations/typography),
[foundations/accessibility](https://atlassian.design/foundations/accessibility),
[foundations/content/language-and-grammar](https://atlassian.design/foundations/content/language-and-grammar),
[foundations/content/inclusive-writing](https://atlassian.design/foundations/content/inclusive-writing),
[foundations/content/voice-tone](https://atlassian.design/foundations/content/voice-tone),
[components/tabs/usage](https://atlassian.design/components/tabs/usage),
[components/empty-state/usage](https://atlassian.design/components/empty-state/usage),
[components/lozenge/usage](https://atlassian.design/components/lozenge/usage),
[components/dynamic-table/usage](https://atlassian.design/components/dynamic-table/usage),
[components/modal-dialog/usage](https://atlassian.design/components/modal-dialog/usage),
[components/skeleton/usage](https://atlassian.design/components/skeleton/usage),
[components/spinner/usage](https://atlassian.design/components/spinner/usage),
[components/panel/usage](https://atlassian.design/components/panel/usage),
[components/progress-indicator/usage](https://atlassian.design/components/progress-indicator/usage),
[components/navigation-system](https://atlassian.design/components/navigation-system),
[components/navigation-system/layout](https://atlassian.design/components/navigation-system/layout),
[components/navigation-system/top-nav-items](https://atlassian.design/components/navigation-system/top-nav-items),
[components/breadcrumbs/usage](https://atlassian.design/components/breadcrumbs/usage),
[components/page-header/examples](https://atlassian.design/components/page-header/examples),
[components/side-navigation/usage](https://atlassian.design/components/side-navigation/usage) (deprecated),
[components/page-layout/usage](https://atlassian.design/components/page-layout/usage) (deprecated).

**Jira product docs** —
[switch between views](https://support.atlassian.com/jira-service-management-cloud/docs/switch-between-views-for-different-ways-to-visualize-your-work-items/),
[find specific work items](https://support.atlassian.com/jira-software-cloud/docs/find-specific-issues/),
[configure field layout](https://support.atlassian.com/jira-software-cloud/docs/configure-field-layout-in-the-work-item/),
[customize your view of the board and backlog](https://support.atlassian.com/jira-software-cloud/docs/customize-your-view-of-the-board-and-backlog/),
[add and customize gadgets](https://support.atlassian.com/jira-software-cloud/docs/add-and-customize-gadgets/),
[create and edit dashboards](https://support.atlassian.com/jira-software-cloud/docs/create-and-edit-dashboards/),
[permissions overview](https://support.atlassian.com/jira/kb/jira-permissions-general-overview/),
[configure issue security schemes](https://support.atlassian.com/jira-cloud-administration/docs/configure-issue-security-schemes/),
[boards guide](https://www.atlassian.com/software/jira/guides/boards/overview),
[navigation guide](https://www.atlassian.com/software/jira/guides/navigation/overview),
[projects tutorials](https://www.atlassian.com/software/jira/guides/projects/tutorials),
[what is a Jira space](https://support.atlassian.com/jira-software-cloud/docs/what-is-a-jira-software-project/),
[what is a board](https://support.atlassian.com/jira-software-cloud/docs/what-is-a-jira-software-board/),
[use your Scrum backlog](https://support.atlassian.com/jira-software-cloud/docs/use-your-scrum-backlog/),
[save your search as a filter](https://support.atlassian.com/jira-software-cloud/docs/save-your-search-as-a-filter/),
[configure filters](https://support.atlassian.com/jira-software-cloud/docs/configure-filters/),
[create a board based on filters](https://support.atlassian.com/jira-software-cloud/docs/create-a-board-based-on-filters/),
[what is a Jira dashboard](https://support.atlassian.com/jira-software-cloud/docs/what-is-a-jira-dashboard/),
[work item hierarchy](https://www.atlassian.com/software/jira/guides/issues/overview),
[defining a project (DC)](https://confluence.atlassian.com/adminjiraserver/defining-a-project-938847066.html).

**ClickUp** —
[Intro to the Hierarchy](https://help.clickup.com/hc/en-us/articles/13856392825367-Intro-to-the-Hierarchy),
[Intro to views](https://help.clickup.com/hc/en-us/articles/6329880717719-Intro-to-views),
[Intro to ClickApps](https://help.clickup.com/hc/en-us/articles/6304327753111-Intro-to-ClickApps),
[Customizable ClickUp features](https://help.clickup.com/hc/en-us/articles/9559764679831-Customizable-ClickUp-features),
[Create and share a Table view](https://help.clickup.com/hc/en-us/articles/6329890854935-Create-and-share-a-Table-view),
[Customize List view](https://help.clickup.com/hc/en-us/articles/7255389296919-Customize-List-view),
[Intro to Custom Fields](https://help.clickup.com/hc/en-us/articles/6303536766231-Intro-to-Custom-Fields),
[Custom Field permissions](https://help.clickup.com/hc/en-us/articles/26025804975895-Custom-Field-permissions),
[Intro to permissions](https://help.clickup.com/hc/en-us/articles/6309225399703-Intro-to-permissions),
[Intro to ClickUp 4.0](https://help.clickup.com/hc/en-us/articles/31142608907543-Intro-to-ClickUp-4-0),
[My Tasks page](https://help.clickup.com/hc/en-us/articles/6308921446935-Home),
[clickup.com/about](https://clickup.com/about),
[Hierarchy best practices](https://help.clickup.com/hc/en-us/articles/20480724378135-Hierarchy-best-practices),
[What are Folders](https://help.clickup.com/hc/en-us/articles/6311450560407-What-are-Folders),
[Add a view to All Tasks](https://help.clickup.com/hc/en-us/articles/6310138041367-Add-a-view-to-All-Tasks),
[View all your tasks](https://help.clickup.com/hc/en-us/articles/6309783246103-View-all-your-tasks),
[My Tasks page (formerly Home)](https://help.clickup.com/hc/en-us/articles/18944788880791-My-Tasks-page-formerly-Home),
[Create nested subtasks](https://help.clickup.com/hc/en-us/articles/6304431740055-Create-nested-subtasks),
[Intro to subtasks](https://help.clickup.com/hc/en-us/articles/6309825777943-Intro-to-subtasks),
[Everything You Need to Know About Task Views](https://help.clickup.com/hc/en-us/articles/6310172583831-Everything-You-Need-to-Know-About-Task-Views),
[Intro to Overviews](https://help.clickup.com/hc/en-us/articles/15115821058071-Intro-to-Overviews).

**Nielsen Norman Group** —
[Ten Usability Heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/),
[Aesthetic and Minimalist Design](https://www.nngroup.com/articles/aesthetic-minimalist-design/),
[Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/),
[Response Times: The 3 Important Limits](https://www.nngroup.com/articles/response-times-3-important-limits/),
[Tabs, Used Right](https://www.nngroup.com/articles/tabs-used-right/),
[Information Scent](https://www.nngroup.com/articles/information-scent/),
[F-Shaped Pattern](https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content/),
[Layer-Cake Pattern](https://www.nngroup.com/articles/layer-cake-pattern-scanning/),
[Scrolling and Attention](https://www.nngroup.com/articles/scrolling-and-attention/),
[Flat UI Elements Attract Less Attention](https://www.nngroup.com/articles/flat-ui-less-attention-cause-uncertainty/),
[Data Tables: Four Major User Tasks](https://www.nngroup.com/articles/data-tables/),
[Mobile Tables](https://www.nngroup.com/articles/mobile-tables/),
[Legibility, Readability, and Comprehension](https://www.nngroup.com/articles/legibility-readability-comprehension/),
[International Usability: Big Stuff the Same, Details Differ](https://www.nngroup.com/articles/international-usability-details-differ/),
[International B2B](https://www.nngroup.com/articles/international-b2b/),
[IA vs. Navigation](https://www.nngroup.com/articles/ia-vs-navigation/),
[Flat vs. Deep Hierarchy](https://www.nngroup.com/articles/flat-vs-deep-hierarchy/),
[IA Questions for Navigation Menus](https://www.nngroup.com/articles/ia-questions-navigation-menus/),
[The 3-Click Rule](https://www.nngroup.com/articles/3-click-rule/),
[Interaction Cost](https://www.nngroup.com/articles/interaction-cost-definition/),
[Pogo-Sticking](https://www.nngroup.com/articles/pogo-sticking/),
[List Entries](https://www.nngroup.com/articles/list-entries/),
[Task Analysis](https://www.nngroup.com/articles/task-analysis/),
[Journey Mapping 101](https://www.nngroup.com/articles/journey-mapping-101/),
[Card Sorting](https://www.nngroup.com/articles/card-sorting-definition/),
[Mental Models](https://www.nngroup.com/articles/mental-models/),
[Match the Real World](https://www.nngroup.com/articles/match-system-real-world/),
[Recognition vs. Recall](https://www.nngroup.com/articles/recognition-and-recall/),
[Short-Term Memory and Web Usability](https://www.nngroup.com/articles/short-term-memory-and-web-usability/),
[Chunking](https://www.nngroup.com/articles/chunking/),
[Dashboards: Preattentive Attributes](https://www.nngroup.com/articles/dashboards-preattentive/),
[Complex Application Design](https://www.nngroup.com/articles/complex-application-design/),
[Mobile Navigation Patterns](https://www.nngroup.com/articles/mobile-navigation-patterns/),
[Customer Service Model](https://www.nngroup.com/articles/customer-service-model/),
[Saving Scroll Position](https://www.nngroup.com/articles/saving-scroll-position/).

**W3C** —
[WAI-ARIA APG: Tabs pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/),
[APG: Grid pattern](https://www.w3.org/WAI/ARIA/apg/patterns/grid/),
WCAG 2.2 Understanding docs for
[1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html),
[1.4.8](https://www.w3.org/WAI/WCAG22/Understanding/visual-presentation.html),
[1.4.10](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html),
[1.4.12](https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html),
[2.4.3](https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html),
[2.4.7](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html),
[3.1.1](https://www.w3.org/WAI/WCAG22/Understanding/language-of-page.html),
[3.1.2](https://www.w3.org/WAI/WCAG22/Understanding/language-of-parts.html),
[4.1.2](https://www.w3.org/WAI/WCAG22/Understanding/name-role-value.html).

### 10.2 Claims I could not source, and therefore did not make

Listed so that nobody re-introduces them from memory:

1. **Linear "Opinionated software."** No such page or heading exists on
   linear.app today. The real principle is "Purpose-built."
2. **Linear "no spinners, no waiting, no problems."** Not on the current site.
   The citable speed claim is the local-first paragraph in the engineering blog.
3. **A Linear ⌘K philosophy.** No page states one, and there is no
   `linear.app/docs/keyboard-shortcuts` page at all — only per-feature shortcut
   lists. §6.12's argument therefore rests on NN/g's weak-signifier research and
   on the plain fact that the chip does nothing, not on a Linear quote.
4. **Linear against dashboards or vanity metrics.** No source; Linear ships
   Dashboards.
5. **Linear on maximum content width or a narrow-sidebar rationale.** No source.
   §3.2's width numbers are all Atlassian's.
6. **A maximum number of tabs**, from anybody. ADS says "keep the number of tabs
   low"; NN/g says "the fewer the better". Neither gives an integer. "Nine is
   too many" is my judgement.
7. **Atlassian "WCAG 2.2 AA is the floor, not the ceiling."** A search result
   attributes this to atlassian.design; it is not on any page fetched. What ADS
   does publish is the 4.5:1 / 3:1 ratios and, in its machine-readable
   `llms.txt`, "WCAG 2.1 AA".
8. **ADS guidance on table column counts, horizontal scroll, or numeric column
   alignment.** None published. `/components/table` is marked Caution with no
   usage page.
9. **A characters-per-line measure from NN/g or Atlassian.** Neither publishes
   one. The only citable figure anywhere is WCAG 1.4.8's 80 characters, which is
   a AAA criterion.
10. **The Doherty threshold (400ms).** NN/g has published nothing on it. Its
    origin is Doherty & Thadani, *IBM Systems Journal* (1982); every accessible
    modern write-up is on a non-primary domain. §3.7 uses NN/g's 0.1 / 1 / 10
    second limits instead.
11. **A ClickUp global "Simple vs Advanced" mode.** Does not exist. "Advanced"
    appears only as local sub-menu labels. Per-Space ClickApps are the real
    mechanism.
12. **A ClickUp sidebar width figure.** Not published.
13. **Any published rationale from Linear for splitting Inbox from My Issues.**
    The two surfaces demonstrably exist side by side in the sidebar
    ([linear.app/docs/layout](https://linear.app/docs/layout)); the reasoning in
    §9.5 E for why AuraOS should keep Home and My work apart is mine.
14. ~~**NN/g on information architecture specifically**~~ — **withdrawn
    2026-08-25: this material exists and has now been read.** §9 was written
    before a second sourcing round returned, and this entry recorded the gap
    honestly at the time. It was wrong about the corpus. NN/g publishes
    canonical articles on all three:

    - **Pogo-sticking** is a named NN/g concept, and the definition indicts the
      exact shape §9 describes: *"Misleading links and omitted information force
      users to bounce back and forth in a hub-and-spoke pattern between a
      routing page and subpages linked from it, **increasing the interaction
      cost and decreasing engagement over time**"*
      ([pogo-sticking](https://www.nngroup.com/articles/pogo-sticking/)). The
      list/detail half is sharper still: *"a list entry without enough detail
      leaves too many questions unanswered, forcing users to pogo stick"*
      ([list-entries](https://www.nngroup.com/articles/list-entries/)) — which
      is §9's argument for putting `floor_breached` on the list, not only in
      the editor.
    - **Interaction cost** is defined and enumerated: *"the sum of efforts —
      mental and physical — that users must deploy in interacting with a
      digital product in order to reach their goals"*, and the enumerated list
      ends with *"**Memory load** — the information that users must remember in
      order to complete their task"*
      ([interaction-cost](https://www.nngroup.com/articles/interaction-cost-definition/)).
      That is a stronger citation than heuristic #6 for §9's remembered-record-name
      finding, because it names the cost rather than only the remedy.
    - **Breadth versus depth** exists as prose: *"Content is more discoverable
      when it's not buried under multiple intervening layers. All other things
      being equal, deep hierarchies are more difficult to use"*
      ([flat-vs-deep-hierarchy](https://www.nngroup.com/articles/flat-vs-deep-hierarchy/)).

    **What is still unsourceable is the number**, and that is worth keeping
    because it also retires item 6 above. There is no NN/g optimal count of
    items per level or of levels, and this is NN/g's *position* rather than a
    search failure — they name the seven-category rule a myth in the same
    breath as the three-click rule: *"many designers have to choose between two
    UX myths (neither supported by data): either no more than 3 clicks or no
    more than 7 main-navigation categories … they aren't supported by research,
    and they conflict"*
    ([3-click-rule](https://www.nngroup.com/articles/3-click-rule/)). The
    governing sentence is *"the number of categories should be determined by
    what makes it easiest for people to discover and access information — not
    by some preordained decision"*
    ([ia-questions-navigation-menus](https://www.nngroup.com/articles/ia-questions-navigation-menus/)).
    So "nine Finance tabs is too many" stays **my judgement**, and §9 is right
    to argue it from the six dead-end tabs rather than from the nine.

15. **Any first-party Atlassian criteria for "new project versus component
    versus label".** No such page exists on `support.atlassian.com` or the Jira
    guides. The line that circulates as Atlassian guidance — *"The time to
    create a new project is when you need a different set of project-specific
    settings"* — is from `community.atlassian.com`, a user forum, and is
    deliberately not cited here. The closest first-party statement is
    *"**There is no one-size fits all approach to structuring a project in
    Jira**"*
    ([atlassian.com](https://www.atlassian.com/software/jira/guides/projects/tutorials)).
16. **A public ADS page enumerating navigation levels.**
    `atlassian.design/components/navigation-system` states the fuller guidance is
    *"(Atlassians only)"*. What ADS publishes is layout *areas* (banner, top nav,
    side nav, main, panel) with pixel defaults. Jira's own navigation guide names
    three levels and is cited instead. `atlassian.design/patterns` redirects;
    `components/atlassian-navigation/usage` is a 404.
17. **Jira guidance on when to split a project.** None found. Confluence Data
    Center publishes a governance analogue — an 8,000-space soft ceiling and
    *"Set up space rules, including when to create new spaces"*
    ([confluence.atlassian.com](https://confluence.atlassian.com/enterprise/managing-the-number-of-spaces-in-confluence-data-center-1607598774.html))
    — which is about instance performance, not IA, and is not used above.

**A terminology caveat.** Current Jira Cloud docs have renamed **project →
space** and **issue → work item**; Data Center docs still use the old words.
Quotations in this document preserve whichever term the cited page uses, which
is why §6.17 says "work item" and §9.1 says both. That is inconsistency in the
source, not in the citation.

The same churn runs through ClickUp, and worse, because it is applied
inconsistently inside their own documentation: **Home → My Tasks**, **Everything
view → All Tasks**, **LineUp → Priorities**. The last is live mid-rename — the
card table on the My Tasks page still says "LineUp" while the page that
documents the card is titled "Use the Priorities card". Where this document
quotes ClickUp it preserves the vintage of the page quoted.

**A sourcing caveat.** `atlassian.design` is a client-rendered SPA: plain fetches
return a ~640KB shell whose article bodies are empty, and there is no
`page-data.json` escape hatch. Every `atlassian.design` quote here was read from
a rendered page in a browser. `support.atlassian.com`, `www.atlassian.com` and
`confluence.atlassian.com` are server-rendered and fetch normally.

**One more caveat specific to §9.** Its flow traces are read off the routing
and the `<Link>` graph, not observed over anyone's shoulder. They are an
accurate account of what the app *permits* and *affords*; they are not a claim
about what any particular producer actually does. A half-day of watching one
person price a deal and one person close a shoot would be worth more than the
whole of §9, and nothing here substitutes for it.

### 10.3 Method

Codebase measurements were taken on `origin/main` at `05607de` by counting
literal occurrences in `frontend-react/src/routes/` and
`frontend-react/src/components/aura/`, and by arithmetic on the width constants
in the files named. Contrast ratios were computed from the OKLCH values in
`styles.css` by converting through OKLab to linear sRGB and applying the WCAG
relative-luminance formula; they are arithmetic on the source tokens, not
measurements of rendered pixels, and should be confirmed with a contrast tool
before anyone changes a colour on their authority.

`help.clickup.com` refuses automated fetches with HTTP 403. **This sentence
first said the content "was retrieved from the same URLs over plain HTTP",
which is wrong** — plain `curl` is refused exactly as the fetcher is. The pages
yield only to a full browser header set (User-Agent, Accept, Accept-Language
and `Sec-Fetch-*` together), which is how every `help.clickup.com` quote here
was obtained; all of them are verifiable in a browser. Separately,
`clickup.com/hierarchy-guide` is client-rendered — its raw HTML carries only tab
labels — so no per-level copy is quoted from it.

**Dead URLs met while sourcing**, recorded so nobody re-derives them:
`linear.app/docs/cycles`, `/docs/views`, `/docs/sub-issues` and `/docs/issues` are
all 404 (use `use-cycles`, `custom-views`, `parent-and-sub-issues`);
`linear.app/method/scope-projects-down` is `scope-projects`;
`nngroup.com/articles/the-magical-number-seven/` is 404 and its content lives in
`/articles/chunking/`; `nngroup.com/articles/dashboards-preattentive-attributes/`
is 404 and the slug is `/articles/dashboards-preattentive/`. NN/g's *"How Many
Items in a Navigation Menu?"* is **video-only** and so is quoted nowhere here.
`atlassian.design` component pages are client-rendered and were read in a
browser rather than fetched.

Nothing in this document was taken from a blog roundup, a Medium post, or a
"UX tips" listicle.

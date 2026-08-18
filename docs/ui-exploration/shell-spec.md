# App shell spec - left spine navigation

Founder direction, 2026-08-18:

> bạn tạo không gian trống 2 bên là đúng nhưng như vậy đang làm cho UX UI không đồng nhất vì Cost breakdown đang là full width screen. Add thêm navigation bar bên side bar trái. Sau đó gom UX UI không để nó quá rộng 2 ra 2 bên thử xem

Three requirements: the bounded sheet is right but Cost breakdown breaks the consistency, navigation moves to a left sidebar, and the content should be pulled tighter rather than spread across the full width.

The sidebar resolves all three at once. Every screen gets the same frame, so the breakdown stops being the odd one out; its wide table scrolls inside the content area instead of escaping the layout.

**This spec is copied verbatim into every prototype. Do not restyle it, do not rename classes, do not change the measures.** The only per-page difference is which nav item carries `class="on"`.

## The frame

```
+--------+--------------------------------------------+
| spine  |  app-main                                   |
| 208px  |    +------------------------------------+  |
|  ink   |    |  measure - max 1120px, centred     |  |
|  black |    |  document screens live here        |  |
|        |    +------------------------------------+  |
|        |  wide tables get .bleed instead and         |
|        |  scroll inside app-main                     |
+--------+--------------------------------------------+
```

At 1440px: spine 208 + main 1232. A 1120px sheet inside 1232 leaves 56px of desk each side, which is the "gom lại" the founder asked for - previously it was about 160px each side.

## CSS - paste verbatim

```css
/* ---- app shell ---------------------------------------------------- */
:root{ --desk:#BEBBB0; --stock:#E6E4DD; --ink:#14130E; --ink2:#6E6B60; --rule:#B9B6AA; }
html,body{margin:0;padding:0}
/* ROUND 4: the ground is stock, not desk. While content was narrow, a desk
   tone behind a bounded sheet read as paper on a desk. At full width all that
   survived was a 24px band around the edge, which reads as leftover margin -
   the founder called it out. The working area IS the sheet now. `--desk` is
   kept only for the rare element that still wants a recessed tone. */
body{background:var(--stock);}
.app{display:grid;grid-template-columns:208px minmax(0,1fr);min-height:100vh;align-items:start}

/* the spine: a binder edge, reusing the reversed-ink device the sections
   already use, so it is the same stationery rather than a new component */
.spine{position:sticky;top:0;align-self:start;height:100vh;background:var(--ink);
  color:var(--stock);display:flex;flex-direction:column;
  font:600 11px/1.2 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  letter-spacing:.14em;text-transform:uppercase}
.spine-mark{padding:18px 14px 16px;border-bottom:1px solid #3a372f}
.spine-mark b{display:block;font-size:15px;letter-spacing:.2em}
.spine-mark span{display:block;margin-top:5px;font-size:9px;color:#8d887a;letter-spacing:.12em}
.spine-nav{list-style:none;margin:0;padding:8px 0 0}
.spine-nav a{display:block;padding:9px 14px;color:var(--stock);text-decoration:none;
  border-left:3px solid transparent}
.spine-nav a:hover{background:#221f19}
.spine-nav a:focus-visible{outline:2px solid var(--stock);outline-offset:-2px}
.spine-nav .on a{background:var(--stock);color:var(--ink);border-left-color:#A81F16}
.spine-foot{margin-top:auto;padding:14px;border-top:1px solid #3a372f}
.spine-foot a{color:#8d887a;text-decoration:none}
.spine-foot a:hover{color:var(--stock)}

/* the working area.
   REVISED 2026-08-18 round 3: there is no narrow measure any more. Every
   screen fills app-main edge to edge. The founder asked for full width on
   all screens for consistency, plus "gom nhóm / rút gọn UI lại cho phù hợp".
   Those two go together: width is spent by GROUPING content into columns,
   never by stretching one column of text or a lone row across 1200px.
   Stretching is what was rejected in round 1, not width itself - and a real
   call sheet is already a multi-column document, so this is the more
   faithful reading of the direction. */
.app-main{min-width:0;padding:22px 24px 90px;background:var(--stock)}
/* the 24px padding stays - text must not touch the ink spine - but it is now
   stock on stock, so it is breathing room rather than a visible edge */
.sheet{border-color:transparent;box-shadow:none}

/* grouping grids - use these rather than inventing per-page column systems */
.grid2{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:22px;align-items:start}
.grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px;align-items:start}
@media (max-width:1100px){ .grid2,.grid3{grid-template-columns:minmax(0,1fr)} }

/* below 900px the spine lies down as a top strip */
@media (max-width:900px){
  /* minmax(0,1fr), not 1fr: a plain 1fr track takes its min-content from the
     nav labels and lets the page scroll sideways on a phone */
  .app{grid-template-columns:minmax(0,1fr)}
  .spine{position:static;height:auto;flex-direction:row;align-items:center;
    flex-wrap:wrap;gap:0 2px;padding:0 8px}
  .spine-mark{border-bottom:0;padding:10px 10px 10px 4px}
  .spine-mark span{display:none}
  /* must wrap: six items at min-content are ~430px, wider than a 390px phone,
     which forced 56px of horizontal page scroll before this was added */
  .spine-nav{display:flex;flex-wrap:wrap;padding:0}
  .spine-nav a{padding:10px;border-left:0;border-bottom:3px solid transparent}
  .spine-nav .on a{border-left-color:transparent;border-bottom-color:#A81F16}
  .spine-foot{margin-left:auto;border-top:0;padding:10px}
  .app-main{padding:14px 12px 90px}
}
```

## HTML - paste verbatim as the first child of `<body>`

Wrap the whole existing page content in `<div class="app"> … <main class="app-main"> … </main></div>`.

```html
<div class="app">
<nav class="spine" aria-label="Main navigation">
  <div class="spine-mark"><b>AuraOS</b><span>Production ops</span></div>
  <ul class="spine-nav">
    <li><a href="dense-dashboard-call-sheet.html">Home</a></li>
    <li><a href="pipeline-call-sheet.html">Deals</a></li>
    <li><a href="#jobs">Jobs</a></li>
    <li><a href="#contacts">Contacts</a></li>
    <li><a href="#paperwork">Paperwork</a></li>
    <li><a href="#settings">Settings</a></li>
  </ul>
  <div class="spine-foot"><a href="#logout">Log out</a></div>
</nav>
<main class="app-main">

  <!-- existing page content goes here, wrapped in .measure or .bleed -->

</main>
</div>
```

Add `class="on"` to exactly one `<li>`:

| Page | Active item |
| --- | --- |
| `dense-dashboard-call-sheet.html` | Home |
| `pipeline-call-sheet.html` | Deals |
| `dense-breakdown-call-sheet.html` | Deals |
| `dense-quote-call-sheet.html` | Deals |

## Per-page application

| Page | Note |
| --- | --- |
| Dashboard | Fills `app-main`. Content regrouped into columns so nothing stretches. |
| Quote builder | Fills `app-main`. Same. |
| Breakdown | The table keeps its full width and scrolls inside `app-main`. Its pinned stub and computed gutters pin against the content area, not the viewport. |
| Pipeline board | The board is genuinely wider than the screen; it keeps scrolling horizontally inside `app-main`. |

Removing the measure also gives width back to the two screens that were paying for it: the breakdown's working band and the pipeline board both widen by the 56px of desk that used to sit either side.

## Rules that still apply

- Any existing `body{padding-bottom:90px}` moves to `.app-main` so the switcher never covers content.
- The page must not scroll horizontally. Only `app-main`'s inner wrappers may.
- No Vietnamese inside a mono-styled element. Every nav label above is ASCII, so the spine is safe.
- No em dash anywhere. Use "-".
- Keep the prototype switcher block at the end of `<body>`, outside `.app`, unchanged.

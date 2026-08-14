---
date: 2026-08-14
question: >
  How far can the existing Vue + frappe-ui + Tailwind setup in frontend/ be
  pushed visually without forking components - palette, global theming
  (fonts/spacing/radius/dark mode), and which components hard-code styles a
  restyle would have to fight?
status: complete
---

# frappe-ui theming constraints - what the real frontend can express

Researched against primary sources only: `frontend/node_modules/frappe-ui`
(installed version, per `frontend/package.json` line 8: `"frappe-ui": "^0.1.0"`,
resolved to **0.1.278** per `frontend/node_modules/frappe-ui/package.json`
line 2), `frontend/tailwind.config.cjs`, `frontend/src/index.css`, and the
frappe-ui GitHub repo ([github.com/frappe/frappe-ui](https://github.com/frappe/frappe-ui))
for context where the installed source is undocumented inline.

## 1. TL;DR

- The restricted palette is real and by design: `frappe-ui/tailwind/plugin.js`
  sets `theme.colors` (not `theme.extend.colors`), so it **replaces** Tailwind's
  default 22-family color object with 12 families total. Off-palette classes
  like `emerald`/`sky`/`indigo`/`lime` don't exist as keys at all, so Tailwind's
  JIT compiler generates no CSS for them - hence "silently transparent."
  Sanctioned fix: standard Tailwind `theme.extend.colors` in the app's own
  `frontend/tailwind.config.cjs` (additive, doesn't fight the preset).
- Fonts, spacing (additively), border radius, and dark mode are all themeable
  through documented mechanisms - dark mode exists in this version via a
  `[data-theme="dark"]` attribute selector plus a shipped `useTheme()`
  composable, but the app currently uses none of it.
- Every frappe-ui component actually imported by this app (`Button`, `Dialog`,
  `ErrorMessage`, `FeatherIcon`, `FileUploader`, `FormControl`, `Checkbox`,
  `TextEditor`) is built on the CSS-custom-property token layer
  (`--ink-*`, `--surface-*`, `--outline-*`), which is cleanly re-themeable by
  overriding those variables in `frontend/src/index.css` - no component
  forking needed for color/shape restyle. The one real fight: several
  components (`Button`, `Badge`, `Alert`) hard-code a small, **inconsistent**
  per-component subset of the 12 color families as a `theme` prop enum
  (e.g. `Button` only wires up gray/blue/green/red - see below), so a brand
  color outside that subset can't be selected through props even though it
  exists in the palette.

## 2. What restricts the Tailwind palette, and how to extend it

`frontend/tailwind.config.cjs` (full file):

```js
module.exports = {
  presets: [require("frappe-ui/tailwind")],
  content: [
    "./index.html",
    "./src/**/*.{vue,js}",
    "./node_modules/frappe-ui/src/components/**/*.{vue,js}",
  ],
}
```

The app adds no `theme` key of its own - it inherits 100% of its color/type/
spacing scale from the frappe-ui preset.

`frontend/node_modules/frappe-ui/tailwind/index.js` re-exports
`frontend/node_modules/frappe-ui/tailwind/preset.js`, which registers
`themePlugin` (from `plugin.js`) alongside `@tailwindcss/forms`,
`@tailwindcss/typography`, and a Lucide icons plugin.

`frontend/node_modules/frappe-ui/tailwind/plugin.js` (lines 47-64) calls
Tailwind's `plugin(fn, config)` with a second argument whose `theme.colors`
key is set directly - **not** nested under `theme.extend`:

```js
export default plugin(
  function ({ addBase, addComponents, theme }) { ... },
  {
    theme: {
      colors: colorPalette,       // <- replaces, does not extend
      borderRadius: { ... },      // <- also replaces (no 3xl, no default Tailwind sizes)
      boxShadow: { ... },
      fontSize: { ... },          // <- also replaces (caps at 3xl = 24px, no 4xl-9xl)
      screens: { ... },
      extend: { spacing: {...}, width: {...}, ... },  // additive, see below
    },
  },
)
```

In Tailwind's config-resolution order, a plugin's non-`extend` theme keys are
merged the same way a preset's are: they become the base that the *app's own*
`theme.extend` is layered on top of. Since the app config currently declares
no `theme` at all, the resolved `colors` object is exactly
`colorPalette` from `frontend/node_modules/frappe-ui/tailwind/colorPalette.js`.

`colorPalette.js` (lines 4-25) builds that object explicitly:

```js
const colorPalette = {
  inherit, current, transparent, black, white,
  gray: {}, blue: {}, green: {}, red: {}, orange: {}, yellow: {},
  teal: {}, violet: {}, cyan: {}, amber: {}, pink: {}, purple: {},
  'white-overlay': {}, 'black-overlay': {},
}
```

populated from `frontend/node_modules/frappe-ui/tailwind/colors.json`, whose
`lightMode`/`darkMode` objects have exactly these 12 keys (verified by
inspection): `gray, blue, green, red, amber, orange, yellow, teal, cyan,
purple, pink, violet`. There is no `emerald`, `sky`, `indigo`, `lime`, `rose`,
`fuchsia`, `slate`, `zinc`, `neutral`, or `stone` key anywhere in this object -
they aren't overridden to empty, they simply don't exist. Tailwind's JIT
generator only emits a utility class if the referenced theme key resolves;
an unresolvable color name produces no rule, so `bg-emerald-500` compiles to
nothing and the element keeps its default (transparent) background. This
exactly matches the reported symptom.

**Sanctioned extension mechanism:** standard Tailwind preset/extend
composition, nothing frappe-ui-specific. Because the *app's own*
`tailwind.config.cjs` `theme.extend` is resolved after all presets (including
plugin-injected theme), adding

```js
module.exports = {
  presets: [require("frappe-ui/tailwind")],
  theme: {
    extend: {
      colors: { brand: { 500: '#...', ... } }, // new families, additive
    },
  },
  content: [ ... ],
}
```

adds new families (or overrides one of the 12 existing families, e.g. `gray`)
without touching the preset file and without losing any frappe-ui component's
own generated classes (since those reference the semantic tokens, see §4, not
raw palette names directly in most cases). Fully **replacing** the whole
`colors` object (non-extend) is also possible but would require
re-declaring everything frappe-ui's own components depend on (`gray`,
`blue`, etc., plus the semantic `ink`/`surface`/`outline` scales) - not
recommended.

`borderRadius` and `fontSize` are replaced the same way (not `extend`), so
the app also only has `none/sm/DEFAULT/md/lg/xl/2xl/full` radii (no
Tailwind-default `3xl`) and a type scale capped at `3xl` = 24px (no
`4xl`-`9xl`) unless the app extends those keys too, by the identical
mechanism.

## 3. Global theming: fonts, spacing, radius, dark mode

**Fonts.** `plugin.js` `globalStyles()` (lines 12-16) sets
`html { font-family: InterVar, ${theme('fontFamily.sans')} }`. `InterVar` is
declared via `@font-face` in
`frontend/node_modules/frappe-ui/src/fonts/Inter/inter.css` (variable-font
woff2, weights 100-900). This CSS file is **not currently imported anywhere**
in `frontend/src` (checked `main.js`, `index.css`) - the app hasn't pulled in
the actual Inter font files, so `InterVar` silently falls through to the
Tailwind default sans stack in whatever browser renders it today. Swapping
fonts is a standard Tailwind `theme.extend.fontFamily` override in the app's
own config plus an `@font-face`/`@import` in `frontend/src/index.css` -
nothing frappe-ui-specific blocks this, and there's no competing font
currently loaded to fight.

**Spacing.** Base spacing scale is Tailwind's untouched default (4px grid);
`plugin.js` only adds fractional half-steps under `extend.spacing` (lines
245-260, e.g. `4.5: '1.125rem'`) plus a few named `width`/`height`/`minWidth`
values. This is fully additive - the app can extend further the same way
without conflict.

**Border radius.** Themeable, but as a **replacement** scale (§2) rather than
an extension - the whole `borderRadius` object in `plugin.js` (lines 55-64)
would need to be overridden via the app's own `theme.borderRadius` (or
`theme.extend.borderRadius` to add sizes) to change the "roundedness"
language app-wide (e.g. sharper corners for a divergent direction).

**Dark mode.** Supported in this version. `frontend/node_modules/frappe-ui/tailwind/preset.js`
line 8: `darkMode: ['selector', '[data-theme="dark"]']` - dark variants
activate off a `data-theme="dark"` attribute on `<html>`, not
`prefers-color-scheme` directly. `colorPalette.js` `generateCSSVariables()`
(lines 59-107) emits two blocks of CSS custom properties, one under `:root`
(light values) and one under `[data-theme="dark"]` (dark values), covering
every semantic token (`--surface-*`, `--ink-*`, `--outline-*`) and every raw
shade (`--gray-500`, `--dark-gray-500`, etc.) - these are injected via
`addBase` in `plugin.js` line 49, so they land in Tailwind's base layer.
frappe-ui ships a ready-made toggle composable at
`frontend/node_modules/frappe-ui/src/utils/theme.ts` (`useTheme()`):
`setTheme('light'|'dark'|'system')` sets `data-theme` on
`document.documentElement` and persists to `localStorage`; `system` mode also
subscribes to the `prefers-color-scheme` media query. **The app does not use
this today** - a search of `frontend/src` found no `data-theme` or `dark:`
usage, and `frontend/src/main.js` imports only `setConfig`, `frappeRequest`,
`resourcesPlugin` from `frappe-ui`, not `useTheme` or the legacy `FrappeUI`
plugin. So dark mode is available "for free" at the token layer but has never
been wired up in this codebase - turning it on is a `useTheme()` call plus a
toggle control, not new plumbing.

**Recolor without touching Tailwind config at all.** Because every token is a
CSS custom property emitted by `addBase` (Tailwind `@layer base`), and
`frontend/src/index.css` (checked in full - 8 lines, only a `.truncate`
line-height fix today) is compiled as *unlayered* CSS after `@tailwind base;`,
any `:root { --surface-gray-2: ...; --ink-gray-9: ...; }` block added there
wins the cascade over the layered preset defaults (CSS spec: unlayered rules
beat any `@layer`-declared rules regardless of source order or specificity).
This means the entire semantic surface/ink/outline system can be recolored
app-wide by editing `frontend/src/index.css` alone, no Tailwind config change
and no component fork.

## 4. Which imported frappe-ui components fight a restyle, and which don't

Components actually imported in `frontend/src` (from `grep -rn "from \"frappe-ui\"" frontend/src`):
`Button`, `Dialog`, `ErrorMessage`, `FeatherIcon`, `FileUploader`,
`FormControl`, `Checkbox`, `TextEditor`, plus non-visual `createResource`,
`createListResource`, `setConfig`, `frappeRequest`, `resourcesPlugin`,
`ListView` (imported in `ContactsPage.vue`).

**Cleanly themeable (token-driven, no arbitrary values):**
- `Dialog` - `frontend/node_modules/frappe-ui/src/components/Dialog/Dialog.vue`:
  every color class is a semantic token (`bg-surface-modal`, `text-ink-gray-9`,
  `bg-black-overlay-200`, `dark:bg-black-overlay-700` on line 5 - i.e. it
  already has a dark-mode class ready to go). Shape (`rounded-xl`) and
  animation are the only non-recolorable parts, both overridable via
  `<style>`/config, not JS logic.
- `FormControl` (`.../FormControl/FormControl.vue`) - a thin router to
  `TextInput`/`Select`/`Textarea`/`Checkbox`/`Combobox`/`Autocomplete`; its own
  template has zero hardcoded colors, only token-based description text
  (`text-ink-gray-5`, line 111).
- `Checkbox` (`.../Checkbox/Checkbox.vue`) - 100% semantic tokens
  (`bg-surface-white`, `border-outline-gray-4`, `text-ink-gray-9`, etc.),
  fully recolorable via CSS-variable override.
- `FileUploader` (`.../FileUploader/FileUploader.vue`) - no styling of its
  own; renders a hidden `<input>` and a default `<slot>` containing a
  `Button` (line 23), fully replaceable via the slot without touching the
  component.
- `ErrorMessage`, `FeatherIcon` - trivial, token-based or unstyled (icon
  outlines inherit `currentColor`).
- `TextEditor` (`.../TextEditor/style.css`) - almost entirely `var(--ink-*)`
  / `var(--outline-*)` / `var(--surface-*)`, including inline fallback hex
  values (e.g. line 96: `var(--surface-gray-1, #f8f8f8)`) that only apply if
  the variable is somehow unset. One outlier at line 85:
  `color: theme('colors.gray.900')` for the task-list checkbox tick, which
  resolves through the same `gray` family that `theme.extend.colors.gray`
  would override (§2) - not a hardcoded literal, but not a CSS-variable
  either, so overriding it requires a Tailwind config change rather than a
  CSS-variable override.

**The real fight - hardcoded theme enums, not CSS:**
- `Button` (`.../Button/Button.vue`, lines 116-154) hardcodes four
  JS objects (`solidClasses`, `subtleClasses`, `outlineClasses`,
  `ghostClasses`, `focusClasses`, `disabledClassesMap`) each keyed on exactly
  `{ gray, blue, green, red }`, and `Button/types.ts` types the `theme` prop
  to that same 4-value union (confirmed against
  `.../Button/stories/Themes.vue`, which only demonstrates those four). A
  divergent brand color - even one of the 8 *other* families frappe-ui's own
  palette already defines (`orange`, `yellow`, `teal`, `cyan`, `purple`,
  `pink`, `violet`, `amber`) - has no `theme="..."` value that reaches it on
  `Button` without either (a) overriding the `gray`/`blue`/`green`/`red` CSS
  variables globally (which recolors every other gray/blue/green/red use in
  the app too), or (b) forking `Button.vue` to add a themeClasses entry.
- The other components sampled for their own `Themes.vue` stories confirm
  this is **per-component and inconsistent**, not a single shared enum:
  `Badge` wires up `gray, blue, green, orange`
  (`.../Badge/stories/Themes.vue`); `Alert` wires up
  `green, yellow, red, blue` (`.../Alert/stories/Themes.vue`). A single
  "accent" color picked for a restyle is not guaranteed to be pluggable into
  every themed component without touching component internals - only the
  gray/blue/green/red-ish defaults are safe everywhere.

## 5. What this means for a restyle

**Cheap, no theming layer needed, for:**
- Any palette recolor that works by overriding the existing semantic tokens
  (`--surface-*`, `--ink-*`, `--outline-*`, and the raw `--gray-*` /
  `--blue-*` / etc. shade variables) in `frontend/src/index.css`. This
  reaches `Dialog`, `FormControl`, `Checkbox`, `FileUploader`, `ErrorMessage`,
  and almost all of `TextEditor` with zero component changes.
- Adding new color families, fonts, or extra spacing/radius values via
  `theme.extend` in `frontend/tailwind.config.cjs` - standard Tailwind, fully
  additive, doesn't fight the preset.
- Turning on dark mode - the token infrastructure and a working
  `useTheme()` composable already ship in this version; it's unused, not
  unsupported.

**Needs budget - a small theming/wrapper layer, not a full fork, for:**
- Any restyle whose brand accent isn't one of `Button`'s four wired colors
  (`gray/blue/green/red`) if the design wants that accent to show up as a
  solid/subtle/outline/ghost *button*, since that mapping is JS logic, not
  CSS. Cheapest real fix is a thin app-level wrapper component (e.g.
  `AppButton.vue`) that maps the app's own theme names onto frappe-ui's
  `theme` prop plus a manual class override for the one custom look - still
  not a fork of `Button.vue` itself, but it is new code, not pure config.
  The same applies wherever the divergent direction needs `Badge`/`Alert` in
  a color those components don't wire up either.
- The `borderRadius` and `fontSize` scales are **replacement**, not
  **extension**, in the preset - pushing the type scale beyond `3xl` (24px)
  or getting Tailwind's default `3xl` radius back requires an explicit
  `theme.extend` (or full override) entry per key, not just adding one line;
  small effort, but worth calling out as a real (if minor) gap versus
  "it just works."

**Bottom line:** a divergent color/type/spacing/dark-mode direction can be
expressed in the real frontend cheaply, through config and CSS-variable
overrides, for every component this app currently imports except `Button`'s
(and by extension `Badge`'s/`Alert`'s) hardcoded theme-color enum. The spec
should budget a small amount of time for either (a) picking a winning accent
that happens to land on gray/blue/green/red, or (b) a thin wrapper component
for the buttons/badges/alerts - not a theming layer, and not forking
frappe-ui.

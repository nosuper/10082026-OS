// Attio Clean / Producer Desk tokens. Every colour, radius and shadow the new UI
// uses lives here - components never hardcode a hex.
// `carbon`, not `ink`: frappe-ui's preset owns `ink` as a nested scale
// (ink-gray-1, ink-amber-2 and friends) in the textColor, fill, stroke and
// placeholder namespaces, and a namespace entry beats theme.extend.colors. A
// colors.ink of our own therefore yields bg-ink and border-ink but no bare
// text-ink, so the build dies on @apply text-ink. Their scale is not reachable
// either - frappe-ui's exports map only publishes ./tailwind. Renaming our
// token is the supportable fix; text-ink-gray-5 stays theirs.
module.exports = {
  presets: [require("frappe-ui/tailwind")],
  content: [
    "./index.html",
    "./src/**/*.{vue,js}",
    "./node_modules/frappe-ui/src/components/**/*.{vue,js}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#fbfbfa",
        paper: "#ffffff",
        carbon: "#1a1a1a",
        "carbon-soft": "#2d2d2d",
        muted: "#6b6b6b",
        faint: "#9a9a98",
        hairline: "#e8e8e7",
        accent: {
          DEFAULT: "#e85d3a",
          soft: "#fdf0ec",
          ink: "#b8431f",
        },
        // Semantic states, kept quiet so the ember accent stays the only loud colour.
        ok: "#2f7a55",
        warn: "#9a6b12",
        "warn-soft": "#fdf6e7",
      },
      fontFamily: {
        display: ['"Space Grotesk"', "system-ui", "sans-serif"],
        sans: ['"DM Sans"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      borderRadius: {
        card: "12px",
        pill: "999px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(26, 26, 26, 0.04)",
        drawer: "-8px 0 24px rgba(26, 26, 26, 0.08)",
      },
      backgroundImage: {
        dots: "radial-gradient(circle, #e8e8e7 1px, transparent 1px)",
      },
      backgroundSize: {
        dots: "24px 24px",
      },
      spacing: {
        sidebar: "256px",
      },
    },
  },
}

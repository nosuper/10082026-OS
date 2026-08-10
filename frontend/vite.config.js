import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import frappeui from "frappe-ui/vite"

// Built assets are served by Frappe from auraos/public/aura at
// /assets/auraos/aura/; the HTML shell is copied to auraos/www/aura.html
// by copy-html-entry.mjs so the page is reachable at /aura.
//
// Only the lucideIcons part of the frappeui plugin is enabled: it
// supplies the ~icons/lucide/* imports frappe-ui components use.
// frappeProxy is off because its bench-path walk never terminates on
// Windows (`while (currentDir !== '/')`); the dev proxy below is the
// same thing declared by hand. jinjaBootData/buildConfig are off
// because we manage the outDir and HTML shell ourselves.
export default defineConfig({
  plugins: [
    frappeui({
      frappeProxy: false,
      jinjaBootData: false,
      buildConfig: false,
    }),
    vue(),
  ],
  base: "/assets/auraos/aura/",
  build: {
    outDir: "../auraos/public/aura",
    emptyOutDir: true,
    target: "es2018",
  },
  server: {
    port: 8080,
    proxy: {
      "^/(app|login|api|assets|files|private)": {
        target: "http://127.0.0.1:8000",
        ws: true,
      },
    },
  },
})

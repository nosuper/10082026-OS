import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import tsConfigPaths from "vite-tsconfig-paths";
import { tanstackRouter } from "@tanstack/router-plugin/vite";

// Plain Vite, no TanStack Start: this app has no server functions and no SSR,
// so it builds to a static SPA that Frappe serves. Built assets land in
// auraos/public/aura-next and are served at /assets/auraos/aura-next/; the HTML
// shell is copied to auraos/www/aura-next.html by copy-html-entry.mjs so the
// page is reachable at /aura-next.
//
// The router plugin stays: it is what regenerates src/routeTree.gen.ts from
// the files in src/routes.
export default defineConfig({
  plugins: [
    tanstackRouter({ target: "react", autoCodeSplitting: true }),
    react(),
    tailwindcss(),
    tsConfigPaths(),
  ],
  base: "/assets/auraos/aura-next/",
  build: {
    outDir: "../auraos/public/aura-next",
    emptyOutDir: true,
    target: "es2020",
  },
  server: {
    port: 8081,
    proxy: {
      "^/(app|login|api|assets|files|private)": {
        target: "http://127.0.0.1:8000",
        ws: true,
      },
    },
  },
});

import { RouterProvider } from "@tanstack/react-router";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { getRouter } from "./router";
import { requireSession } from "./lib/session";
import "./styles.css";

// The page itself is public - the data behind it is not. Bounce guests to the
// Frappe login before mounting, so no screen ever paints without a session.
if (requireSession()) {
  const container = document.getElementById("aura-next-root");
  if (!container) {
    throw new Error("missing #aura-next-root in the page shell");
  }

  createRoot(container).render(
    <StrictMode>
      <RouterProvider router={getRouter()} />
    </StrictMode>,
  );
}

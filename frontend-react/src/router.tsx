import { QueryClient } from "@tanstack/react-query";
import { createRouter } from "@tanstack/react-router";
import { routeTree } from "./routeTree.gen";

// Frappe serves this app under /aura-next (see the website_route_rules entry in
// auraos/hooks.py), so the router has to treat that prefix as its root or a
// reload on a deep link 404s inside the app.
export const BASEPATH = "/aura-next";

export const getRouter = () => {
  const queryClient = new QueryClient();

  const router = createRouter({
    routeTree,
    basepath: BASEPATH,
    context: { queryClient },
    scrollRestoration: true,
    defaultPreloadStaleTime: 0,
  });

  return router;
};

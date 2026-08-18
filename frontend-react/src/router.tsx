import { QueryClient } from "@tanstack/react-query";
import { createRouter } from "@tanstack/react-router";
import { routeTree } from "./routeTree.gen";
import { FrappeError } from "./lib/frappe";

// Frappe serves this app under /aura-next (see the website_route_rules entry in
// auraos/hooks.py), so the router has to treat that prefix as its root or a
// reload on a deep link 404s inside the app.
export const BASEPATH = "/aura-next";

export const getRouter = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        // The desk is a working screen, not a live dashboard: half a minute of
        // staleness is invisible and saves a refetch on every navigation.
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        // A refused request is refused. Retrying a permission error just makes
        // the screen take three times as long to say so; only a lost
        // connection or a server fault is worth a second attempt.
        retry: (failureCount, error) => {
          if (!(error instanceof FrappeError)) return false;
          return (error.kind === "network" || error.kind === "server") && failureCount < 2;
        },
      },
      // A write is never retried: the server may have applied the first one.
      mutations: { retry: false },
    },
  });

  const router = createRouter({
    routeTree,
    basepath: BASEPATH,
    context: { queryClient },
    scrollRestoration: true,
    defaultPreloadStaleTime: 0,
  });

  return router;
};

import { createRouter, createWebHistory } from "vue-router"

const routes = [
  // The board is the landing page: deal state at a glance is the
  // headline pain of the project.
  { path: "/", redirect: "/deals" },
  {
    path: "/deals",
    name: "Deals",
    component: () => import("./pages/DealsPage.vue"),
  },
  {
    path: "/contacts",
    name: "Contacts",
    component: () => import("./pages/ContactsPage.vue"),
  },
]

// Frappe serves the SPA at /aura (website_route_rules in hooks.py).
export const router = createRouter({
  history: createWebHistory("/aura"),
  routes,
})

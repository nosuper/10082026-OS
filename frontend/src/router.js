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
    path: "/deals/:name/breakdown",
    name: "DealBreakdown",
    component: () => import("./pages/DealBreakdownPage.vue"),
  },
  {
    path: "/jobs",
    name: "Jobs",
    component: () => import("./pages/JobsPage.vue"),
  },
  {
    path: "/jobs/:name",
    name: "Job",
    component: () => import("./pages/JobPage.vue"),
  },
  {
    // The phone screen: one thing, big enough to hit while holding a
    // receipt in the other hand.
    path: "/jobs/:name/expense",
    name: "JobExpense",
    component: () => import("./pages/JobExpensePage.vue"),
  },
  {
    path: "/contacts",
    name: "Contacts",
    component: () => import("./pages/ContactsPage.vue"),
  },
  {
    path: "/settings",
    name: "Settings",
    component: () => import("./pages/SettingsPage.vue"),
  },
  {
    path: "/overhead",
    name: "Overhead",
    component: () => import("./pages/OverheadPage.vue"),
  },
]

// Frappe serves the SPA at /aura (website_route_rules in hooks.py).
export const router = createRouter({
  history: createWebHistory("/aura"),
  routes,
})

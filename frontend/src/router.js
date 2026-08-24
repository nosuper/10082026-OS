import { createRouter, createWebHistory } from "vue-router"

const routes = [
  // Home is the landing page (founder, A4 round 4): the day's numbers
  // and the quick expense before any navigation.
  {
    path: "/",
    name: "Home",
    component: () => import("./pages/HomePage.vue"),
  },
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
    // The crew screens (T7.1): the only pages a designer or editor can
    // open, and money-free by construction - they read
    // auraos.api.crew_job and auraos.api.job_tasks, never the Job.
    path: "/my-work",
    name: "MyWork",
    component: () => import("./pages/MyWorkPage.vue"),
  },
  {
    path: "/my-work/:name",
    name: "CrewJob",
    component: () => import("./pages/CrewJobPage.vue"),
  },
  {
    path: "/contacts",
    name: "Contacts",
    component: () => import("./pages/ContactsPage.vue"),
  },
  {
    path: "/paperwork",
    name: "Paperwork",
    component: () => import("./pages/PaperworkPage.vue"),
  },
  {
    path: "/settings",
    name: "Settings",
    component: () => import("./pages/SettingsPage.vue"),
  },
  {
    // The deal-classification SOP, linked from the deal form so the
    // rule book is one click from where the call is made.
    path: "/sop/deals",
    name: "SopDeals",
    component: () => import("./pages/SopDealsPage.vue"),
  },
]

// Frappe serves the SPA at /aura (website_route_rules in hooks.py).
export const router = createRouter({
  history: createWebHistory("/aura"),
  routes,
})

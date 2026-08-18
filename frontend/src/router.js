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
  // The sidebar splits the directory into Companies and People. Both land on
  // the same page until Phase 4 builds them properly; the page already opens
  // on its Companies tab, so /contacts keeps working as the shorter address.
  {
    path: "/contacts",
    redirect: "/contacts/companies",
  },
  {
    path: "/contacts/companies",
    name: "ContactsCompanies",
    component: () => import("./pages/ContactsPage.vue"),
  },
  {
    path: "/contacts/people",
    name: "ContactsPeople",
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

import { createRouter, createWebHistory } from "vue-router"

const routes = [
  { path: "/", redirect: "/contacts" },
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

<template>
  <div class="min-h-screen bg-gray-50">
    <header class="border-b bg-white">
      <!-- Wraps on a phone rather than pushing the whole page sideways:
           the expense screen is used one-handed on a shoot, and a page
           that pans left and right reads as broken. Unchanged from `sm`
           up, where the row has always fitted. -->
      <div
        class="mx-auto flex max-w-5xl flex-wrap items-center gap-x-3 gap-y-1
               px-3 py-2 sm:h-14 sm:flex-nowrap sm:gap-x-6 sm:px-4 sm:py-0"
      >
        <span class="text-lg font-semibold text-gray-900">AuraOS</span>
        <nav class="flex flex-wrap gap-1">
          <router-link
            v-for="item in nav"
            :key="item.route"
            :to="item.route"
            class="rounded px-2 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 sm:px-3"
            active-class="bg-gray-100 text-gray-900"
          >
            {{ item.label }}
          </router-link>
        </nav>
        <Button class="ml-auto" variant="ghost" @click="logout.fetch()">
          Log out
        </Button>
      </div>
    </header>
    <main>
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from "vue"
import { Button, createResource } from "frappe-ui"

// Settings only appears for sessions that can actually read it (the
// founder); probing the floor endpoint doubles as the role check.
const isFounder = ref(false)
createResource({
  url: "auraos.api.get_margin_floor",
  auto: true,
  onSuccess() {
    isFounder.value = true
  },
  onError() {},
})

const nav = computed(() => [
  { label: "Home", route: "/" },
  { label: "Deals", route: "/deals" },
  { label: "Jobs", route: "/jobs" },
  { label: "Contacts", route: "/contacts" },
  // Both roles: producers generate paperwork, the founder owns the
  // templates, and the page itself only offers what the session may do.
  { label: "Paperwork", route: "/paperwork" },
  ...(isFounder.value ? [{ label: "Settings", route: "/settings" }] : []),
])

// Log out via the API, then land on a login page that returns here -
// otherwise re-login strands the user in the Desk.
const logout = createResource({
  url: "logout",
  onSuccess() {
    window.location.replace(
      "/login?redirect-to=" + encodeURIComponent("/aura/deals")
    )
  },
})

// The page itself is public; the data is not. Bounce guests to login.
// Read Frappe's user_id cookie instead of calling the API: a failed
// API call here (e.g. CSRF) would redirect logged-in users to /login,
// which bounces straight back - an infinite reload loop.
const userId = document.cookie
  .split("; ")
  .find((c) => c.startsWith("user_id="))
  ?.split("=")[1]
if (!userId || decodeURIComponent(userId) === "Guest") {
  window.location.replace(
    "/login?redirect-to=" + encodeURIComponent(window.location.pathname)
  )
}
</script>

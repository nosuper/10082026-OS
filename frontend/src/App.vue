<template>
  <AppShell :is-founder="isFounder" :user-name="userName" @logout="logout.fetch()">
    <router-view />
  </AppShell>
</template>

<script setup>
import { ref } from "vue"
import { createResource } from "frappe-ui"
import AppShell from "./components/AppShell.vue"

// Settings only appears for sessions that can actually read it (the founder);
// probing the floor endpoint doubles as the role check. The UI is never the
// permission boundary - the server refuses the data either way.
const isFounder = ref(false)
createResource({
  url: "auraos.api.get_margin_floor",
  auto: true,
  onSuccess() {
    isFounder.value = true
  },
  onError() {},
})

// The page itself is public; the data is not. Bounce guests to login.
// Read Frappe's user_id cookie instead of calling the API: a failed API call
// here (e.g. CSRF) would redirect logged-in users to /login, which bounces
// straight back - an infinite reload loop.
const userId = document.cookie
  .split("; ")
  .find((c) => c.startsWith("user_id="))
  ?.split("=")[1]

if (!userId || decodeURIComponent(userId) === "Guest") {
  window.location.replace(
    "/login?redirect-to=" + encodeURIComponent(window.location.pathname)
  )
}

const userName = decodeURIComponent(userId || "").split("@")[0] || "Signed in"

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
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <header class="border-b bg-white">
      <div class="mx-auto flex h-14 max-w-5xl items-center gap-6 px-4">
        <span class="text-lg font-semibold text-gray-900">AuraOS</span>
        <nav class="flex gap-1">
          <router-link
            v-for="item in nav"
            :key="item.route"
            :to="item.route"
            class="rounded px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100"
            active-class="bg-gray-100 text-gray-900"
          >
            {{ item.label }}
          </router-link>
        </nav>
      </div>
    </header>
    <main>
      <router-view />
    </main>
  </div>
</template>

<script setup>
const nav = [{ label: "Contacts", route: "/contacts" }]

// The page itself is public; the data is not. Bounce guests to login.
// Read Frappe's user_id cookie instead of calling the API: a failed
// API call here (e.g. CSRF) would redirect logged-in users to /login,
// which bounces straight back — an infinite reload loop.
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

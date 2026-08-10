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
import { createResource } from "frappe-ui"

const nav = [{ label: "Contacts", route: "/contacts" }]

// The page itself is public; the data is not. Bounce guests to login.
createResource({
  url: "frappe.auth.get_logged_user",
  auto: true,
  onError() {
    window.location.href =
      "/login?redirect-to=" + encodeURIComponent(window.location.pathname)
  },
})
</script>

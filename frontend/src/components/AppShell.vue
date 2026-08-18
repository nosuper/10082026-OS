<template>
  <div class="aura-canvas flex min-h-screen">
    <!-- Sidebar is persistent on desktop and hidden on a phone: the one screen
         used on set (expense entry) is single-column and needs the full width. -->
    <SidebarNav
      class="hidden lg:flex"
      :is-founder="isFounder"
      :user-name="userName"
      @logout="$emit('logout')"
    />

    <div class="flex min-w-0 flex-1 flex-col">
      <header
        class="sticky top-0 z-10 flex h-14 items-center gap-3 border-b border-hairline bg-canvas/85 px-4 backdrop-blur"
      >
        <div class="min-w-0 lg:hidden">
          <span class="font-display text-sm font-semibold text-carbon">AuraOS</span>
        </div>
        <div class="min-w-0 flex-1">
          <QuickActions @submit="$emit('search', $event)" />
        </div>
        <div class="shrink-0"><slot name="actions" /></div>
      </header>

      <!-- Mobile nav row: the sidebar's top-level routes, scrollable. -->
      <nav class="flex gap-1 overflow-x-auto border-b border-hairline px-3 py-2 lg:hidden">
        <router-link
          v-for="item in mobileNav"
          :key="item.route"
          :to="item.route"
          class="flex items-center gap-1.5 whitespace-nowrap rounded-[8px] px-2 py-1 text-sm text-muted"
          active-class="bg-accent-soft text-accent-ink"
        >
          <FeatherIcon :name="item.icon" class="h-4 w-4 shrink-0" aria-hidden="true" />
          {{ item.label }}
        </router-link>
      </nav>

      <main class="min-w-0 flex-1 px-4 py-5 lg:px-6 lg:py-6">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue"
import { FeatherIcon } from "frappe-ui"
import SidebarNav from "./SidebarNav.vue"
import QuickActions from "./QuickActions.vue"

const props = defineProps({
  isFounder: { type: Boolean, default: false },
  userName: { type: String, default: "" },
})

defineEmits(["logout", "search"])

// Same icons as the sidebar, so a route looks the same whichever nav you meet
// it in.
const mobileNav = computed(() => [
  { label: "Home", route: "/", icon: "home" },
  { label: "Deals", route: "/deals", icon: "trending-up" },
  { label: "Jobs", route: "/jobs", icon: "film" },
  { label: "Paperwork", route: "/paperwork", icon: "file-text" },
  { label: "Companies", route: "/contacts/companies", icon: "briefcase" },
  { label: "People", route: "/contacts/people", icon: "users" },
  ...(props.isFounder ? [{ label: "Settings", route: "/settings", icon: "settings" }] : []),
])
</script>

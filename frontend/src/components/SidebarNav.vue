<template>
  <aside
    class="flex w-sidebar shrink-0 flex-col border-r border-hairline bg-surface/80 backdrop-blur"
  >
    <div class="flex h-14 items-center gap-2 px-4">
      <span class="flex h-5 w-5 items-center justify-center rounded-[6px] bg-accent">
        <span class="h-1.5 w-1.5 rounded-full bg-white"></span>
      </span>
      <span class="font-display text-base font-semibold text-ink">AuraOS</span>
    </div>

    <nav class="flex-1 space-y-0.5 px-2 py-2">
      <template v-for="item in items" :key="item.label">
        <!-- Group with sub-routes (Contacts -> Companies / People). -->
        <div v-if="item.children" class="pt-3">
          <div class="aura-eyebrow px-2 pb-1">{{ item.label }}</div>
          <router-link
            v-for="child in item.children"
            :key="child.route"
            :to="child.route"
            class="block rounded-[8px] px-2 py-1.5 text-sm text-muted transition-colors hover:bg-canvas hover:text-ink"
            active-class="bg-accent-soft text-accent-ink"
          >
            {{ child.label }}
          </router-link>
        </div>

        <router-link
          v-else
          :to="item.route"
          class="block rounded-[8px] px-2 py-1.5 text-sm text-muted transition-colors hover:bg-canvas hover:text-ink"
          active-class="bg-accent-soft text-accent-ink"
        >
          {{ item.label }}
        </router-link>
      </template>
    </nav>

    <div class="border-t border-hairline px-3 py-3">
      <div class="flex items-center gap-2">
        <span class="h-7 w-7 shrink-0 rounded-full border border-hairline bg-canvas"></span>
        <div class="min-w-0">
          <div class="truncate text-sm font-medium text-ink">{{ userName }}</div>
          <div class="aura-eyebrow">{{ isFounder ? "Founder" : "Producer" }}</div>
        </div>
        <button
          class="ml-auto rounded-[8px] p-1 text-faint transition-colors hover:bg-canvas hover:text-ink"
          title="Log out"
          @click="$emit('logout')"
        >
          <FeatherIcon name="log-out" class="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from "vue"
import { FeatherIcon } from "frappe-ui"

const props = defineProps({
  isFounder: { type: Boolean, default: false },
  userName: { type: String, default: "" },
})

defineEmits(["logout"])

// Contacts is a group, not a page: Companies and People are their own routes so
// refresh and deep links land where the user was.
const items = computed(() => [
  { label: "Home", route: "/" },
  { label: "Deals", route: "/deals" },
  { label: "Jobs", route: "/jobs" },
  { label: "Paperwork", route: "/paperwork" },
  {
    label: "Contacts",
    children: [
      { label: "Companies", route: "/contacts/companies" },
      { label: "People", route: "/contacts/people" },
    ],
  },
  ...(props.isFounder
    ? [
        {
          label: "Founder",
          children: [
            { label: "Settings", route: "/settings" },
            { label: "SOP · Deals", route: "/sop/deals" },
          ],
        },
      ]
    : []),
])
</script>

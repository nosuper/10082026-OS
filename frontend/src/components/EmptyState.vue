<template>
  <div class="flex flex-col items-center justify-center gap-1 px-4 py-8 text-center">
    <FeatherIcon v-if="icon" :name="icon" class="h-4 w-4 text-faint" />
    <p class="text-sm text-muted">{{ title }}</p>
    <p v-if="detail" class="text-xs text-faint">{{ detail }}</p>
    <slot />
  </div>
</template>

<script setup>
import { FeatherIcon } from "frappe-ui"

defineProps({
  icon: { type: String, default: "" },
  title: { type: String, required: true },
  detail: { type: String, default: "" },
})
</script>

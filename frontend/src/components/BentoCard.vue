<template>
  <component
    :is="to ? 'router-link' : 'div'"
    :to="to || undefined"
    class="flex flex-col p-4"
    :class="[
      founder ? 'aura-card-founder' : 'aura-card',
      to ? 'transition-colors hover:border-accent/40' : '',
      attention && !founder ? 'border-accent/40' : '',
    ]"
  >
    <div v-if="title || $slots.action" class="mb-3 flex items-start gap-2">
      <div class="min-w-0">
        <div class="aura-eyebrow" :class="founder ? 'text-white/60' : ''">
          {{ title }}
        </div>
        <div
          v-if="subtitle"
          class="mt-0.5 text-xs"
          :class="founder ? 'text-white/50' : 'text-faint'"
        >
          {{ subtitle }}
        </div>
      </div>
      <div class="ml-auto shrink-0">
        <slot name="action" />
      </div>
    </div>
    <div class="min-w-0 flex-1">
      <slot />
    </div>
    <div v-if="$slots.footer" class="mt-3 border-t pt-2" :class="founder ? 'border-white/10' : 'border-hairline'">
      <slot name="footer" />
    </div>
  </component>
</template>

<script setup>
// The only card chrome in the app. `founder` inverts it (margin data),
// `attention` outlines it in the accent (something needs a human).
defineProps({
  title: { type: String, default: "" },
  subtitle: { type: String, default: "" },
  to: { type: [String, Object], default: null },
  founder: { type: Boolean, default: false },
  attention: { type: Boolean, default: false },
})
</script>

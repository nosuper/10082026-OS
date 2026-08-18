<template>
  <span
    class="inline-flex items-center rounded-pill border px-2 py-0.5 text-[11px] font-medium uppercase tracking-[0.06em]"
    :class="toneClass"
  >
    <slot>{{ label }}</slot>
  </span>
</template>

<script setup>
import { computed } from "vue"

// Tones are deliberately few: neutral for facts, accent for "act on this",
// warn for "watch this", ok for settled. Stage vocabularies map onto these.
const props = defineProps({
  label: { type: String, default: "" },
  tone: { type: String, default: "neutral" },
})

const TONES = {
  neutral: "border-hairline bg-canvas text-muted",
  ink: "border-carbon bg-carbon text-white",
  accent: "border-accent/30 bg-accent-soft text-accent-ink",
  warn: "border-warn/25 bg-warn-soft text-warn",
  ok: "border-ok/25 bg-ok/5 text-ok",
}

const toneClass = computed(() => TONES[props.tone] || TONES.neutral)
</script>

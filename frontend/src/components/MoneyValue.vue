<template>
  <span class="aura-num" :class="[sizeClass, toneClass]">{{ text }}</span>
</template>

<script setup>
import { computed } from "vue"
import { vnd, vndShort } from "../utils/money"

// One place decides how money reads: grouped thousands, no decimals, tabular
// numerals so columns line up. `short` is for headline tiles only.
const props = defineProps({
  amount: { type: [Number, String], default: null },
  short: { type: Boolean, default: false },
  size: { type: String, default: "md" },
  tone: { type: String, default: "ink" },
  placeholder: { type: String, default: "—" },
})

const SIZES = {
  sm: "text-xs",
  md: "text-sm",
  lg: "text-2xl font-medium",
  xl: "text-3xl font-medium",
}

const TONES = {
  ink: "text-ink",
  muted: "text-muted",
  accent: "text-accent",
  inverse: "text-white",
}

const value = computed(() => {
  const n = typeof props.amount === "string" ? Number(props.amount) : props.amount
  return Number.isFinite(n) ? n : null
})

const text = computed(() => {
  if (value.value === null) return props.placeholder
  return props.short ? vndShort(value.value) : vnd(value.value)
})

const sizeClass = computed(() => SIZES[props.size] || SIZES.md)
const toneClass = computed(() => TONES[props.tone] || TONES.ink)
</script>

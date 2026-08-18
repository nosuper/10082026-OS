<template>
  <span class="aura-num whitespace-nowrap" :class="[sizeClass, toneClass]"
    >{{ text }}<span v-if="value !== null" class="ml-1 text-faint">₫</span></span
  >
</template>

<script setup>
import { computed } from "vue"
import { vnd } from "../utils/money"

// One place decides how money reads: grouped thousands, no decimals, tabular
// numerals so columns line up, and a đồng sign so a figure is never mistaken
// for a count.
//
// `short` no longer spells the magnitude. vndShort renders "1,9 tỷ" and
// "850 triệu", and the founder reads those as words where a figure belongs -
// the design reference uses full digits everywhere and never abbreviates.
// The prop stays so call sites keep working, but it now only means "this is a
// headline figure"; it no longer changes the number.
const props = defineProps({
  amount: { type: [Number, String], default: null },
  short: { type: Boolean, default: false },
  size: { type: String, default: "md" },
  tone: { type: String, default: "ink" },
  placeholder: { type: String, default: "-" },
})

const SIZES = {
  sm: "text-xs",
  md: "text-sm",
  lg: "text-2xl font-medium",
  xl: "text-3xl font-medium",
}

const TONES = {
  ink: "text-carbon",
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
  return vnd(value.value)
})

const sizeClass = computed(() => SIZES[props.size] || SIZES.md)
const toneClass = computed(() => TONES[props.tone] || TONES.ink)
</script>

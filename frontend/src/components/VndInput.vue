<template>
  <input
    :value="display"
    type="text"
    inputmode="numeric"
    autocomplete="off"
    @input="onInput"
    @keydown.enter="$emit('enter', $event)"
    @keydown.esc="$emit('esc', $event)"
    @blur="$emit('blur', $event)"
  />
</template>

<script setup>
import { computed } from "vue"
import { parseVnd, vnd } from "../utils/money"

// A money field that always reads the way money is written: the user
// types digits, the field itself shows 2.000.000, the model carries the
// number. Raw digits sitting beside formatted displays confused the
// founder on the A1 walkthrough — the fix is that the two never differ.
const props = defineProps({
  modelValue: { type: [Number, String], default: "" },
})

const emit = defineEmits(["update:modelValue", "enter", "esc", "blur"])

const display = computed(() =>
  props.modelValue === "" || props.modelValue == null
    ? ""
    : vnd(props.modelValue)
)

function onInput(event) {
  const value = parseVnd(event.target.value) || ""
  // Rewrite the field immediately so stray characters never linger; a
  // caret jump to the end is the accepted price on a money field.
  event.target.value = value === "" ? "" : vnd(value)
  emit("update:modelValue", value)
}
</script>

<template>
  <div class="relative">
    <input
      :value="modelValue"
      type="text"
      :placeholder="placeholder"
      :class="inputClass"
      autocomplete="off"
      @input="onInput"
      @focus="open = true"
      @blur="onBlur"
      @keydown.esc="open = false"
    />
    <div
      v-if="open && filtered.length"
      class="absolute left-0 top-full z-30 mt-0.5 max-h-48 w-56 overflow-y-auto rounded-md border bg-white py-1 shadow-lg"
    >
      <button
        v-for="option in filtered"
        :key="option"
        type="button"
        class="block w-full truncate px-3 py-1.5 text-left text-sm text-gray-800 hover:bg-gray-50"
        @mousedown.prevent="pick(option)"
      >
        {{ option }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue"

// A datalist looked like a bare dialog and hid its options until typing
// (founder, A2 walkthrough) - this is the query-style picker instead:
// click shows everything, typing filters, free text still allowed so
// vocabularies keep growing in place.
const props = defineProps({
  modelValue: { type: String, default: "" },
  // Plain strings, already ordered.
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: "" },
  inputClass: {
    type: String,
    default: "w-36 rounded border-gray-200 px-2 py-1 text-sm",
  },
})

const emit = defineEmits(["update:modelValue", "commit"])

const open = ref(false)

const filtered = computed(() => {
  const needle = (props.modelValue || "").toLowerCase()
  const all = props.options.filter(Boolean)
  if (!needle) return all
  return all.filter((option) => option.toLowerCase().includes(needle))
})

function onInput(event) {
  open.value = true
  emit("update:modelValue", event.target.value)
}

function pick(option) {
  emit("update:modelValue", option)
  open.value = false
  emit("commit", option)
}

function onBlur() {
  open.value = false
  emit("commit", props.modelValue)
}
</script>

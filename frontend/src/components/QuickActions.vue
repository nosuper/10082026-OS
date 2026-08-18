<template>
  <div class="relative w-full max-w-sm">
    <FeatherIcon
      name="search"
      class="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint"
    />
    <input
      ref="input"
      v-model="query"
      type="text"
      :placeholder="placeholder"
      class="w-full rounded-[10px] border border-hairline bg-surface py-1.5 pl-8 pr-12 text-sm text-ink placeholder:text-faint focus:border-accent/40 focus:aura-focus"
      @keydown.esc="clear"
      @keydown.enter="submit"
    />
    <span
      class="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 rounded-[6px] border border-hairline px-1.5 py-0.5 text-[10px] text-faint"
    >
      ⌘K
    </span>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref } from "vue"
import { FeatherIcon } from "frappe-ui"

// The header field is both search and command entry. `/` and ⌘K focus it from
// anywhere except while typing in another field.
defineProps({
  placeholder: { type: String, default: "Search deals, jobs, people…" },
})

const emit = defineEmits(["submit"])

const query = ref("")
const input = ref(null)

function isTyping(target) {
  const tag = target?.tagName
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target?.isContentEditable
}

function onKeydown(event) {
  const combo = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k"
  const slash = event.key === "/" && !isTyping(event.target)
  if (combo || slash) {
    event.preventDefault()
    input.value?.focus()
  }
}

function clear() {
  query.value = ""
  input.value?.blur()
}

function submit() {
  if (query.value.trim()) emit("submit", query.value.trim())
}

onMounted(() => window.addEventListener("keydown", onKeydown))
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown))
</script>

<template>
  <div class="mx-auto max-w-xl px-4 py-6">
    <h1 class="mb-4 text-lg font-semibold text-gray-900">Company Settings</h1>

    <div v-if="denied" class="rounded-md border bg-gray-50 px-3 py-2 text-sm text-gray-600">
      Only the founder can view company settings.
    </div>

    <div v-else class="rounded-lg border bg-white p-4">
      <label class="block text-sm font-medium text-gray-800">
        Global margin floor %
      </label>
      <p class="mt-1 text-xs text-gray-500">
        Quotes whose margin falls below this warn every role — without
        revealing where the number comes from. 0 turns the warning off.
      </p>
      <div class="mt-3 flex items-center gap-2">
        <input
          v-model.number="floorPct"
          type="number"
          min="0"
          step="0.5"
          class="w-28 rounded border-gray-200 px-2 py-1 text-right text-sm"
        />
        <Button variant="solid" :loading="saver.loading" @click="save">
          Save
        </Button>
        <span v-if="saved" class="text-xs text-green-700">Saved.</span>
      </div>
      <hr class="my-5" />

      <label class="block text-sm font-medium text-gray-800">
        Quote silence nudge (days)
      </label>
      <p class="mt-1 text-xs text-gray-500">
        A sent quote with no reply after this many days is flagged on the
        deal board. 0 turns the nudge off.
      </p>
      <div class="mt-3 flex items-center gap-2">
        <input
          v-model.number="silenceDays"
          type="number"
          min="0"
          step="1"
          class="w-28 rounded border-gray-200 px-2 py-1 text-right text-sm"
        />
        <Button variant="solid" :loading="silenceSaver.loading" @click="saveSilence">
          Save
        </Button>
        <span v-if="silenceSaved" class="text-xs text-green-700">Saved.</span>
      </div>

      <ErrorMessage class="mt-2" :message="error" />
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue"
import { Button, ErrorMessage, createResource } from "frappe-ui"
import { frappeErrorMessage } from "../utils/frappeError"

const floorPct = ref(0)
const denied = ref(false)
const saved = ref(false)
const error = ref("")

createResource({
  url: "auraos.api.get_margin_floor",
  auto: true,
  onSuccess(value) {
    floorPct.value = value
  },
  onError() {
    // Producer sessions have no read permission on the settings single.
    denied.value = true
  },
})

const saver = createResource({
  url: "auraos.api.set_margin_floor",
  onSuccess(value) {
    floorPct.value = value
    saved.value = true
    error.value = ""
  },
  onError(err) {
    saved.value = false
    error.value = frappeErrorMessage(err)
  },
})

function save() {
  saved.value = false
  saver.submit({ pct: floorPct.value || 0 })
}

const silenceDays = ref(5)
const silenceSaved = ref(false)

createResource({
  url: "auraos.api.get_quote_silence_days",
  auto: true,
  onSuccess(value) {
    silenceDays.value = value
  },
  onError() {
    denied.value = true
  },
})

const silenceSaver = createResource({
  url: "auraos.api.set_quote_silence_days",
  onSuccess(value) {
    silenceDays.value = value
    silenceSaved.value = true
    error.value = ""
  },
  onError(err) {
    silenceSaved.value = false
    error.value = frappeErrorMessage(err)
  },
})

function saveSilence() {
  silenceSaved.value = false
  silenceSaver.submit({ days: silenceDays.value || 0 })
}
</script>

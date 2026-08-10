<template>
  <div class="rounded-lg border p-4">
    <h3 class="mb-1 text-xs font-semibold uppercase text-gray-500">
      Client-facing quote
    </h3>
    <p class="text-xs text-gray-500">
      Publishing freezes the packages and totals above into a new version
      at its own link. Published versions never change — send a new one
      instead.
    </p>

    <textarea
      v-model="notes"
      rows="2"
      class="mt-3 w-full rounded border-gray-200 px-2 py-1 text-sm"
      placeholder="Note for the client (validity, payment terms…)"
    />
    <Button class="mt-2" variant="solid" :loading="publishing" @click="publish">
      Publish version {{ (quotes.data?.[0]?.version || 0) + 1 }}
    </Button>

    <div v-if="quotes.data?.length" class="mt-4 space-y-3">
      <div
        v-for="quote in quotes.data"
        :key="quote.name"
        class="rounded-md border p-3 text-sm"
      >
        <div class="flex items-center gap-2">
          <span class="font-medium">v{{ quote.version }}</span>
          <span
            class="rounded-full px-2 py-0.5 text-xs"
            :class="STATUS_CLASS[quote.status] || 'bg-gray-100 text-gray-700'"
          >
            {{ quote.status }}
          </span>
          <span class="ml-auto tabular-nums text-gray-600">
            {{ vnd(quote.total) }}
          </span>
        </div>

        <div class="mt-2 flex items-center gap-2 text-xs">
          <a
            :href="quote.url"
            target="_blank"
            rel="noopener"
            class="truncate text-blue-700 hover:underline"
          >
            {{ quote.url }}
          </a>
          <button
            class="shrink-0 rounded border px-1.5 py-0.5 text-gray-600 hover:bg-gray-50"
            @click="copy(quote.url)"
          >
            {{ copied === quote.url ? "Copied" : "Copy" }}
          </button>
          <a
            :href="quote.pdf_url"
            class="shrink-0 rounded border px-1.5 py-0.5 text-gray-600 hover:bg-gray-50"
          >
            PDF
          </a>
        </div>

        <div class="mt-2 flex items-center gap-2 text-xs text-gray-600">
          <span :class="quote.opens ? 'text-green-700' : ''">
            {{ quote.opens }} open{{ quote.opens === 1 ? "" : "s" }}
          </span>
          <span v-if="quote.sent_on">· sent {{ day(quote.sent_on) }}</span>
          <span v-if="quote.confirmed_on">
            · confirmed {{ day(quote.confirmed_on) }}
          </span>
          <span class="ml-auto flex gap-1">
            <button
              v-if="quote.status === 'Published'"
              class="rounded border px-1.5 py-0.5 hover:bg-gray-50"
              @click="mark(quote, 'sent')"
            >
              Mark sent
            </button>
            <button
              v-if="quote.status !== 'Confirmed'"
              class="rounded border px-1.5 py-0.5 hover:bg-gray-50"
              @click="mark(quote, 'confirmed')"
            >
              Mark confirmed
            </button>
          </span>
        </div>
      </div>
    </div>
    <p v-else class="mt-4 text-xs text-gray-400">
      No quote published yet.
    </p>

    <ErrorMessage class="mt-2" :message="error" />
  </div>
</template>

<script setup>
import { ref } from "vue"
import { Button, ErrorMessage, createResource } from "frappe-ui"
import { frappeErrorMessage } from "../utils/frappeError"

const props = defineProps({
  deal: { type: String, required: true },
  // Called before publishing so the version freezes what the producer
  // sees on screen, not the last thing they happened to save.
  beforePublish: { type: Function, default: null },
})
const emit = defineEmits(["changed"])

const STATUS_CLASS = {
  Published: "bg-gray-100 text-gray-700",
  Sent: "bg-blue-50 text-blue-700",
  Confirmed: "bg-green-50 text-green-700",
}

const notes = ref("")
const error = ref("")
const publishing = ref(false)
const copied = ref("")

const quotes = createResource({
  url: "auraos.api.deal_quotes",
  params: { deal: props.deal },
  auto: true,
  onError: onFail,
})

function onFail(err) {
  error.value = frappeErrorMessage(err)
}

const publisher = createResource({
  url: "auraos.api.publish_quote",
  onSuccess() {
    error.value = ""
    notes.value = ""
    quotes.reload()
  },
  onError: onFail,
})

async function publish() {
  publishing.value = true
  try {
    if (props.beforePublish) await props.beforePublish()
    await publisher.submit({ deal: props.deal, notes: notes.value })
  } catch (err) {
    onFail(err)
  } finally {
    publishing.value = false
  }
}

function onMarked() {
  error.value = ""
  quotes.reload()
  // Marking sent can move the deal's stage server-side.
  emit("changed")
}

const markers = {
  sent: createResource({
    url: "auraos.api.mark_quote_sent",
    onSuccess: onMarked,
    onError: onFail,
  }),
  confirmed: createResource({
    url: "auraos.api.mark_quote_confirmed",
    onSuccess: onMarked,
    onError: onFail,
  }),
}

function mark(quote, what) {
  markers[what].submit({ quote: quote.name })
}

function copy(url) {
  navigator.clipboard?.writeText(url)
  copied.value = url
}

function vnd(amount) {
  if (amount == null) return "—"
  return new Intl.NumberFormat("vi-VN").format(amount)
}

function day(value) {
  return value?.slice(0, 10)
}
</script>

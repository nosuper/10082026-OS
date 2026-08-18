<template>
  <BentoCard
    title="Client-facing quote"
    subtitle="Publishing freezes the packages and totals above into a new version at its own link. Published versions never change - send a new one instead."
  >
    <textarea
      v-model="notes"
      rows="2"
      class="w-full rounded-[10px] border border-hairline bg-paper px-2.5 py-2 text-sm text-carbon placeholder:text-faint focus:border-accent focus:ring-0"
      placeholder="Note for the client (validity, payment terms…)"
    />
    <button
      type="button"
      class="mt-2 inline-flex w-full items-center justify-center gap-1.5 rounded-[10px] bg-accent px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-ink disabled:cursor-not-allowed disabled:opacity-60"
      :disabled="publishing"
      @click="publish"
    >
      <FeatherIcon
        :name="publishing ? 'loader' : 'send'"
        class="h-3.5 w-3.5"
        :class="publishing ? 'animate-spin' : ''"
      />
      Publish version {{ (quotes.data?.[0]?.version || 0) + 1 }}
    </button>

    <ul v-if="quotes.data?.length" class="mt-4 divide-y divide-hairline">
      <li v-for="quote in quotes.data" :key="quote.name" class="py-3 first:pt-0">
        <div class="flex items-center gap-2">
          <span class="aura-num text-sm font-semibold text-carbon">
            v{{ quote.version }}
          </span>
          <StatusPill :label="quote.status" :tone="statusTone(quote.status)" />
          <MoneyValue :amount="quote.total" class="ml-auto" />
        </div>

        <div class="mt-2 flex items-center gap-1.5 text-xs">
          <a
            :href="quote.url"
            target="_blank"
            rel="noopener"
            class="aura-num min-w-0 truncate text-muted hover:text-accent"
          >
            {{ quote.url }}
          </a>
          <button type="button" :class="chip" @click="copy(quote.url)">
            {{ copied === quote.url ? "Copied" : "Copy" }}
          </button>
          <a :href="quote.pdf_url" :class="chip">PDF</a>
        </div>

        <div class="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
          <button
            type="button"
            class="underline-offset-2 hover:underline"
            :class="quote.opens ? 'font-medium text-ok' : ''"
            @click="toggleOpens(quote)"
          >
            {{ quote.opens }} open{{ quote.opens === 1 ? "" : "s" }}
            <template v-if="quote.downloads">
              · {{ quote.downloads }} PDF
            </template>
            <template v-if="quote.last_open">
              · last {{ day(quote.last_open) }}
            </template>
          </button>
          <span v-if="quote.sent_on" class="text-faint">
            · sent {{ day(quote.sent_on) }}
          </span>
          <span v-if="quote.confirmed_on" class="text-faint">
            · confirmed {{ day(quote.confirmed_on) }}
          </span>
          <span class="ml-auto flex shrink-0 gap-1">
            <button
              v-if="quote.status !== 'Sent'"
              type="button"
              :class="chip"
              @click="mark(quote, 'sent')"
            >
              {{ quote.status === "Confirmed" ? "Undo confirm" : "Mark sent" }}
            </button>
            <button
              v-if="quote.status !== 'Confirmed'"
              type="button"
              :class="chip"
              @click="mark(quote, 'confirmed')"
            >
              Mark confirmed
            </button>
          </span>
        </div>

        <!-- Story 22: *when* it was opened is what decides follow-up timing. -->
        <ul
          v-if="openLog[quote.name]"
          class="mt-2 border-t border-hairline pt-2 text-xs text-faint"
        >
          <li v-for="(event, i) in openLog[quote.name]" :key="i" class="aura-num">
            {{ event.opened_on?.slice(0, 16) }} · {{ event.via }}
          </li>
          <li v-if="!openLog[quote.name].length" class="text-muted">
            No opens yet.
          </li>
        </ul>
      </li>
    </ul>
    <EmptyState v-else title="No quote published yet." />

    <ErrorMessage class="mt-2" :message="error" />
  </BentoCard>
</template>

<script setup>
import { ref } from "vue"
import { ErrorMessage, FeatherIcon, createResource } from "frappe-ui"
import BentoCard from "./BentoCard.vue"
import EmptyState from "./EmptyState.vue"
import MoneyValue from "./MoneyValue.vue"
import StatusPill from "./StatusPill.vue"
import { frappeErrorMessage } from "../utils/frappeError"

const props = defineProps({
  deal: { type: String, required: true },
  // Called before publishing so the version freezes what the producer
  // sees on screen, not the last thing they happened to save.
  beforePublish: { type: Function, default: null },
})
const emit = defineEmits(["changed"])

// Quiet chrome for the secondary actions - the ember belongs to Publish.
const chip =
  "shrink-0 rounded-[6px] border border-hairline bg-paper px-1.5 py-0.5 text-muted transition-colors hover:border-accent/40 hover:text-accent-ink"

// Published is a fact, Sent is in flight, Confirmed is settled.
function statusTone(status) {
  if (status === "Confirmed") return "ok"
  if (status === "Sent") return "accent"
  return "neutral"
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

const openLog = ref({})

const opensLoader = createResource({
  url: "auraos.api.quote_opens",
  onError: onFail,
})

function toggleOpens(quote) {
  if (openLog.value[quote.name]) {
    delete openLog.value[quote.name]
    return
  }
  opensLoader.submit({ quote: quote.name }).then((events) => {
    openLog.value = { ...openLog.value, [quote.name]: events || [] }
  })
}

function copy(url) {
  navigator.clipboard?.writeText(url)
  copied.value = url
}

function day(value) {
  return value?.slice(0, 10)
}
</script>

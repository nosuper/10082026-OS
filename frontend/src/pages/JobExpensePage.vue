<template>
  <!-- Built for one hand on a shoot: amount, category, save. Everything
       else has a default that is right nearly every time. The column stays
       narrow and phone-first even on a desktop - this screen is never the
       one you sit down to. -->
  <div class="mx-auto max-w-md space-y-3">
    <!-- Head: which job you are spending against, then the one verb. -->
    <div class="min-w-0">
      <router-link
        :to="`/jobs/${name}`"
        class="inline-flex max-w-full items-center gap-1 text-xs text-muted hover:text-accent"
      >
        <FeatherIcon name="arrow-left" class="h-3 w-3 shrink-0" />
        <span class="truncate">{{ job.data?.title || name }}</span>
      </router-link>
      <h1 class="mt-1 text-xl font-semibold text-carbon">Log an expense</h1>
    </div>

    <!-- The float is the only number worth carrying on this screen: it is the
         answer to "can I still pay for this out of what I'm holding?" -->
    <div class="aura-card p-4">
      <div class="aura-eyebrow">Your float</div>
      <template v-if="held">
        <div class="mt-1 flex items-baseline gap-1.5">
          <MoneyValue :amount="floatMagnitude" size="lg" :tone="floatTone" />
          <span
            class="aura-num text-base"
            :class="floatTone === 'accent' ? 'text-accent' : 'text-faint'"
          >
            ₫
          </span>
        </div>
        <p class="mt-0.5 text-sm text-muted">{{ floatCaption }}</p>
      </template>
      <p v-else class="mt-1 text-sm text-muted">
        No advance on this job yet - what you log comes back to you.
      </p>
    </div>

    <!-- The entry card. Amount first and largest: it is the only field that
         is always filled, and the thumb lands on it before reading. -->
    <div class="aura-card space-y-4 p-4">
      <div>
        <label for="expense-amount" class="aura-eyebrow">Amount</label>
        <div
          class="mt-1.5 flex items-center gap-2 rounded-[10px] border border-hairline bg-paper px-3 py-3 transition-colors focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/20"
        >
          <VndInput
            id="expense-amount"
            ref="amountInput"
            v-model="amount"
            placeholder="0"
            class="aura-num w-full min-w-0 border-0 bg-transparent p-0 text-right text-3xl font-medium text-carbon placeholder:text-faint focus:border-0 focus:outline-none focus:ring-0"
            @enter="save"
          />
          <span class="shrink-0 text-xl text-faint">₫</span>
        </div>
      </div>

      <div>
        <span class="aura-eyebrow">Category</span>
        <div class="mt-1.5 flex flex-wrap gap-2">
          <button
            v-for="title in categories.data || []"
            :key="title"
            type="button"
            class="rounded-pill border px-3.5 py-2 text-sm transition-colors"
            :class="
              category === title
                ? 'border-carbon bg-carbon text-white'
                : 'border-hairline bg-paper text-carbon-soft hover:border-accent/40 hover:text-accent-ink'
            "
            @click="category = category === title ? '' : title"
          >
            {{ title }}
          </button>
          <p v-if="!(categories.data || []).length" class="text-sm text-faint">
            This job was quoted with no packages - everything lands uncategorised.
          </p>
        </div>
      </div>

      <div>
        <label for="expense-note" class="aura-eyebrow">Note</label>
        <input
          id="expense-note"
          v-model="description"
          placeholder="What was it for? (optional)"
          class="mt-1.5 w-full rounded-[10px] border border-hairline bg-paper px-3 py-3 text-sm text-carbon placeholder:text-faint focus:border-accent focus:ring-2 focus:ring-accent/20"
        />
      </div>

      <div>
        <span class="aura-eyebrow">Receipt</span>
        <FileUploader
          class="mt-1.5"
          file-types="image/*"
          :upload-args="{ private: true, optimize: true, max_width: 1600 }"
          @success="onPhoto"
        >
          <template #default="{ uploading, progress, openFileSelector }">
            <button
              type="button"
              :disabled="uploading"
              class="flex w-full items-center justify-center gap-2 rounded-[10px] border border-dashed border-hairline py-5 text-sm text-muted transition-colors hover:border-accent hover:text-accent disabled:opacity-60"
              @click="openFileSelector"
            >
              <FeatherIcon name="camera" class="h-4 w-4 shrink-0" />
              {{
                uploading
                  ? `Uploading ${progress}%`
                  : photo
                    ? "Replace receipt photo"
                    : "Attach receipt photo"
              }}
            </button>
          </template>
        </FileUploader>
        <div
          v-if="photo"
          class="mt-2 flex items-center gap-3 rounded-[10px] border border-hairline bg-canvas p-2"
        >
          <img
            :src="photo"
            alt="receipt"
            class="h-12 w-12 shrink-0 rounded-[8px] object-cover"
          />
          <span class="min-w-0 truncate text-xs text-muted">Receipt attached</span>
          <button
            type="button"
            class="ml-auto shrink-0 rounded-[8px] px-2 py-1.5 text-xs text-muted hover:text-accent"
            @click="photo = ''"
          >
            Remove
          </button>
        </div>
      </div>
    </div>

    <!-- Full width, thumb height, and dead until there is an amount. -->
    <div class="space-y-2">
      <button
        type="button"
        class="w-full rounded-[10px] bg-accent py-4 text-base font-semibold text-white shadow-card transition-colors hover:bg-accent-ink disabled:cursor-not-allowed disabled:bg-hairline disabled:text-faint disabled:shadow-none"
        :disabled="!parsed || expense.loading"
        @click="save"
      >
        {{
          expense.loading
            ? "Saving..."
            : `Log ${parsed ? vnd(parsed) + " ₫" : "expense"}`
        }}
      </button>
      <ErrorMessage :message="error" />
    </div>

    <div v-if="logged.length" class="aura-card p-4">
      <div class="aura-eyebrow">Logged just now</div>
      <ul class="mt-2 divide-y divide-hairline">
        <li
          v-for="row in logged"
          :key="row.name"
          class="flex items-center gap-2 py-2.5 first:pt-0"
        >
          <FeatherIcon name="check" class="h-3.5 w-3.5 shrink-0 text-ok" />
          <span class="min-w-0 truncate text-sm text-carbon">
            {{ row.category || "Uncategorised" }}
          </span>
          <MoneyValue :amount="row.amount" class="ml-auto shrink-0" />
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from "vue"
import { useRoute } from "vue-router"
import {
  ErrorMessage,
  FeatherIcon,
  FileUploader,
  createResource,
} from "frappe-ui"
import MoneyValue from "../components/MoneyValue.vue"
import VndInput from "../components/VndInput.vue"
import { frappeErrorMessage } from "../utils/frappeError"
import { parseVnd, vnd } from "../utils/money"

const route = useRoute()
const name = route.params.name

const amount = ref("")
const category = ref("")
const description = ref("")
const photo = ref("")
const error = ref("")
const logged = ref([])
const held = ref(null)
const amountInput = ref(null)

const parsed = computed(() => parseVnd(amount.value))

const job = createResource({
  url: "frappe.client.get_value",
  makeParams: () => ({
    doctype: "Job",
    filters: { name },
    fieldname: "title",
  }),
  auto: true,
})

const categories = createResource({
  url: "auraos.api.job_expense_categories",
  makeParams: () => ({ job: name }),
  auto: true,
  onError(err) {
    error.value = frappeErrorMessage(err)
  },
})

const money = createResource({
  url: "auraos.api.job_money",
  makeParams: () => ({ job: name }),
  auto: true,
  onSuccess(data) {
    held.value =
      (data.floats || []).find((row) => row.holder === currentUser) || null
  },
})

const currentUser = decodeURIComponent(
  document.cookie
    .split("; ")
    .find((c) => c.startsWith("user_id="))
    ?.split("=")[1] || ""
)

// Three states, one card: advance remaining, own money spent, no advance.
// The sign lives in the caption so the number itself always reads positive.
const floatMagnitude = computed(() => {
  if (!held.value) return null
  return held.value.amount >= 0 ? held.value.amount : -held.value.amount
})

const floatCaption = computed(() => {
  if (!held.value) return ""
  return held.value.amount >= 0
    ? "left of your advance"
    : "of your own money, so far"
})

const floatTone = computed(() => (held.value?.amount >= 0 ? "ink" : "accent"))

const expense = createResource({
  url: "auraos.api.log_job_expense",
  onSuccess(result) {
    logged.value.unshift(result)
    held.value = result.float
    amount.value = ""
    description.value = ""
    photo.value = ""
    error.value = ""
    amountInput.value?.focus()
  },
  onError(err) {
    error.value = frappeErrorMessage(err)
  },
})

function onPhoto(file) {
  photo.value = file.file_url
}

function save() {
  if (!parsed.value) return
  expense.submit({
    job: name,
    amount: parsed.value,
    category: category.value || null,
    description: description.value || null,
    photo: photo.value || null,
  })
}

onMounted(() => amountInput.value?.focus())
</script>

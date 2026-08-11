<template>
  <div v-if="authorized" class="mx-auto max-w-4xl px-4 py-6">
    <div class="mb-5 flex flex-wrap items-center gap-3">
      <div>
        <h1 class="text-lg font-semibold text-gray-900">Overhead & break-even</h1>
        <p class="text-sm text-gray-500">
          What booked work contributes against this month’s overhead.
        </p>
      </div>
      <input
        v-model="selectedMonth"
        type="month"
        class="ml-auto rounded border-gray-200 px-2 py-1 text-sm"
      />
    </div>

    <div class="grid gap-3 sm:grid-cols-3">
      <div class="rounded-lg border bg-white p-4">
        <div class="text-xs uppercase tracking-wide text-gray-500">Overhead</div>
        <div class="mt-1 text-xl font-semibold tabular-nums">
          {{ vnd(dashboard.data?.overhead, "0") }} ₫
        </div>
      </div>
      <div class="rounded-lg border bg-white p-4">
        <div class="text-xs uppercase tracking-wide text-gray-500">Booked margin</div>
        <div class="mt-1 text-xl font-semibold tabular-nums">
          {{ vnd(dashboard.data?.booked_margin, "0") }} ₫
        </div>
        <div class="mt-1 text-xs text-gray-500">
          {{ dashboard.data?.job_count || 0 }} booked job{{ dashboard.data?.job_count === 1 ? "" : "s" }}
        </div>
      </div>
      <div
        class="rounded-lg border p-4"
        :class="position.classes"
      >
        <div class="text-xs uppercase tracking-wide text-gray-500">
          {{ position.label }}
        </div>
        <div class="mt-1 text-xl font-semibold tabular-nums">
          {{ vnd(position.amount, "0") }} ₫
        </div>
      </div>
    </div>

    <div class="mt-6 rounded-lg border bg-white">
      <div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
        <h2 class="font-medium text-gray-900">Monthly overhead</h2>
        <Button class="ml-auto" variant="subtle" @click="addRecurring">
          Add recurring
        </Button>
        <Button variant="subtle" @click="addOneOff">Add one-off</Button>
      </div>

      <div v-if="!items.length" class="px-4 py-8 text-center text-sm text-gray-400">
        No overhead entered for this month.
      </div>
      <div
        v-for="(item, index) in items"
        :key="index"
        class="grid gap-2 border-b px-4 py-3 sm:grid-cols-[7rem_9rem_1fr_9rem_auto]"
      >
        <select v-model="item.kind" class="rounded border-gray-200 text-sm">
          <option>Recurring</option>
          <option>One-off</option>
        </select>
        <select v-model="item.category" class="rounded border-gray-200 text-sm">
          <option v-for="category in CATEGORIES" :key="category">{{ category }}</option>
        </select>
        <input
          v-model="item.description"
          class="rounded border-gray-200 text-sm"
          placeholder="Description (optional)"
        />
        <input
          v-model.number="item.amount"
          type="number"
          min="0"
          step="1000"
          class="rounded border-gray-200 text-right text-sm tabular-nums"
          placeholder="Amount"
        />
        <Button variant="ghost" @click="items.splice(index, 1)">Remove</Button>
      </div>

      <div class="flex items-center gap-3 px-4 py-3">
        <span class="text-sm font-medium text-gray-700">
          Total: {{ vnd(total, "0") }} ₫
        </span>
        <Button class="ml-auto" variant="solid" :loading="saver.loading" @click="save">
          Save month
        </Button>
        <span v-if="saved" class="text-xs text-green-700">Saved.</span>
      </div>
    </div>
    <ErrorMessage class="mt-2" :message="error" />
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue"
import { useRouter } from "vue-router"
import { Button, ErrorMessage, createResource } from "frappe-ui"
import { frappeErrorMessage } from "../utils/frappeError"
import { vnd } from "../utils/money"

const CATEGORIES = ["Rent", "Salaries", "Utilities", "Subscriptions", "Other"]
const now = new Date()
const selectedMonth = ref(
  `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`
)
const items = ref([])
const authorized = ref(false)
const saved = ref(false)
const error = ref("")
const router = useRouter()

const monthDate = computed(() => `${selectedMonth.value}-01`)
const total = computed(() =>
  items.value.reduce((sum, item) => sum + Number(item.amount || 0), 0)
)
const position = computed(() => {
  const contribution = dashboard.data?.contribution || 0
  if (contribution < 0) {
    return {
      label: "Shortfall",
      amount: -contribution,
      classes: "border-red-200 bg-red-50",
    }
  }
  if (contribution > 0) {
    return {
      label: "Surplus",
      amount: contribution,
      classes: "border-green-200 bg-green-50",
    }
  }
  return {
    label: "Break-even",
    amount: 0,
    classes: "border-gray-200 bg-gray-50",
  }
})

function deny() {
  authorized.value = false
  router.replace("/deals")
}

const month = createResource({
  url: "auraos.api.get_overhead_month",
  onSuccess(value) {
    authorized.value = true
    items.value = value.items || []
    error.value = ""
  },
  onError: deny,
})

const dashboard = createResource({
  url: "auraos.api.break_even_dashboard",
  onError: deny,
})

function load() {
  saved.value = false
  month.fetch({ month: monthDate.value })
  dashboard.fetch({ month: monthDate.value })
}

watch(selectedMonth, load, { immediate: true })

function addRecurring() {
  items.value.push({ kind: "Recurring", category: "Rent", description: "", amount: 0 })
}

function addOneOff() {
  items.value.push({ kind: "One-off", category: "Other", description: "", amount: 0 })
}

const saver = createResource({
  url: "auraos.api.save_overhead_month",
  onSuccess(value) {
    items.value = value.items
    saved.value = true
    error.value = ""
    dashboard.fetch({ month: monthDate.value })
  },
  onError(err) {
    saved.value = false
    error.value = frappeErrorMessage(err)
  },
})

function save() {
  saved.value = false
  saver.submit({ month: monthDate.value, items: items.value })
}
</script>

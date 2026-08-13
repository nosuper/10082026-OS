<template>
  <div class="mx-auto max-w-5xl px-4 py-6">
    <!-- The numbers the founder opens the app for, before any clicking
         (founder, A4 round 4: a dashboard as the default screen). -->
    <div class="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
      <router-link to="/deals" class="rounded-lg border bg-white p-3 hover:border-gray-300">
        <div class="text-xs text-gray-500">Pipeline (open deals)</div>
        <div class="mt-0.5 text-lg font-semibold tabular-nums text-gray-900">
          {{ vndShort(pipelineTotal) || "0" }}
        </div>
        <div class="mt-0.5 text-xs text-gray-500">{{ openDeals.length }} deals</div>
      </router-link>
      <router-link to="/jobs" class="rounded-lg border bg-white p-3 hover:border-gray-300">
        <div class="text-xs text-gray-500">In production</div>
        <div class="mt-0.5 text-lg font-semibold tabular-nums text-gray-900">
          {{ vndShort(productionTotal) || "0" }}
        </div>
        <div class="mt-0.5 text-xs text-gray-500">{{ openJobs.length }} jobs</div>
      </router-link>
      <router-link
        to="/jobs"
        class="rounded-lg border bg-white p-3 hover:border-gray-300"
        :class="overdue.length ? 'border-red-200 bg-red-50' : ''"
      >
        <div class="text-xs" :class="overdue.length ? 'text-red-700' : 'text-gray-500'">
          Overdue payments
        </div>
        <div
          class="mt-0.5 text-lg font-semibold tabular-nums"
          :class="overdue.length ? 'text-red-700' : 'text-gray-900'"
        >
          {{ overdue.length ? vndShort(overdueTotal) : "0" }}
        </div>
        <div class="mt-0.5 text-xs" :class="overdue.length ? 'text-red-700' : 'text-gray-500'">
          {{ overdue.length }} milestone{{ overdue.length === 1 ? "" : "s" }}
        </div>
      </router-link>
      <router-link
        to="/deals"
        class="rounded-lg border bg-white p-3 hover:border-gray-300"
        :class="silent.length ? 'border-amber-200 bg-amber-50' : ''"
      >
        <div class="text-xs" :class="silent.length ? 'text-amber-800' : 'text-gray-500'">
          Quotes gone quiet
        </div>
        <div
          class="mt-0.5 text-lg font-semibold tabular-nums"
          :class="silent.length ? 'text-amber-800' : 'text-gray-900'"
        >
          {{ silent.length }}
        </div>
        <div class="mt-0.5 text-xs" :class="silent.length ? 'text-amber-800' : 'text-gray-500'">
          past {{ silenceDays || "—" }} days
        </div>
      </router-link>
    </div>

    <div class="grid gap-4 lg:grid-cols-2">
      <!-- Quick expense: the single most frequent entry, one card away
           from the home screen. -->
      <div class="rounded-lg border bg-white p-4">
        <h2 class="mb-2 text-sm font-semibold text-gray-800">Quick expense</h2>
        <div class="grid gap-2">
          <select
            v-model="expenseJob"
            class="w-full rounded border-gray-200 py-2 pl-2 pr-8 text-sm"
          >
            <option value="">Which job…</option>
            <option v-for="job in openJobs" :key="job.name" :value="job.name">
              {{ job.title }} · {{ job.name }}
            </option>
          </select>
          <VndInput
            v-model="expenseAmount"
            placeholder="Amount"
            class="w-full rounded border-gray-200 px-3 py-2.5 text-right text-xl tabular-nums"
          />
          <select
            v-model="expenseCategory"
            class="w-full rounded border-gray-200 py-2 pl-2 pr-8 text-sm"
            :disabled="!expenseJob"
          >
            <option value="">Uncategorised</option>
            <option v-for="title in categories.data || []" :key="title" :value="title">
              {{ title }}
            </option>
          </select>
          <input
            v-model="expenseNote"
            placeholder="What was it for? (optional)"
            class="w-full rounded border-gray-200 px-2 py-2 text-sm"
          />
          <Button
            variant="solid"
            :disabled="!expenseJob || !parseVnd(expenseAmount)"
            :loading="expense.loading"
            @click="logExpense"
          >
            Log {{ parseVnd(expenseAmount) ? vnd(parseVnd(expenseAmount)) : "expense" }}
          </Button>
          <p v-if="expenseLogged" class="text-xs text-blue-700">{{ expenseLogged }}</p>
          <ErrorMessage :message="expenseError" />
        </div>
      </div>

      <!-- What needs a human today. -->
      <div class="rounded-lg border bg-white p-4">
        <h2 class="mb-2 text-sm font-semibold text-gray-800">Needs attention</h2>
        <ul v-if="attention.length" class="space-y-2 text-sm">
          <li
            v-for="item in attention"
            :key="item.key"
            class="flex flex-wrap items-baseline gap-2"
          >
            <FeatherIcon
              :name="item.icon"
              class="h-3.5 w-3.5 shrink-0"
              :class="item.tone"
            />
            <router-link :to="item.to" class="font-medium text-gray-900 hover:underline">
              {{ item.title }}
            </router-link>
            <span class="text-gray-600">{{ item.detail }}</span>
            <span v-if="item.amount" class="ml-auto tabular-nums text-gray-800">
              {{ vnd(item.amount) }}
            </span>
          </li>
        </ul>
        <p v-else class="py-2 text-sm text-gray-400">
          Nothing chasing you — the board is quiet.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue"
import {
  Button,
  ErrorMessage,
  FeatherIcon,
  createResource,
  createListResource,
} from "frappe-ui"
import VndInput from "../components/VndInput.vue"
import { frappeErrorMessage } from "../utils/frappeError"
import { parseVnd, vnd, vndShort } from "../utils/money"
import { overdueLabel } from "../data/milestones"

// -- the four headline numbers --

const deals = createListResource({
  doctype: "Deal",
  fields: ["name", "title", "stage", "estimated_budget"],
  pageLength: 500,
  auto: true,
})

const openDeals = computed(() =>
  (deals.data || []).filter((row) => row.stage !== "Won" && row.stage !== "Lost")
)

const pipelineTotal = computed(() =>
  openDeals.value.reduce((sum, row) => sum + (row.estimated_budget || 0), 0)
)

const jobs = createListResource({
  doctype: "Job",
  fields: ["name", "title", "stage", "quote_total"],
  orderBy: "modified desc",
  pageLength: 500,
  auto: true,
})

const openJobs = computed(() =>
  (jobs.data || []).filter((row) => row.stage !== "Complete")
)

const productionTotal = computed(() =>
  openJobs.value.reduce((sum, row) => sum + (row.quote_total || 0), 0)
)

const nudges = createResource({ url: "auraos.api.overdue_milestones", auto: true })
const overdue = computed(() => nudges.data?.milestones || [])
const overdueTotal = computed(() =>
  overdue.value.reduce((sum, row) => sum + (row.amount || 0), 0)
)

const silence = createResource({ url: "auraos.api.silent_quote_deals", auto: true })
const silent = computed(() => silence.data?.deals || [])
const silenceDays = computed(() => silence.data?.silence_days)

// One list, worst first: overdue money, then quotes gone quiet.
const attention = computed(() => [
  ...overdue.value.map((row) => ({
    key: `overdue-${row.name}`,
    icon: "alert-circle",
    tone: "text-red-600",
    to: `/jobs/${row.job}`,
    title: row.job_title || row.job,
    detail: `${row.title} · ${overdueLabel(row.days_overdue)}`,
    amount: row.amount,
  })),
  ...silent.value.map((row) => ({
    key: `silent-${row.name}`,
    icon: "clock",
    tone: "text-amber-600",
    to: `/deals`,
    title: row.title || row.name,
    detail: "quote sent, no reply",
    amount: null,
  })),
])

// -- quick expense --

const expenseJob = ref("")
const expenseAmount = ref("")
const expenseCategory = ref("")
const expenseNote = ref("")
const expenseError = ref("")
const expenseLogged = ref("")

const categories = createResource({ url: "auraos.api.job_expense_categories" })

watch(expenseJob, (job) => {
  expenseCategory.value = ""
  if (job) categories.submit({ job })
})

const expense = createResource({
  url: "auraos.api.log_job_expense",
  onSuccess() {
    expenseLogged.value = `Logged ${vnd(parseVnd(expenseAmount.value))} on ${expenseJob.value}.`
    expenseAmount.value = ""
    expenseNote.value = ""
    expenseError.value = ""
  },
  onError(err) {
    expenseLogged.value = ""
    expenseError.value = frappeErrorMessage(err)
  },
})

function logExpense() {
  if (!expenseJob.value || !parseVnd(expenseAmount.value)) return
  expenseLogged.value = ""
  expense.submit({
    job: expenseJob.value,
    amount: parseVnd(expenseAmount.value),
    category: expenseCategory.value || null,
    description: expenseNote.value || null,
  })
}
</script>

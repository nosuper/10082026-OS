<template>
  <div class="space-y-4">
    <!-- Page head: what the founder opens the app for, in words, before numbers. -->
    <div class="flex flex-wrap items-end gap-x-3 gap-y-1">
      <h1 class="text-xl font-semibold text-ink">Today</h1>
      <p class="text-sm text-muted">
        {{ openDeals.length }} open deal{{ openDeals.length === 1 ? "" : "s" }} ·
        {{ openJobs.length }} in production
        <template v-if="attention.length">
          · <span class="text-accent">{{ attention.length }} need{{ attention.length === 1 ? "s" : "" }} a human</span>
        </template>
      </p>
    </div>

    <!-- Row 1: the four headline numbers. Attention states outline in ember. -->
    <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <BentoCard title="Pipeline · open deals" to="/deals">
        <MoneyValue :amount="pipelineTotal" short size="lg" />
        <template #footer>
          <span class="text-xs text-faint">{{ openDeals.length }} deals</span>
        </template>
      </BentoCard>

      <BentoCard title="In production" to="/jobs">
        <MoneyValue :amount="productionTotal" short size="lg" />
        <template #footer>
          <span class="text-xs text-faint">{{ openJobs.length }} jobs</span>
        </template>
      </BentoCard>

      <BentoCard title="Overdue payments" to="/jobs" :attention="overdue.length > 0">
        <MoneyValue
          :amount="overdue.length ? overdueTotal : 0"
          short
          size="lg"
          :tone="overdue.length ? 'accent' : 'ink'"
        />
        <template #footer>
          <span class="text-xs" :class="overdue.length ? 'text-accent' : 'text-faint'">
            {{ overdue.length }} milestone{{ overdue.length === 1 ? "" : "s" }}
          </span>
        </template>
      </BentoCard>

      <BentoCard title="Quotes gone quiet" to="/deals" :attention="silent.length > 0">
        <span class="aura-num text-2xl font-medium" :class="silent.length ? 'text-accent' : 'text-ink'">
          {{ silent.length }}
        </span>
        <template #footer>
          <span class="text-xs" :class="silent.length ? 'text-accent' : 'text-faint'">
            past {{ silenceDays || "—" }} days
          </span>
        </template>
      </BentoCard>
    </div>

    <!-- Row 2: what needs a human, next to the founder-only margin card. -->
    <div class="grid gap-3 lg:grid-cols-3">
      <BentoCard
        class="lg:col-span-2"
        title="Attention required"
        :subtitle="attention.length ? 'Worst first: money owed, then silence.' : ''"
      >
        <ul v-if="attention.length" class="divide-y divide-hairline">
          <li v-for="item in attention" :key="item.key" class="flex items-baseline gap-2 py-2 first:pt-0">
            <StatusPill :label="item.kind" :tone="item.tone" />
            <router-link :to="item.to" class="min-w-0 truncate text-sm font-medium text-ink hover:text-accent">
              {{ item.title }}
            </router-link>
            <span class="min-w-0 truncate text-xs text-muted">{{ item.detail }}</span>
            <MoneyValue v-if="item.amount" :amount="item.amount" class="ml-auto shrink-0" />
          </li>
        </ul>
        <EmptyState
          v-else
          icon="check-circle"
          title="Nothing chasing you."
          detail="No overdue milestones, no silent quotes."
        />
      </BentoCard>

      <!-- Founder-only: server-gated data, inverted surface so it never reads
           as producer-safe. Absent for producers because the call fails. -->
      <BentoCard v-if="isFounder" founder title="Margin · open pipeline">
        <div class="flex items-baseline gap-2">
          <span class="aura-num text-3xl font-medium text-white">
            {{ marginFloor !== null ? marginFloor + "%" : "—" }}
          </span>
          <span class="text-xs text-white/50">floor</span>
        </div>
        <p class="mt-2 text-xs leading-relaxed text-white/60">
          Quotes below the floor are blocked at publish, not at send. Pricing shows the
          cause per line.
        </p>
        <template #footer>
          <router-link to="/settings" class="text-xs text-white/70 hover:text-white">
            Adjust floor and defaults →
          </router-link>
        </template>
      </BentoCard>
    </div>

    <!-- Row 3: active production, full width. -->
    <DataTable
      title="Active production"
      :count="openJobs.length"
      :columns="jobColumns"
      :rows="openJobs"
      clickable
      empty-title="No jobs in production."
      @row-click="(row) => $router.push(`/jobs/${row.name}`)"
    >
      <template #cell-title="{ row }">
        <div class="min-w-0">
          <div class="truncate text-sm font-medium text-ink">{{ row.title || row.name }}</div>
          <div class="aura-num text-[11px] text-faint">{{ row.name }}</div>
        </div>
      </template>
      <template #cell-stage="{ row }">
        <StatusPill :label="row.stage" :tone="stageTone(row.stage)" />
      </template>
      <template #cell-quote_total="{ row }">
        <MoneyValue :amount="row.quote_total" />
      </template>
    </DataTable>

    <!-- Row 4: quick expense stays one card from home - the most frequent entry. -->
    <div class="grid gap-3 lg:grid-cols-3">
      <BentoCard title="Quick expense" subtitle="Logs against a job's float.">
        <div class="grid gap-2">
          <select
            v-model="expenseJob"
            class="w-full rounded-[10px] border border-hairline bg-surface py-2 pl-2 pr-8 text-sm text-ink"
          >
            <option value="">Which job…</option>
            <option v-for="job in openJobs" :key="job.name" :value="job.name">
              {{ job.title }} · {{ job.name }}
            </option>
          </select>
          <VndInput
            v-model="expenseAmount"
            placeholder="Amount"
            class="aura-num w-full rounded-[10px] border border-hairline px-3 py-2.5 text-right text-xl"
          />
          <select
            v-model="expenseCategory"
            :disabled="!expenseJob"
            class="w-full rounded-[10px] border border-hairline bg-surface py-2 pl-2 pr-8 text-sm text-ink disabled:text-faint"
          >
            <option value="">Uncategorised</option>
            <option v-for="title in categories.data || []" :key="title" :value="title">
              {{ title }}
            </option>
          </select>
          <input
            v-model="expenseNote"
            placeholder="What was it for? (optional)"
            class="w-full rounded-[10px] border border-hairline px-2 py-2 text-sm"
          />
          <Button
            variant="solid"
            :disabled="!expenseJob || !parseVnd(expenseAmount)"
            :loading="expense.loading"
            @click="logExpense"
          >
            Log {{ parseVnd(expenseAmount) ? vnd(parseVnd(expenseAmount)) : "expense" }}
          </Button>
          <p v-if="expenseLogged" class="text-xs text-ok">{{ expenseLogged }}</p>
          <ErrorMessage :message="expenseError" />
        </div>
      </BentoCard>

      <BentoCard class="lg:col-span-2" title="Cash flow · next milestones">
        <ul v-if="upcoming.length" class="divide-y divide-hairline">
          <li v-for="row in upcoming" :key="row.name" class="flex items-baseline gap-2 py-2 first:pt-0">
            <router-link :to="`/jobs/${row.job}`" class="min-w-0 truncate text-sm font-medium text-ink hover:text-accent">
              {{ row.job_title || row.job }}
            </router-link>
            <span class="min-w-0 truncate text-xs text-muted">{{ row.title }}</span>
            <StatusPill :label="overdueLabel(row.days_overdue)" tone="accent" class="shrink-0" />
            <MoneyValue :amount="row.amount" class="ml-auto shrink-0" />
          </li>
        </ul>
        <EmptyState v-else title="No milestone is overdue." detail="Collections are current." />
      </BentoCard>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue"
import { Button, ErrorMessage, createResource, createListResource } from "frappe-ui"
import BentoCard from "../components/BentoCard.vue"
import DataTable from "../components/DataTable.vue"
import StatusPill from "../components/StatusPill.vue"
import MoneyValue from "../components/MoneyValue.vue"
import EmptyState from "../components/EmptyState.vue"
import VndInput from "../components/VndInput.vue"
import { frappeErrorMessage } from "../utils/frappeError"
import { parseVnd, vnd } from "../utils/money"
import { overdueLabel } from "../data/milestones"

// -- same server calls as before; only the presentation is rebuilt --

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

const openJobs = computed(() => (jobs.data || []).filter((row) => row.stage !== "Complete"))

const productionTotal = computed(() =>
  openJobs.value.reduce((sum, row) => sum + (row.quote_total || 0), 0)
)

const jobColumns = [
  { key: "title", label: "Job" },
  { key: "stage", label: "Stage", width: "180px" },
  { key: "quote_total", label: "Quoted", align: "right", width: "160px" },
]

// Stage tone: the current-attention stages read in ember, settled ones quiet.
function stageTone(stage) {
  if (!stage) return "neutral"
  if (stage === "Complete") return "ok"
  if (["Delivery", "Post", "Hậu kỳ", "Bàn giao"].includes(stage)) return "accent"
  return "neutral"
}

const nudges = createResource({ url: "auraos.api.overdue_milestones", auto: true })
const overdue = computed(() => nudges.data?.milestones || [])
const overdueTotal = computed(() => overdue.value.reduce((sum, row) => sum + (row.amount || 0), 0))
const upcoming = computed(() => overdue.value.slice(0, 6))

const silence = createResource({ url: "auraos.api.silent_quote_deals", auto: true })
const silent = computed(() => silence.data?.deals || [])
const silenceDays = computed(() => silence.data?.silence_days)

// Founder gate: the same probe App.vue uses. Margin data stays server-gated.
const isFounder = ref(false)
const marginFloor = ref(null)
createResource({
  url: "auraos.api.get_margin_floor",
  auto: true,
  onSuccess(data) {
    isFounder.value = true
    const value = typeof data === "object" ? data?.margin_floor ?? data?.floor : data
    marginFloor.value = Number.isFinite(Number(value)) ? Number(value) : null
  },
  onError() {},
})

// One list, worst first: overdue money, then quotes gone quiet.
const attention = computed(() => [
  ...overdue.value.map((row) => ({
    key: `overdue-${row.name}`,
    kind: "Overdue",
    tone: "accent",
    to: `/jobs/${row.job}`,
    title: row.job_title || row.job,
    detail: `${row.title} · ${overdueLabel(row.days_overdue)}`,
    amount: row.amount,
  })),
  ...silent.value.map((row) => ({
    key: `silent-${row.name}`,
    kind: "Silent",
    tone: "warn",
    to: "/deals",
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

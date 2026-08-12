<template>
  <div class="px-4 py-6">
    <div class="mb-4 flex flex-wrap items-center gap-2">
      <h1 class="text-lg font-semibold text-gray-900">Jobs</h1>
      <span class="text-sm tabular-nums text-gray-400">
        {{ filteredJobs.length }}
      </span>
      <div class="relative ml-2">
        <FeatherIcon
          name="search"
          class="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400"
        />
        <input
          v-model.trim="query"
          type="text"
          placeholder="Search jobs"
          class="w-56 rounded-md border-gray-300 py-1.5 pl-8 text-sm placeholder-gray-500 focus:border-gray-500 focus:ring-0"
        />
      </div>
      <span class="ml-auto text-sm text-gray-500">
        Won deals in production — new jobs are created from the deal board.
      </span>
    </div>

    <!-- Money owed past the company's payment terms. Unpaid milestones
         should chase the founder, not the reverse (spec #2, story 39);
         this strip carries the nudge until T12 builds the dashboard. -->
    <div
      v-if="overdue.length"
      class="mb-4 rounded-lg border border-red-200 bg-red-50 p-3"
    >
      <div class="mb-1 flex flex-wrap items-baseline gap-2">
        <span class="inline-flex items-center gap-1.5 text-sm font-semibold text-red-900">
          <FeatherIcon name="alert-circle" class="h-4 w-4" />
          {{ vnd(overdueTotal) }} ₫ uncollected
        </span>
        <span class="text-xs text-red-800">
          {{ overdue.length }} milestone{{ overdue.length > 1 ? "s" : "" }}
          past the {{ nudges.data?.payment_terms_days }}-day payment terms
        </span>
      </div>
      <ul class="space-y-0.5 text-sm">
        <li
          v-for="row in overdue"
          :key="row.name"
          class="flex flex-wrap items-baseline gap-2"
        >
          <router-link
            :to="`/jobs/${row.job}`"
            class="font-medium text-red-900 hover:underline"
          >
            {{ row.job_title || row.job }}
          </router-link>
          <span class="text-red-800">{{ row.title }}</span>
          <span class="tabular-nums text-red-900">{{ vnd(row.amount) }} ₫</span>
          <span class="text-xs text-red-700">
            {{ overdueLabel(row.days_overdue) }} · {{ row.status }}
          </span>
        </li>
      </ul>
    </div>

    <div class="flex gap-3 overflow-x-auto pb-4">
      <div
        v-for="stage in STAGES"
        :key="stage"
        class="flex w-72 shrink-0 flex-col rounded-lg transition-colors"
        :class="
          dragOverStage === stage
            ? 'bg-blue-50 ring-2 ring-inset ring-blue-300'
            : 'bg-gray-100'
        "
        @dragover.prevent="dragOverStage = stage"
        @dragleave="onDragLeave(stage, $event)"
        @drop="onDrop(stage)"
      >
        <div class="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-800">
          <span class="h-2 w-2 shrink-0 rounded-full" :class="jobStageDot(stage)"></span>
          {{ stage }}
          <span class="text-xs font-normal text-gray-500">
            {{ jobsByStage[stage]?.length || 0 }}
          </span>
          <span
            v-if="stageTotals[stage]"
            class="ml-auto text-xs font-medium tabular-nums text-gray-600"
            :title="`${vnd(stageTotals[stage])} ₫ quoted in ${stage}`"
          >
            {{ vndShort(stageTotals[stage]) }}
          </span>
        </div>
        <div class="flex min-h-24 flex-1 flex-col gap-2 px-2 pb-2">
          <div
            v-for="job in jobsByStage[stage]"
            :key="job.name"
            class="cursor-grab rounded-md border bg-white p-3 shadow-sm transition-shadow hover:border-gray-300 hover:shadow"
            :class="dragged === job ? 'opacity-50' : ''"
            draggable="true"
            @dragstart="dragged = job"
            @dragend="((dragged = null), (dragOverStage = null))"
            @click="open(job)"
          >
            <div class="flex items-baseline gap-2">
              <span class="min-w-0 flex-1 truncate text-sm font-medium text-gray-900">
                {{ job.title }}
              </span>
              <span class="shrink-0 text-xs tabular-nums text-gray-400">
                {{ job.name }}
              </span>
            </div>
            <div v-if="job.company" class="mt-0.5 truncate text-xs text-gray-500">
              {{ companyNames[job.company] || job.company }}
            </div>
            <div v-if="job.quote_total" class="mt-2 text-sm font-medium tabular-nums text-gray-800">
              {{ vnd(job.quote_total) }}
            </div>
            <div class="mt-2 flex flex-wrap items-center gap-1.5">
              <span
                v-if="job.change_order_due"
                class="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-800"
                title="Revision rounds past the included ones — chargeable"
              >
                <FeatherIcon name="alert-triangle" class="h-3 w-3" />
                Change order · {{ job.revision_rounds }} rounds
              </span>
              <span
                v-else-if="job.revision_rounds"
                class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700"
              >
                {{ job.revision_rounds }} revision{{
                  job.revision_rounds > 1 ? "s" : ""
                }}
              </span>
              <span
                v-if="!job.files_location"
                class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500"
                title="No shared folder recorded yet"
              >
                no files location
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <p v-if="!jobs.data?.length" class="py-8 text-center text-sm text-gray-400">
      No jobs yet — mark a deal Won on the deal board to create one.
    </p>

    <ErrorMessage class="mt-2" :message="moveError" />
  </div>
</template>

<script setup>
import { ref, computed } from "vue"
import { useRouter } from "vue-router"
import {
  ErrorMessage,
  FeatherIcon,
  createResource,
  createListResource,
} from "frappe-ui"
import { frappeErrorMessage } from "../utils/frappeError"
import { vnd, vndShort } from "../utils/money"
import { STAGES } from "../data/jobStages"
import { jobStageDot } from "../utils/stages"
import { overdueLabel } from "../data/milestones"

// Overdue money, oldest debt first — the server decides what counts as
// overdue, so the board and a future dashboard cannot disagree.
const nudges = createResource({
  url: "auraos.api.overdue_milestones",
  auto: true,
})

const overdue = computed(() => nudges.data?.milestones || [])

const overdueTotal = computed(() =>
  overdue.value.reduce((sum, row) => sum + (row.amount || 0), 0)
)

const jobs = createListResource({
  doctype: "Job",
  fields: [
    "name",
    "title",
    "stage",
    "company",
    "job_owner",
    "files_location",
    "revision_rounds",
    "change_order_due",
    "quote_total",
    "modified",
  ],
  orderBy: "modified desc",
  pageLength: 500,
  auto: true,
})

const companies = createListResource({
  doctype: "Party Company",
  fields: ["name", "company_name"],
  pageLength: 500,
  auto: true,
})

const companyNames = computed(() => {
  const map = {}
  for (const c of companies.data || []) map[c.name] = c.company_name
  return map
})

// -- search (shared toolbar pattern with the deals board) --

const query = ref("")

const filteredJobs = computed(() => {
  const needle = query.value.toLowerCase()
  if (!needle) return jobs.data || []
  return (jobs.data || []).filter((job) =>
    [job.title, companyNames.value[job.company] || job.company, job.name]
      .filter(Boolean)
      .some((text) => String(text).toLowerCase().includes(needle))
  )
})

const jobsByStage = computed(() => {
  const map = {}
  for (const job of filteredJobs.value) {
    ;(map[job.stage] ||= []).push(job)
  }
  return map
})

// Money in production per column — quoted totals, the board's scale.
const stageTotals = computed(() => {
  const totals = {}
  for (const job of filteredJobs.value) {
    if (!job.quote_total) continue
    totals[job.stage] = (totals[job.stage] || 0) + job.quote_total
  }
  return totals
})

// -- drag & drop between stages (both roles may move a job) --

const dragged = ref(null)
const dragOverStage = ref(null)
const moveError = ref("")

function onDragLeave(stage, event) {
  if (dragOverStage.value !== stage) return
  if (event.relatedTarget && event.currentTarget.contains(event.relatedTarget)) {
    return
  }
  dragOverStage.value = null
}

const setStage = createResource({
  url: "frappe.client.set_value",
  onSuccess() {
    moveError.value = ""
    jobs.reload()
  },
  onError(err) {
    moveError.value = frappeErrorMessage(err)
    jobs.reload()
  },
})

function onDrop(stage) {
  const job = dragged.value
  dragged.value = null
  dragOverStage.value = null
  if (!job || job.stage === stage) return
  // Move the card before the server answers — a drop that waits out a
  // round-trip reads as lag (A1's verdict, applied here too).
  job.stage = stage
  setStage.submit({
    doctype: "Job",
    name: job.name,
    fieldname: { stage },
  })
}

const router = useRouter()

function open(job) {
  router.push(`/jobs/${job.name}`)
}
</script>

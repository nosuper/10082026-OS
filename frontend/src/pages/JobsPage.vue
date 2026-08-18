<template>
  <div class="space-y-4">
    <!-- Page head: the board's scale in words before the columns. No "New job"
         action - a job exists because a deal was won, never because a button
         was pressed. -->
    <div class="flex flex-wrap items-end gap-x-3 gap-y-2">
      <div class="min-w-0">
        <h1 class="text-xl font-semibold text-carbon">Jobs</h1>
        <p class="mt-0.5 text-sm text-muted">
          {{ filteredJobs.length }} job{{ filteredJobs.length === 1 ? "" : "s" }}
          <template v-if="boardTotal">
            · <span class="tabular-nums">{{ vndShort(boardTotal) }} ₫</span> in production
          </template>
        </p>
        <p class="mt-0.5 text-xs text-faint">
          Won deals in production - new jobs are created from the deal board.
        </p>
      </div>

      <div class="relative ml-auto">
        <FeatherIcon
          name="search"
          class="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint"
        />
        <input
          v-model.trim="query"
          type="text"
          placeholder="Search jobs"
          class="w-56 rounded-[10px] border border-hairline bg-paper py-2 pl-9 pr-3 text-sm text-carbon placeholder-faint focus:border-accent/40 focus:outline-none focus:ring-0"
        />
      </div>
    </div>

    <!-- Money owed past the company's payment terms. Unpaid milestones
         should chase the founder, not the reverse (spec #2, story 39);
         this strip carries the nudge until T12 builds the dashboard.
         It is the loudest thing on the page: the ember band is used here
         and nowhere else on the board. -->
    <section
      v-if="overdue.length"
      class="overflow-hidden rounded-card border border-accent/30 bg-paper shadow-card"
    >
      <div
        class="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-accent/20 bg-accent-soft px-4 py-3"
      >
        <FeatherIcon name="alert-circle" class="h-4 w-4 shrink-0 text-accent" />
        <div class="min-w-0">
          <div class="aura-eyebrow text-accent-ink">Uncollected</div>
          <div class="mt-0.5 flex items-baseline gap-1">
            <MoneyValue :amount="overdueTotal" size="lg" tone="accent" />
            <span class="text-sm text-accent">₫</span>
          </div>
        </div>
        <p class="text-xs text-accent-ink sm:ml-auto sm:text-right">
          {{ overdue.length }} milestone{{ overdue.length > 1 ? "s" : "" }}
          past the {{ nudges.data?.payment_terms_days }}-day payment terms
        </p>
      </div>

      <ul class="divide-y divide-hairline px-4">
        <li
          v-for="row in overdue"
          :key="row.name"
          class="flex flex-wrap items-baseline gap-x-2 gap-y-1 py-2"
        >
          <router-link
            :to="`/jobs/${row.job}`"
            class="min-w-0 truncate text-sm font-medium text-carbon hover:text-accent"
          >
            {{ row.job_title || row.job }}
          </router-link>
          <span class="min-w-0 truncate text-xs text-muted">{{ row.title }}</span>
          <StatusPill
            :label="overdueLabel(row.days_overdue)"
            tone="accent"
            class="shrink-0"
          />
          <span class="shrink-0 text-xs text-faint">{{ row.status }}</span>
          <MoneyValue :amount="row.amount" class="ml-auto shrink-0 font-medium" />
        </li>
      </ul>
    </section>

    <!-- The production flow, left to right. Columns are canvas, cards are
         paper - the only depth on the board. -->
    <div class="flex gap-3 overflow-x-auto pb-2">
      <div
        v-for="stage in STAGES"
        :key="stage"
        class="flex w-[272px] shrink-0 flex-col rounded-card border transition-colors"
        :class="
          dragOverStage === stage
            ? 'border-accent/40 bg-accent-soft'
            : 'border-hairline bg-canvas'
        "
        @dragover.prevent="dragOverStage = stage"
        @dragleave="onDragLeave(stage, $event)"
        @drop="onDrop(stage)"
      >
        <div class="flex items-center gap-2 border-b border-hairline px-3 py-2.5">
          <span class="h-1.5 w-1.5 shrink-0 rounded-pill" :class="jobStageDot(stage)"></span>
          <span class="truncate text-xs font-medium text-carbon">{{ stage }}</span>
          <span class="aura-num shrink-0 text-[11px] text-faint">
            {{ jobsByStage[stage]?.length || 0 }}
          </span>
          <!-- Column money is sans, not the mono ledger face: vndShort spells
               the unit in Vietnamese ("triệu", "tỷ") and the mono face has no
               diacritics to spell it with. -->
          <span
            v-if="stageTotals[stage]"
            class="ml-auto shrink-0 text-[11px] font-medium tabular-nums text-muted"
            :title="`${vnd(stageTotals[stage])} ₫ quoted in ${stage}`"
          >
            {{ vndShort(stageTotals[stage]) }}
          </span>
        </div>

        <div class="flex min-h-24 flex-1 flex-col gap-2 p-2">
          <div
            v-for="job in jobsByStage[stage]"
            :key="job.name"
            class="cursor-grab rounded-[10px] border border-hairline bg-paper p-3 shadow-card transition-colors hover:border-accent/40"
            :class="dragged === job ? 'opacity-50' : ''"
            draggable="true"
            @dragstart="dragged = job"
            @dragend="((dragged = null), (dragOverStage = null))"
            @click="open(job)"
          >
            <div class="flex items-start justify-between gap-2">
              <span class="min-w-0 flex-1 truncate text-sm font-medium leading-snug text-carbon">
                {{ job.title }}
              </span>
              <span class="aura-num shrink-0 text-[11px] text-faint">
                {{ job.name }}
              </span>
            </div>

            <div v-if="job.company" class="mt-1 truncate text-xs text-muted">
              {{ companyNames[job.company] || job.company }}
            </div>

            <div v-if="job.quote_total" class="mt-2.5">
              <MoneyValue :amount="job.quote_total" class="font-medium" />
            </div>

            <div
              v-if="job.change_order_due || job.revision_rounds || !job.files_location"
              class="mt-2 flex flex-wrap items-center gap-1 border-t border-hairline pt-2"
            >
              <StatusPill
                v-if="job.change_order_due"
                tone="warn"
                title="Revision rounds past the included ones - chargeable"
              >
                <FeatherIcon name="alert-triangle" class="mr-1 h-3 w-3" />
                Change order · {{ job.revision_rounds }} rounds
              </StatusPill>
              <StatusPill
                v-else-if="job.revision_rounds"
                tone="neutral"
                :label="`${job.revision_rounds} revision${job.revision_rounds > 1 ? 's' : ''}`"
              />
              <StatusPill
                v-if="!job.files_location"
                tone="neutral"
                label="no files location"
                title="No shared folder recorded yet"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="!jobs.data?.length" class="aura-card">
      <EmptyState
        icon="briefcase"
        title="No jobs yet - mark a deal Won on the deal board to create one."
      />
    </div>

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
import StatusPill from "../components/StatusPill.vue"
import MoneyValue from "../components/MoneyValue.vue"
import EmptyState from "../components/EmptyState.vue"
import { frappeErrorMessage } from "../utils/frappeError"
import { vnd, vndShort } from "../utils/money"
import { STAGES } from "../data/jobStages"
import { jobStageDot } from "../utils/stages"
import { overdueLabel } from "../data/milestones"

// Overdue money, oldest debt first - the server decides what counts as
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

// Money in production per column - quoted totals, the board's scale.
const stageTotals = computed(() => {
  const totals = {}
  for (const job of filteredJobs.value) {
    if (!job.quote_total) continue
    totals[job.stage] = (totals[job.stage] || 0) + job.quote_total
  }
  return totals
})

// The same figure across every visible column - the head's one number.
const boardTotal = computed(() =>
  filteredJobs.value.reduce((sum, job) => sum + (job.quote_total || 0), 0)
)

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
  // Move the card before the server answers - a drop that waits out a
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

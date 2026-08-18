<template>
  <div class="space-y-4">
    <!-- Page head: the job's identity, then the one control that moves it.
         The app shell's header is already sticky, so this reads as a title
         block, not a second bar. -->
    <div class="flex flex-wrap items-end gap-x-3 gap-y-1">
      <router-link to="/jobs" class="text-sm text-muted hover:text-accent">
        ← Jobs
      </router-link>
      <h1 class="text-xl font-semibold text-carbon">
        {{ doc?.title || name }}
      </h1>
      <span class="aura-num text-xs text-faint">{{ name }}</span>
      <span v-if="companyName" class="text-sm text-muted">
        · {{ companyName }}
      </span>
      <div v-if="doc" class="ml-auto flex items-center gap-2">
        <span
          class="h-1.5 w-1.5 rounded-pill"
          :class="stage === 'Complete' ? 'bg-ok' : 'bg-accent'"
        ></span>
        <select
          v-model="stage"
          class="rounded-[10px] border border-hairline bg-paper py-1.5 pl-2 pr-8 text-sm text-carbon focus:outline-none focus:ring-2 focus:ring-accent/30"
          @change="saveStage"
        >
          <option v-for="option in STAGES" :key="option" :value="option">
            {{ option }}
          </option>
        </select>
      </div>
    </div>

    <div v-if="job.loading" class="aura-card p-10 text-center text-sm text-muted">
      Loading…
    </div>

    <template v-else-if="doc">
      <!-- Production progress as a chip trail: where the job is, and one
           click to move it. -->
      <div class="aura-card flex flex-wrap items-center gap-1 p-2">
        <template v-for="(option, index) in STAGES" :key="option">
          <button
            class="rounded-[8px] border px-2.5 py-1 text-xs transition-colors"
            :class="stageChipClass(index)"
            :title="`Move to ${option}`"
            @click="setStageTo(option)"
          >
            {{ option }}
          </button>
          <FeatherIcon
            v-if="index < STAGES.length - 1"
            name="chevron-right"
            class="h-3 w-3 shrink-0 text-faint/60"
          />
        </template>
      </div>

      <!-- The job's money at a glance - collected against quoted is the
           number the founder chases (spec #2, story 39). -->
      <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <BentoCard title="Quoted">
          <MoneyValue :amount="doc.quote_total" short size="lg" />
        </BentoCard>

        <BentoCard title="Collected">
          <span class="aura-num text-2xl font-medium text-ok">
            {{ vndShort(collected) }}
          </span>
          <div class="mt-2 h-1.5 overflow-hidden rounded-pill bg-hairline">
            <div
              class="h-full rounded-pill bg-ok transition-all"
              :style="{ width: `${collectedPct}%` }"
            ></div>
          </div>
          <template #footer>
            <span class="text-xs text-faint">{{ collectedPct }}% of the quote</span>
          </template>
        </BentoCard>

        <BentoCard title="Uncollected" :attention="overdueCount > 0">
          <template v-if="overdueCount" #action>
            <StatusPill tone="accent" :label="`${overdueCount} overdue`" />
          </template>
          <MoneyValue
            :amount="uncollected"
            short
            size="lg"
            :tone="overdueCount ? 'accent' : 'ink'"
          />
        </BentoCard>

        <BentoCard title="Spent">
          <MoneyValue :amount="moneySummary.data?.spent_total || 0" short size="lg" />
          <template #footer>
            <span class="text-xs text-faint">
              of {{ vnd(moneySummary.data?.quoted_total || 0) }} quoted costs ·
              {{ vnd(moneySummary.data?.advanced_total || 0) }} advanced
            </span>
          </template>
        </BentoCard>
      </div>

      <!-- Tabs: production work, money, paperwork - the market pattern
           for a record this deep. v-show, not v-if: panels keep their
           state and their reload handles while hidden. -->
      <div class="flex items-center gap-1 border-b border-hairline">
        <button
          v-for="tab in TABS"
          :key="tab"
          class="-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors"
          :class="
            activeTab === tab
              ? 'border-accent text-carbon'
              : 'border-transparent text-muted hover:text-carbon'
          "
          @click="activeTab = tab"
        >
          {{ tab }}
          <span
            v-if="tab === 'Money' && overdueCount"
            class="ml-1 inline-block h-1.5 w-1.5 rounded-pill bg-accent align-middle"
            title="Overdue payments"
          ></span>
        </button>
      </div>

      <div v-show="activeTab === 'Production'">
        <div class="grid gap-3 lg:grid-cols-3">
          <div class="space-y-3 lg:col-span-2">
            <!-- Files location: the answer to "where does this job live?" -->
            <BentoCard title="Files">
              <div class="flex flex-wrap items-center gap-2">
                <input
                  v-model="filesLocation"
                  class="min-w-0 flex-1 rounded-[10px] border border-hairline bg-paper px-2.5 py-1.5 text-sm text-carbon placeholder:text-faint focus:outline-none focus:ring-2 focus:ring-accent/30"
                  :placeholder="`Shared folder for this job code - e.g. //nas/jobs/${name}`"
                />
                <Button
                  :disabled="filesLocation === (doc.files_location || '')"
                  @click="saveFilesLocation"
                >
                  Save
                </Button>
              </div>
              <p v-if="!doc.files_location" class="mt-2 text-xs text-warn">
                No folder recorded yet - files still live on someone's personal
                drive.
              </p>
            </BentoCard>

            <!-- Revisions -->
            <DataTable
              title="Revisions"
              :count="doc.revisions?.length || 0"
              :columns="revisionColumns"
              :rows="doc.revisions || []"
              empty-title="No revision rounds logged."
            >
              <template #action>
                <div class="flex flex-wrap items-center justify-end gap-3">
                  <StatusPill
                    v-if="doc.change_order_due"
                    tone="warn"
                    :label="`Round ${doc.revision_rounds} · chargeable change order`"
                  />
                  <span v-else class="text-xs text-muted">
                    {{ doc.revision_rounds || 0 }} of
                    {{ includedRounds }} included rounds used
                  </span>
                  <label class="flex items-center gap-1.5 text-xs text-muted">
                    Included rounds
                    <input
                      v-model.number="includedRounds"
                      type="number"
                      min="0"
                      class="aura-num w-12 rounded-[8px] border border-hairline bg-paper px-1.5 py-0.5 text-right text-xs text-carbon focus:outline-none focus:ring-2 focus:ring-accent/30"
                      @change="saveIncludedRounds"
                    />
                  </label>
                </div>
              </template>

              <template #cell-round="{ row }">
                <span class="inline-flex items-center gap-1.5">
                  <span class="aura-num text-sm text-carbon">{{ row.round }}</span>
                  <FeatherIcon
                    v-if="row.chargeable"
                    name="alert-triangle"
                    class="h-3 w-3 text-warn"
                    title="Chargeable"
                  />
                </span>
              </template>
              <template #cell-requested_on="{ row }">
                <span class="aura-num whitespace-nowrap text-xs text-muted">
                  {{ row.requested_on?.slice(0, 16) }}
                </span>
              </template>
              <template #cell-note="{ row }">
                <span class="text-sm text-carbon">{{ row.note }}</span>
              </template>
              <template #cell-logged_by="{ row }">
                <span class="whitespace-nowrap text-xs text-faint">{{ row.logged_by }}</span>
              </template>

              <template #footer>
                <div class="space-y-1.5 py-1">
                  <div class="flex flex-wrap items-center gap-2">
                    <input
                      v-model="revisionNote"
                      class="min-w-0 flex-1 rounded-[10px] border border-hairline bg-paper px-2.5 py-1.5 text-sm text-carbon placeholder:text-faint focus:outline-none focus:ring-2 focus:ring-accent/30"
                      placeholder="What did the client ask for?"
                      @keyup.enter="logRevision"
                    />
                    <Button
                      variant="solid"
                      :disabled="!revisionNote.trim()"
                      :loading="revision.loading"
                      @click="logRevision"
                    >
                      Log revision
                    </Button>
                  </div>
                  <p v-if="redoNotice" class="text-xs text-accent-ink">
                    {{ redoNotice }}
                  </p>
                  <p v-if="nextIsChargeable" class="text-xs text-warn">
                    The next round is past the included ones - it will be flagged
                    as a chargeable change order.
                  </p>
                  <p v-if="redoOnLog" class="text-xs text-faint">
                    Logging a revision sends this job back to {{ REDO_STAGE }}.
                  </p>
                </div>
              </template>
            </DataTable>

            <!-- Carried packages -->
            <DataTable
              title="Packages"
              :count="doc.packages?.length || 0"
              :columns="packageColumns"
              :rows="doc.packages || []"
              empty-title="The deal had no packages."
            >
              <template #action>
                <span class="text-xs text-faint">carried from the deal</span>
              </template>
              <template #cell-title="{ row }">
                <span class="text-sm font-medium text-carbon">{{ row.title }}</span>
              </template>
              <template #cell-description="{ row }">
                <span class="text-sm text-muted">{{ row.description }}</span>
              </template>
              <template #cell-price="{ row }">
                <MoneyValue :amount="row.price" />
              </template>
            </DataTable>
          </div>

          <!-- Client, links, totals -->
          <div class="space-y-3">
            <BentoCard title="Client">
              <dl class="space-y-1.5 text-sm">
                <div class="flex justify-between gap-3">
                  <dt class="text-muted">Company</dt>
                  <dd class="text-carbon">{{ companyName || doc.company }}</dd>
                </div>
                <div v-if="doc.contact" class="flex justify-between gap-3">
                  <dt class="text-muted">Contact</dt>
                  <dd class="text-carbon">{{ doc.contact }}</dd>
                </div>
                <div class="flex justify-between gap-3">
                  <dt class="text-muted">Owner</dt>
                  <dd class="text-carbon">{{ doc.job_owner }}</dd>
                </div>
                <div v-if="doc.deal" class="flex justify-between gap-3">
                  <dt class="text-muted">From deal</dt>
                  <dd>
                    <router-link
                      :to="`/deals/${doc.deal}/breakdown`"
                      class="aura-num text-accent-ink hover:underline"
                    >
                      {{ doc.deal }}
                    </router-link>
                  </dd>
                </div>
              </dl>
            </BentoCard>

            <BentoCard v-if="doc.job_links?.length" title="Links">
              <ul class="space-y-1.5 text-sm">
                <li v-for="row in doc.job_links" :key="row.name">
                  <a
                    :href="row.url"
                    target="_blank"
                    rel="noopener"
                    class="text-accent-ink hover:underline"
                  >
                    {{ row.label }}
                  </a>
                </li>
              </ul>
            </BentoCard>

            <BentoCard title="Quoted" subtitle="At conversion">
              <dl class="space-y-1.5 text-sm">
                <div class="flex justify-between gap-3">
                  <dt class="text-muted">Subtotal</dt>
                  <dd><MoneyValue :amount="doc.quote_subtotal" /></dd>
                </div>
                <div class="flex justify-between gap-3">
                  <dt class="text-muted">Management fee</dt>
                  <dd><MoneyValue :amount="doc.quote_mf_amount" /></dd>
                </div>
                <div class="flex justify-between gap-3">
                  <dt class="text-muted">VAT</dt>
                  <dd><MoneyValue :amount="doc.quote_vat_amount" /></dd>
                </div>
                <div class="flex justify-between gap-3 border-t border-hairline pt-1.5">
                  <dt class="font-medium text-carbon">Total</dt>
                  <dd><MoneyValue :amount="doc.quote_total" /></dd>
                </div>
              </dl>
            </BentoCard>
          </div>
        </div>
      </div>

      <div v-show="activeTab === 'Money'" class="space-y-3">
        <!-- Money in: what the client owes, and where it has got to -->
        <MilestonesPanel ref="milestones" :job="name" @changed="moneyChanged" />

        <!-- Advances, expenses and settlement (T8) -->
        <JobMoneyPanel :name="name" @changed="moneyChanged" />
      </div>

      <div v-show="activeTab === 'Paperwork'">
        <PaperworkPanel :job="name" />
      </div>
    </template>

    <ErrorMessage class="mt-3" :message="error" />
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue"
import { useRoute } from "vue-router"
import { Button, ErrorMessage, FeatherIcon, createResource } from "frappe-ui"
import PaperworkPanel from "../components/PaperworkPanel.vue"
import BentoCard from "../components/BentoCard.vue"
import DataTable from "../components/DataTable.vue"
import StatusPill from "../components/StatusPill.vue"
import MoneyValue from "../components/MoneyValue.vue"
import { frappeErrorMessage } from "../utils/frappeError"
import { vnd, vndShort } from "../utils/money"
import JobMoneyPanel from "../components/JobMoneyPanel.vue"
import MilestonesPanel from "../components/MilestonesPanel.vue"
import { PAID } from "../data/milestones"
import {
  STAGES,
  INCLUDED_REVISION_ROUNDS,
  REDO_STAGE,
  LAST_REDOABLE_STAGE,
} from "../data/jobStages"

const route = useRoute()
const name = route.params.name

const TABS = ["Production", "Money", "Paperwork"]
const activeTab = ref("Production")

const error = ref("")
const stage = ref("")
const filesLocation = ref("")
const revisionNote = ref("")
const redoNotice = ref("")
// Per job, negotiated deal by deal; the constant is only what a new job
// starts with, and the server is the authority on both.
const includedRounds = ref(INCLUDED_REVISION_ROUNDS)

const revisionColumns = [
  { key: "round", label: "#", width: "56px" },
  { key: "requested_on", label: "Requested", width: "150px" },
  { key: "note", label: "What the client asked for" },
  { key: "logged_by", label: "By", width: "160px" },
]

const packageColumns = [
  { key: "title", label: "Package", width: "220px" },
  { key: "description", label: "Description" },
  { key: "price", label: "Price (VND)", align: "right", width: "160px" },
]

const job = createResource({
  url: "frappe.client.get",
  makeParams: () => ({ doctype: "Job", name }),
  auto: true,
  onSuccess(loaded) {
    stage.value = loaded.stage
    filesLocation.value = loaded.files_location || ""
    includedRounds.value =
      loaded.included_revision_rounds ?? INCLUDED_REVISION_ROUNDS
    error.value = ""
  },
  onError(err) {
    error.value = frappeErrorMessage(err)
  },
})

const doc = computed(() => job.data)

const stageIndex = computed(() => STAGES.indexOf(doc.value?.stage))

// The chip trail: done stages sit on the canvas, the current one carries
// the accent, the rest stay quiet until hovered.
function stageChipClass(index) {
  if (index === stageIndex.value) return "border-accent bg-accent text-white"
  if (index < stageIndex.value) return "border-hairline bg-canvas text-carbon"
  return "border-transparent text-faint hover:border-hairline hover:text-muted"
}

// -- the stat strip: the same numbers the panels read, fetched here so
//    the summary shows before either tab is opened --

const moneySummary = createResource({
  url: "auraos.api.job_money",
  makeParams: () => ({ job: name }),
  auto: true,
})

const milestoneSummary = createResource({
  url: "auraos.api.job_milestones",
  makeParams: () => ({ job: name }),
  auto: true,
})

const milestoneRows = computed(() => milestoneSummary.data?.milestones || [])

const collected = computed(() =>
  milestoneRows.value
    .filter((row) => row.status === PAID)
    .reduce((sum, row) => sum + (row.amount || 0), 0)
)

const collectedPct = computed(() => {
  const total = doc.value?.quote_total || 0
  if (!total) return 0
  return Math.min(100, Math.round((collected.value / total) * 100))
})

const uncollected = computed(() =>
  Math.max(0, (doc.value?.quote_total || 0) - collected.value)
)

const overdueCount = computed(
  () => milestoneRows.value.filter((row) => row.overdue).length
)

// The panels change the money; the strip follows.
function moneyChanged() {
  moneySummary.reload()
  milestoneSummary.reload()
}

const company = createResource({
  url: "frappe.client.get_value",
  makeParams: () => ({
    doctype: "Party Company",
    filters: { name: doc.value?.company },
    fieldname: "company_name",
  }),
})

watch(
  () => doc.value?.company,
  (value) => value && company.submit()
)

const companyName = computed(() => company.data?.company_name)

const nextIsChargeable = computed(
  () => (doc.value?.revision_rounds || 0) >= includedRounds.value
)

// Mirrors redo_stage_for on the server: between being shown a cut and
// signing it off, a revision sends the job back to the edit.
const redoOnLog = computed(() => {
  const current = STAGES.indexOf(doc.value?.stage)
  return (
    current > STAGES.indexOf(REDO_STAGE) &&
    current <= STAGES.indexOf(LAST_REDOABLE_STAGE)
  )
})

// Moving a stage can make a payment fall due, so the milestones panel
// is told to refresh whenever the job itself is written.
const milestones = ref(null)

const setValue = createResource({
  url: "frappe.client.set_value",
  onSuccess() {
    error.value = ""
    job.reload()
    milestones.value?.reload()
    milestoneSummary.reload()
  },
  onError(err) {
    error.value = frappeErrorMessage(err)
    job.reload()
  },
})

function saveStage() {
  setValue.submit({
    doctype: "Job",
    name,
    fieldname: { stage: stage.value },
  })
}

function setStageTo(option) {
  if (option === stage.value) return
  stage.value = option
  saveStage()
}

function saveIncludedRounds() {
  setValue.submit({
    doctype: "Job",
    name,
    fieldname: { included_revision_rounds: includedRounds.value },
  })
}

function saveFilesLocation() {
  setValue.submit({
    doctype: "Job",
    name,
    fieldname: { files_location: filesLocation.value },
  })
}

const revision = createResource({
  url: "auraos.api.log_job_revision",
  onSuccess(result) {
    revisionNote.value = ""
    error.value = ""
    // Say it out loud: the stage moved without anyone dragging a card.
    redoNotice.value = result.redo
      ? `Round ${result.round} logged - this job is back in ${result.stage}.`
      : ""
    job.reload()
  },
  onError(err) {
    error.value = frappeErrorMessage(err)
  },
})

function logRevision() {
  if (!revisionNote.value.trim()) return
  redoNotice.value = ""
  revision.submit({ job: name, note: revisionNote.value })
}
</script>

<template>
  <div class="px-4 pb-6">
    <!-- Sticky, like the breakdown editor: the job's identity and stage
         never scroll away. -->
    <div
      class="sticky top-0 z-10 -mx-4 mb-4 border-b bg-gray-50/95 px-4 py-3 backdrop-blur"
    >
      <div class="flex flex-wrap items-center gap-3">
        <router-link to="/jobs" class="text-sm text-gray-500 hover:text-gray-800">
          ← Jobs
        </router-link>
        <h1 class="text-lg font-semibold text-gray-900">
          {{ doc?.title || name }}
        </h1>
        <span class="text-xs tabular-nums text-gray-400">{{ name }}</span>
        <span v-if="companyName" class="text-sm text-gray-500">
          · {{ companyName }}
        </span>
        <div v-if="doc" class="ml-auto flex items-center gap-2">
          <span class="h-2 w-2 rounded-full" :class="jobStageDot(stage)"></span>
          <select
            v-model="stage"
            class="rounded border-gray-200 py-1 pl-2 pr-8 text-sm"
            @change="saveStage"
          >
            <option v-for="option in STAGES" :key="option" :value="option">
              {{ option }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <div v-if="job.loading" class="py-12 text-center text-sm text-gray-500">
      Loading…
    </div>

    <template v-else-if="doc">
      <!-- Production progress, market-app style: the pipeline as a
           stepper, one click to move the job. -->
      <div class="mb-4 flex gap-1">
        <button
          v-for="(option, index) in STAGES"
          :key="option"
          class="group min-w-0 flex-1"
          :title="`Move to ${option}`"
          @click="setStageTo(option)"
        >
          <span
            class="block h-1.5 rounded-full transition-colors"
            :class="
              index <= stageIndex
                ? jobStageDot(doc.stage)
                : 'bg-gray-200 group-hover:bg-gray-300'
            "
          ></span>
          <span
            class="mt-1 block truncate text-center text-[11px] leading-tight"
            :class="
              option === doc.stage
                ? 'font-semibold text-gray-900'
                : 'text-gray-400 group-hover:text-gray-600'
            "
          >
            {{ option }}
          </span>
        </button>
      </div>

      <!-- The job's money at a glance — collected against quoted is the
           number the founder chases (spec #2, story 39). -->
      <div class="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div class="rounded-lg border bg-white p-3">
          <div class="text-xs text-gray-500">Quoted</div>
          <div class="mt-0.5 text-lg font-semibold tabular-nums text-gray-900">
            {{ vnd(doc.quote_total) }}
          </div>
        </div>
        <div class="rounded-lg border bg-white p-3">
          <div class="text-xs text-gray-500">Collected</div>
          <div class="mt-0.5 text-lg font-semibold tabular-nums text-green-700">
            {{ vnd(collected) }}
          </div>
          <div class="mt-1.5 h-1.5 overflow-hidden rounded-full bg-gray-100">
            <div
              class="h-full rounded-full bg-green-500"
              :style="{ width: `${collectedPct}%` }"
            ></div>
          </div>
        </div>
        <div class="rounded-lg border bg-white p-3">
          <div class="flex items-center gap-1.5 text-xs text-gray-500">
            Uncollected
            <span
              v-if="overdueCount"
              class="inline-flex items-center gap-0.5 rounded-full bg-red-50 px-1.5 py-0.5 text-[11px] font-medium text-red-700"
            >
              <FeatherIcon name="alert-circle" class="h-3 w-3" />
              {{ overdueCount }} overdue
            </span>
          </div>
          <div
            class="mt-0.5 text-lg font-semibold tabular-nums"
            :class="overdueCount ? 'text-red-700' : 'text-gray-900'"
          >
            {{ vnd(uncollected) }}
          </div>
        </div>
        <div class="rounded-lg border bg-white p-3">
          <div class="text-xs text-gray-500">Spent</div>
          <div class="mt-0.5 text-lg font-semibold tabular-nums text-gray-900">
            {{ vnd(moneySummary.data?.spent_total || 0) }}
          </div>
          <div class="mt-0.5 text-xs text-gray-500">
            of {{ vnd(moneySummary.data?.quoted_total || 0) }} quoted costs ·
            {{ vnd(moneySummary.data?.advanced_total || 0) }} advanced
          </div>
        </div>
      </div>

      <!-- Tabs: production work, money, paperwork — the market pattern
           for a record this deep. v-show, not v-if: panels keep their
           state and their reload handles while hidden. -->
      <div class="mb-4 flex items-center gap-1 border-b">
        <button
          v-for="tab in TABS"
          :key="tab"
          class="-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors"
          :class="
            activeTab === tab
              ? 'border-gray-900 text-gray-900'
              : 'border-transparent text-gray-500 hover:text-gray-800'
          "
          @click="activeTab = tab"
        >
          {{ tab }}
          <span
            v-if="tab === 'Money' && overdueCount"
            class="ml-1 inline-block h-2 w-2 rounded-full bg-red-500"
            title="Overdue payments"
          ></span>
        </button>
      </div>

      <div v-show="activeTab === 'Production'">
        <div class="grid gap-4 lg:grid-cols-3">
          <div class="space-y-4 lg:col-span-2">
            <!-- Files location: the answer to "where does this job live?" -->
            <div class="rounded-lg border bg-white p-3">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-sm font-semibold text-gray-800">Files</span>
                <input
                  v-model="filesLocation"
                  class="min-w-0 flex-1 rounded border-gray-200 px-2 py-1 text-sm"
                  :placeholder="`Shared folder for this job code — e.g. //nas/jobs/${name}`"
                />
                <Button
                  :disabled="filesLocation === (doc.files_location || '')"
                  @click="saveFilesLocation"
                >
                  Save
                </Button>
              </div>
              <p v-if="!doc.files_location" class="mt-1 text-xs text-amber-700">
                No folder recorded yet — files still live on someone's personal
                drive.
              </p>
            </div>

            <!-- Revisions -->
            <div class="rounded-lg border bg-white p-3">
              <div class="mb-2 flex flex-wrap items-center gap-2">
                <h2 class="text-sm font-semibold text-gray-800">Revisions</h2>
                <span
                  v-if="doc.change_order_due"
                  class="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-800"
                >
                  <FeatherIcon name="alert-triangle" class="h-3 w-3" />
                  Round {{ doc.revision_rounds }} — chargeable change order
                </span>
                <span v-else class="text-xs text-gray-500">
                  {{ doc.revision_rounds || 0 }} of
                  {{ includedRounds }} included rounds used
                </span>

                <label
                  class="ml-auto flex items-center gap-1 text-xs text-gray-500"
                >
                  Included rounds
                  <input
                    v-model.number="includedRounds"
                    type="number"
                    min="0"
                    class="w-14 rounded border-gray-200 px-1 py-0.5 text-xs tabular-nums"
                    @change="saveIncludedRounds"
                  />
                </label>
              </div>

              <table v-if="doc.revisions?.length" class="w-full text-sm">
                <thead class="text-left text-xs text-gray-600">
                  <tr>
                    <th class="py-1 font-medium">#</th>
                    <th class="py-1 font-medium">Requested</th>
                    <th class="py-1 font-medium">What the client asked for</th>
                    <th class="py-1 font-medium">By</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="row in doc.revisions"
                    :key="row.name"
                    class="border-t"
                    :class="row.chargeable ? 'bg-amber-50' : ''"
                  >
                    <td class="py-1 pr-2 tabular-nums">
                      <span class="inline-flex items-center gap-1">
                        {{ row.round }}
                        <FeatherIcon
                          v-if="row.chargeable"
                          name="alert-triangle"
                          class="h-3 w-3 text-amber-700"
                          title="Chargeable"
                        />
                      </span>
                    </td>
                    <td
                      class="whitespace-nowrap py-1 pr-2 tabular-nums text-gray-600"
                    >
                      {{ row.requested_on?.slice(0, 16) }}
                    </td>
                    <td class="py-1 pr-2 text-gray-800">{{ row.note }}</td>
                    <td class="whitespace-nowrap py-1 text-gray-500">
                      {{ row.logged_by }}
                    </td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="py-2 text-sm text-gray-400">
                No revision rounds logged.
              </p>

              <div class="mt-3 flex flex-wrap items-center gap-2">
                <input
                  v-model="revisionNote"
                  class="min-w-0 flex-1 rounded border-gray-200 px-2 py-1 text-sm"
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
              <p v-if="reopenNotice" class="mt-1 text-xs text-blue-700">
                {{ reopenNotice }}
              </p>
              <p v-if="nextIsChargeable" class="mt-1 text-xs text-amber-700">
                The next round is past the included ones — it will be flagged
                as a chargeable change order.
              </p>
              <p v-if="reopensOnLog" class="mt-1 text-xs text-gray-500">
                Logging a revision sends this job back to {{ REDO_STAGE }}.
              </p>
            </div>

            <!-- Carried packages -->
            <div class="rounded-lg border bg-white p-3">
              <h2 class="mb-2 text-sm font-semibold text-gray-800">
                Packages (carried from the deal)
              </h2>
              <table v-if="doc.packages?.length" class="w-full text-sm">
                <thead class="text-left text-xs text-gray-600">
                  <tr>
                    <th class="py-1 font-medium">Package</th>
                    <th class="py-1 font-medium">Description</th>
                    <th class="py-1 text-right font-medium">Price (VND)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="row in doc.packages"
                    :key="row.name"
                    class="border-t"
                  >
                    <td class="py-1 pr-2 font-medium text-gray-900">
                      {{ row.title }}
                    </td>
                    <td class="py-1 pr-2 text-gray-600">
                      {{ row.description }}
                    </td>
                    <td class="py-1 text-right tabular-nums">
                      {{ vnd(row.price) }}
                    </td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="py-2 text-sm text-gray-400">
                The deal had no packages.
              </p>
            </div>
          </div>

          <!-- Client, links, totals -->
          <div class="space-y-4">
            <div class="rounded-lg border bg-white p-3 text-sm">
              <h2 class="mb-2 text-sm font-semibold text-gray-800">Client</h2>
              <dl class="space-y-1 text-gray-700">
                <div class="flex justify-between gap-2">
                  <dt class="text-gray-500">Company</dt>
                  <dd>{{ companyName || doc.company }}</dd>
                </div>
                <div v-if="doc.contact" class="flex justify-between gap-2">
                  <dt class="text-gray-500">Contact</dt>
                  <dd>{{ doc.contact }}</dd>
                </div>
                <div class="flex justify-between gap-2">
                  <dt class="text-gray-500">Owner</dt>
                  <dd>{{ doc.job_owner }}</dd>
                </div>
                <div v-if="doc.deal" class="flex justify-between gap-2">
                  <dt class="text-gray-500">From deal</dt>
                  <dd>
                    <router-link
                      :to="`/deals/${doc.deal}/breakdown`"
                      class="text-blue-700 hover:underline"
                    >
                      {{ doc.deal }}
                    </router-link>
                  </dd>
                </div>
              </dl>
            </div>

            <div
              v-if="doc.job_links?.length"
              class="rounded-lg border bg-white p-3"
            >
              <h2 class="mb-2 text-sm font-semibold text-gray-800">Links</h2>
              <ul class="space-y-1 text-sm">
                <li v-for="row in doc.job_links" :key="row.name">
                  <a
                    :href="row.url"
                    target="_blank"
                    rel="noopener"
                    class="text-blue-700 hover:underline"
                  >
                    {{ row.label }}
                  </a>
                </li>
              </ul>
            </div>

            <div class="rounded-lg border bg-white p-3 text-sm">
              <h2 class="mb-2 text-sm font-semibold text-gray-800">
                Quoted (at conversion)
              </h2>
              <dl class="space-y-1 text-gray-700">
                <div class="flex justify-between gap-2">
                  <dt class="text-gray-500">Subtotal</dt>
                  <dd class="tabular-nums">{{ vnd(doc.quote_subtotal) }}</dd>
                </div>
                <div class="flex justify-between gap-2">
                  <dt class="text-gray-500">Management fee</dt>
                  <dd class="tabular-nums">{{ vnd(doc.quote_mf_amount) }}</dd>
                </div>
                <div class="flex justify-between gap-2">
                  <dt class="text-gray-500">VAT</dt>
                  <dd class="tabular-nums">{{ vnd(doc.quote_vat_amount) }}</dd>
                </div>
                <div
                  class="flex justify-between gap-2 border-t pt-1 font-medium"
                >
                  <dt>Total</dt>
                  <dd class="tabular-nums">{{ vnd(doc.quote_total) }}</dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      </div>

      <div v-show="activeTab === 'Money'" class="space-y-4">
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
import { frappeErrorMessage } from "../utils/frappeError"
import { vnd } from "../utils/money"
import { jobStageDot } from "../utils/stages"
import JobMoneyPanel from "../components/JobMoneyPanel.vue"
import MilestonesPanel from "../components/MilestonesPanel.vue"
import { PAID } from "../data/milestones"
import {
  STAGES,
  INCLUDED_REVISION_ROUNDS,
  REDO_STAGE,
  LAST_REOPENABLE_STAGE,
} from "../data/jobStages"

const route = useRoute()
const name = route.params.name

const TABS = ["Production", "Money", "Paperwork"]
const activeTab = ref("Production")

const error = ref("")
const stage = ref("")
const filesLocation = ref("")
const revisionNote = ref("")
const reopenNotice = ref("")
// Per job, negotiated deal by deal; the constant is only what a new job
// starts with, and the server is the authority on both.
const includedRounds = ref(INCLUDED_REVISION_ROUNDS)

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
const reopensOnLog = computed(() => {
  const current = STAGES.indexOf(doc.value?.stage)
  return (
    current > STAGES.indexOf(REDO_STAGE) &&
    current <= STAGES.indexOf(LAST_REOPENABLE_STAGE)
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
    reopenNotice.value = result.reopened
      ? `Round ${result.round} logged — this job is back in ${result.stage}.`
      : ""
    job.reload()
  },
  onError(err) {
    error.value = frappeErrorMessage(err)
  },
})

function logRevision() {
  if (!revisionNote.value.trim()) return
  reopenNotice.value = ""
  revision.submit({ job: name, note: revisionNote.value })
}
</script>

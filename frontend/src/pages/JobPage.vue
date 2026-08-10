<template>
  <div class="px-4 py-6">
    <div class="mb-4 flex flex-wrap items-center gap-3">
      <router-link to="/jobs" class="text-sm text-gray-500 hover:text-gray-800">
        ← Jobs
      </router-link>
      <h1 class="text-lg font-semibold text-gray-900">
        {{ doc?.title || name }}
      </h1>
      <span class="text-xs tabular-nums text-gray-400">{{ name }}</span>
      <select
        v-if="doc"
        v-model="stage"
        class="ml-auto rounded border-gray-200 py-1 pl-2 pr-8 text-sm"
        @change="saveStage"
      >
        <option v-for="option in STAGES" :key="option" :value="option">
          {{ option }}
        </option>
      </select>
    </div>

    <div v-if="job.loading" class="py-12 text-center text-sm text-gray-500">
      Loading…
    </div>

    <template v-else-if="doc">
      <!-- Files location: the answer to "where does this job live?" -->
      <div class="mb-4 rounded-lg border bg-white p-3">
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
          No folder recorded yet — files still live on someone's personal drive.
        </p>
      </div>

      <div class="grid gap-4 lg:grid-cols-3">
        <div class="space-y-4 lg:col-span-2">
          <!-- Revisions -->
          <div class="rounded-lg border bg-white p-3">
            <div class="mb-2 flex flex-wrap items-center gap-2">
              <h2 class="text-sm font-semibold text-gray-800">Revisions</h2>
              <span
                v-if="doc.change_order_due"
                class="rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-800"
              >
                ⚠ Round {{ doc.revision_rounds }} — chargeable change order
              </span>
              <span v-else class="text-xs text-gray-500">
                {{ doc.revision_rounds || 0 }} of
                {{ INCLUDED_REVISION_ROUNDS }} included rounds used
              </span>
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
                    {{ row.round }}
                    <span v-if="row.chargeable" title="Chargeable">⚠</span>
                  </td>
                  <td class="py-1 pr-2 whitespace-nowrap tabular-nums text-gray-600">
                    {{ row.requested_on?.slice(0, 16) }}
                  </td>
                  <td class="py-1 pr-2 text-gray-800">{{ row.note }}</td>
                  <td class="py-1 whitespace-nowrap text-gray-500">
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
                  <td class="py-1 pr-2 text-gray-600">{{ row.description }}</td>
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

          <div v-if="doc.job_links?.length" class="rounded-lg border bg-white p-3">
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
              <div class="flex justify-between gap-2 border-t pt-1 font-medium">
                <dt>Total</dt>
                <dd class="tabular-nums">{{ vnd(doc.quote_total) }}</dd>
              </div>
            </dl>
          </div>
        </div>
      </div>
    </template>

    <ErrorMessage class="mt-3" :message="error" />
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue"
import { useRoute } from "vue-router"
import { Button, ErrorMessage, createResource } from "frappe-ui"
import { frappeErrorMessage } from "../utils/frappeError"
import { vnd } from "../utils/money"
import {
  STAGES,
  INCLUDED_REVISION_ROUNDS,
  REDO_STAGE,
  LAST_REOPENABLE_STAGE,
} from "../data/jobStages"

const route = useRoute()
const name = route.params.name

const error = ref("")
const stage = ref("")
const filesLocation = ref("")
const revisionNote = ref("")
const reopenNotice = ref("")

const job = createResource({
  url: "frappe.client.get",
  makeParams: () => ({ doctype: "Job", name }),
  auto: true,
  onSuccess(loaded) {
    stage.value = loaded.stage
    filesLocation.value = loaded.files_location || ""
    error.value = ""
  },
  onError(err) {
    error.value = frappeErrorMessage(err)
  },
})

const doc = computed(() => job.data)

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
  () => (doc.value?.revision_rounds || 0) >= INCLUDED_REVISION_ROUNDS
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

const setValue = createResource({
  url: "frappe.client.set_value",
  onSuccess() {
    error.value = ""
    job.reload()
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

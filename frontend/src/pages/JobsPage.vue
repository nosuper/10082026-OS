<template>
  <div class="px-4 py-6">
    <div class="mb-4 flex items-center gap-3">
      <h1 class="text-lg font-semibold text-gray-900">Jobs</h1>
      <span class="text-sm text-gray-500">
        Won deals in production — new jobs are created from the deal board.
      </span>
    </div>

    <div class="flex gap-3 overflow-x-auto pb-4">
      <div
        v-for="stage in STAGES"
        :key="stage"
        class="flex w-60 shrink-0 flex-col rounded-lg bg-gray-100"
        @dragover.prevent
        @drop="onDrop(stage)"
      >
        <div class="flex items-center gap-2 px-3 py-2 text-sm font-medium">
          {{ stage }}
          <span class="text-xs font-normal text-gray-500">
            {{ jobsByStage[stage]?.length || 0 }}
          </span>
        </div>
        <div class="flex min-h-24 flex-1 flex-col gap-2 px-2 pb-2">
          <div
            v-for="job in jobsByStage[stage]"
            :key="job.name"
            class="cursor-grab rounded-md border bg-white p-3 shadow-sm hover:border-gray-400"
            draggable="true"
            @dragstart="dragged = job"
            @dragend="dragged = null"
            @click="open(job)"
          >
            <div class="flex items-baseline gap-2">
              <span class="text-sm font-medium text-gray-900">
                {{ job.title }}
              </span>
              <span class="ml-auto text-xs tabular-nums text-gray-400">
                {{ job.name }}
              </span>
            </div>
            <div v-if="job.company" class="mt-0.5 text-xs text-gray-600">
              {{ companyNames[job.company] || job.company }}
            </div>
            <div class="mt-2 flex flex-wrap items-center gap-1.5">
              <span
                v-if="job.change_order_due"
                class="rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-800"
                title="Revision rounds past the included ones — chargeable"
              >
                ⚠ Change order · {{ job.revision_rounds }} rounds
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
import { ErrorMessage, createResource, createListResource } from "frappe-ui"
import { frappeErrorMessage } from "../utils/frappeError"
import { STAGES } from "../data/jobStages"

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

const jobsByStage = computed(() => {
  const map = {}
  for (const job of jobs.data || []) {
    ;(map[job.stage] ||= []).push(job)
  }
  return map
})

// -- drag & drop between stages (both roles may move a job) --

const dragged = ref(null)
const moveError = ref("")

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
  if (!job || job.stage === stage) return
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

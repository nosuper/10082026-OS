<template>
  <div class="px-4 pb-6">
    <div
      class="sticky top-0 z-10 -mx-4 mb-4 border-b bg-gray-50/95 px-4 py-3 backdrop-blur"
    >
      <div class="flex flex-wrap items-center gap-3">
        <router-link to="/my-work" class="text-sm text-gray-500 hover:text-gray-800">
          ← My work
        </router-link>
        <h1 class="text-lg font-semibold text-gray-900">
          {{ doc?.title || name }}
        </h1>
        <span class="text-xs tabular-nums text-gray-400">{{ name }}</span>
        <span v-if="doc?.company_name" class="text-sm text-gray-500">
          · {{ doc.company_name }}
        </span>
        <div v-if="doc" class="ml-auto flex items-center gap-2 text-sm text-gray-700">
          <span class="h-2 w-2 rounded-full" :class="jobStageDot(doc.stage)"></span>
          {{ doc.stage }}
        </div>
      </div>
    </div>

    <div v-if="crewView.loading" class="py-12 text-center text-sm text-gray-500">
      Loading…
    </div>

    <ErrorMessage v-else-if="error" :message="error" />

    <template v-else-if="doc">
      <!-- What a crew member needs off the job itself: where the files
           are and what the brief links to. Everything the job was
           priced at is not fetched here at all - see auraos.api.crew_job. -->
      <div class="mb-4 grid gap-3 sm:grid-cols-2">
        <div class="rounded-lg border bg-white p-3 text-sm">
          <div class="text-xs text-gray-500">Files location</div>
          <div class="mt-0.5 break-all font-medium text-gray-900">
            {{ doc.files_location || "not recorded yet" }}
          </div>
        </div>
        <div v-if="doc.links?.length" class="rounded-lg border bg-white p-3">
          <div class="mb-1 text-xs text-gray-500">Links</div>
          <ul class="space-y-1 text-sm">
            <li v-for="(row, index) in doc.links" :key="index">
              <a
                :href="row.url"
                target="_blank"
                rel="noopener"
                class="text-blue-700 hover:underline"
              >
                {{ row.label || row.url }}
              </a>
            </li>
          </ul>
        </div>
      </div>

      <JobTasksPanel
        :job="name"
        empty-message="Nothing on the plan yet - whoever is running this job writes it."
      />
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from "vue"
import { useRoute } from "vue-router"
import { ErrorMessage, createResource } from "frappe-ui"
import JobTasksPanel from "../components/JobTasksPanel.vue"
import { frappeErrorMessage } from "../utils/frappeError"
import { jobStageDot } from "../utils/stages"

const route = useRoute()
const name = route.params.name

const error = ref("")

// The money-free view of the job. Not frappe.client.get: crew hold no
// permission on Job at all, which is what keeps the pricing out of
// reach rather than out of sight.
const crewView = createResource({
  url: "auraos.api.crew_job",
  makeParams: () => ({ job: name }),
  auto: true,
  onSuccess() {
    error.value = ""
  },
  onError(err) {
    error.value = frappeErrorMessage(err)
  },
})

const doc = computed(() => crewView.data)
</script>

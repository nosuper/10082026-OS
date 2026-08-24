<template>
  <div class="px-4 py-6">
    <div class="mb-4 flex flex-wrap items-baseline gap-2">
      <h1 class="text-lg font-semibold text-gray-900">My work</h1>
      <span class="text-sm tabular-nums text-gray-400">{{ jobs.length }}</span>
      <span class="ml-auto text-sm text-gray-500">
        The jobs you hold a task on.
      </span>
    </div>

    <ErrorMessage class="mb-2" :message="error" />

    <div v-if="mine.loading" class="py-12 text-center text-sm text-gray-500">
      Loading…
    </div>

    <ul v-else-if="jobs.length" class="space-y-2">
      <li v-for="job in jobs" :key="job.name">
        <router-link
          :to="`/my-work/${job.name}`"
          class="block rounded-lg border bg-white p-3 transition-shadow hover:border-gray-300 hover:shadow"
        >
          <div class="flex flex-wrap items-baseline gap-2">
            <span class="font-medium text-gray-900">{{ job.title }}</span>
            <span class="text-xs tabular-nums text-gray-400">{{ job.name }}</span>
            <span class="ml-auto flex items-center gap-1.5 text-sm text-gray-600">
              <span class="h-2 w-2 rounded-full" :class="jobStageDot(job.stage)"></span>
              {{ job.stage }}
            </span>
          </div>
          <div class="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
            <span v-if="job.company_name">{{ job.company_name }}</span>
            <span>
              {{ job.task_count }} task{{ job.task_count === 1 ? "" : "s" }} on the job
            </span>
            <span
              v-if="job.open_tasks"
              class="rounded-full bg-blue-50 px-2 py-0.5 font-medium text-blue-700"
            >
              {{ job.open_tasks }} of yours open
            </span>
            <span v-else class="rounded-full bg-green-50 px-2 py-0.5 text-green-700">
              your part is done
            </span>
          </div>
        </router-link>
      </li>
    </ul>

    <p v-else class="py-12 text-center text-sm text-gray-400">
      Nothing assigned to you yet - a job appears here the moment someone
      puts your name on a task.
    </p>
  </div>
</template>

<script setup>
import { ref, computed } from "vue"
import { ErrorMessage, createResource } from "frappe-ui"
import { frappeErrorMessage } from "../utils/frappeError"
import { jobStageDot } from "../utils/stages"

const error = ref("")

// The crew member's whole list, built from their tasks rather than from
// the Job list API - which they cannot call, and which is the point.
const mine = createResource({
  url: "auraos.api.my_jobs",
  auto: true,
  onSuccess() {
    error.value = ""
  },
  onError(err) {
    error.value = frappeErrorMessage(err)
  },
})

const jobs = computed(() => mine.data || [])
</script>

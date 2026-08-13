<template>
  <!-- Built for one hand on a shoot: amount, category, save. Everything
       else has a default that is right nearly every time. -->
  <div class="mx-auto max-w-md px-4 py-5">
    <div class="mb-3 flex items-baseline gap-2">
      <router-link
        :to="`/jobs/${name}`"
        class="text-sm text-gray-500 hover:text-gray-800"
      >
        ← {{ job.data?.title || name }}
      </router-link>
    </div>

    <h1 class="text-lg font-semibold text-gray-900">Log an expense</h1>
    <p v-if="held" class="mt-0.5 text-sm" :class="floatClass">
      {{ floatWording }}
    </p>
    <p v-else class="mt-0.5 text-sm text-gray-500">
      No advance on this job yet - what you log comes back to you.
    </p>

    <label class="mt-4 block text-xs font-medium text-gray-600">Amount</label>
    <VndInput
      ref="amountInput"
      v-model="amount"
      placeholder="0"
      class="mt-1 w-full rounded-lg border-gray-300 px-3 py-3 text-right text-2xl tabular-nums"
      @enter="save"
    />

    <label class="mt-4 block text-xs font-medium text-gray-600">Category</label>
    <div class="mt-1 flex flex-wrap gap-2">
      <button
        v-for="title in categories.data || []"
        :key="title"
        class="rounded-full border px-3 py-1.5 text-sm"
        :class="
          category === title
            ? 'border-gray-900 bg-gray-900 text-white'
            : 'border-gray-300 bg-white text-gray-700'
        "
        @click="category = category === title ? '' : title"
      >
        {{ title }}
      </button>
      <span
        v-if="!(categories.data || []).length"
        class="text-sm text-gray-400"
      >
        This job was quoted with no packages - everything lands uncategorised.
      </span>
    </div>

    <input
      v-model="description"
      placeholder="What was it for? (optional)"
      class="mt-4 w-full rounded-lg border-gray-300 px-3 py-2 text-sm"
    />

    <div class="mt-3 flex items-center gap-2">
      <FileUploader
        file-types="image/*"
        :upload-args="{ private: true, optimize: true, max_width: 1600 }"
        @success="onPhoto"
      >
        <template #default="{ uploading, progress, openFileSelector }">
          <Button :loading="uploading" @click="openFileSelector">
            {{ uploading ? `Uploading ${progress}%` : "📷 Receipt" }}
          </Button>
        </template>
      </FileUploader>
      <template v-if="photo">
        <img :src="photo" alt="receipt" class="h-10 w-10 rounded object-cover" />
        <button class="text-xs text-gray-500 underline" @click="photo = ''">
          remove
        </button>
      </template>
    </div>

    <Button
      class="mt-5 w-full"
      variant="solid"
      size="lg"
      :disabled="!parsed"
      :loading="expense.loading"
      @click="save"
    >
      Log {{ parsed ? vnd(parsed) : "expense" }}
    </Button>

    <ErrorMessage class="mt-2" :message="error" />

    <div v-if="logged.length" class="mt-6">
      <h2 class="text-xs font-medium text-gray-600">Logged just now</h2>
      <div
        v-for="row in logged"
        :key="row.name"
        class="flex items-baseline gap-2 border-b py-1.5 text-sm"
      >
        <span class="text-green-700">✓</span>
        <span class="text-gray-800">{{ row.category || "Uncategorised" }}</span>
        <span class="ml-auto tabular-nums">{{ vnd(row.amount) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from "vue"
import { useRoute } from "vue-router"
import { Button, ErrorMessage, FileUploader, createResource } from "frappe-ui"
import VndInput from "../components/VndInput.vue"
import { frappeErrorMessage } from "../utils/frappeError"
import { parseVnd, vnd } from "../utils/money"

const route = useRoute()
const name = route.params.name

const amount = ref("")
const category = ref("")
const description = ref("")
const photo = ref("")
const error = ref("")
const logged = ref([])
const held = ref(null)
const amountInput = ref(null)

const parsed = computed(() => parseVnd(amount.value))

const job = createResource({
  url: "frappe.client.get_value",
  makeParams: () => ({
    doctype: "Job",
    filters: { name },
    fieldname: "title",
  }),
  auto: true,
})

const categories = createResource({
  url: "auraos.api.job_expense_categories",
  makeParams: () => ({ job: name }),
  auto: true,
  onError(err) {
    error.value = frappeErrorMessage(err)
  },
})

// The float is the only number worth carrying on this screen: it is the
// answer to "can I still pay for this out of what I'm holding?"
const money = createResource({
  url: "auraos.api.job_money",
  makeParams: () => ({ job: name }),
  auto: true,
  onSuccess(data) {
    held.value =
      (data.floats || []).find((row) => row.holder === currentUser) || null
  },
})

const currentUser = decodeURIComponent(
  document.cookie
    .split("; ")
    .find((c) => c.startsWith("user_id="))
    ?.split("=")[1] || ""
)

const floatWording = computed(() => {
  if (!held.value) return ""
  return held.value.amount >= 0
    ? `${vnd(held.value.amount)} ₫ left of your advance`
    : `${vnd(-held.value.amount)} ₫ of your own money, so far`
})

const floatClass = computed(() =>
  held.value?.amount >= 0 ? "text-gray-600" : "text-amber-700"
)

const expense = createResource({
  url: "auraos.api.log_job_expense",
  onSuccess(result) {
    logged.value.unshift(result)
    held.value = result.float
    amount.value = ""
    description.value = ""
    photo.value = ""
    error.value = ""
    amountInput.value?.focus()
  },
  onError(err) {
    error.value = frappeErrorMessage(err)
  },
})

function onPhoto(file) {
  photo.value = file.file_url
}

function save() {
  if (!parsed.value) return
  expense.submit({
    job: name,
    amount: parsed.value,
    category: category.value || null,
    description: description.value || null,
    photo: photo.value || null,
  })
}

onMounted(() => amountInput.value?.focus())
</script>

<template>
  <div class="rounded-lg border bg-white p-3">
    <div class="mb-2 flex flex-wrap items-center gap-2">
      <h2 class="text-sm font-semibold text-gray-800">Paperwork</h2>
      <span class="text-xs text-gray-500">
        Filled from this job and printed for wet-ink signature.
      </span>
    </div>

    <div v-if="!templates.data?.length" class="py-2 text-sm text-gray-400">
      No templates in the library yet.
      <router-link to="/paperwork" class="text-blue-700 hover:underline">
        Upload one
      </router-link>
      to generate paperwork from it.
    </div>

    <template v-else>
      <div class="flex flex-wrap items-end gap-2">
        <label class="text-xs text-gray-500">
          Template
          <select
            v-model="chosen"
            class="mt-0.5 block w-56 rounded border-gray-200 py-1 pl-2 pr-8 text-sm"
          >
            <option v-for="row in templates.data" :key="row.name" :value="row.name">
              {{ row.template_name }}
            </option>
          </select>
        </label>

        <!-- Only the parties this paper actually mentions are asked for. -->
        <label v-if="template?.needs_freelancer" class="text-xs text-gray-500">
          Freelancer
          <select
            v-model="freelancer"
            class="mt-0.5 block w-48 rounded border-gray-200 py-1 pl-2 pr-8 text-sm"
          >
            <option value="">- pick a person -</option>
            <optgroup v-if="crew.length" label="On this job">
              <option v-for="row in crew" :key="row.name" :value="row.name">
                {{ row.full_name }}
              </option>
            </optgroup>
            <optgroup :label="crew.length ? 'Everyone' : 'Contacts'">
              <option
                v-for="row in contactsOffJob"
                :key="row.name"
                :value="row.name"
              >
                {{ row.full_name }}
              </option>
            </optgroup>
          </select>
        </label>

        <label v-if="template?.needs_vendor" class="text-xs text-gray-500">
          Vendor
          <select
            v-model="vendor"
            class="mt-0.5 block w-48 rounded border-gray-200 py-1 pl-2 pr-8 text-sm"
          >
            <option value="">- pick a company -</option>
            <option v-for="row in companies.data" :key="row.name" :value="row.name">
              {{ row.company_name }}
            </option>
          </select>
        </label>

        <!-- One door: every paper is read before it exists - Generate
             lives inside the window (founder, A5 round 5). -->
        <Button
          variant="solid"
          :loading="previewer.loading"
          @click="openPreview"
        >
          Preview
        </Button>
      </div>

      <PaperWindow
        ref="draftWindow"
        :modelValue="!!preview"
        :title="draftTitle"
        :content="preview?.html || ''"
        save-label="Generate .docx"
        :saving="draftSaver.loading || generator.loading"
        @update:modelValue="(open) => !open && (preview = null)"
        @save="generateFromWindow"
      />

      <p v-if="template?.unknown_placeholders?.length" class="mt-2 text-xs text-amber-700">
        ⚠ This template asks for
        {{ template.unknown_placeholders.join(", ") }} - no such placeholder
        exists, so it will print as a gap marker. Fix the docx in the
        <router-link to="/paperwork" class="underline">library</router-link>.
      </p>

      <!-- The whole point of the ticket: what did not get filled, said
           out loud, beside the document it is missing from. -->
      <div
        v-if="generated"
        class="mt-3 rounded-md border p-2 text-sm"
        :class="gaps.length ? 'border-amber-200 bg-amber-50' : 'border-green-200 bg-green-50'"
      >
        <!-- Opens the reading window like every other paper - no
             surprise downloads (founder, A5 round 7). -->
        <button
          class="text-left font-medium text-blue-700 hover:underline"
          @click="openDocument(generated)"
        >
          {{ generated.file_name }}
        </button>
        <p v-if="!gaps.length" class="mt-1 text-xs text-green-800">
          Every placeholder filled - ready to print.
        </p>
        <template v-else>
          <p class="mt-1 text-xs text-amber-900">
            Printed with {{ gaps.length }}
            {{ gaps.length === 1 ? "gap" : "gaps" }} marked on the page -
            fill these in and generate again:
          </p>
          <ul class="mt-1 space-y-0.5 text-xs text-amber-900">
            <li v-for="name in generated.missing" :key="name">
              · <code>{{ name }}</code> - no data on the record
            </li>
            <li v-for="name in generated.unknown" :key="name">
              · <code>{{ name }}</code> - not a placeholder this system has
            </li>
          </ul>
        </template>
      </div>
    </template>

    <table v-if="documents.data?.length" class="mt-3 w-full text-sm">
      <thead class="text-left text-xs text-gray-600">
        <tr>
          <th class="py-1 font-medium">Document on this job</th>
          <th class="py-1 font-medium">Added</th>
          <th class="py-1 font-medium">By</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in documents.data" :key="row.name" class="border-t">
          <td class="py-1 pr-2">
            <button
              class="text-left text-blue-700 hover:underline"
              @click="openDocument(row)"
            >
              {{ row.file_name }}
            </button>
          </td>
          <td class="py-1 pr-2 whitespace-nowrap tabular-nums text-gray-600">
            {{ row.creation?.slice(0, 16) }}
          </td>
          <td class="py-1 whitespace-nowrap text-gray-500">{{ row.owner }}</td>
        </tr>
      </tbody>
    </table>

    <!-- Reading window for papers already on the job. -->
    <PaperWindow
      :modelValue="!!docWindow"
      :title="docWindow?.title"
      :content="docWindow?.content || ''"
      :download-url="docWindow?.downloadUrl || ''"
      @update:modelValue="(open) => !open && (docWindow = null)"
    />

    <ErrorMessage class="mt-2" :message="error" />
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue"
import { Button, ErrorMessage, createResource } from "frappe-ui"
import PaperWindow from "./PaperWindow.vue"
import { frappeErrorMessage } from "../utils/frappeError"

const props = defineProps({
  job: { type: String, required: true },
})

const error = ref("")
const chosen = ref("")
const vendor = ref("")
const freelancer = ref("")
const generated = ref(null)

function onFail(err) {
  error.value = frappeErrorMessage(err)
}

const templates = createResource({
  url: "auraos.api.paperwork_templates",
  auto: true,
  onSuccess(rows) {
    error.value = ""
    if (!chosen.value) chosen.value = rows?.[0]?.name || ""
  },
  onError: onFail,
})

const template = computed(() =>
  templates.data?.find((row) => row.name === chosen.value)
)

const documents = createResource({
  url: "auraos.api.job_paperwork",
  params: { job: props.job },
  auto: true,
  onError: onFail,
})

// The party lists are only fetched for templates that name one - most
// papers are between us and the client, who is already on the job.
const contacts = createResource({
  url: "frappe.client.get_list",
  makeParams: () => ({
    doctype: "Party Contact",
    fields: ["name", "full_name"],
    order_by: "full_name asc",
    limit_page_length: 0,
  }),
  onError: onFail,
})

const companies = createResource({
  url: "frappe.client.get_list",
  makeParams: () => ({
    doctype: "Party Company",
    fields: ["name", "company_name"],
    order_by: "company_name asc",
    limit_page_length: 0,
  }),
  onError: onFail,
})

// A freelancer contract is nearly always for someone already on the
// job's cost lines - they come first, everyone else below.
const parties = createResource({
  url: "auraos.api.job_parties",
  makeParams: () => ({ job: props.job }),
  onError: onFail,
})

const crew = computed(() => parties.data?.freelancers || [])

const contactsOffJob = computed(() => {
  const onJob = new Set(crew.value.map((row) => row.name))
  return (contacts.data || []).filter((row) => !onJob.has(row.name))
})

watch(
  template,
  (row) => {
    if (row?.needs_freelancer && !contacts.data) {
      contacts.submit()
      parties.submit()
    }
    if (row?.needs_vendor && !companies.data) companies.submit()
  },
  { immediate: true }
)

const gaps = computed(() => [
  ...(generated.value?.missing || []),
  ...(generated.value?.unknown || []),
])

const generator = createResource({
  url: "auraos.api.generate_job_paperwork",
  onSuccess(result) {
    error.value = ""
    generated.value = result
    documents.reload()
  },
  onError(err) {
    generated.value = null
    onFail(err)
  },
})

// -- the draft window: read, edit, print, generate (A5 rounds 3–5) --

const preview = ref(null)
const draftWindow = ref(null)

const previewer = createResource({
  url: "auraos.api.preview_job_paperwork",
  onSuccess(result) {
    error.value = ""
    preview.value = result
  },
  onError(err) {
    preview.value = null
    onFail(err)
  },
})

const draftTitle = computed(
  () => `Draft - ${template.value?.template_name || "paper"}`
)

function openPreview() {
  preview.value = null
  previewer.submit({
    job: props.job,
    template: chosen.value,
    vendor: vendor.value || null,
    freelancer: freelancer.value || null,
  })
}

const draftSaver = createResource({
  url: "auraos.api.save_job_paperwork_draft",
  onSuccess(result) {
    error.value = ""
    preview.value = null
    generated.value = { ...result, missing: [], unknown: [] }
    documents.reload()
  },
  onError: onFail,
})

// Generate lives inside the window. An untouched draft generates from
// the original file - an uploaded Word template keeps its exact
// formatting that way; an edited draft is what the founder approved,
// so the edit wins and builds through the HTML→Word translator.
function generateFromWindow(html) {
  if (draftWindow.value?.edited()) {
    draftSaver.submit({
      job: props.job,
      template: chosen.value,
      html,
      vendor: vendor.value || null,
      freelancer: freelancer.value || null,
    })
  } else {
    preview.value = null
    generate()
  }
}

// -- reading papers already on the job --

const docWindow = ref(null)
let pendingDoc = null

const docPreviewer = createResource({
  url: "auraos.api.preview_paper",
  onSuccess(data) {
    error.value = ""
    docWindow.value = {
      title: pendingDoc?.file_name || "Paper",
      content: data.html || "<p>(File này không phải văn bản .docx)</p>",
      downloadUrl: pendingDoc?.file_url || "",
    }
  },
  onError: onFail,
})

function openDocument(row) {
  pendingDoc = row
  docPreviewer.submit({ file_url: row.file_url })
}

function generate() {
  generated.value = null
  generator.submit({
    job: props.job,
    template: chosen.value,
    vendor: vendor.value || null,
    freelancer: freelancer.value || null,
  })
}
</script>

<style>
/* The preview's gap markers - v-html content is out of Tailwind's
   reach, so the highlight is plain CSS. */
.aura-paper mark[data-gap] {
  background-color: #fde68a;
  color: #92400e;
  padding: 0 2px;
  border-radius: 2px;
}
</style>

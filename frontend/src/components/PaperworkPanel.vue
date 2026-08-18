<template>
  <div class="overflow-hidden rounded-card border border-hairline bg-paper shadow-card">
    <div class="flex flex-wrap items-center gap-2 border-b border-hairline px-4 py-3">
      <h2 class="font-display text-sm font-semibold text-carbon">Paperwork</h2>
      <span class="text-xs text-faint">
        Filled from this job and printed for wet-ink signature.
      </span>
    </div>

    <div v-if="!templates.data?.length" class="px-4 py-6 text-center text-sm text-muted">
      No templates in the library yet.
      <router-link to="/paperwork" class="text-accent-ink hover:underline">
        Upload one
      </router-link>
      to generate paperwork from it.
    </div>

    <template v-else>
      <div class="flex flex-wrap items-end gap-3 px-4 py-3">
        <label class="block">
          <span class="aura-eyebrow">Template</span>
          <select
            v-model="chosen"
            class="mt-1 block w-56 rounded-[10px] border border-hairline bg-paper py-1.5 pl-2 pr-8 text-sm text-carbon focus:outline-none focus:ring-2 focus:ring-accent/30"
          >
            <option v-for="row in templates.data" :key="row.name" :value="row.name">
              {{ row.template_name }}
            </option>
          </select>
        </label>

        <!-- Only the parties this paper actually mentions are asked for. -->
        <label v-if="template?.needs_freelancer" class="block">
          <span class="aura-eyebrow">Freelancer</span>
          <select
            v-model="freelancer"
            class="mt-1 block w-48 rounded-[10px] border border-hairline bg-paper py-1.5 pl-2 pr-8 text-sm text-carbon focus:outline-none focus:ring-2 focus:ring-accent/30"
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

        <label v-if="template?.needs_vendor" class="block">
          <span class="aura-eyebrow">Vendor</span>
          <select
            v-model="vendor"
            class="mt-1 block w-48 rounded-[10px] border border-hairline bg-paper py-1.5 pl-2 pr-8 text-sm text-carbon focus:outline-none focus:ring-2 focus:ring-accent/30"
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

      <p
        v-if="template?.unknown_placeholders?.length"
        class="flex items-start gap-1.5 px-4 pb-3 text-xs text-warn"
      >
        <FeatherIcon name="alert-triangle" class="mt-0.5 h-3 w-3 shrink-0" />
        <span>
          This template asks for
          {{ template.unknown_placeholders.join(", ") }} - no such placeholder
          exists, so it will print as a gap marker. Fix the docx in the
          <router-link to="/paperwork" class="underline">library</router-link>.
        </span>
      </p>

      <!-- The whole point of the ticket: what did not get filled, said
           out loud, beside the document it is missing from. -->
      <div
        v-if="generated"
        class="mx-4 mb-3 rounded-card border p-3 text-sm"
        :class="gaps.length ? 'border-warn/25 bg-warn-soft' : 'border-ok/25 bg-ok/5'"
      >
        <!-- Opens the reading window like every other paper - no
             surprise downloads (founder, A5 round 7). -->
        <button
          class="text-left font-medium text-accent-ink hover:underline"
          @click="openDocument(generated)"
        >
          {{ generated.file_name }}
        </button>
        <p v-if="!gaps.length" class="mt-1 text-xs text-ok">
          Every placeholder filled - ready to print.
        </p>
        <template v-else>
          <p class="mt-1 text-xs text-warn">
            Printed with {{ gaps.length }}
            {{ gaps.length === 1 ? "gap" : "gaps" }} marked on the page -
            fill these in and generate again:
          </p>
          <ul class="mt-1 space-y-0.5 text-xs text-warn">
            <li v-for="name in generated.missing" :key="name">
              · <code class="aura-num">{{ name }}</code> - no data on the record
            </li>
            <li v-for="name in generated.unknown" :key="name">
              · <code class="aura-num">{{ name }}</code> - not a placeholder this system has
            </li>
          </ul>
        </template>
      </div>
    </template>

    <div v-if="documents.data?.length" class="overflow-x-auto border-t border-hairline">
      <table class="w-full border-collapse text-sm">
        <thead>
          <tr class="border-b border-hairline bg-canvas/60">
            <th class="aura-eyebrow px-4 py-2 text-left font-medium">
              Document on this job
            </th>
            <th class="aura-eyebrow px-2 py-2 text-left font-medium">Added</th>
            <th class="aura-eyebrow px-4 py-2 text-left font-medium">By</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in documents.data"
            :key="row.name"
            class="border-b border-hairline last:border-0"
          >
            <td class="px-4 py-2">
              <button
                class="text-left text-sm font-medium text-accent-ink hover:underline"
                @click="openDocument(row)"
              >
                {{ row.file_name }}
              </button>
            </td>
            <td class="aura-num whitespace-nowrap px-2 py-2 text-xs text-muted">
              {{ row.creation?.slice(0, 16) }}
            </td>
            <td class="whitespace-nowrap px-4 py-2 text-xs text-faint">
              {{ row.owner }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Reading window for papers already on the job. -->
    <PaperWindow
      :modelValue="!!docWindow"
      :title="docWindow?.title"
      :content="docWindow?.content || ''"
      :download-url="docWindow?.downloadUrl || ''"
      @update:modelValue="(open) => !open && (docWindow = null)"
    />

    <ErrorMessage class="px-4 pb-3" :message="error" />
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue"
import { Button, ErrorMessage, FeatherIcon, createResource } from "frappe-ui"
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

// -- the draft window: read, edit, print, generate (A5 rounds 3-5) --

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
// so the edit wins and builds through the HTML to Word translator.
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
  background-color: #fdf0ec;
  color: #b8431f;
  padding: 0 2px;
  border-radius: 2px;
}
</style>

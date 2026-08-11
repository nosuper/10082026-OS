<template>
  <div class="mx-auto max-w-3xl px-4 py-6">
    <h1 class="mb-1 text-lg font-semibold text-gray-900">Paperwork templates</h1>
    <p class="mb-4 text-sm text-gray-500">
      Design each paper once in Word — letterhead, clauses, signature block
      — and type <code>{{ EXAMPLE }}</code> where a value belongs.
      Generating fills those in and attaches the result to the job.
    </p>

    <div
      v-if="library.data && !library.data.can_manage"
      class="mb-4 rounded-md border bg-gray-50 px-3 py-2 text-sm text-gray-600"
    >
      Only the founder can add or change templates. You can generate
      paperwork from these on any job.
    </div>

    <!-- Upload -->
    <div v-if="library.data?.can_manage" class="mb-6 rounded-lg border bg-white p-4">
      <div class="flex flex-wrap items-end gap-2">
        <label class="text-sm text-gray-700">
          Name
          <input
            v-model="name"
            class="mt-0.5 block w-64 rounded border-gray-200 px-2 py-1 text-sm"
            placeholder="Hợp đồng dịch vụ"
          />
        </label>
        <FileUploader
          :file-types="DOCX"
          :upload-args="{ private: true }"
          @success="onUploaded"
          @failure="onFail"
        >
          <template #default="{ openFileSelector, uploading }">
            <Button :loading="uploading" @click="openFileSelector">
              {{ uploaded ? "Choose another .docx" : "Choose .docx" }}
            </Button>
          </template>
        </FileUploader>
        <span v-if="uploaded" class="text-xs text-gray-600">
          {{ uploaded.file_name }}
        </span>
        <Button
          variant="solid"
          :disabled="!name.trim() || !uploaded"
          :loading="creator.loading"
          @click="create"
        >
          Add to library
        </Button>
      </div>
      <p class="mt-2 text-xs text-gray-500">
        Only .docx — a .doc renamed, or a PDF, is refused when saved.
      </p>
    </div>

    <!-- The library -->
    <div
      v-for="row in library.data?.templates || []"
      :key="row.name"
      class="mb-3 rounded-lg border bg-white p-3"
      :class="row.disabled ? 'opacity-60' : ''"
    >
      <div class="flex flex-wrap items-center gap-2">
        <a :href="row.template_file" class="font-medium text-blue-700 hover:underline">
          {{ row.template_name }}
        </a>
        <span v-if="row.disabled" class="text-xs text-gray-500">retired</span>
        <span class="ml-auto flex gap-1" v-if="library.data?.can_manage">
          <button
            class="rounded border px-1.5 py-0.5 text-xs text-gray-600 hover:bg-gray-50"
            @click="setDisabled(row, !row.disabled)"
          >
            {{ row.disabled ? "Bring back" : "Retire" }}
          </button>
          <button
            class="rounded border px-1.5 py-0.5 text-xs text-red-700 hover:bg-red-50"
            @click="remove(row)"
          >
            Delete
          </button>
        </span>
      </div>

      <p v-if="row.unknown_placeholders.length" class="mt-1 text-xs text-amber-700">
        ⚠ Asks for {{ row.unknown_placeholders.join(", ") }} — no such
        placeholder, so it prints as a gap marker. Fix the docx and upload
        it again.
      </p>

      <p v-if="row.placeholders.length" class="mt-1 text-xs text-gray-500">
        Fills:
        <code
          v-for="field in row.placeholders"
          :key="field"
          class="mr-1"
          :class="row.unknown_placeholders.includes(field) ? 'text-amber-700' : ''"
        >
          {{ field }}
        </code>
      </p>
      <p v-else class="mt-1 text-xs text-gray-400">
        No placeholders — this prints exactly as designed.
      </p>
    </div>

    <p
      v-if="library.data && !library.data.templates.length"
      class="rounded-lg border bg-white p-4 text-sm text-gray-400"
    >
      The library is empty.
    </p>

    <!-- The cheat sheet: what a template may ask for -->
    <details v-if="library.data" class="mt-6 rounded-lg border bg-white p-3">
      <summary class="cursor-pointer text-sm font-semibold text-gray-800">
        Placeholders a template can use ({{ library.data.placeholders.length }})
      </summary>
      <div class="mt-2 grid grid-cols-2 gap-x-4 gap-y-0.5 sm:grid-cols-3">
        <code v-for="field in library.data.placeholders" :key="field" class="text-xs">
          {{ braced(field) }}
        </code>
      </div>
      <p class="mt-2 text-xs text-gray-500">
        Our own company name, tax code and address are not on this list —
        they are the same on every paper, so type them into the template.
      </p>
    </details>

    <ErrorMessage class="mt-3" :message="error" />
  </div>
</template>

<script setup>
import { ref } from "vue"
import { Button, ErrorMessage, FileUploader, createResource } from "frappe-ui"
import { frappeErrorMessage } from "../utils/frappeError"

const DOCX =
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

// Placeholder syntax has to be shown, not interpolated — a literal
// "}}" in the template markup would close the interpolation early.
function braced(field) {
  return `{{${field}}}`
}
const EXAMPLE = braced("client.tax_code")

const error = ref("")
const name = ref("")
const uploaded = ref(null)

function onFail(err) {
  error.value = frappeErrorMessage(err) || String(err)
}

const library = createResource({
  url: "auraos.api.paperwork_library",
  auto: true,
  onSuccess() {
    error.value = ""
  },
  onError: onFail,
})

function onUploaded(file) {
  error.value = ""
  uploaded.value = file
}

const creator = createResource({
  url: "frappe.client.insert",
  onSuccess() {
    name.value = ""
    uploaded.value = null
    error.value = ""
    library.reload()
  },
  onError: onFail,
})

function create() {
  creator.submit({
    doc: {
      doctype: "Paperwork Template",
      template_name: name.value.trim(),
      template_file: uploaded.value.file_url,
    },
  })
}

const setter = createResource({
  url: "frappe.client.set_value",
  onSuccess() {
    error.value = ""
    library.reload()
  },
  onError: onFail,
})

function setDisabled(row, disabled) {
  setter.submit({
    doctype: "Paperwork Template",
    name: row.name,
    fieldname: { disabled: disabled ? 1 : 0 },
  })
}

const deleter = createResource({
  url: "frappe.client.delete",
  onSuccess() {
    error.value = ""
    library.reload()
  },
  onError: onFail,
})

function remove(row) {
  // Papers already generated are attached to their jobs and survive
  // this — deleting a template only stops new ones being made from it.
  if (!window.confirm(`Delete the template "${row.template_name}"?`)) return
  deleter.submit({ doctype: "Paperwork Template", name: row.name })
}
</script>

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

    <!-- Upload, or write one right here -->
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
        <Button v-if="!editor" class="ml-auto" @click="openEditor()">
          Write one here
        </Button>
      </div>
      <p class="mt-2 text-xs text-gray-500">
        Only .docx — a .doc renamed, or a PDF, is refused when saved.
      </p>
    </div>

    <!-- The web editor (A5 round 2): type the paper, click a
         placeholder to drop it in at the cursor, save — the .docx is
         built server-side. Templates written here stay editable here;
         uploaded ones are edited in Word. -->
    <div v-if="editor" class="mb-6 rounded-lg border bg-white p-4">
      <div class="mb-2 flex flex-wrap items-center gap-2">
        <h2 class="text-sm font-semibold text-gray-800">
          {{ editor.name ? "Edit template" : "Write a template" }}
        </h2>
        <Button class="ml-auto" @click="editor = null">Cancel</Button>
        <Button
          variant="solid"
          :disabled="!editor.template_name.trim() || !editor.template_source.trim()"
          :loading="editorSaver.loading"
          @click="saveEditor"
        >
          Save template
        </Button>
      </div>
      <input
        v-model="editor.template_name"
        placeholder="Template name — e.g. Hợp đồng cộng tác viên"
        class="mb-2 w-full rounded border-gray-200 px-2 py-1.5 text-sm sm:w-96"
      />
      <textarea
        ref="editorArea"
        v-model="editor.template_source"
        rows="14"
        spellcheck="false"
        class="w-full rounded border-gray-200 px-3 py-2 font-mono text-sm leading-relaxed"
        placeholder="HỢP ĐỒNG CỘNG TÁC VIÊN&#10;&#10;Hôm nay, ngày {{ '{{today.day}}' }}…"
      ></textarea>
      <p class="mb-1 mt-2 text-xs font-medium text-gray-600">
        Click to insert at the cursor:
      </p>
      <div class="flex max-h-28 flex-wrap gap-1 overflow-y-auto">
        <button
          v-for="field in library.data?.placeholders || []"
          :key="field"
          class="rounded bg-gray-50 px-1.5 py-0.5 font-mono text-xs text-gray-700 hover:bg-blue-50 hover:text-blue-800"
          @click="insertPlaceholder(field)"
        >
          {{ field }}
        </button>
      </div>
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
        <span
          v-if="row.template_source"
          class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
          title="Written in the app — editable right here"
        >
          web
        </span>
        <span class="ml-auto flex gap-1" v-if="library.data?.can_manage">
          <button
            v-if="row.template_source"
            class="rounded border px-1.5 py-0.5 text-xs text-blue-700 hover:bg-blue-50"
            @click="openEditor(row)"
          >
            Edit
          </button>
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

      <p
        v-if="row.unknown_placeholders.length"
        class="mt-1 flex items-start gap-1 text-xs text-amber-700"
      >
        <FeatherIcon name="alert-triangle" class="mt-0.5 h-3 w-3 shrink-0" />
        <span>
          Asks for {{ row.unknown_placeholders.join(", ") }} — no such
          placeholder, so it prints as a gap marker. Fix the docx and upload
          it again.
        </span>
      </p>

      <div
        v-if="row.placeholders.length"
        class="mt-1.5 flex flex-wrap items-center gap-1 text-xs text-gray-500"
      >
        <span>Fills:</span>
        <code
          v-for="field in row.placeholders"
          :key="field"
          class="rounded bg-gray-50 px-1 py-0.5"
          :class="row.unknown_placeholders.includes(field) ? 'bg-amber-50 text-amber-700' : ''"
        >
          {{ field }}
        </code>
      </div>
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

    <!-- The registry (A5 round 2): every paper ever generated, in one
         place — the files themselves hang off their jobs. -->
    <div class="mt-6 rounded-lg border bg-white p-3">
      <div class="mb-2 flex flex-wrap items-baseline gap-2">
        <h2 class="text-sm font-semibold text-gray-800">Generated papers</h2>
        <span v-if="papers.data?.length" class="text-xs text-gray-500">
          {{ papers.data.length }}
        </span>
        <input
          v-model.trim="paperSearch"
          placeholder="Search…"
          class="ml-auto w-48 rounded border-gray-200 px-2 py-1 text-sm"
        />
      </div>
      <div v-if="filteredPapers.length" class="overflow-x-auto">
        <table class="w-full min-w-[36rem] text-sm">
          <thead class="text-left text-xs text-gray-600">
            <tr>
              <th class="py-1 font-medium">Paper</th>
              <th class="py-1 font-medium">For</th>
              <th class="py-1 font-medium">Job</th>
              <th class="py-1 font-medium">Generated</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredPapers" :key="row.name" class="border-t">
              <td class="py-1.5 pr-3">
                <a
                  :href="row.file_url"
                  class="font-medium text-blue-700 hover:underline"
                >
                  {{ row.template_name || row.file_name }}
                </a>
              </td>
              <td class="py-1.5 pr-3 text-gray-700">
                {{ row.freelancer_label || row.vendor_label || "Client" }}
              </td>
              <td class="py-1.5 pr-3">
                <router-link
                  :to="`/jobs/${row.job}`"
                  class="text-blue-700 hover:underline"
                >
                  {{ row.job }}
                </router-link>
              </td>
              <td class="whitespace-nowrap py-1.5 tabular-nums text-gray-500">
                {{ row.creation?.slice(0, 16) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="py-2 text-sm text-gray-400">
        Nothing generated yet — papers made on a job appear here.
      </p>
    </div>

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
import { computed, nextTick, ref } from "vue"
import { Button, ErrorMessage, FeatherIcon, FileUploader, createResource } from "frappe-ui"
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

// -- the web editor (A5 round 2) --

const editor = ref(null)
const editorArea = ref(null)

function openEditor(row = null) {
  editor.value = {
    name: row?.name || null,
    template_name: row?.template_name || "",
    template_source: row?.template_source || "",
  }
}

function insertPlaceholder(field) {
  const area = editorArea.value
  const token = braced(field)
  if (!area) {
    editor.value.template_source += token
    return
  }
  const start = area.selectionStart ?? editor.value.template_source.length
  const end = area.selectionEnd ?? start
  const text = editor.value.template_source
  editor.value.template_source = text.slice(0, start) + token + text.slice(end)
  nextTick(() => {
    area.focus()
    area.selectionStart = area.selectionEnd = start + token.length
  })
}

// set_value, not client.save: a partial doc through client.save would
// blank every field it doesn't carry (notes, disabled, the file).
const editorSaver = createResource({
  url: "frappe.client.set_value",
  onSuccess() {
    editor.value = null
    error.value = ""
    library.reload()
  },
  onError: onFail,
})

const editorCreator = createResource({
  url: "frappe.client.insert",
  onSuccess() {
    editor.value = null
    error.value = ""
    library.reload()
  },
  onError: onFail,
})

function saveEditor() {
  const draft = editor.value
  if (draft.name) {
    editorSaver.submit({
      doctype: "Paperwork Template",
      name: draft.name,
      fieldname: {
        template_name: draft.template_name.trim(),
        template_source: draft.template_source,
      },
    })
  } else {
    editorCreator.submit({
      doc: {
        doctype: "Paperwork Template",
        template_name: draft.template_name.trim(),
        template_source: draft.template_source,
      },
    })
  }
}

// -- the registry of generated papers --

const papers = createResource({ url: "auraos.api.generated_papers", auto: true })
const paperSearch = ref("")

const filteredPapers = computed(() => {
  const rows = papers.data || []
  const needle = paperSearch.value.toLowerCase()
  if (!needle) return rows
  return rows.filter((row) =>
    [row.template_name, row.file_name, row.job, row.vendor_label, row.freelancer_label]
      .filter(Boolean)
      .some((text) => String(text).toLowerCase().includes(needle))
  )
})
</script>

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

    <!-- The web editor (A5 round 2, a modal since round 4): a document
         window like the tools the founder knows — type the paper, click
         a placeholder to drop it in at the cursor, save; the .docx is
         built server-side. Templates written here stay editable here;
         uploaded ones are edited in Word. -->
    <Dialog
      :modelValue="!!editor"
      :options="{
        title: editor?.name ? 'Edit template' : 'Write a template',
        size: '4xl',
      }"
      @update:modelValue="(open) => !open && (editor = null)"
    >
      <template #body-content>
        <div v-if="editor">
          <input
            v-model="editor.template_name"
            placeholder="Template name — e.g. Hợp đồng cộng tác viên"
            class="mb-2 w-full rounded border-gray-200 px-2 py-1.5 text-sm sm:w-96"
          />
          <!-- Placeholders appear as @chips; typing @ suggests them
               (founder, A5 round 5). Stored back as {{…}} on save. -->
          <!-- relative: the dialog panel is transformed, which hijacks
               position:fixed — the dropdown anchors to the editor box
               instead. -->
          <div class="relative">
            <TextEditor
              ref="editorRef"
              :content="editor.template_source"
              :fixed-menu="true"
              :mentions="mentionItems"
              editor-class="aura-paper prose prose-sm min-h-[24rem] max-h-[55vh] max-w-none overflow-y-auto rounded-b border border-t-0 border-gray-200 px-6 py-4 focus:outline-none"
              @change="(html) => (editor.template_source = html)"
              @transaction="onEditorTransaction"
            />
            <!-- Our own @-suggestions: type @ and keep typing to
                 filter; click inserts the field as a chip. (frappe-ui's
                 built-in popup dies silently inside a modal.) -->
            <div
              v-if="suggest && suggestions.length"
              class="absolute z-[100] max-h-56 w-72 overflow-y-auto rounded-md border bg-white py-1 shadow-lg"
              :style="{ left: `${suggest.x}px`, top: `${suggest.y}px` }"
            >
              <button
                v-for="field in suggestions"
                :key="field"
                class="block w-full truncate px-3 py-1.5 text-left font-mono text-xs text-gray-800 hover:bg-blue-50"
                @mousedown.prevent="pickSuggestion(field)"
              >
                {{ field }}
              </button>
            </div>
          </div>
          <p class="mb-1 mt-2 text-xs font-medium text-gray-600">
            Type <code>@</code> to insert a field, or click one:
          </p>
          <div class="flex max-h-24 flex-wrap gap-1 overflow-y-auto">
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
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button @click="editor = null">Cancel</Button>
          <Button
            variant="solid"
            :disabled="!editor?.template_name.trim() || !editor?.template_source.trim()"
            :loading="editorSaver.loading || editorCreator.loading"
            @click="saveEditor"
          >
            Save template
          </Button>
        </div>
      </template>
    </Dialog>

    <!-- The library -->
    <div
      v-for="row in library.data?.templates || []"
      :key="row.name"
      class="mb-3 rounded-lg border bg-white p-3"
      :class="row.disabled ? 'opacity-60' : ''"
    >
      <div class="flex flex-wrap items-center gap-2">
        <!-- Every title opens a reading window first; edit, print and
             download live inside it (founder, A5 round 5). -->
        <button
          class="font-medium text-blue-700 hover:underline"
          @click="openTemplateWindow(row)"
        >
          {{ row.template_name }}
        </button>
        <a
          :href="row.template_file"
          class="text-gray-400 hover:text-gray-700"
          title="Download the .docx"
        >
          <FeatherIcon name="download" class="h-3.5 w-3.5" />
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
                <button
                  class="text-left font-medium text-blue-700 hover:underline"
                  @click="openPaperWindow(row)"
                >
                  {{ row.template_name || row.file_name }}
                </button>
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

    <!-- The shared reading window: a template or a generated paper,
         read first, acted on inside. -->
    <PaperWindow
      :modelValue="!!paperWindow"
      :title="paperWindow?.title"
      :content="paperWindow?.content || ''"
      :download-url="paperWindow?.downloadUrl || ''"
      :editable="paperWindow?.editable ?? true"
      :edit-inline="paperWindow?.editInline ?? true"
      @update:modelValue="(open) => !open && (paperWindow = null)"
      @edit="onWindowEdit"
    />

    <ErrorMessage class="mt-3" :message="error" />
  </div>
</template>

<script setup>
import { computed, ref } from "vue"
import {
  Button,
  Dialog,
  ErrorMessage,
  FeatherIcon,
  FileUploader,
  TextEditor,
  createResource,
} from "frappe-ui"
import PaperWindow from "../components/PaperWindow.vue"
import { frappeErrorMessage } from "../utils/frappeError"
import { editorToSource, sourceToEditor } from "../utils/placeholders"

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
const editorRef = ref(null)

// Typing @ in the editor suggests every fillable field.
const mentionItems = computed(() =>
  (library.data?.placeholders || []).map((field) => ({
    id: field,
    label: field,
  }))
)

function openEditor(row = null) {
  const source = row?.template_source || ""
  // Legacy plain paragraph lines upgrade to HTML; placeholders become
  // @chips for the editor and go back to {{…}} on save.
  const html = source.trimStart().startsWith("<")
    ? source
    : source
        .split("\n")
        .map((line) => `<p>${line}</p>`)
        .join("")
  editor.value = {
    name: row?.name || null,
    template_name: row?.template_name || "",
    template_source: sourceToEditor(html),
  }
}

function insertPlaceholder(field) {
  const tiptap = editorRef.value?.editor
  if (tiptap) {
    tiptap
      .chain()
      .focus()
      .insertContent({ type: "mention", attrs: { id: field, label: field } })
      .run()
  } else {
    editor.value.template_source += `<p>${braced(field)}</p>`
  }
}

// -- @-suggestions, filtered as the founder types (A5 round 6) --

const suggest = ref(null)

function onEditorTransaction(tiptap) {
  if (!tiptap?.state) return
  const { from, empty } = tiptap.state.selection
  if (!empty) {
    suggest.value = null
    return
  }
  const textBefore = tiptap.state.doc.textBetween(
    Math.max(0, from - 60),
    from,
    "\n",
    "\0"
  )
  const match = textBefore.match(/@([\w.]*)$/)
  if (!match) {
    suggest.value = null
    return
  }
  const coords = tiptap.view.coordsAtPos(from)
  // Anchor to the editor's own box: the dialog is transformed, so
  // viewport coordinates would land the dropdown somewhere else.
  const box = tiptap.view.dom.closest(".relative")?.getBoundingClientRect()
  suggest.value = {
    query: match[1],
    from: from - match[0].length,
    to: from,
    x: coords.left - (box?.left || 0),
    y: coords.bottom - (box?.top || 0) + 6,
  }
}

const suggestions = computed(() => {
  if (!suggest.value) return []
  const needle = suggest.value.query.toLowerCase()
  return (library.data?.placeholders || [])
    .filter((field) => field.toLowerCase().includes(needle))
    .slice(0, 8)
})

function pickSuggestion(field) {
  const tiptap = editorRef.value?.editor
  const range = suggest.value
  suggest.value = null
  if (!tiptap || !range) return
  tiptap
    .chain()
    .focus()
    .deleteRange({ from: range.from, to: range.to })
    .insertContent([
      { type: "mention", attrs: { id: field, label: field } },
      { type: "text", text: " " },
    ])
    .run()
}

// -- the shared reading window (A5 round 5) --

const paperWindow = ref(null)
let pendingTemplate = null
let pendingPaper = null

const templatePreviewer = createResource({
  url: "auraos.api.preview_template",
  onSuccess(data) {
    error.value = ""
    paperWindow.value = {
      title: pendingTemplate?.template_name || "Template",
      content: data.html || "<p>(Không đọc được nội dung file)</p>",
      downloadUrl: data.file_url || "",
      // Editing an uploaded template converts it to a web one (its
      // text and placeholders carry over; Word-only styling doesn't).
      editable: !!library.data?.can_manage,
      editInline: false,
      row: pendingTemplate,
    }
  },
  onError: onFail,
})

function openTemplateWindow(row) {
  pendingTemplate = row
  templatePreviewer.submit({ template: row.name })
}

function onWindowEdit() {
  const win = paperWindow.value
  paperWindow.value = null
  const row = win?.row
  if (!row) return
  if (row.template_source) {
    openEditor(row)
  } else {
    // An uploaded template edited here becomes a web template: the
    // window's extracted text (placeholders included) is the source.
    openEditor({ ...row, template_source: win.content })
  }
}

const paperPreviewer = createResource({
  url: "auraos.api.preview_paper",
  onSuccess(data) {
    error.value = ""
    paperWindow.value = {
      title: pendingPaper?.template_name || pendingPaper?.file_name || "Paper",
      content: data.html || "<p>(File này không phải văn bản .docx)</p>",
      downloadUrl: pendingPaper?.file_url || "",
      editable: true,
      editInline: true,
    }
  },
  onError: onFail,
})

function openPaperWindow(row) {
  pendingPaper = row
  paperPreviewer.submit({ file_url: row.file_url })
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
  // Chips out, {{…}} in — the stored source is the fill pipeline's.
  const source = editorToSource(draft.template_source)
  if (draft.name) {
    editorSaver.submit({
      doctype: "Paperwork Template",
      name: draft.name,
      fieldname: {
        template_name: draft.template_name.trim(),
        template_source: source,
      },
    })
  } else {
    editorCreator.submit({
      doc: {
        doctype: "Paperwork Template",
        template_name: draft.template_name.trim(),
        template_source: source,
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

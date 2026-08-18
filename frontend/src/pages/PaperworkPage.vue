<template>
  <div class="space-y-4">
    <!-- Page head: what this screen is for, in words, before the library. -->
    <div class="flex flex-wrap items-end gap-x-3 gap-y-1">
      <h1 class="text-xl font-semibold text-carbon">Paperwork</h1>
      <p class="text-sm text-muted">
        {{ templateRows.length }} template{{ templateRows.length === 1 ? "" : "s" }} ·
        {{ papers.data?.length || 0 }} paper{{ papers.data?.length === 1 ? "" : "s" }} generated
      </p>
    </div>

    <p class="max-w-3xl text-sm text-muted">
      Design each paper once in Word - letterhead, clauses, signature block
      - and type
      <code class="rounded-[6px] border border-hairline bg-canvas px-1 py-0.5 font-mono text-[11px] text-carbon">{{ EXAMPLE }}</code>
      where a value belongs.
      Generating fills those in and attaches the result to the job.
    </p>

    <!-- Producers see the library read-only; the founder gate is unchanged. -->
    <div
      v-if="library.data && !library.data.can_manage"
      class="aura-card flex items-start gap-2 px-4 py-3 text-sm text-muted"
    >
      <FeatherIcon name="lock" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-faint" />
      <span>
        Only the founder can add or change templates. You can generate
        paperwork from these on any job.
      </span>
    </div>

    <div class="grid gap-3 lg:grid-cols-3">
      <!-- The library -->
      <BentoCard
        class="lg:col-span-2"
        title="Template library"
        subtitle="Open one to read it; edit, print and download live inside."
      >
        <ul v-if="templateRows.length" class="divide-y divide-hairline">
          <li
            v-for="row in templateRows"
            :key="row.name"
            class="py-2.5 first:pt-0 last:pb-0"
            :class="row.disabled ? 'opacity-60' : ''"
          >
            <div class="flex flex-wrap items-center gap-2">
              <FeatherIcon name="file-text" class="h-4 w-4 shrink-0 text-faint" />
              <!-- Every title opens a reading window first; edit, print and
                   download live inside it (founder, A5 round 5). -->
              <button
                class="min-w-0 truncate text-sm font-medium text-carbon hover:text-accent"
                @click="openTemplateWindow(row)"
              >
                {{ row.template_name }}
              </button>
              <StatusPill
                v-if="row.template_source"
                label="Web"
                tone="neutral"
                title="Written in the app - editable right here"
              />
              <StatusPill v-if="row.disabled" label="Retired" tone="warn" />

              <span class="ml-auto flex shrink-0 items-center gap-1">
                <a
                  :href="row.template_file"
                  class="rounded-[8px] p-1.5 text-faint hover:bg-canvas hover:text-carbon"
                  title="Download the .docx"
                >
                  <FeatherIcon name="download" class="h-3.5 w-3.5" />
                </a>
                <template v-if="library.data?.can_manage">
                  <button
                    v-if="row.template_source"
                    :class="ROW_BTN"
                    @click="openEditor(row)"
                  >
                    Edit
                  </button>
                  <button :class="ROW_BTN" @click="setDisabled(row, !row.disabled)">
                    {{ row.disabled ? "Bring back" : "Retire" }}
                  </button>
                  <button :class="DANGER_BTN" @click="remove(row)">Delete</button>
                </template>
              </span>
            </div>

            <p
              v-if="row.unknown_placeholders.length"
              class="mt-2 flex items-start gap-1.5 rounded-[10px] border border-warn/25 bg-warn-soft px-2 py-1.5 text-xs text-warn"
            >
              <FeatherIcon name="alert-triangle" class="mt-0.5 h-3 w-3 shrink-0" />
              <span>
                Asks for {{ row.unknown_placeholders.join(", ") }} - no such
                placeholder, so it prints as a gap marker. Fix the docx and upload
                it again.
              </span>
            </p>

            <div
              v-if="row.placeholders.length"
              class="mt-2 flex flex-wrap items-center gap-1"
            >
              <span class="aura-eyebrow mr-0.5">Fills</span>
              <code
                v-for="field in row.placeholders"
                :key="field"
                class="rounded-[6px] border px-1.5 py-0.5 font-mono text-[11px]"
                :class="
                  row.unknown_placeholders.includes(field)
                    ? 'border-warn/25 bg-warn-soft text-warn'
                    : 'border-hairline bg-canvas text-muted'
                "
              >
                {{ field }}
              </code>
            </div>
            <p v-else class="mt-2 text-xs text-faint">
              No placeholders - this prints exactly as designed.
            </p>
          </li>
        </ul>

        <EmptyState
          v-else-if="library.data"
          icon="file-text"
          title="The library is empty."
          :detail="library.data.can_manage ? 'Upload a .docx, or write one here.' : ''"
        />
      </BentoCard>

      <!-- Right rail: making a template, and the vocabulary it may use. -->
      <div class="space-y-3">
        <BentoCard
          v-if="library.data?.can_manage"
          title="New template"
          subtitle="Upload the Word file, or write one in the app."
        >
          <div class="grid gap-2">
            <label class="block text-xs text-muted">
              Name
              <input
                v-model="name"
                class="mt-1 block w-full rounded-[10px] border border-hairline px-2 py-2 text-sm text-carbon"
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
                <Button class="w-full" :loading="uploading" @click="openFileSelector">
                  {{ uploaded ? "Choose another .docx" : "Choose .docx" }}
                </Button>
              </template>
            </FileUploader>
            <p v-if="uploaded" class="truncate text-xs text-muted">
              {{ uploaded.file_name }}
            </p>
            <Button
              variant="solid"
              :disabled="!name.trim() || !uploaded"
              :loading="creator.loading"
              @click="create"
            >
              Add to library
            </Button>
            <Button v-if="!editor" @click="openEditor()">Write one here</Button>
          </div>
          <template #footer>
            <p class="text-xs text-faint">
              Only .docx - a .doc renamed, or a PDF, is refused when saved.
            </p>
          </template>
        </BentoCard>

        <!-- The cheat sheet: what a template may ask for -->
        <details v-if="library.data" class="aura-card px-4 py-3">
          <summary class="cursor-pointer text-sm font-medium text-carbon">
            Placeholders a template can use ({{ library.data.placeholders.length }})
          </summary>
          <div class="mt-3 grid grid-cols-2 gap-x-3 gap-y-1">
            <code
              v-for="field in library.data.placeholders"
              :key="field"
              class="truncate font-mono text-[11px] text-muted"
            >
              {{ braced(field) }}
            </code>
          </div>
          <p class="mt-3 border-t border-hairline pt-2 text-xs text-faint">
            Our own company name, tax code and address are not on this list -
            they are the same on every paper, so type them into the template.
          </p>
        </details>
      </div>
    </div>

    <!-- The registry (A5 round 2): every paper ever generated, in one
         place - the files themselves hang off their jobs. -->
    <DataTable
      title="Generated papers"
      :count="papers.data?.length || null"
      :columns="paperColumns"
      :rows="filteredPapers"
      empty-title="Nothing generated yet - papers made on a job appear here."
    >
      <template #action>
        <div class="flex items-center gap-1.5 rounded-[10px] border border-hairline px-2 py-1">
          <FeatherIcon name="search" class="h-3.5 w-3.5 shrink-0 text-faint" />
          <input
            v-model.trim="paperSearch"
            placeholder="Search…"
            class="w-32 bg-transparent text-sm text-carbon outline-none placeholder:text-faint sm:w-44"
          />
        </div>
      </template>

      <template #cell-template_name="{ row }">
        <button
          class="min-w-0 truncate text-left text-sm font-medium text-carbon hover:text-accent"
          @click="openPaperWindow(row)"
        >
          {{ row.template_name || row.file_name }}
        </button>
      </template>
      <template #cell-party="{ row }">
        <span class="text-sm text-muted">
          {{ row.freelancer_label || row.vendor_label || "Client" }}
        </span>
      </template>
      <template #cell-job="{ row }">
        <router-link
          :to="`/jobs/${row.job}`"
          class="aura-num text-xs text-muted hover:text-accent"
        >
          {{ row.job }}
        </router-link>
      </template>
      <template #cell-creation="{ row }">
        <span class="aura-num whitespace-nowrap text-xs text-faint">
          {{ row.creation?.slice(0, 16) }}
        </span>
      </template>
    </DataTable>

    <!-- The web editor (A5 round 2, a modal since round 4): a document
         window like the tools the founder knows - type the paper, click
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
        <div v-if="editor" class="space-y-3">
          <input
            v-model="editor.template_name"
            placeholder="Template name - e.g. Hợp đồng cộng tác viên"
            class="w-full rounded-[10px] border border-hairline px-3 py-2 text-sm text-carbon sm:w-96"
          />
          <!-- Placeholders appear as @chips; typing @ suggests them
               (founder, A5 round 5). Stored back as {{…}} on save. -->
          <!-- relative: the dialog panel is transformed, which hijacks
               position:fixed - the dropdown anchors to the editor box
               instead. -->
          <div class="relative">
            <TextEditor
              ref="editorRef"
              :content="editor.template_source"
              :fixed-menu="true"
              :mentions="mentionItems"
              editor-class="aura-paper prose prose-sm min-h-[24rem] max-h-[55vh] max-w-none overflow-y-auto rounded-b-[10px] border border-t-0 border-hairline bg-paper px-6 py-4 focus:outline-none"
              @change="(html) => (editor.template_source = html)"
              @transaction="onEditorTransaction"
            />
            <!-- Our own @-suggestions: type @ and keep typing to
                 filter; click inserts the field as a chip. (frappe-ui's
                 built-in popup dies silently inside a modal.) -->
            <div
              v-if="suggest && suggestions.length"
              class="absolute z-[100] max-h-56 w-72 overflow-y-auto rounded-card border border-hairline bg-paper py-1 shadow-drawer"
              :style="{ left: `${suggest.x}px`, top: `${suggest.y}px` }"
            >
              <button
                v-for="field in suggestions"
                :key="field"
                class="block w-full truncate px-3 py-1.5 text-left font-mono text-xs text-carbon hover:bg-accent-soft hover:text-accent-ink"
                @mousedown.prevent="pickSuggestion(field)"
              >
                {{ field }}
              </button>
            </div>
          </div>

          <div>
            <p class="mb-1.5 text-xs text-muted">
              Type
              <code class="rounded-[4px] border border-hairline bg-canvas px-1 font-mono text-[11px] text-carbon">@</code>
              to insert a field, or click one:
            </p>
            <div class="flex max-h-24 flex-wrap gap-1 overflow-y-auto">
              <button
                v-for="field in library.data?.placeholders || []"
                :key="field"
                class="rounded-[6px] border border-hairline bg-canvas px-1.5 py-0.5 font-mono text-[11px] text-muted hover:border-accent/40 hover:bg-accent-soft hover:text-accent-ink"
                @click="insertPlaceholder(field)"
              >
                {{ field }}
              </button>
            </div>
          </div>
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2 border-t border-hairline pt-3">
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
import BentoCard from "../components/BentoCard.vue"
import DataTable from "../components/DataTable.vue"
import EmptyState from "../components/EmptyState.vue"
import StatusPill from "../components/StatusPill.vue"
import PaperWindow from "../components/PaperWindow.vue"
import { frappeErrorMessage } from "../utils/frappeError"
import { editorToSource, sourceToEditor } from "../utils/placeholders"

const DOCX =
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

// The one row-action button shape, so the library's Edit / Retire / Delete
// read as one control set rather than three.
const ROW_BTN =
  "rounded-[8px] border border-hairline px-2 py-1 text-xs text-muted hover:border-accent/40 hover:text-accent-ink"
const DANGER_BTN =
  "rounded-[8px] border border-accent/30 px-2 py-1 text-xs text-accent-ink hover:bg-accent-soft"

// Placeholder syntax has to be shown, not interpolated - a literal
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

const templateRows = computed(() => library.data?.templates || [])

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
  // this - deleting a template only stops new ones being made from it.
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
  // Chips out, {{…}} in - the stored source is the fill pipeline's.
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

const paperColumns = [
  { key: "template_name", label: "Paper" },
  { key: "party", label: "For", width: "220px" },
  { key: "job", label: "Job", width: "160px" },
  { key: "creation", label: "Generated", width: "160px" },
]

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

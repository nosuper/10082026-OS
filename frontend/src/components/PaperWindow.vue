<template>
  <Dialog
    :modelValue="modelValue"
    :options="{ title, size: '4xl' }"
    @update:modelValue="(open) => $emit('update:modelValue', open)"
  >
    <template #body-content>
      <div v-if="modelValue">
        <p
          v-if="gapCount"
          class="mb-2 flex items-center gap-1.5 text-xs text-amber-700"
        >
          <FeatherIcon name="alert-triangle" class="h-3.5 w-3.5" />
          {{ gapCount }} gap{{ gapCount > 1 ? "s" : "" }} highlighted - fill
          the record, or type over them here.
        </p>

        <!-- Reading first, editing on request (founder, A5 round 5):
             the window opens as the document; Edit swaps in the same
             rich editor everything else uses. -->
        <div
          v-if="mode === 'view'"
          class="aura-paper prose prose-sm max-h-[55vh] min-h-[16rem] max-w-none overflow-y-auto rounded border border-gray-200 px-6 py-4"
          v-html="html"
        ></div>
        <TextEditor
          v-else
          :content="html"
          :fixed-menu="true"
          editor-class="aura-paper prose prose-sm min-h-[16rem] max-h-[55vh] max-w-none overflow-y-auto rounded-b border border-t-0 border-gray-200 px-6 py-4 focus:outline-none"
          @change="(edited) => (html = edited)"
        />
      </div>
    </template>
    <template #actions>
      <div class="flex flex-wrap items-center justify-end gap-2">
        <Button v-if="mode === 'view' && editable" @click="edit">
          {{ editInline ? "Edit" : "Edit template" }}
        </Button>
        <Button @click="print">Print</Button>
        <Button v-if="downloadUrl" :link="downloadUrl">Download</Button>
        <Button
          v-if="saveLabel"
          variant="solid"
          :loading="saving"
          @click="$emit('save', html)"
        >
          {{ saveLabel }}
        </Button>
        <Button @click="$emit('update:modelValue', false)">Close</Button>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { computed, ref, watch } from "vue"
import { Button, Dialog, FeatherIcon, TextEditor } from "frappe-ui"

// One window for every paper-shaped thing: a template, a filled draft,
// a generated document. Opens reading, edits on request, prints what
// is on screen, downloads the stored file when there is one.
const props = defineProps({
  modelValue: Boolean,
  title: { type: String, default: "Paper" },
  content: { type: String, default: "" },
  downloadUrl: { type: String, default: "" },
  // Whether Edit swaps to the inline editor (papers) or asks the
  // parent to open its own editor (web templates → template editor).
  editable: { type: Boolean, default: true },
  editInline: { type: Boolean, default: true },
  saveLabel: { type: String, default: "" },
  saving: Boolean,
})

const emit = defineEmits(["update:modelValue", "save", "edit"])

const mode = ref("view")
const html = ref(props.content)

watch(
  () => [props.modelValue, props.content],
  () => {
    if (props.modelValue) {
      mode.value = "view"
      html.value = props.content
    }
  }
)

const gapCount = computed(() => (html.value.match(/data-gap/g) || []).length)

function edit() {
  if (props.editInline) {
    mode.value = "edit"
  } else {
    emit("edit")
  }
}

function print() {
  const printWindow = window.open("", "_blank")
  if (!printWindow) return
  printWindow.document.write(`<!doctype html><html><head><meta charset="utf-8">
    <title>Print</title>
    <style>
      body { font-family: "Times New Roman", serif; font-size: 13pt;
             line-height: 1.6; max-width: 17cm; margin: 1cm auto; }
      mark[data-gap] { background: #fde68a; }
      h1, h2, h3 { line-height: 1.3; }
      span.mention { font-family: ui-monospace, monospace; background: #f3f4f6;
             padding: 0 2px; border-radius: 2px; }
      table { border-collapse: collapse; width: 100%; margin: 0.4cm 0; }
      td, th { border: 1px solid #6b7280; padding: 0.15cm 0.25cm;
             vertical-align: top; }
      table.borderless td, table.borderless th { border: none; }
      td p { margin: 0; }
    </style></head><body>${html.value}</body></html>`)
  printWindow.document.close()
  printWindow.focus()
  printWindow.print()
}

defineExpose({ currentHtml: () => html.value, edited: () => mode.value === "edit" })
</script>

<style>
.aura-paper mark[data-gap] {
  background-color: #fde68a;
  color: #92400e;
  padding: 0 2px;
  border-radius: 2px;
}
.aura-paper span.mention {
  font-family: ui-monospace, monospace;
  font-size: 0.85em;
  background: #eff6ff;
  color: #1d4ed8;
  padding: 0 3px;
  border-radius: 3px;
}
</style>

<style>
/* Tables read back from Word keep their grid on screen. */
.aura-paper table {
  border-collapse: collapse;
  width: 100%;
  margin: 0.5rem 0;
}
.aura-paper td,
.aura-paper th {
  border: 1px solid #d1d5db;
  padding: 0.35rem 0.6rem;
  vertical-align: top;
}
.aura-paper td p {
  margin: 0;
}
/* A signature block is a borderless table - Word draws nothing, and
   neither do we (checked against the founder's own contracts). */
.aura-paper table.borderless td,
.aura-paper table.borderless th {
  border: none;
}
</style>

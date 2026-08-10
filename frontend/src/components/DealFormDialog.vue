<template>
  <Dialog
    :modelValue="modelValue"
    @update:modelValue="$emit('update:modelValue', $event)"
    :options="{ title: name ? 'Edit Deal' : 'New Deal', size: 'xl' }"
  >
    <template #body-content>
      <div v-if="loading" class="py-8 text-center text-sm text-gray-500">
        Loading…
      </div>
      <div v-else class="space-y-4">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormControl
            type="text"
            label="Title"
            v-model="form.title"
            required
          />
          <FormControl
            type="select"
            label="Owner"
            :options="ownerOptions"
            v-model="form.deal_owner"
            required
          />
          <FormControl
            type="autocomplete"
            label="Company"
            :options="companyOptions"
            v-model="companySelection"
            placeholder="Select company"
            required
          />
          <FormControl
            type="autocomplete"
            label="Contact"
            :options="contactOptions"
            v-model="contactSelection"
            placeholder="No contact"
          />
        </div>
        <FormControl
          type="textarea"
          label="Brief"
          v-model="form.brief"
          :rows="5"
        />

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormControl
            type="number"
            label="Est. Client Budget (VND)"
            v-model="form.estimated_budget"
            :min="0"
          />
          <FormControl
            type="select"
            label="Source"
            :options="sourceOptions"
            v-model="form.source"
          />
          <FormControl
            type="select"
            label="Project Type"
            :options="projectTypeOptions"
            v-model="form.project_type"
          />
          <div>
            <div class="mb-1.5 text-xs text-gray-600">Tags</div>
            <div class="flex flex-wrap items-center gap-1.5">
              <span
                v-for="(row, i) in form.deal_tags || []"
                :key="row.deal_tag"
                class="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700"
              >
                {{ row.deal_tag }}
                <button
                  class="text-gray-400 hover:text-gray-700"
                  title="Remove tag"
                  @click="form.deal_tags.splice(i, 1)"
                >
                  ×
                </button>
              </span>
            </div>
            <div class="mt-1.5 flex gap-1.5">
              <input
                v-model="tagInput"
                list="deal-tag-options"
                placeholder="Add tag"
                class="w-full rounded border-gray-300 py-1.5 text-sm placeholder-gray-500 focus:border-gray-500 focus:ring-0"
                @keydown.enter.prevent="addTag"
              />
              <datalist id="deal-tag-options">
                <option
                  v-for="tag in unusedTags"
                  :key="tag.name"
                  :value="tag.name"
                />
              </datalist>
              <Button @click="addTag" :loading="creatingTag">Add</Button>
            </div>
            <ErrorMessage class="mt-1" :message="tagError" />
          </div>
        </div>

        <!-- Links -->
        <div class="border-t pt-3">
          <div class="mb-2 text-xs font-medium text-gray-700">Links</div>
          <div
            v-for="(row, i) in form.deal_links || []"
            :key="`${row.url}-${i}`"
            class="flex items-center gap-2 py-0.5 text-sm"
          >
            <a
              :href="row.url"
              target="_blank"
              rel="noopener noreferrer"
              class="text-blue-600 underline"
            >
              {{ row.label }}
            </a>
            <span class="truncate text-xs text-gray-400">{{ row.url }}</span>
            <button
              class="ml-auto text-gray-400 hover:text-gray-700"
              title="Remove link"
              @click="form.deal_links.splice(i, 1)"
            >
              ×
            </button>
          </div>
          <div class="mt-1.5 flex gap-1.5">
            <input
              v-model="linkLabel"
              placeholder="Label (e.g. Drive folder)"
              class="w-2/5 rounded border-gray-300 py-1.5 text-sm placeholder-gray-500 focus:border-gray-500 focus:ring-0"
            />
            <input
              v-model="linkUrl"
              placeholder="https://…"
              class="w-3/5 rounded border-gray-300 py-1.5 text-sm placeholder-gray-500 focus:border-gray-500 focus:ring-0"
              @keydown.enter.prevent="addLink"
            />
            <Button @click="addLink">Add</Button>
          </div>
          <ErrorMessage class="mt-1" :message="linkError" />
        </div>

        <!-- Attachments (existing deals only — files attach to a saved doc) -->
        <div v-if="name" class="border-t pt-3">
          <div class="mb-2 flex items-center text-xs font-medium text-gray-700">
            Attachments
            <FileUploader
              class="ml-auto"
              :upload-args="{ doctype: 'Deal', docname: name, private: true }"
              @success="attachments.reload()"
            >
              <template #default="{ uploading, progress, openFileSelector, error }">
                <Button @click="openFileSelector" :loading="uploading">
                  {{ uploading ? `Uploading ${progress}%` : "Attach file" }}
                </Button>
              </template>
            </FileUploader>
          </div>
          <div
            v-for="file in attachments.data || []"
            :key="file.name"
            class="flex items-center gap-2 py-0.5 text-sm"
          >
            <a
              :href="file.file_url"
              target="_blank"
              rel="noopener noreferrer"
              class="text-blue-600 underline"
            >
              {{ file.file_name || file.file_url }}
            </a>
            <span class="text-xs text-gray-400">
              {{ formatSize(file.file_size) }}
            </span>
          </div>
          <div
            v-if="!(attachments.data || []).length"
            class="text-xs text-gray-400"
          >
            No files yet.
          </div>
        </div>

        <!-- Comments (existing deals only) -->
        <div v-if="name" class="border-t pt-3">
          <div class="mb-2 text-xs font-medium text-gray-700">Comments</div>
          <div class="space-y-2">
            <div
              v-for="comment in comments.data || []"
              :key="comment.name"
              class="rounded-md bg-gray-50 px-3 py-2"
            >
              <div class="flex gap-2 text-xs text-gray-500">
                <span class="font-medium text-gray-700">
                  {{ comment.comment_by || comment.comment_email }}
                </span>
                <span class="tabular-nums">
                  {{ comment.creation?.slice(0, 16) }}
                </span>
              </div>
              <!-- Comment content is server-sanitized HTML; render as text -->
              <div class="mt-0.5 whitespace-pre-line text-sm text-gray-800">
                {{ stripHtml(comment.content) }}
              </div>
            </div>
          </div>
          <div class="mt-2 flex gap-1.5">
            <input
              v-model="commentInput"
              placeholder="Write a comment"
              class="w-full rounded border-gray-300 py-1.5 text-sm placeholder-gray-500 focus:border-gray-500 focus:ring-0"
              @keydown.enter.prevent="postComment"
            />
            <Button
              variant="subtle"
              :loading="addComment.loading"
              @click="postComment"
            >
              Comment
            </Button>
          </div>
          <ErrorMessage class="mt-1" :message="commentError" />
        </div>

        <div v-if="stageHistory.length">
          <div class="mb-2 border-t pt-3 text-xs font-medium text-gray-700">
            Stage History
          </div>
          <div class="space-y-1">
            <div
              v-for="entry in stageHistory"
              :key="entry.name"
              class="flex gap-2 text-xs text-gray-600"
            >
              <span class="w-36 shrink-0 tabular-nums">
                {{ entry.changed_on?.slice(0, 16) }}
              </span>
              <span>
                {{ entry.from_stage ? `${entry.from_stage} → ` : "" }}
                <span class="font-medium text-gray-800">{{ entry.to_stage }}</span>
                <span class="text-gray-400"> — {{ entry.changed_by }}</span>
              </span>
            </div>
          </div>
        </div>

        <ErrorMessage :message="saveError" />
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button @click="$emit('update:modelValue', false)">Cancel</Button>
        <Button variant="solid" :loading="saving" @click="save">
          {{ name ? "Save" : "Create" }}
        </Button>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, computed, watch } from "vue"
import {
  Dialog,
  Button,
  FormControl,
  FileUploader,
  ErrorMessage,
  createResource,
  createListResource,
} from "frappe-ui"

const props = defineProps({
  modelValue: Boolean,
  // null → create a new deal
  name: { type: String, default: null },
  // [{name, full_name}] from auraos.api.operating_users
  owners: { type: Array, default: () => [] },
})
const emit = defineEmits(["update:modelValue", "saved"])

const form = ref({})
const companySelection = ref(null)
const contactSelection = ref(null)
const loading = ref(false)
const saving = ref(false)
const saveError = ref("")
// The server copy of an existing doc; edits are overlaid on save so
// name/modified/stage_history survive the round trip.
let serverDoc = null
const stageHistory = ref([])

const ownerOptions = computed(() => [
  { label: "", value: "" },
  ...props.owners.map((u) => ({
    label: u.full_name || u.name,
    value: u.name,
  })),
])

const companies = createListResource({
  doctype: "Party Company",
  fields: ["name", "company_name"],
  orderBy: "company_name asc",
  pageLength: 500,
})

const companyOptions = computed(() =>
  (companies.data || []).map((c) => ({
    label: c.company_name,
    value: c.name,
  }))
)

const contacts = createListResource({
  doctype: "Party Contact",
  fields: ["name", "full_name", "company"],
  orderBy: "full_name asc",
  pageLength: 500,
})

// Only people of the selected company (T3 walkthrough decision);
// no company chosen yet → all contacts.
const contactOptions = computed(() => {
  const company = companySelection.value?.value
  const all = contacts.data || []
  return (company ? all.filter((c) => c.company === company) : all).map(
    (c) => ({ label: c.full_name, value: c.name })
  )
})

// Switching company invalidates a contact from the previous one.
// Judge from the loaded contact record itself — while the list is
// still fetching we must not wipe a valid saved contact.
watch(companySelection, (selected) => {
  const contact = (contacts.data || []).find(
    (c) => c.name === contactSelection.value?.value
  )
  if (contact && selected?.value && contact.company !== selected.value) {
    contactSelection.value = null
  }
})

// -- details vocabularies (T3.2, issue #21) --

const sources = createListResource({
  doctype: "Deal Source",
  fields: ["name"],
  orderBy: "name asc",
  pageLength: 500,
})

const projectTypes = createListResource({
  doctype: "Project Type",
  fields: ["name"],
  orderBy: "name asc",
  pageLength: 500,
})

const asSelectOptions = (resource) => [
  { label: "", value: "" },
  ...(resource.data || []).map((row) => ({ label: row.name, value: row.name })),
]

const sourceOptions = computed(() => asSelectOptions(sources))
const projectTypeOptions = computed(() => asSelectOptions(projectTypes))

// -- tags --

const tags = createListResource({
  doctype: "Deal Tag",
  fields: ["name"],
  orderBy: "name asc",
  pageLength: 500,
})

const tagInput = ref("")
const tagError = ref("")
const creatingTag = ref(false)

const unusedTags = computed(() => {
  const used = new Set((form.value.deal_tags || []).map((r) => r.deal_tag))
  return (tags.data || []).filter((t) => !used.has(t.name))
})

const createTag = createResource({ url: "frappe.client.insert" })

async function addTag() {
  const value = tagInput.value.trim()
  if (!value) return
  tagError.value = ""
  form.value.deal_tags ||= []
  if (form.value.deal_tags.some((r) => r.deal_tag === value)) {
    tagInput.value = ""
    return
  }
  // Unknown tag → create it first (grow-in vocabulary, both roles may)
  const known = (tags.data || []).some((t) => t.name === value)
  if (!known) {
    creatingTag.value = true
    try {
      await createTag.submit({
        doc: { doctype: "Deal Tag", tag_name: value },
      })
      tags.reload()
    } catch (err) {
      tagError.value = err.messages?.join("\n") || err.message
      return
    } finally {
      creatingTag.value = false
    }
  }
  form.value.deal_tags.push({ deal_tag: value })
  tagInput.value = ""
}

// -- links --

const linkLabel = ref("")
const linkUrl = ref("")
const linkError = ref("")

function addLink() {
  const label = linkLabel.value.trim()
  const url = linkUrl.value.trim()
  linkError.value = ""
  if (!label || !url) {
    linkError.value = "A link needs both a label and a URL"
    return
  }
  form.value.deal_links ||= []
  form.value.deal_links.push({ label, url })
  linkLabel.value = ""
  linkUrl.value = ""
}

// -- comments & attachments (persisted rows; existing deals only) --

const comments = createResource({ url: "auraos.api.deal_comments" })
const attachments = createResource({ url: "auraos.api.deal_attachments" })

const commentInput = ref("")
const commentError = ref("")

const addComment = createResource({
  url: "auraos.api.add_deal_comment",
  onSuccess() {
    commentInput.value = ""
    comments.reload()
  },
  onError(err) {
    commentError.value = err.messages?.join("\n") || err.message
  },
})

function postComment() {
  if (!commentInput.value.trim()) return
  commentError.value = ""
  addComment.submit({ deal: props.name, content: commentInput.value })
}

function stripHtml(html) {
  const el = document.createElement("div")
  el.innerHTML = html || ""
  return el.textContent
}

function formatSize(bytes) {
  if (!bytes) return ""
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const fetchDoc = createResource({
  url: "frappe.client.get",
  onSuccess(doc) {
    serverDoc = doc
    stageHistory.value = doc.stage_history || []
    form.value = { ...doc }
    companySelection.value = doc.company
      ? { label: labelFor(companies, doc.company, "company_name"), value: doc.company }
      : null
    contactSelection.value = doc.contact
      ? { label: labelFor(contacts, doc.contact, "full_name"), value: doc.contact }
      : null
    loading.value = false
  },
  onError() {
    loading.value = false
  },
})

function labelFor(resource, name, field) {
  const match = (resource.data || []).find((row) => row.name === name)
  return match?.[field] || name
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    saveError.value = ""
    tagError.value = ""
    linkError.value = ""
    commentError.value = ""
    tagInput.value = ""
    linkLabel.value = ""
    linkUrl.value = ""
    commentInput.value = ""
    serverDoc = null
    stageHistory.value = []
    form.value = {}
    companySelection.value = null
    contactSelection.value = null
    companies.fetch()
    contacts.fetch()
    sources.fetch()
    projectTypes.fetch()
    tags.fetch()
    if (props.name) {
      loading.value = true
      fetchDoc.fetch({ doctype: "Deal", name: props.name })
      comments.fetch({ deal: props.name })
      attachments.fetch({ deal: props.name })
    } else {
      comments.reset()
      attachments.reset()
    }
  }
)

function onSaveSuccess() {
  saving.value = false
  emit("update:modelValue", false)
  emit("saved")
}

function onSaveError(err) {
  saving.value = false
  saveError.value = err.messages?.join("\n") || err.message
}

const saveResource = createResource({
  url: "frappe.client.save",
  onSuccess: onSaveSuccess,
  onError: onSaveError,
})

const insertResource = createResource({
  url: "frappe.client.insert",
  onSuccess: onSaveSuccess,
  onError: onSaveError,
})

function save() {
  saving.value = true
  saveError.value = ""
  const doc = {
    ...(serverDoc || {}),
    ...form.value,
    doctype: "Deal",
    company: companySelection.value?.value || null,
    contact: contactSelection.value?.value || null,
  }
  if (props.name) {
    saveResource.submit({ doc })
  } else {
    insertResource.submit({ doc })
  }
}
</script>

<!--
  Every file hanging on a deal, in one place.

  Files arrive through a deal card - that is where someone has the deal
  open and knows what the file is - so this page lists and manages
  rather than uploads. What it adds is the view a card cannot give: the
  brief you remember attaching but not to which deal.

  Each row says whether the file is private. Today they all are, and
  only a signed-in seat can open one; the column is here because client
  sharing is the next thing the founder asked for, and a page that
  assumed "private" everywhere would have to be unpicked to get it.
-->
<template>
  <div class="px-4 py-6">
    <div class="mb-4 flex flex-wrap items-center gap-2">
      <h1 class="text-lg font-semibold text-gray-900">Files</h1>
      <span class="text-sm tabular-nums text-gray-400">{{ rows.length }}</span>
      <div class="relative ml-2">
        <FeatherIcon
          name="search"
          class="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400"
        />
        <input
          v-model.trim="query"
          type="text"
          placeholder="Search files"
          class="w-56 rounded-md border-gray-300 py-1.5 pl-8 text-sm placeholder-gray-500 focus:border-gray-500 focus:ring-0"
        />
      </div>
      <span class="ml-auto text-sm text-gray-500">
        Attached from deal cards. Links open for signed-in seats only.
      </span>
    </div>

    <div class="mb-3 flex flex-wrap items-end gap-3">
      <FormControl
        type="select"
        label="Deal"
        class="w-56"
        :options="dealOptions"
        v-model="filters.deal"
      />
      <FormControl
        type="select"
        label="Type"
        class="w-32"
        :options="typeOptions"
        v-model="filters.file_type"
      />
      <FormControl
        type="select"
        label="Uploaded by"
        class="w-48"
        :options="uploaderOptions"
        v-model="filters.uploader"
      />
      <Button v-if="anyFilter" variant="subtle" @click="clearFilters">
        Clear
      </Button>
    </div>

    <div class="overflow-x-auto rounded-lg border bg-white">
      <table class="min-w-full text-sm">
        <thead class="border-b bg-gray-50 text-xs text-gray-600">
          <tr>
            <th class="px-3 py-2 text-left font-medium">File</th>
            <th class="px-3 py-2 text-left font-medium">Deal</th>
            <th class="px-3 py-2 text-left font-medium">Type</th>
            <th class="px-3 py-2 text-right font-medium">Size</th>
            <th class="px-3 py-2 text-left font-medium">Uploaded by</th>
            <th class="px-3 py-2 text-left font-medium">When</th>
            <th class="px-3 py-2 text-right font-medium"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="file in rows" :key="file.name" class="border-b last:border-0">
            <td class="px-3 py-2">
              <div v-if="renaming === file.name" class="flex items-center gap-1.5">
                <input
                  v-model="renameTo"
                  class="w-64 rounded border-gray-300 py-1 text-sm focus:border-gray-500 focus:ring-0"
                  @keydown.enter.prevent="saveRename(file)"
                  @keydown.esc="renaming = null"
                />
                <Button
                  variant="solid"
                  :loading="renameFile.loading"
                  @click="saveRename(file)"
                >
                  Save
                </Button>
                <Button @click="renaming = null">Cancel</Button>
              </div>
              <a
                v-else
                :href="file.file_url"
                target="_blank"
                rel="noopener noreferrer"
                class="text-blue-600 underline"
              >
                {{ file.file_name || file.file_url }}
              </a>
            </td>
            <td class="px-3 py-2">
              <router-link
                :to="`/deals?deal=${file.deal}`"
                class="text-gray-800 hover:underline"
              >
                {{ file.deal_title || file.deal }}
              </router-link>
            </td>
            <td class="px-3 py-2 text-gray-600">
              {{ file.file_type || "—" }}
              <span
                v-if="!file.is_private"
                class="ml-1 rounded-full bg-amber-50 px-1.5 py-0.5 text-xs text-amber-800"
                title="Anyone with the link can open this file"
              >
                public
              </span>
            </td>
            <td class="px-3 py-2 text-right tabular-nums text-gray-600">
              {{ formatSize(file.file_size) }}
            </td>
            <td class="px-3 py-2 text-gray-600">{{ file.uploader_name }}</td>
            <td class="px-3 py-2 tabular-nums text-gray-500">
              {{ file.creation?.slice(0, 10) }}
            </td>
            <td class="whitespace-nowrap px-3 py-2 text-right">
              <template v-if="confirming === file.name">
                <button
                  class="rounded px-1.5 py-0.5 text-xs font-medium text-red-700 hover:bg-red-50"
                  @click="remove(file)"
                >
                  Delete for good
                </button>
                <button
                  class="rounded px-1.5 py-0.5 text-xs text-gray-600 hover:bg-gray-100"
                  @click="confirming = null"
                >
                  Keep
                </button>
              </template>
              <template v-else>
                <button
                  class="rounded px-1.5 py-0.5 text-xs text-gray-600 hover:bg-gray-100"
                  @click="startRename(file)"
                >
                  Rename
                </button>
                <button
                  class="rounded px-1.5 py-0.5 text-xs text-gray-600 hover:bg-gray-100"
                  @click="((confirming = file.name), (renaming = null))"
                >
                  Delete
                </button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>

      <p v-if="!rows.length" class="py-8 text-center text-sm text-gray-400">
        {{
          files.data
            ? anyFilter || query
              ? "No files match these filters."
              : "No files yet - attach one from a deal card."
            : "Loading…"
        }}
      </p>
    </div>

    <ErrorMessage class="mt-2" :message="error" />
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue"
import {
  Button,
  ErrorMessage,
  FeatherIcon,
  FormControl,
  createResource,
} from "frappe-ui"
import { frappeErrorMessage } from "../utils/frappeError"

const error = ref("")
const query = ref("")
const renaming = ref(null)
const renameTo = ref("")
const confirming = ref(null)

const filters = reactive({ deal: "", file_type: "", uploader: "" })

const files = createResource({
  url: "auraos.api.deal_files",
  onSuccess() {
    error.value = ""
    renaming.value = null
    confirming.value = null
  },
  onError(err) {
    error.value = frappeErrorMessage(err)
  },
})

function load() {
  files.fetch({ ...filters })
}

load()
watch(filters, load)

// The dropdowns are built from the unfiltered set the server also
// returns, so choosing one filter never empties the others.
const dealOptions = computed(() => [
  { label: "All deals", value: "" },
  ...(files.data?.deals || []).map((deal) => ({
    label: deal.title,
    value: deal.name,
  })),
])

const typeOptions = computed(() => [
  { label: "All types", value: "" },
  ...(files.data?.file_types || []).map((type) => ({
    label: type,
    value: type,
  })),
])

const uploaderOptions = computed(() => [
  { label: "Anyone", value: "" },
  ...(files.data?.uploaders || []).map((user) => ({
    label: user.full_name,
    value: user.name,
  })),
])

const anyFilter = computed(() =>
  Boolean(filters.deal || filters.file_type || filters.uploader)
)

function clearFilters() {
  filters.deal = ""
  filters.file_type = ""
  filters.uploader = ""
}

// Search is on the rows already fetched: the filters above are the
// server's job, the needle is a scan of what's on screen.
const rows = computed(() => {
  const needle = query.value.toLowerCase()
  const all = files.data?.files || []
  if (!needle) return all
  return all.filter((file) =>
    [file.file_name, file.deal_title, file.deal, file.uploader_name]
      .filter(Boolean)
      .some((text) => String(text).toLowerCase().includes(needle))
  )
})

function formatSize(bytes) {
  if (!bytes) return ""
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const renameFile = createResource({
  url: "auraos.api.rename_deal_file",
  onSuccess: load,
  onError(err) {
    error.value = frappeErrorMessage(err)
  },
})

const deleteFile = createResource({
  url: "auraos.api.delete_deal_file",
  onSuccess: load,
  onError(err) {
    error.value = frappeErrorMessage(err)
  },
})

function startRename(file) {
  confirming.value = null
  renaming.value = file.name
  renameTo.value = file.file_name || ""
}

function saveRename(file) {
  if (!renameTo.value.trim()) return
  error.value = ""
  renameFile.submit({ file: file.name, file_name: renameTo.value })
}

function remove(file) {
  error.value = ""
  deleteFile.submit({ file: file.name })
}
</script>

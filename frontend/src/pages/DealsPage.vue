<template>
  <div class="px-4 py-6">
    <div class="mb-4 flex items-center gap-3">
      <h1 class="text-lg font-semibold text-gray-900">Deals</h1>
      <div class="ml-auto flex items-center gap-2">
        <div class="flex rounded-md bg-gray-100 p-0.5">
          <button
            v-for="mode in ['Board', 'Table']"
            :key="mode"
            class="rounded px-2.5 py-1 text-sm"
            :class="
              view === mode
                ? 'bg-white font-medium text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            "
            @click="setView(mode)"
          >
            {{ mode }}
          </button>
        </div>
        <Button variant="solid" @click="openNew">New Deal</Button>
      </div>
    </div>

    <div v-if="view === 'Board'" class="flex gap-3 overflow-x-auto pb-4">
      <div
        v-for="stage in STAGES"
        :key="stage.value"
        class="flex w-64 shrink-0 flex-col rounded-lg bg-gray-100"
        @dragover.prevent
        @drop="onDrop(stage.value)"
      >
        <div
          class="flex items-center gap-2 px-3 py-2 text-sm font-medium"
          :class="stage.headerClass"
        >
          {{ stage.label }}
          <span class="text-xs font-normal text-gray-500">
            {{ dealsByStage[stage.value]?.length || 0 }}
          </span>
        </div>
        <div class="flex min-h-24 flex-1 flex-col gap-2 px-2 pb-2">
          <div
            v-for="deal in dealsByStage[stage.value]"
            :key="deal.name"
            class="cursor-grab rounded-md border bg-white p-3 shadow-sm hover:border-gray-400"
            draggable="true"
            @dragstart="dragged = deal"
            @dragend="dragged = null"
            @click="openEdit(deal)"
          >
            <div class="text-sm font-medium text-gray-900">
              {{ deal.title }}
            </div>
            <div v-if="deal.company" class="mt-0.5 text-xs text-gray-600">
              {{ companyNames[deal.company] || deal.company }}
            </div>
            <div class="mt-2 flex items-center gap-1.5">
              <span
                class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700"
              >
                {{ ownerLabel(deal.deal_owner) }}
              </span>
              <span
                v-if="deal.stage === 'Lost' && deal.lost_reason"
                class="rounded-full bg-red-50 px-2 py-0.5 text-xs text-red-700"
              >
                {{ deal.lost_reason }}
              </span>
              <span
                v-if="silentDeals[deal.name]"
                class="rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-800"
                :title="`Quote sent ${silentDeals[deal.name].quote_sent_on?.slice(0, 10)} — no reply after ${silence.data?.silence_days} days`"
              >
                ⏰ Silent
              </span>
              <a
                v-if="quoteLinks[deal.name]"
                :href="quoteLinks[deal.name].url"
                target="_blank"
                rel="noopener"
                class="rounded px-1.5 py-0.5 text-xs text-blue-700 hover:bg-blue-50"
                :title="`Open the client's quote page (v${quoteLinks[deal.name].version})`"
                @click.stop
              >
                🔗 v{{ quoteLinks[deal.name].version }}
              </a>
              <button
                class="ml-auto rounded px-1.5 py-0.5 text-xs text-blue-700 hover:bg-blue-50"
                title="Breakdown & Quote"
                @click.stop="openBreakdown(deal)"
              >
                ₫ Breakdown
              </button>
              <button
                v-if="deal.stage === 'Won'"
                class="rounded px-1.5 py-0.5 text-xs text-green-700 hover:bg-green-50"
                :title="jobFor(deal) ? 'Open the job' : 'Create the job'"
                @click.stop="openOrCreateJob(deal)"
              >
                {{ jobFor(deal) ? "Job →" : "+ Job" }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else>
      <div class="mb-2 flex justify-end">
        <details class="relative">
          <summary
            class="cursor-pointer select-none rounded-md border bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
          >
            Columns
          </summary>
          <div
            class="absolute right-0 z-10 mt-1 w-48 rounded-md border bg-white p-2 shadow-lg"
          >
            <label
              v-for="col in COLUMNS"
              :key="col.key"
              class="flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-sm hover:bg-gray-50"
            >
              <input
                type="checkbox"
                :checked="visibleColumnKeys.includes(col.key)"
                :disabled="col.required"
                @change="toggleColumn(col.key)"
              />
              {{ col.label }}
            </label>
          </div>
        </details>
      </div>

      <div class="overflow-x-auto rounded-lg border">
        <table class="w-full text-sm">
        <thead>
          <tr class="border-b bg-gray-50 text-left text-xs text-gray-600">
            <th
              v-for="col in visibleColumns"
              :key="col.key"
              class="cursor-pointer select-none whitespace-nowrap px-3 py-2 font-medium hover:text-gray-900"
              @click="sortBy(col.key)"
            >
              {{ col.label }}
              <span v-if="sortKey === col.key">
                {{ sortDir === "asc" ? "↑" : "↓" }}
              </span>
            </th>
            <th class="whitespace-nowrap px-3 py-2 font-medium">Action</th>
          </tr>
        </thead>
        <tbody>
          <tr class="border-b bg-blue-50/40 align-top">
            <td
              v-for="col in visibleColumns"
              :key="col.key"
              class="min-w-32 px-2 py-1.5"
            >
              <select
                v-if="col.editable && col.type === 'select'"
                v-model="newDeal[col.key]"
                class="w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm"
              >
                <option
                  v-for="option in optionsFor(col.key)"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>
              <input
                v-else-if="col.editable"
                v-model="newDeal[col.key]"
                :type="col.type === 'number' ? 'number' : 'text'"
                :placeholder="col.key === 'tags' ? 'tag, tag' : col.label"
                class="w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm"
                @keydown.enter="createFromTable"
              />
              <span v-else class="text-gray-300">—</span>
            </td>
            <td class="whitespace-nowrap px-2 py-1.5">
              <Button
                variant="solid"
                :loading="createTableRow.loading"
                @click="createFromTable"
              >
                Add
              </Button>
            </td>
          </tr>
          <tr
            v-for="deal in sortedDeals"
            :key="deal.name"
            class="border-b last:border-b-0 hover:bg-gray-50"
          >
            <td
              v-for="col in visibleColumns"
              :key="col.key"
              class="min-w-32 px-3 py-2 text-gray-700"
              :class="col.editable && col.key !== 'title' ? 'cursor-text' : ''"
              @click="startEditing(deal, col)"
            >
              <template v-if="isEditing(deal, col)">
                <select
                  v-if="col.type === 'select'"
                  v-model="editing.value"
                  class="w-full rounded border border-blue-400 bg-white px-2 py-1 text-sm"
                  autofocus
                  @click.stop
                  @change="saveInline"
                  @keydown.esc="cancelEditing"
                >
                  <option
                    v-for="option in optionsFor(col.key)"
                    :key="option.value"
                    :value="option.value"
                  >
                    {{ option.label }}
                  </option>
                </select>
                <input
                  v-else
                  v-model="editing.value"
                  :type="col.type === 'number' ? 'number' : 'text'"
                  class="w-full rounded border border-blue-400 bg-white px-2 py-1 text-sm"
                  autofocus
                  @click.stop
                  @change="saveInline"
                  @keydown.enter.prevent="$event.target.blur()"
                  @keydown.esc="cancelEditing"
                />
              </template>
              <template v-else-if="col.key === 'title'">
                <button
                  class="font-medium text-blue-700 hover:underline"
                  @click.stop="openEdit(deal)"
                >
                  {{ deal.title }}
                </button>
                <button
                  class="ml-2 text-xs text-gray-400 hover:text-gray-700"
                  title="Edit title inline"
                  @click.stop="startEditing(deal, col, true)"
                >
                  ✎
                </button>
              </template>
              <span
                v-else-if="col.key === 'stage'"
                class="whitespace-nowrap rounded-full px-2 py-0.5 text-xs"
                :class="stageClass(deal.stage)"
              >
                {{ deal.stage }}
              </span>
              <template v-else-if="col.key === 'tags'">
                <span
                  v-for="tag in tagsFor(deal)"
                  :key="tag"
                  class="mr-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700"
                >
                  {{ tag }}
                </span>
              </template>
              <template v-else-if="col.key === 'quote_status'">
                {{ deal.quote_status === "Not Sent" ? "" : deal.quote_status }}
                <span
                  v-if="silentDeals[deal.name]"
                  class="ml-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-800"
                >
                  ⏰ Silent
                </span>
              </template>
              <span v-else-if="col.key === 'company'">
                {{ companyNames[deal.company] || deal.company }}
              </span>
              <span v-else-if="col.key === 'deal_owner'">
                {{ ownerLabel(deal.deal_owner) }}
              </span>
              <span v-else-if="col.key === 'estimated_budget'" class="tabular-nums">
                {{ formatBudget(deal.estimated_budget) }}
              </span>
              <span v-else-if="col.key === 'modified'" class="whitespace-nowrap tabular-nums text-gray-500">
                {{ deal.modified?.slice(0, 16) }}
              </span>
              <span v-else>{{ deal[col.key] }}</span>
            </td>
            <td class="whitespace-nowrap px-3 py-2 text-xs text-gray-400">
              Click a cell to edit
            </td>
          </tr>
          <tr v-if="!sortedDeals.length">
            <td
              :colspan="visibleColumns.length + 1"
              class="px-3 py-6 text-center text-gray-400"
            >
              No deals yet.
            </td>
          </tr>
        </tbody>
        </table>
      </div>
    </div>

    <ErrorMessage class="mt-2" :message="moveError || tableError" />

    <DealFormDialog
      v-model="dialogOpen"
      :name="dialogName"
      :owners="owners"
      @saved="onSaved"
    />

    <LostReasonDialog
      v-model="lostDialogOpen"
      :deal-title="pendingLost?.title || ''"
      @confirm="markLost"
    />

    <Dialog
      v-model="jobOfferOpen"
      :options="{ title: `“${pendingJob?.title || ''}” is won` }"
    >
      <template #body-content>
        <p class="text-sm text-gray-700">
          Create the job now? It carries the breakdown, packages and links
          across, so nothing is re-entered.
        </p>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button @click="jobOfferOpen = false">Not yet</Button>
          <Button
            variant="solid"
            :loading="createJob.loading"
            @click="confirmJobCreation"
          >
            Create job
          </Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, computed } from "vue"
import { useRouter } from "vue-router"
import {
  Button,
  Dialog,
  ErrorMessage,
  createResource,
  createListResource,
} from "frappe-ui"
import DealFormDialog from "../components/DealFormDialog.vue"
import LostReasonDialog from "../components/LostReasonDialog.vue"
import { frappeErrorMessage } from "../utils/frappeError"
import { vnd } from "../utils/money"

// The agreed pipeline, in board order (spec issue #2, story 3).
const STAGES = [
  { label: "Brief Received", value: "Brief Received" },
  { label: "De-brief", value: "De-brief" },
  { label: "Breakdown", value: "Breakdown" },
  { label: "Quote Sent", value: "Quote Sent" },
  { label: "Negotiation", value: "Negotiation" },
  { label: "Won", value: "Won", headerClass: "text-green-700" },
  { label: "Lost", value: "Lost", headerClass: "text-red-700" },
]

const deals = createListResource({
  doctype: "Deal",
  fields: [
    "name",
    "title",
    "stage",
    "deal_owner",
    "company",
    "lost_reason",
    "estimated_budget",
    "source",
    "project_type",
    "quote_status",
    "quote_sent_on",
    "modified",
  ],
  orderBy: "modified desc",
  pageLength: 500,
  auto: true,
})

// Quotes that have gone unanswered past the company's silence window
// (spec #2, story 6) — the deal-killer the board is meant to surface.
const silence = createResource({
  url: "auraos.api.silent_quote_deals",
  auto: true,
})

const silentDeals = computed(() => {
  const map = {}
  for (const deal of silence.data?.deals || []) map[deal.name] = deal
  return map
})

// The link to hand a client, straight off the card (T6 walkthrough).
const quoteLinkMap = createResource({
  url: "auraos.api.deal_quote_links",
  auto: true,
})

const quoteLinks = computed(() => quoteLinkMap.data || {})

const companies = createListResource({
  doctype: "Party Company",
  fields: ["name", "company_name"],
  pageLength: 500,
  auto: true,
})

const sources = createListResource({
  doctype: "Deal Source",
  fields: ["name"],
  orderBy: "name asc",
  pageLength: 500,
  auto: true,
})

const projectTypes = createListResource({
  doctype: "Project Type",
  fields: ["name"],
  orderBy: "name asc",
  pageLength: 500,
  auto: true,
})

const companyNames = computed(() => {
  const map = {}
  for (const c of companies.data || []) map[c.name] = c.company_name
  return map
})

const operatingUsers = createResource({
  url: "auraos.api.operating_users",
  auto: true,
})

const owners = computed(() => operatingUsers.data || [])

function ownerLabel(user) {
  const match = owners.value.find((u) => u.name === user)
  return match?.full_name || user
}

// -- table view (T3.2) --

function currentUser() {
  const cookie = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith("user_id="))
  return cookie ? decodeURIComponent(cookie.slice("user_id=".length)) : "unknown"
}

const preferenceKey = `auraos.deals.table.${currentUser()}`

function loadTablePreferences() {
  try {
    return JSON.parse(localStorage.getItem(preferenceKey)) || {}
  } catch {
    return {}
  }
}

const savedPreferences = loadTablePreferences()
const view = ref(savedPreferences.view === "Table" ? "Table" : "Board")
const sortKey = ref("modified")
const sortDir = ref("desc")

const COLUMNS = [
  {
    key: "title",
    label: "Title",
    editable: true,
    required: true,
    type: "text",
  },
  {
    key: "company",
    label: "Company",
    editable: true,
    required: true,
    type: "select",
  },
  { key: "stage", label: "Stage", editable: true, type: "select" },
  { key: "deal_owner", label: "Owner", editable: true, type: "select" },
  {
    key: "estimated_budget",
    label: "Budget (VND)",
    editable: true,
    type: "number",
  },
  { key: "source", label: "Source", editable: true, type: "select" },
  {
    key: "project_type",
    label: "Project Type",
    editable: true,
    type: "select",
  },
  { key: "quote_status", label: "Quote" },
  { key: "tags", label: "Tags", editable: true, type: "text" },
  { key: "modified", label: "Updated" },
]

const allColumnKeys = COLUMNS.map((col) => col.key)
const requiredColumnKeys = COLUMNS.filter((col) => col.required).map(
  (col) => col.key
)
const savedColumns = Array.isArray(savedPreferences.columns)
  ? savedPreferences.columns.filter((key) => allColumnKeys.includes(key))
  : allColumnKeys
const initialColumnKeys = savedColumns.length ? savedColumns : allColumnKeys
const visibleColumnKeys = ref(
  [...new Set([...requiredColumnKeys, ...initialColumnKeys])]
)
const visibleColumns = computed(() =>
  COLUMNS.filter((col) => visibleColumnKeys.value.includes(col.key))
)

function saveTablePreferences() {
  try {
    localStorage.setItem(
      preferenceKey,
      JSON.stringify({ view: view.value, columns: visibleColumnKeys.value })
    )
  } catch {
    // Preferences are an enhancement; a blocked storage API must not
    // make the deals page unusable.
  }
}

function setView(mode) {
  view.value = mode
  saveTablePreferences()
}

function toggleColumn(key) {
  if (requiredColumnKeys.includes(key)) return
  if (visibleColumnKeys.value.includes(key)) {
    if (visibleColumnKeys.value.length === 1) return
    visibleColumnKeys.value = visibleColumnKeys.value.filter((item) => item !== key)
  } else {
    visibleColumnKeys.value = [...visibleColumnKeys.value, key]
  }
  saveTablePreferences()
}

const blankOption = { label: "", value: "" }

function optionsFor(key) {
  if (key === "company") {
    return [
      blankOption,
      ...(companies.data || []).map((company) => ({
        label: company.company_name,
        value: company.name,
      })),
    ]
  }
  if (key === "stage") return STAGES
  if (key === "deal_owner") {
    return [
      blankOption,
      ...owners.value.map((owner) => ({
        label: owner.full_name || owner.name,
        value: owner.name,
      })),
    ]
  }
  if (key === "source") {
    return [blankOption, ...(sources.data || []).map(namedOption)]
  }
  if (key === "project_type") {
    return [blankOption, ...(projectTypes.data || []).map(namedOption)]
  }
  return []
}

function namedOption(row) {
  return { label: row.name, value: row.name }
}

// Child rows aren't reachable through the list API; the endpoint
// returns {deal_name: [tag, ...]} in one call.
const dealTags = createResource({
  url: "auraos.api.deal_tags_map",
  auto: true,
})

function tagsFor(deal) {
  return dealTags.data?.[deal.name] || []
}

function stageClass(stage) {
  if (stage === "Lost") return "bg-red-50 text-red-700"
  if (stage === "Won") return "bg-green-50 text-green-700"
  return "bg-gray-100 text-gray-700"
}

// -- inline editing and blank-row creation (T3.3, issue #27) --

const tableError = ref("")
const editing = ref(null)
const updateTableRow = createResource({
  url: "auraos.api.update_deal_table_row",
  onError() {},
})
const createTableRow = createResource({
  url: "auraos.api.create_deal_table_row",
  onError() {},
})
const newDeal = ref(emptyTableRow())

function emptyTableRow() {
  return {
    title: "",
    company: "",
    stage: "Brief Received",
    deal_owner: "",
    estimated_budget: "",
    source: "",
    project_type: "",
    tags: "",
  }
}

function isEditing(deal, col) {
  return editing.value?.deal.name === deal.name && editing.value?.key === col.key
}

function startEditing(deal, col, force = false) {
  if (!col.editable || (col.key === "title" && !force)) return
  tableError.value = ""
  editing.value = {
    deal,
    key: col.key,
    original: editableValue(deal, col.key),
    value: editableValue(deal, col.key),
  }
}

function editableValue(deal, key) {
  if (key === "tags") return tagsFor(deal).join(", ")
  return deal[key] ?? ""
}

function cancelEditing() {
  editing.value = null
}

function valueForServer(key, value) {
  if (key === "tags") {
    return [...new Set(String(value).split(",").map((tag) => tag.trim()).filter(Boolean))]
  }
  if (key === "estimated_budget") return value === "" ? null : Number(value)
  return value
}

async function saveInline() {
  if (updateTableRow.loading) return
  const active = editing.value
  if (!active) return
  if (active.value === active.original) {
    cancelEditing()
    return
  }
  if (active.key === "stage" && active.value === "Lost") {
    pendingLost.value = active.deal
    lostDialogOpen.value = true
    cancelEditing()
    return
  }
  tableError.value = ""
  try {
    await updateTableRow.submit({
      deal: active.deal.name,
      values: {
        [active.key === "tags" ? "deal_tags" : active.key]: valueForServer(
          active.key,
          active.value
        ),
      },
    })
    if (editing.value === active) cancelEditing()
    deals.reload()
    dealTags.reload()
    if (active.key === "stage" && active.value === "Won" && !jobFor(active.deal)) {
      offerJob({ ...active.deal, stage: "Won" })
    }
  } catch (err) {
    tableError.value = frappeErrorMessage(err)
  }
}

function tableRowValues(row) {
  const values = {
    title: row.title.trim(),
    company: row.company,
    stage: row.stage,
  }
  for (const key of ["deal_owner", "source", "project_type"]) {
    if (row[key]) values[key] = row[key]
  }
  if (row.estimated_budget !== "") {
    values.estimated_budget = Number(row.estimated_budget)
  }
  const tags = valueForServer("tags", row.tags)
  if (tags.length) values.deal_tags = tags
  return values
}

async function createFromTable() {
  if (createTableRow.loading) return
  tableError.value = ""
  try {
    await createTableRow.submit({ values: tableRowValues(newDeal.value) })
    newDeal.value = emptyTableRow()
    deals.reload()
    dealTags.reload()
  } catch (err) {
    tableError.value = frappeErrorMessage(err)
  }
}

function sortBy(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === "asc" ? "desc" : "asc"
  } else {
    sortKey.value = key
    sortDir.value = "asc"
  }
}

// Sort what the user sees (display names, joined tags), not raw ids.
function sortValue(deal, key) {
  if (key === "company") return companyNames.value[deal.company] || ""
  if (key === "deal_owner") return ownerLabel(deal.deal_owner) || ""
  if (key === "tags") return tagsFor(deal).join(", ")
  if (key === "estimated_budget") return deal.estimated_budget || 0
  return deal[key] || ""
}

const sortedDeals = computed(() => {
  const dir = sortDir.value === "asc" ? 1 : -1
  return [...(deals.data || [])].sort((a, b) => {
    const va = sortValue(a, sortKey.value)
    const vb = sortValue(b, sortKey.value)
    if (typeof va === "number" || typeof vb === "number") {
      return ((va || 0) - (vb || 0)) * dir
    }
    return String(va).localeCompare(String(vb), "vi") * dir
  })
})

function formatBudget(value) {
  return value ? vnd(value) : ""
}

const dealsByStage = computed(() => {
  const map = {}
  for (const deal of deals.data || []) {
    ;(map[deal.stage] ||= []).push(deal)
  }
  return map
})

// -- drag & drop --

const dragged = ref(null)
const moveError = ref("")
const lostDialogOpen = ref(false)
const pendingLost = ref(null)
// The move a pending set_value is carrying out, so its success handler
// knows what just happened.
const lastMove = ref(null)

const setStage = createResource({
  url: "frappe.client.set_value",
  onSuccess() {
    moveError.value = ""
    deals.reload()
    // Winning a deal is where the job gets created (T7); ask right here
    // rather than leaving it to be remembered later.
    if (lastMove.value?.stage === "Won" && !jobFor(lastMove.value.deal)) {
      offerJob(lastMove.value.deal)
    }
    lastMove.value = null
  },
  onError(err) {
    moveError.value = frappeErrorMessage(err)
    deals.reload()
    lastMove.value = null
  },
})

function onDrop(stage) {
  const deal = dragged.value
  dragged.value = null
  if (!deal || deal.stage === stage) return
  if (stage === "Lost") {
    // The server refuses Lost without a reason; collect it first.
    pendingLost.value = deal
    lostDialogOpen.value = true
    return
  }
  lastMove.value = { deal, stage }
  setStage.submit({
    doctype: "Deal",
    name: deal.name,
    fieldname: { stage },
  })
}

function markLost({ reason, note }) {
  lostDialogOpen.value = false
  setStage.submit({
    doctype: "Deal",
    name: pendingLost.value.name,
    fieldname: { stage: "Lost", lost_reason: reason, lost_note: note },
  })
  pendingLost.value = null
}

// -- dialog --

const dialogOpen = ref(false)
const dialogName = ref(null)

function openNew() {
  dialogName.value = null
  dialogOpen.value = true
}

function openEdit(deal) {
  dialogName.value = deal.name
  dialogOpen.value = true
}

function onSaved(deal) {
  deals.reload()
  dealTags.reload()
  if (deal?.stage === "Won" && !jobFor(deal)) offerJob(deal)
}

const router = useRouter()

function openBreakdown(deal) {
  router.push(`/deals/${deal.name}/breakdown`)
}

// -- won deal → job (T7) --

// {deal: job}; a won deal either offers conversion or opens its job.
const jobsByDeal = createResource({
  url: "auraos.api.jobs_by_deal",
  auto: true,
})

function jobFor(deal) {
  return jobsByDeal.data?.[deal.name]
}

const jobOfferOpen = ref(false)
const pendingJob = ref(null)

function offerJob(deal) {
  pendingJob.value = deal
  jobOfferOpen.value = true
}

const createJob = createResource({
  url: "auraos.api.create_job_from_deal",
  onSuccess(job) {
    jobOfferOpen.value = false
    pendingJob.value = null
    jobsByDeal.reload()
    router.push(`/jobs/${job.name}`)
  },
  onError(err) {
    jobOfferOpen.value = false
    pendingJob.value = null
    moveError.value = frappeErrorMessage(err)
    jobsByDeal.reload()
  },
})

function confirmJobCreation() {
  createJob.submit({ deal: pendingJob.value.name })
}

function openOrCreateJob(deal) {
  const existing = jobFor(deal)
  if (existing) router.push(`/jobs/${existing}`)
  else offerJob(deal)
}
</script>

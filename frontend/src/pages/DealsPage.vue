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
            @click="view = mode"
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
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="overflow-x-auto rounded-lg border">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b bg-gray-50 text-left text-xs text-gray-600">
            <th
              v-for="col in COLUMNS"
              :key="col.key"
              class="cursor-pointer select-none whitespace-nowrap px-3 py-2 font-medium hover:text-gray-900"
              @click="sortBy(col.key)"
            >
              {{ col.label }}
              <span v-if="sortKey === col.key">
                {{ sortDir === "asc" ? "↑" : "↓" }}
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="deal in sortedDeals"
            :key="deal.name"
            class="cursor-pointer border-b last:border-b-0 hover:bg-gray-50"
            @click="openEdit(deal)"
          >
            <td class="px-3 py-2 font-medium text-gray-900">
              {{ deal.title }}
            </td>
            <td class="px-3 py-2 text-gray-700">
              {{ companyNames[deal.company] || deal.company }}
            </td>
            <td class="whitespace-nowrap px-3 py-2">
              <span
                class="rounded-full px-2 py-0.5 text-xs"
                :class="
                  deal.stage === 'Lost'
                    ? 'bg-red-50 text-red-700'
                    : deal.stage === 'Won'
                      ? 'bg-green-50 text-green-700'
                      : 'bg-gray-100 text-gray-700'
                "
              >
                {{ deal.stage }}
              </span>
            </td>
            <td class="whitespace-nowrap px-3 py-2 text-gray-700">
              {{ ownerLabel(deal.deal_owner) }}
            </td>
            <td class="whitespace-nowrap px-3 py-2 text-right tabular-nums text-gray-700">
              {{ formatBudget(deal.estimated_budget) }}
            </td>
            <td class="whitespace-nowrap px-3 py-2 text-gray-700">
              {{ deal.source }}
            </td>
            <td class="whitespace-nowrap px-3 py-2 text-gray-700">
              {{ deal.project_type }}
            </td>
            <td class="px-3 py-2">
              <span
                v-for="tag in tagsFor(deal)"
                :key="tag"
                class="mr-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700"
              >
                {{ tag }}
              </span>
            </td>
            <td class="whitespace-nowrap px-3 py-2 tabular-nums text-gray-500">
              {{ deal.modified?.slice(0, 16) }}
            </td>
          </tr>
          <tr v-if="!sortedDeals.length">
            <td
              :colspan="COLUMNS.length"
              class="px-3 py-6 text-center text-gray-400"
            >
              No deals yet.
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <ErrorMessage class="mt-2" :message="moveError" />

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
  </div>
</template>

<script setup>
import { ref, computed } from "vue"
import {
  Button,
  ErrorMessage,
  createResource,
  createListResource,
} from "frappe-ui"
import DealFormDialog from "../components/DealFormDialog.vue"
import LostReasonDialog from "../components/LostReasonDialog.vue"
import { frappeErrorMessage } from "../utils/frappeError"

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
    "modified",
  ],
  orderBy: "modified desc",
  pageLength: 500,
  auto: true,
})

const companies = createListResource({
  doctype: "Party Company",
  fields: ["name", "company_name"],
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

const view = ref("Board")
const sortKey = ref("modified")
const sortDir = ref("desc")

const COLUMNS = [
  { key: "title", label: "Title" },
  { key: "company", label: "Company" },
  { key: "stage", label: "Stage" },
  { key: "deal_owner", label: "Owner" },
  { key: "estimated_budget", label: "Budget (VND)" },
  { key: "source", label: "Source" },
  { key: "project_type", label: "Project Type" },
  { key: "tags", label: "Tags" },
  { key: "modified", label: "Updated" },
]

// Child rows aren't reachable through the list API; the endpoint
// returns {deal_name: [tag, ...]} in one call.
const dealTags = createResource({
  url: "auraos.api.deal_tags_map",
  auto: true,
})

function tagsFor(deal) {
  return dealTags.data?.[deal.name] || []
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
  return value ? Number(value).toLocaleString("vi-VN") : ""
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

const setStage = createResource({
  url: "frappe.client.set_value",
  onSuccess() {
    moveError.value = ""
    deals.reload()
  },
  onError(err) {
    moveError.value = frappeErrorMessage(err)
    deals.reload()
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

function onSaved() {
  deals.reload()
  dealTags.reload()
}
</script>

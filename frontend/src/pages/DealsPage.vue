<template>
  <div class="px-4 py-6">
    <div class="mb-4 flex items-center gap-3">
      <h1 class="text-lg font-semibold text-gray-900">Deals</h1>
      <div class="ml-auto">
        <Button variant="solid" @click="openNew">New Deal</Button>
      </div>
    </div>

    <div class="flex gap-3 overflow-x-auto pb-4">
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

    <ErrorMessage class="mt-2" :message="moveError" />

    <DealFormDialog
      v-model="dialogOpen"
      :name="dialogName"
      :owners="owners"
      @saved="deals.reload()"
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
    moveError.value = err.messages?.join("\n") || err.message
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
</script>

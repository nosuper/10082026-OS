<template>
  <div class="px-4 py-6">
    <div class="mb-4 flex flex-wrap items-center gap-2">
      <h1 class="text-lg font-semibold text-gray-900">Deals</h1>
      <span class="text-sm tabular-nums text-gray-400">
        {{ filteredDeals.length }}
      </span>
      <div class="relative ml-2">
        <FeatherIcon
          name="search"
          class="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400"
        />
        <input
          v-model.trim="query"
          type="text"
          placeholder="Search deals"
          class="w-56 rounded-md border-gray-300 py-1.5 pl-8 text-sm placeholder-gray-500 focus:border-gray-500 focus:ring-0"
        />
      </div>
      <select
        v-model="ownerFilter"
        class="rounded-md border-gray-300 py-1.5 text-sm text-gray-700 focus:border-gray-500 focus:ring-0"
      >
        <option value="">All owners</option>
        <option v-for="owner in owners" :key="owner.name" :value="owner.name">
          {{ owner.full_name || owner.name }}
        </option>
      </select>
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
        class="flex w-72 shrink-0 flex-col rounded-lg transition-colors"
        :class="
          dragOverStage === stage.value
            ? 'bg-blue-50 ring-2 ring-inset ring-blue-300'
            : 'bg-gray-100'
        "
        @dragover.prevent="dragOverStage = stage.value"
        @dragleave="onDragLeave(stage.value, $event)"
        @drop="onDrop(stage.value)"
      >
        <div class="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-800">
          <span class="h-2 w-2 shrink-0 rounded-full" :class="stage.dot"></span>
          {{ stage.label }}
          <span class="text-xs font-normal text-gray-500">
            {{ dealsByStage[stage.value]?.length || 0 }}
          </span>
          <span
            v-if="stageTotals[stage.value]"
            class="ml-auto text-xs font-medium tabular-nums text-gray-600"
            :title="`${vnd(stageTotals[stage.value])} ₫ total in ${stage.label}`"
          >
            {{ vndShort(stageTotals[stage.value]) }}
          </span>
        </div>
        <div class="flex min-h-24 flex-1 flex-col gap-2 px-2 pb-2">
          <div
            v-for="deal in dealsByStage[stage.value]"
            :key="deal.name"
            class="group cursor-grab rounded-md border bg-white p-3 shadow-sm transition-shadow hover:border-gray-300 hover:shadow"
            :class="dragged === deal ? 'opacity-50' : ''"
            draggable="true"
            @dragstart="dragged = deal"
            @dragend="((dragged = null), (dragOverStage = null))"
            @click="openEdit(deal)"
          >
            <div class="flex items-start gap-2">
              <div class="min-w-0 flex-1">
                <div
                  class="truncate text-sm font-medium text-gray-900"
                  :title="deal.title"
                >
                  {{ deal.title }}
                </div>
                <div
                  v-if="deal.company"
                  class="mt-0.5 truncate text-xs text-gray-500"
                >
                  {{ companyNames[deal.company] || deal.company }}
                </div>
              </div>
              <button
                class="shrink-0 rounded p-1 text-gray-400 opacity-0 transition-opacity hover:bg-gray-100 hover:text-gray-700 group-hover:opacity-100"
                title="Breakdown & Quote"
                @click.stop="openBreakdown(deal)"
              >
                <FeatherIcon name="dollar-sign" class="h-3.5 w-3.5" />
              </button>
            </div>
            <div
              v-if="deal.estimated_budget || deal.project_type"
              class="mt-2 flex items-center gap-2"
            >
              <span
                v-if="deal.estimated_budget"
                class="text-sm font-medium tabular-nums text-gray-800"
              >
                {{ vnd(deal.estimated_budget) }}
              </span>
              <span
                v-if="deal.project_type"
                class="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600"
              >
                {{ deal.project_type }}
              </span>
              <span
                v-if="deal.tier"
                class="rounded px-1.5 py-0.5 text-xs"
                :class="tierClass(deal.tier)"
                :title="deal.positioning ? `${deal.tier} · ${deal.positioning}` : deal.tier"
              >
                {{ deal.tier.replace("Tier ", "T") }}
              </span>
            </div>
            <div class="mt-2 flex flex-wrap items-center gap-1.5">
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
                class="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-800"
                :title="`Quote sent ${silentDeals[deal.name].quote_sent_on?.slice(0, 10)} - no reply after ${silence.data?.silence_days} days`"
              >
                <FeatherIcon name="clock" class="h-3 w-3" />
                Silent
              </span>
              <a
                v-if="quoteLinks[deal.name]"
                :href="quoteLinks[deal.name].url"
                target="_blank"
                rel="noopener"
                class="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700 hover:bg-blue-100"
                :title="`Open the client's quote page (v${quoteLinks[deal.name].version})`"
                @click.stop
              >
                <FeatherIcon name="link" class="h-3 w-3" />
                v{{ quoteLinks[deal.name].version }}
              </a>
              <button
                v-if="deal.stage === 'Won'"
                class="rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700 hover:bg-green-100"
                :title="jobFor(deal) ? 'Open the job' : 'Create the job'"
                @click.stop="openOrCreateJob(deal)"
              >
                {{ jobFor(deal) ? "Job →" : "+ Job" }}
              </button>
              <span
                v-if="stageAge(deal) >= 1 && deal.stage !== 'Won' && deal.stage !== 'Lost'"
                class="ml-auto text-xs tabular-nums"
                :class="
                  stageAge(deal) > STALE_DAYS
                    ? 'rounded-full bg-amber-100 px-2 py-0.5 font-medium text-amber-800'
                    : 'text-gray-400'
                "
                :title="`In ${deal.stage} for ${stageAge(deal)} ${stageAge(deal) === 1 ? 'day' : 'days'}`"
              >
                {{ stageAge(deal) }} {{ stageAge(deal) === 1 ? "day" : "days" }}
              </span>
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
              :class="col.align === 'right' ? 'text-right' : ''"
              @click="sortBy(col.key)"
            >
              {{ col.label }}
              <span v-if="sortKey === col.key">
                {{ sortDir === "asc" ? "↑" : "↓" }}
              </span>
            </th>
            <th class="sticky right-0 w-px bg-gray-50 px-3 py-2"></th>
          </tr>
        </thead>
        <tbody>
          <tr class="border-b bg-gray-50/70 align-top">
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
              <VndInput
                v-else-if="col.editable && col.type === 'number'"
                v-model="newDeal[col.key]"
                :placeholder="col.label"
                class="w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-right text-sm tabular-nums"
                @enter="createFromTable"
              />
              <input
                v-else-if="col.editable"
                v-model="newDeal[col.key]"
                type="text"
                :placeholder="col.key === 'tags' ? 'tag, tag' : col.label"
                class="w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm"
                @keydown.enter="createFromTable"
              />
              <span v-else class="text-gray-300">-</span>
            </td>
            <td class="sticky right-0 whitespace-nowrap bg-gray-50 px-2 py-1.5">
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
            class="group border-b last:border-b-0 hover:bg-gray-50"
          >
            <td
              v-for="col in visibleColumns"
              :key="col.key"
              class="px-3 py-2 text-gray-700"
              :class="[
                col.key === 'title' ? 'min-w-56' : 'min-w-32',
                col.align === 'right' ? 'text-right' : '',
                col.editable && col.key !== 'title'
                  ? 'cursor-text hover:bg-blue-50/50'
                  : '',
              ]"
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
                <VndInput
                  v-else-if="col.type === 'number'"
                  v-model="editing.value"
                  class="w-full rounded border border-blue-400 bg-white px-2 py-1 text-right text-sm tabular-nums"
                  autofocus
                  @click.stop
                  @enter="$event.target.blur()"
                  @esc="cancelEditing"
                  @blur="saveInline"
                />
                <input
                  v-else
                  v-model="editing.value"
                  type="text"
                  class="w-full rounded border border-blue-400 bg-white px-2 py-1 text-sm"
                  autofocus
                  @click.stop
                  @change="saveInline"
                  @keydown.enter.prevent="$event.target.blur()"
                  @keydown.esc="cancelEditing"
                />
              </template>
              <template v-else-if="col.key === 'title'">
                <div class="group flex items-center gap-1.5">
                  <button
                    class="text-left font-medium text-blue-700 hover:underline"
                    @click.stop="openEdit(deal)"
                  >
                    {{ deal.title }}
                  </button>
                  <button
                    class="shrink-0 rounded p-0.5 text-gray-400 opacity-0 transition-opacity hover:bg-gray-100 hover:text-gray-700 group-hover:opacity-100"
                    title="Edit title inline"
                    @click.stop="startEditing(deal, col, true)"
                  >
                    <FeatherIcon name="edit-2" class="h-3 w-3" />
                  </button>
                </div>
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
                  class="ml-1 inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-800"
                >
                  <FeatherIcon name="clock" class="h-3 w-3" />
                  Silent
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
              <span
                v-else-if="col.key === 'modified'"
                class="whitespace-nowrap tabular-nums text-gray-500"
                :title="deal.modified?.slice(0, 16)"
              >
                {{ ago(deal.modified) }}
              </span>
              <span v-else>{{ deal[col.key] }}</span>
            </td>
            <td class="sticky right-0 bg-white px-3 py-2 group-hover:bg-gray-50"></td>
          </tr>
          <tr v-if="!sortedDeals.length">
            <td
              :colspan="visibleColumns.length + 1"
              class="px-3 py-6 text-center text-gray-400"
            >
              {{
                query || ownerFilter
                  ? "No deals match your search."
                  : "No deals yet - add one in the row above."
              }}
            </td>
          </tr>
        </tbody>
        </table>
      </div>
      <div class="mt-2 flex items-center justify-between text-xs text-gray-500">
        <span>Click any cell to edit it in place - Enter saves, Esc cancels.</span>
        <span v-if="tableBudgetTotal" class="tabular-nums">
          {{ sortedDeals.length }} deals · {{ vnd(tableBudgetTotal) }} ₫
        </span>
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
  FeatherIcon,
  createResource,
  createListResource,
} from "frappe-ui"
import DealFormDialog from "../components/DealFormDialog.vue"
import LostReasonDialog from "../components/LostReasonDialog.vue"
import VndInput from "../components/VndInput.vue"
import { frappeErrorMessage } from "../utils/frappeError"
import { vnd, vndShort } from "../utils/money"
import { ago, daysSince } from "../utils/time"
import { STAGES, stageClass } from "../utils/stages"
import { currentUser } from "../utils/user"

// The founder's weekly ritual: which deal has sat still for over a
// week? Past this many days in one stage, the age badge turns amber.
const STALE_DAYS = 7

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
    "tier",
    "positioning",
    "modified",
    "creation",
  ],
  orderBy: "modified desc",
  pageLength: 500,
  auto: true,
})

// {deal: datetime it entered its current stage} - the age badge.
const stageEntries = createResource({
  url: "auraos.api.deal_stage_entries",
  auto: true,
})

function stageAge(deal) {
  return daysSince(stageEntries.data?.[deal.name] || deal.creation) ?? 0
}

// Quotes that have gone unanswered past the company's silence window
// (spec #2, story 6) - the deal-killer the board is meant to surface.
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

// -- search & owner filter (shared by both views) --

const query = ref("")
const ownerFilter = ref("")

const filteredDeals = computed(() => {
  const needle = query.value.toLowerCase()
  const owner = ownerFilter.value
  return (deals.data || []).filter((deal) => {
    if (owner && deal.deal_owner !== owner) return false
    if (!needle) return true
    return [
      deal.title,
      companyNames.value[deal.company] || deal.company,
      deal.project_type,
      deal.name,
    ]
      .filter(Boolean)
      .some((text) => String(text).toLowerCase().includes(needle))
  })
})

// Pipeline value per column - the number the playbook's 3X coverage
// rule is read off of.
const stageTotals = computed(() => {
  const totals = {}
  for (const deal of filteredDeals.value) {
    if (!deal.estimated_budget) continue
    totals[deal.stage] = (totals[deal.stage] || 0) + deal.estimated_budget
  }
  return totals
})

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
    align: "right",
  },
  { key: "source", label: "Source", editable: true, type: "select" },
  {
    key: "project_type",
    label: "Project Type",
    editable: true,
    type: "select",
  },
  { key: "tier", label: "Tier", editable: true, type: "select" },
  { key: "positioning", label: "Positioning", editable: true, type: "select" },
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
  if (key === "tier") {
    return [
      blankOption,
      { label: "Tier 1", value: "Tier 1" },
      { label: "Tier 2", value: "Tier 2" },
      { label: "Tier 3", value: "Tier 3" },
    ]
  }
  if (key === "positioning") {
    return [
      blankOption,
      { label: "Cash", value: "Cash" },
      { label: "Bridge", value: "Bridge" },
      { label: "Brand", value: "Brand" },
    ]
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
    if (active.key === "stage") stageEntries.reload()
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
    stageEntries.reload()
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
  return [...filteredDeals.value].sort((a, b) => {
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

// Tier badges: quiet for the daily bread, louder as it climbs.
function tierClass(tier) {
  if (tier === "Tier 3") return "bg-violet-50 font-medium text-violet-700"
  if (tier === "Tier 2") return "bg-blue-50 text-blue-700"
  return "bg-gray-100 text-gray-600"
}

const dealsByStage = computed(() => {
  const map = {}
  for (const deal of filteredDeals.value) {
    ;(map[deal.stage] ||= []).push(deal)
  }
  return map
})

const tableBudgetTotal = computed(() =>
  sortedDeals.value.reduce((sum, deal) => sum + (deal.estimated_budget || 0), 0)
)

// -- drag & drop --

const dragged = ref(null)
// The column a card is currently held over - its highlight is the
// "you are about to drop here" answer.
const dragOverStage = ref(null)
const moveError = ref("")

function onDragLeave(stage, event) {
  if (dragOverStage.value !== stage) return
  // Moving over a card inside the column also fires dragleave; only
  // clear when the pointer truly left the column.
  if (event.relatedTarget && event.currentTarget.contains(event.relatedTarget)) {
    return
  }
  dragOverStage.value = null
}
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
    stageEntries.reload()
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
  dragOverStage.value = null
  if (!deal || deal.stage === stage) return
  if (stage === "Lost") {
    // The server refuses Lost without a reason; collect it first.
    pendingLost.value = deal
    lostDialogOpen.value = true
    return
  }
  lastMove.value = { deal, stage }
  // Move the card before the server answers: a drop that waits out a
  // round-trip before landing reads as lag (founder, A1 walkthrough).
  // The reload in the success/error handlers is the correction if the
  // server disagrees.
  deal.stage = stage
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
  stageEntries.reload()
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

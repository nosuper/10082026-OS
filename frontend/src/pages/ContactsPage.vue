<template>
  <div class="space-y-4">
    <!-- Page head: who is in the book, and how much of it is contract-ready. -->
    <div class="flex flex-wrap items-end gap-x-3 gap-y-2">
      <h1 class="text-xl font-semibold text-carbon">{{ activeLabel }}</h1>
      <p class="text-sm text-muted">
        {{ activeRows.length }} {{ activeNoun }}
        <template v-if="incompleteCount">
          · <span class="text-accent">{{ incompleteCount }} missing paperwork</span>
        </template>
      </p>
      <div class="ml-auto">
        <Button variant="solid" @click="openNew">
          {{ activeTab === "companies" ? "New Company" : "New Person" }}
        </Button>
      </div>
    </div>

    <!-- The two halves of the directory are two addresses: the tab is the URL,
         so a bookmark or a sidebar link lands on the right side. -->
    <div class="flex flex-wrap items-center gap-2">
      <div class="inline-flex items-center gap-1 rounded-pill border border-hairline bg-paper p-1 shadow-card">
        <router-link
          v-for="tab in tabs"
          :key="tab.value"
          :to="tab.to"
          class="flex items-center gap-1.5 rounded-pill px-3 py-1.5 text-sm transition-colors"
          :class="
            activeTab === tab.value
              ? 'bg-carbon font-medium text-white'
              : 'text-muted hover:text-carbon'
          "
        >
          {{ tab.label }}
          <span
            class="aura-num text-[11px]"
            :class="activeTab === tab.value ? 'text-white/60' : 'text-faint'"
          >
            {{ tab.value === "companies" ? (companies.data || []).length : (people.data || []).length }}
          </span>
        </router-link>
      </div>

      <label
        class="flex min-w-[200px] flex-1 items-center gap-2 rounded-[10px] border border-hairline bg-paper px-2.5 py-2 shadow-card transition-colors focus-within:border-accent/40"
      >
        <FeatherIcon name="search" class="h-3.5 w-3.5 shrink-0 text-faint" />
        <input
          v-model="search"
          type="text"
          :placeholder="activeTab === 'companies' ? 'Search companies' : 'Search people or company'"
          class="w-full bg-transparent text-sm text-carbon outline-none placeholder:text-faint"
        />
      </label>
    </div>

    <!-- Role chips filter server-side on the Party Role Tag child table, so the
         answer is not capped by whatever page happens to be loaded. -->
    <div class="flex flex-wrap items-center gap-1.5">
      <button
        v-for="option in roleFilterOptions"
        :key="option.value"
        type="button"
        class="rounded-pill border px-2.5 py-1 text-xs transition-colors"
        :class="
          roleFilter === option.value
            ? 'border-carbon bg-carbon font-medium text-white'
            : 'border-hairline bg-paper text-muted hover:text-carbon'
        "
        @click="roleFilter = option.value"
      >
        {{ option.label }}
      </button>
    </div>

    <DataTable
      title="Directory"
      :count="filteredRows.length"
      :columns="columns"
      :rows="filteredRows"
      clickable
      @row-click="openEdit"
    >
      <template #cell-company_name="{ row }">
        <div class="min-w-0">
          <div class="truncate text-sm font-medium text-carbon">
            {{ row.company_name || row.name }}
          </div>
          <div v-if="row.address" class="truncate text-xs text-faint">{{ row.address }}</div>
        </div>
      </template>

      <template #cell-full_name="{ row }">
        <div class="truncate text-sm font-medium text-carbon">
          {{ row.full_name || row.name }}
        </div>
      </template>

      <template #cell-company_label="{ row }">
        <span class="truncate text-sm text-muted">{{ row.company_label || "-" }}</span>
      </template>

      <template #cell-tax_code="{ row }">
        <span class="aura-num text-xs text-muted">{{ row.tax_code || "-" }}</span>
      </template>

      <template #cell-phone="{ row }">
        <span class="aura-num text-xs text-muted">{{ row.phone || "-" }}</span>
      </template>

      <template #cell-email="{ row }">
        <span class="block truncate text-sm text-muted">{{ row.email || "-" }}</span>
      </template>

      <!-- Paperwork completeness: incomplete records cannot generate a contract
           without gap markers, so the holes are named here, before the print. -->
      <template #cell-docs_label="{ row }">
        <span v-if="row.docs_missing.length" class="flex min-w-0 items-center gap-1.5">
          <StatusPill label="Missing" tone="warn" class="shrink-0" />
          <span class="truncate text-xs text-muted">{{ row.docs_missing.join(", ") }}</span>
        </span>
        <StatusPill v-else label="Complete" tone="ok" />
      </template>

      <template #empty>
        <EmptyState
          icon="users"
          title="Nothing here yet."
          :detail="
            search || roleFilter
              ? 'No record matches this search or role.'
              : 'Create the first record with the button above.'
          "
        />
      </template>
    </DataTable>

    <PartyFormDialog
      v-model="dialogOpen"
      :doctype="dialogDoctype"
      :name="dialogName"
      @saved="reload"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue"
import { useRoute } from "vue-router"
import { Button, FeatherIcon, createListResource } from "frappe-ui"
import DataTable from "../components/DataTable.vue"
import StatusPill from "../components/StatusPill.vue"
import EmptyState from "../components/EmptyState.vue"
import PartyFormDialog from "../components/PartyFormDialog.vue"

const tabs = [
  { label: "Companies", value: "companies", to: "/contacts/companies" },
  { label: "People", value: "people", to: "/contacts/people" },
]

// The tab is the URL: /contacts/companies and /contacts/people already resolve
// here, so the route path is the single source of truth and the tab links are
// plain navigation - no internal state to fall out of step with the address.
const route = useRoute()
const activeTab = computed(() =>
  route.path.endsWith("/people") ? "people" : "companies"
)
const activeLabel = computed(() =>
  activeTab.value === "companies" ? "Companies" : "People"
)
const activeNoun = computed(() =>
  activeTab.value === "companies" ? "companies" : "people"
)

const search = ref("")
const roleFilter = ref("")

const partyRoles = createListResource({
  doctype: "Party Role",
  fields: ["name"],
  pageLength: 50,
  auto: true,
})

const roleFilterOptions = computed(() => [
  { label: "All roles", value: "" },
  ...(partyRoles.data || []).map((r) => ({ label: r.name, value: r.name })),
])

// Filtering on the child table server-side: works past any page cap.
watch(roleFilter, (role) => {
  const filters = role
    ? [["Party Role Tag", "party_role", "=", role]]
    : []
  companies.filters = filters
  people.filters = filters
  companies.reload()
  people.reload()
})

const companies = createListResource({
  doctype: "Party Company",
  fields: [
    "name",
    "company_name",
    "tax_code",
    "phone",
    "email",
    "address",
    "bank_account_number",
  ],
  orderBy: "modified desc",
  pageLength: 500,
  auto: true,
})

const people = createListResource({
  doctype: "Party Contact",
  fields: [
    "name",
    "full_name",
    "company",
    "phone",
    "email",
    "id_number",
    "tax_code",
    "bank_account_number",
  ],
  orderBy: "modified desc",
  pageLength: 500,
  auto: true,
})

// What the paperwork needs to fill a contract without «thiếu: …» gap
// markers - surfaced here so the holes are visible before generating,
// not on the printed page.
const COMPANY_DOCS = [
  ["tax_code", "tax code"],
  ["address", "address"],
  ["bank_account_number", "bank"],
]

const PERSON_DOCS = [
  ["id_number", "CCCD"],
  ["tax_code", "tax code"],
  ["bank_account_number", "bank"],
]

function docsMissing(row, spec) {
  return spec.filter(([field]) => !row[field]).map(([, label]) => label)
}

function docsLabel(missing) {
  return missing.length ? `missing ${missing.join(", ")}` : "complete"
}

const COMPANY_COLUMNS = [
  { label: "Company", key: "company_name", width: "220px" },
  { label: "Tax Code", key: "tax_code", width: "120px" },
  { label: "Phone", key: "phone", width: "140px" },
  { label: "Email", key: "email", width: "220px" },
  { label: "Paperwork", key: "docs_label", width: "220px" },
]

const PEOPLE_COLUMNS = [
  { label: "Name", key: "full_name", width: "200px" },
  { label: "Company", key: "company_label", width: "180px" },
  { label: "Phone", key: "phone", width: "140px" },
  { label: "Email", key: "email", width: "200px" },
  { label: "Paperwork", key: "docs_label", width: "220px" },
]

const columns = computed(() =>
  activeTab.value === "companies" ? COMPANY_COLUMNS : PEOPLE_COLUMNS
)

const companyNames = computed(() => {
  const map = {}
  for (const c of companies.data || []) map[c.name] = c.company_name
  return map
})

const activeRows = computed(() => {
  if (activeTab.value === "companies") {
    return (companies.data || []).map((c) => {
      const missing = docsMissing(c, COMPANY_DOCS)
      return { ...c, docs_missing: missing, docs_label: docsLabel(missing) }
    })
  }
  return (people.data || []).map((p) => {
    const missing = docsMissing(p, PERSON_DOCS)
    return {
      ...p,
      company_label: companyNames.value[p.company] || "",
      docs_missing: missing,
      docs_label: docsLabel(missing),
    }
  })
})

const incompleteCount = computed(
  () => activeRows.value.filter((row) => row.docs_missing.length).length
)

const filteredRows = computed(() => {
  const rows = activeRows.value
  const q = search.value.trim().toLowerCase()
  if (!q) return rows
  return rows.filter((row) =>
    Object.values(row).some(
      (value) => value && String(value).toLowerCase().includes(q)
    )
  )
})

const dialogOpen = ref(false)
const dialogName = ref(null)
const dialogDoctype = computed(() =>
  activeTab.value === "companies" ? "Party Company" : "Party Contact"
)

function openNew() {
  dialogName.value = null
  dialogOpen.value = true
}

function openEdit(row) {
  dialogName.value = row.name
  dialogOpen.value = true
}

function reload() {
  companies.reload()
  people.reload()
}
</script>

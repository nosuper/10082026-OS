<template>
  <div class="mx-auto max-w-5xl px-4 py-6">
    <div class="mb-4 flex flex-wrap items-center gap-3">
      <div class="flex rounded-lg bg-gray-100 p-0.5">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          class="rounded-md px-3 py-1.5 text-sm font-medium"
          :class="
            activeTab === tab.value
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-800'
          "
          @click="activeTab = tab.value"
        >
          {{ tab.label }}
        </button>
      </div>
      <FormControl
        type="text"
        class="w-56"
        placeholder="Search…"
        v-model="search"
      />
      <div class="ml-auto">
        <Button variant="solid" @click="openNew">
          {{ activeTab === "companies" ? "New Company" : "New Person" }}
        </Button>
      </div>
    </div>

    <div class="rounded-lg border bg-white">
      <ListView
        :columns="columns"
        :rows="filteredRows"
        row-key="name"
        :options="{
          selectable: false,
          onRowClick: openEdit,
          emptyState: {
            title: 'Nothing here yet',
            description: 'Create the first record with the button above.',
          },
        }"
      />
    </div>

    <PartyFormDialog
      v-model="dialogOpen"
      :doctype="dialogDoctype"
      :name="dialogName"
      @saved="reload"
    />
  </div>
</template>

<script setup>
import { ref, computed } from "vue"
import { Button, FormControl, ListView, createListResource } from "frappe-ui"
import PartyFormDialog from "../components/PartyFormDialog.vue"

const tabs = [
  { label: "Companies", value: "companies" },
  { label: "People", value: "people" },
]
const activeTab = ref("companies")
const search = ref("")

const companies = createListResource({
  doctype: "Party Company",
  fields: ["name", "company_name", "tax_code", "phone", "email"],
  orderBy: "modified desc",
  pageLength: 500,
  auto: true,
})

const people = createListResource({
  doctype: "Party Contact",
  fields: ["name", "full_name", "company", "phone", "email"],
  orderBy: "modified desc",
  pageLength: 500,
  auto: true,
})

const COMPANY_COLUMNS = [
  { label: "Company", key: "company_name" },
  { label: "Tax Code", key: "tax_code" },
  { label: "Phone", key: "phone" },
  { label: "Email", key: "email" },
]

const PEOPLE_COLUMNS = [
  { label: "Name", key: "full_name" },
  { label: "Company", key: "company_label" },
  { label: "Phone", key: "phone" },
  { label: "Email", key: "email" },
]

const columns = computed(() =>
  activeTab.value === "companies" ? COMPANY_COLUMNS : PEOPLE_COLUMNS
)

const companyNames = computed(() => {
  const map = {}
  for (const c of companies.data || []) map[c.name] = c.company_name
  return map
})

const filteredRows = computed(() => {
  const rows =
    activeTab.value === "companies"
      ? companies.data || []
      : (people.data || []).map((p) => ({
          ...p,
          company_label: companyNames.value[p.company] || "",
        }))
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

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
            placeholder="No company"
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

// Contacts of the chosen company first; unattached contacts still
// selectable so a person can be linked before their company exists.
const contactOptions = computed(() => {
  const company = companySelection.value?.value
  const all = contacts.data || []
  const ranked = company
    ? [...all.filter((c) => c.company === company), ...all.filter((c) => c.company !== company)]
    : all
  return ranked.map((c) => ({ label: c.full_name, value: c.name }))
})

const fetchDoc = createResource({
  url: "frappe.client.get",
  onSuccess(doc) {
    serverDoc = doc
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
    serverDoc = null
    form.value = {}
    companySelection.value = null
    contactSelection.value = null
    companies.fetch()
    contacts.fetch()
    if (props.name) {
      loading.value = true
      fetchDoc.fetch({ doctype: "Deal", name: props.name })
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

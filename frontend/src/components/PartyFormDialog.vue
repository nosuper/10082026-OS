<template>
  <Dialog
    :modelValue="modelValue"
    @update:modelValue="$emit('update:modelValue', $event)"
    :options="{ title: title, size: 'xl' }"
  >
    <template #body-content>
      <div v-if="loading" class="py-8 text-center text-sm text-gray-500">
        Loading…
      </div>
      <div v-else class="space-y-4">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormControl
            v-for="field in fields"
            :key="field.fieldname"
            :type="field.type || 'text'"
            :label="field.label"
            v-model="form[field.fieldname]"
            :required="field.required"
            :class="{ 'sm:col-span-2': field.wide }"
          />
        </div>

        <div v-if="isContact">
          <FormControl
            type="autocomplete"
            label="Company"
            :options="companyOptions"
            v-model="companySelection"
            placeholder="No company"
          />
        </div>

        <div>
          <div class="mb-1.5 text-xs text-gray-600">Role Tags</div>
          <div class="flex gap-4">
            <Checkbox
              v-for="role in partyRoles.data || []"
              :key="role.name"
              :label="role.name"
              :modelValue="selectedRoles.includes(role.name)"
              @update:modelValue="toggleRole(role.name, $event)"
            />
          </div>
        </div>

        <FormControl
          type="textarea"
          label="Notes"
          v-model="form.notes"
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
  Checkbox,
  ErrorMessage,
  createResource,
  createListResource,
} from "frappe-ui"

const props = defineProps({
  modelValue: Boolean,
  doctype: { type: String, required: true },
  // null → create a new record
  name: { type: String, default: null },
})
const emit = defineEmits(["update:modelValue", "saved"])

const isContact = computed(() => props.doctype === "Party Contact")
const title = computed(() => {
  const noun = isContact.value ? "Person" : "Company"
  return props.name ? `Edit ${noun}` : `New ${noun}`
})

const COMPANY_FIELDS = [
  { fieldname: "company_name", label: "Company Name", required: true },
  { fieldname: "tax_code", label: "Tax Code" },
  { fieldname: "phone", label: "Phone" },
  { fieldname: "email", label: "Email", type: "email" },
  { fieldname: "website", label: "Website" },
  { fieldname: "address", label: "Address" },
  { fieldname: "bank_name", label: "Bank Name" },
  { fieldname: "bank_account_number", label: "Bank Account Number" },
  { fieldname: "bank_account_name", label: "Bank Account Name" },
]

const CONTACT_FIELDS = [
  { fieldname: "full_name", label: "Full Name", required: true },
  { fieldname: "phone", label: "Phone" },
  { fieldname: "zalo", label: "Zalo" },
  { fieldname: "email", label: "Email", type: "email" },
  { fieldname: "tax_code", label: "Personal Tax Code" },
  { fieldname: "id_number", label: "ID Number (CCCD)" },
  { fieldname: "bank_name", label: "Bank Name" },
  { fieldname: "bank_account_number", label: "Bank Account Number" },
  { fieldname: "bank_account_name", label: "Bank Account Name" },
]

const fields = computed(() =>
  isContact.value ? CONTACT_FIELDS : COMPANY_FIELDS
)

const form = ref({})
const selectedRoles = ref([])
const companySelection = ref(null)
const loading = ref(false)
const saving = ref(false)
const saveError = ref("")
// The server copy of an existing doc; edits are overlaid on save so
// name/modified survive the round trip.
let serverDoc = null

const partyRoles = createListResource({
  doctype: "Party Role",
  fields: ["name"],
  pageLength: 50,
  auto: true,
})

const companies = createListResource({
  doctype: "Party Company",
  fields: ["name", "company_name"],
  orderBy: "company_name asc",
  pageLength: 500,
  onSuccess(data) {
    // The doc may load before the company list; fix up the label.
    if (companySelection.value) {
      const match = data.find((c) => c.name === companySelection.value.value)
      if (match) {
        companySelection.value = {
          label: match.company_name,
          value: match.name,
        }
      }
    }
  },
})

const companyOptions = computed(() =>
  (companies.data || []).map((c) => ({
    label: c.company_name,
    value: c.name,
  }))
)

const fetchDoc = createResource({
  url: "frappe.client.get",
  onSuccess(doc) {
    serverDoc = doc
    form.value = { ...doc }
    selectedRoles.value = (doc.role_tags || []).map((r) => r.party_role)
    const match = (companies.data || []).find((c) => c.name === doc.company)
    companySelection.value = doc.company
      ? { label: match?.company_name || doc.company, value: doc.company }
      : null
    loading.value = false
  },
  onError() {
    loading.value = false
  },
})

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    saveError.value = ""
    serverDoc = null
    form.value = {}
    selectedRoles.value = []
    companySelection.value = null
    if (isContact.value) companies.fetch()
    if (props.name) {
      loading.value = true
      fetchDoc.fetch({ doctype: props.doctype, name: props.name })
    }
  }
)

function toggleRole(role, checked) {
  selectedRoles.value = checked
    ? [...selectedRoles.value, role]
    : selectedRoles.value.filter((r) => r !== role)
}

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
    doctype: props.doctype,
    role_tags: selectedRoles.value.map((role) => ({
      doctype: "Party Role Tag",
      party_role: role,
    })),
  }
  if (isContact.value) {
    doc.company = companySelection.value?.value || null
  }
  if (props.name) {
    saveResource.submit({ doc })
  } else {
    insertResource.submit({ doc })
  }
}
</script>

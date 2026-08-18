<template>
  <Dialog
    :modelValue="modelValue"
    @update:modelValue="$emit('update:modelValue', $event)"
    :options="{ title: title, size: 'xl' }"
  >
    <!-- Own title block: the app's display face, with a line saying what this
         record is for, so the form is not a bare grid of boxes. The dialog's
         own close button and title semantics are kept. -->
    <template #body-title>
      <div class="min-w-0">
        <div class="aura-eyebrow">{{ isContact ? "Person" : "Company" }}</div>
        <h3 class="mt-0.5 font-display text-lg font-semibold text-carbon">
          {{ title }}
        </h3>
        <p class="mt-1 text-xs font-normal text-muted">{{ subtitle }}</p>
      </div>
    </template>

    <template #body-content>
      <div v-if="loading" class="py-10 text-center text-sm text-muted">
        Loading…
      </div>
      <div v-else class="space-y-5">
        <div class="grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2">
          <div v-for="field in fields" :key="field.fieldname" class="space-y-1.5">
            <label class="aura-eyebrow block" :for="`party-${field.fieldname}`">
              {{ field.label }}
              <span v-if="field.required" class="text-accent">*</span>
            </label>
            <FormControl
              :id="`party-${field.fieldname}`"
              :type="field.type || 'text'"
              size="md"
              variant="outline"
              v-model="form[field.fieldname]"
              :required="field.required"
            />
          </div>

          <div v-if="isContact" class="space-y-1.5 sm:col-span-2">
            <label class="aura-eyebrow block" for="party-company">Company</label>
            <FormControl
              id="party-company"
              type="autocomplete"
              size="md"
              variant="outline"
              :options="companyOptions"
              v-model="companySelection"
              placeholder="No company"
            />
          </div>
        </div>

        <!-- Role tags drive what the rest of the form asks for, so they sit
             above the conditional sections, not buried at the bottom. -->
        <div class="border-t border-hairline pt-4">
          <div class="aura-eyebrow">Role Tags</div>
          <div class="mt-2 flex flex-wrap gap-2">
            <div
              v-for="role in availableRoles"
              :key="role"
              class="flex items-center rounded-pill border px-3 py-1.5 transition-colors"
              :class="
                selectedRoles.includes(role)
                  ? 'border-carbon bg-canvas'
                  : 'border-hairline bg-paper'
              "
            >
              <Checkbox
                :label="role"
                :modelValue="selectedRoles.includes(role)"
                @update:modelValue="toggleRole(role, $event)"
              />
            </div>
            <p v-if="!availableRoles.length" class="text-xs text-faint">
              No roles defined yet.
            </p>
          </div>
        </div>

        <div v-if="showFreelancerPaperwork" class="border-t border-hairline pt-4">
          <div class="flex flex-wrap items-baseline gap-2">
            <div class="aura-eyebrow">Freelancer Paperwork</div>
            <span class="text-xs text-faint">
              Blank fields print as gaps on the contract.
            </span>
          </div>
          <div class="mt-2 grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2">
            <div
              v-for="field in FREELANCER_FIELDS"
              :key="field.fieldname"
              class="space-y-1.5"
            >
              <label class="aura-eyebrow block" :for="`party-${field.fieldname}`">
                {{ field.label }}
              </label>
              <FormControl
                :id="`party-${field.fieldname}`"
                :type="field.type || 'text'"
                size="md"
                variant="outline"
                v-model="form[field.fieldname]"
              />
            </div>
          </div>
        </div>

        <div class="border-t border-hairline pt-4">
          <div class="aura-eyebrow">Bank</div>
          <div class="mt-2 grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2">
            <div class="space-y-1.5">
              <label class="aura-eyebrow block" for="party-bank_name">Bank Name</label>
              <FormControl
                id="party-bank_name"
                type="select"
                size="md"
                variant="outline"
                :options="bankOptions"
                v-model="form.bank_name"
              />
            </div>
            <div class="space-y-1.5">
              <label class="aura-eyebrow block" for="party-bank_account_number">
                Bank Account Number
              </label>
              <FormControl
                id="party-bank_account_number"
                type="text"
                size="md"
                variant="outline"
                class="aura-num"
                v-model="form.bank_account_number"
              />
            </div>
            <div class="space-y-1.5 sm:col-span-2">
              <label class="aura-eyebrow block" for="party-bank_account_name">
                Bank Account Name
              </label>
              <FormControl
                id="party-bank_account_name"
                type="text"
                size="md"
                variant="outline"
                v-model="form.bank_account_name"
              />
            </div>
          </div>
        </div>

        <div class="space-y-1.5 border-t border-hairline pt-4">
          <label class="aura-eyebrow block" for="party-notes">Notes</label>
          <FormControl
            id="party-notes"
            type="textarea"
            size="md"
            variant="outline"
            v-model="form.notes"
          />
        </div>

        <ErrorMessage :message="saveError" />
      </div>
    </template>

    <template #actions>
      <div class="flex items-center justify-end gap-2 border-t border-hairline pt-4">
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
import { VN_BANKS } from "../data/banks"
import { frappeErrorMessage } from "../utils/frappeError"

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

// One line under the title, saying why the fields below matter.
const subtitle = computed(() =>
  isContact.value
    ? "People carry their own paperwork: CCCD, tax code and bank."
    : "Companies hold tax code, address and bank details for contracts."
)

const COMPANY_FIELDS = [
  { fieldname: "company_name", label: "Company Name", required: true },
  { fieldname: "tax_code", label: "Tax Code" },
  { fieldname: "phone", label: "Phone" },
  { fieldname: "email", label: "Email", type: "email" },
  { fieldname: "website", label: "Website" },
  { fieldname: "address", label: "Address" },
]

const CONTACT_FIELDS = [
  { fieldname: "full_name", label: "Full Name", required: true },
  { fieldname: "phone", label: "Phone / Zalo", required: true },
  { fieldname: "email", label: "Email", type: "email" },
]

const FREELANCER_FIELDS = [
  { fieldname: "id_number", label: "ID Number (CCCD)" },
  { fieldname: "date_of_birth", label: "Date of Birth", type: "date" },
  { fieldname: "tax_code", label: "Personal Tax Code" },
  { fieldname: "permanent_address", label: "Permanent Address" },
  { fieldname: "contact_address", label: "Contact Address" },
]

// Freelancers are people; the server rejects this tag on companies.
const ROLES_NOT_FOR_COMPANIES = ["Freelancer"]

const fields = computed(() =>
  isContact.value ? CONTACT_FIELDS : COMPANY_FIELDS
)

const bankOptions = ["", ...VN_BANKS]

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

const availableRoles = computed(() => {
  const all = (partyRoles.data || []).map((r) => r.name)
  return isContact.value
    ? all
    : all.filter((r) => !ROLES_NOT_FOR_COMPANIES.includes(r))
})

const showFreelancerPaperwork = computed(
  () => isContact.value && selectedRoles.value.includes("Freelancer")
)

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
  saveError.value = frappeErrorMessage(err)
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

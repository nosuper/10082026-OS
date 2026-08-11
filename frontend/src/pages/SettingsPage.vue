<template>
  <div class="mx-auto max-w-xl px-4 py-6">
    <h1 class="mb-4 text-lg font-semibold text-gray-900">Company Settings</h1>

    <div v-if="denied" class="rounded-md border bg-gray-50 px-3 py-2 text-sm text-gray-600">
      Only the founder can view company settings.
    </div>

    <div v-else class="rounded-lg border bg-white p-4">
      <label class="block text-sm font-medium text-gray-800">
        Global margin floor %
      </label>
      <p class="mt-1 text-xs text-gray-500">
        Quotes whose margin falls below this warn every role — without
        revealing where the number comes from. 0 turns the warning off.
      </p>
      <div class="mt-3 flex items-center gap-2">
        <input
          v-model.number="floorPct"
          type="number"
          min="0"
          step="0.5"
          class="w-28 rounded border-gray-200 px-2 py-1 text-right text-sm"
        />
        <Button variant="solid" :loading="saver.loading" @click="save">
          Save
        </Button>
        <span v-if="saved" class="text-xs text-green-700">Saved.</span>
      </div>
      <hr class="my-5" />

      <label class="block text-sm font-medium text-gray-800">
        Quote silence nudge (days)
      </label>
      <p class="mt-1 text-xs text-gray-500">
        A sent quote with no reply after this many days is flagged on the
        deal board. 0 turns the nudge off.
      </p>
      <div class="mt-3 flex items-center gap-2">
        <input
          v-model.number="silenceDays"
          type="number"
          min="0"
          step="1"
          class="w-28 rounded border-gray-200 px-2 py-1 text-right text-sm"
        />
        <Button variant="solid" :loading="silenceSaver.loading" @click="saveSilence">
          Save
        </Button>
        <span v-if="silenceSaved" class="text-xs text-green-700">Saved.</span>
      </div>

      <ErrorMessage class="mt-2" :message="error" />
    </div>

    <!--
      What a client reads at the top of every quote. Rendered live, so
      editing this changes quotes already sent — see
      docs/adr/0002-quote-branding-renders-live.md.
    -->
    <div v-if="!denied" class="mt-4 rounded-lg border bg-white p-4">
      <h2 class="text-sm font-semibold text-gray-800">Company identity</h2>
      <p class="mt-1 text-xs text-gray-500">
        Printed on every quote page and PDF. These render live — changing
        one updates quotes already sent, without making a new version. An
        empty field prints nothing at all.
      </p>

      <div class="mt-3 flex flex-wrap items-center gap-3">
        <img
          v-if="company.logo"
          :src="company.logo"
          alt="Logo"
          class="max-h-12 max-w-40 rounded border bg-white p-1"
        />
        <!-- Public on purpose: a client with no account has to load it,
             and a private file would 404 on the quote page. -->
        <FileUploader
          :file-types="'image/*'"
          :upload-args="{ private: false }"
          @success="onLogo"
          @failure="onFail"
        >
          <template #default="{ openFileSelector, uploading }">
            <Button :loading="uploading" @click="openFileSelector">
              {{ company.logo ? "Replace logo" : "Upload logo" }}
            </Button>
          </template>
        </FileUploader>
        <button
          v-if="company.logo"
          class="text-xs text-gray-500 underline"
          @click="company.logo = null"
        >
          Remove
        </button>
      </div>
      <p class="mt-1 text-xs text-gray-500">
        Uploaded public, because a client with no account has to be able to
        load it.
      </p>

      <div class="mt-4 grid gap-3 sm:grid-cols-2">
        <label v-for="field in IDENTITY_FIELDS" :key="field.name" class="text-xs text-gray-600">
          {{ field.label }}
          <input
            v-model="company[field.name]"
            class="mt-0.5 block w-full rounded border-gray-200 px-2 py-1 text-sm"
            :placeholder="field.placeholder || ''"
          />
        </label>
      </div>

      <div class="mt-4 flex items-center gap-2">
        <Button variant="solid" :loading="companySaver.loading" @click="saveCompany">
          Save
        </Button>
        <span v-if="companySaved" class="text-xs text-green-700">Saved.</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue"
import { Button, ErrorMessage, FileUploader, createResource } from "frappe-ui"
import { frappeErrorMessage } from "../utils/frappeError"

// Mirrors auraos.lib.quote.COMPANY_FIELDS, minus the logo, which has its
// own uploader. Drift is only caught in one direction: a field added
// here and not there is refused by name on save, but a field added there
// and not here is simply uneditable from this screen.
const IDENTITY_FIELDS = [
  { name: "company_name", label: "Company name" },
  { name: "tax_code", label: "Tax code" },
  { name: "address", label: "Address" },
  { name: "phone", label: "Phone" },
  { name: "email", label: "Email" },
  { name: "website", label: "Website" },
  { name: "bank_name", label: "Bank" },
  { name: "bank_account_number", label: "Bank account number" },
  { name: "bank_account_name", label: "Bank account holder" },
  {
    name: "signatory_name",
    label: "Signatory name",
    placeholder: "Printed on the PDF signature block",
  },
  { name: "signatory_title", label: "Signatory title" },
]

const floorPct = ref(0)
const denied = ref(false)
const saved = ref(false)
const error = ref("")

createResource({
  url: "auraos.api.get_margin_floor",
  auto: true,
  onSuccess(value) {
    floorPct.value = value
  },
  onError() {
    // Producer sessions have no read permission on the settings single.
    denied.value = true
  },
})

const saver = createResource({
  url: "auraos.api.set_margin_floor",
  onSuccess(value) {
    floorPct.value = value
    saved.value = true
    error.value = ""
  },
  onError(err) {
    saved.value = false
    error.value = frappeErrorMessage(err)
  },
})

function save() {
  saved.value = false
  saver.submit({ pct: floorPct.value || 0 })
}

const silenceDays = ref(5)
const silenceSaved = ref(false)

createResource({
  url: "auraos.api.get_quote_silence_days",
  auto: true,
  onSuccess(value) {
    silenceDays.value = value
  },
  onError() {
    denied.value = true
  },
})

const silenceSaver = createResource({
  url: "auraos.api.set_quote_silence_days",
  onSuccess(value) {
    silenceDays.value = value
    silenceSaved.value = true
    error.value = ""
  },
  onError(err) {
    silenceSaved.value = false
    error.value = frappeErrorMessage(err)
  },
})

function saveSilence() {
  silenceSaved.value = false
  silenceSaver.submit({ days: silenceDays.value || 0 })
}

// -- company identity (T6.1a) --

const company = reactive({ logo: null })
const companySaved = ref(false)

createResource({
  url: "auraos.api.get_company_identity",
  auto: true,
  onSuccess(stored) {
    Object.assign(company, stored)
  },
  onError() {
    denied.value = true
  },
})

const companySaver = createResource({
  url: "auraos.api.set_company_identity",
  onSuccess(stored) {
    Object.assign(company, stored)
    companySaved.value = true
    error.value = ""
  },
  onError(err) {
    companySaved.value = false
    error.value = frappeErrorMessage(err)
  },
})

function onLogo(file) {
  error.value = ""
  company.logo = file.file_url
  companySaved.value = false
}

function onFail(err) {
  error.value = frappeErrorMessage(err) || String(err)
}

function saveCompany() {
  companySaved.value = false
  companySaver.submit({ values: { ...company } })
}
</script>

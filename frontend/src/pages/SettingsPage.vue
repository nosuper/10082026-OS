<template>
  <div class="mx-auto max-w-xl px-4 py-6">
    <h1 class="mb-4 text-lg font-semibold text-gray-900">Company Settings</h1>

    <!--
      T3.5 (issue #29): the page is no longer a founder-only door. The
      lists a producer manages are drawn here, the company numbers below
      only for a session that can read them - the margin floor stays
      founder-only whatever else this page grows.
    -->
    <div
      v-if="denied && !manageable.length"
      class="rounded-md border bg-gray-50 px-3 py-2 text-sm text-gray-600"
    >
      Only the founder can view company settings.
    </div>

    <div v-if="manageable.length" class="mb-4 rounded-lg border bg-white p-4">
      <h2 class="text-sm font-semibold text-gray-800">Lists</h2>
      <p class="mt-1 text-xs text-gray-500">
        The values the deal form offers. Renaming one carries every deal
        already on it across; a value still on a deal cannot be removed -
        rename it, or clear it from those deals first. Tags are not here:
        both roles invent those while editing a deal.
      </p>
      <div class="mt-4 grid gap-5 sm:grid-cols-2">
        <VocabularyList
          v-for="vocab in manageable"
          :key="vocab.key"
          :vocab="vocab"
          @updated="vocabularies = $event"
        />
      </div>
    </div>

    <div v-if="!denied" class="rounded-lg border bg-white p-4">
      <label class="flex items-center gap-2 text-sm font-medium text-gray-800">
        Global margin floor %
        <span
          v-if="!floorPct"
          class="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-normal text-amber-800"
        >
          currently off
        </span>
      </label>
      <p class="mt-1 text-xs text-gray-500">
        Quotes whose margin falls below this warn every role - without
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

      <label class="flex items-center gap-2 text-sm font-medium text-gray-800">
        Quote silence nudge (days)
        <span
          v-if="!silenceDays"
          class="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-normal text-amber-800"
        >
          currently off
        </span>
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
      <hr class="my-5" />

      <label class="flex items-center gap-2 text-sm font-medium text-gray-800">
        Payment terms (days)
        <span
          v-if="!paymentTermsDays"
          class="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-normal text-amber-800"
        >
          currently off
        </span>
      </label>
      <p class="mt-1 text-xs text-gray-500">
        A payment milestone still uncollected this many days after it falls
        due is flagged on the jobs board. 0 turns the nudge off.
      </p>
      <div class="mt-3 flex items-center gap-2">
        <input
          v-model.number="paymentTermsDays"
          type="number"
          min="0"
          step="1"
          class="w-28 rounded border-gray-200 px-2 py-1 text-right text-sm"
        />
        <Button variant="solid" :loading="termsSaver.loading" @click="saveTerms">
          Save
        </Button>
        <span v-if="termsSaved" class="text-xs text-green-700">Saved.</span>
      </div>
      <hr class="my-5" />

      <label class="block text-sm font-medium text-gray-800">
        Tier thresholds (VND)
      </label>
      <p class="mt-1 text-xs text-gray-500">
        Every deal's tier is derived (playbook §2.2): Brand positioning -
        or a positioning-segment job type - means Tier 3 whatever it
        pays; otherwise Tier 2 from the first number, Tier 3 from the
        second. Hand-setting a tier on a deal pins it against the rules.
      </p>
      <div class="mt-3 flex flex-wrap items-center gap-2">
        <label class="text-xs text-gray-500">
          Tier 2 from
          <VndInput
            v-model="tier2"
            class="mt-0.5 block w-36 rounded border-gray-200 px-2 py-1 text-right text-sm tabular-nums"
          />
        </label>
        <label class="text-xs text-gray-500">
          Tier 3 from
          <VndInput
            v-model="tier3"
            class="mt-0.5 block w-36 rounded border-gray-200 px-2 py-1 text-right text-sm tabular-nums"
          />
        </label>
        <Button
          class="self-end"
          variant="solid"
          :loading="tierSaver.loading"
          @click="saveTiers"
        >
          Save
        </Button>
        <span v-if="tiersSaved" class="self-end text-xs text-green-700">Saved.</span>
      </div>
      <hr class="my-5" />

      <label class="block text-sm font-medium text-gray-800">
        Positioning mix targets (%)
      </label>
      <p class="mt-1 text-xs text-gray-500">
        The cash / bridge / brand allocation lens (playbook §6.1) - tune
        it as the company moves phases. The deal form and the
        <a href="/aura/sop/deals" target="_blank" rel="noopener noreferrer" class="underline">SOP page</a>
        read these live.
      </p>
      <div class="mt-3 flex flex-wrap items-end gap-2">
        <label
          v-for="key in ['cash', 'bridge', 'brand']"
          :key="key"
          class="text-xs capitalize text-gray-500"
        >
          {{ key }}
          <input
            v-model.number="mixTargets[key]"
            type="number"
            min="0"
            max="100"
            step="5"
            class="mt-0.5 block w-20 rounded border-gray-200 px-2 py-1 text-right text-sm"
          />
        </label>
        <span
          class="pb-1.5 text-xs"
          :class="mixSum === 100 ? 'text-gray-400' : 'text-amber-700'"
        >
          sums to {{ mixSum }}%
        </span>
      </div>

      <div class="mt-4">
        <label class="block text-sm font-medium text-gray-800">
          Positioning-segment job types
        </label>
        <p class="mt-1 text-xs text-gray-500">
          Deals of these types derive Tier 3 whatever they pay - even
          when their positioning is left empty.
        </p>
        <div class="mt-2 flex flex-wrap gap-x-4 gap-y-1.5">
          <label
            v-for="row in typeRows"
            :key="row.name"
            class="flex items-center gap-1.5 text-sm text-gray-700"
          >
            <input
              type="checkbox"
              class="rounded border-gray-300"
              :checked="!!row.is_positioning"
              @change="row.is_positioning = $event.target.checked ? 1 : 0"
            />
            {{ row.name }}
          </label>
          <span v-if="!typeRows.length" class="text-xs text-gray-400">
            No project types yet.
          </span>
        </div>
      </div>
      <div class="mt-3 flex items-center gap-2">
        <Button variant="solid" :loading="positioningSaver.loading" @click="savePositioning">
          Save
        </Button>
        <span v-if="positioningSaved" class="text-xs text-green-700">Saved.</span>
      </div>

      <ErrorMessage class="mt-2" :message="error" />
    </div>

    <!--
      What a client reads at the top of every quote. Rendered live, so
      editing this changes quotes already sent - see
      docs/adr/0002-quote-branding-renders-live.md.
    -->
    <div v-if="!denied" class="mt-4 rounded-lg border bg-white p-4">
      <h2 class="text-sm font-semibold text-gray-800">Company identity</h2>
      <p class="mt-1 text-xs text-gray-500">
        Printed on every quote page and PDF. These render live - changing
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
import { computed, reactive, ref } from "vue"
import { Button, ErrorMessage, FileUploader, createResource } from "frappe-ui"
import VndInput from "../components/VndInput.vue"
import VocabularyList from "../components/VocabularyList.vue"
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

// -- managed lists (T3.5, issue #29) --
//
// Sections, not a page-level gate: the endpoint answers for every list
// with what this session may do to it, and only the manageable ones are
// drawn. A producer therefore gets the sources section and no
// project-type section at all, rather than one that refuses when used.
const vocabularies = ref([])
const manageable = computed(() =>
  vocabularies.value.filter((vocab) => vocab.can_manage)
)

createResource({
  url: "auraos.api.get_vocabularies",
  auto: true,
  onSuccess(rows) {
    vocabularies.value = rows
  },
  onError() {},
})

const floorPct = ref(0)
// The founder-only half of this page: the margin floor, the nudges, the
// tier dials and the company identity all read the settings single, so
// one refusal from it hides the lot.
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

// -- tier thresholds (Phase B) --

const tier2 = ref("")
const tier3 = ref("")
const tiersSaved = ref(false)

createResource({
  url: "auraos.api.get_tier_thresholds",
  auto: true,
  onSuccess(value) {
    tier2.value = value.tier2
    tier3.value = value.tier3
  },
  onError() {
    denied.value = true
  },
})

const tierSaver = createResource({
  url: "auraos.api.set_tier_thresholds",
  onSuccess(value) {
    tier2.value = value.tier2
    tier3.value = value.tier3
    tiersSaved.value = true
    error.value = ""
  },
  onError(err) {
    tiersSaved.value = false
    error.value = frappeErrorMessage(err)
  },
})

function saveTiers() {
  tiersSaved.value = false
  tierSaver.submit({ tier2: tier2.value || 0, tier3: tier3.value || 0 })
}

// -- positioning rules (Phase B round 3) --

const mixTargets = reactive({ cash: 70, bridge: 20, brand: 10 })
const typeRows = ref([])
const positioningSaved = ref(false)

const mixSum = computed(
  () =>
    (mixTargets.cash || 0) + (mixTargets.bridge || 0) + (mixTargets.brand || 0)
)

function applyPositioningRules(value) {
  Object.assign(mixTargets, value.mix)
  typeRows.value = value.project_types
}

createResource({
  url: "auraos.api.get_positioning_rules",
  auto: true,
  onSuccess: applyPositioningRules,
  onError() {
    denied.value = true
  },
})

const positioningSaver = createResource({
  url: "auraos.api.set_positioning_rules",
  onSuccess(value) {
    applyPositioningRules(value)
    positioningSaved.value = true
    error.value = ""
  },
  onError(err) {
    positioningSaved.value = false
    error.value = frappeErrorMessage(err)
  },
})

function savePositioning() {
  positioningSaved.value = false
  positioningSaver.submit({
    cash: mixTargets.cash || 0,
    bridge: mixTargets.bridge || 0,
    brand: mixTargets.brand || 0,
    positioning_types: typeRows.value
      .filter((row) => row.is_positioning)
      .map((row) => row.name),
  })
}

const paymentTermsDays = ref(7)
const termsSaved = ref(false)

createResource({
  url: "auraos.api.get_payment_terms_days",
  auto: true,
  onSuccess(value) {
    paymentTermsDays.value = value
  },
  onError() {
    denied.value = true
  },
})

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

const termsSaver = createResource({
  url: "auraos.api.set_payment_terms_days",
  onSuccess(value) {
    paymentTermsDays.value = value
    termsSaved.value = true
    error.value = ""
  },
  onError(err) {
    termsSaved.value = false
    error.value = frappeErrorMessage(err)
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

function saveTerms() {
  termsSaved.value = false
  termsSaver.submit({ days: paymentTermsDays.value || 0 })
}

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

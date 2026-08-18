<template>
  <div class="space-y-4">
    <!-- Page head: what this screen is for, in words, before any field. -->
    <div class="flex flex-wrap items-end gap-x-3 gap-y-1">
      <h1 class="text-xl font-semibold text-carbon">Company settings</h1>
      <p class="text-sm text-muted">
        Studio-wide defaults - deals, quotes and the jobs board read these live.
      </p>
    </div>

    <!-- The founder gate. Any settings call failing replaces the whole body:
         a producer session must never see a settings field, even empty. -->
    <div v-if="denied" class="aura-card flex items-start gap-2 p-4 text-sm text-muted">
      <FeatherIcon name="lock" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-faint" aria-hidden="true" />
      <span>Only the founder can view company settings.</span>
    </div>

    <div v-else class="space-y-3">
      <!-- Row 1: the three single-number defaults. Each saves on its own. -->
      <div class="grid gap-3 lg:grid-cols-3">
        <BentoCard title="Global margin floor">
          <template #action>
            <StatusPill v-if="!floorPct" label="currently off" tone="warn" />
          </template>
          <div class="flex items-center gap-2 rounded-[10px] border border-hairline bg-paper px-3 py-2 focus-within:border-accent/50">
            <input
              v-model.number="floorPct"
              type="number"
              min="0"
              step="0.5"
              class="aura-num w-full bg-transparent text-sm text-carbon outline-none"
            />
            <span class="shrink-0 text-xs text-muted">%</span>
          </div>
          <p class="mt-2 text-xs leading-relaxed text-muted">
            Quotes whose margin falls below this warn every role - without
            revealing where the number comes from. 0 turns the warning off.
          </p>
          <template #footer>
            <div class="flex items-center gap-2">
              <Button variant="solid" :loading="saver.loading" @click="save">
                Save
              </Button>
              <span v-if="saved" class="text-xs text-ok">Saved.</span>
            </div>
          </template>
        </BentoCard>

        <BentoCard title="Quote silence nudge">
          <template #action>
            <StatusPill v-if="!silenceDays" label="currently off" tone="warn" />
          </template>
          <div class="flex items-center gap-2 rounded-[10px] border border-hairline bg-paper px-3 py-2 focus-within:border-accent/50">
            <input
              v-model.number="silenceDays"
              type="number"
              min="0"
              step="1"
              class="aura-num w-full bg-transparent text-sm text-carbon outline-none"
            />
            <span class="shrink-0 text-xs text-muted">days</span>
          </div>
          <p class="mt-2 text-xs leading-relaxed text-muted">
            A sent quote with no reply after this many days is flagged on the
            deal board. 0 turns the nudge off.
          </p>
          <template #footer>
            <div class="flex items-center gap-2">
              <Button variant="solid" :loading="silenceSaver.loading" @click="saveSilence">
                Save
              </Button>
              <span v-if="silenceSaved" class="text-xs text-ok">Saved.</span>
            </div>
          </template>
        </BentoCard>

        <BentoCard title="Payment terms">
          <template #action>
            <StatusPill v-if="!paymentTermsDays" label="currently off" tone="warn" />
          </template>
          <div class="flex items-center gap-2 rounded-[10px] border border-hairline bg-paper px-3 py-2 focus-within:border-accent/50">
            <input
              v-model.number="paymentTermsDays"
              type="number"
              min="0"
              step="1"
              class="aura-num w-full bg-transparent text-sm text-carbon outline-none"
            />
            <span class="shrink-0 text-xs text-muted">days</span>
          </div>
          <p class="mt-2 text-xs leading-relaxed text-muted">
            A payment milestone still uncollected this many days after it falls
            due is flagged on the jobs board. 0 turns the nudge off.
          </p>
          <template #footer>
            <div class="flex items-center gap-2">
              <Button variant="solid" :loading="termsSaver.loading" @click="saveTerms">
                Save
              </Button>
              <span v-if="termsSaved" class="text-xs text-ok">Saved.</span>
            </div>
          </template>
        </BentoCard>
      </div>

      <!-- Row 2: the two rule cards - tier derivation and the mix lens. -->
      <div class="grid gap-3 lg:grid-cols-3">
        <BentoCard title="Tier thresholds" subtitle="Playbook §2.2">
          <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <div>
              <div class="aura-eyebrow">Tier 2 from</div>
              <div class="mt-1.5 flex items-center gap-2 rounded-[10px] border border-hairline bg-paper px-3 py-2 focus-within:border-accent/50">
                <VndInput
                  v-model="tier2"
                  class="aura-num w-full bg-transparent text-right text-sm text-carbon outline-none"
                />
                <span class="shrink-0 text-xs text-muted">VND</span>
              </div>
            </div>
            <div>
              <div class="aura-eyebrow">Tier 3 from</div>
              <div class="mt-1.5 flex items-center gap-2 rounded-[10px] border border-hairline bg-paper px-3 py-2 focus-within:border-accent/50">
                <VndInput
                  v-model="tier3"
                  class="aura-num w-full bg-transparent text-right text-sm text-carbon outline-none"
                />
                <span class="shrink-0 text-xs text-muted">VND</span>
              </div>
            </div>
          </div>
          <p class="mt-2 text-xs leading-relaxed text-muted">
            Every deal's tier is derived: Brand positioning - or a
            positioning-segment job type - means Tier 3 whatever it pays;
            otherwise Tier 2 from the first number, Tier 3 from the second.
            Hand-setting a tier on a deal pins it against the rules.
          </p>
          <template #footer>
            <div class="flex items-center gap-2">
              <Button variant="solid" :loading="tierSaver.loading" @click="saveTiers">
                Save
              </Button>
              <span v-if="tiersSaved" class="text-xs text-ok">Saved.</span>
            </div>
          </template>
        </BentoCard>

        <!-- Mix targets and the positioning job types share one save: the
             server writes them in a single call. -->
        <BentoCard class="lg:col-span-2" title="Positioning mix targets" subtitle="Playbook §6.1">
          <div class="grid gap-3 sm:grid-cols-3">
            <div v-for="key in ['cash', 'bridge', 'brand']" :key="key">
              <div class="aura-eyebrow">{{ key }}</div>
              <div class="mt-1.5 flex items-center gap-2 rounded-[10px] border border-hairline bg-paper px-3 py-2 focus-within:border-accent/50">
                <input
                  v-model.number="mixTargets[key]"
                  type="number"
                  min="0"
                  max="100"
                  step="5"
                  class="aura-num w-full bg-transparent text-right text-sm text-carbon outline-none"
                />
                <span class="shrink-0 text-xs text-muted">%</span>
              </div>
            </div>
          </div>

          <div class="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span
              class="text-xs"
              :class="mixSum === 100 ? 'text-faint' : 'text-warn'"
            >
              sums to <span class="aura-num">{{ mixSum }}%</span>
            </span>
            <p class="min-w-0 flex-1 text-xs leading-relaxed text-muted">
              The cash / bridge / brand allocation lens - tune it as the company
              moves phases. The deal form and the
              <a
                href="/aura/sop/deals"
                target="_blank"
                rel="noopener noreferrer"
                class="text-accent underline underline-offset-2 hover:text-accent-ink"
              >
                SOP page
              </a>
              read these live.
            </p>
          </div>

          <div class="mt-3 border-t border-hairline pt-3">
            <div class="aura-eyebrow">Positioning-segment job types</div>
            <p class="mt-1 text-xs leading-relaxed text-muted">
              Deals of these types derive Tier 3 whatever they pay - even when
              their positioning is left empty.
            </p>
            <div class="mt-2 flex flex-wrap gap-x-4 gap-y-2">
              <label
                v-for="row in typeRows"
                :key="row.name"
                class="flex items-center gap-2 text-sm text-carbon"
              >
                <input
                  type="checkbox"
                  class="rounded border-hairline text-accent focus:ring-accent/30"
                  :checked="!!row.is_positioning"
                  @change="row.is_positioning = $event.target.checked ? 1 : 0"
                />
                {{ row.name }}
              </label>
              <span v-if="!typeRows.length" class="text-xs text-faint">
                No project types yet.
              </span>
            </div>
          </div>

          <template #footer>
            <div class="flex items-center gap-2">
              <Button variant="solid" :loading="positioningSaver.loading" @click="savePositioning">
                Save
              </Button>
              <span v-if="positioningSaved" class="text-xs text-ok">Saved.</span>
            </div>
          </template>
        </BentoCard>
      </div>

      <!--
        What a client reads at the top of every quote. Rendered live, so
        editing this changes quotes already sent - see
        docs/adr/0002-quote-branding-renders-live.md.
      -->
      <BentoCard title="Company identity" subtitle="Printed on every quote page and PDF">
        <p class="text-xs leading-relaxed text-muted">
          These render live - changing one updates quotes already sent, without
          making a new version. An empty field prints nothing at all.
        </p>

        <div class="mt-3 flex flex-wrap items-center gap-3">
          <img
            v-if="company.logo"
            :src="company.logo"
            alt="Logo"
            class="max-h-12 max-w-40 rounded-[10px] border border-hairline bg-paper p-1"
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
              <Button icon-left="upload" :loading="uploading" @click="openFileSelector">
                {{ company.logo ? "Replace logo" : "Upload logo" }}
              </Button>
            </template>
          </FileUploader>
          <button
            v-if="company.logo"
            class="text-xs text-muted underline underline-offset-2 hover:text-accent"
            @click="company.logo = null"
          >
            Remove
          </button>
          <p class="min-w-0 flex-1 text-xs leading-relaxed text-faint">
            Uploaded public, because a client with no account has to be able to
            load it.
          </p>
        </div>

        <div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div v-for="field in IDENTITY_FIELDS" :key="field.name">
            <div class="aura-eyebrow">{{ field.label }}</div>
            <div class="mt-1.5 rounded-[10px] border border-hairline bg-paper px-3 py-2 focus-within:border-accent/50">
              <input
                v-model="company[field.name]"
                class="w-full bg-transparent text-sm text-carbon outline-none placeholder:text-faint"
                :class="field.numeric ? 'aura-num' : ''"
                :placeholder="field.placeholder || ''"
              />
            </div>
          </div>
        </div>

        <template #footer>
          <div class="flex items-center gap-2">
            <Button variant="solid" :loading="companySaver.loading" @click="saveCompany">
              Save
            </Button>
            <span v-if="companySaved" class="text-xs text-ok">Saved.</span>
          </div>
        </template>
      </BentoCard>

      <ErrorMessage :message="error" />
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from "vue"
import { Button, ErrorMessage, FeatherIcon, FileUploader, createResource } from "frappe-ui"
import BentoCard from "../components/BentoCard.vue"
import StatusPill from "../components/StatusPill.vue"
import VndInput from "../components/VndInput.vue"
import { frappeErrorMessage } from "../utils/frappeError"

// Mirrors auraos.lib.quote.COMPANY_FIELDS, minus the logo, which has its
// own uploader. Drift is only caught in one direction: a field added
// here and not there is refused by name on save, but a field added there
// and not here is simply uneditable from this screen.
// `numeric` is presentation only: digit-only fields read in the ledger face.
const IDENTITY_FIELDS = [
  { name: "company_name", label: "Company name" },
  { name: "tax_code", label: "Tax code", numeric: true },
  { name: "address", label: "Address" },
  { name: "phone", label: "Phone", numeric: true },
  { name: "email", label: "Email" },
  { name: "website", label: "Website" },
  { name: "bank_name", label: "Bank" },
  { name: "bank_account_number", label: "Bank account number", numeric: true },
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

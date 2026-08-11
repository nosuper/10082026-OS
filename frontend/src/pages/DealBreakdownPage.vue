<template>
  <div class="px-4 py-6">
    <div class="mb-4 flex items-center gap-3">
      <router-link to="/deals" class="text-sm text-gray-500 hover:text-gray-800">
        ← Deals
      </router-link>
      <h1 class="text-lg font-semibold text-gray-900">
        {{ deal.data?.title || name }}
      </h1>
      <span
        v-if="deal.data"
        class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700"
      >
        {{ deal.data.stage }}
      </span>
      <div class="ml-auto flex items-center gap-2">
        <Button variant="solid" :loading="saving" @click="save">Save</Button>
      </div>
    </div>

    <div
      v-if="live?.floor_breached"
      class="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
    >
      ⚠ Margin is below the company floor — this quote is flagged as
      unprofitable.
    </div>

    <div v-if="deal.loading" class="py-12 text-center text-sm text-gray-500">
      Loading…
    </div>

    <template v-else-if="deal.data">
      <!-- Cost lines -->
      <div class="mb-2 flex items-center gap-2">
        <h2 class="text-sm font-semibold text-gray-800">Cost lines</h2>
        <Button class="ml-auto" @click="addLine">Add line</Button>
      </div>
      <div class="overflow-x-auto rounded-lg border">
        <table class="w-full min-w-[1700px] text-sm">
          <thead class="bg-gray-50 text-left text-xs text-gray-600">
            <tr>
              <th class="px-2 py-2 font-medium">Description</th>
              <th class="px-2 py-2 font-medium">Item Category</th>
              <th class="px-2 py-2 font-medium">Cost Phase</th>
              <th class="px-2 py-2 font-medium">Source Type</th>
              <th class="px-2 py-2 font-medium">Source Contact</th>
              <th class="px-2 py-2 font-medium">Package</th>
              <th class="px-2 py-2 font-medium">Qty</th>
              <th class="px-2 py-2 font-medium">Unit</th>
              <th class="px-2 py-2 font-medium">Qty</th>
              <th class="px-2 py-2 font-medium">Unit</th>
              <th class="px-2 py-2 text-right font-medium">Unit Price</th>
              <th class="px-2 py-2 font-medium">Tax Type</th>
              <th class="px-2 py-2 text-right font-medium">Vendor MF %</th>
              <th class="px-2 py-2 text-right font-medium">Markup %</th>
              <th class="px-2 py-2 text-right font-medium">Subtotal</th>
              <th class="px-2 py-2 text-right font-medium">Quote Price</th>
              <th class="px-2 py-2 text-right font-medium">Margin</th>
              <th class="px-2 py-2"></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(line, i) in state.lines"
              :key="i"
              class="border-t align-middle"
            >
              <td class="px-1 py-1">
                <input
                  v-model="line.description"
                  class="w-44 rounded border-gray-200 px-2 py-1 text-sm"
                  placeholder="Description"
                />
              </td>
              <td class="px-1 py-1">
                <input
                  v-model="line.item_category"
                  list="item-categories"
                  class="w-36 rounded border-gray-200 px-2 py-1 text-sm"
                  placeholder="Select or add"
                  @change="ensureItemCategory(line)"
                />
              </td>
              <td class="px-1 py-1">
                <select
                  v-model="line.cost_phase"
                  class="w-36 rounded border-gray-200 px-2 py-1 text-sm"
                >
                  <option value=""></option>
                  <option
                    v-for="phase in COST_PHASES"
                    :key="phase"
                    :value="phase"
                  >
                    {{ phase }}
                  </option>
                </select>
              </td>
              <td class="px-1 py-1">
                <select
                  v-model="line.source_type"
                  class="w-28 rounded border-gray-200 px-2 py-1 text-sm"
                >
                  <option value=""></option>
                  <option v-for="type in SOURCE_TYPES" :key="type" :value="type">
                    {{ type }}
                  </option>
                </select>
              </td>
              <td class="px-1 py-1">
                <select
                  v-model="line.source_contact"
                  class="w-40 rounded border-gray-200 px-2 py-1 text-sm"
                >
                  <option value=""></option>
                  <option
                    v-for="contact in contacts.data || []"
                    :key="contact.name"
                    :value="contact.name"
                  >
                    {{ contact.full_name }}
                  </option>
                </select>
              </td>
              <td class="px-1 py-1">
                <input
                  v-model="line.package"
                  list="package-titles"
                  class="w-36 rounded border-gray-200 px-2 py-1 text-sm"
                  placeholder="No package"
                  @change="ensurePackage(line.package)"
                />
              </td>
              <td class="px-1 py-1">
                <input
                  v-model.number="line.qty1"
                  type="number"
                  min="0"
                  class="w-16 rounded border-gray-200 px-2 py-1 text-right text-sm"
                />
              </td>
              <td class="px-1 py-1">
                <input
                  v-model="line.qty1_unit"
                  class="w-20 rounded border-gray-200 px-2 py-1 text-sm"
                  placeholder="người"
                />
              </td>
              <td class="px-1 py-1">
                <input
                  v-model.number="line.qty2"
                  type="number"
                  min="0"
                  class="w-16 rounded border-gray-200 px-2 py-1 text-right text-sm"
                />
              </td>
              <td class="px-1 py-1">
                <input
                  v-model="line.qty2_unit"
                  class="w-20 rounded border-gray-200 px-2 py-1 text-sm"
                  placeholder="ngày"
                />
              </td>
              <td class="px-1 py-1">
                <input
                  v-model.number="line.unit_price"
                  type="number"
                  min="0"
                  step="1000"
                  class="w-28 rounded border-gray-200 px-2 py-1 text-right text-sm"
                />
              </td>
              <td class="px-1 py-1">
                <select
                  v-model="line.tax_type"
                  class="w-32 rounded border-gray-200 px-2 py-1 text-sm"
                >
                  <option v-for="t in TAX_TYPES" :key="t" :value="t">
                    {{ t }}
                  </option>
                </select>
              </td>
              <td class="px-1 py-1">
                <input
                  v-model.number="line.vendor_mf_pct"
                  type="number"
                  min="0"
                  class="w-16 rounded border-gray-200 px-2 py-1 text-right text-sm"
                />
              </td>
              <td class="px-1 py-1">
                <input
                  v-model.number="line.markup_pct"
                  type="number"
                  min="0"
                  class="w-16 rounded border-gray-200 px-2 py-1 text-right text-sm"
                />
              </td>
              <td class="px-2 py-1 text-right tabular-nums text-gray-700">
                {{ vnd(live?.lines?.[i]?.subtotal) }}
              </td>
              <td class="px-2 py-1 text-right font-medium tabular-nums">
                {{ vnd(live?.lines?.[i]?.quote_price) }}
              </td>
              <td class="px-2 py-1 text-right tabular-nums text-gray-700">
                {{ vnd(live?.lines?.[i]?.margin) }}
              </td>
              <td class="px-1 py-1 whitespace-nowrap text-gray-400">
                <button
                  class="px-1 hover:text-gray-800 disabled:opacity-30"
                  :disabled="i === 0"
                  title="Move up"
                  @click="moveLine(i, -1)"
                >
                  ↑
                </button>
                <button
                  class="px-1 hover:text-gray-800 disabled:opacity-30"
                  :disabled="i === state.lines.length - 1"
                  title="Move down"
                  @click="moveLine(i, 1)"
                >
                  ↓
                </button>
                <button
                  class="px-1 hover:text-red-600"
                  title="Remove line"
                  @click="state.lines.splice(i, 1)"
                >
                  ✕
                </button>
              </td>
            </tr>
            <tr v-if="!state.lines.length">
              <td colspan="18" class="px-3 py-6 text-center text-gray-400">
                No cost lines yet — add the first one.
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <datalist id="package-titles">
        <option v-for="p in state.packages" :key="p.title" :value="p.title" />
      </datalist>
      <datalist id="item-categories">
        <option
          v-for="category in categories.data || []"
          :key="category.name"
          :value="category.name"
        />
      </datalist>

      <div class="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <!-- Packages -->
        <div class="lg:col-span-2">
          <div class="mb-2 flex items-center gap-2">
            <h2 class="text-sm font-semibold text-gray-800">
              Client-facing packages
            </h2>
            <Button class="ml-auto" @click="addPackage">Add package</Button>
          </div>
          <div class="overflow-x-auto rounded-lg border">
            <table class="w-full min-w-[640px] text-sm">
              <thead class="bg-gray-50 text-left text-xs text-gray-600">
                <tr>
                  <th class="px-2 py-2 font-medium">Title</th>
                  <th class="px-2 py-2 font-medium">Description</th>
                  <th class="px-2 py-2 text-right font-medium">Override</th>
                  <th class="px-2 py-2 text-right font-medium">Member Sum</th>
                  <th class="px-2 py-2 text-right font-medium">Price</th>
                  <th class="px-2 py-2 text-right font-medium">Variance</th>
                  <th class="px-2 py-2"></th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(pkg, i) in state.packages"
                  :key="i"
                  class="border-t align-middle"
                >
                  <td class="px-1 py-1">
                    <input
                      v-model="pkg.title"
                      class="w-40 rounded border-gray-200 px-2 py-1 text-sm"
                      placeholder="Human resources"
                    />
                  </td>
                  <td class="px-1 py-1">
                    <input
                      v-model="pkg.description"
                      class="w-full min-w-40 rounded border-gray-200 px-2 py-1 text-sm"
                      placeholder="What the client reads"
                    />
                  </td>
                  <td class="px-1 py-1">
                    <input
                      v-model.number="pkg.price_override"
                      type="number"
                      min="0"
                      step="1000"
                      class="w-32 rounded border-gray-200 px-2 py-1 text-right text-sm"
                      placeholder="auto"
                    />
                  </td>
                  <td class="px-2 py-1 text-right tabular-nums text-gray-700">
                    {{ vnd(livePackage(pkg.title)?.default_price) }}
                  </td>
                  <td class="px-2 py-1 text-right font-medium tabular-nums">
                    {{ vnd(livePackage(pkg.title)?.price) }}
                  </td>
                  <td
                    class="px-2 py-1 text-right tabular-nums"
                    :class="
                      livePackage(pkg.title)?.variance
                        ? 'font-medium text-amber-700'
                        : 'text-gray-400'
                    "
                  >
                    {{ vnd(livePackage(pkg.title)?.variance) }}
                  </td>
                  <td class="px-1 py-1 text-gray-400">
                    <button
                      class="px-1 hover:text-red-600"
                      title="Remove package"
                      @click="removePackage(i)"
                    >
                      ✕
                    </button>
                  </td>
                </tr>
                <tr v-if="!state.packages.length">
                  <td colspan="7" class="px-3 py-6 text-center text-gray-400">
                    No packages — the client would see raw lines.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Totals & founder block -->
        <div class="space-y-4">
          <div class="rounded-lg border p-4">
            <div class="mb-3 flex items-center gap-4">
              <label class="text-xs text-gray-600">
                Quote MF %
                <input
                  v-model.number="state.quote_mf_pct"
                  type="number"
                  min="0"
                  class="mt-1 w-20 rounded border-gray-200 px-2 py-1 text-right text-sm"
                />
              </label>
              <label class="text-xs text-gray-600">
                VAT %
                <input
                  v-model.number="state.vat_pct"
                  type="number"
                  min="0"
                  class="mt-1 w-20 rounded border-gray-200 px-2 py-1 text-right text-sm"
                />
              </label>
            </div>
            <dl class="space-y-1 text-sm">
              <div class="flex justify-between">
                <dt class="text-gray-600">Subtotal</dt>
                <dd class="tabular-nums">{{ vnd(live?.subtotal) }}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-gray-600">
                  Management fee ({{ state.quote_mf_pct }}%)
                </dt>
                <dd class="tabular-nums">{{ vnd(live?.management_fee) }}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-gray-600">VAT ({{ state.vat_pct }}%)</dt>
                <dd class="tabular-nums">{{ vnd(live?.vat) }}</dd>
              </div>
              <div class="flex justify-between border-t pt-1 font-semibold">
                <dt>Total</dt>
                <dd class="tabular-nums">{{ vnd(live?.total) }}</dd>
              </div>
              <div
                class="flex justify-between pt-2"
                :class="live?.floor_breached ? 'text-red-700' : 'text-green-700'"
              >
                <dt>
                  Margin
                  <span v-if="live?.margin_pct != null">
                    ({{ live.margin_pct.toFixed(1) }}%)
                  </span>
                </dt>
                <dd class="font-medium tabular-nums">{{ vnd(live?.margin) }}</dd>
              </div>
            </dl>
          </div>

          <div v-if="live?.founder" class="rounded-lg border p-4">
            <h3 class="mb-3 text-xs font-semibold uppercase text-gray-500">
              Founder only
            </h3>
            <label class="text-xs text-gray-600">
              Commission %
              <input
                v-model.number="state.commission_pct"
                type="number"
                min="0"
                class="mt-1 w-20 rounded border-gray-200 px-2 py-1 text-right text-sm"
              />
            </label>
            <dl class="mt-3 space-y-1 text-sm">
              <div class="flex justify-between">
                <dt class="text-gray-600">Commission (CMF)</dt>
                <dd class="tabular-nums">
                  {{ vnd(live.founder.total_commission) }}
                </dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-gray-600">CM (after commission)</dt>
                <dd class="tabular-nums">{{ vnd(live.founder.cm) }}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-gray-600">Lợi nhuận trước thuế</dt>
                <dd class="tabular-nums">
                  {{ vnd(live.founder.profit_before_tax) }}
                </dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-gray-600">TNDN (20%)</dt>
                <dd class="tabular-nums">{{ vnd(live.founder.tndn) }}</dd>
              </div>
              <div class="flex justify-between font-medium">
                <dt>Net profit</dt>
                <dd class="tabular-nums">{{ vnd(live.founder.net_profit) }}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-gray-600">VAT phải nộp</dt>
                <dd class="tabular-nums">{{ vnd(live.founder.vat_payable) }}</dd>
              </div>
            </dl>
            <div class="mt-4 flex items-center justify-between border-t pt-3 text-xs text-gray-600">
              <span>
                Margin floor:
                {{ live.founder.margin_floor_pct || "off" }}{{ live.founder.margin_floor_pct ? "%" : "" }}
              </span>
              <router-link to="/settings" class="text-blue-700 hover:underline">
                Edit in Settings →
              </router-link>
            </div>
          </div>

          <QuotePanel
            :deal="name"
            :before-publish="save"
            @changed="deal.reload()"
          />
        </div>
      </div>
    </template>

    <ErrorMessage class="mt-3" :message="error" />
  </div>
</template>

<script setup>
import { reactive, ref, computed, watch } from "vue"
import { useRoute } from "vue-router"
import {
  Button,
  ErrorMessage,
  createListResource,
  createResource,
} from "frappe-ui"
import QuotePanel from "../components/QuotePanel.vue"
import { vnd } from "../utils/money"

// Must match the Deal Cost Line tax_type options. Internal work carries
// no invoice — Không hoá đơn.
const TAX_TYPES = ["Công ty", "Cá nhân", "Không hoá đơn"]
const COST_PHASES = [
  "Pre-production",
  "Production",
  "Post-production",
  "Appendix",
]
const SOURCE_TYPES = ["Internal", "Freelancer", "Vendor"]

const route = useRoute()
const name = route.params.name

const state = reactive({
  lines: [],
  packages: [],
  quote_mf_pct: 10,
  vat_pct: 8,
  // Founder-only; stays null for producers (the server ignores it from
  // them anyway).
  commission_pct: null,
})
let serverDoc = null
const error = ref("")
const saving = ref(false)

const LINE_FIELDS = [
  "description",
  "item_category",
  "cost_phase",
  "source_type",
  "source_contact",
  "package",
  "qty1",
  "qty1_unit",
  "qty2",
  "qty2_unit",
  "unit_price",
  "tax_type",
  "vendor_mf_pct",
  "markup_pct",
]

function pick(obj, keys) {
  const out = {}
  for (const k of keys) out[k] = obj[k] ?? null
  return out
}

const deal = createResource({
  url: "frappe.client.get",
  makeParams: () => ({ doctype: "Deal", name }),
  auto: true,
  onSuccess(doc) {
    serverDoc = doc
    state.lines = (doc.cost_lines || []).map((row) => ({
      ...pick(row, LINE_FIELDS),
      package: row.package || "",
    }))
    state.packages = (doc.packages || []).map((row) =>
      pick(row, ["title", "description", "price_override"])
    )
    state.quote_mf_pct = doc.quote_mf_pct ?? 10
    state.vat_pct = doc.vat_pct ?? 8
    // Producers never receive this field; null keeps the server default.
    state.commission_pct = doc.commission_pct ?? null
    recompute()
  },
  onError(err) {
    error.value = errorMessage(err)
  },
})

const compute = createResource({
  url: "auraos.api.compute_breakdown",
  onError(err) {
    error.value = errorMessage(err)
  },
  onSuccess() {
    error.value = ""
  },
})

const live = computed(() => compute.data)

const categories = createListResource({
  doctype: "Cost Item Category",
  fields: ["name"],
  orderBy: "name asc",
  pageLength: 500,
})

const contacts = createListResource({
  doctype: "Party Contact",
  fields: ["name", "full_name"],
  orderBy: "full_name asc",
  pageLength: 500,
})

const categoryCreator = createResource({ url: "frappe.client.insert" })
const categoryCreations = new Map()

function errorMessage(err) {
  return err.messages?.join("\n") || err.message || "Could not add category"
}

async function ensureItemCategory(line) {
  const value = (line.item_category || "").trim()
  line.item_category = value
  if (!value || (categories.data || []).some((row) => row.name === value)) return
  if (!categoryCreations.has(value)) {
    categoryCreations.set(
      value,
      categoryCreator
        .submit({
          doc: { doctype: "Cost Item Category", category_name: value },
        })
        .then(() => categories.reload())
        .finally(() => categoryCreations.delete(value))
    )
  }
  try {
    await categoryCreations.get(value)
    error.value = ""
  } catch (err) {
    error.value = errorMessage(err)
    throw err
  }
}

function recompute() {
  compute.submit({
    lines: JSON.stringify(state.lines),
    packages: JSON.stringify(state.packages),
    quote_mf_pct: state.quote_mf_pct || 0,
    vat_pct: state.vat_pct || 0,
    commission_pct: state.commission_pct,
  })
}

let computeTimer = null
watch(
  state,
  () => {
    clearTimeout(computeTimer)
    computeTimer = setTimeout(recompute, 400)
  },
  { deep: true }
)

function livePackage(title) {
  return (live.value?.packages || []).find((p) => p.title === title)
}


// -- editing --

function addLine() {
  state.lines.push({
    description: "",
    item_category: "",
    cost_phase: "",
    source_type: "Internal",
    source_contact: "",
    package: "",
    qty1: 1,
    qty1_unit: "",
    qty2: 1,
    qty2_unit: "",
    unit_price: 0,
    tax_type: "Không hoá đơn",
    vendor_mf_pct: 0,
    markup_pct: 0,
  })
}

function moveLine(i, delta) {
  const j = i + delta
  const [row] = state.lines.splice(i, 1)
  state.lines.splice(j, 0, row)
}

function addPackage() {
  state.packages.push({ title: "", description: "", price_override: null })
}

// Typing a new name in a line's package cell creates the package on the
// spot (T5 walkthrough request) — otherwise the save would reject an
// unknown package reference.
function ensurePackage(title) {
  const trimmed = (title || "").trim()
  if (!trimmed) return
  if (!state.packages.some((p) => p.title === trimmed)) {
    state.packages.push({
      title: trimmed,
      description: "",
      price_override: null,
    })
  }
}

function removePackage(i) {
  const [removed] = state.packages.splice(i, 1)
  // Lines pointing at the removed package become ungrouped instead of
  // failing server validation.
  for (const line of state.lines) {
    if (line.package === removed.title) line.package = ""
  }
}

// -- saving --

function onSaveError(err) {
  saving.value = false
  error.value = errorMessage(err)
}

const saveResource = createResource({
  url: "frappe.client.save",
  onSuccess(doc) {
    saving.value = false
    error.value = ""
    serverDoc = doc
  },
  onError: onSaveError,
})

async function save() {
  if (!serverDoc) return
  saving.value = true
  try {
    for (const line of state.lines) await ensureItemCategory(line)
  } catch (err) {
    saving.value = false
    throw err
  }
  const doc = {
    ...serverDoc,
    doctype: "Deal",
    quote_mf_pct: state.quote_mf_pct || 0,
    vat_pct: state.vat_pct || 0,
    cost_lines: state.lines.map((line) => ({
      ...line,
      doctype: "Deal Cost Line",
    })),
    packages: state.packages.map((pkg) => ({
      ...pkg,
      doctype: "Deal Package",
    })),
  }
  if (live.value?.founder && state.commission_pct != null) {
    doc.commission_pct = state.commission_pct
  }
  // Returned so publishing can save first and freeze what's on screen.
  return saveResource.submit({ doc })
}

</script>

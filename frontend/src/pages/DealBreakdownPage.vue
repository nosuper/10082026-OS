<template>
  <div class="space-y-4">
    <!-- Sticky under the shell header: this page is long and the founder sits
         on it for hours; Save and the deal's identity must never scroll away. -->
    <div
      class="sticky top-14 z-20 -mx-4 flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-hairline bg-canvas/90 px-4 py-3 backdrop-blur lg:-mx-6 lg:px-6"
    >
      <router-link
        to="/deals"
        class="inline-flex shrink-0 items-center gap-1 text-sm text-muted hover:text-accent"
      >
        <FeatherIcon name="chevron-left" class="h-3.5 w-3.5" />
        Deals
      </router-link>

      <div class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
        <h1 class="min-w-0 truncate text-xl font-semibold text-carbon">
          {{ deal.data?.title || name }}
        </h1>
        <span class="aura-num text-xs text-faint">{{ name }}</span>
        <StatusPill
          v-if="deal.data"
          :label="deal.data.stage"
          :tone="stageTone(deal.data.stage)"
        />
      </div>

      <div class="ml-auto flex items-center gap-3">
        <span v-if="saving" class="text-xs text-muted">Saving…</span>
        <span
          v-else-if="dirty && !allLinesComplete"
          class="text-xs font-medium text-accent-ink"
        >
          A line is missing its description - autosave is waiting
        </span>
        <span v-else-if="dirty" class="text-xs text-warn">
          Unsaved changes - autosaves in a moment, Ctrl+S saves now
        </span>
        <span v-else-if="baseline" class="text-xs text-faint">
          All changes saved
        </span>
        <button
          type="button"
          class="inline-flex shrink-0 items-center gap-1.5 rounded-[10px] bg-accent px-3.5 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-ink disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="saving"
          @click="save"
        >
          <FeatherIcon
            v-if="saving"
            name="loader"
            class="h-3.5 w-3.5 animate-spin"
          />
          Save
        </button>
      </div>
    </div>

    <!-- The floor warning is the one loud thing on the page. -->
    <div
      v-if="live?.floor_breached"
      class="flex items-center gap-2 rounded-card border border-accent/30 bg-accent-soft px-3 py-2.5 text-sm text-accent-ink"
    >
      <FeatherIcon name="alert-triangle" class="h-4 w-4 shrink-0" />
      Margin is below the company floor - this quote is flagged as
      unprofitable.
    </div>

    <div v-if="deal.loading" class="py-12 text-center text-sm text-muted">
      Loading…
    </div>

    <template v-else-if="deal.data">
      <!-- Cost lines: the widest thing in the app. It keeps its own
           horizontal scroll, the description column freezes to the left so a
           row never loses its name, and the three computed money columns sit
           in a tinted band on the right. -->
      <section class="aura-card">
        <div class="flex flex-wrap items-center gap-2 border-b border-hairline px-4 py-3">
          <h2 class="font-display text-sm font-semibold text-carbon">Cost lines</h2>
          <span class="aura-num text-xs text-faint">{{ state.lines.length }}</span>

          <details class="relative ml-auto">
            <summary
              class="flex cursor-pointer select-none list-none items-center gap-1.5 rounded-[8px] border border-hairline bg-paper px-2.5 py-1.5 text-xs font-medium text-muted transition-colors hover:border-accent/40 hover:text-carbon"
            >
              Detail columns
              <FeatherIcon name="chevron-down" class="h-3 w-3" />
            </summary>
            <div
              class="absolute right-0 z-30 mt-1.5 w-56 rounded-card border border-hairline bg-paper p-2 shadow-card"
            >
              <label
                v-for="col in META_COLUMNS"
                :key="col.key"
                class="flex cursor-pointer items-center gap-2 rounded-[8px] px-2 py-1.5 text-sm text-carbon hover:bg-canvas"
              >
                <input
                  type="checkbox"
                  class="h-3.5 w-3.5 rounded border-hairline text-accent focus:ring-0"
                  :checked="visibleMeta.includes(col.key)"
                  @change="toggleMeta(col.key)"
                />
                {{ col.label }}
              </label>
              <p class="mt-1 border-t border-hairline px-2 pt-1.5 text-[11px] text-faint">
                Money columns are always shown.
              </p>
            </div>
          </details>

          <button type="button" :class="ghostButton" @click="addLine">
            <FeatherIcon name="plus" class="h-3 w-3" />
            Add line
          </button>
        </div>

        <div class="overflow-x-auto rounded-b-card">
          <table
            class="w-full border-collapse text-sm"
            :class="visibleMeta.length ? 'min-w-[1700px]' : 'min-w-[1100px]'"
          >
            <thead class="bg-canvas">
              <tr class="border-b border-hairline">
                <th :class="[headCell, stickyHead]">Description</th>
                <th v-if="metaVisible('item_category')" :class="headCell">Item Category</th>
                <th v-if="metaVisible('cost_phase')" :class="headCell">Cost Phase</th>
                <th v-if="metaVisible('source_type')" :class="headCell">Source Type</th>
                <th v-if="metaVisible('source_contact')" :class="headCell">Source Contact</th>
                <th :class="headCell">Package</th>
                <th :class="[headCell, 'text-right']">Qty 1</th>
                <th :class="headCell">Unit 1</th>
                <th :class="[headCell, 'text-right']">Qty 2</th>
                <th :class="headCell">Unit 2</th>
                <th :class="[headCell, 'text-right']">Unit Price</th>
                <th :class="headCell">Tax Type</th>
                <th :class="[headCell, 'text-right']">Vendor MF %</th>
                <th :class="[headCell, 'text-right']">Markup %</th>
                <th :class="[headCell, 'border-l border-hairline text-right']">Subtotal</th>
                <th :class="[headCell, 'text-right']">Quote Price</th>
                <th :class="[headCell, 'text-right']">Margin</th>
                <th :class="headCell"></th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(line, i) in state.lines"
                :key="i"
                class="group border-b border-hairline align-middle last:border-0 hover:bg-canvas"
              >
                <td :class="[bodyCell, stickyBody]">
                  <input
                    v-model="line.description"
                    class="w-44 rounded-[8px] border px-2 py-1 text-sm text-carbon placeholder:text-faint focus:border-accent focus:ring-0"
                    :class="
                      line.description?.trim()
                        ? 'border-hairline bg-paper'
                        : 'border-accent/50 bg-accent-soft'
                    "
                    placeholder="Description"
                    title="A line needs a description before it can save"
                  />
                </td>
                <td v-if="metaVisible('item_category')" :class="bodyCell">
                  <ComboInput
                    v-model="line.item_category"
                    :options="(categories.data || []).map((row) => row.name)"
                    placeholder="Select or add"
                    @commit="ensureItemCategory(line)"
                  />
                </td>
                <td v-if="metaVisible('cost_phase')" :class="bodyCell">
                  <select v-model="line.cost_phase" :class="[cellSelect, 'w-36']">
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
                <td v-if="metaVisible('source_type')" :class="bodyCell">
                  <select v-model="line.source_type" :class="[cellSelect, 'w-28']">
                    <option value=""></option>
                    <option v-for="type in SOURCE_TYPES" :key="type" :value="type">
                      {{ type }}
                    </option>
                  </select>
                </td>
                <td v-if="metaVisible('source_contact')" :class="bodyCell">
                  <select v-model="line.source_contact" :class="[cellSelect, 'w-40']">
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
                <td :class="bodyCell">
                  <ComboInput
                    v-model="line.package"
                    :options="state.packages.map((pkg) => pkg.title)"
                    placeholder="No package"
                    @commit="ensurePackage(line.package)"
                  />
                </td>
                <td :class="bodyCell">
                  <input
                    v-model.number="line.qty1"
                    type="number"
                    min="0"
                    :class="[cellNum, 'ml-auto block w-16']"
                  />
                </td>
                <td :class="bodyCell">
                  <input
                    v-model="line.qty1_unit"
                    :class="[cellInput, 'w-20']"
                    placeholder="người"
                  />
                </td>
                <td :class="bodyCell">
                  <input
                    v-model.number="line.qty2"
                    type="number"
                    min="0"
                    :class="[cellNum, 'ml-auto block w-16']"
                  />
                </td>
                <td :class="bodyCell">
                  <input
                    v-model="line.qty2_unit"
                    :class="[cellInput, 'w-20']"
                    placeholder="ngày"
                  />
                </td>
                <td :class="bodyCell">
                  <VndInput
                    :model-value="line.unit_price"
                    :class="[cellNum, 'ml-auto block w-32 font-medium']"
                    @update:model-value="line.unit_price = $event === '' ? 0 : $event"
                  />
                </td>
                <td :class="bodyCell">
                  <select v-model="line.tax_type" :class="[cellSelect, 'w-36']">
                    <option v-for="t in TAX_TYPES" :key="t" :value="t">
                      {{ t }}
                    </option>
                  </select>
                </td>
                <td :class="bodyCell">
                  <input
                    v-model.number="line.vendor_mf_pct"
                    type="number"
                    min="0"
                    :class="[cellNum, 'ml-auto block w-16']"
                  />
                </td>
                <td :class="bodyCell">
                  <input
                    v-model.number="line.markup_pct"
                    type="number"
                    min="0"
                    :class="[cellNum, 'ml-auto block w-16']"
                  />
                </td>
                <td :class="[computedCell, 'border-l border-hairline']">
                  <MoneyValue :amount="live?.lines?.[i]?.subtotal" tone="muted" />
                </td>
                <td :class="computedCell">
                  <MoneyValue
                    :amount="live?.lines?.[i]?.quote_price"
                    class="font-medium"
                  />
                </td>
                <td :class="computedCell">
                  <MoneyValue :amount="live?.lines?.[i]?.margin" tone="muted" />
                </td>
                <td class="whitespace-nowrap px-2 py-1.5 text-right">
                  <button :class="rowIcon" :disabled="i === 0" title="Move up" @click="moveLine(i, -1)">
                    <FeatherIcon name="chevron-up" class="h-3.5 w-3.5" />
                  </button>
                  <button
                    :class="rowIcon"
                    :disabled="i === state.lines.length - 1"
                    title="Move down"
                    @click="moveLine(i, 1)"
                  >
                    <FeatherIcon name="chevron-down" class="h-3.5 w-3.5" />
                  </button>
                  <button :class="rowIcon" title="Remove line" @click="state.lines.splice(i, 1)">
                    <FeatherIcon name="x" class="h-3.5 w-3.5" />
                  </button>
                </td>
              </tr>
              <tr v-if="!state.lines.length">
                <td :colspan="14 + visibleMeta.length">
                  <EmptyState title="No cost lines yet - add the first one." />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <!-- Packages: what the client actually reads. -->
        <section class="aura-card lg:col-span-2">
          <div class="flex items-center gap-2 border-b border-hairline px-4 py-3">
            <h2 class="font-display text-sm font-semibold text-carbon">
              Client-facing packages
            </h2>
            <span class="aura-num text-xs text-faint">{{ state.packages.length }}</span>
            <button type="button" :class="[ghostButton, 'ml-auto']" @click="addPackage">
              <FeatherIcon name="plus" class="h-3 w-3" />
              Add package
            </button>
          </div>
          <div class="overflow-x-auto rounded-b-card">
            <table class="w-full min-w-[640px] border-collapse text-sm">
              <thead class="bg-canvas">
                <tr class="border-b border-hairline">
                  <th :class="headCell">Title</th>
                  <th :class="headCell">Description</th>
                  <th :class="[headCell, 'text-right']">Override</th>
                  <th :class="[headCell, 'text-right']">Member Sum</th>
                  <th :class="[headCell, 'text-right']">Price</th>
                  <th :class="[headCell, 'text-right']">Variance</th>
                  <th :class="headCell"></th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(pkg, i) in state.packages"
                  :key="i"
                  class="border-b border-hairline align-middle last:border-0 hover:bg-canvas"
                >
                  <td :class="bodyCell">
                    <input
                      v-model="pkg.title"
                      :class="[cellInput, 'w-40 font-medium']"
                      placeholder="Human resources"
                    />
                  </td>
                  <td :class="bodyCell">
                    <input
                      v-model="pkg.description"
                      :class="[cellInput, 'w-full min-w-40']"
                      placeholder="What the client reads"
                    />
                  </td>
                  <td :class="bodyCell">
                    <VndInput
                      :model-value="pkg.has_price_override ? pkg.price_override : ''"
                      :class="[cellNum, 'ml-auto block w-32']"
                      placeholder="auto"
                      :title="
                        pkg.has_price_override && !pkg.price_override
                          ? 'Quoted free of charge'
                          : 'Blank = sum of member lines; 0 = free of charge'
                      "
                      @update:model-value="setOverride(pkg, $event)"
                    />
                  </td>
                  <td :class="computedCell">
                    <MoneyValue :amount="livePackage(pkg.title)?.default_price" tone="muted" />
                  </td>
                  <td :class="computedCell">
                    <MoneyValue :amount="livePackage(pkg.title)?.price" class="font-medium" />
                  </td>
                  <td :class="computedCell">
                    <span v-if="livePackage(pkg.title)?.variance" class="aura-num text-sm font-medium text-warn">
                      {{ vnd(livePackage(pkg.title)?.variance) }}
                    </span>
                    <span v-else class="aura-num text-sm text-faint">
                      {{ vnd(livePackage(pkg.title)?.variance) }}
                    </span>
                  </td>
                  <td class="whitespace-nowrap px-2 py-1.5 text-right">
                    <button :class="rowIcon" title="Remove package" @click="removePackage(i)">
                      <FeatherIcon name="x" class="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
                <tr v-if="!state.packages.length">
                  <td colspan="7">
                    <EmptyState title="No packages - the client would see raw lines." />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- Right rail: what the numbers add up to, then who may see what. -->
        <div class="space-y-4">
          <BentoCard title="Quote totals">
            <div class="mb-3 flex items-center gap-4">
              <label class="text-xs text-muted">
                Quote MF %
                <input
                  v-model.number="state.quote_mf_pct"
                  type="number"
                  min="0"
                  :class="[cellNum, 'mt-1 block w-20']"
                />
              </label>
              <label class="text-xs text-muted">
                VAT %
                <input
                  v-model.number="state.vat_pct"
                  type="number"
                  min="0"
                  :class="[cellNum, 'mt-1 block w-20']"
                />
              </label>
            </div>
            <dl class="space-y-1.5 text-sm">
              <div class="flex items-baseline justify-between gap-3">
                <dt class="text-muted">Subtotal</dt>
                <dd><MoneyValue :amount="live?.subtotal" /></dd>
              </div>
              <div class="flex items-baseline justify-between gap-3">
                <dt class="text-muted">
                  Management fee ({{ state.quote_mf_pct }}%)
                </dt>
                <dd><MoneyValue :amount="live?.management_fee" /></dd>
              </div>
              <div class="flex items-baseline justify-between gap-3">
                <dt class="text-muted">VAT ({{ state.vat_pct }}%)</dt>
                <dd><MoneyValue :amount="live?.vat" /></dd>
              </div>
              <div
                class="flex items-baseline justify-between gap-3 border-t border-hairline pt-2"
              >
                <dt class="font-display text-sm font-semibold text-carbon">Total</dt>
                <dd><MoneyValue :amount="live?.total" size="lg" /></dd>
              </div>
              <div class="flex items-baseline justify-between gap-3 pt-1">
                <dt class="flex items-baseline gap-1.5 text-muted">
                  Margin
                  <span
                    v-if="live?.margin_pct != null"
                    class="aura-num text-xs font-medium"
                    :class="live?.floor_breached ? 'text-accent' : 'text-ok'"
                  >
                    {{ live.margin_pct.toFixed(1) }}%
                  </span>
                </dt>
                <dd>
                  <MoneyValue
                    :amount="live?.margin"
                    :tone="live?.floor_breached ? 'accent' : 'ink'"
                    class="font-medium"
                  />
                </dd>
              </div>
            </dl>
            <template v-if="live?.floor_breached" #footer>
              <StatusPill label="Below floor" tone="accent" />
            </template>
          </BentoCard>

          <!-- Founder-only: server-gated, inverted surface so commission and
               net profit never sit in the producer-safe register. -->
          <BentoCard v-if="live?.founder" founder title="Founder only">
            <label class="block text-xs text-white/60">
              Commission %
              <input
                v-model.number="state.commission_pct"
                type="number"
                min="0"
                class="aura-num mt-1 block w-20 rounded-[8px] border border-white/15 bg-white/10 px-2 py-1 text-right text-sm text-white focus:border-white/40 focus:ring-0"
              />
            </label>
            <dl class="mt-3 space-y-1.5 text-sm">
              <div class="flex items-baseline justify-between gap-3">
                <dt class="text-white/60">Commission (CMF)</dt>
                <dd><MoneyValue :amount="live.founder.total_commission" tone="inverse" /></dd>
              </div>
              <div class="flex items-baseline justify-between gap-3">
                <dt class="text-white/60">CM (after commission)</dt>
                <dd><MoneyValue :amount="live.founder.cm" tone="inverse" /></dd>
              </div>
              <div class="flex items-baseline justify-between gap-3">
                <dt class="text-white/60">Lợi nhuận trước thuế</dt>
                <dd><MoneyValue :amount="live.founder.profit_before_tax" tone="inverse" /></dd>
              </div>
              <div class="flex items-baseline justify-between gap-3">
                <dt class="text-white/60">TNDN (20%)</dt>
                <dd><MoneyValue :amount="live.founder.tndn" tone="inverse" /></dd>
              </div>
              <div
                class="flex items-baseline justify-between gap-3 border-t border-white/10 pt-2"
              >
                <dt class="font-medium text-white">Net profit</dt>
                <dd>
                  <MoneyValue :amount="live.founder.net_profit" tone="inverse" class="font-medium" />
                </dd>
              </div>
              <div class="flex items-baseline justify-between gap-3">
                <dt class="text-white/60">VAT phải nộp</dt>
                <dd><MoneyValue :amount="live.founder.vat_payable" tone="inverse" /></dd>
              </div>
            </dl>
            <template #footer>
              <div class="flex items-center justify-between gap-2 text-xs">
                <span class="text-white/60">
                  Margin floor:
                  {{ live.founder.margin_floor_pct || "off" }}{{ live.founder.margin_floor_pct ? "%" : "" }}
                </span>
                <router-link to="/settings" class="text-white/70 hover:text-white">
                  Edit in Settings →
                </router-link>
              </div>
            </template>
          </BentoCard>

          <BentoCard
            title="Quote detail level"
            subtitle="How much of the build the client's page and PDF show - the next published version uses this."
          >
            <div class="space-y-1.5">
              <button
                v-for="level in DETAIL_LEVELS"
                :key="level.value"
                type="button"
                class="flex w-full flex-col items-start rounded-[10px] border px-3 py-2 text-left transition-colors"
                :class="
                  state.quote_detail_level === level.value
                    ? 'border-accent bg-accent-soft'
                    : 'border-hairline hover:border-accent/40 hover:bg-canvas'
                "
                @click="state.quote_detail_level = level.value"
              >
                <span
                  class="text-sm font-medium"
                  :class="
                    state.quote_detail_level === level.value
                      ? 'text-accent-ink'
                      : 'text-carbon'
                  "
                >
                  {{ level.value }}
                </span>
                <span
                  class="text-xs"
                  :class="
                    state.quote_detail_level === level.value
                      ? 'text-accent-ink/70'
                      : 'text-faint'
                  "
                >
                  {{ level.hint }}
                </span>
              </button>
            </div>
          </BentoCard>

          <QuotePanel
            :deal="name"
            :before-publish="save"
            @changed="deal.reload()"
          />
        </div>
      </div>
    </template>

    <ErrorMessage :message="error" />
  </div>
</template>

<script setup>
import { reactive, ref, computed, watch, onMounted, onUnmounted } from "vue"
import { useRoute } from "vue-router"
import {
  ErrorMessage,
  FeatherIcon,
  createListResource,
  createResource,
} from "frappe-ui"
import BentoCard from "../components/BentoCard.vue"
import ComboInput from "../components/ComboInput.vue"
import EmptyState from "../components/EmptyState.vue"
import MoneyValue from "../components/MoneyValue.vue"
import QuotePanel from "../components/QuotePanel.vue"
import StatusPill from "../components/StatusPill.vue"
import VndInput from "../components/VndInput.vue"
import { vnd } from "../utils/money"
import { currentUser } from "../utils/user"

// -- the look: one definition per shape, so 18 columns stay consistent --

const headCell =
  "aura-eyebrow whitespace-nowrap px-2 py-2 text-left font-medium"
const bodyCell = "px-2 py-1.5"
const computedCell = "bg-canvas/60 px-2 py-1.5 text-right"
// The description column freezes to the left: a wide table must never leave a
// row without its name. bg-paper keeps the scrolled-under cells hidden.
const stickyHead = "sticky left-0 border-r border-hairline bg-canvas"
const stickyBody =
  "sticky left-0 border-r border-hairline bg-paper group-hover:bg-canvas"

const cellInput =
  "rounded-[8px] border border-hairline bg-paper px-2 py-1 text-sm text-carbon placeholder:text-faint focus:border-accent focus:ring-0"
// Numerals read as a ledger; Vietnamese unit and tax fields stay in the sans face.
const cellNum = `${cellInput} aura-num text-right`
const cellSelect =
  "rounded-[8px] border border-hairline bg-paper py-1 pl-2 pr-7 text-sm text-carbon focus:border-accent focus:ring-0"
const ghostButton =
  "inline-flex shrink-0 items-center gap-1.5 rounded-[8px] border border-hairline bg-paper px-2.5 py-1.5 text-xs font-medium text-carbon transition-colors hover:border-accent/40 hover:text-accent-ink"
const rowIcon =
  "rounded-[6px] p-1 text-faint transition-colors hover:bg-canvas hover:text-accent-ink disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-faint"

// Deal stages onto the four pill tones: act-on-this in the accent, settled in ok.
function stageTone(stage) {
  if (stage === "Won") return "ok"
  if (stage === "Lost") return "warn"
  if (stage === "Quote Sent" || stage === "Negotiation") return "accent"
  return "neutral"
}

// Must match the Deal Cost Line tax_type options. Internal work carries
// no invoice - Không hoá đơn.
const TAX_TYPES = ["Công ty", "Cá nhân", "Không hoá đơn"]
const COST_PHASES = [
  "Pre-production",
  "Production",
  "Post-production",
  "Appendix",
]
const SOURCE_TYPES = ["Internal", "Freelancer", "Vendor"]

// The three Quote Detail Level values, with what each one means to the
// client. The value strings are the doctype's - only the chrome is new.
const DETAIL_LEVELS = [
  { value: "Package totals", hint: "One price per package" },
  { value: "Line by line", hint: "Every item with quantities (AICP-style)" },
  { value: "Lump sum", hint: "A single figure for the whole job" },
]

// T5.1 metadata - real, but not what pricing a job needs on screen.
// Hidden by default so the table fits a laptop without sideways
// scrolling; the choice sticks per user.
const META_COLUMNS = [
  { key: "item_category", label: "Item Category" },
  { key: "cost_phase", label: "Cost Phase" },
  { key: "source_type", label: "Source Type" },
  { key: "source_contact", label: "Source Contact" },
]

const route = useRoute()
const name = route.params.name

const metaKey = `auraos.breakdown.columns.${currentUser()}`

function loadMeta() {
  try {
    const saved = JSON.parse(localStorage.getItem(metaKey))
    return Array.isArray(saved)
      ? saved.filter((key) => META_COLUMNS.some((col) => col.key === key))
      : []
  } catch {
    return []
  }
}

const visibleMeta = ref(loadMeta())

function metaVisible(key) {
  return visibleMeta.value.includes(key)
}

function toggleMeta(key) {
  visibleMeta.value = metaVisible(key)
    ? visibleMeta.value.filter((item) => item !== key)
    : [...visibleMeta.value, key]
  try {
    localStorage.setItem(metaKey, JSON.stringify(visibleMeta.value))
  } catch {
    // A blocked storage API must not make the editor unusable.
  }
}

const state = reactive({
  lines: [],
  packages: [],
  quote_mf_pct: 10,
  vat_pct: 8,
  quote_detail_level: "Package totals",
  // Founder-only; stays null for producers (the server ignores it from
  // them anyway).
  commission_pct: null,
})
let serverDoc = null
const error = ref("")
const saving = ref(false)

// Dirty = what's on screen differs from the last load or save. A JSON
// snapshot, not a flag: population on load must not count as an edit.
const baseline = ref("")

function snapshot() {
  return JSON.stringify({
    lines: state.lines,
    packages: state.packages,
    quote_mf_pct: state.quote_mf_pct,
    vat_pct: state.vat_pct,
    quote_detail_level: state.quote_detail_level,
    commission_pct: state.commission_pct,
  })
}

const dirty = computed(() => Boolean(baseline.value) && snapshot() !== baseline.value)

// Autosave holds off while a line has no description - the save would
// only bounce off server validation; the accent border says why.
const allLinesComplete = computed(() =>
  state.lines.every((line) => (line.description || "").trim())
)

// The founder sits on this page for hours; muscle-memory save must work.
function onKeydown(event) {
  if ((event.metaKey || event.ctrlKey) && event.key === "s") {
    event.preventDefault()
    save()
  }
}

onMounted(() => window.addEventListener("keydown", onKeydown))
onUnmounted(() => window.removeEventListener("keydown", onKeydown))

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
    state.packages = (doc.packages || []).map((row) => {
      const pkg = pick(row, [
        "title",
        "description",
        "price_override",
        "has_price_override",
      ])
      // The Check carries "is this set": without it the Currency
      // column's default 0 is meaningless, with it 0 is a real
      // free-of-charge override.
      pkg.has_price_override = pkg.has_price_override ? 1 : 0
      if (!pkg.has_price_override) pkg.price_override = null
      return pkg
    })
    state.quote_mf_pct = doc.quote_mf_pct ?? 10
    state.vat_pct = doc.vat_pct ?? 8
    state.quote_detail_level = doc.quote_detail_level || "Package totals"
    // Producers never receive this field; null keeps the server default.
    state.commission_pct = doc.commission_pct ?? null
    recompute()
    baseline.value = snapshot()
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
  return err.messages?.join("\n") || err.message || "Something went wrong"
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
let autosaveTimer = null
watch(
  state,
  () => {
    clearTimeout(computeTimer)
    computeTimer = setTimeout(recompute, 400)
    // Autosave asked for on the A2 walkthrough: a couple of quiet
    // seconds after the last edit, the page saves itself. Ctrl+S and
    // the button stay for the impatient.
    clearTimeout(autosaveTimer)
    autosaveTimer = setTimeout(autosave, 2500)
  },
  { deep: true }
)

function autosave() {
  if (!dirty.value || saving.value || !serverDoc) return
  if (!allLinesComplete.value) return
  save()
}

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
  state.packages.push({
    title: "",
    description: "",
    price_override: null,
    has_price_override: 0,
  })
}

function setOverride(pkg, value) {
  if (value === "") {
    pkg.has_price_override = 0
    pkg.price_override = null
  } else {
    pkg.has_price_override = 1
    pkg.price_override = value
  }
}

// Typing a new name in a line's package cell creates the package on the
// spot (T5 walkthrough request) - otherwise the save would reject an
// unknown package reference.
function ensurePackage(title) {
  const trimmed = (title || "").trim()
  if (!trimmed) return
  if (!state.packages.some((p) => p.title === trimmed)) {
    state.packages.push({
      title: trimmed,
      description: "",
      price_override: null,
      has_price_override: 0,
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

// What the in-flight save actually carried: edits typed while the
// request runs must stay dirty, not be silently marked saved.
let sentSnapshot = ""

const saveResource = createResource({
  url: "frappe.client.save",
  onSuccess(doc) {
    saving.value = false
    error.value = ""
    serverDoc = doc
    baseline.value = sentSnapshot || snapshot()
  },
  onError: onSaveError,
})

async function save() {
  if (!serverDoc || saving.value) return
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
    quote_detail_level: state.quote_detail_level,
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
  sentSnapshot = snapshot()
  // Returned so publishing can save first and freeze what's on screen.
  return saveResource.submit({ doc })
}

</script>

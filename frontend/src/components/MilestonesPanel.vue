<template>
  <div class="overflow-hidden rounded-card border border-hairline bg-paper shadow-card">
    <div class="flex flex-wrap items-center gap-2 border-b border-hairline px-4 py-3">
      <h2 class="font-display text-sm font-semibold text-carbon">
        Payment milestones
      </h2>
      <StatusPill
        v-if="overdueCount"
        tone="accent"
        :label="`${overdueCount} overdue`"
        :title="`Uncollected more than ${termsDays} days after falling due`"
      />
      <span class="ml-auto text-xs" :class="planClass">
        {{ plannedPct }}% of the quote planned
      </span>
    </div>

    <!-- Fixed columns: the collection control carries the longest text
         on the row ("Not requested - chưa yêu cầu") and an auto layout
         gave the width to the amounts, clipping it mid-word. -->
    <div class="overflow-x-auto">
      <table
        v-if="rows.length"
        class="w-full min-w-[46rem] table-fixed border-collapse text-sm"
      >
        <thead>
          <tr class="border-b border-hairline bg-canvas/60">
            <th class="aura-eyebrow w-1/6 px-4 py-2 text-left font-medium">Milestone</th>
            <th class="aura-eyebrow w-20 px-2 py-2 text-left font-medium">% of quote</th>
            <th class="aura-eyebrow w-1/6 px-2 py-2 text-left font-medium">Trigger stage</th>
            <th class="aura-eyebrow w-1/6 px-2 py-2 text-right font-medium">Amount (VND)</th>
            <th class="aura-eyebrow px-2 py-2 text-left font-medium">Collection</th>
            <th class="w-32 px-4 py-2"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, index) in rows"
            :key="row.key"
            class="border-b border-hairline align-top last:border-0"
            :class="row.overdue ? 'bg-accent-soft' : ''"
          >
            <td class="px-4 py-2">
              <input
                v-model="row.title"
                class="w-full rounded-[8px] border border-hairline bg-paper px-2 py-1 text-sm text-carbon placeholder:text-faint focus:outline-none focus:ring-2 focus:ring-accent/30"
                placeholder="Deposit"
              />
            </td>
            <td class="px-2 py-2">
              <input
                :value="row.pct"
                type="number"
                min="0"
                step="5"
                class="aura-num w-16 rounded-[8px] border border-hairline bg-paper px-2 py-1 text-right text-sm text-carbon focus:outline-none focus:ring-2 focus:ring-accent/30"
                @input="
                  ((row.pct = $event.target.valueAsNumber || 0),
                  rebalance(row))
                "
              />
            </td>
            <td class="px-2 py-2">
              <select
                v-model="row.trigger_stage"
                class="w-full rounded-[8px] border border-hairline bg-paper py-1 pl-2 pr-7 text-sm text-carbon focus:outline-none focus:ring-2 focus:ring-accent/30"
              >
                <option v-for="stage in STAGES" :key="stage" :value="stage">
                  {{ stage }}
                </option>
              </select>
            </td>
            <td class="px-2 py-2 text-right">
              <MoneyValue :amount="row.amount" />
              <div v-if="row.overdue" class="whitespace-nowrap text-xs text-accent">
                {{ overdueLabel(row.days_overdue) }}
              </div>
              <div
                v-else-if="row.due_on"
                class="whitespace-nowrap text-xs text-muted"
              >
                due since {{ row.due_on.slice(0, 10) }}
              </div>
              <div v-else class="text-xs text-faint">not due yet</div>
            </td>
            <td class="px-2 py-2">
              <!-- Sans, not mono: the second half of every option is
                   Vietnamese and the ledger face has no diacritics. -->
              <select
                :value="row.status"
                :disabled="!row.name"
                class="w-full rounded-[8px] border border-hairline bg-paper py-1 pl-2 pr-7 font-sans text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 disabled:text-faint"
                :class="row.status === PAID ? 'text-ok' : 'text-carbon'"
                @change="setStatus(row, $event.target.value)"
              >
                <option
                  v-for="option in COLLECTION_STATUSES"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.value }} - {{ option.vi }}
                </option>
              </select>
              <div v-if="row.name" class="aura-num mt-1 text-xs text-faint">
                {{ stampFor(row) }}
              </div>
            </td>
            <td class="whitespace-nowrap px-4 py-2 text-right">
              <button
                v-if="row.name"
                class="rounded-[8px] border border-hairline px-2 py-1 text-xs text-muted transition-colors hover:border-accent/40 hover:text-accent-ink"
                title="Copy the invoice request for the accountant, ready to paste into Zalo"
                @click="copyInvoiceRequest(row)"
              >
                Invoice request
              </button>
              <button
                class="ml-1 rounded-[8px] border border-hairline p-1 text-faint transition-colors hover:border-accent/40 hover:text-accent"
                title="Remove this milestone"
                @click="rows.splice(index, 1)"
              >
                <FeatherIcon name="x" class="h-3 w-3" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <EmptyState
      v-if="!rows.length"
      title="No payment milestones."
      detail="This job has nothing chasing the client."
    />

    <div class="space-y-2 border-t border-hairline px-4 py-3">
      <p v-if="plannedPct !== 100 && lockedPct" class="text-xs text-warn">
        {{ lockedPct }}% of the plan is already invoiced or paid and cannot
        rebalance itself - adjust the open rows to bring the total to 100%.
      </p>

      <div class="flex flex-wrap items-center gap-2">
        <Button @click="addRow">Add milestone</Button>
        <Button
          variant="solid"
          :disabled="!dirty"
          :loading="saver.loading"
          @click="savePlan"
        >
          Save plan
        </Button>
        <span v-if="dirty" class="text-xs text-warn">
          Unsaved changes - amounts refresh from the quote on save.
        </span>
      </div>

      <!-- Beside the buttons, not at the foot of the panel: with the
           invoice request open, a message down there is off the bottom of
           what the founder is looking at. -->
      <ErrorMessage :message="error" />

      <!-- The invoice request: copied by the button above, shown here so
           the founder can read what they are about to paste. -->
      <div v-if="invoiceText" class="rounded-card border border-hairline bg-canvas p-3">
        <div class="mb-2 flex items-center gap-2">
          <span class="aura-eyebrow">
            {{ copied ? "Copied - paste into Zalo" : "Invoice request for the accountant" }}
          </span>
          <button
            class="ml-auto rounded-[8px] border border-hairline bg-paper px-2 py-0.5 text-xs text-muted transition-colors hover:border-accent/40 hover:text-accent-ink"
            @click="copyInvoiceText"
          >
            {{ copied ? "Copy again" : "Copy" }}
          </button>
          <button
            class="rounded-[8px] border border-hairline bg-paper px-2 py-0.5 text-xs text-faint transition-colors hover:text-carbon"
            @click="invoiceText = ''"
          >
            Close
          </button>
        </div>
        <!-- Sans: the request is Vietnamese prose, not a ledger column. -->
        <pre class="whitespace-pre-wrap font-sans text-sm text-carbon">{{ invoiceText }}</pre>
        <p class="mt-2 text-xs text-faint">
          Copying does not change the milestone - mark it
          <em>Requested</em> once you have actually sent it.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue"
import { Button, ErrorMessage, FeatherIcon, createResource } from "frappe-ui"
import StatusPill from "./StatusPill.vue"
import MoneyValue from "./MoneyValue.vue"
import EmptyState from "./EmptyState.vue"
import { frappeErrorMessage } from "../utils/frappeError"
import { STAGES } from "../data/jobStages"
import { COLLECTION_STATUSES, PAID, overdueLabel } from "../data/milestones"

const props = defineProps({ job: { type: String, required: true } })

// The job page's stat strip mirrors these numbers; it listens for this.
const emit = defineEmits(["changed"])

const error = ref("")
const rows = ref([])
const invoiceText = ref("")
const copied = ref(false)
// Row identity for v-for: saved rows have a server name, new ones need
// something stable of their own or Vue reuses inputs across edits.
let nextKey = 0

const milestones = createResource({
  url: "auraos.api.job_milestones",
  makeParams: () => ({ job: props.job }),
  auto: true,
  onSuccess(data) {
    rows.value = (data.milestones || []).map((row) => ({
      ...row,
      key: row.name || `new-${nextKey++}`,
    }))
    // Deliberately not clearing `error`: a refused save reloads to show
    // what is actually stored, and clearing here wiped the very message
    // explaining the refusal - the plan snapped back saying nothing.
    // Each user action clears it when it starts instead.
  },
  onError(err) {
    error.value = frappeErrorMessage(err)
  },
})

// What the server last handed us, as the comparison for "unsaved".
const stored = computed(() => milestones.data?.milestones || [])

const termsDays = computed(() => milestones.data?.payment_terms_days)

const plannedPct = computed(() =>
  rows.value.reduce((sum, row) => sum + (Number(row.pct) || 0), 0)
)

const planClass = computed(() => {
  if (plannedPct.value > 100) return "text-accent"
  return plannedPct.value === 100 ? "text-faint" : "text-warn"
})

const overdueCount = computed(
  () => rows.value.filter((row) => row.overdue).length
)

// Why a plan may refuse to rebalance itself: the share already sitting
// with invoiced/paid milestones. Without this line the auto-balance
// just looks broken on a fully collected job (founder, A4 round 4).
const lockedPct = computed(() =>
  rows.value
    .filter((row) => LOCKED_STATUSES.includes(row.status))
    .reduce((sum, row) => sum + (Number(row.pct) || 0), 0)
)

const dirty = computed(() => {
  const plan = (row) => [row.name || "", row.title || "", Number(row.pct) || 0, row.trigger_stage || ""]
  const mine = rows.value.map(plan)
  const theirs = stored.value.map(plan)
  return JSON.stringify(mine) !== JSON.stringify(theirs)
})

function addRow() {
  rows.value.push({
    key: `new-${nextKey++}`,
    title: "",
    pct: Math.max(0, 100 - plannedPct.value),
    trigger_stage: STAGES[0],
    status: "Not requested",
  })
}

// Statuses whose money is already committed on paper: an invoiced or
// paid milestone's share is history and never rebalances itself.
const LOCKED_STATUSES = ["Invoiced", "Paid"]

function isLocked(row) {
  return LOCKED_STATUSES.includes(row.status)
}

// Editing one milestone's share rebalances the others so the plan
// lands back on 100% by itself (founder, A4 round 3). Invoiced/Paid
// rows never move - changing their % would rewrite an invoice the
// client already holds.
function rebalance(edited) {
  const movable = rows.value.filter((row) => row !== edited && !isLocked(row))
  if (!movable.length) return
  const fixed = rows.value
    .filter((row) => row !== edited && !movable.includes(row))
    .reduce((sum, row) => sum + (Number(row.pct) || 0), 0)
  const target = Math.max(0, 100 - (Number(edited.pct) || 0) - fixed)
  const current = movable.reduce((sum, row) => sum + (Number(row.pct) || 0), 0)
  let running = 0
  movable.forEach((row, index) => {
    let share
    if (index === movable.length - 1) {
      // Whole percents, remainder on the last movable row, so the plan
      // closes on exactly 100.
      share = Math.max(0, target - running)
    } else if (current > 0) {
      share = Math.round(((Number(row.pct) || 0) / current) * target)
    } else {
      share = Math.round(target / movable.length)
    }
    row.pct = share
    running += share
  })
}

const saver = createResource({
  url: "auraos.api.save_job_milestones",
  onSuccess() {
    // Reload rather than take the response: a row saved for the first
    // time gets its server name here, and everything keyed off that
    // name (the invoice text, the status control) needs it.
    milestones.reload()
    emit("changed")
  },
  onError(err) {
    // The typed plan is left alone on purpose: a refusal is usually a
    // number to correct, and throwing away what the founder just typed
    // makes them retype it to find out they were nearly right.
    error.value = frappeErrorMessage(err)
  },
})

function savePlan() {
  error.value = ""
  saver.submit({
    job: props.job,
    milestones: rows.value.map((row) => ({
      name: row.name,
      title: row.title,
      pct: row.pct,
      trigger_stage: row.trigger_stage,
    })),
  })
}

const statusSetter = createResource({
  url: "auraos.api.set_milestone_status",
  onSuccess() {
    error.value = ""
    milestones.reload()
    emit("changed")
  },
  onError(err) {
    error.value = frappeErrorMessage(err)
    milestones.reload()
  },
})

function setStatus(row, status) {
  error.value = ""
  row.status = status
  statusSetter.submit({ job: props.job, milestone: row.name, status })
}

// Which step of the flow this milestone last took, and when.
function stampFor(row) {
  const stamp = row.paid_on || row.invoiced_on || row.requested_on
  return stamp ? stamp.slice(0, 10) : ""
}

// One click: fetch the text and put it on the clipboard. It is shown
// below as well, both so the founder can read what they are pasting and
// so a browser that refuses the clipboard still leaves them something
// to select.
const invoiceRequest = createResource({
  url: "auraos.api.milestone_invoice_request",
  onSuccess(data) {
    invoiceText.value = data.text
    error.value = ""
    copyInvoiceText()
  },
  onError(err) {
    error.value = frappeErrorMessage(err)
  },
})

function copyInvoiceRequest(row) {
  copied.value = false
  error.value = ""
  invoiceRequest.submit({ job: props.job, milestone: row.name })
}

function copyInvoiceText() {
  navigator.clipboard?.writeText(invoiceText.value)
  copied.value = true
}

watch(
  () => props.job,
  () => milestones.reload()
)

// The amounts follow the quoted total, so a job whose totals change
// under us should not keep showing yesterday's numbers.
defineExpose({ reload: () => milestones.reload() })
</script>

<template>
  <div class="rounded-lg border bg-white p-3">
    <div class="mb-2 flex flex-wrap items-center gap-2">
      <h2 class="text-sm font-semibold text-gray-800">Payment milestones</h2>
      <span
        v-if="overdueCount"
        class="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-xs text-red-800"
        :title="`Uncollected more than ${termsDays} days after falling due`"
      >
        <FeatherIcon name="alert-circle" class="h-3 w-3" />
        {{ overdueCount }} overdue
      </span>
      <span class="ml-auto text-xs" :class="planClass">
        {{ plannedPct }}% of the quote planned
      </span>
    </div>

    <!-- Fixed columns: the collection control carries the longest text
         on the row ("Not requested — chưa yêu cầu") and an auto layout
         gave the width to the amounts, clipping it mid-word. -->
    <div class="overflow-x-auto">
    <table v-if="rows.length" class="w-full min-w-[40rem] table-fixed text-sm">
      <thead class="text-left text-xs text-gray-600">
        <tr>
          <th class="w-1/6 py-1 font-medium">Milestone</th>
          <th class="w-16 py-1 font-medium">% of quote</th>
          <th class="w-1/6 py-1 font-medium">Trigger stage</th>
          <th class="w-1/6 py-1 text-right font-medium">Amount (VND)</th>
          <th class="py-1 font-medium">Collection</th>
          <th class="w-28"></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, index) in rows"
          :key="row.key"
          class="border-t align-top"
          :class="row.overdue ? 'bg-red-50' : ''"
        >
          <td class="py-1 pr-2">
            <input
              v-model="row.title"
              class="w-full rounded border-gray-200 px-1 py-0.5 text-sm"
              placeholder="Deposit"
            />
          </td>
          <td class="py-1 pr-2">
            <input
              :value="row.pct"
              type="number"
              min="0"
              step="5"
              class="w-16 rounded border-gray-200 px-1 py-0.5 text-right text-sm tabular-nums"
              @input="
                ((row.pct = $event.target.valueAsNumber || 0),
                rebalance(row))
              "
            />
          </td>
          <td class="py-1 pr-2">
            <select
              v-model="row.trigger_stage"
              class="w-full rounded border-gray-200 py-0.5 pl-1 pr-6 text-sm"
            >
              <option v-for="stage in STAGES" :key="stage" :value="stage">
                {{ stage }}
              </option>
            </select>
          </td>
          <td class="py-1 pr-2 text-right tabular-nums text-gray-800">
            {{ vnd(row.amount) }}
            <div v-if="row.overdue" class="whitespace-nowrap text-xs text-red-700">
              {{ overdueLabel(row.days_overdue) }}
            </div>
            <div
              v-else-if="row.due_on"
              class="whitespace-nowrap text-xs text-gray-500"
            >
              due since {{ row.due_on.slice(0, 10) }}
            </div>
            <div v-else class="text-xs text-gray-400">not due yet</div>
          </td>
          <td class="py-1 pr-2">
            <select
              :value="row.status"
              :disabled="!row.name"
              class="w-full rounded border-gray-200 py-0.5 pl-1 pr-6 text-sm"
              :class="row.status === PAID ? 'text-green-700' : ''"
              @change="setStatus(row, $event.target.value)"
            >
              <option
                v-for="option in COLLECTION_STATUSES"
                :key="option.value"
                :value="option.value"
              >
                {{ option.value }} — {{ option.vi }}
              </option>
            </select>
            <div v-if="row.name" class="mt-0.5 text-xs text-gray-500">
              {{ stampFor(row) }}
            </div>
          </td>
          <td class="py-1 whitespace-nowrap text-right">
            <button
              v-if="row.name"
              class="rounded border px-1.5 py-0.5 text-xs text-gray-600 hover:bg-gray-50"
              title="Copy the invoice request for the accountant, ready to paste into Zalo"
              @click="copyInvoiceRequest(row)"
            >
              Invoice request
            </button>
            <button
              class="ml-1 rounded border p-1 text-xs text-gray-500 hover:bg-red-50 hover:text-red-600"
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
    <p v-if="!rows.length" class="py-2 text-sm text-gray-400">
      No payment milestones — this job has nothing chasing the client.
    </p>

    <div class="mt-3 flex flex-wrap items-center gap-2">
      <Button @click="addRow">Add milestone</Button>
      <Button
        variant="solid"
        :disabled="!dirty"
        :loading="saver.loading"
        @click="savePlan"
      >
        Save plan
      </Button>
      <span v-if="dirty" class="text-xs text-amber-700">
        Unsaved changes — amounts refresh from the quote on save.
      </span>
    </div>

    <!-- Beside the buttons, not at the foot of the panel: with the
         invoice request open, a message down there is off the bottom of
         what the founder is looking at. -->
    <ErrorMessage class="mt-2" :message="error" />

    <!-- The invoice request: copied by the button above, shown here so
         the founder can read what they are about to paste. -->
    <div v-if="invoiceText" class="mt-3 rounded-md border bg-gray-50 p-3">
      <div class="mb-1 flex items-center gap-2">
        <span class="text-xs font-semibold text-gray-700">
          {{ copied ? "Copied — paste into Zalo" : "Invoice request for the accountant" }}
        </span>
        <button
          class="ml-auto rounded border bg-white px-1.5 py-0.5 text-xs text-gray-600 hover:bg-gray-100"
          @click="copyInvoiceText"
        >
          {{ copied ? "Copy again" : "Copy" }}
        </button>
        <button
          class="rounded border bg-white px-1.5 py-0.5 text-xs text-gray-500 hover:bg-gray-100"
          @click="invoiceText = ''"
        >
          Close
        </button>
      </div>
      <pre class="whitespace-pre-wrap font-sans text-sm text-gray-800">{{ invoiceText }}</pre>
      <p class="mt-1 text-xs text-gray-500">
        Copying does not change the milestone — mark it
        <em>Requested</em> once you have actually sent it.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue"
import { Button, ErrorMessage, FeatherIcon, createResource } from "frappe-ui"
import { frappeErrorMessage } from "../utils/frappeError"
import { vnd } from "../utils/money"
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
    // explaining the refusal — the plan snapped back saying nothing.
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
  if (plannedPct.value > 100) return "text-red-700"
  return plannedPct.value === 100 ? "text-gray-500" : "text-amber-700"
})

const overdueCount = computed(
  () => rows.value.filter((row) => row.overdue).length
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

// Editing one milestone's share rebalances the others so the plan
// lands back on 100% by itself (founder, A4 round 3). Only rows the
// collection hasn't touched may move — a Requested/Invoiced/Paid
// milestone's share is already out with the client.
function rebalance(edited) {
  const movable = rows.value.filter(
    (row) =>
      row !== edited && (row.status || "Not requested") === "Not requested"
  )
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

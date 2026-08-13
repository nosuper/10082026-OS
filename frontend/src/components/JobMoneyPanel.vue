<template>
  <div class="space-y-4">
    <!-- Advances as a history, floats and settlement -->
    <div class="rounded-lg border bg-white p-3">
      <div class="mb-2 flex flex-wrap items-baseline gap-2">
        <h2 class="text-sm font-semibold text-gray-800">Cash advanced</h2>
        <span class="text-xs text-gray-500">
          {{ vnd(money.data?.spent_total || 0) }} spent of
          {{ vnd(money.data?.quoted_total || 0) }} quoted ·
          {{ vnd(money.data?.advanced_total || 0) }} advanced
        </span>
        <Button
          v-if="money.data?.may_advance && !showAdvanceForm"
          class="ml-auto"
          @click="showAdvanceForm = true"
        >
          + Record advance
        </Button>
      </div>

      <!-- Every advance on its own line — a history, not a per-person
           sum (founder, A4 round 3). The per-holder float below stays:
           settlement closes a person's float, not a single line. -->
      <div class="overflow-x-auto">
      <table v-if="advanceRows.length" class="w-full min-w-[28rem] text-sm">
        <thead class="text-left text-xs text-gray-600">
          <tr>
            <th class="py-1 font-medium">Date</th>
            <th class="py-1 font-medium">To</th>
            <th class="py-1 text-right font-medium">Amount</th>
            <th class="py-1 pl-3 font-medium">Note</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in advanceRows" :key="row.name" class="border-t">
            <td class="whitespace-nowrap py-1 pr-2 tabular-nums text-gray-600">
              {{ row.transferred_on }}
            </td>
            <td class="py-1 pr-2 text-gray-900">{{ row.recipient }}</td>
            <td class="py-1 text-right tabular-nums">{{ vnd(row.amount) }}</td>
            <td class="py-1 pl-3 text-gray-500">{{ row.note }}</td>
          </tr>
        </tbody>
      </table>
      </div>
      <p v-if="!advanceRows.length" class="py-2 text-sm text-gray-400">
        No cash advanced on this job yet.
      </p>

      <h3
        v-if="floats.length"
        class="mt-3 border-t pt-3 text-xs font-semibold uppercase text-gray-500"
      >
        Currently holding
      </h3>
      <div v-if="floats.length" class="overflow-x-auto">
      <table class="w-full min-w-[32rem] text-sm">
        <thead class="text-left text-xs text-gray-600">
          <tr>
            <th class="py-1 font-medium">Holding</th>
            <th class="py-1 text-right font-medium">Advanced</th>
            <th class="py-1 text-right font-medium">Spent</th>
            <th class="py-1 text-right font-medium">Float</th>
            <th class="py-1 pl-3 font-medium">Settle</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="held in floats" :key="held.holder" class="border-t">
            <td class="py-1.5 pr-2 text-gray-900">{{ held.holder }}</td>
            <td class="py-1.5 pr-2 text-right tabular-nums text-gray-600">
              {{ vnd(held.advanced) }}
            </td>
            <td class="py-1.5 pr-2 text-right tabular-nums text-gray-600">
              {{ vnd(held.spent) }}
            </td>
            <td class="py-1.5 pr-2 text-right font-medium tabular-nums">
              {{ vnd(Math.abs(held.amount)) }}
            </td>
            <td class="py-1.5 pl-3">
              <span v-if="held.direction === EVEN" class="text-xs text-gray-400">
                Settled
              </span>
              <template v-else-if="confirming === held.holder">
                <span class="text-xs text-gray-700">{{ settleWording(held) }}?</span>
                <Button
                  class="ml-1"
                  variant="solid"
                  :loading="settle.loading"
                  @click="doSettle(held)"
                >
                  Confirm
                </Button>
                <Button class="ml-1" @click="confirming = null">Cancel</Button>
              </template>
              <template v-else>
                <span class="text-xs text-gray-700">{{ settleWording(held) }}</span>
                <Button
                  v-if="money.data?.may_settle"
                  class="ml-2"
                  @click="confirming = held.holder"
                >
                  Settle
                </Button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
      </div>
      <p v-if="settled" class="mt-1 text-xs text-blue-700">{{ settled }}</p>

      <!-- Recording an advance is the founder's move; the form stays
           out of sight until asked for (founder, A4 round 4: too much
           on this page). -->
      <div
        v-if="money.data?.may_advance && showAdvanceForm"
        class="mt-3 grid gap-2 border-t pt-3 sm:flex sm:flex-wrap sm:items-center"
      >
        <span class="text-xs font-medium text-gray-700">Advance</span>
        <select
          v-model="advanceForm.recipient"
          class="w-full rounded border-gray-200 py-2 pl-2 pr-8 text-sm sm:w-auto sm:py-1"
        >
          <option value="">Who receives it…</option>
          <option v-for="user in users.data || []" :key="user.name" :value="user.name">
            {{ user.full_name || user.name }}
          </option>
        </select>
        <VndInput
          v-model="advanceForm.amount"
          placeholder="Amount"
          class="w-full rounded border-gray-200 px-3 py-2.5 text-right text-xl tabular-nums sm:w-36 sm:px-2 sm:py-1 sm:text-sm"
        />
        <input
          v-model="advanceForm.note"
          placeholder="Note (optional)"
          class="w-full min-w-0 rounded border-gray-200 px-2 py-2 text-sm sm:flex-1 sm:py-1"
        />
        <Button
          class="w-full sm:w-auto"
          variant="solid"
          :disabled="!advanceForm.recipient || !parseVnd(advanceForm.amount)"
          :loading="advance.loading"
          @click="recordAdvance"
        >
          Record
        </Button>
      </div>
    </div>

    <!-- The ledger, plus the full-control entry form -->
    <div class="rounded-lg border bg-white p-3">
      <div class="mb-2 flex flex-wrap items-baseline gap-2">
        <h2 class="text-sm font-semibold text-gray-800">Expenses</h2>
        <span v-if="expenses.length" class="text-xs text-gray-500">
          {{ expenses.length }} · {{ vnd(money.data?.spent_total || 0) }}
        </span>
        <Button
          v-if="!showExpenseForm"
          class="ml-auto"
          @click="showExpenseForm = true"
        >
          + Log expense
        </Button>
      </div>

      <div class="overflow-x-auto">
      <table v-if="expenses.length" class="w-full min-w-[32rem] text-sm">
        <thead class="text-left text-xs text-gray-600">
          <tr>
            <th class="py-1 font-medium">Date</th>
            <th class="py-1 font-medium">Category</th>
            <th class="py-1 font-medium">What</th>
            <th class="py-1 font-medium">Paid by</th>
            <th class="py-1 text-right font-medium">Amount</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in expenses" :key="row.name" class="border-t">
            <td class="py-1 pr-2 whitespace-nowrap tabular-nums text-gray-600">
              {{ row.spent_on }}
            </td>
            <td class="py-1 pr-2 text-gray-800">
              {{ row.category || "—" }}
            </td>
            <td class="py-1 pr-2 text-gray-700">
              {{ row.description }}
              <a
                v-if="row.photo"
                :href="row.photo"
                target="_blank"
                rel="noopener"
                class="inline-flex items-center gap-1 text-blue-700 hover:underline"
              >
                <FeatherIcon name="paperclip" class="h-3 w-3" />
                receipt
              </a>
            </td>
            <td class="py-1 pr-2 whitespace-nowrap text-gray-500">
              {{ row.paid_by }}
              <span
                v-if="row.paid_from === FROM_COMPANY"
                class="rounded-full bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600"
                title="Paid by the company directly — settles no float"
              >
                company
              </span>
            </td>
            <td class="py-1 text-right tabular-nums">{{ vnd(row.amount) }}</td>
          </tr>
        </tbody>
      </table>
      </div>
      <p v-if="!expenses.length" class="py-2 text-sm text-gray-400">Nothing logged yet.</p>

      <!-- One form, two shapes: the inline desktop row becomes the
           big-thumb phone layout below `sm` on its own — no separate
           "log on phone" page to know about (founder, A4 round 3).
           Hidden until asked for (round 4). -->
      <div
        v-if="showExpenseForm"
        class="mt-3 grid gap-2 border-t pt-3 sm:flex sm:flex-wrap sm:items-center"
      >
        <VndInput
          v-model="expenseForm.amount"
          placeholder="Amount"
          class="w-full rounded border-gray-200 px-3 py-2.5 text-right text-xl tabular-nums sm:w-32 sm:px-2 sm:py-1 sm:text-sm"
        />
        <select
          v-model="expenseForm.category"
          class="w-full rounded border-gray-200 py-2 pl-2 pr-8 text-sm sm:w-auto sm:py-1"
        >
          <option value="">Uncategorised</option>
          <option
            v-for="title in categories.data || []"
            :key="title"
            :value="title"
          >
            {{ title }}
          </option>
        </select>
        <input
          v-model="expenseForm.description"
          placeholder="What was it for?"
          class="w-full min-w-0 rounded border-gray-200 px-2 py-2 text-sm sm:flex-1 sm:py-1"
        />
        <select
          v-model="expenseForm.paid_by"
          class="w-full rounded border-gray-200 py-2 pl-2 pr-8 text-sm sm:w-auto sm:py-1"
        >
          <option value="">paid by me</option>
          <option v-for="user in users.data || []" :key="user.name" :value="user.name">
            {{ user.full_name || user.name }}
          </option>
        </select>
        <select
          v-model="expenseForm.paid_from"
          class="w-full rounded border-gray-200 py-2 pl-2 pr-8 text-sm sm:w-auto sm:py-1"
          :class="expenseForm.paid_from ? '' : 'border-amber-400'"
          title="Whose money was it? An advance settles with the person holding it; the company's settles with nobody."
        >
          <option value="">whose money?</option>
          <option :value="FROM_ADVANCE">from advance</option>
          <option :value="FROM_COMPANY">company paid</option>
        </select>
        <Button
          class="w-full sm:w-auto"
          variant="solid"
          :disabled="!parseVnd(expenseForm.amount) || !expenseForm.paid_from"
          :loading="expense.loading"
          @click="logExpense"
        >
          Log
        </Button>
      </div>
    </div>

    <!-- Actual against quoted, per category — free, because the
         categories are the quote's own entries. Bars, not a bare
         table: how far along each budget is should read at a glance
         (founder, A4 round 2 — "like the apps on the market"). -->
    <div class="rounded-lg border bg-white p-3">
      <h2 class="mb-3 text-sm font-semibold text-gray-800">
        Where the money went
      </h2>
      <div class="space-y-3">
        <div v-for="row in money.data?.categories || []" :key="row.title">
          <div class="flex items-baseline gap-2 text-sm">
            <span class="font-medium text-gray-900">{{ row.title }}</span>
            <span class="ml-auto tabular-nums text-gray-700">
              {{ vnd(row.actual) }}
              <span class="text-gray-400">/ {{ vnd(row.quoted) }}</span>
            </span>
            <span
              class="w-24 text-right text-xs tabular-nums"
              :class="row.variance > 0 ? 'font-medium text-red-600' : 'text-gray-400'"
            >
              {{ row.variance > 0 ? "+" : "" }}{{ vnd(row.variance) }}
            </span>
          </div>
          <div class="mt-1 h-2 overflow-hidden rounded-full bg-gray-100">
            <div
              class="h-full rounded-full transition-all"
              :class="barClass(row)"
              :style="{ width: `${barWidth(row)}%` }"
            ></div>
          </div>
        </div>
      </div>
      <p class="mt-2 text-xs text-gray-500">
        Quoted cost is what the job expected to pay out for that category —
        not what the client is charged for it.
      </p>
    </div>

    <ErrorMessage :message="error" />
  </div>
</template>

<script setup>
import { computed, reactive, ref } from "vue"
import { Button, ErrorMessage, FeatherIcon, createResource } from "frappe-ui"
import { frappeErrorMessage } from "../utils/frappeError"
import { parseVnd, vnd } from "../utils/money"
import { EVEN, FROM_ADVANCE, FROM_COMPANY, RETURN } from "../data/money"
import VndInput from "./VndInput.vue"

const props = defineProps({ name: { type: String, required: true } })

// The job page's stat strip mirrors these numbers; it listens for this.
const emit = defineEmits(["changed"])

// Entry forms stay collapsed until asked for — the page reads first,
// writes second (founder, A4 round 4).
const showAdvanceForm = ref(false)
const showExpenseForm = ref(false)

const error = ref("")
const settled = ref("")
const confirming = ref(null)

const money = createResource({
  url: "auraos.api.job_money",
  makeParams: () => ({ job: props.name }),
  auto: true,
  onError(err) {
    error.value = frappeErrorMessage(err)
  },
})

const users = createResource({ url: "auraos.api.operating_users", auto: true })

const floats = computed(() => money.data?.floats || [])
const expenses = computed(() => money.data?.expenses || [])
// Newest first: the question is "what just went out", not archaeology.
const advanceRows = computed(() =>
  [...(money.data?.advances || [])].sort((a, b) =>
    String(b.transferred_on || "").localeCompare(String(a.transferred_on || ""))
  )
)

// The one endpoint that answers what an expense may be categorised as,
// shared with the phone screen — the actual-vs-quoted rows carry the
// same titles, but also the row for anything that landed outside them.
const categories = createResource({
  url: "auraos.api.job_expense_categories",
  makeParams: () => ({ job: props.name }),
  auto: true,
})

function settleWording(held) {
  return held.direction === RETURN
    ? `${held.holder} returns ${vnd(held.amount)}`
    : `Pay ${held.holder} ${vnd(-held.amount)}`
}

function reload() {
  error.value = ""
  money.reload()
  emit("changed")
}

// Budget bars: fill toward the quoted cost; spending past it turns the
// bar red. A category with no quoted cost (unplanned spend) is all red.
function barWidth(row) {
  if (!row.quoted) return row.actual ? 100 : 0
  return Math.min(100, Math.round((row.actual / row.quoted) * 100))
}

function barClass(row) {
  if (!row.actual) return "bg-gray-200"
  // green, not emerald — emerald is outside frappe-ui's palette and
  // renders transparent.
  return row.variance > 0 ? "bg-red-500" : "bg-green-500"
}

function fail(err) {
  error.value = frappeErrorMessage(err)
}

// -- advances --

const advanceForm = reactive({ recipient: "", amount: "", note: "" })

const advance = createResource({
  url: "auraos.api.record_job_advance",
  onSuccess() {
    advanceForm.amount = ""
    advanceForm.note = ""
    reload()
  },
  onError: fail,
})

function recordAdvance() {
  advance.submit({
    job: props.name,
    recipient: advanceForm.recipient,
    amount: parseVnd(advanceForm.amount),
    note: advanceForm.note || null,
  })
}

// -- expenses --

// paid_from is deliberately unset: it is the one field that decides who
// owes whom afterwards, and a founder logging a company transfer with
// somebody else's default would open a float in his own name.
const expenseForm = reactive({
  amount: "",
  category: "",
  description: "",
  paid_by: "",
  paid_from: "",
})

const expense = createResource({
  url: "auraos.api.log_job_expense",
  onSuccess() {
    expenseForm.amount = ""
    expenseForm.description = ""
    reload()
  },
  onError: fail,
})

function logExpense() {
  expense.submit({
    job: props.name,
    amount: parseVnd(expenseForm.amount),
    category: expenseForm.category || null,
    description: expenseForm.description || null,
    paid_by: expenseForm.paid_by || null,
    paid_from: expenseForm.paid_from,
  })
}

// -- settlement --

const settle = createResource({
  url: "auraos.api.settle_job",
  onSuccess(result) {
    confirming.value = null
    settled.value =
      result.direction === RETURN
        ? `${result.recipient} returned ${vnd(result.amount)} — float closed.`
        : `Paid ${result.recipient} ${vnd(-result.amount)} — float closed.`
    reload()
  },
  onError(err) {
    confirming.value = null
    fail(err)
  },
})

function doSettle(held) {
  settled.value = ""
  settle.submit({ job: props.name, holder: held.holder })
}
</script>

<template>
  <div class="space-y-4">
    <!-- Floats and settlement: who is holding company cash right now -->
    <div class="rounded-lg border bg-white p-3">
      <div class="mb-2 flex flex-wrap items-baseline gap-2">
        <h2 class="text-sm font-semibold text-gray-800">Money out</h2>
        <span class="text-xs text-gray-500">
          {{ vnd(money.data?.spent_total || 0) }} spent of
          {{ vnd(money.data?.quoted_total || 0) }} quoted ·
          {{ vnd(money.data?.advanced_total || 0) }} advanced
        </span>
        <router-link
          :to="`/jobs/${name}/spend`"
          class="ml-auto text-sm font-medium text-blue-700 hover:underline"
        >
          Log expense on phone →
        </router-link>
      </div>

      <table v-if="floats.length" class="w-full text-sm">
        <thead class="text-left text-xs text-gray-600">
          <tr>
            <th class="py-1 font-medium">Holding</th>
            <th class="py-1 text-right font-medium">Advanced</th>
            <th class="py-1 text-right font-medium">Spent</th>
            <th class="py-1 text-right font-medium">Balance</th>
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
              {{ vnd(Math.abs(held.outstanding)) }}
            </td>
            <td class="py-1.5 pl-3">
              <span v-if="held.direction === 'Even'" class="text-xs text-gray-400">
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
      <p v-else class="py-2 text-sm text-gray-400">
        Nobody is holding cash for this job.
      </p>

      <p v-if="settled" class="mt-1 text-xs text-blue-700">{{ settled }}</p>

      <!-- Recording an advance is the founder's move -->
      <div
        v-if="money.data?.may_advance"
        class="mt-3 flex flex-wrap items-center gap-2 border-t pt-3"
      >
        <span class="text-xs font-medium text-gray-700">Advance</span>
        <select
          v-model="advanceForm.recipient"
          class="rounded border-gray-200 py-1 pl-2 pr-8 text-sm"
        >
          <option value="">Who receives it…</option>
          <option v-for="user in users.data || []" :key="user.name" :value="user.name">
            {{ user.full_name || user.name }}
          </option>
        </select>
        <input
          v-model="advanceForm.amount"
          inputmode="numeric"
          placeholder="Amount"
          class="w-36 rounded border-gray-200 px-2 py-1 text-right text-sm tabular-nums"
        />
        <input
          v-model="advanceForm.note"
          placeholder="Note (optional)"
          class="min-w-0 flex-1 rounded border-gray-200 px-2 py-1 text-sm"
        />
        <Button
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
      <h2 class="mb-2 text-sm font-semibold text-gray-800">Expenses</h2>

      <table v-if="expenses.length" class="w-full text-sm">
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
                class="text-blue-700 hover:underline"
              >
                📷 receipt
              </a>
            </td>
            <td class="py-1 pr-2 whitespace-nowrap text-gray-500">
              {{ row.paid_by }}
              <span
                v-if="row.paid_from === 'Company'"
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
      <p v-else class="py-2 text-sm text-gray-400">Nothing logged yet.</p>

      <div class="mt-3 flex flex-wrap items-center gap-2 border-t pt-3">
        <input
          v-model="expenseForm.amount"
          inputmode="numeric"
          placeholder="Amount"
          class="w-32 rounded border-gray-200 px-2 py-1 text-right text-sm tabular-nums"
        />
        <select
          v-model="expenseForm.category"
          class="rounded border-gray-200 py-1 pl-2 pr-8 text-sm"
        >
          <option value="">Uncategorised</option>
          <option v-for="title in categories" :key="title" :value="title">
            {{ title }}
          </option>
        </select>
        <input
          v-model="expenseForm.description"
          placeholder="What was it for?"
          class="min-w-0 flex-1 rounded border-gray-200 px-2 py-1 text-sm"
        />
        <select
          v-model="expenseForm.paid_by"
          class="rounded border-gray-200 py-1 pl-2 pr-8 text-sm"
        >
          <option value="">paid by me</option>
          <option v-for="user in users.data || []" :key="user.name" :value="user.name">
            {{ user.full_name || user.name }}
          </option>
        </select>
        <select
          v-model="expenseForm.paid_from"
          class="rounded border-gray-200 py-1 pl-2 pr-8 text-sm"
          title="Advance = out of the float that person holds"
        >
          <option value="Advance">from advance</option>
          <option value="Company">company paid</option>
        </select>
        <Button
          variant="solid"
          :disabled="!parseVnd(expenseForm.amount)"
          :loading="expense.loading"
          @click="logExpense"
        >
          Log
        </Button>
      </div>
    </div>

    <!-- Actual against quoted, per category — free, because the
         categories are the quote's own entries -->
    <div class="rounded-lg border bg-white p-3">
      <h2 class="mb-2 text-sm font-semibold text-gray-800">
        Where the money went
      </h2>
      <table class="w-full text-sm">
        <thead class="text-left text-xs text-gray-600">
          <tr>
            <th class="py-1 font-medium">Category</th>
            <th class="py-1 text-right font-medium">Quoted cost</th>
            <th class="py-1 text-right font-medium">Actual</th>
            <th class="py-1 text-right font-medium">Over / under</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in money.data?.categories || []"
            :key="row.title"
            class="border-t"
          >
            <td class="py-1 pr-2 text-gray-900">{{ row.title }}</td>
            <td class="py-1 pr-2 text-right tabular-nums text-gray-600">
              {{ vnd(row.quoted) }}
            </td>
            <td class="py-1 pr-2 text-right tabular-nums">{{ vnd(row.actual) }}</td>
            <td
              class="py-1 text-right tabular-nums"
              :class="row.variance > 0 ? 'text-amber-700' : 'text-gray-500'"
            >
              {{ row.variance > 0 ? "+" : "" }}{{ vnd(row.variance) }}
            </td>
          </tr>
        </tbody>
      </table>
      <p class="mt-1 text-xs text-gray-500">
        Quoted cost is what the job expected to pay out for that category —
        not what the client is charged for it.
      </p>
    </div>

    <ErrorMessage :message="error" />
  </div>
</template>

<script setup>
import { computed, reactive, ref } from "vue"
import { Button, ErrorMessage, createResource } from "frappe-ui"
import { frappeErrorMessage } from "../utils/frappeError"
import { parseVnd, vnd } from "../utils/money"

const props = defineProps({ name: { type: String, required: true } })

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
// The quote's own entries, straight off the actual-vs-quoted rows —
// minus the bucket that only exists once something lands outside them.
const categories = computed(() =>
  (money.data?.categories || [])
    .map((row) => row.title)
    .filter((title) => title !== "Uncategorised")
)

function settleWording(held) {
  return held.direction === "Return"
    ? `${held.holder} returns ${vnd(held.outstanding)}`
    : `Pay ${held.holder} ${vnd(-held.outstanding)}`
}

function reload() {
  error.value = ""
  money.reload()
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

const expenseForm = reactive({
  amount: "",
  category: "",
  description: "",
  paid_by: "",
  paid_from: "Advance",
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
      result.direction === "Return"
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

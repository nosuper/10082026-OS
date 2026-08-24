<template>
  <div>
    <!-- One plan, three ways of reading it: the list to write it, the
         board to work it, the timeline to see whether it fits. -->
    <div class="mb-3 flex flex-wrap items-center gap-2">
      <div class="flex items-center gap-1 rounded-md bg-gray-100 p-0.5">
        <button
          v-for="option in VIEWS"
          :key="option"
          class="rounded px-2.5 py-1 text-sm font-medium transition-colors"
          :class="
            view === option
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-500 hover:text-gray-800'
          "
          @click="view = option"
        >
          {{ option }}
        </button>
      </div>
      <span class="text-sm tabular-nums text-gray-400">
        {{ tasks.length }} task{{ tasks.length === 1 ? "" : "s" }}
      </span>
      <span v-if="lateCount" class="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-xs text-red-700">
        <FeatherIcon name="alert-circle" class="h-3 w-3" />
        {{ lateCount }} overdue
      </span>
      <Button
        v-if="canPlan"
        class="ml-auto"
        variant="solid"
        icon-left="plus"
        @click="startDraft"
      >
        Add task
      </Button>
    </div>

    <ErrorMessage class="mb-2" :message="error" />

    <!-- -- list: the plan as it is written -- -->
    <div v-show="view === 'List'" class="overflow-x-auto rounded-lg border bg-white">
      <table class="w-full min-w-[46rem] text-sm">
        <thead class="border-b bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-3 py-2 font-medium">Task</th>
            <th class="px-3 py-2 font-medium">Craft</th>
            <th class="px-3 py-2 font-medium">Who</th>
            <th class="px-3 py-2 font-medium">Start</th>
            <th class="px-3 py-2 font-medium">Due</th>
            <th class="px-3 py-2 font-medium">Status</th>
            <th v-if="canPlan" class="w-8 px-3 py-2"></th>
          </tr>
        </thead>
        <tbody class="divide-y">
          <tr v-if="draft" class="bg-blue-50/40">
            <td class="px-3 py-2">
              <input
                ref="draftTitle"
                v-model.trim="draft.title"
                type="text"
                placeholder="What has to happen"
                class="w-full rounded border-gray-300 py-1 text-sm"
                @keyup.enter="saveDraft"
                @keyup.esc="draft = null"
              />
            </td>
            <td class="px-3 py-2">
              <select v-model="draft.craft" class="w-full rounded border-gray-300 py-1 text-sm">
                <option :value="null">—</option>
                <option v-for="craft in crafts" :key="craft" :value="craft">
                  {{ craft }}
                </option>
              </select>
            </td>
            <td class="px-3 py-2">
              <select v-model="draft.assigned_to" class="w-full rounded border-gray-300 py-1 text-sm">
                <option :value="null">—</option>
                <option v-for="person in people" :key="person.name" :value="person.name">
                  {{ person.full_name || person.name }}
                </option>
              </select>
            </td>
            <td class="px-3 py-2">
              <input v-model="draft.start_date" type="date" class="rounded border-gray-300 py-1 text-sm" />
            </td>
            <td class="px-3 py-2">
              <input v-model="draft.end_date" type="date" class="rounded border-gray-300 py-1 text-sm" />
            </td>
            <td class="px-3 py-2">
              <select v-model="draft.status" class="w-full rounded border-gray-300 py-1 text-sm">
                <option v-for="status in statuses" :key="status" :value="status">
                  {{ status }}
                </option>
              </select>
            </td>
            <td class="px-3 py-2">
              <Button variant="ghost" icon="check" title="Save" @click="saveDraft" />
            </td>
          </tr>

          <tr v-for="task in tasks" :key="task.name" class="align-middle">
            <td class="px-3 py-2">
              <input
                v-if="canPlan"
                :value="task.title"
                type="text"
                class="w-full rounded border-transparent py-1 text-sm hover:border-gray-200 focus:border-gray-400"
                @change="patch(task, { title: $event.target.value })"
              />
              <span v-else class="font-medium text-gray-900">{{ task.title }}</span>
              <!-- The note is the other half of a crew card: whoever
                   holds the task may say what is happening on it. -->
              <input
                v-if="canMove(task)"
                :value="task.notes"
                type="text"
                placeholder="Add a note"
                class="mt-0.5 w-full rounded border-transparent px-0 py-0.5 text-xs text-gray-600 placeholder-gray-400 hover:border-gray-200 focus:border-gray-400"
                @change="note(task, $event.target.value)"
              />
              <div v-else-if="task.notes" class="mt-0.5 text-xs text-gray-500">
                {{ task.notes }}
              </div>
            </td>
            <td class="px-3 py-2">
              <select
                v-if="canPlan"
                :value="task.craft"
                class="w-full rounded border-transparent py-1 text-sm hover:border-gray-200"
                @change="patch(task, { craft: $event.target.value || null })"
              >
                <option value="">—</option>
                <option v-for="craft in crafts" :key="craft" :value="craft">
                  {{ craft }}
                </option>
              </select>
              <span v-else class="text-gray-600">{{ task.craft || "—" }}</span>
            </td>
            <td class="px-3 py-2">
              <select
                v-if="canPlan"
                :value="task.assigned_to"
                class="w-full rounded border-transparent py-1 text-sm hover:border-gray-200"
                @change="patch(task, { assigned_to: $event.target.value || null })"
              >
                <option value="">—</option>
                <option v-for="person in people" :key="person.name" :value="person.name">
                  {{ person.full_name || person.name }}
                </option>
              </select>
              <span v-else :class="mine(task) ? 'font-medium text-gray-900' : 'text-gray-600'">
                {{ personLabel(task.assigned_to) }}
              </span>
            </td>
            <td class="px-3 py-2">
              <input
                v-if="canPlan"
                :value="task.start_date"
                type="date"
                class="rounded border-transparent py-1 text-sm hover:border-gray-200"
                @change="patch(task, { start_date: $event.target.value || null })"
              />
              <span v-else class="tabular-nums text-gray-600">
                {{ shortDate(task.start_date) || "—" }}
              </span>
            </td>
            <td class="px-3 py-2">
              <input
                v-if="canPlan"
                :value="task.end_date"
                type="date"
                class="rounded border-transparent py-1 text-sm hover:border-gray-200"
                @change="patch(task, { end_date: $event.target.value || null })"
              />
              <span v-else class="tabular-nums text-gray-600">
                {{ shortDate(task.end_date) || "—" }}
              </span>
              <span v-if="daysLate(task)" class="ml-1 text-xs text-red-700">
                +{{ daysLate(task) }}d
              </span>
            </td>
            <td class="px-3 py-2">
              <select
                v-if="canMove(task)"
                :value="task.status"
                class="rounded border-transparent py-1 text-sm hover:border-gray-200"
                @change="move(task, $event.target.value)"
              >
                <option v-for="status in statuses" :key="status" :value="status">
                  {{ status }}
                </option>
              </select>
              <span
                v-else
                class="inline-block rounded-full px-2 py-0.5 text-xs"
                :class="statusPill(task.status)"
              >
                {{ task.status }}
              </span>
            </td>
            <td v-if="canPlan" class="px-3 py-2">
              <Button variant="ghost" icon="trash-2" title="Remove" @click="remove(task)" />
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!tasks.length && !draft" class="px-3 py-8 text-center text-sm text-gray-400">
        {{ emptyMessage }}
      </p>
    </div>

    <!-- -- board: the plan as it is worked -- -->
    <div v-show="view === 'Board'" class="flex gap-3 overflow-x-auto pb-2">
      <div
        v-for="status in statuses"
        :key="status"
        class="flex w-64 shrink-0 flex-col rounded-lg transition-colors"
        :class="
          dragOverStatus === status
            ? 'bg-blue-50 ring-2 ring-inset ring-blue-300'
            : 'bg-gray-100'
        "
        @dragover.prevent="dragOverStatus = status"
        @dragleave="onDragLeave(status, $event)"
        @drop="onDrop(status)"
      >
        <div class="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-800">
          <span class="h-2 w-2 shrink-0 rounded-full" :class="statusDot(status)"></span>
          {{ status }}
          <span class="text-xs font-normal text-gray-500">
            {{ byStatus[status]?.length || 0 }}
          </span>
        </div>
        <div class="flex min-h-24 flex-1 flex-col gap-2 px-2 pb-2">
          <div
            v-for="task in byStatus[status]"
            :key="task.name"
            class="rounded-md border bg-white p-2.5 shadow-sm transition-shadow"
            :class="[
              canMove(task) ? 'cursor-grab hover:border-gray-300 hover:shadow' : 'cursor-default',
              dragged === task ? 'opacity-50' : '',
              mine(task) ? 'border-l-4 border-l-blue-400' : '',
            ]"
            :draggable="canMove(task)"
            @dragstart="dragged = task"
            @dragend="((dragged = null), (dragOverStatus = null))"
          >
            <div class="text-sm font-medium text-gray-900">{{ task.title }}</div>
            <div class="mt-1 flex flex-wrap items-center gap-1.5 text-xs">
              <span v-if="task.craft" class="rounded-full bg-gray-100 px-2 py-0.5 text-gray-700">
                {{ task.craft }}
              </span>
              <span :class="mine(task) ? 'font-medium text-gray-800' : 'text-gray-500'">
                {{ personLabel(task.assigned_to) }}
              </span>
            </div>
            <div class="mt-1 flex items-center gap-1.5 text-xs tabular-nums text-gray-500">
              <template v-if="task.start_date || task.end_date">
                {{ shortDate(task.start_date) || "?" }} → {{ shortDate(task.end_date) || "?" }}
              </template>
              <span v-else class="text-gray-400">not scheduled</span>
              <span v-if="daysLate(task)" class="font-medium text-red-700">
                +{{ daysLate(task) }}d
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- -- timeline: the plan as a shape -- -->
    <div v-show="view === 'Timeline'" class="rounded-lg border bg-white p-3">
      <div v-if="scheduled.length" class="overflow-x-auto">
        <div class="min-w-[36rem]">
          <!-- Month ruler above the bars; the bars hang off the same
               percentage scale, so the two can never drift apart. -->
          <div class="flex">
            <div class="w-40 shrink-0 sm:w-56"></div>
            <div class="relative h-5 flex-1 border-b">
              <span
                v-for="tick in ticks"
                :key="tick.at"
                class="absolute -top-0.5 text-[11px] text-gray-400"
                :style="{ left: `${tick.at}%` }"
              >
                {{ tick.label }}
              </span>
            </div>
          </div>

          <div
            v-for="task in scheduled"
            :key="task.name"
            class="flex items-center border-b border-gray-50 py-1.5 last:border-b-0"
          >
            <div class="w-40 shrink-0 pr-3 sm:w-56">
              <div class="truncate text-sm text-gray-900" :title="task.title">
                {{ task.title }}
              </div>
              <div class="truncate text-xs text-gray-500">
                {{ personLabel(task.assigned_to) }}
                <template v-if="task.craft"> · {{ task.craft }}</template>
              </div>
            </div>
            <div class="relative h-6 flex-1">
              <!-- The gridlines the ruler names, so a bar can be read
                   against a month without counting pixels. -->
              <span
                v-for="tick in ticks"
                :key="tick.at"
                class="absolute top-0 h-full w-px bg-gray-100"
                :style="{ left: `${tick.at}%` }"
              ></span>
              <span
                v-if="todayAt !== null"
                class="absolute top-0 h-full w-px bg-red-300"
                :style="{ left: `${todayAt}%` }"
                title="Today"
              ></span>
              <span
                class="absolute top-1 flex h-4 items-center rounded px-1.5 text-[11px] text-white"
                :class="[statusBar(task.status), mine(task) ? 'ring-2 ring-blue-300' : '']"
                :style="barStyle(task)"
                :title="`${task.title} · ${task.start_date} → ${task.end_date} · ${task.status}`"
              >
                <span class="truncate">{{ task.status }}</span>
              </span>
            </div>
          </div>
        </div>
      </div>
      <p v-else class="py-8 text-center text-sm text-gray-400">
        Nothing dated yet - a task needs a start and a due date to earn a bar.
      </p>

      <div v-if="unscheduled.length" class="mt-3 border-t pt-2">
        <div class="mb-1 text-xs uppercase text-gray-500">Not scheduled</div>
        <div class="flex flex-wrap gap-1.5">
          <span
            v-for="task in unscheduled"
            :key="task.name"
            class="rounded-full px-2 py-0.5 text-xs"
            :class="statusPill(task.status)"
          >
            {{ task.title }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch } from "vue"
import { Button, ErrorMessage, FeatherIcon, createResource } from "frappe-ui"
import { frappeErrorMessage } from "../utils/frappeError"
import {
  DAY_MS,
  STATUSES,
  daysLate,
  parseDate,
  shortDate,
  statusBar,
  statusDot,
  statusPill,
} from "../data/jobTasks"

const props = defineProps({
  job: { type: String, required: true },
  // What the screen says when the plan is empty - a producer is told to
  // write one, a crew member that nobody has yet.
  emptyMessage: {
    type: String,
    default: "No tasks yet - add the first one.",
  },
})

const VIEWS = ["List", "Board", "Timeline"]
const view = ref("List")
const error = ref("")

const plan = createResource({
  url: "auraos.api.job_tasks",
  makeParams: () => ({ job: props.job }),
  auto: true,
  onSuccess() {
    error.value = ""
  },
  onError(err) {
    error.value = frappeErrorMessage(err)
  },
})

watch(() => props.job, () => plan.reload())

const tasks = computed(() => plan.data?.tasks || [])
const statuses = computed(() => plan.data?.statuses || STATUSES)
const canPlan = computed(() => !!plan.data?.can_plan)
const me = computed(() => plan.data?.user)

// Whose card this is, and therefore who may move it: a crew member
// moves their own, whoever runs the job moves any of them.
function mine(task) {
  return !!task.assigned_to && task.assigned_to === me.value
}

function canMove(task) {
  return canPlan.value || mine(task)
}

const lateCount = computed(() => tasks.value.filter((task) => daysLate(task)).length)

// Names for the people on this job, so a card reads "Minh" rather than
// an email. Served with the plan, because crew cannot list users.
const named = computed(() => plan.data?.people || {})

function personLabel(email) {
  if (!email) return "Unassigned"
  return named.value[email] || email.split("@")[0]
}

// -- the planner's vocabularies (both endpoints refuse a crew session,
//    so they are only fetched once the plan says this one may plan) --

const craftList = createResource({ url: "auraos.api.task_crafts" })
const assignable = createResource({ url: "auraos.api.assignable_users" })

watch(canPlan, (allowed) => {
  if (!allowed) return
  craftList.fetch()
  assignable.fetch()
})

const crafts = computed(() => craftList.data || [])
const people = computed(() => assignable.data || [])

// -- writing --

const save = createResource({
  url: "auraos.api.save_job_task",
  onSuccess() {
    error.value = ""
    plan.reload()
  },
  onError(err) {
    error.value = frappeErrorMessage(err)
    plan.reload()
  },
})

function patch(task, values) {
  save.submit({ job: props.job, values: { name: task.name, ...values } })
}

const draft = ref(null)
const draftTitle = ref(null)

function startDraft() {
  draft.value = {
    title: "",
    craft: null,
    assigned_to: null,
    start_date: null,
    end_date: null,
    status: statuses.value[0],
  }
  nextTick(() => draftTitle.value?.focus())
}

function saveDraft() {
  if (!draft.value?.title) return
  save.submit({ job: props.job, values: { ...draft.value } })
  draft.value = null
}

const drop = createResource({
  url: "auraos.api.delete_job_task",
  onSuccess() {
    error.value = ""
    plan.reload()
  },
  onError(err) {
    error.value = frappeErrorMessage(err)
    plan.reload()
  },
})

function remove(task) {
  drop.submit({ task: task.name })
}

// The one write a crew session may make, through its own endpoint.
const setStatus = createResource({
  url: "auraos.api.set_job_task_status",
  onSuccess() {
    error.value = ""
    plan.reload()
  },
  onError(err) {
    error.value = frappeErrorMessage(err)
    plan.reload()
  },
})

const setNote = createResource({
  url: "auraos.api.set_job_task_note",
  onSuccess() {
    error.value = ""
    plan.reload()
  },
  onError(err) {
    error.value = frappeErrorMessage(err)
    plan.reload()
  },
})

function note(task, text) {
  if ((task.notes || "") === text) return
  setNote.submit({ task: task.name, note: text })
}

function move(task, status) {
  if (task.status === status) return
  // Move the card before the server answers - a drop that waits out a
  // round-trip reads as lag (the jobs board settled this).
  task.status = status
  setStatus.submit({ task: task.name, status })
}

// -- board --

const byStatus = computed(() => {
  const map = {}
  for (const task of tasks.value) (map[task.status] ||= []).push(task)
  return map
})

const dragged = ref(null)
const dragOverStatus = ref(null)

function onDragLeave(status, event) {
  if (dragOverStatus.value !== status) return
  if (event.relatedTarget && event.currentTarget.contains(event.relatedTarget)) {
    return
  }
  dragOverStatus.value = null
}

function onDrop(status) {
  const task = dragged.value
  dragged.value = null
  dragOverStatus.value = null
  if (!task || !canMove(task)) return
  move(task, status)
}

// -- timeline --

const scheduled = computed(() =>
  tasks.value.filter((task) => task.start_date && task.end_date)
)

const unscheduled = computed(() =>
  tasks.value.filter((task) => !(task.start_date && task.end_date))
)

// The window the bars are drawn in: the whole plan, padded by a day at
// each end so a bar never sits flush against the edge.
const span = computed(() => {
  const starts = scheduled.value.map((task) => parseDate(task.start_date))
  const ends = scheduled.value.map((task) => parseDate(task.end_date))
  if (!starts.length) return null
  const from = new Date(Math.min(...starts) - DAY_MS)
  const to = new Date(Math.max(...ends) + DAY_MS)
  return { from, to, days: Math.max(1, (to - from) / DAY_MS) }
})

function positionOf(date) {
  if (!span.value || !date) return null
  return ((date - span.value.from) / DAY_MS / span.value.days) * 100
}

function barStyle(task) {
  const from = positionOf(parseDate(task.start_date))
  const to = positionOf(parseDate(task.end_date))
  if (from === null || to === null) return {}
  // A one-day task ends where it starts, so the bar is widened to the
  // day it occupies rather than rendering as a hairline.
  const width = Math.max(to - from, 100 / span.value.days)
  return { left: `${from}%`, width: `${width}%` }
}

function dayLabel(date) {
  return `${date.getDate()}/${date.getMonth() + 1}`
}

// A tick at the first of each month the plan crosses; a short plan that
// crosses none is ticked at its two ends instead, so the ruler is never
// blank.
const ticks = computed(() => {
  if (!span.value) return []
  const marks = []
  const cursor = new Date(span.value.from.getFullYear(), span.value.from.getMonth() + 1, 1)
  while (cursor <= span.value.to) {
    marks.push({ at: positionOf(new Date(cursor)), label: `Thg ${cursor.getMonth() + 1}` })
    cursor.setMonth(cursor.getMonth() + 1)
  }
  if (marks.length) return marks
  return [
    { at: 0, label: dayLabel(span.value.from) },
    { at: 100, label: dayLabel(span.value.to) },
  ]
})

const todayAt = computed(() => {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const at = positionOf(today)
  return at === null || at < 0 || at > 100 ? null : at
})

defineExpose({ reload: () => plan.reload() })
</script>

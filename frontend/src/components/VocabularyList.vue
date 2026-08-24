<!--
  One managed vocabulary on the Settings screen (T3.5, issue #29): the
  deal-source or project-type list, add / rename / remove.

  The two in-use rules are the server's (auraos.lib.vocabulary) - this
  screen only makes them visible before they are hit: a value on a deal
  says so, its Remove is disabled with the reason on hover, and Rename
  stays offered because renaming carries those deals across.
-->
<template>
  <div>
    <div class="flex items-baseline gap-2">
      <h3 class="text-sm font-semibold text-gray-800">{{ vocab.label }}</h3>
      <span class="text-xs text-gray-400">{{ vocab.values.length }}</span>
    </div>

    <ul class="mt-2 divide-y rounded border">
      <li
        v-for="row in vocab.values"
        :key="row.name"
        class="flex flex-wrap items-center gap-2 px-2 py-1.5 text-sm"
      >
        <template v-if="editing === row.name">
          <input
            v-model="draft"
            class="w-44 rounded border-gray-200 px-2 py-1 text-sm"
            @keyup.enter="rename(row)"
            @keyup.esc="editing = null"
          />
          <Button variant="solid" :loading="busy" @click="rename(row)">
            Save
          </Button>
          <button class="text-xs text-gray-500 underline" @click="editing = null">
            Cancel
          </button>
        </template>
        <template v-else>
          <span class="text-gray-900">{{ row.name }}</span>
          <span v-if="row.in_use" class="text-xs text-gray-400">
            on {{ row.in_use }} {{ row.in_use === 1 ? "deal" : "deals" }}
          </span>
          <button
            class="ml-auto text-xs text-gray-500 underline"
            @click="startRename(row)"
          >
            Rename
          </button>
          <button
            class="text-xs underline"
            :class="row.in_use ? 'cursor-not-allowed text-gray-300' : 'text-gray-500'"
            :disabled="!!row.in_use"
            :title="row.in_use ? inUseHint(row) : 'Remove this value'"
            @click="remove(row)"
          >
            Remove
          </button>
        </template>
      </li>
      <li v-if="!vocab.values.length" class="px-2 py-1.5 text-xs text-gray-400">
        Nothing in this list yet.
      </li>
    </ul>

    <div class="mt-2 flex items-center gap-2">
      <input
        v-model="added"
        class="w-44 rounded border-gray-200 px-2 py-1 text-sm"
        :placeholder="`Add to ${vocab.label.toLowerCase()}`"
        @keyup.enter="add"
      />
      <Button :loading="busy" @click="add">Add</Button>
    </div>

    <ErrorMessage class="mt-2" :message="error" />
  </div>
</template>

<script setup>
import { ref } from "vue"
import { Button, ErrorMessage, createResource } from "frappe-ui"
import { frappeErrorMessage } from "../utils/frappeError"

const props = defineProps({ vocab: { type: Object, required: true } })
// Every endpoint answers with the whole set of lists, so the parent
// re-renders from the server's own view rather than a guessed one.
const emit = defineEmits(["updated"])

const added = ref("")
const editing = ref(null)
const draft = ref("")
const busy = ref(false)
const error = ref("")

function inUseHint(row) {
  const deals = row.in_use === 1 ? "deal" : "deals"
  return `${row.name} is on ${row.in_use} ${deals} - rename it instead, or clear it from those ${deals} first.`
}

function startRename(row) {
  error.value = ""
  editing.value = row.name
  draft.value = row.name
}

const adder = createResource({ url: "auraos.api.add_vocabulary_value" })
const renamer = createResource({ url: "auraos.api.rename_vocabulary_value" })
const remover = createResource({ url: "auraos.api.remove_vocabulary_value" })

// Every refusal this screen can provoke is the server's - an empty
// value, a duplicate, a merge, a value still on a deal - so they are
// shown as they were phrased rather than second-guessed here.
async function call(resource, params) {
  error.value = ""
  busy.value = true
  try {
    emit("updated", await resource.submit({ kind: props.vocab.key, ...params }))
    return true
  } catch (err) {
    error.value = frappeErrorMessage(err)
    return false
  } finally {
    busy.value = false
  }
}

async function add() {
  const value = added.value.trim()
  if (!value) return
  if (await call(adder, { value })) {
    added.value = ""
  }
}

async function rename(row) {
  const value = draft.value.trim()
  if (!value || value === row.name) {
    editing.value = null
    return
  }
  if (await call(renamer, { value: row.name, new_value: value })) {
    editing.value = null
  }
}

function remove(row) {
  if (row.in_use) return
  call(remover, { value: row.name })
}
</script>

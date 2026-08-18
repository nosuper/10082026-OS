<template>
  <Dialog
    :modelValue="modelValue"
    @update:modelValue="$emit('update:modelValue', $event)"
    :options="{ title: `Mark “${dealTitle}” as Lost` }"
  >
    <template #body-title>
      <div class="min-w-0">
        <h3 class="font-display text-base font-semibold tracking-tight text-carbon">
          Mark “{{ dealTitle }}” as Lost
        </h3>
        <p class="mt-0.5 text-xs text-muted">
          A reason is required. The note is for anything the list cannot say.
        </p>
      </div>
    </template>
    <template #body-content>
      <div class="space-y-4">
        <label class="block">
          <span class="text-xs text-muted">
            Why was it lost?
            <span class="text-accent" aria-hidden="true">*</span>
          </span>
          <select
            v-model="reason"
            required
            class="mt-1.5 w-full rounded-[10px] border border-hairline bg-paper py-2 pl-2.5 pr-8 text-sm text-carbon focus:border-carbon/30 focus:ring-0"
          >
            <option v-for="option in reasonOptions" :key="option" :value="option">
              {{ option }}
            </option>
          </select>
        </label>
        <label class="block">
          <span class="text-xs text-muted">Note (optional)</span>
          <textarea
            v-model="note"
            rows="3"
            class="mt-1.5 w-full rounded-[10px] border border-hairline bg-paper px-2.5 py-2 text-sm text-carbon placeholder-faint focus:border-carbon/30 focus:ring-0"
          ></textarea>
        </label>
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button @click="$emit('update:modelValue', false)">Cancel</Button>
        <Button
          variant="solid"
          :disabled="!reason"
          :class="reason ? '!bg-accent hover:!bg-accent-ink' : ''"
          @click="confirm"
        >
          Mark Lost
        </Button>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, watch } from "vue"
import { Dialog, Button } from "frappe-ui"

// Fixed vocabulary from the spec - mirrors the Deal.lost_reason Select.
const LOST_REASONS = ["Price", "Timing", "Silence", "Competitor", "Scope"]

const props = defineProps({
  modelValue: Boolean,
  dealTitle: { type: String, default: "" },
})
const emit = defineEmits(["update:modelValue", "confirm"])

const reason = ref("")
const note = ref("")

const reasonOptions = ["", ...LOST_REASONS]

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      reason.value = ""
      note.value = ""
    }
  }
)

function confirm() {
  emit("confirm", { reason: reason.value, note: note.value })
}
</script>

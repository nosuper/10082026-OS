<template>
  <Dialog
    :modelValue="modelValue"
    @update:modelValue="$emit('update:modelValue', $event)"
    :options="{ title: `Mark “${dealTitle}” as Lost` }"
  >
    <template #body-content>
      <div class="space-y-4">
        <FormControl
          type="select"
          label="Why was it lost?"
          :options="reasonOptions"
          v-model="reason"
          required
        />
        <FormControl
          type="textarea"
          label="Note (optional)"
          v-model="note"
        />
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button @click="$emit('update:modelValue', false)">Cancel</Button>
        <Button
          variant="solid"
          theme="red"
          :disabled="!reason"
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
import { Dialog, Button, FormControl } from "frappe-ui"

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

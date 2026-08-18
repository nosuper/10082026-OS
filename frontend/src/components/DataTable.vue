<template>
  <div class="overflow-hidden rounded-card border border-hairline bg-paper shadow-card">
    <div v-if="title || $slots.action" class="flex items-center gap-2 border-b border-hairline px-4 py-3">
      <h2 class="font-display text-sm font-semibold text-carbon">{{ title }}</h2>
      <span v-if="count !== null" class="aura-num text-xs text-faint">{{ count }}</span>
      <div class="ml-auto"><slot name="action" /></div>
    </div>

    <div class="overflow-x-auto">
      <table class="w-full border-collapse text-sm">
        <thead>
          <tr class="border-b border-hairline bg-canvas/60">
            <th
              v-for="col in columns"
              :key="col.key"
              class="aura-eyebrow whitespace-nowrap px-4 py-2 text-left font-medium"
              :class="col.align === 'right' ? 'text-right' : ''"
              :style="col.width ? { width: col.width } : null"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, i) in rows"
            :key="rowKey ? row[rowKey] : i"
            class="border-b border-hairline last:border-0"
            :class="clickable ? 'cursor-pointer hover:bg-canvas' : ''"
            @click="clickable ? $emit('rowClick', row) : null"
          >
            <td
              v-for="col in columns"
              :key="col.key"
              class="px-4 py-3 align-middle"
              :class="col.align === 'right' ? 'text-right' : ''"
            >
              <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
                <span class="text-carbon">{{ row[col.key] ?? "-" }}</span>
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="!rows.length" class="border-t border-hairline">
      <slot name="empty">
        <EmptyState :title="emptyTitle" />
      </slot>
    </div>

    <div v-if="$slots.footer" class="border-t border-hairline px-4 py-2 text-xs text-faint">
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup>
import EmptyState from "./EmptyState.vue"

// Columns: [{ key, label, align, width }]. Cells are overridable per key so
// pages never rebuild table chrome to render a pill or a money value.
defineProps({
  title: { type: String, default: "" },
  count: { type: [Number, String], default: null },
  columns: { type: Array, required: true },
  rows: { type: Array, default: () => [] },
  rowKey: { type: String, default: "name" },
  clickable: { type: Boolean, default: false },
  emptyTitle: { type: String, default: "Nothing here yet." },
})

defineEmits(["rowClick"])
</script>

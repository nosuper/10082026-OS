<template>
  <div class="flex min-h-screen items-center justify-center bg-gray-50">
    <div class="w-full max-w-md rounded-lg border bg-white p-8 text-center shadow-sm">
      <h1 class="text-2xl font-semibold text-gray-900">AuraOS</h1>
      <p class="mt-2 text-gray-600">
        Placeholder page — the frappe-ui toolchain is wired end to end.
      </p>
      <Button class="mt-6" variant="solid" @click="count++">
        Clicked {{ count }} {{ count === 1 ? "time" : "times" }}
      </Button>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue"
import { Button } from "frappe-ui"

const count = ref(0)
</script>

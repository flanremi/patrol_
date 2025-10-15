<template>
  <div class="text-center p-3 bg-gray-50 rounded-md">
    <div class="text-xs text-gray-500 font-medium mb-1">{{ label }}</div>
    <div
      class="text-xl font-bold text-gray-900"
      :class="{
        'text-green-600': status === 'ok',
        'text-amber-600': status === 'loading',
        'text-red-600': status === 'error',
      }"
    >
      {{ value }}
    </div>
  </div>
</template>

<script setup>
defineProps({
  label: {
    type: String,
    required: true,
  },
  value: {
    type: [String, Number],
    required: true,
  },
  status: {
    type: String,
    default: '', // 'ok', 'loading', 'error'
  },
})
</script>

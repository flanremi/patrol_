<template>
  <div class="flex items-center gap-2.5 p-2 bg-gray-50 rounded-md transition-colors duration-200 hover:bg-gray-100">
    <div
      class="w-8 h-8 flex items-center justify-center text-base rounded-md text-white"
      :style="{ backgroundColor: color }"
    >
      {{ icon }}
    </div>
    <div class="flex-1 text-sm font-medium text-gray-700">
      {{ label }}
    </div>
    <div class="text-xs font-semibold text-gray-500 bg-white px-2 py-0.5 rounded">
      {{ count }}
    </div>
  </div>
</template>

<script setup>
defineProps({
  icon: {
    type: String,
    required: true,
  },
  label: {
    type: String,
    required: true,
  },
  color: {
    type: String,
    required: true,
  },
  count: {
    type: Number,
    required: true,
  },
})
</script>

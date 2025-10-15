<template>
  <button
    @click="$emit('click')"
    :disabled="disabled"
    class="flex items-center gap-2 h-5 w-5 justify-center text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded cursor-pointer transition-all duration-200 hover:bg-gray-50 hover:border-gray-400 disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:transform-none"
    :class="{
      'bg-blue-500 border-blue-500 text-white hover:bg-blue-600 hover:border-blue-600': primary,
      '!bg-blue-600 !border-blue-600': primary && !disabled,
    }"
  >
    <span class="text-base">
      <slot name="icon"></slot>
    </span>
    <span v-if="$slots.default">
      <slot></slot>
    </span>
  </button>
</template>

<script setup>
defineProps({
  disabled: {
    type: Boolean,
    default: false,
  },
  primary: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['click'])
</script>

<template>
  <button
    :class="[
      'flex items-center justify-center w-8 h-8 rounded transition-colors',
      variant === 'primary'
        ? 'text-white bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400'
        : variant === 'active'
        ? 'text-blue-600 bg-blue-50 hover:bg-blue-100'
        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100',
      disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
    ]"
    :disabled="disabled"
    :title="title"
    @click="$emit('click')"
  >
    <slot>
      <svg v-if="icon"
           class="w-4 h-4"
           :class="loading ? 'animate-spin' : ''"
           fill="none"
           stroke="currentColor"
           viewBox="0 0 24 24">
        <path stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              :d="icon"/>
      </svg>
    </slot>
  </button>
</template>

<script setup>
defineProps({
  variant: {
    type: String,
    default: 'default', // 'default' | 'primary' | 'active'
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  title: {
    type: String,
    default: '',
  },
  icon: {
    type: String,
    default: '',
  },
})

defineEmits(['click'])
</script>


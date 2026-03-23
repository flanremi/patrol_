<template>
  <div class="flex items-center gap-2.5">
    <!-- AI Agent Workflow Logo: 三角形网络节点 -->
    <Logo class="w-7 h-7"></Logo>

    <div class="flex flex-col">
      <h1 class="text-base font-semibold  leading-tight">{{ title }}</h1>
      <p class="text-xs text-blue-600 leading-tight">{{ subtitle }}</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: '中车巡检智能体平台'
  },
  subtitle: {
    type: String,
    default: ''
  }
})
</script>

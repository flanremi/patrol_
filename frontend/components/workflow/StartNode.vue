<template>
  <div class="relative">
    <!-- 节点主体 -->
    <div
      class="relative w-12 h-12 rounded-full bg-blue-500 border-2 border-blue-600 flex items-center justify-center transition-all duration-200 hover:bg-blue-600 hover:shadow-md"
      :class="{
        'ring-2 ring-blue-300 ring-offset-1': isHighlighted,
        'animate-pulse bg-blue-400': executionStatus === 'executing'
      }"
    >
      <!-- 图标 -->
      <div class="relative">
        <PlayIcon class="w-4 h-4 text-white"/>

        <!-- 执行状态指示器 -->
        <div v-if="executionStatus === 'executing'"
             class="absolute -top-0.5 -right-0.5">
          <div class="w-2 h-2 bg-green-400 rounded-full animate-ping"></div>
        </div>
        <div v-else-if="executionStatus === 'completed'"
             class="absolute -top-0.5 -right-0.5">
          <CheckCircleIcon class="w-2.5 h-2.5 text-green-500 bg-white rounded-full border border-gray-200"/>
        </div>
      </div>

      <!-- 右侧连接点 -->
      <div class="absolute top-1/2 right-0 w-1.5 h-1.5 -mr-0.5 -mt-0.5 bg-blue-700 rounded-full"></div>
    </div>
  </div>
</template>

<script setup>
import { toRefs } from 'vue'
import { CheckCircleIcon, PlayIcon } from '@heroicons/vue/24/solid'

const props = defineProps({
  nodeData: {
    type: Object,
    required: true,
  },
  executionStatus: {
    type: String,
    default: null,
  },
  executionProgress: {
    type: Number,
    default: 0,
  },
  isHighlighted: {
    type: Boolean,
    default: false,
  },
})

const { nodeData, executionStatus, isHighlighted } = toRefs(props)
</script>

<style scoped>
@keyframes pulse {
  0%, 100% {
    opacity: 0.3;
  }
  50% {
    opacity: 0.5;
  }
}
</style>


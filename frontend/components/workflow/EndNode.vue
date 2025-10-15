<template>
  <div class="relative">
    <!-- 外圈发光效果 -->
    <div class="absolute -inset-1 bg-gradient-to-br from-red-400 via-rose-500 to-pink-500 rounded-full opacity-30 blur-lg animate-pulse"></div>
    
    <!-- 节点主体 -->
    <div 
      class="relative w-24 h-24 rounded-full bg-gradient-to-br from-red-500 via-rose-600 to-pink-600 shadow-xl transition-all duration-300 hover:shadow-2xl hover:scale-105"
      :class="{
        'ring-4 ring-blue-400 ring-offset-2': isHighlighted,
        'animate-pulse': executionStatus === 'executing'
      }"
    >
      <!-- 内圈背景 -->
      <div class="absolute inset-2 bg-white rounded-full flex items-center justify-center">
        <!-- 图标 -->
        <div class="relative">
          <FlagIcon class="w-10 h-10 text-rose-600" />
          
          <!-- 执行状态指示器 -->
          <div v-if="executionStatus === 'executing'" 
               class="absolute -top-1 -right-1">
            <span class="flex h-4 w-4">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-4 w-4 bg-blue-500"></span>
            </span>
          </div>
          <div v-else-if="executionStatus === 'completed'" 
               class="absolute -top-1 -right-1">
            <CheckCircleIcon class="w-5 h-5 text-green-600 bg-white rounded-full" />
          </div>
        </div>
      </div>
      
      <!-- 进度环 -->
      <svg v-if="executionProgress > 0" 
           class="absolute inset-0 w-full h-full -rotate-90"
           viewBox="0 0 100 100">
        <circle
          cx="50"
          cy="50"
          r="46"
          fill="none"
          stroke="rgba(255,255,255,0.3)"
          stroke-width="2"
        />
        <circle
          cx="50"
          cy="50"
          r="46"
          fill="none"
          stroke="white"
          stroke-width="2"
          stroke-linecap="round"
          :stroke-dasharray="`${executionProgress * 2.89} 289`"
          class="transition-all duration-300"
        />
      </svg>
    </div>
    
    <!-- 标签 -->
    <div class="absolute -bottom-7 left-1/2 -translate-x-1/2 whitespace-nowrap">
      <div class="px-3 py-1 bg-rose-600 text-white text-xs font-bold rounded-full shadow-lg">
        {{ nodeData.label || nodeData.name || '结束' }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { toRefs } from 'vue'
import { FlagIcon, CheckCircleIcon } from '@heroicons/vue/24/solid'

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

const { nodeData, executionStatus, executionProgress, isHighlighted } = toRefs(props)
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


<template>
  <transition name="slide-left">
    <div
      v-if="selectedNode"
      class="absolute top-0 right-0 w-[380px] h-full bg-white border-l border-slate-200/80 shadow-2xl overflow-hidden z-50 flex flex-col backdrop-blur-sm"
    >
      <!-- 抽屉头部 - 简洁风格 -->
      <div class="flex-shrink-0 border-b border-slate-200/80">
        <div class="px-4 py-3 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="w-1.5 h-1.5 rounded-full bg-blue-500"></div>
            <h3 class="text-xs font-semibold text-slate-900">节点详情</h3>
          </div>
          <button
            @click="$emit('close')"
            class="w-7 h-7 flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-all duration-200"
            title="关闭"
          >
            <XMarkIcon class="w-4 h-4"/>
          </button>
        </div>
      </div>

      <!-- 抽屉内容 -->
      <div class="flex-1 overflow-hidden bg-slate-50/30">
        <WorkflowNodeInfo :node="selectedNode"/>
      </div>

      <!-- 抽屉底部 - 极简状态栏 -->
      <div class="flex-shrink-0 border-t border-slate-200/80 bg-white/80 backdrop-blur-sm">
        <div class="px-4 py-2.5 flex items-center justify-between text-xs">
          <div class="flex items-center gap-1.5 text-slate-500">
            <div class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
            <span class="font-medium">Active</span>
          </div>
          <span class="text-slate-400 font-mono tabular-nums">
            {{ currentTime }}
          </span>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import WorkflowNodeInfo from './WorkflowNodeInfo.vue'
import { computed } from 'vue'
import { XMarkIcon } from '@heroicons/vue/24/outline'

defineProps({
  selectedNode: {
    type: Object,
    default: null,
  },
})

defineEmits(['close'])

const currentTime = computed(() => {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
})
</script>

<style scoped>
/* 自定义滚动条 */
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.4);
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.6);
}

/* 抽屉动画 */
.slide-left-enter-active,
.slide-left-leave-active {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease;
}

.slide-left-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.slide-left-leave-to {
  transform: translateX(100%);
  opacity: 0;
}
</style>

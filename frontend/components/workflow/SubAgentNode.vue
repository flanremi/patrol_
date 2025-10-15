<template>
  <BaseWorkflowNode
    :node-data="nodeData"
    :execution-status="executionStatus"
    :execution-progress="executionProgress"
    :is-highlighted="isHighlighted"
    :node-width="NODE_TYPE_SIZES.subagent.width"
    :node-height="NODE_TYPE_SIZES.subagent.height"
    :icon="CubeIcon"
    :icon-bg-class="'text-blue-500 bg-blue-50'"
    :top-bar-color="'bg-blue-500'"
  >
    <!-- 自定义头部 -->
    <template #header="{ nodeData }">
      <div class="flex items-center gap-3 px-0.5">
        <!-- 图标容器 -->
        <div class="relative">
          <div class="absolute inset-0 bg-blue-400 rounded-lg blur opacity-20"></div>
          <div class="relative flex items-center justify-center w-9 h-9 rounded-lg flex-shrink-0 text-blue-600 bg-gradient-to-br from-blue-50 to-blue-100/80 shadow-sm border border-blue-200/40">
            <CubeIcon class="w-5 h-5 stroke-[2.5]"/>
          </div>
        </div>

        <!-- 标题区域 -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 ">
            <h3 class="text-sm font-bold text-slate-900 truncate tracking-tight">
              {{nodeData.label || nodeData.id}}
            </h3>
          </div>
          <!-- 描述 -->
          <div
            v-if="nodeData.description"
            class="text-[11px] text-slate-500 leading-relaxed line-clamp-1 font-medium"
          >
            {{nodeData.description}}
          </div>
        </div>

        <!-- 执行状态图标 -->
        <div v-if="executionStatus"
             class="flex items-center flex-shrink-0">
          <span
            v-if="executionStatus === 'executing'"
            class="inline-flex items-center justify-center w-6 h-6 rounded-lg bg-blue-100 shadow-sm"
          >
            <ArrowPathIcon class="w-4 h-4 text-blue-600 animate-spin"/>
          </span>
          <span
            v-else-if="executionStatus === 'completed'"
            class="inline-flex items-center justify-center w-6 h-6 rounded-lg bg-green-100 shadow-sm"
          >
            <CheckCircleIcon class="w-4 h-4 text-green-600"/>
          </span>
          <span
            v-else-if="executionStatus === 'error'"
            class="inline-flex items-center justify-center w-6 h-6 rounded-lg bg-red-100 shadow-sm"
          >
            <XCircleIcon class="w-4 h-4 text-red-600"/>
          </span>
        </div>
      </div>
    </template>

    <!-- 节点主体内容 -->
    <template #body="{ nodeData }">
      <div class="flex flex-col flex-1 justify-center space-y-2.5 px-0.5">
        <!-- 子智能体配置 -->
        <div class="flex items-center justify-between gap-2">
          <!-- 父智能体 -->
          <div v-if="nodeData.parentAgent"
               class="flex items-center gap-1.5 px-2 py-1 bg-slate-50 rounded-lg border border-slate-200/60 flex-1 min-w-0">
            <ArrowUpIcon class="w-3.5 h-3.5 text-slate-400 flex-shrink-0"/>
            <span class="text-[11px] font-medium text-slate-600 truncate">{{nodeData.parentAgent}}</span>
          </div>

          <!-- 优先级 -->
          <div v-if="nodeData.priority"
               class="flex items-center gap-1 flex-shrink-0">
            <span class="px-2 py-1 text-[10px] font-semibold rounded-lg shadow-sm"
                  :class="getPriorityClass(nodeData.priority)">
              {{getPriorityLabel(nodeData.priority)}}
            </span>
          </div>
        </div>

        <!-- 任务类型 -->
        <div v-if="nodeData.taskType"
             class="flex items-center gap-2 px-2.5 py-1.5 bg-white rounded-lg border border-slate-200/80 shadow-sm">
          <BriefcaseIcon class="w-4 h-4 text-indigo-500 flex-shrink-0"/>
          <span class="text-[11px] font-medium text-slate-700 truncate">{{nodeData.taskType}}</span>
        </div>

        <!-- 工具列表 -->
        <div v-if="nodeData.tools && nodeData.tools.length > 0"
             class="space-y-1.5">
          <div class="flex items-center gap-1.5 px-1">
            <div class="h-px flex-1 bg-slate-200"></div>
            <span class="text-[9px] font-semibold text-slate-400 uppercase tracking-wider">工具</span>
            <div class="h-px flex-1 bg-slate-200"></div>
          </div>
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="(tool, index) in nodeData.tools.slice(0, 2)"
              :key="index"
              class="px-2 py-1 text-[10px] font-semibold bg-gradient-to-br from-amber-50 to-amber-100/50 text-amber-700 rounded-md border border-amber-200/60 shadow-sm"
            >
              {{tool}}
            </span>
            <span
              v-if="nodeData.tools.length > 2"
              class="px-2 py-1 text-[10px] font-semibold bg-slate-100 text-slate-600 rounded-md"
            >
              +{{nodeData.tools.length - 2}}
            </span>
          </div>
        </div>
      </div>
    </template>
  </BaseWorkflowNode>
</template>

<script setup>
import { toRefs } from 'vue'
import BaseWorkflowNode from './BaseWorkflowNode.vue'
import { NODE_TYPE_SIZES } from '../../composables/useNodeControl'
import {
  ArrowPathIcon,
  ArrowUpIcon,
  BriefcaseIcon,
  CheckCircleIcon,
  CubeIcon,
  XCircleIcon,
} from '@heroicons/vue/24/outline'

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

// 获取优先级样式
const getPriorityClass = (priority) => {
  const classes = {
    high: 'bg-gradient-to-br from-red-100 to-red-200/60 text-red-700 border border-red-300/60',
    medium: 'bg-gradient-to-br from-yellow-100 to-yellow-200/60 text-yellow-700 border border-yellow-300/60',
    low: 'bg-gradient-to-br from-green-100 to-green-200/60 text-green-700 border border-green-300/60',
  }
  return classes[priority] || 'bg-slate-100 text-slate-600 border border-slate-200'
}

// 获取优先级标签
const getPriorityLabel = (priority) => {
  const labels = {
    high: '高优先级',
    medium: '中优先级',
    low: '低优先级',
  }
  return labels[priority] || priority
}
</script>


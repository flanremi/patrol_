<template>
  <div class="relative p-[2px] rounded-lg bg-gradient-to-br from-indigo-500 via-yellow-500 to-gray-300 shadow-lg"
       style="background-image: linear-gradient(123deg, #5d70f4, #f3c647, #ccc 50%);"
  >
    <BaseWorkflowNode
      :node-data="nodeData"
      :execution-status="executionStatus"
      :execution-progress="executionProgress"
      :is-highlighted="isHighlighted"
      :node-width="NODE_TYPE_SIZES.agent.width"
      :node-height="NODE_TYPE_SIZES.agent.height"
      :icon="SparklesIcon"
      :icon-bg-class="'text-transparent bg-gradient-to-br from-pink-500 to-blue-600'"
    >
      <!-- 自定义头部 -->
      <template #header="{ nodeData }">
        <div class="flex flex-col items-center gap-3 p-3 border-b">
          <!-- 图标容器 - 带动画光晕效果 -->
          <div class="relative">
            <div class="relative flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-pink-50 to-blue-50 shadow-sm">
              <SparklesIcon class="w-6 h-6 text-pink-600"/>
            </div>
          </div>

          <!-- 标题区域 -->
          <div class="text-center min-w-0 w-full px-2">
            <h3 class="text-base font-bold text-slate-900 truncate mb-1 tracking-tight">
              {{nodeData.label || nodeData.id}}
            </h3>
            <!-- 描述 -->
            <div
              v-if="nodeData.description"
              class="text-[11px] text-slate-500 leading-relaxed line-clamp-2 font-medium"
            >
              {{nodeData.description}}
            </div>
          </div>

          <!-- 执行状态图标 -->
          <div v-if="executionStatus"
               class="absolute top-3 right-3 flex items-center flex-shrink-0">
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
        <div class="flex flex-col flex-1 space-y-3 p-1">
          <!-- 描述 -->
          <div
            v-if="nodeData.description2"
            class="text-xs text-slate-600 overflow-hidden leading-6 line-clamp-3 px-3 rounded-lg"
          >
            {{nodeData.description2}}
          </div>

          <!-- 智能体配置信息 -->
          <div v-if="nodeData.model || nodeData.temperature"
               class="grid grid-cols-2 gap-2.5 px-2">
            <!-- 模型信息 -->
            <div v-if="nodeData.model"
                 class="flex items-center gap-2 px-2.5 py-1.5 bg-white rounded-lg border border-slate-200/80 shadow-sm">
              <CpuChipIcon class="w-4 h-4 text-indigo-500 flex-shrink-0"/>
              <span class="text-[11px] font-medium text-slate-700 truncate">{{nodeData.model}}</span>
            </div>

            <!-- 温度参数 -->
            <div v-if="nodeData.temperature !== undefined"
                 class="flex items-center gap-2 px-2.5 py-1.5 bg-white rounded-lg border border-slate-200/80 shadow-sm">
              <FireIcon class="w-4 h-4 text-orange-500 flex-shrink-0"/>
              <span class="text-[11px] font-medium text-slate-700">T: {{nodeData.temperature}}</span>
            </div>
          </div>

          <!-- 工具列表 -->
          <div v-if="nodeData.tools && nodeData.tools.length > 0"
               class="space-y-1.5 px-2">
            <div class="flex items-center gap-1.5">
              <div class="h-px flex-1 bg-gradient-to-r from-transparent via-slate-200 to-transparent"></div>
              <span class="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">工具</span>
              <div class="h-px flex-1 bg-gradient-to-r from-transparent via-slate-200 to-transparent"></div>
            </div>
            <div class="flex flex-wrap gap-1.5">
              <span
                v-for="(tool, index) in nodeData.tools.slice(0, 3)"
                :key="index"
                class="px-2 py-1 text-[10px] font-semibold bg-gradient-to-br from-amber-50 to-amber-100/50 text-amber-700 rounded-md border border-amber-200/60 shadow-sm"
              >
                {{tool}}
              </span>
              <span
                v-if="nodeData.tools.length > 3"
                class="px-2 py-1 text-[10px] font-semibold bg-slate-100 text-slate-600 rounded-md"
              >
                +{{nodeData.tools.length - 3}}
              </span>
            </div>
          </div>

          <!-- 系统提示词预览 -->
          <div v-if="nodeData.systemPrompt"
               class="mx-2 text-[11px] text-slate-600 leading-relaxed line-clamp-2 bg-gradient-to-br from-slate-50 to-slate-100/50 rounded-lg px-3 py-2 border border-slate-200/60 shadow-sm">
            <span class="font-medium text-slate-500">💬 </span>{{nodeData.systemPrompt}}
          </div>
        </div>
      </template>
    </BaseWorkflowNode>
  </div>
</template>

<script setup>
import { toRefs } from 'vue'
import BaseWorkflowNode from './BaseWorkflowNode.vue'
import { NODE_TYPE_SIZES } from '~/composables/useNodeControl'
import {
  ArrowPathIcon,
  CheckCircleIcon,
  CpuChipIcon,
  FireIcon,
  SparklesIcon,
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
</script>


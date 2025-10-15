<template>
  <BaseWorkflowNode
    :node-data="nodeData"
    :execution-status="executionStatus"
    :execution-progress="executionProgress"
    :is-highlighted="isHighlighted"
    :node-width="NODE_TYPE_SIZES.tool.width"
    :node-height="NODE_TYPE_SIZES.tool.height"
    :icon="WrenchScrewdriverIcon"
    :icon-bg-class="'text-amber-500 bg-amber-50'"
    :top-bar-color="'bg-amber-500'"
  >
    <!-- 自定义头部 -->
    <template #header="{ nodeData }">
      <div class="flex items-center gap-3 px-0.5">
        <!-- 图标容器 -->
        <div class="relative">
          <div class="absolute inset-0 bg-amber-400 rounded-lg blur opacity-20"></div>
          <div class="relative flex items-center justify-center w-9 h-9 rounded-lg flex-shrink-0 text-amber-600 bg-gradient-to-br from-amber-50 to-amber-100/80 shadow-sm border border-amber-200/40">
            <component :is="getToolIcon(nodeData.toolType)"
                       class="w-5 h-5 stroke-[2.5]"/>
          </div>
        </div>

        <!-- 标题区域 -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 mb-0.5">
            <h3 class="text-sm font-bold text-slate-900 truncate tracking-tight">
              {{nodeData.label || nodeData.id}}
            </h3>
          </div>
          <!-- 工具类型标签 -->
          <div v-if="nodeData.toolType"
               class="inline-flex items-center gap-1">
            <span class="text-[10px] font-semibold text-amber-600 uppercase tracking-wide">
              {{getToolTypeLabel(nodeData.toolType)}}
            </span>
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
        <!-- 输入参数 -->
        <div v-if="nodeData.parameters && Object.keys(nodeData.parameters).length > 0"
             class="space-y-1.5">
          <div class="flex items-center gap-1.5 px-1">
            <div class="h-px flex-1 bg-slate-200"></div>
            <span class="text-[9px] font-semibold text-slate-400 uppercase tracking-wider">参数</span>
            <div class="h-px flex-1 bg-slate-200"></div>
          </div>
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="(value, key) in getDisplayParameters(nodeData.parameters)"
              :key="key"
              class="px-2 py-1 text-[10px] font-mono font-medium bg-white text-slate-700 rounded-md border border-slate-200/80 shadow-sm"
            >
              {{key}}
            </span>
            <span
              v-if="Object.keys(nodeData.parameters).length > 3"
              class="px-2 py-1 text-[10px] font-semibold bg-slate-100 text-slate-600 rounded-md"
            >
              +{{Object.keys(nodeData.parameters).length - 3}}
            </span>
          </div>
        </div>

        <!-- 工具状态标签 -->
        <div class="flex items-center gap-2">
          <div v-if="nodeData.isAsync"
               class="inline-flex items-center gap-1.5 px-2 py-1 bg-gradient-to-br from-blue-100 to-blue-200/60 text-blue-700 rounded-lg border border-blue-300/60 shadow-sm">
            <div class="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></div>
            <span class="text-[10px] font-semibold">异步执行</span>
          </div>
        </div>
      </div>
    </template>
  </BaseWorkflowNode>
</template>

<script setup>
import { toRefs } from 'vue'
import BaseWorkflowNode from './BaseWorkflowNode.vue'
import { NODE_TYPE_SIZES } from '~/composables/useNodeControl'
import {
  ArrowPathIcon,
  CheckCircleIcon,
  CloudIcon,
  CodeBracketIcon,
  DocumentTextIcon,
  MagnifyingGlassIcon,
  PhotoIcon,
  ServerIcon,
  WrenchScrewdriverIcon,
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

// 根据工具类型获取图标
const getToolIcon = (toolType) => {
  const iconMap = {
    search: MagnifyingGlassIcon,
    document: DocumentTextIcon,
    image: PhotoIcon,
    code: CodeBracketIcon,
    api: CloudIcon,
    database: ServerIcon,
    default: WrenchScrewdriverIcon,
  }
  return iconMap[toolType] || iconMap.default
}

// 获取工具类型标签
const getToolTypeLabel = (toolType) => {
  const labelMap = {
    search: '搜索',
    document: '文档',
    image: '图像',
    code: '代码',
    api: 'API',
    database: '数据库',
  }
  return labelMap[toolType] || toolType
}

// 获取显示的参数（最多3个）
const getDisplayParameters = (parameters) => {
  const entries = Object.entries(parameters)
  return Object.fromEntries(entries.slice(0, 3))
}

</script>


<template>
  <div class="relative">
    <BaseWorkflowNode
      :node-data="nodeData"
      :execution-status="executionStatus"
      :execution-progress="executionProgress"
      :is-highlighted="isHighlighted"
      :node-width="NODE_TYPE_SIZES.default.width"
      :node-height="NODE_TYPE_SIZES.default.height"
      :icon="getNodeIcon(nodeData.type)"
      :icon-bg-class="getIconBgClasses(nodeData.type)"
      :top-bar-color="getTopBarClasses(nodeData.type)"
    >
      <!-- 自定义头部 -->
      <template #header="{ nodeData }">
        <div class="flex items-center gap-2.5">
          <!-- 图标容器 -->
          <div
            class="flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0"
            :class="getIconBgClasses(nodeData.type)"
          >
            <component
              :is="getNodeIcon(nodeData.type)"
              class="w-4 h-4"
            />
          </div>

          <!-- 标题区域 -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-1.5 mb-0.5">
              <h3 class="text-sm font-semibold text-slate-900 truncate">
                {{nodeData.label || nodeData.id}}
              </h3>
              <!-- 子节点标记 -->
              <component
                v-if="nodeData.hasChildren"
                :is="CubeIcon"
                class="w-3 h-3 text-slate-400"
                title="包含子节点"
              />
            </div>
            <!-- 描述 -->
            <div
              v-if="nodeData.description"
              class="text-xs text-slate-500 leading-tight line-clamp-1"
            >
              {{nodeData.description}}
            </div>
          </div>

          <!-- 执行状态图标 -->
          <div v-if="executionStatus"
               class="flex items-center flex-shrink-0">
            <span
              v-if="executionStatus === 'executing'"
              class="inline-flex items-center justify-center w-5 h-5 rounded bg-blue-100"
            >
              <ArrowPathIcon class="w-3.5 h-3.5 text-blue-600 animate-spin"/>
            </span>
            <span
              v-else-if="executionStatus === 'completed'"
              class="inline-flex items-center justify-center w-5 h-5 rounded bg-green-100"
            >
              <CheckCircleIcon class="w-3.5 h-3.5 text-green-600"/>
            </span>
            <span
              v-else-if="executionStatus === 'error'"
              class="inline-flex items-center justify-center w-5 h-5 rounded bg-red-100"
            >
              <XCircleIcon class="w-3.5 h-3.5 text-red-600"/>
            </span>
          </div>
        </div>
      </template>
    </BaseWorkflowNode>
  </div>
</template>

<script setup>
import { toRefs } from 'vue'
import BaseWorkflowNode from './BaseWorkflowNode.vue'
import {
  ArrowPathIcon,
  ArrowsRightLeftIcon,
  ChatBubbleLeftRightIcon,
  CheckCircleIcon,
  CubeIcon,
  DocumentTextIcon,
  FlagIcon,
  PlayIcon,
  QuestionMarkCircleIcon,
  SparklesIcon,
  UserGroupIcon,
  UserIcon,
  WrenchIcon,
  WrenchScrewdriverIcon,
  XCircleIcon,
} from '@heroicons/vue/24/outline'
import { NODE_TYPE_SIZES } from '~/composables/useNodeControl'

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

// 获取顶部条颜色
const getTopBarClasses = (type) => {
  const barClasses = {
    start: 'bg-green-500',
    end: 'bg-red-500',
    chatbot: 'bg-blue-500',
    tool: 'bg-amber-500',
    tools: 'bg-amber-500',
    summary: 'bg-cyan-500',
    agent: 'bg-pink-500',
    subagent: 'bg-blue-500',
    worker: 'bg-teal-500',
    router: 'bg-gray-500',
    condition: 'bg-orange-500',
    default: 'bg-gray-400',
  }
  return barClasses[type] || barClasses.default
}

// 获取图标背景样式
const getIconBgClasses = (type) => {
  const bgClasses = {
    start: 'text-green-500 bg-gray-100',
    end: 'text-red-500 bg-gray-100',
    chatbot: 'text-blue-500 bg-gray-100',
    tool: 'text-amber-500 bg-gray-100',
    tools: 'text-amber-500 bg-gray-100',
    summary: 'text-cyan-500 bg-gray-100',
    agent: 'text-pink-500 bg-gray-100',
    supervisor: 'text-indigo-500 bg-gray-100',
    subagent: 'text-blue-500 bg-gray-100',
    worker: 'text-teal-500 bg-gray-100',
    router: 'text-gray-500 bg-gray-100',
    condition: 'text-orange-500 bg-gray-100',
    default: 'text-gray-500 bg-gray-100',
  }
  return bgClasses[type] || bgClasses.default
}

// 获取节点图标（使用 Heroicons）
const getNodeIcon = (type) => {
  const iconMap = {
    start: PlayIcon,
    end: FlagIcon,
    chatbot: ChatBubbleLeftRightIcon,
    tool: WrenchIcon,
    tools: WrenchScrewdriverIcon,
    summary: DocumentTextIcon,
    agent: SparklesIcon,
    supervisor: UserGroupIcon,
    subagent: CubeIcon,
    worker: UserIcon,
    router: ArrowsRightLeftIcon,
    condition: QuestionMarkCircleIcon,
    default: CubeIcon,
  }
  return iconMap[type] || iconMap.default
}

</script>



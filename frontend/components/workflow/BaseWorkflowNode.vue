<template>
  <div
  >
    <!-- 输入输出端口 (Handles) -->
    <Handle
      v-if="!isStartNode"
      type="target"
      :position="Position.Left"
      class="!w-3 !h-3 !bg-white !border !border-gray-300 !rounded-full transition-all duration-200 hover:!border-blue-500 hover:!bg-blue-500 hover:!shadow-lg !-left-0 !z-10"
    />
    <Handle
      v-if="!isEndNode"
      type="source"
      :position="Position.Right"
      class="!w-3 !h-3 !bg-white !border !border-gray-300 !rounded-full transition-all duration-200 hover:!border-blue-500 hover:!bg-blue-500 hover:!shadow-lg !-right-0 !z-10"
    />

    <!-- 节点内容 -->
    <div
      class="flex flex-col bg-white rounded-lg overflow-hidden cursor-pointer transition-all duration-300 border border-slate-200 relative"
      :style="{ width: nodeWidth + 'px', height: nodeHeight + 'px' }"
      :class="[
        nodeData.selected ? 'shadow-lg ring-2 ring-blue-500' : 'shadow hover:shadow-md',
        getExecutionStatusClasses(),
        isHighlighted ? 'ring-4 ring-orange-400 shadow-2xl scale-105 z-50' : ''
      ]"
    >
      <!-- 高亮发光效果 -->
      <div
        v-if="isHighlighted"
        class="absolute inset-0 rounded-lg bg-gradient-to-r from-orange-400/20 via-yellow-400/20 to-orange-400/20 animate-pulse pointer-events-none"
      ></div>
      <!-- 彩色顶部条 -->
      <div
        v-if="false"
        class="h-1 flex-shrink-0"
        :class="getTopBarClasses()"
      >
        <div
          v-if="executionProgress > 0 && executionProgress < 100"
          class="h-full bg-white/40 transition-all duration-300"
          :style="{ width: executionProgress + '%' }"
        ></div>
      </div>

      <!-- 插槽：节点头部 -->
      <div class="px-3 py-2.5 flex-shrink-0">
        <slot name="header"
              :nodeData="nodeData"
              :executionStatus="executionStatus">
          <!-- 默认头部 -->
          <div class="flex items-center gap-2.5">
            <!-- 图标容器 -->
            <div
              class="flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0"
              :class="iconBgClass"
            >
              <component
                :is="icon"
                class="w-4 h-4"
              />
            </div>

            <!-- 标题区域 -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-1.5 mb-0.5">
                <h3 class="text-sm font-semibold text-slate-900 truncate">
                  {{nodeData.label || nodeData.id}}
                </h3>
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
        </slot>
      </div>

      <!-- 插槽：节点主体内容 -->
      <div v-if="$slots.body"
           class="px-3 pb-2.5 pt-0 flex-1 min-h-0 flex flex-col">
        <slot name="body"
              :nodeData="nodeData"
              :executionStatus="executionStatus"></slot>
      </div>

      <!-- 插槽：节点底部 -->
      <div v-if="$slots.footer"
           class="px-3 py-2 bg-slate-50 border-t border-slate-100 flex-shrink-0">
        <slot name="footer"
              :nodeData="nodeData"
              :executionStatus="executionStatus"></slot>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, toRefs } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { ArrowPathIcon, CheckCircleIcon, CubeIcon, XCircleIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  nodeData: {
    type: Object,
    required: true,
  },
  executionStatus: {
    type: String,
    default: null,
    validator: (value) => ['executing', 'completed', 'error', 'pending', null].includes(value),
  },
  executionProgress: {
    type: Number,
    default: 0,
    validator: (value) => value >= 0 && value <= 100,
  },
  isHighlighted: {
    type: Boolean,
    default: false,
  },
  nodeWidth: {
    type: Number,
    default: 240, // 默认 w-56 = 224px
  },
  nodeHeight: {
    type: Number,
    default: 120,
  },
  icon: {
    default: () => CubeIcon,
  },
  iconBgClass: {
    type: String,
    default: 'text-gray-500 bg-gray-100',
  },
  topBarColor: {
    type: String,
    default: 'bg-gray-400',
  },
})

const { nodeData, executionStatus, executionProgress, isHighlighted } = toRefs(props)

// 获取顶部条颜色
const getTopBarClasses = () => {
  if (executionStatus.value === 'executing') return 'bg-blue-500'
  if (executionStatus.value === 'completed') return 'bg-green-500'
  if (executionStatus.value === 'error') return 'bg-red-500'
  return props.topBarColor
}

// 获取执行状态样式类
const getExecutionStatusClasses = () => {
  const statusClasses = {
    executing: 'ring-2 ring-blue-400',
    completed: '',
    error: 'ring-2 ring-red-400',
  }
  return statusClasses[executionStatus.value] || ''
}

// 判断是否为开始/结束节点
const isStartNode = computed(() => {
  return props.nodeData.type === 'start' || props.nodeData.id === 'start' || props.nodeData.id === '__start__'
})

const isEndNode = computed(() => {
  return props.nodeData.type === 'end' || props.nodeData.id === 'end' || props.nodeData.id === '__end__'
})
</script>


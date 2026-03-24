<template>
  <div class="tool-selector">
    <!-- 工具选择按钮 - Gemini 风格 -->
    <div class="flex items-center gap-2">
      <!-- 添加工具按钮 -->
      <button
        @click="toggleDropdown"
        class="flex items-center gap-1.5 px-3 py-2 rounded-xl text-gray-600 hover:bg-gray-100 transition-all duration-200 border border-transparent hover:border-gray-200"
        :class="{ 'bg-gray-100 border-gray-200': isOpen }"
      >
        <PlusIcon class="w-4 h-4" />
        <Cog6ToothIcon class="w-4 h-4" />
        <span class="text-sm font-medium">工具</span>
      </button>
    </div>

    <!-- 下拉菜单 -->
    <Transition
      enter-active-class="transition ease-out duration-200"
      enter-from-class="opacity-0 translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition ease-in duration-150"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 translate-y-1"
    >
      <div
        v-if="isOpen"
        class="absolute left-0 bottom-full mb-2 w-80 bg-white rounded-2xl shadow-xl border border-gray-200 overflow-hidden z-50"
      >
        <!-- 标题 -->
        <div class="px-4 py-3 border-b border-gray-100 bg-gradient-to-r from-blue-50 to-white">
          <h3 class="text-sm font-bold text-gray-800">选择工具模块</h3>
          <p class="text-xs text-gray-500 mt-0.5">切换不同的智能体功能</p>
        </div>

        <!-- 工具列表 -->
        <div class="p-2 max-h-80 overflow-y-auto">
          <button
            v-for="tool in tools"
            :key="tool.id"
            @click="selectTool(tool)"
            class="w-full flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-200 group"
            :class="[
              selectedTool?.id === tool.id
                ? 'bg-blue-50 border-2 border-blue-200'
                : 'hover:bg-gray-50 border-2 border-transparent'
            ]"
          >
            <!-- 图标 -->
            <div
              class="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center text-xl transition-all duration-200"
              :class="getToolIconClass(tool.id, selectedTool?.id === tool.id)"
            >
              {{ tool.icon }}
            </div>

            <!-- 信息 -->
            <div class="flex-1 text-left">
              <div class="flex items-center gap-2">
                <span class="text-sm font-semibold text-gray-800">{{ tool.name }}</span>
                <span
                  v-if="selectedTool?.id === tool.id"
                  class="px-1.5 py-0.5 text-[10px] font-bold bg-blue-100 text-blue-600 rounded"
                >
                  当前
                </span>
              </div>
              <p class="text-xs text-gray-500 mt-0.5">{{ tool.description }}</p>
            </div>

            <!-- 选中指示 -->
            <div
              v-if="selectedTool?.id === tool.id"
              class="flex-shrink-0"
            >
              <CheckCircleIcon class="w-5 h-5 text-blue-500" />
            </div>
          </button>
        </div>

        <!-- 底部提示 -->
        <div class="px-4 py-2 bg-gray-50 border-t border-gray-100">
          <p class="text-[11px] text-gray-500">
            💡 切换工具后，对话将转发至对应的智能体处理
          </p>
        </div>
      </div>
    </Transition>

    <!-- 遮罩层 -->
    <div
      v-if="isOpen"
      class="fixed inset-0 z-40"
      @click="closeDropdown"
    ></div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import {
  PlusIcon,
  Cog6ToothIcon,
  CheckCircleIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  modelValue: {
    type: String,
    default: 'inspection'
  },
  tools: {
    type: Array,
    default: () => [
      {
        id: 'inspection',
        name: '故障检测工单',
        icon: '🔍',
        description: '智能故障检测与分析'
      },
      {
        id: 'planning',
        name: '巡检计划',
        icon: '📅',
        description: '自动生成巡检计划'
      },
      {
        id: 'repair',
        name: '维修方案',
        icon: '🔧',
        description: '维修方案咨询'
      },
      {
        id: 'quality',
        name: '工单质检',
        icon: '✅',
        description: '工单质量检查'
      },
      {
        id: 'training',
        name: '员工培训',
        icon: '📚',
        description: '新员工培训系统'
      },
      {
        id: 'field_guidance',
        name: '现场作业指导',
        icon: '📍',
        description: '语音/拍照/位置感知的智能指导'
      }
    ]
  }
})

const emit = defineEmits(['update:modelValue', 'tool-change'])

const isOpen = ref(false)

const selectedTool = computed(() => {
  return props.tools.find(t => t.id === props.modelValue)
})

const toggleDropdown = () => {
  isOpen.value = !isOpen.value
}

const closeDropdown = () => {
  isOpen.value = false
}

const selectTool = (tool) => {
  emit('update:modelValue', tool.id)
  emit('tool-change', tool)
  closeDropdown()
}

const getToolIconClass = (toolId, isSelected) => {
  const baseClasses = {
    inspection: 'bg-blue-100 group-hover:bg-blue-200',
    planning: 'bg-green-100 group-hover:bg-green-200',
    repair: 'bg-orange-100 group-hover:bg-orange-200',
    quality: 'bg-emerald-100 group-hover:bg-emerald-200',
    training: 'bg-purple-100 group-hover:bg-purple-200',
    field_guidance: 'bg-teal-100 group-hover:bg-teal-200'
  }

  if (isSelected) {
    return baseClasses[toolId]?.replace('group-hover:', '') || 'bg-gray-100'
  }

  return baseClasses[toolId] || 'bg-gray-100 group-hover:bg-gray-200'
}

</script>

<style scoped>
.tool-selector {
  position: relative;
}
</style>

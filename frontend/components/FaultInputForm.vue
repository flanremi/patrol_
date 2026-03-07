<template>
  <div class="fault-input-form bg-gradient-to-br from-amber-50 to-orange-50 rounded-2xl border-2 border-amber-200 p-6 shadow-lg animate-fade-in">
    <!-- 表单头部 -->
    <div class="flex items-center gap-3 mb-6">
      <div class="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center border-2 border-amber-200">
        <ClipboardDocumentListIcon class="w-5 h-5 text-amber-600"/>
      </div>
      <div>
        <h3 class="text-lg font-bold text-gray-900">故障信息录入</h3>
        <p class="text-sm text-gray-600">{{ message || '请填写以下信息以进行故障分析' }}</p>
      </div>
    </div>

    <!-- 表单内容 -->
    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- 检测时间 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          <span class="text-red-500 mr-1">*</span>检测时间
        </label>
        <input
          type="datetime-local"
          v-model="formData.detect_time"
          required
          class="w-full px-4 py-2.5 rounded-xl border-2 border-gray-200 focus:border-amber-400 focus:ring-2 focus:ring-amber-100 transition-all text-gray-900"
        />
      </div>

      <!-- 部件名称 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          <span class="text-red-500 mr-1">*</span>部件名称
        </label>
        <input
          type="text"
          v-model="formData.part_name"
          required
          placeholder="如：轴承、辅助逆变器、制动器"
          class="w-full px-4 py-2.5 rounded-xl border-2 border-gray-200 focus:border-amber-400 focus:ring-2 focus:ring-amber-100 transition-all text-gray-900 placeholder-gray-400"
        />
      </div>

      <!-- 部件位置 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          部件位置
        </label>
        <input
          type="text"
          v-model="formData.part_position"
          placeholder="如：0116车、A轴、前转向架"
          class="w-full px-4 py-2.5 rounded-xl border-2 border-gray-200 focus:border-amber-400 focus:ring-2 focus:ring-amber-100 transition-all text-gray-900 placeholder-gray-400"
        />
      </div>

      <!-- 缺陷类型 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          <span class="text-red-500 mr-1">*</span>缺陷类型
        </label>
        <input
          type="text"
          v-model="formData.defect_type"
          required
          placeholder="如：温度异常、显黄、振动过大、噪音"
          class="w-full px-4 py-2.5 rounded-xl border-2 border-gray-200 focus:border-amber-400 focus:ring-2 focus:ring-amber-100 transition-all text-gray-900 placeholder-gray-400"
        />
      </div>

      <!-- 检测置信度 -->
      <div class="form-group">
        <label class="block text-sm font-semibold text-gray-700 mb-1.5">
          检测置信度
          <span class="text-gray-500 font-normal ml-2">{{ (formData.detect_confidence * 100).toFixed(0) }}%</span>
        </label>
        <input
          type="range"
          v-model.number="formData.detect_confidence"
          min="0"
          max="1"
          step="0.01"
          class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-amber-500"
        />
        <div class="flex justify-between text-xs text-gray-500 mt-1">
          <span>0%</span>
          <span>100%</span>
        </div>
      </div>

      <!-- 按钮组 -->
      <div class="flex items-center gap-3 pt-4">
        <button
          type="submit"
          :disabled="isSubmitting || !isFormValid"
          class="flex-1 px-6 py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl hover:from-amber-600 hover:to-orange-600 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          <ArrowPathIcon v-if="isSubmitting" class="w-5 h-5 animate-spin"/>
          <MagnifyingGlassIcon v-else class="w-5 h-5"/>
          <span>{{ isSubmitting ? '分析中...' : '开始分析' }}</span>
        </button>
        <button
          type="button"
          @click="handleCancel"
          :disabled="isSubmitting"
          class="px-6 py-3 bg-gray-100 text-gray-700 font-semibold rounded-xl hover:bg-gray-200 transition-all duration-200 disabled:opacity-50"
        >
          取消
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import {
  ArrowPathIcon,
  ClipboardDocumentListIcon,
  MagnifyingGlassIcon,
} from '@heroicons/vue/24/outline'

// Props
const props = defineProps({
  message: {
    type: String,
    default: ''
  },
  fields: {
    type: Array,
    default: () => []
  }
})

// Emits
const emit = defineEmits(['submit', 'cancel'])

// 表单数据
const formData = reactive({
  detect_time: new Date().toISOString().slice(0, 16),
  part_name: '',
  part_position: '',
  defect_type: '',
  detect_confidence: 0.95
})

// 状态
const isSubmitting = ref(false)

// 表单验证
const isFormValid = computed(() => {
  return formData.part_name.trim() && formData.defect_type.trim()
})

// 提交表单
const handleSubmit = () => {
  if (!isFormValid.value) return

  isSubmitting.value = true
  emit('submit', { ...formData })
}

// 取消
const handleCancel = () => {
  emit('cancel')
}

// 重置提交状态（供父组件调用）
const resetSubmitting = () => {
  isSubmitting.value = false
}

defineExpose({
  resetSubmitting
})
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 自定义 range slider */
input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  background: linear-gradient(135deg, #f59e0b, #ea580c);
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(245, 158, 11, 0.4);
}

input[type="range"]::-moz-range-thumb {
  width: 20px;
  height: 20px;
  background: linear-gradient(135deg, #f59e0b, #ea580c);
  border-radius: 50%;
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 6px rgba(245, 158, 11, 0.4);
}
</style>

